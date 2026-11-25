"""Separate consumer exports; complete named provenance and reversible CSV encoding."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from astrotrust.collector.consumer_models import ConsumerRun
from astrotrust.collector.consumer_store import identity
from astrotrust.collector.exports import (
    CSV_ENCODING,
    ExportFormat,
    _csv_safe,
    _json,
    fence,
    parse_json,
)
from astrotrust.collector.models import STATUS


def validate_collection(runs: tuple[ConsumerRun, ...]) -> None:
    if len({r.run_id for r in runs}) != len(runs):
        raise ValueError("Duplicate consumer run ID in import")
    if len({identity(r) for r in runs}) != len(runs):
        raise ValueError("Duplicate consumer capture identity in import")


def jsonl(runs: tuple[ConsumerRun, ...]) -> str:
    validate_collection(runs)
    return "".join(_json(r.model_dump(mode="json")) + "\n" for r in runs)


def load_jsonl(content: str) -> tuple[ConsumerRun, ...]:
    runs = []
    for number, line in enumerate(content.split("\n"), 1):
        if not line.strip():
            continue
        try:
            runs.append(ConsumerRun.model_validate(parse_json(line)))
        except ValueError as exc:
            raise ValueError(f"Consumer JSONL line {number}: {exc}") from exc
    result = tuple(runs)
    validate_collection(result)
    return result


def csv_row(run: ConsumerRun) -> dict[str, str]:
    row = {
        "csv_text_encoding": CSV_ENCODING,
        "source_category": run.source_category,
        "run_id": run.run_id,
        "prompt_id": run.prompt_id,
        "registry_version": run.registry_version,
        "exact_prompt": run.exact_prompt,
        "prompt_sha256": run.prompt_sha256,
        "raw_response": run.raw_response,
        "response_sha256": run.response_sha256,
        "profile_id": run.profile_id,
        "profile_version": "null" if run.profile_version is None else run.profile_version,
        "profile_sha256": "null" if run.profile_sha256 is None else run.profile_sha256,
        "profile_fields_submitted": _json(run.profile_fields_submitted),
        "profile_snapshot": _json(
            None if run.profile_snapshot is None else run.profile_snapshot.model_dump(mode="json")
        ),
        "gender_required": _json(run.gender_required),
        "interaction_mode": run.interaction_mode,
        "interaction_record_type": run.interaction_record_type,
        "exact_interaction": "null" if run.exact_interaction is None else run.exact_interaction,
        "interaction_sha256": "null" if run.interaction_sha256 is None else run.interaction_sha256,
        "record_json": _json(run.model_dump(mode="json")),
    }
    for key, value in run.metadata.model_dump(mode="json").items():
        row[f"metadata_{key}"] = value if isinstance(value, str) else _json(value)
    return {key: _csv_safe(value) for key, value in row.items()}


def csv_export(runs: tuple[ConsumerRun, ...]) -> str:
    validate_collection(runs)
    if not runs:
        return '"research_status"\r\n' + '"' + STATUS + '"\r\n'
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(csv_row(runs[0])), quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(csv_row(run) for run in runs)
    return output.getvalue()


def load_csv(content: str) -> tuple[ConsumerRun, ...]:
    reader = csv.DictReader(io.StringIO(content, newline=""))
    rows = list(reader)
    if reader.fieldnames == ["research_status"] and rows == [{"research_status": STATUS}]:
        return ()
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not {"record_json", "csv_text_encoding"} <= set(fields):
        raise ValueError("Not a consumer collector CSV header")
    runs = []
    for row in rows:
        if row.get("csv_text_encoding") != CSV_ENCODING:
            raise ValueError("Unknown consumer CSV encoding")
        run = ConsumerRun.model_validate(parse_json(row.get("record_json", "")))
        if row != csv_row(run):
            raise ValueError("CSV flattened fields differ from complete consumer record")
        runs.append(run)
    result = tuple(runs)
    validate_collection(result)
    return result


def single_report(run: ConsumerRun) -> str:
    return (
        "# AstroTrust Consumer Astrology Service Capture\n\n"
        + STATUS
        + "\n\n"
        + f"Prompt: {run.prompt_id} · Run {run.metadata.run_number} · {run.run_id}\n\n"
        + "## Observed service and capture metadata\n\n"
        + fence(_json(run.metadata.model_dump(mode="json")), "json")
        + "\n## Fixed synthetic input provenance\n\n"
        + "FICTIONAL / SYNTHETIC RESEARCH INPUT — NOT PARTICIPANT DATA. "
        "Only profile_fields_submitted were supplied; the full registry snapshot is retained "
        "for reproducibility. Requested fields remain separate in capture metadata.\n\n"
        + fence(
            _json(
                {
                    "profile_id": run.profile_id,
                    "profile_version": run.profile_version,
                    "profile_sha256": run.profile_sha256,
                    "profile_fields_submitted": run.profile_fields_submitted,
                    "gender_required": run.gender_required,
                    "profile_snapshot": (
                        None
                        if run.profile_snapshot is None
                        else run.profile_snapshot.model_dump(mode="json")
                    ),
                }
            ),
            "json",
        )
        + "\n## Exact initial submitted prompt\n\n"
        + fence(run.exact_prompt)
        + "\n## Interaction / protocol provenance\n\n"
        + f"Interaction mode: {run.interaction_mode}; "
        + f"record type: {run.interaction_record_type}.\n\n"
        + (
            (
                "The final response follows the recorded additional interaction; "
                "do not attribute it to the initial prompt alone.\n\n"
                if run.interaction_mode == "multi_step"
                else "The complete interaction history is unknown; this record documents available "
                "evidence and omissions. Please do not attribute the final response to the "
                "initial prompt alone.\n\n"
            )
            + fence(run.exact_interaction)
            if run.exact_interaction is not None
            else (
                "Researcher explicitly reported the initial prompt plus the listed fixed synthetic "
                "profile inputs, with no additional exchange.\n\n"
                if run.interaction_mode == "prompt_and_fixed_profile_only"
                else "Researcher explicitly reported the initial prompt only, "
                "without profile inputs.\n\n"
            )
        )
        + "\n## Exact raw response\n\n"
        + fence(run.raw_response)
        + "\n## Complete provenance and integrity\n\n"
        + "Fenced text adds a framing newline. Reconstruct exact strings from this complete "
        "record or authoritative JSONL. Service names are retained without anonymization.\n\n"
        + fence(_json(run.model_dump(mode="json")), "json")
    )


def markdown_report(runs: tuple[ConsumerRun, ...]) -> str:
    validate_collection(runs)
    if not runs:
        return "# AstroTrust Consumer Pilot\n\n" + STATUS + "\n\nNo captures saved.\n"
    return "\n".join(
        single_report(r)
        for r in sorted(
            runs,
            key=lambda r: (r.metadata.service_name, r.prompt_id, r.metadata.run_number, r.run_id),
        )
    )


def export(runs: tuple[ConsumerRun, ...], format: ExportFormat) -> str:
    return {"jsonl": jsonl, "csv": csv_export, "markdown": markdown_report}[format](runs)


def load_export(path: Path) -> tuple[ConsumerRun, ...]:
    if path.suffix not in {".jsonl", ".csv"}:
        raise ValueError("Import/validate accepts consumer .jsonl or .csv; Markdown is a report")
    with path.open(encoding="utf-8", newline="") as file:
        content = file.read()
    return load_csv(content) if path.suffix == ".csv" else load_jsonl(content)
