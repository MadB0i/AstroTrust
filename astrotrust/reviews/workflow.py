"""Preserve returned submissions and summarize construction judgments, never model results."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, get_args

from astrotrust import INSTRUMENT_VERSION
from astrotrust.benchmark.models import Digest, PromptTemplate, Record, Scenario, ScenarioID, Text
from astrotrust.benchmark.prompts import digest
from astrotrust.reviews.export import build_packet, validate_feedback, validate_mapping
from astrotrust.reviews.forms import parse_manual_form
from astrotrust.reviews.models import ResearcherKey, ReviewFeedback, ReviewField, ReviewPacket
from astrotrust.validation.files import canonical_json, read_json


class ReviewImportReceipt(Record):
    schema_version: Literal["1.0"]
    kind: Literal["construction_review_import"]
    instrument_version: Literal["instrument-v0.1"]
    importer_version: Literal["review-import-1"]
    original_sha256: Digest
    feedback_sha256: Digest
    packet_sha256: Digest
    original_format: Literal["markdown", "json"]
    imported_at: datetime


class ReviewerCounts(Record):
    completed: int
    skipped: int
    judgments: dict[ReviewField, dict[str, int]]


class ConstructionDisagreement(Record):
    scenario_id: ScenarioID
    field: ReviewField | Literal["suggested_stakes", "status"]
    values: dict[Text, Text]


class ConstructionSummary(Record):
    schema_version: Literal["1.0"]
    kind: Literal["construction_review_summary"]
    instrument_version: Literal["instrument-v0.1"]
    summary_version: Literal["review-summary-1"]
    source_sha256: Digest
    feedback_sha256: dict[Text, Digest]
    mapping_sha256: dict[Text, Digest]
    reviewers: dict[Text, ReviewerCounts]
    disagreements: tuple[ConstructionDisagreement, ...]
    flagged_scenarios: tuple[ScenarioID, ...]


def validate_submission(feedback: ReviewFeedback, packet: ReviewPacket) -> str:
    validate_feedback(feedback, packet)
    if feedback.purpose != "private_review":
        raise ValueError("returned submissions must have purpose=private_review")
    if {r.review_id for r in feedback.reviews} != {i.review_id for i in packet.items}:
        raise ValueError("submission must cover every packet item, including explicit skips")
    reviewers = {r.reviewer_id for r in feedback.reviews}
    if len(reviewers) != 1 or None in reviewers or len(feedback.reviews) != len(packet.items):
        raise ValueError("one complete submission per pseudonymous reviewer is required")
    reviewer = next(iter(reviewers))
    assert reviewer is not None
    return reviewer


def import_submission(source: Path, packet: ReviewPacket, output: Path) -> ReviewImportReceipt:
    source = source.resolve()
    output = output.resolve()
    if output.exists() or source.is_relative_to(output):
        raise ValueError("import output must be a new directory outside the original submission")
    raw = source.read_bytes()
    text = raw.decode("utf-8-sig")
    if source.suffix.lower() == ".json":
        feedback = ReviewFeedback.model_validate(read_json(source))
        original_format: Literal["markdown", "json"] = "json"
    elif source.suffix.lower() in {".md", ".txt"}:
        feedback = parse_manual_form(text)
        original_format = "markdown"
    else:
        raise ValueError("import accepts the supplied Markdown/plain-text form or JSON")
    validate_submission(feedback, packet)
    normalized = canonical_json(feedback)
    receipt = ReviewImportReceipt(
        schema_version="1.0",
        kind="construction_review_import",
        instrument_version=INSTRUMENT_VERSION,
        importer_version="review-import-1",
        original_sha256=hashlib.sha256(raw).hexdigest(),
        feedback_sha256=digest(normalized),
        packet_sha256=digest(canonical_json(packet)),
        original_format=original_format,
        imported_at=datetime.now(UTC),
    )
    output.mkdir(parents=True)
    # Validate first; copy the exact bytes, including BOM/newlines, without altering source.
    with (output / ("original.json" if original_format == "json" else "original.md")).open(
        "xb"
    ) as file:
        file.write(raw)
    for filename, content in (
        ("feedback.json", normalized),
        ("receipt.json", canonical_json(receipt)),
    ):
        with (output / filename).open("x", encoding="utf-8", newline="\n") as file:
            file.write(content)
    return receipt


def summarize_construction(
    submissions: tuple[tuple[ReviewFeedback, ResearcherKey], ...],
) -> ConstructionSummary:
    if len(submissions) != 2:
        raise ValueError("construction comparison currently requires exactly two submissions")
    source_hashes = set()
    batches = {}
    keys = {}
    tables = {}
    for feedback, key in submissions:
        scenarios = tuple(Scenario.model_validate(s) for s in key.scenario_snapshots.values())
        packet, _, _ = build_packet(
            scenarios, PromptTemplate.model_validate(key.template_snapshot), seed=key.seed
        )
        validate_mapping(packet, key)
        reviewer = validate_submission(feedback, packet)
        if reviewer in tables:
            raise ValueError("select two distinct reviewer pseudonyms")
        source_hashes.add(
            digest(
                json.dumps(
                    {"scenarios": key.scenario_snapshots, "template": key.template_snapshot},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        )
        lookup = {entry.review_id: entry.scenario_id for entry in key.entries.values()}
        tables[reviewer] = {lookup[r.review_id]: r for r in feedback.reviews}
        batches[reviewer] = digest(canonical_json(feedback))
        keys[reviewer] = digest(canonical_json(key))
    if len(source_hashes) != 1:
        raise ValueError("reviewers evaluated different scenario/template source snapshots")
    counts = {}
    flagged: set[str] = set()
    for reviewer, table in tables.items():
        completed = [r for r in table.values() if r.status == "completed"]
        counts[reviewer] = ReviewerCounts(
            completed=len(completed),
            skipped=len(table) - len(completed),
            judgments={
                field: {
                    label: sum(r.judgments[field] == label for r in completed)
                    for label in ("acceptable", "issue", "unclear", "not_applicable")
                }
                for field in get_args(ReviewField)
            },
        )
        flagged.update(
            sid for sid, r in table.items() if r.needs_adjudication or r.status == "skipped"
        )
    raters = sorted(tables)
    differences = []
    for sid in sorted(tables[raters[0]]):
        first, second = (tables[r][sid] for r in raters)
        if first.status != second.status:
            differences.append(
                ConstructionDisagreement(
                    scenario_id=sid,
                    field="status",
                    values={raters[0]: first.status, raters[1]: second.status},
                )
            )
        if first.status != "completed" or second.status != "completed":
            continue  # Never count unassessed/skipped judgments as comparable labels.
        for field in get_args(ReviewField):
            if first.judgments[field] != second.judgments[field]:
                differences.append(
                    ConstructionDisagreement(
                        scenario_id=sid,
                        field=field,
                        values={
                            raters[0]: first.judgments[field],
                            raters[1]: second.judgments[field],
                        },
                    )
                )
        if first.suggested_stakes != second.suggested_stakes:
            differences.append(
                ConstructionDisagreement(
                    scenario_id=sid,
                    field="suggested_stakes",
                    values={r: str(tables[r][sid].suggested_stakes) for r in raters},
                )
            )
    return ConstructionSummary(
        schema_version="1.0",
        kind="construction_review_summary",
        instrument_version=INSTRUMENT_VERSION,
        summary_version="review-summary-1",
        source_sha256=next(iter(source_hashes)),
        feedback_sha256=batches,
        mapping_sha256=keys,
        reviewers=counts,
        disagreements=tuple(differences),
        flagged_scenarios=tuple(sorted(flagged)),
    )
