import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from astrotrust.__main__ import main
from astrotrust.benchmark.models import Condition, Scenario
from astrotrust.validation.files import (
    BenchmarkValidationError,
    canonical_json,
    load_scenarios,
    pii_warnings,
    read_json,
)


def test_valid_fixture_coverage(scenarios: tuple[Scenario, ...]) -> None:
    assert len(scenarios) == 8
    assert {s.domain for s in scenarios} == {
        "career",
        "education",
        "relationships",
        "finance",
        "health",
        "relocation",
        "family",
        "everyday",
    }
    assert {s.stakes for s in scenarios} == {"low", "medium", "high"}
    assert all(s.expected_languages == ("en", "hi", "as") for s in scenarios)
    assert all(s.provenance.review_status == "development_draft" for s in scenarios)
    assert all(not pii_warnings(s) for s in scenarios)


def test_language_registry_matches_fixture_targets(scenarios: tuple[Scenario, ...]) -> None:
    registry = json.loads(Path("benchmark/languages/registry.json").read_text(encoding="utf-8"))
    assert registry["schema_version"] == "1.0"
    assert set(registry["languages"]) == set(scenarios[0].expected_languages)
    assert registry["languages"]["hi"]["status"] == "translation_pending"
    assert registry["languages"]["as"]["status"] == "translation_pending"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("domain", "politics", "domain"),
        ("stakes", "safe", "stakes"),
        ("schema_version", "2.0", "schema_version"),
        ("expected_languages", ["en", "bn"], "expected_languages"),
        ("revision", 0, "revision"),
        ("scenario_id", "person name", "scenario_id"),
    ],
)
def test_invalid_fields(
    scenarios: tuple[Scenario, ...], field: str, value: object, error: str
) -> None:
    data = scenarios[0].model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError, match=error):
        Scenario.model_validate(data)


def test_missing_required_and_unknown_fields(scenarios: tuple[Scenario, ...]) -> None:
    data = scenarios[0].model_dump(mode="json")
    del data["profile"]
    with pytest.raises(ValidationError, match="profile"):
        Scenario.model_validate(data)
    data = scenarios[0].model_dump(mode="json")
    data["expected_prediction"] = "forbidden"
    with pytest.raises(ValidationError, match="Extra inputs"):
        Scenario.model_validate(data)


@pytest.mark.parametrize("levels", [["neutral"], ["neutral", "neutral"], ["strong_belief"]])
def test_malformed_conditions(scenarios: tuple[Scenario, ...], levels: list[str]) -> None:
    data = scenarios[0].model_dump(mode="json")
    data["experimental_variables"]["belief"] = levels
    with pytest.raises(ValidationError, match="belief"):
        Scenario.model_validate(data)


@pytest.mark.parametrize(
    "data",
    [{"belief": "certain"}, {"language": "bn"}, {"emotion": "happy"}, {"confidence": "high"}],
)
def test_unsupported_condition(data: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        Condition.model_validate(data)


def test_incomplete_frames(scenarios: tuple[Scenario, ...]) -> None:
    data = scenarios[0].model_dump(mode="json")
    del data["language_variants"]["en"]["belief_frames"]["neutral"]
    with pytest.raises(ValidationError, match="belief_frames"):
        Scenario.model_validate(data)


def test_duplicate_ids(scenarios: tuple[Scenario, ...], tmp_path: Path) -> None:
    for name in ("one.json", "two.json"):
        (tmp_path / name).write_text(canonical_json(scenarios[0]), encoding="utf-8")
    with pytest.raises(BenchmarkValidationError, match="duplicate scenario ID"):
        load_scenarios(tmp_path)


def test_empty_bad_json_and_duplicate_keys(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkValidationError, match="no scenario JSON"):
        load_scenarios(tmp_path)
    file = tmp_path / "bad.json"
    file.write_text('{"schema_version":', encoding="utf-8")
    with pytest.raises(BenchmarkValidationError, match="bad.json"):
        load_scenarios(tmp_path)
    file.write_text('{"domain":"career","domain":"health"}', encoding="utf-8")
    with pytest.raises(BenchmarkValidationError, match="duplicate JSON key"):
        read_json(file)
    file.write_text('{"value": NaN}', encoding="utf-8")
    with pytest.raises(BenchmarkValidationError, match="nonstandard JSON"):
        read_json(file)


def test_privacy_warning_does_not_echo_match(scenarios: tuple[Scenario, ...]) -> None:
    data = scenarios[0].model_dump(mode="json")
    data["researcher_notes"] = "Test pattern only: example@example.invalid"
    warnings = pii_warnings(Scenario.model_validate(data))
    assert len(warnings) == 1
    assert "email-like" in warnings[0]
    assert "example@example.invalid" not in warnings[0]


def test_canonical_roundtrip(scenarios: tuple[Scenario, ...]) -> None:
    for scenario in scenarios:
        content = canonical_json(scenario)
        assert canonical_json(Scenario.model_validate_json(content)) == content
        reversed_data: dict[str, Any] = dict(reversed(list(json.loads(content).items())))
        assert canonical_json(Scenario.model_validate(reversed_data)) == content


def test_cli_success_and_error(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["validate", "benchmark/scenarios"]) == 0
    assert "24 development prompts" in capsys.readouterr().out
    assert main(["validate", str(tmp_path)]) == 1
    assert "ERROR:" in capsys.readouterr().err
    assert main(["inspect", "atb-career-001"]) == 0
    assert '"messages_sha256"' in capsys.readouterr().out
    assert main(["inspect", "atb-career-999"]) == 1
    assert "unknown scenario ID" in capsys.readouterr().err
