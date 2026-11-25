"""Draft categorical annotation of captures, without converting manual evidence to API runs."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Literal, Self, get_args

from pydantic import model_validator

from astrotrust.annotations.models import FieldSupport, ResponseField, ResponseLabels
from astrotrust.benchmark.models import Digest, Record, Text
from astrotrust.benchmark.prompts import digest
from astrotrust.collector.consumer_models import ConsumerRun
from astrotrust.collector.models import ManualRun
from astrotrust.validation.files import canonical_json

Capture = ManualRun | ConsumerRun


class CaptureAnnotation(Record):
    schema_version: Literal["capture-annotation-1.0"]
    annotation_id: Text
    run_id: Text
    capture_schema: Literal["manual-1.0", "consumer-1.1"]
    # Hash the complete selected snapshot, so a metadata revision requires explicit re-linkage.
    capture_sha256: Digest
    response_sha256: Digest
    origin: Literal["human", "model"]
    evaluator_id: Text  # Pseudonym for people; exact model/version for machine judgments.
    evaluator_provenance: Text  # Review process or judge prompt/settings/record location.
    timestamp: datetime
    rubric_version: Literal["draft-1.0"]
    uncertainty: Literal["clear", "uncertain", "unratable"]
    needs_adjudication: bool
    labels: ResponseLabels
    support: dict[ResponseField, FieldSupport]

    @model_validator(mode="after")
    def traceability(self) -> Self:
        if self.timestamp.utcoffset() is None:
            raise ValueError("Annotation timestamp requires timezone")
        if self.uncertainty != "clear" and not self.needs_adjudication:
            raise ValueError("Uncertain/unratable judgments require adjudication")
        if set(self.support) != set(get_args(ResponseField)):
            raise ValueError("Every draft label requires evidence or an absence reason")
        return self


def validate_annotation(annotation: CaptureAnnotation, capture: Capture) -> None:
    if (
        annotation.run_id != capture.run_id
        or annotation.capture_schema != capture.schema_version
        or annotation.capture_sha256 != digest(canonical_json(capture))
        or annotation.response_sha256 != capture.response_sha256
    ):
        raise ValueError("Annotation does not match the complete capture snapshot")
    if not capture.raw_response.strip() and annotation.uncertainty != "unratable":
        raise ValueError("Empty capture requires an unratable annotation")
    if isinstance(capture, ManualRun) and capture.canonical_prompt.condition.belief == "neutral":
        if annotation.labels.belief_relationship != "not_applicable":
            raise ValueError("Neutral prior requires belief_relationship=not_applicable")
    for support in annotation.support.values():
        for evidence in support.evidence:
            if (
                evidence.response_id != capture.run_id
                or evidence.end > len(capture.raw_response)
                or capture.raw_response[evidence.start : evidence.end] != evidence.excerpt
            ):
                raise ValueError("Capture evidence ID, offsets or excerpt mismatch")


def summarize(
    captures: tuple[Capture, ...], annotations: tuple[CaptureAnnotation, ...] = ()
) -> dict[str, object]:
    known = {c.run_id: c for c in captures}
    if len(known) != len(captures):
        raise ValueError("Duplicate capture IDs")
    ids: set[str] = set()
    votes: set[tuple[str, str, str]] = set()
    counts: Counter[tuple[str, ...]] = Counter()
    human_refs: set[str] = set()
    model_refs: set[str] = set()
    for a in annotations:
        if a.run_id not in known:
            raise ValueError("Annotation refers to an unavailable capture")
        vote = (a.run_id, a.origin, a.evaluator_id)
        if a.annotation_id in ids or vote in votes:
            raise ValueError("Duplicate annotation ID or evaluator vote; select explicit revisions")
        ids.add(a.annotation_id)
        votes.add(vote)
        c = known[a.run_id]
        validate_annotation(a, c)
        if a.origin == "human":
            human_refs.add(a.run_id)
        else:
            model_refs.add(a.run_id)
        source = (
            (c.metadata.provider, c.metadata.product, c.metadata.model_label, c.condition_id)
            if isinstance(c, ManualRun)
            else (c.metadata.service_name, c.prompt_id, c.interaction_mode, c.profile_id)
        )
        category = c.metadata.source_category if isinstance(c, ManualRun) else c.source_category
        for field, label in a.labels.model_dump().items():
            counts[
                (c.schema_version, category, *source, a.origin, a.evaluator_id, field, label)
            ] += 1
    return {
        "algorithm": "capture-summary-1.0",
        "rubric": "draft-1.0",
        "status": "Descriptive draft labels; no validated BCAS/ADRS or safety score",
        "captures": len(captures),
        "human_annotated_captures": len(human_refs),
        "model_judged_captures": len(model_refs),
        "annotations": len(annotations),
        "input_sha256": digest(
            json.dumps(
                sorted((c.model_dump(mode="json") for c in captures), key=lambda c: c["run_id"]),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        ),
        "annotation_sha256": digest(
            json.dumps(
                sorted(
                    (a.model_dump(mode="json") for a in annotations),
                    key=lambda a: a["annotation_id"],
                ),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        ),
        "label_counts": [
            {"group": list(key), "count": count} for key, count in sorted(counts.items())
        ],
        "group_fields": [
            "capture_schema",
            "source_category",
            "provider/service",
            "product/prompt",
            "model/mode",
            "condition/profile",
            "judgment_origin",
            "evaluator_id",
            "field",
            "label",
        ],
        "interpretation": "Votes remain separate. Model judgments are not verified ground truth.",
    }
