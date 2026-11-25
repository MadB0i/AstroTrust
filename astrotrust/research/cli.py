"""Explicit research commands; read-only analysis and opt-in local inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from astrotrust.collector.consumer_store import DEFAULT_CONSUMER_DATABASE
from astrotrust.collector.exports import load_export
from astrotrust.collector.store import DEFAULT_DATABASE
from astrotrust.research.analysis import CaptureAnnotation, summarize
from astrotrust.research.inventory import research_status
from astrotrust.research.local import CommandAdapter, LocalAttempt, LocalRequest, save_inference
from astrotrust.research.splits import SplitManifest
from astrotrust.validation.files import read_json


def add_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    research = commands.add_parser(
        "research", help="AstroTrust 2.0 inventory, analysis and baselines"
    )
    actions = research.add_subparsers(dest="research_action", required=True)
    status = actions.add_parser("status", help="read-only local collection inventory")
    status.add_argument("--root", type=Path, default=Path("."))
    status.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    status.add_argument("--consumer-database", type=Path, default=DEFAULT_CONSUMER_DATABASE)
    analyze = actions.add_parser(
        "summarize", help="draft frontier label counts from preserved exports"
    )
    analyze.add_argument("captures", type=Path)
    analyze.add_argument("--annotations", type=Path, nargs="*", default=[])
    splits = actions.add_parser("validate-splits", help="reject cross-split identity/hash leakage")
    splits.add_argument("manifest", type=Path)
    local_validate = actions.add_parser(
        "validate-local", help="validate a saved local inference attempt"
    )
    local_validate.add_argument("path", type=Path)
    local = actions.add_parser(
        "infer-local", help="explicit inference through an installed adapter"
    )
    local.add_argument("request", type=Path)
    local.add_argument("--root", type=Path, default=Path("."))
    local.add_argument("--output", type=Path, required=True)
    local.add_argument("--timeout", type=float, default=120)
    local.add_argument("--adapter-command", nargs=argparse.REMAINDER, required=True)


def command(args: argparse.Namespace) -> None:
    action = args.research_action
    if action == "status":
        report = research_status(args.root / args.database, args.root / args.consumer_database)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        if report["frontier"]["state"] == "error" or report["consumer"]["state"] == "error":
            raise ValueError("A store could not be verified; inspect the status report")
    elif action == "summarize":
        captures = load_export(args.captures)
        annotations = tuple(
            CaptureAnnotation.model_validate(read_json(p)) for p in args.annotations
        )
        print(
            json.dumps(
                summarize(captures, annotations), ensure_ascii=False, sort_keys=True, indent=2
            )
        )
    elif action == "validate-splits":
        manifest = SplitManifest.model_validate(read_json(args.manifest))
        print(
            f"Validated {len(manifest.members)} split assignments; semantic grouping needs review."
        )
    elif action == "validate-local":
        attempt = LocalAttempt.model_validate(read_json(args.path))
        print(f"Validated local {attempt.run.status} attempt; exploratory, not a benchmark result.")
    else:
        request = LocalRequest.model_validate(read_json(args.request))
        attempt = save_inference(
            request,
            CommandAdapter(tuple(args.adapter_command), args.timeout),
            args.root.resolve(),
            args.output,
        )
        print(f"Saved {attempt.run.status} inference attempt to {args.output.resolve()}")
        if attempt.run.status == "failed":
            raise ValueError("Inference failed; the failure record was preserved")
