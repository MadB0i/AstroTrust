import json
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from astrotrust.__main__ import main
from astrotrust.benchmark.models import PromptTemplate, Scenario
from astrotrust.benchmark.prompts import belief_conditions, render_prompt
from astrotrust.reviews.export import (
    build_packet,
    export_packet,
    packet_markdown,
    validate_feedback,
    validate_mapping,
)
from astrotrust.reviews.models import ReviewFeedback, ReviewField, ReviewPacket
from astrotrust.validation.files import canonical_json, read_json


def test_deterministic_randomization_and_input_order(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
) -> None:
    first = build_packet(scenarios, template, seed=20261005)
    same = build_packet(tuple(reversed(scenarios)), template, seed=20261005)
    assert tuple(canonical_json(x) for x in first) == tuple(canonical_json(x) for x in same)
    different = build_packet(scenarios, template, seed=20261006)
    assert first[0] != different[0]
    assert [first[1].entries[i.prompts[0].variant_id].scenario_id for i in first[0].items] != [
        different[1].entries[i.prompts[0].variant_id].scenario_id for i in different[0].items
    ]
    orders = []
    for item in first[0].items:
        beliefs = []
        for variant in item.prompts:
            condition = first[1].entries[variant.variant_id].condition
            assert condition is not None
            beliefs.append(condition.belief)
        orders.append(tuple(beliefs))
    assert len(set(orders)) > 1
    assert any(
        order != ("neutral", "positive_expectation", "negative_expectation") for order in orders
    )
    validate_mapping(first[0], first[1])
    validate_mapping(different[0], different[1])


def test_all_variants_exactly_once_and_mapping_reconstructs(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
) -> None:
    packet, key, feedback = build_packet(scenarios, template, seed=20261005)
    expected = {
        render_prompt(s, template, c).messages[0].content
        for s in scenarios
        for c in belief_conditions()
    }
    actual = [v.text for item in packet.items for v in item.prompts]
    assert len(packet.items) == 8 and len(actual) == 24 and set(actual) == expected
    assert len(key.entries) == 56  # 24 full prompts + 32 existing wording options.
    assert len(feedback.reviews) == 8
    lookup = {s.scenario_id: s for s in scenarios}
    for item in packet.items:
        for variant in item.prompts:
            entry = key.entries[variant.variant_id]
            assert entry.kind == "prompt" and entry.condition is not None
            assert entry.review_id == item.review_id
            assert (
                variant.text
                == render_prompt(lookup[entry.scenario_id], template, entry.condition)
                .messages[0]
                .content
            )
        for wording in item.additional_wording_sets:
            for variant in wording.options:
                entry = key.entries[variant.variant_id]
                local = lookup[entry.scenario_id].language_variants["en"]
                frames = (
                    local.emotional_frames
                    if entry.wording_dimension == "emotion"
                    else local.personalization_frames
                )
                assert entry.level is not None
                generic_frames: dict[str, str] = {str(k): v for k, v in frames.items()}
                assert generic_frames[entry.level] == variant.text


def test_packet_blinds_internal_keys_and_has_only_pending_feedback(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
) -> None:
    packet, _, feedback = build_packet(scenarios, template, seed=20261005)
    serialized = canonical_json(packet) + canonical_json(feedback) + packet_markdown(packet)
    for forbidden in (
        "atb-",
        "scenario_id",
        "researcher_notes",
        "stakes_rationale",
        "positive_expectation",
        "negative_expectation",
        "BCAS",
        "ADRS",
        "provenance",
        "20261005",
    ):
        assert forbidden not in serialized
    assert set(packet.model_dump()) == {
        "schema_version",
        "packet_id",
        "purpose",
        "language",
        "items",
    }
    assert all(
        review.status == "pending" and review.reviewer_id is None for review in feedback.reviews
    )


def test_export_separation_no_overwrite_and_bytes(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
    tmp_path: Path,
) -> None:
    output = tmp_path / "reviewer"
    with pytest.raises(ValueError, match="outside"):
        export_packet(scenarios, template, seed=1, output=output, mapping=output / "mapping.json")
    export_packet(
        scenarios, template, seed=1, output=output, mapping=tmp_path / "researcher/key.json"
    )
    assert set(p.name for p in output.iterdir()) == {
        "packet.json",
        "packet.md",
        "feedback.template.json",
        "instructions.md",
        "feedback.md",
    }
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(ValueError, match="refuses existing"):
        export_packet(
            scenarios, template, seed=2, output=output, mapping=tmp_path / "other-key.json"
        )
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_feedback_completion_and_unknown_labels(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
) -> None:
    packet, _, feedback = build_packet(scenarios, template, seed=20261005)
    validate_feedback(feedback, packet)
    data = feedback.model_dump(mode="json")
    data["purpose"] = "synthetic_example"
    review = data["reviews"][0]
    review.update(
        status="completed",
        reviewer_id="reviewer-toy",
        timestamp="2026-10-05T00:00:00Z",
        suggested_stakes="medium",
        judgments={field: "acceptable" for field in get_args(ReviewField)},
    )
    validate_feedback(ReviewFeedback.model_validate(data), packet)
    review["judgments"]["belief_isolation"] = "issue"
    with pytest.raises(ValidationError, match="notes"):
        ReviewFeedback.model_validate(data)
    review["judgments"]["belief_isolation"] = "validated_truth"
    with pytest.raises(ValidationError):
        ReviewFeedback.model_validate(data)
    wrong = feedback.model_dump(mode="json")
    wrong["reviews"][0]["packet_id"] = "wrong-packet"
    with pytest.raises(ValueError, match="unknown packet"):
        validate_feedback(ReviewFeedback.model_validate(wrong), packet)


def test_committed_example_and_templates_are_current(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
) -> None:
    packet, key, feedback = build_packet(scenarios, template, seed=20261005)
    example = Path("reviews/examples/seed-20261005")
    for path, content in (
        (example / "reviewer/packet.json", canonical_json(packet)),
        (example / "reviewer/packet.md", packet_markdown(packet)),
        (example / "reviewer/feedback.template.json", canonical_json(feedback)),
        (example / "researcher-key.json", canonical_json(key)),
    ):
        assert path.read_text(encoding="utf-8") == content
    assert ReviewPacket.model_validate(read_json(example / "reviewer/packet.json")) == packet
    for name in ("response", "comparison"):
        form = json.loads(
            Path(f"reviews/templates/{name}.template.json").read_text(encoding="utf-8")
        )
        assert form["annotations"][0]["annotation_id"] is None


def test_review_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "reviewer"
    assert (
        main(
            [
                "review",
                "export",
                "benchmark/scenarios",
                "--seed",
                "20261005",
                "--output",
                str(output),
                "--mapping",
                str(tmp_path / "key.json"),
            ]
        )
        == 0
    )
    assert "8 English items" in capsys.readouterr().out
    assert (
        main(
            [
                "review",
                "validate",
                str(output / "feedback.template.json"),
                "--packet",
                str(output / "packet.json"),
            ]
        )
        == 0
    )
    assert "0 completed" in capsys.readouterr().out
