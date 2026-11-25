"""Reject scenario-family, prompt and response leakage across declared research splits."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from astrotrust.benchmark.models import Digest, Record, Text


class SplitMember(Record):
    run_id: Text
    source: Literal["frontier", "consumer", "local"]
    scenario_family: Text  # Same across revisions, translations, paraphrases and app protocols.
    scenario_sha256: Digest
    prompt_sha256: Digest
    response_sha256: Digest | None
    split: Literal["pilot", "train", "validation", "test"]


class SplitManifest(Record):
    schema_version: Literal["splits-1.0"]
    policy: Literal["scenario-family-disjoint"]
    rationale: Text
    members: Annotated[tuple[SplitMember, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def no_leakage(self) -> Self:
        ids: set[str] = set()
        assignments: dict[tuple[str, str], str] = {}
        for member in self.members:
            if member.run_id in ids:
                raise ValueError("A run can belong to only one split")
            ids.add(member.run_id)
            for field in ("scenario_family", "scenario_sha256", "prompt_sha256", "response_sha256"):
                value = getattr(member, field)
                if value is None:
                    continue
                key = (field, value)
                if key in assignments and assignments[key] != member.split:
                    raise ValueError(f"Cross-split leakage through {field}")
                assignments[key] = member.split
        return self
