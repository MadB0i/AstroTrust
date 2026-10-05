"""Small offline developer CLI; errors produce exit status 1."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from astrotrust.annotations.adjudication import AdjudicationRecord, adjudicate, verify_originals
from astrotrust.annotations.agreement import EXCLUDED, AgreementReport, batch_agreement
from astrotrust.annotations.files import load_batch, load_runs, validate_sources
from astrotrust.annotations.models import AnnotationBatch
from astrotrust.benchmark.models import Condition
from astrotrust.benchmark.prompts import belief_conditions, digest, load_template, render_prompt
from astrotrust.reviews.export import export_packet, validate_feedback
from astrotrust.reviews.models import ResearcherKey, ReviewFeedback, ReviewPacket
from astrotrust.reviews.workflow import (
    import_submission,
    summarize_construction,
    validate_submission,
)
from astrotrust.validation.files import canonical_json, load_scenarios, pii_warnings, read_json


def _review_command(args: argparse.Namespace) -> None:
    if args.action == "export":
        scenarios = load_scenarios(args.path)
        export_packet(
            scenarios,
            load_template(args.template),
            seed=args.seed,
            output=args.output,
            mapping=args.mapping,
        )
        print(f"Exported {len(scenarios)} English items; share only the reviewer directory.")
    elif args.action == "import":
        packet = ReviewPacket.model_validate(read_json(args.packet))
        import_submission(args.path, packet, args.output)
        print("Imported construction feedback; exact original bytes preserved separately.")
    elif args.action == "summarize":
        submissions = tuple(
            (
                ReviewFeedback.model_validate(read_json(feedback_path)),
                ResearcherKey.model_validate(read_json(mapping_path)),
            )
            for feedback_path, mapping_path in zip(args.feedback, args.mappings, strict=True)
        )
        print(canonical_json(summarize_construction(submissions)), end="")
        print(
            "Construction-review counts/disagreements only; no model-annotation reliability.",
            file=sys.stderr,
        )
    else:
        feedback = ReviewFeedback.model_validate(read_json(args.path))
        packet = ReviewPacket.model_validate(read_json(args.packet))
        validate_feedback(feedback, packet)
        if feedback.purpose == "private_review":
            validate_submission(feedback, packet)
        completed = sum(r.status == "completed" for r in feedback.reviews)
        print(f"Validated {feedback.purpose}: {completed} completed construction reviews.")


def _annotations_command(args: argparse.Namespace) -> None:
    if args.action == "adjudicate":
        original_batch = load_batch(args.originals)
        final_batch = load_batch(args.final)
        if original_batch.purpose != final_batch.purpose:
            raise ValueError("original and final batch purposes must match")
        if len(final_batch.annotations) != 1:
            raise ValueError("final batch must contain exactly one proposed final annotation")
        selected = tuple(a for a in original_batch.annotations if a.annotation_id in args.ids)
        if {a.annotation_id for a in selected} != set(args.ids):
            raise ValueError("unknown original annotation ID")
        record = adjudicate(
            selected,
            final_batch.annotations[0],
            adjudication_id=args.adjudication_id,
            reason=args.reason,
            timestamp=datetime.fromisoformat(args.timestamp),
            purpose=original_batch.purpose,
        )
        with args.output.open("x", encoding="utf-8", newline="\n") as file:
            file.write(canonical_json(record))
        print("Saved a separate adjudication record; original files were not modified.")
        return
    raw = read_json(args.path)
    if isinstance(raw, dict) and raw.get("kind") == "adjudication":
        if args.action != "validate":
            raise ValueError("agreement must use independent annotations, not adjudicated labels")
        record = AdjudicationRecord.model_validate(raw)
        if args.originals:
            verify_originals(record, load_batch(args.originals).annotations)
        batch = AnnotationBatch(
            kind="annotation_batch",
            schema_version="1.0",
            purpose=record.purpose,
            annotations=(record.final_annotation,),
        )
        print(
            "Adjudication structurally valid; originals "
            + ("verified." if args.originals else "unchecked (supply --originals).")
        )
    else:
        batch = AnnotationBatch.model_validate(raw)
    if args.runs:
        validate_sources(batch, load_runs(args.runs))
        print(
            "Run references, control metadata and evidence excerpts verified.",
            file=sys.stdout if args.action == "validate" else sys.stderr,
        )
    else:
        print(
            "Structural validation only; source runs/evidence unchecked (supply --runs).",
            file=sys.stdout if args.action == "validate" else sys.stderr,
        )
    if args.action == "validate":
        print(f"Validated {len(batch.annotations)} annotations; purpose={batch.purpose}.")
    else:
        result = batch_agreement(
            batch,
            kind=args.kind,
            field=args.field,
            raters=tuple(args.raters),
            weights=args.weights,
        )
        report = AgreementReport(
            schema_version="1.0",
            algorithm_version="agreement-1",
            input_sha256=digest(canonical_json(batch)),
            rubric_version="draft-1.0",
            annotation_level=args.kind,
            field=args.field,
            raters=tuple(args.raters),
            exclusion_policy=tuple(sorted(EXCLUDED)) + ("overall_unratable",),
            result=result,
        )
        print(canonical_json(report), end="")
        print(
            "Descriptive agreement only; no construct-validity or independence claim.",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AstroTrustBench offline development tools")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser(
        "validate", help="validate source scenarios and prompt structure"
    )
    validate.add_argument("path", type=Path)
    inspect = commands.add_parser(
        "inspect", help="print a scenario's controlled English belief trio"
    )
    inspect.add_argument("scenario_id")
    inspect.add_argument("--scenarios", type=Path, default=Path("benchmark/scenarios"))
    review = commands.add_parser("review", help="construction-review export/validation")
    review_actions = review.add_subparsers(dest="action", required=True)
    export = review_actions.add_parser("export")
    export.add_argument("path", type=Path)
    export.add_argument("--seed", type=int, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--mapping", type=Path, required=True)
    export.add_argument(
        "--template", type=Path, default=Path("benchmark/prompts/controlled-v1.json")
    )
    review_validate = review_actions.add_parser("validate")
    review_validate.add_argument("path", type=Path)
    review_validate.add_argument("--packet", type=Path, required=True)
    review_import = review_actions.add_parser(
        "import", help="preserve and import returned feedback"
    )
    review_import.add_argument("path", type=Path)
    review_import.add_argument("--packet", type=Path, required=True)
    review_import.add_argument("--output", type=Path, required=True)
    review_summary = review_actions.add_parser("summarize", help="compare two construction reviews")
    review_summary.add_argument("--feedback", nargs=2, type=Path, required=True)
    review_summary.add_argument("--mappings", nargs=2, type=Path, required=True)
    annotations = commands.add_parser("annotations", help="offline human annotation workflow")
    annotation_actions = annotations.add_subparsers(dest="action", required=True)
    ann_validate = annotation_actions.add_parser("validate")
    ann_agreement = annotation_actions.add_parser("agreement")
    for command in (ann_validate, ann_agreement):
        command.add_argument("path", type=Path)
        command.add_argument("--runs", type=Path)
    ann_validate.add_argument("--originals", type=Path)
    ann_agreement.add_argument("--kind", choices=("response", "comparison"), required=True)
    ann_agreement.add_argument("--field", required=True)
    ann_agreement.add_argument("--raters", nargs=2, required=True)
    ann_agreement.add_argument(
        "--weights", choices=("nominal", "linear", "quadratic"), default="nominal"
    )
    adjudication = annotation_actions.add_parser("adjudicate")
    adjudication.add_argument("originals", type=Path)
    adjudication.add_argument("final", type=Path)
    adjudication.add_argument("--ids", nargs="+", required=True)
    adjudication.add_argument("--adjudication-id", required=True)
    adjudication.add_argument("--reason", required=True)
    adjudication.add_argument("--timestamp", required=True)
    adjudication.add_argument("--output", type=Path, required=True)
    for command in (validate, inspect):
        command.add_argument(
            "--template", type=Path, default=Path("benchmark/prompts/controlled-v1.json")
        )
    args = parser.parse_args(argv)
    try:
        if args.command == "review":
            _review_command(args)
            return 0
        if args.command == "annotations":
            _annotations_command(args)
            return 0
        scenarios = load_scenarios(args.path if args.command == "validate" else args.scenarios)
        template = load_template(args.template)
        if args.command == "validate":
            count = 0
            for scenario in scenarios:
                for language in scenario.language_variants:
                    for condition in belief_conditions(Condition(language=language)):
                        render_prompt(scenario, template, condition)
                        count += 1
                for warning in pii_warnings(scenario):
                    print(f"WARNING: {warning}", file=sys.stderr)
            print(f"Validated {len(scenarios)} scenarios; rendered {count} development prompts.")
            print(
                "Development validation does not certify linguistic equivalence "
                "or research validity."
            )
        else:
            selected = next((s for s in scenarios if s.scenario_id == args.scenario_id), None)
            if selected is None:
                raise ValueError(f"unknown scenario ID: {args.scenario_id}")
            for condition in belief_conditions():
                print(canonical_json(render_prompt(selected, template, condition)), end="")
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
