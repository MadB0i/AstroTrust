"""Portable complete records and verbatim reports; no interpretation or response scoring."""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Literal

from astrotrust.collector.models import STATUS, ManualRun
from astrotrust.collector.store import identity

ExportFormat = Literal["jsonl", "csv", "markdown"]
CSV_ENCODING = "apostrophe-escaped-risky-v1"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key in imported JSON")
        result[key] = value
    return result


def parse_json(content: str) -> object:
    def invalid_constant(value: str) -> object:
        raise ValueError("Nonstandard JSON number is unsupported")

    return json.loads(content, object_pairs_hook=_unique_keys, parse_constant=invalid_constant)


def validate_collection(runs: tuple[ManualRun, ...]) -> None:
    if len({r.run_id for r in runs}) != len(runs):
        raise ValueError("Duplicate run ID in import")
    if len({identity(r) for r in runs}) != len(runs):
        raise ValueError("Duplicate capture identity in import")


def jsonl(runs: tuple[ManualRun, ...]) -> str:
    validate_collection(runs)
    return "".join(_json(run.model_dump(mode="json")) + "\n" for run in runs)


def load_jsonl(content: str) -> tuple[ManualRun, ...]:
    runs = []
    # JSONL separates records on LF, not Unicode NEL/paragraph/line separator characters.
    for line_number, line in enumerate(content.split("\n"), 1):
        if not line.strip():
            continue
        try:
            runs.append(ManualRun.model_validate(parse_json(line)))
        except ValueError as exc:
            raise ValueError(f"JSONL line {line_number}: {exc}") from exc
    result = tuple(runs)
    validate_collection(result)
    return result


def _csv_safe(value: str) -> str:
    # CSV quoting does not disable spreadsheet formulas. Escape only risky strings,
    # including leading apostrophes, with an explicit reversible format marker.
    risky = value.lstrip(" \t\r\n\ufeff").startswith(("=", "+", "-", "@", "'"))
    return "'" + value if risky or value.startswith(("\t", "\r", "'")) else value


def _csv_row(run: ManualRun) -> dict[str, str]:
    prompt = run.canonical_prompt
    row = {
        "csv_text_encoding": CSV_ENCODING,
        "run_id": run.run_id,
        "research_status": run.research_status,
        "scenario_id": prompt.scenario_id,
        "scenario_revision": str(prompt.scenario_revision),
        "condition_id": run.condition_id,
        "language": prompt.condition.language,
        "prompt_version": prompt.template_version,
        "prompt_sha256": run.prompt_sha256,
        "response_sha256": run.response_sha256,
        "exact_prompt": run.exact_prompt,
        "raw_response": run.raw_response,
        "response_length_characters": str(len(run.raw_response)),
        "collector_version": run.collector_version,
        "instrument_version": run.instrument_version,
        # Full source record enables lossless round-trip of nested provenance/history.
        "record_json": _json(run.model_dump(mode="json")),
    }
    for key, value in run.metadata.model_dump(mode="json").items():
        row[f"metadata_{key}"] = value if isinstance(value, str) else _json(value)
    return {key: _csv_safe(value) for key, value in row.items()}


def csv_export(runs: tuple[ManualRun, ...]) -> str:
    validate_collection(runs)
    output = io.StringIO(newline="")
    if not runs:
        return '"research_status"\r\n' + '"' + STATUS + '"\r\n'
    writer = csv.DictWriter(output, fieldnames=list(_csv_row(runs[0])), quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(_csv_row(run) for run in runs)
    return output.getvalue()


def load_csv(content: str) -> tuple[ManualRun, ...]:
    reader = csv.DictReader(io.StringIO(content, newline=""))
    rows = list(reader)
    if reader.fieldnames == ["research_status"] and rows == [{"research_status": STATUS}]:
        return ()
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)) or not {
        "record_json",
        "csv_text_encoding",
        "raw_response",
    } <= set(fields):
        raise ValueError("Not a collector CSV header; use the complete exported CSV or JSONL")
    runs = []
    for row in rows:
        if row.get("csv_text_encoding") != CSV_ENCODING:
            raise ValueError("Unknown CSV encoding; import collector CSV or JSONL")
        run = ManualRun.model_validate(parse_json(row.get("record_json", "")))
        if row != _csv_row(run):
            raise ValueError(
                "CSV flattened fields differ from complete record; use metadata revision"
            )
        runs.append(run)
    result = tuple(runs)
    validate_collection(result)
    return result


