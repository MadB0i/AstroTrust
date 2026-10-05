from pathlib import Path
from typing import get_args

import pytest

from astrotrust.annotations.models import (
    ComparisonAnnotation,
    ComparisonField,
    ResponseAnnotation,
    ResponseField,
    reference_from_run,
)
from astrotrust.benchmark.models import ModelRun, PromptTemplate, Scenario
from astrotrust.benchmark.prompts import belief_conditions, load_template, render_prompt
from astrotrust.validation.files import load_scenarios


@pytest.fixture(scope="session")
def scenarios() -> tuple[Scenario, ...]:
    return load_scenarios(Path("benchmark/scenarios"))


@pytest.fixture(scope="session")
def template() -> PromptTemplate:
    return load_template(Path("benchmark/prompts/controlled-v1.json"))


@pytest.fixture
def toy_runs(scenarios: tuple[Scenario, ...], template: PromptTemplate) -> tuple[ModelRun, ...]:
    """Schema-testing sentinels only: never collected model outputs or research data."""
    return tuple(
        ModelRun.model_validate(
            {
                "schema_version": "1.0",
                "run_id": f"toy-run-{i}",
                "response_id": f"toy-response-{i}",
                "prompt": render_prompt(scenarios[0], template, condition).model_dump(mode="json"),
                "provider": "unit-test",
                "requested_model": "unit-test",
                "returned_model_identifier": None,
                "model_version": None,
                "generation_settings": {
                    "temperature": 0,
                    "top_p": 1,
                    "max_output_tokens": 100,
                    "seed": 7,
                    "provider_parameters": {},
                },
                "run_number": 1,
                "timestamp": "2026-10-05T00:00:00Z",
                "evaluator_version": "unit-test",
                "status": "completed",
                "raw_response": f"TOY SCHEMA SENTINEL {i}; not a model output.",
                "error": None,
                "code_revision": "unit-test",
                "environment_record": "unit-test",
            }
        )
        for i, condition in enumerate(belief_conditions())
    )


@pytest.fixture
def toy_response(toy_runs: tuple[ModelRun, ...]) -> ResponseAnnotation:
    return ResponseAnnotation.model_validate(
        {
            "kind": "response",
            "schema_version": "1.0",
            "annotation_id": "ann-toy-a",
            "annotator_id": "rater-a1",
            "rubric_version": "draft-1.0",
            "timestamp": "2026-10-05T00:00:00Z",
            "annotation_uncertainty": "clear",
            "needs_adjudication": False,
            "rationale": "Toy structure only, no research judgment.",
            "target": reference_from_run(toy_runs[0]).model_dump(mode="json"),
            "labels": {
                "astrological_claim": "absent",
                "belief_relationship": "not_applicable",
                "epistemic_framing": "none",
                "practical_grounding": "none",
                "decision_reliance": "no_decision_basis",
                "reliance_stance": "no_position",
                "prediction_uncertainty": "not_applicable",
                "action_recommendation": "none",
                "emotional_affirmation": "absent",
                "acknowledgment_without_endorsement": "absent",
                "guidance_displacement": "no_position",
            },
            "support": {
                field: {"evidence": [], "reason": "Toy schema-only reason."}
                for field in get_args(ResponseField)
            },
        }
    )


@pytest.fixture
def toy_comparison(
    toy_runs: tuple[ModelRun, ...], toy_response: ResponseAnnotation
) -> ComparisonAnnotation:
    meta = toy_response.model_dump(mode="json", exclude={"target", "labels", "support"})
    meta.update(kind="comparison", annotation_id="ann-toy-comparison")
    return ComparisonAnnotation.model_validate(
        meta
        | {
            "targets": [reference_from_run(run).model_dump(mode="json") for run in toy_runs],
            "contrasts": [
                {
                    "variant_response_id": run.response_id,
                    "labels": {
                        "conclusion_direction": "incomparable",
                        "prior_alignment": "not_applicable",
                        "confidence_change": "incomparable",
                        "astrological_rationale": "not_applicable",
                        "practical_guidance": "not_applicable",
                        "contradiction": "incomparable",
                    },
                    "support": {
                        field: {"evidence": [], "reason": "Toy structure only."}
                        for field in get_args(ComparisonField)
                    },
                }
                for run in toy_runs[1:]
            ],
        }
    )
