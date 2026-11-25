"""Small launcher and portable import/export commands."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from astrotrust.collector import consumer_exports
from astrotrust.collector.consumer_store import ConsumerStore
from astrotrust.collector.exports import ExportFormat, export, load_export, single_report
from astrotrust.collector.server import serve
from astrotrust.collector.store import RunStore


def command(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    database = root / args.database
    action = args.collect_action or "serve"
    consumer_mode = args.command == "collect-consumer"
    if action == "serve":
        serve(root, database, args.port, consumer_mode=consumer_mode)
    elif action == "validate":
        runs = (
            load_export(args.path) if not consumer_mode else consumer_exports.load_export(args.path)
        )
        print(f"Validated {len(runs)} exploratory captures, hashes and metadata histories.")
        print("Integrity validation does not authenticate frontend origin or scientific validity.")
    elif action == "import":
        if consumer_mode:
            imported_consumer = consumer_exports.load_export(args.path)
            ConsumerStore(database).insert_many(imported_consumer)
            count = len(imported_consumer)
        else:
            imported_general = load_export(args.path)
            RunStore(database).insert_many(imported_general)
            count = len(imported_general)
        print(f"Imported {count} captures atomically; no existing records overwritten.")
    else:
        if not database.is_file():
            raise ValueError("Local database does not exist; start the collector first")
        if consumer_mode:
            consumer_store = ConsumerStore(database)
            if args.run_id:
                if args.format != "markdown":
                    raise ValueError("--run-id requires --format markdown")
                content = consumer_exports.single_report(consumer_store.get(args.run_id))
            else:
                consumer_runs = consumer_store.all()
                if not consumer_runs:
                    raise ValueError("No consumer captures saved yet")
                content = consumer_exports.export(consumer_runs, cast(ExportFormat, args.format))
            _write_export(Path(args.output), content)
            return
        store = RunStore(database)
        if args.run_id:
            if args.format != "markdown":
                raise ValueError("--run-id requires --format markdown")
            content = single_report(store.get(args.run_id))
        else:
            runs = store.all()
            if not runs:
                raise ValueError("No captures saved yet. Save a raw run before exporting.")
            content = export(runs, cast(ExportFormat, args.format))
        _write_export(Path(args.output), content)


def _write_export(output: Path, content: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="") as file:
        file.write(content)
    print(f"Exported to {output.resolve()}; existing files are never overwritten.")
