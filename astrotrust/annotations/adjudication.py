"""Separate final decisions linked to immutable-by-convention source snapshots."""

from datetime import datetime
from typing import Literal, Self

from pydantic import model_validator

from astrotrust.annotations.models import Annotation, ResponseAnnotation
from astrotrust.benchmark.models import Digest, Record, Text
from astrotrust.benchmark.prompts import digest
from astrotrust.validation.files import canonical_json


def unit_identity(annotation: Annotation) -> tuple[object, ...]:
    if isinstance(annotation, ResponseAnnotation):
        return (annotation.kind, canonical_json(annotation.target))
    return (
        annotation.kind,
        tuple(sorted(canonical_json(ref) for ref in annotation.targets)),
    )


class AdjudicationRecord(Record):
    kind: Literal["adjudication"]
    schema_version: Literal["1.0"]
    purpose: Literal["research", "synthetic_example"]
    adjudication_id: Text
    source_sha256: dict[Text, Digest]  # Keys are the original annotation IDs.
    final_annotation: Annotation
    decision_reason: Text
    timestamp: datetime
    rubric_clarification: Text | None
    proposed_rubric_version: Text | None

    @model_validator(mode="after")
    def separate_decision(self) -> Self:
        if len(self.source_sha256) < 2:
            raise ValueError("adjudication requires at least two original annotation IDs")
        if self.final_annotation.annotation_id in self.source_sha256:
            raise ValueError("final annotation ID must differ from original IDs")
        if self.timestamp.utcoffset() is None:
            raise ValueError("adjudication timestamp must include a timezone")
        if bool(self.rubric_clarification) != bool(self.proposed_rubric_version):
            raise ValueError("rubric clarification requires a proposed version, and conversely")
        if self.proposed_rubric_version == self.final_annotation.rubric_version:
            raise ValueError("rubric clarification must propose a new version")
        return self


def adjudicate(
    originals: tuple[Annotation, ...],
    final: Annotation,
    *,
    adjudication_id: str,
    reason: str,
    timestamp: datetime,
    rubric_clarification: str | None = None,
    proposed_rubric_version: str | None = None,
    purpose: Literal["research", "synthetic_example"] = "research",
) -> AdjudicationRecord:
    if len(originals) < 2 or len({a.annotation_id for a in originals}) != len(originals):
        raise ValueError("at least two distinct original annotations are required")
    if len({a.annotator_id for a in originals}) != len(originals):
        raise ValueError("original annotations must come from independent raters")
    if any(unit_identity(a) != unit_identity(final) for a in originals):
        raise ValueError("adjudication must preserve the original annotation unit")
    if any(a.rubric_version != final.rubric_version for a in originals):
        raise ValueError("adjudication cannot silently mix rubric versions")
    return AdjudicationRecord(
        kind="adjudication",
        schema_version="1.0",
        purpose=purpose,
        adjudication_id=adjudication_id,
        source_sha256={a.annotation_id: digest(canonical_json(a)) for a in originals},
        final_annotation=final,
        decision_reason=reason,
        timestamp=timestamp,
        rubric_clarification=rubric_clarification,
        proposed_rubric_version=proposed_rubric_version,
    )


def verify_originals(record: AdjudicationRecord, batch: tuple[Annotation, ...]) -> None:
    lookup = {a.annotation_id: a for a in batch}
    originals = []
    for annotation_id, expected in record.source_sha256.items():
        original = lookup.get(annotation_id)
        if original is None or digest(canonical_json(original)) != expected:
            raise ValueError("original annotation missing or changed since adjudication")
        originals.append(original)
    # Recheck unit identity, independent raters and version agreement against sources.
    adjudicate(
        tuple(originals),
        record.final_annotation,
        adjudication_id=record.adjudication_id,
        reason=record.decision_reason,
        timestamp=record.timestamp,
        rubric_clarification=record.rubric_clarification,
        proposed_rubric_version=record.proposed_rubric_version,
        purpose=record.purpose,
    )
