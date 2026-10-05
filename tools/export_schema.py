"""Export portable JSON Schema from the typed records; --check detects drift."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic.json_schema import models_json_schema

from astrotrust.annotations.adjudication import AdjudicationRecord
from astrotrust.annotations.agreement import AgreementReport
from astrotrust.annotations.models import AnnotationBatch, ComparisonAnnotation, ResponseAnnotation
from astrotrust.benchmark.models import ModelRun, Prompt, Scenario
from astrotrust.metrics.provisional import ADRSObservation, BCASObservation
from astrotrust.reviews.models import ResearcherKey, ReviewFeedback, ReviewPacket
from astrotrust.reviews.workflow import ConstructionSummary, ReviewImportReceipt

DESTINATION = Path("benchmark/schema/records.schema.json")


def schema_text() -> str:
    refs, schema = models_json_schema(
        [
            (Scenario, "validation"),
            (Prompt, "validation"),
            (ModelRun, "validation"),
            (BCASObservation, "validation"),
            (ADRSObservation, "validation"),
            (ResponseAnnotation, "validation"),
            (ComparisonAnnotation, "validation"),
            (AnnotationBatch, "validation"),
            (AdjudicationRecord, "validation"),
            (AgreementReport, "validation"),
            (ReviewPacket, "validation"),
            (ResearcherKey, "validation"),
            (ReviewFeedback, "validation"),
            (ReviewImportReceipt, "validation"),
            (ConstructionSummary, "validation"),
        ],
        title="AstroTrust development records, schema 1.0",
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["oneOf"] = list(refs.values())
    return json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = schema_text()
    if args.check:
        if not DESTINATION.exists() or DESTINATION.read_text(encoding="utf-8") != content:
            print(f"Schema drift: regenerate {DESTINATION}")
            return 1
        print("JSON Schema matches Python records.")
    else:
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        DESTINATION.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
