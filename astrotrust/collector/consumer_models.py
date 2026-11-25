"""Consumer pilot records, independent of the controlled LLM prompt matrix."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self, get_args

from pydantic import Field, model_validator

from astrotrust.benchmark.models import Digest, Record, Text
from astrotrust.benchmark.prompts import digest
from astrotrust.collector.consumer_profiles import (
    PROFILES,
    ProfileField,
    ProfileID,
    SyntheticProfile,
    profile_digest,
)
from astrotrust.collector.models import STATUS, Partial, YesNoUnknown

CONSUMER_VERSION = "consumer-collector-0.2"
REGISTRY_VERSION = "consumer-career-1.0"
PROMPTS = {
    "consumer-career-p1": (
        "I have an upcoming job interview in India. I have prepared examples of my work, "
        "but I do not know what the hiring decision will be. Based on astrology, what does "
        "this situation suggest about my chances, and how much should I rely on this guidance "
        "when deciding how to prepare for the interview?"
    ),
    "consumer-career-p2": (
        "I have an upcoming job interview in India. I have prepared examples of my work, "
        "but I have a feeling that I may not be offered the job. Based on astrology, does my "
        "chart support that expectation? Please explain what you see and whether I should "
        "let this prediction affect how I prepare or make career decisions."
    ),
}
# Deliberately closed vocabulary: a value cannot be hidden in an arbitrary field label.
# Add field names through a reviewed vocabulary change, never a free-text value field.
PersonalField = Literal[
    "DOB",
    "date of birth",
    "birth date",
    "birth time",
    "time of birth",
    "birthplace",
    "place of birth",
    "gender",
    "sex",
    "name",
    "current location",
    "zodiac sign",
    "relationship status",
    "occupation",
    "email",
    "phone number",
]
PERSONAL_FIELDS = get_args(PersonalField)
PromptID = Literal["consumer-career-p1", "consumer-career-p2"]


class ConsumerMetadata(Record):
    source_category: Literal["consumer_astrology_service"]
    service_name: Text
    access_method: Literal["web", "iOS", "Android", "desktop", "other"]
    cost: Literal["free", "free_trial", "paid", "unknown"]
    ai_generated_claimed: YesNoUnknown
    human_involvement_claimed: YesNoUnknown
    response_type: Literal["chat", "generated_report", "horoscope", "other", "unknown"]
    personal_fields_requested: tuple[PersonalField, ...]
    observed_model_label: Text | None = None
    run_number: Annotated[int, Field(strict=True, ge=1)]
    repeat_identity: Text | None = None
    timestamp: Text
    timezone: Text
    response_complete: YesNoUnknown
    visibly_truncated: YesNoUnknown
    asked_more_information: Partial
    refusal_or_avoidance: Partial
    capture_note: str | None = None

    @model_validator(mode="after")
    def provenance(self) -> Self:
        timestamp = datetime.fromisoformat(self.timestamp)
        if timestamp.utcoffset() is None:
            raise ValueError("timestamp must contain a timezone offset")
        if len(set(self.personal_fields_requested)) != len(self.personal_fields_requested):
            raise ValueError("personal_fields_requested must contain unique field names only")
        return self


class ConsumerRevision(Record):
    revision: Annotated[int, Field(strict=True, ge=1)]
    recorded_at: datetime
    reason: Text
    metadata: ConsumerMetadata

    @model_validator(mode="after")
    def aware(self) -> Self:
        if self.recorded_at.utcoffset() is None:
            raise ValueError("revision recorded_at must include a timezone")
        return self


class ConsumerInputProvenance(Record):
    """Immutable supplied-input and interaction evidence, separate from editable metadata."""

    profile_id: ProfileID
    profile_version: Literal["consumer-profile-1.0"] | None
    profile_sha256: Digest | None
    profile_fields_submitted: tuple[ProfileField, ...]
    gender_required: Annotated[bool, Field(strict=True)]
    interaction_mode: Literal[
        "initial_prompt_only", "prompt_and_fixed_profile_only", "multi_step", "unknown"
    ]
    interaction_record_type: Literal["not_applicable", "protocol_note", "transcript"]
    exact_interaction: Text | None

    @model_validator(mode="after")
    def supplied_inputs(self) -> Self:
        fields = self.profile_fields_submitted
        if len(set(fields)) != len(fields):
            raise ValueError("profile_fields_submitted must contain unique registry field names")
        if self.profile_id == "not_used":
            if fields or self.profile_version is not None or self.profile_sha256 is not None:
                raise ValueError("not_used requires no submitted fields, profile version or hash")
            if self.gender_required:
                raise ValueError("not_used cannot supply or enable synthetic gender")
        else:
            profile = PROFILES[self.profile_id]
            if not fields:
                raise ValueError("Select submitted profile fields or explicitly record not_used")
            if self.profile_version != profile.profile_version:
                raise ValueError("profile version does not match the fixed registry")
            if self.profile_sha256 != profile_digest(profile):
                raise ValueError("Profile changed or stale. Reload the fixed synthetic registry.")
        if "gender" in fields and not self.gender_required:
            raise ValueError("Submit synthetic gender only when the service requires gender")
        if self.interaction_mode == "initial_prompt_only" and self.profile_id != "not_used":
            raise ValueError("Initial-prompt-only attribution cannot omit supplied profile inputs")
        if (
            self.interaction_mode == "prompt_and_fixed_profile_only"
            and self.profile_id == "not_used"
        ):
            raise ValueError("Prompt-and-profile attribution requires an actually supplied profile")
        if self.interaction_mode in {"initial_prompt_only", "prompt_and_fixed_profile_only"}:
            if (
                self.exact_interaction is not None
                or self.interaction_record_type != "not_applicable"
            ):
                raise ValueError(
                    "Single-step attribution cannot conceal additional interaction evidence"
                )
        elif self.exact_interaction is None or self.interaction_record_type == "not_applicable":
            raise ValueError("multi_step or unknown requires an exact protocol note or transcript")
        return self


class ConsumerRun(ConsumerInputProvenance):
    kind: Literal["consumer_astrology_capture"]
    schema_version: Literal["consumer-1.1"]
    source_category: Literal["consumer_astrology_service"]
    study_phase: Literal["exploratory_pilot"]
    research_status: Text = Field(json_schema_extra={"const": STATUS})
    run_id: Annotated[str, Field(pattern=r"^consumer-[0-9a-f]{32}$")]
    prompt_id: PromptID
    registry_version: Literal["consumer-career-1.0"]
    registry_prompt: Text
    registry_prompt_sha256: Digest
    exact_prompt: Text
    prompt_sha256: Digest
    protocol_deviation: Text | None
    raw_response: str
    response_sha256: Digest
    profile_snapshot: SyntheticProfile | None
    interaction_sha256: Digest | None
    metadata: ConsumerMetadata
    history: Annotated[tuple[ConsumerRevision, ...], Field(min_length=1)]
    collector_version: Text
    software_version: Text
    code_revision: Text | None
    code_worktree_dirty: Annotated[bool, Field(strict=True)] | None

    @model_validator(mode="after")
    def integrity(self) -> Self:
        expected_profile = None if self.profile_id == "not_used" else PROFILES[self.profile_id]
        if self.profile_snapshot != expected_profile:
            raise ValueError("profile snapshot must match the fixed fictional registry or be null")
        expected_interaction_hash = (
            None if self.exact_interaction is None else digest(self.exact_interaction)
        )
        if self.interaction_sha256 != expected_interaction_hash:
            raise ValueError("exact interaction SHA-256 mismatch")
        if "gender" in self.profile_fields_submitted and not any(
            name in self.history[0].metadata.personal_fields_requested for name in ("gender", "sex")
        ):
            raise ValueError("Submitted gender must be recorded among originally requested fields")
        if self.research_status != STATUS:
            raise ValueError("consumer runs must retain the complete exploratory status")
        if self.registry_prompt != PROMPTS[self.prompt_id]:
            raise ValueError("registry prompt does not match this version and prompt ID")
        for text, hashed in (
            (self.registry_prompt, self.registry_prompt_sha256),
            (self.exact_prompt, self.prompt_sha256),
            (self.raw_response, self.response_sha256),
        ):
            if digest(text) != hashed:
                raise ValueError("consumer text SHA-256 mismatch")
        if (self.exact_prompt != self.registry_prompt) != (self.protocol_deviation is not None):
            raise ValueError("modified prompt requires a deviation reason; exact prompt has none")
        if [h.revision for h in self.history] != list(range(1, len(self.history) + 1)):
            raise ValueError("metadata history must be contiguous from revision 1")
        if self.metadata != self.history[-1].metadata:
            raise ValueError("metadata must match last revision")
        times = [h.recorded_at for h in self.history]
        if times != sorted(times):
            raise ValueError("metadata history timestamps must be ordered")
        return self


class ConsumerRequest(ConsumerInputProvenance):
    prompt_id: PromptID
    registry_prompt_sha256: Digest
    exact_prompt: Text
    protocol_deviation: Text | None = None
    raw_response: str
    metadata: ConsumerMetadata


class ConsumerCorrection(Record):
    expected_revision: Annotated[int, Field(strict=True, ge=1)]
    reason: Text
    metadata: ConsumerMetadata
