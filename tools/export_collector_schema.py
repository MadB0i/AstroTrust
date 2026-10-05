"""Export manual collector schema separately, without changing instrument-v0.1 records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic.json_schema import models_json_schema

from astrotrust.collector.models import CaptureRequest, CorrectionRequest, ManualRun

DESTINATION = Path("benchmark/schema/manual-run.schema.json")


def schema_text() -> str:
    refs, schema = models_json_schema(
        [
            (ManualRun, "validation"),
            (CaptureRequest, "validation"),
            (CorrectionRequest, "validation"),
        ],
        title="AstroTrust exploratory manual capture, manual-1.0",
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
        if not DESTINATION.exists() or DESTINATION.read_text("utf-8") != content:
            print(f"Collector schema drift: regenerate {DESTINATION}")
            return 1
        print("Manual collector JSON Schema matches Python records.")
    else:
        DESTINATION.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
