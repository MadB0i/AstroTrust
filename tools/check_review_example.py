"""Check deterministic public example/blank forms; --write updates only these known assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import get_args

from astrotrust.annotations.models import ComparisonField, ResponseField
from astrotrust.benchmark.prompts import load_template
from astrotrust.reviews.export import build_packet, reviewer_files
from astrotrust.validation.files import canonical_json, load_scenarios

EXAMPLE = Path("reviews/examples/seed-20261005")


def blank_form(kind: str) -> str:
    fields = get_args(ResponseField if kind == "response" else ComparisonField)
    labels = {field: None for field in fields}
    support: dict[str, object] = {field: {"evidence": [], "reason": None} for field in fields}
    annotation: dict[str, object] = {
        "kind": kind,
        "schema_version": "1.0",
        "annotation_id": None,
        "annotator_id": None,
        "rubric_version": "draft-1.0",
        "timestamp": None,
        "annotation_uncertainty": None,
        "needs_adjudication": None,
        "rationale": None,
    }
    if kind == "response":
        annotation.update(target=None, labels=labels, support=support)
    else:
        annotation.update(
            targets=[],
            contrasts=[
                {"variant_response_id": None, "labels": labels, "support": support},
                {"variant_response_id": None, "labels": labels, "support": support},
            ],
        )
    return (
        json.dumps(
            {
                "kind": "annotation_batch",
                "schema_version": "1.0",
                "purpose": "research",
                "annotations": [annotation],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def expected_files() -> dict[Path, str]:
    packet, key, feedback = build_packet(
        load_scenarios(Path("benchmark/scenarios")),
        load_template(Path("benchmark/prompts/controlled-v1.json")),
        seed=20261005,
    )
    return {
        **{
            EXAMPLE / "reviewer" / name: content
            for name, content in reviewer_files(packet, feedback).items()
        },
        EXAMPLE / "researcher-key.json": canonical_json(key),
        Path("reviews/templates/response.template.json"): blank_form("response"),
        Path("reviews/templates/comparison.template.json"): blank_form("comparison"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    mismatches = []
    for path, content in expected_files().items():
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        elif not path.exists() or path.read_text(encoding="utf-8") != content:
            mismatches.append(str(path))
    if mismatches:
        print("Example/template drift: " + ", ".join(mismatches))
        return 1
    print("Review example and blank annotation forms match their deterministic sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
