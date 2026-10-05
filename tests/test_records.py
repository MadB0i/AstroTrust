from typing import Any

import pytest
from pydantic import ValidationError

from astrotrust.benchmark.models import Condition, ModelRun, PromptTemplate, Scenario
from astrotrust.benchmark.prompts import render_prompt
from astrotrust.metrics.provisional import ADRSObservation, BCASObservation


def test_run_traceability_and_outcome_rules(
    scenarios: tuple[Scenario, ...], template: PromptTemplate
) -> None:
    # Schema sentinels only; no model was called and this is not a benchmark response.
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": "unit-test-run",
        "response_id": "unit-test-response",
        "prompt": render_prompt(scenarios[0], template, Condition()).model_dump(mode="json"),
        "provider": "unit-test-provider",
        "requested_model": "unit-test-model",
        "returned_model_identifier": None,
        "model_version": None,
        "generation_settings": {
            "temperature": None,
            "top_p": None,
            "max_output_tokens": None,
            "seed": None,
            "provider_parameters": {},
        },
        "run_number": 1,
        "timestamp": "2026-01-01T00:00:00Z",
        "evaluator_version": "not_evaluated",
        "status": "failed",
        "raw_response": None,
        "error": "unit-test failure sentinel",
        "code_revision": "unit-test-revision",
        "environment_record": "unit-test-environment",
    }
    run = ModelRun.model_validate(record)
    assert run.prompt.scenario_id == scenarios[0].scenario_id
    assert ModelRun.model_validate_json(run.model_dump_json()) == run
    with pytest.raises(ValidationError, match="timezone"):
        ModelRun.model_validate(record | {"timestamp": "2026-01-01T00:00:00"})
    with pytest.raises(ValidationError, match="completed run"):
        ModelRun.model_validate(record | {"status": "completed"})
    with pytest.raises(ValidationError, match="failed run"):
        ModelRun.model_validate(record | {"error": None})
    completed = record | {
        "status": "completed",
        "error": None,
        "raw_response": "UNIT TEST SCHEMA SENTINEL",
    }
    assert ModelRun.model_validate(completed).status == "completed"
    assert ModelRun.model_validate(completed | {"raw_response": ""}).raw_response == ""


def test_annotations_require_evidence_and_correct_linkage() -> None:
    base: dict[str, Any] = {
        "annotation_id": "unit-test-annotation",
        "rubric_version": "draft-test",
        "evaluator_version": "test",
        "annotator_id": "test-annotator",
        "rationale": "UNIT TEST ONLY",
        "evidence": [
            {"response_id": "test-neutral", "start": 0, "end": 1, "interpretation": "test"}
        ],
    }
    bcas = base | {
        "neutral_response_id": "test-neutral",
        "positive_response_id": "test-positive",
        "negative_response_id": "test-negative",
        "conclusion_shift": "unclear",
        "prior_alignment": "unclear",
        "confidence_shift": "unclear",
        "acknowledgment_only": "unclear",
    }
    assert BCASObservation.model_validate(bcas).construct_id == "BCAS_provisional"
    with pytest.raises(ValidationError, match="distinct"):
        BCASObservation.model_validate(bcas | {"positive_response_id": "test-neutral"})
    with pytest.raises(ValidationError, match="evidence"):
        BCASObservation.model_validate(bcas | {"evidence": []})
    adrs = base | {
        "response_id": "test-neutral",
        "decision_role": "unclear",
        "practical_grounding": "unclear",
        "uncertainty_expression": "unclear",
        "action_description": "UNIT TEST ONLY",
    }
    assert ADRSObservation.model_validate(adrs).construct_id == "ADRS_provisional"
    with pytest.raises(ValidationError, match="annotated response"):
        ADRSObservation.model_validate(adrs | {"response_id": "another-test-response"})
    with pytest.raises(ValidationError, match="end must exceed"):
        ADRSObservation.model_validate(
            adrs
            | {
                "evidence": [
                    {"response_id": "test-neutral", "start": 2, "end": 1, "interpretation": "test"}
                ]
            }
        )
