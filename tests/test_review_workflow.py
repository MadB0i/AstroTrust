"""Synthetic workflow sentinels only: no real reviews or scientific reports are produced."""

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from astrotrust.__main__ import main
from astrotrust.benchmark.models import PromptTemplate, Scenario
from astrotrust.benchmark.prompts import digest
from astrotrust.reviews.export import build_packet, reviewer_files
from astrotrust.reviews.forms import manual_form, parse_manual_form
from astrotrust.reviews.models import ReviewFeedback, ReviewField, ReviewPacket
from astrotrust.reviews.workflow import (
    ConstructionSummary,
    import_submission,
    summarize_construction,
    validate_submission,
)
from astrotrust.validation.files import canonical_json, read_json


def completed_toy(packet: ReviewPacket, reviewer: str) -> ReviewFeedback:
    # private_review is required to exercise production guards; these are test toys only.
    text = manual_form(packet)
    text = text.replace("reviewer_id: pending", f"reviewer_id: {reviewer}")
    text = text.replace("timestamp: pending", "timestamp: 2026-10-05T00:00:00Z")
    text = text.replace("status: pending", "status: completed")
    text = text.replace("suggested_stakes: pending", "suggested_stakes: medium")
    text = text.replace("| pending |", "| acceptable |")
    return parse_manual_form(text)


def test_pending_bundles_frozen_complete_and_blinded(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
) -> None:
    subprocess.run(
        [sys.executable, "tools/check_review_bundles.py"], check=True, capture_output=True
    )
    sequences = []
    for name, seed in (("reviewer-a", 20261007), ("reviewer-b", 20261008)):
        packet, key, feedback = build_packet(scenarios, template, seed=seed)
        files = reviewer_files(packet, feedback)
        assert len(packet.items) == 8
        assert sum(len(item.prompts) for item in packet.items) == 24
        sequences.append(
            tuple(key.entries[i.prompts[0].variant_id].scenario_id for i in packet.items)
        )
        combined = "\n".join(files.values())
        for hidden in (
            "atb-",
            "scenario_id",
            "stakes_rationale",
            "positive_expectation",
            "negative_expectation",
            "BCAS",
            "ADRS",
            "researcher_notes",
            str(seed),
        ):
            assert hidden not in combined
        assert "No Python or Git is needed" in files["instructions.md"]
        assert all(r.status == "pending" for r in feedback.reviews)
        assert {p.name for p in (Path("reviews/pending") / name).iterdir()} == set(files)
    assert sequences[0] != sequences[1]


def test_manual_import_preserves_bom_newlines_unicode_and_no_overwrite(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
    tmp_path: Path,
) -> None:
    packet, _, _ = build_packet(scenarios, template, seed=1)
    feedback = completed_toy(packet, "reviewer-toy-a")
    text = manual_form(packet)
    for old, new in (
        ("reviewer_id: pending", "reviewer_id: reviewer-toy-a"),
        ("timestamp: pending", "timestamp: 2026-10-05T00:00:00Z"),
        ("status: pending", "status: completed"),
        ("suggested_stakes: pending", "suggested_stakes: medium"),
        ("| pending |", "| acceptable |"),
    ):
        text = text.replace(old, new)
    text = text.replace(
        "| understandable | acceptable | |",
        r"| understandable | issue | TOY: café \| unclear referent |",
        1,
    )
    raw = b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8")
    source = tmp_path / "returned.md"
    source.write_bytes(raw)
    output = tmp_path / "imported"
    receipt = import_submission(source, packet, output)
    assert source.read_bytes() == (output / "original.md").read_bytes() == raw
    assert receipt.original_sha256 == hashlib.sha256(raw).hexdigest()
    parsed = ReviewFeedback.model_validate(read_json(output / "feedback.json"))
    assert parsed.reviews[0].notes["understandable"] == "TOY: café | unclear referent"
    assert parsed.reviews[0].needs_adjudication
    assert receipt.feedback_sha256 == digest(canonical_json(parsed))
    with pytest.raises(ValueError, match="new directory"):
        import_submission(source, packet, output)
    assert source.read_bytes() == raw
    json_source = tmp_path / "returned.json"
    json_source.write_text(canonical_json(feedback), encoding="utf-8")
    json_receipt = import_submission(json_source, packet, tmp_path / "json-import")
    assert json_receipt.original_format == "json"


