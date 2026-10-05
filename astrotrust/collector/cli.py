"""Small launcher and portable import/export commands."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from astrotrust.collector.exports import ExportFormat, export, load_export, single_report
from astrotrust.collector.server import serve
from astrotrust.collector.store import RunStore


def command(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    database = root / args.database
    action = args.collect_action or "serve"
    if action == "serve":
        serve(root, database, args.port)
    elif action == "validate":
        runs = load_export(args.path)
        print(f"Validated {len(runs)} exploratory captures, hashes and metadata histories.")
        print("Integrity validation does not authenticate frontend origin or scientific validity.")
    elif action == "import":
        runs = load_export(args.path)
        RunStore(database).insert_many(runs)
        print(f"Imported {len(runs)} captures atomically; no existing records overwritten.")
    else:
        if not database.is_file():
            raise ValueError("Local database does not exist; start the collector first")
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
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="") as file:
            file.write(content)
        print(f"Exported to {output.resolve()}; existing files are never overwritten.")
