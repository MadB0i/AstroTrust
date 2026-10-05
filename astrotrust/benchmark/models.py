"""Versioned research records. JSON Schema is generated from these models."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from string import Formatter
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
ScenarioID = Annotated[str, Field(pattern=r"^atb-[a-z]+-[0-9]{3}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Language = Literal["en", "hi", "as"]
Domain = Literal[
    "career", "education", "relationships", "finance", "health", "relocation", "family", "everyday"
]
Stakes = Literal["low", "medium", "high"]
Belief = Literal["neutral", "positive_expectation", "negative_expectation"]
Emotion = Literal["neutral", "distressed"]
Personalization = Literal["generic", "explicitly_personalized"]
BELIEFS: tuple[Belief, ...] = ("neutral", "positive_expectation", "negative_expectation")


class Record(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False,
        hide_input_in_errors=True,
    )


class Condition(Record):
    belief: Belief = "neutral"
    emotion: Emotion = "neutral"
    personalization: Personalization = "generic"
    language: Language = "en"


class ExperimentalVariables(Record):
    belief: tuple[Belief, ...]
    emotion: tuple[Emotion, ...]
    personalization: tuple[Personalization, ...]

    @model_validator(mode="after")
    def coverage(self) -> Self:
        for name, required in (
            ("belief", set(BELIEFS)),
            ("emotion", {"neutral", "distressed"}),
            ("personalization", {"generic", "explicitly_personalized"}),
        ):
            values = getattr(self, name)
            if len(values) != len(set(values)) or set(values) != required:
                raise ValueError(f"{name} must contain every supported level exactly once")
        return self


class SyntheticProfile(Record):
    synthetic: Literal[True]
    profile_id: Annotated[str, Field(pattern=r"^fictional-[0-9]{3}$")]
    age_band: Text
    country_context: Literal["India"]
    context: Text


class BirthContext(Record):
    synthetic: Literal[True]
    description: Text
    # Coarse or invented context only; no real person's exact birth identifiers.
    rationale: Text


class Review(Record):
    status: Literal["draft", "human_reviewed"]
    reviewer_id: Text | None = None
    review_record: Text | None = None

    @model_validator(mode="after")
    def review_evidence(self) -> Self:
        if self.status == "human_reviewed" and not (self.reviewer_id and self.review_record):
            raise ValueError("human_reviewed requires reviewer_id and review_record")
        return self


class LocalizedText(Record):
    revision: Annotated[int, Field(strict=True, ge=1)]
    review: Review
    profile_text: Text
    situation: Text
    baseline_question: Text
    belief_frames: dict[Belief, Text]
    emotional_frames: dict[Emotion, Text]
    personalization_frames: dict[Personalization, Text]

    @model_validator(mode="after")
    def complete_frames(self) -> Self:
        for name, required in (
            ("belief_frames", set(BELIEFS)),
            ("emotional_frames", {"neutral", "distressed"}),
            ("personalization_frames", {"generic", "explicitly_personalized"}),
        ):
            if set(getattr(self, name)) != required:
                raise ValueError(f"{name} must contain every supported level")
        return self


class Provenance(Record):
    kind: Literal["synthetic_development_fixture"]
    creation_method: Text
    source: Literal["invented; no participant data"]
    review_status: Literal["development_draft"]


class Scenario(Record):
    schema_version: Literal["1.0"]
    scenario_id: ScenarioID
    revision: Annotated[int, Field(strict=True, ge=1)]
    title: Text
    domain: Domain
    stakes: Stakes
    stakes_rationale: Text
    profile: SyntheticProfile
    birth_context: BirthContext | None
    experimental_variables: ExperimentalVariables
    expected_languages: tuple[Language, ...]
    language_variants: dict[Language, LocalizedText]
    researcher_notes: Text
    provenance: Provenance

    @model_validator(mode="after")
    def consistency(self) -> Self:
        if not self.scenario_id.startswith(f"atb-{self.domain}-"):
            raise ValueError("scenario_id domain segment must match domain")
        if not self.expected_languages or len(set(self.expected_languages)) != len(
            self.expected_languages
        ):
            raise ValueError("expected_languages must be nonempty and unique")
        if "en" not in self.language_variants:
            raise ValueError("an English development variant is required")
        if not set(self.language_variants) <= set(self.expected_languages):
            raise ValueError("language_variants must be a subset of expected_languages")
        return self


class PromptTemplate(Record):
    template_id: Literal["atb-controlled"]
    version: Text
    # Only these fields may be interpolated; checked by this model.
    format: Text

    @model_validator(mode="after")
    def controlled_slots(self) -> Self:
        expected = {"profile", "situation", "belief", "emotion", "personalization", "question"}
        fields = []
        for _, field, spec, conversion in Formatter().parse(self.format):
            if field is not None:
                if spec or conversion:
                    raise ValueError(
                        "template conversions and format specifications are unsupported"
                    )
                fields.append(field)
        if set(fields) != expected or len(fields) != len(expected):
            raise ValueError("template must contain each controlled field exactly once")
        return self


class Message(Record):
    role: Literal["system", "user", "assistant"]
    content: Text


def messages_digest(messages: tuple[Message, ...]) -> str:
    content = json.dumps(
        [message.model_dump(mode="json") for message in messages],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class Prompt(Record):
    schema_version: Literal["1.0"]
    scenario_id: ScenarioID
    scenario_revision: Annotated[int, Field(strict=True, ge=1)]
    scenario_sha256: Digest
    template_id: Text
    template_version: Text
    template_sha256: Digest
    language_revision: Annotated[int, Field(strict=True, ge=1)]
    review_status: Literal["draft", "human_reviewed"]
    condition: Condition
    messages: Annotated[tuple[Message, ...], Field(min_length=1)]
    messages_sha256: Digest

    @model_validator(mode="after")
    def message_integrity(self) -> Self:
        if messages_digest(self.messages) != self.messages_sha256:
            raise ValueError("messages_sha256 does not match saved messages")
        return self


class GenerationSettings(Record):
    temperature: Annotated[float, Field(ge=0)] | None
    top_p: Annotated[float, Field(ge=0, le=1)] | None
    max_output_tokens: Annotated[int, Field(strict=True, gt=0)] | None
    seed: Annotated[int, Field(strict=True)] | None
    provider_parameters: dict[str, str | int | float | bool | None]
    # Null means unknown/unsupported, never an assumed provider default.


class ModelRun(Record):
    schema_version: Literal["1.0"]
    run_id: Text
    response_id: Text
    prompt: Prompt
    provider: Text
    requested_model: Text
    returned_model_identifier: Text | None
    model_version: Text | None
    generation_settings: GenerationSettings
    run_number: Annotated[int, Field(strict=True, ge=1)]
    timestamp: datetime
    evaluator_version: Text
    status: Literal["completed", "failed"]
    raw_response: str | None  # Preserve empty/whitespace completions, too.
    error: Text | None
    code_revision: Text
    environment_record: Text

    @model_validator(mode="after")
    def outcome(self) -> Self:
        if self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        if self.status == "completed" and (self.raw_response is None or self.error is not None):
            raise ValueError("completed run requires raw_response and no error")
        if self.status == "failed" and (self.error is None or self.raw_response is not None):
            raise ValueError("failed run requires error and no raw_response")
        return self
