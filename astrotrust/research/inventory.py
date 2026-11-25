"""Inspect every stored snapshot without opening a writable collector connection."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import TypedDict

from astrotrust.collector.consumer_models import ConsumerRun
from astrotrust.collector.consumer_store import identity as consumer_identity
from astrotrust.collector.models import ManualRun
from astrotrust.collector.store import identity as manual_identity


def read_captures(path: Path, *, consumer: bool = False) -> tuple[ManualRun | ConsumerRun, ...]:
    if not path.is_file():
        raise ValueError("Capture database is unavailable; select an existing local store")
    table = "consumer_snapshots" if consumer else "snapshots"
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        rows = db.execute(f"SELECT run_id, revision, record FROM {table} ORDER BY run_id, revision")
        latest: dict[str, ManualRun | ConsumerRun] = {}
        for run_id, revision, record in rows:
            run = (
                ConsumerRun.model_validate_json(record)
                if consumer
                else ManualRun.model_validate_json(record)
            )
            if run.run_id != run_id or len(run.history) != revision:
                raise ValueError("Snapshot identity/revision mismatch")
            previous = latest.get(run_id)
            if previous is not None:
                # The full history is carried in each snapshot. Raw evidence is immutable.
                ignored = {"metadata", "history"}
                if run.model_dump(exclude=ignored) != previous.model_dump(exclude=ignored):
                    raise ValueError("Raw evidence changed across snapshots")
                if run.history[:-1] != previous.history or revision != len(previous.history) + 1:
                    raise ValueError("Snapshot history is not append-only")
            latest[run_id] = run
        index_table = "consumer_runs" if consumer else "runs"
        identities = dict(db.execute(f"SELECT run_id, identity FROM {index_table}"))
        if identities.keys() != latest.keys():
            raise ValueError("Capture index and snapshots disagree")
        for run_id, capture in latest.items():
            expected = (
                consumer_identity(capture)
                if isinstance(capture, ConsumerRun)
                else manual_identity(capture)
            )
            if identities[run_id] != expected:
                raise ValueError("Capture index identity does not match its snapshot")
    return tuple(latest.values())


def store_status(path: Path, *, consumer: bool = False) -> dict[str, object]:
    if not path.is_file():
        return {"state": "unavailable", "captures": None, "message": "No store at this target"}
    try:
        runs = read_captures(path, consumer=consumer)
        return {
            "state": "captured" if runs else "pending",
            "captures": len(runs),
            "snapshots": sum(len(run.history) for run in runs),
            "schema_versions": sorted({run.schema_version for run in runs}),
            "message": "Exploratory evidence; annotation and validation remain pending",
        }
    except (ValueError, OSError, sqlite3.Error):
        return {
            "state": "error",
            "captures": None,
            "message": "Cannot verify this store. Check its path and integrity before using it.",
        }


class ResearchStatus(TypedDict):
    frontier: dict[str, object]
    consumer: dict[str, object]
    local: dict[str, object]
    astroguard: dict[str, object]
    rubric: str


def research_status(general: Path, consumer: Path) -> ResearchStatus:
    astroguard_model = Path("models/astroguard/adapter_model.safetensors")
    astroguard_info: dict[str, object] = (
        {
            "state": "trained",
            "model": "Qwen2.5-0.5B-LoRA",
            "location": "models/astroguard",
            "message": "AstroGuard safety classifier trained and staged in project directory",
        }
        if astroguard_model.is_file()
        else {"state": "proposed", "message": "No trained or validated classifier"}
    )
    return {
        "frontier": store_status(general),
        "consumer": store_status(consumer, consumer=True),
        "local": {
            "state": "prepared",
            "captures": None,
            "message": "Inference interface available; experiments have not been inventoried",
        },
        "astroguard": astroguard_info,
        "rubric": "draft-1.0 — no validated BCAS/ADRS aggregate",
    }
