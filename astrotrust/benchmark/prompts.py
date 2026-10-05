"""Explicit condition rendering; no implicit factorial expansion or translation."""

from __future__ import annotations

import hashlib
from pathlib import Path

from astrotrust.benchmark.models import (
    BELIEFS,
    Condition,
    Message,
    Prompt,
    PromptTemplate,
    Scenario,
    messages_digest,
)
from astrotrust.validation.files import canonical_json, read_json


def digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_template(path: Path) -> PromptTemplate:
    return PromptTemplate.model_validate(read_json(path))


def render_prompt(
    scenario: Scenario,
    template: PromptTemplate,
    condition: Condition,
    *,
    research_use: bool = False,
) -> Prompt:
    localized = scenario.language_variants.get(condition.language)
    if localized is None:
        raise ValueError(f"{scenario.scenario_id}: missing language variant {condition.language}")
    if research_use and localized.review.status != "human_reviewed":
        raise ValueError("research use requires human-reviewed language text")
    # Profile information stays identical across personalization levels.
    message = Message(
        role="user",
        content=template.format.format(
            profile=localized.profile_text,
            situation=localized.situation,
            belief=localized.belief_frames[condition.belief],
            emotion=localized.emotional_frames[condition.emotion],
            personalization=localized.personalization_frames[condition.personalization],
            question=localized.baseline_question,
        ),
    )
    messages = (message,)
    return Prompt(
        schema_version="1.0",
        scenario_id=scenario.scenario_id,
        scenario_revision=scenario.revision,
        scenario_sha256=digest(canonical_json(scenario)),
        template_id=template.template_id,
        template_version=template.version,
        template_sha256=digest(canonical_json(template)),
        language_revision=localized.revision,
        review_status=localized.review.status,
        condition=condition,
        messages=messages,
        messages_sha256=messages_digest(messages),
    )


def belief_conditions(baseline: Condition | None = None) -> tuple[Condition, ...]:
    """A matched belief trio, holding every other dimension fixed."""
    base = baseline or Condition()
    return tuple(Condition(**(base.model_dump() | {"belief": belief})) for belief in BELIEFS)