def fence(text: str, language: str = "text") -> str:
    """Collision-safe fence; framing newline is separate from the exact saved string."""
    longest = max((len(m[0]) for m in re.finditer(r"`+", text)), default=0)
    marker = "`" * max(3, longest + 1)
    return f"{marker}{language}\n{text}\n{marker}\n"


def _heading(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>()#!|])", r"\\\1", text).replace("\n", " ").replace("\r", " ")


def run_report(run: ManualRun, *, level: int = 2) -> str:
    metadata = run.metadata
    p = run.canonical_prompt
    title = "#" * level
    return (
        f"{title} Run {metadata.run_number} — {run.run_id}\n\n"
        f"Scenario: {p.scenario_id}, revision {p.scenario_revision}  \n"
        f"Condition: {run.condition_id}  \n"
        f"Provider / product / exact UI model label: {_heading(metadata.provider)} / "
        f"{_heading(metadata.product)} / {_heading(metadata.model_label)}\n\n"
        "**Capture metadata (all fields)**\n\n"
        + fence(json.dumps(metadata.model_dump(mode="json"), ensure_ascii=False, indent=2), "json")
        + "\n**Exact submitted prompt**\n\n"
        + fence(run.exact_prompt)
        + "\n**Exact raw response**\n\n"
        + fence(run.raw_response)
        + "\n**Integrity and complete provenance**\n\n"
        + "The following complete record preserves exact strings, canonical prompt, hashes, "
        "deviation, versions and metadata revision history. Fenced blocks add a framing newline; "
        "use the complete record or JSONL for byte-exact reconstruction.\n\n"
        + fence(_json(run.model_dump(mode="json")), "json")
    )


def markdown_report(runs: tuple[ManualRun, ...]) -> str:
    validate_collection(runs)
    output = "# AstroTrust Exploratory Pilot\n\n" + STATUS + "\n\n"
    if not runs:
        return output + "No captures saved.\n"
    previous: tuple[str, str, str, str] | None = None
    for run in sorted(
        runs,
        key=lambda r: (
            r.metadata.provider,
            r.metadata.model_label,
            r.canonical_prompt.scenario_id,
            r.condition_id,
            r.metadata.run_number,
            r.run_id,
        ),
    ):
        group = (
            run.metadata.provider,
            run.metadata.model_label,
            run.canonical_prompt.scenario_id,
            run.condition_id,
        )
        for index, value in enumerate(group):
            if previous is None or group[: index + 1] != previous[: index + 1]:
                output += "#" * (index + 2) + " " + _heading(value) + "\n\n"
        output += run_report(run, level=6) + "\n"
        previous = group
    return output


def single_report(run: ManualRun) -> str:
    return "# AstroTrust Manual Capture Report\n\n" + STATUS + "\n\n" + run_report(run)


def export(runs: tuple[ManualRun, ...], format: ExportFormat) -> str:
    return {"jsonl": jsonl, "csv": csv_export, "markdown": markdown_report}[format](runs)


def load_export(path: Path) -> tuple[ManualRun, ...]:
    if path.suffix not in {".jsonl", ".csv"}:
        raise ValueError("Import/validate accepts .jsonl or collector .csv; Markdown is a report")
    with path.open(encoding="utf-8", newline="") as file:
        content = file.read()
    return load_csv(content) if path.suffix == ".csv" else load_jsonl(content)
