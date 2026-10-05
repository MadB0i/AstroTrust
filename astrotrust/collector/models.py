"""Typed manual frontend provenance, separate from controlled API ModelRun records."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from astrotrust.annotations.models import condition_id
from astrotrust.benchmark.models import Condition, Digest, Prompt, Record, Text
from astrotrust.benchmark.prompts import digest

YesNoUnknown = Literal["yes", "no", "unknown"]
Partial = Literal["yes", "no", "partially"]
RunID = Annotated[str, Field(pattern=r"^manual-[0-9a-f]{32}$")]

STATUS = (
    "Exploratory Pilot — NOT FROZEN BENCHMARK DATA. Prompts/instrument remain under "
    "construction review. BCAS and ADRS are not yet validated. No scientific conclusions "
    "should be drawn from these pilot runs."
)


class ServiceMetadata(Record):
    """Future observed claims, never an inference about a service's backend."""

    service_name: Text
    ai_generated_claimed: YesNoUnknown
    human_involvement_claimed: YesNoUnknown
    cost: Literal["free", "paid", "unknown"]
    response_type: Literal["chat", "generated_report", "horoscope", "unknown"]
    personal_fields_requested: tuple[Text, ...]  # Field NAMES only; never personal values.


class CaptureMetadata(Record):
    source_category: Literal["general_purpose_llm", "consumer_astrology_service"]
    service: ServiceMetadata | None
    provider: Literal["OpenAI", "Anthropic", "Google", "Other"]
    product: Text
    model_label: Text  # Exact observed UI label; not an authoritative model identifier.
    access_method: Literal["web", "mobile_app", "desktop_app", "other"]
    account_tier: Literal["free", "paid", "unknown"] | None
    special_mode: Literal["default", "thinking", "research", "other", "none", "unknown"]
    special_mode_detail: Text | None
    browsing: Literal["off", "on", "unknown", "automatic"]
    memory: Literal["off", "on", "unknown"]
    fresh_conversation: Literal["yes", "no"]
    run_number: Annotated[int, Field(strict=True, ge=1, le=3)]
    timestamp: Text
    timezone: Text
    response_complete: YesNoUnknown
    asked_more_information: Partial
    refusal_or_avoidance: Partial
    web_sources: YesNoUnknown
    visibly_truncated: YesNoUnknown
    capture_note: str | None

    @model_validator(mode="after")
    def provenance(self) -> Self:
        try:
            timestamp = datetime.fromisoformat(self.timestamp)
        except ValueError as exc:
            raise ValueError("timestamp must be ISO-8601") from exc
        if timestamp.utcoffset() is None:
            raise ValueError("timestamp must contain a timezone offset")
        if self.source_category == "general_purpose_llm" and self.service is not None:
            raise ValueError("service metadata requires consumer_astrology_service")
        if self.special_mode == "other" and not self.special_mode_detail:
            raise ValueError("other special mode requires special_mode_detail")
        if self.special_mode != "other" and self.special_mode_detail is not None:
            raise ValueError("special_mode_detail applies only to other mode")
        return self


class MetadataRevision(Record):
    revision: Annotated[int, Field(strict=True, ge=1)]
    recorded_at: datetime
    reason: Text
    metadata: CaptureMetadata

    @model_validator(mode="after")
    def aware(self) -> Self:
        if self.recorded_at.utcoffset() is None:
            raise ValueError("revision recorded_at must include a timezone")
        return self


class ManualRun(Record):
    kind: Literal["manual_frontend_run"]
    schema_version: Literal["manual-1.0"]
    study_phase: Literal["exploratory_pilot"]
    research_status: Text = Field(json_schema_extra={"const": STATUS})
    run_id: RunID
    canonical_prompt: Prompt
    condition_id: Text
    canonical_text: Text
    canonical_prompt_sha256: Digest
    exact_prompt: Text
    prompt_sha256: Digest
    protocol_deviation: Text | None
    raw_response: str  # Empty or whitespace captures can document collection failures.
    response_sha256: Digest
    metadata: CaptureMetadata
    history: Annotated[tuple[MetadataRevision, ...], Field(min_length=1)]
    collector_version: Text
    software_version: Text
    instrument_version: Text
    code_revision: Text | None
    code_worktree_dirty: Annotated[bool, Field(strict=True)] | None

    @model_validator(mode="after")
    def integrity(self) -> Self:
        if self.research_status != STATUS:
            raise ValueError("manual runs must retain the complete exploratory status statement")
        prompt = self.canonical_prompt
        if len(prompt.messages) != 1 or prompt.messages[0].role != "user":
            raise ValueError("manual collector supports one user message only")
        if self.condition_id != condition_id(prompt.condition):
            raise ValueError("condition_id does not match canonical condition")
        if self.canonical_text != prompt.messages[0].content:
            raise ValueError("canonical_text must match canonical prompt message exactly")
        for text, hashed, name in (
            (self.canonical_text, self.canonical_prompt_sha256, "canonical prompt"),
            (self.exact_prompt, self.prompt_sha256, "submitted prompt"),
            (self.raw_response, self.response_sha256, "response"),
        ):
            if digest(text) != hashed:
                raise ValueError(f"{name} SHA-256 mismatch")
        if (self.exact_prompt != self.canonical_text) != (self.protocol_deviation is not None):
            raise ValueError("modified prompt requires a deviation reason; exact prompt has none")
        if [h.revision for h in self.history] != list(range(1, len(self.history) + 1)):
            raise ValueError("metadata history must be contiguous from revision 1")
        if self.metadata != self.history[-1].metadata:
            raise ValueError("metadata must match last revision")
        times = [h.recorded_at for h in self.history]
        if times != sorted(times):
            raise ValueError("metadata history timestamps must be ordered")
        return self


class CaptureRequest(Record):
    scenario_id: Text
    condition: Condition
    canonical_prompt_sha256: Digest
    exact_prompt: Text
    protocol_deviation: Text | None
    raw_response: str
    metadata: CaptureMetadata


class CorrectionRequest(Record):
    expected_revision: Annotated[int, Field(strict=True, ge=1)]
    reason: Text
    metadata: CaptureMetadata
