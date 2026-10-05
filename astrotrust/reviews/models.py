"""Public packets, private mapping keys and unfinished/completed construction reviews."""

from datetime import datetime
from typing import Annotated, Literal, Self, get_args

from pydantic import Field, model_validator

from astrotrust.benchmark.models import Condition, Digest, Record, ScenarioID, Stakes, Text

ReviewID = Annotated[str, Field(pattern=r"^r-[0-9a-f]{12}$")]
VariantID = Annotated[str, Field(pattern=r"^v-[0-9a-f]{12}$")]
ReviewJudgment = Literal["pending", "acceptable", "issue", "unclear", "not_applicable"]
ReviewField = Literal[
    "understandable",
    "plausible",
    "belief_isolation",
    "fact_control",
    "nonleading",
    "emotional_isolation",
    "personalization_isolation",
    "stakes_plausibility",
    "cultural_respect",
    "translation_clarity",
    "stereotype_avoidance",
    "high_stakes_handling",
]


class ReviewVariant(Record):
    variant_id: VariantID
    text: Text


class WordingSet(Record):
    set_id: Text
    options: Annotated[tuple[ReviewVariant, ...], Field(min_length=2, max_length=2)]


class ReviewItem(Record):
    review_id: ReviewID
    prompts: Annotated[tuple[ReviewVariant, ...], Field(min_length=3, max_length=3)]
    additional_wording_sets: Annotated[tuple[WordingSet, ...], Field(min_length=2, max_length=2)]


class ReviewPacket(Record):
    schema_version: Literal["1.0"]
    packet_id: Text
    purpose: Literal["scenario_construction_review"]
    language: Literal["en"]
    items: Annotated[tuple[ReviewItem, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        review_ids = [i.review_id for i in self.items]
        variants = [
            v.variant_id
            for i in self.items
            for v in (*i.prompts, *(v for s in i.additional_wording_sets for v in s.options))
        ]
        if len(set(review_ids)) != len(review_ids) or len(set(variants)) != len(variants):
            raise ValueError("review and variant IDs must be unique in a packet")
        return self


class MappingEntry(Record):
    review_id: ReviewID
    scenario_id: ScenarioID
    kind: Literal["prompt", "wording_option"]
    condition: Condition | None
    condition_id: Text | None
    wording_dimension: Literal["emotion", "personalization"] | None
    level: Text | None
    text_sha256: Digest


class ResearcherKey(Record):
    schema_version: Literal["1.0"]
    packet_id: Text
    packet_sha256: Digest
    exporter_version: Literal["review-export-1"]
    seed: Annotated[int, Field(strict=True, ge=0, le=2**64 - 1)]
    template_snapshot: dict[str, object]
    scenario_snapshots: dict[ScenarioID, dict[str, object]]
    entries: dict[VariantID, MappingEntry]


class ConstructionReview(Record):
    packet_id: Text
    review_id: ReviewID
    reviewer_id: Annotated[str, Field(pattern=r"^reviewer-[a-z0-9][a-z0-9-]{1,31}$")] | None
    status: Literal["pending", "completed", "skipped"]
    judgments: dict[ReviewField, ReviewJudgment]
    suggested_stakes: Stakes | Literal["unclear"] | None
    notes: dict[ReviewField, Text]
    needs_adjudication: bool
    timestamp: datetime | None

    @model_validator(mode="after")
    def submission_state(self) -> Self:
        if set(self.judgments) != set(get_args(ReviewField)):
            raise ValueError("construction review must include every review question")
        if self.timestamp is not None and self.timestamp.utcoffset() is None:
            raise ValueError("review timestamp must include a timezone")
        if self.status in {"completed", "skipped"} and (
            self.reviewer_id is None or self.timestamp is None
        ):
            raise ValueError("completed/skipped review requires pseudonym and timestamp")
        if self.status == "completed":
            if self.reviewer_id is None or self.timestamp is None or self.suggested_stakes is None:
                raise ValueError(
                    "completed review requires pseudonym, timestamp and stakes judgment"
                )
            if "pending" in self.judgments.values():
                raise ValueError("completed review cannot retain pending judgments")
            flagged = {k for k, v in self.judgments.items() if v in {"issue", "unclear"}}
            if flagged and (not self.needs_adjudication or not flagged <= set(self.notes)):
                raise ValueError("issue/unclear judgments require notes and adjudication flag")
            if self.suggested_stakes == "unclear" and (
                not self.needs_adjudication or "stakes_plausibility" not in self.notes
            ):
                raise ValueError("unclear stakes requires a note and adjudication flag")
        if self.status == "skipped" and not self.notes:
            raise ValueError("skipped review requires a reason in notes")
        return self


class ReviewFeedback(Record):
    schema_version: Literal["1.0"]
    kind: Literal["construction_reviews"]
    purpose: Literal["template", "synthetic_example", "private_review"]
    reviews: Annotated[tuple[ConstructionReview, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_reviews(self) -> Self:
        keys = [(r.packet_id, r.review_id, r.reviewer_id) for r in self.reviews]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate construction reviews for a reviewer/item")
        if self.purpose == "private_review" and any(r.status == "pending" for r in self.reviews):
            raise ValueError("submitted private reviews must be completed or explicitly skipped")
        if self.purpose == "template" and any(r.status != "pending" for r in self.reviews):
            raise ValueError("template purpose cannot contain completed human feedback")
        return self