def test_invalid_manual_submission_is_not_imported(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
    tmp_path: Path,
) -> None:
    packet, _, _ = build_packet(scenarios, template, seed=1)
    with pytest.raises(ValueError, match="timestamp"):
        parse_manual_form(manual_form(packet))
    source = tmp_path / "pending.md"
    source.write_text(manual_form(packet), encoding="utf-8")
    with pytest.raises(ValueError):
        import_submission(source, packet, tmp_path / "invalid-output")
    assert not (tmp_path / "invalid-output").exists()
    valid = completed_toy(packet, "reviewer-toy-a")
    partial = valid.model_dump(mode="json")
    partial["reviews"].pop()
    with pytest.raises(ValueError, match="every packet item"):
        validate_submission(ReviewFeedback.model_validate(partial), packet)
    raw = canonical_json(valid)
    source.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match="unrecognized"):
        parse_manual_form(raw)
    manual = manual_form(packet)
    for old, new in (
        ("reviewer_id: pending", "reviewer_id: reviewer-toy-a"),
        ("timestamp: pending", "timestamp: 2026-10-05T00:00:00Z"),
        ("status: pending", "status: completed"),
        ("suggested_stakes: pending", "suggested_stakes: medium"),
        ("| pending |", "| acceptable |"),
    ):
        manual = manual.replace(old, new)
    with pytest.raises(ValidationError):
        parse_manual_form(manual.replace("| acceptable |", "| scientifically_valid |", 1))
    row = "| understandable | acceptable | |"
    with pytest.raises(ValueError, match="duplicate feedback question"):
        parse_manual_form(manual.replace(row, row + "\n" + row, 1))


def test_summary_joins_blinded_ids_counts_flags_and_excludes_skips(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
) -> None:
    pa, ka, _ = build_packet(scenarios, template, seed=20261007)
    pb, kb, _ = build_packet(scenarios, template, seed=20261008)
    a = completed_toy(pa, "reviewer-toy-a")
    b_data = completed_toy(pb, "reviewer-toy-b").model_dump(mode="json")
    sid_by_review = {entry.review_id: entry.scenario_id for entry in kb.entries.values()}
    for review in b_data["reviews"]:
        if sid_by_review[review["review_id"]] == "atb-career-001":
            review["judgments"]["belief_isolation"] = "issue"
            review["notes"]["belief_isolation"] = "TOY TEST ONLY"
            review["needs_adjudication"] = True
            review["suggested_stakes"] = "high"
        if sid_by_review[review["review_id"]] == "atb-health-005":
            review["status"] = "skipped"
            review["judgments"] = {field: "pending" for field in get_args(ReviewField)}
            review["notes"] = {"understandable": "TOY skip"}
            review["suggested_stakes"] = None
    b = ReviewFeedback.model_validate(b_data)
    summary = summarize_construction(((a, ka), (b, kb)))
    assert summary.reviewers["reviewer-toy-b"].completed == 7
    assert summary.reviewers["reviewer-toy-b"].skipped == 1
    assert summary.reviewers["reviewer-toy-b"].judgments["belief_isolation"]["issue"] == 1
    assert {(d.scenario_id, d.field) for d in summary.disagreements} == {
        ("atb-career-001", "belief_isolation"),
        ("atb-career-001", "suggested_stakes"),
        ("atb-health-005", "status"),
    }
    assert summary.flagged_scenarios == ("atb-career-001", "atb-health-005")
    assert summary == summarize_construction(((b, kb), (a, ka)))


def test_summary_rejects_examples_same_reviewer_and_mismatched_sources(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
) -> None:
    pa, ka, example = build_packet(scenarios, template, seed=1)
    pb, kb, _ = build_packet(scenarios, template, seed=2)
    a, b = completed_toy(pa, "reviewer-toy-a"), completed_toy(pb, "reviewer-toy-b")
    with pytest.raises(ValueError, match="private_review"):
        summarize_construction(((example, ka), (b, kb)))
    with pytest.raises(ValueError, match="distinct reviewer"):
        summarize_construction(((a, ka), (completed_toy(pb, "reviewer-toy-a"), kb)))
    changed = scenarios[0].model_dump(mode="json")
    changed["revision"] += 1
    pc, kc, _ = build_packet((Scenario.model_validate(changed), *scenarios[1:]), template, seed=2)
    with pytest.raises(ValueError, match="different scenario"):
        summarize_construction(((a, ka), (completed_toy(pc, "reviewer-toy-b"), kc)))


def test_review_import_and_summary_cli(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    packets = []
    keys = []
    inputs = []
    for seed, reviewer in ((1, "reviewer-toy-a"), (2, "reviewer-toy-b")):
        packet, key, _ = build_packet(scenarios, template, seed=seed)
        packet_path = tmp_path / f"packet-{seed}.json"
        key_path = tmp_path / f"key-{seed}.json"
        input_path = tmp_path / f"feedback-{seed}.json"
        packet_path.write_text(canonical_json(packet), encoding="utf-8")
        key_path.write_text(canonical_json(key), encoding="utf-8")
        input_path.write_text(canonical_json(completed_toy(packet, reviewer)), encoding="utf-8")
        packets.append(packet_path)
        keys.append(key_path)
        inputs.append(input_path)
    assert (
        main(
            [
                "review",
                "import",
                str(inputs[0]),
                "--packet",
                str(packets[0]),
                "--output",
                str(tmp_path / "import"),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "review",
                "summarize",
                "--feedback",
                *(str(p) for p in inputs),
                "--mappings",
                *(str(p) for p in keys),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    report = ConstructionSummary.model_validate_json(captured.out)
    assert set(report.reviewers) == {"reviewer-toy-a", "reviewer-toy-b"}
    assert not report.disagreements
    assert "no model-annotation reliability" in captured.err
