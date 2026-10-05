"""Transactional local persistence with append-only snapshots and duplicate protection."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from astrotrust.collector.models import CaptureMetadata, ManualRun, MetadataRevision
from astrotrust.validation.files import canonical_json

DEFAULT_DATABASE = Path("data/pilot/manual-runs/collector.sqlite3")


class DuplicateCapture(ValueError):
    """An identity already exists; correct metadata rather than overwrite raw evidence."""


def identity(run: ManualRun) -> str:
    m = run.metadata
    return json.dumps(
        [
            run.canonical_prompt.scenario_id,
            run.condition_id,
            m.provider,
            m.product,
            m.model_label,
            m.run_number,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


class RunStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS runs ("
                "run_id TEXT PRIMARY KEY, identity TEXT NOT NULL UNIQUE);"
                "CREATE TABLE IF NOT EXISTS snapshots ("
                "run_id TEXT NOT NULL REFERENCES runs(run_id), revision INTEGER NOT NULL, "
                "record TEXT NOT NULL, PRIMARY KEY(run_id, revision));"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            with db:
                yield db
        finally:
            db.close()

    def all(self) -> tuple[ManualRun, ...]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT record FROM snapshots s WHERE revision = "
                "(SELECT MAX(revision) FROM snapshots WHERE run_id=s.run_id) ORDER BY s.run_id"
            ).fetchall()
        return tuple(ManualRun.model_validate_json(row[0]) for row in rows)

    def get(self, run_id: str) -> ManualRun:
        with self._connect() as db:
            row = db.execute(
                "SELECT record FROM snapshots WHERE run_id=? ORDER BY revision DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Run ID not found in this local store")
        return ManualRun.model_validate_json(row[0])

    def insert_many(self, runs: tuple[ManualRun, ...]) -> None:
        """All-or-nothing import; never replace existing records or revisions."""
        try:
            with self._connect() as db:
                for run in runs:
                    run = ManualRun.model_validate(run.model_dump())
                    db.execute("INSERT INTO runs VALUES (?, ?)", (run.run_id, identity(run)))
                    db.execute(
                        "INSERT INTO snapshots VALUES (?, ?, ?)",
                        (run.run_id, len(run.history), canonical_json(run)),
                    )
        except sqlite3.IntegrityError as exc:
            raise DuplicateCapture(
                "This run ID or scenario/condition/provider/product/exact model label/run "
                "already exists. Open the saved run to correct metadata with revision history; "
                "use the next unused run number for an independent capture."
            ) from exc

    def correct(
        self, run_id: str, metadata: CaptureMetadata, reason: str, expected_revision: int
    ) -> ManualRun:
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT record FROM snapshots WHERE run_id=? ORDER BY revision DESC LIMIT 1",
                    (run_id,),
                ).fetchone()
                if row is None:
                    raise ValueError("Run ID not found")
                old = ManualRun.model_validate_json(row[0])
                if len(old.history) != expected_revision:
                    raise ValueError("Record changed. Reopen it before correcting metadata.")
                revision = MetadataRevision(
                    revision=expected_revision + 1,
                    recorded_at=datetime.now(UTC),
                    reason=reason,
                    metadata=metadata,
                )
                updated = ManualRun.model_validate(
                    old.model_dump() | {"metadata": metadata, "history": (*old.history, revision)}
                )
                db.execute("UPDATE runs SET identity=? WHERE run_id=?", (identity(updated), run_id))
                db.execute(
                    "INSERT INTO snapshots VALUES (?, ?, ?)",
                    (run_id, expected_revision + 1, canonical_json(updated)),
                )
                return updated
        except sqlite3.IntegrityError as exc:
            raise DuplicateCapture(
                "Correction would duplicate an existing capture identity"
            ) from exc
