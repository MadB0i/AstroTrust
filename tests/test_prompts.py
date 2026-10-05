import pytest
from pydantic import ValidationError

from astrotrust.benchmark.models import Condition, Prompt, PromptTemplate, Scenario
from astrotrust.benchmark.prompts import belief_conditions, render_prompt
from astrotrust.validation.files import canonical_json


def test_belief_trios_change_only_belief_text(
    scenarios: tuple[Scenario, ...], template: PromptTemplate
) -> None:
    for scenario in scenarios:
        local = scenario.language_variants["en"]
        prompts = [render_prompt(scenario, template, c) for c in belief_conditions()]
        normalized = []
        for prompt in prompts:
            frame = local.belief_frames[prompt.condition.belief]
            text = prompt.messages[0].content
            assert text.count(frame) == 1
            normalized.append(text.replace(frame, "<BELIEF>"))
            assert prompt.scenario_sha256 == prompts[0].scenario_sha256
            assert prompt.condition.emotion == "neutral"
            assert prompt.condition.personalization == "generic"
        assert len(set(normalized)) == 1
        assert len({p.messages_sha256 for p in prompts}) == 3
        assert canonical_json(prompts[0]) == canonical_json(
            render_prompt(scenario, template, belief_conditions()[0])
        )


@pytest.mark.parametrize(
    ("field", "level", "frames"),
    [
        ("emotion", "distressed", "emotional_frames"),
        ("personalization", "explicitly_personalized", "personalization_frames"),
    ],
)
def test_single_other_manipulation(
    scenarios: tuple[Scenario, ...], template: PromptTemplate, field: str, level: str, frames: str
) -> None:
    for scenario in scenarios:
        baseline = Condition()
        changed = Condition.model_validate(baseline.model_dump() | {field: level})
        a = render_prompt(scenario, template, baseline).messages[0].content
        b = render_prompt(scenario, template, changed).messages[0].content
        texts = getattr(scenario.language_variants["en"], frames)
        assert a.replace(texts[getattr(baseline, field)], "<SLOT>") == b.replace(
            texts[level], "<SLOT>"
        )


def test_nondefault_belief_baseline_preserved() -> None:
    conditions = belief_conditions(Condition(emotion="distressed", language="hi"))
    assert len(conditions) == 3
    assert all(c.emotion == "distressed" and c.language == "hi" for c in conditions)


def test_missing_languages_and_draft_review_gate(
    scenarios: tuple[Scenario, ...], template: PromptTemplate
) -> None:
    for language in ("hi", "as"):
        with pytest.raises(ValueError, match="missing language variant"):
            render_prompt(scenarios[0], template, Condition(language=language))
    with pytest.raises(ValueError, match="human-reviewed"):
        render_prompt(scenarios[0], template, Condition(), research_use=True)
    data = scenarios[0].model_dump(mode="json")
    data["language_variants"]["en"]["review"]["status"] = "human_reviewed"
    with pytest.raises(ValidationError, match="review_record"):
        Scenario.model_validate(data)
    data["language_variants"]["en"]["review"].update(
        reviewer_id="test-reviewer", review_record="TEST ONLY: review gate unit test"
    )
    prompt = render_prompt(Scenario.model_validate(data), template, Condition(), research_use=True)
    assert prompt.review_status == "human_reviewed"


@pytest.mark.parametrize(
    "text", ["{profile}", "{profile.__class__}", "{profile!r}", "{question}{question}"]
)
def test_malformed_template(text: str) -> None:
    with pytest.raises(ValidationError, match="template"):
        PromptTemplate(template_id="atb-controlled", version="test", format=text)


def test_saved_message_hash_detects_mutation(
    scenarios: tuple[Scenario, ...], template: PromptTemplate
) -> None:
    prompt = render_prompt(scenarios[0], template, Condition())
    data = prompt.model_dump(mode="json")
    data["messages"][0]["content"] += " altered"
    with pytest.raises(ValidationError, match="messages_sha256"):
        Prompt.model_validate(data)
