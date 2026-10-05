"""Offline validation with source paths and actionable errors."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ValidationError

from astrotrust.benchmark.models import Scenario


class BenchmarkValidationError(ValueError):
    """Invalid benchmark input; safe to show in developer CLI output."""


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BenchmarkValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    raise BenchmarkValidationError(f"nonstandard JSON numeric constant: {value}")


def read_json(path: Path) -> object:
    try:
        return cast(
            object,
            json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_unique_keys,
                parse_constant=_invalid_constant,
            ),
        )
    except (OSError, ValueError) as exc:
        raise BenchmarkValidationError(f"{path}: {exc}") from exc


def canonical_json(record: BaseModel) -> str:
    """Stable UTF-8 JSON representation used for content hashes and snapshots."""
    return (
        json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )


def load_scenarios(path: Path) -> tuple[Scenario, ...]:
    files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    if not files:
        raise BenchmarkValidationError(f"{path}: no scenario JSON files found")
    scenarios: list[Scenario] = []
    seen: dict[str, Path] = {}
    for file in files:
        try:
            scenario = Scenario.model_validate(read_json(file))
        except ValidationError as exc:
            raise BenchmarkValidationError(f"{file}: {exc}") from exc
        if scenario.scenario_id in seen:
            raise BenchmarkValidationError(
                f"{file}: duplicate scenario ID {scenario.scenario_id}; "
                f"first seen in {seen[scenario.scenario_id]}"
            )
        seen[scenario.scenario_id] = file
        scenarios.append(scenario)
    return tuple(sorted(scenarios, key=lambda item: item.scenario_id))


def pii_warnings(scenario: Scenario) -> tuple[str, ...]:
    """Heuristic warnings, never a privacy guarantee or a detector of real identities.

    Do not echo matched values into logs. Dates and names cannot reliably be
    distinguished from invented data; manual review remains mandatory.
    """
    content = canonical_json(scenario)
    patterns = {
        "email-like text": r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
        "phone-like text": r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{9}(?!\d)",
        "12-digit identifier-like text": r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)",
        "precise date-like text": r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b",
    }
    return tuple(
        f"{scenario.scenario_id}: manual privacy review needed ({name})"
        for name, pattern in patterns.items()
        if re.search(pattern, content)
    )
