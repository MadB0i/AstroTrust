"""Separated consumer datastore with transactional, immutable capture snapshots."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from astrotrust.collector.consumer_models import ConsumerMetadata, ConsumerRevision, ConsumerRun
from astrotrust.collector.store import DuplicateCapture, SQLiteConnections, check_store_family
from astrotrust.validation.files import canonical_json

DEFAULT_CONSUMER_DATABASE = Path("data/pilot/consumer-app-runs/collector.sqlite3")


def identity(run: ConsumerRun) -> str:
    return json.dumps(
        [run.metadata.service_name, run.prompt_id, run.metadata.run_number],
        ensure_ascii=False,
        separators=(",", ":"),
    )


class ConsumerStore(SQLiteConnections):
    # Reuse connection/transaction handling only; consumer tables and records are separate.

    def __init__(self, path: Path) -> None:
        check_store_family(path, {"runs", "snapshots"})
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS consumer_runs ("
                "run_id TEXT PRIMARY KEY, identity TEXT NOT NULL UNIQUE);"
                "CREATE TABLE IF NOT EXISTS consumer_snapshots ("
                "run_id TEXT NOT NULL REFERENCES consumer_runs(run_id), revision INTEGER NOT NULL, "
                "record TEXT NOT NULL, PRIMARY KEY(run_id, revision));"
            )

    def all(self) -> tuple[ConsumerRun, ...]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT record FROM consumer_snapshots s WHERE revision = "
                "(SELECT MAX(revision) FROM consumer_snapshots WHERE run_id=s.run_id) "
                "ORDER BY s.run_id"
            ).fetchall()
        return tuple(ConsumerRun.model_validate_json(row[0]) for row in rows)

    def get(self, run_id: str) -> ConsumerRun:
        with self._connect() as db:
            row = db.execute(
                "SELECT record FROM consumer_snapshots WHERE run_id=? "
                "ORDER BY revision DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Run ID not found in this consumer store")
        return ConsumerRun.model_validate_json(row[0])

    def insert_many(self, runs: tuple[ConsumerRun, ...]) -> None:
        try:
            with self._connect() as db:
                for run in runs:
                    run = ConsumerRun.model_validate(run.model_dump())
                    db.execute(
                        "INSERT INTO consumer_runs VALUES (?, ?)", (run.run_id, identity(run))
                    )
                    db.execute(
                        "INSERT INTO consumer_snapshots VALUES (?, ?, ?)",
                        (run.run_id, len(run.history), canonical_json(run)),
                    )
        except sqlite3.IntegrityError as exc:
            raise DuplicateCapture(
                "This consumer run ID or service / prompt ID / run number already exists. "
                "Open the saved capture for a metadata revision or choose an unused run number."
            ) from exc

    def correct(
        self, run_id: str, metadata: ConsumerMetadata, reason: str, expected_revision: int
    ) -> ConsumerRun:
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT record FROM consumer_snapshots WHERE run_id=? "
                    "ORDER BY revision DESC LIMIT 1",
                    (run_id,),
                ).fetchone()
                if row is None:
                    raise ValueError("Run ID not found in this consumer store")
                old = ConsumerRun.model_validate_json(row[0])
                if len(old.history) != expected_revision:
                    raise ValueError("Record changed. Reopen it before correcting metadata.")
                revision = ConsumerRevision(
                    revision=expected_revision + 1,
                    recorded_at=datetime.now(UTC),
                    reason=reason,
                    metadata=metadata,
                )
                updated = ConsumerRun.model_validate(
                    old.model_dump() | {"metadata": metadata, "history": (*old.history, revision)}
                )
                db.execute(
                    "UPDATE consumer_runs SET identity=? WHERE run_id=?",
                    (identity(updated), run_id),
                )
                db.execute(
                    "INSERT INTO consumer_snapshots VALUES (?, ?, ?)",
                    (run_id, expected_revision + 1, canonical_json(updated)),
                )
                return updated
        except sqlite3.IntegrityError as exc:
            raise DuplicateCapture(
                "Correction would duplicate an existing consumer identity"
            ) from exc
