"""Known toy arithmetic only; no scientific estimates are produced."""

import pytest

from astrotrust.annotations.agreement import batch_agreement, cohen_agreement
from astrotrust.annotations.models import AnnotationBatch, ResponseAnnotation


def test_nominal_known_examples() -> None:
    result = cohen_agreement(["a", "a", "b", "b"], ["a", "b", "b", "b"])
    assert result.percent_agreement == 75
    assert result.kappa == pytest.approx(0.5)
    assert result.confusion_matrix == ((1, 1), (0, 2))
    assert cohen_agreement(["a", "b"], ["a", "b"]).kappa == 1
    assert cohen_agreement(["a", "b"], ["b", "a"]).kappa == -1


def test_weighted_known_examples_and_prespecified_unobserved_levels() -> None:
    first = ["low", "middle", "high"]
    second = ["low", "high", "high"]
    order = ("low", "middle", "high")
    assert cohen_agreement(
        first, second, weights="linear", categories=order
    ).kappa == pytest.approx(2 / 3)
    assert cohen_agreement(
        first, second, weights="quadratic", categories=order
    ).kappa == pytest.approx(0.8)
    result = cohen_agreement(
        ["low", "high"], ["middle", "high"], weights="linear", categories=order
    )
    assert result.categories == order
    assert len(result.confusion_matrix) == 3


def test_missing_excluded_and_undefined_cases() -> None:
    result = cohen_agreement(["a", None, "unclear", "b"], ["a", "a", "b", "b"])
    assert (result.n_total, result.n_used, result.n_missing, result.n_excluded) == (4, 2, 1, 1)
    assert result.kappa == 1
    assert cohen_agreement([], []).kappa is None
    unanimous = cohen_agreement(["a", "a"], ["a", "a"])
    assert unanimous.percent_agreement == 100
    assert unanimous.kappa is None
    assert "undefined" in str(unanimous.undefined_reason)
    assert cohen_agreement([None], [None]).percent_agreement is None


def test_invalid_agreement_inputs() -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        cohen_agreement(["a"], [])
    with pytest.raises(ValueError, match="category order"):
        cohen_agreement(["a"], ["a"], weights="linear")
    with pytest.raises(ValueError, match="unique"):
        cohen_agreement(["a"], ["a"], categories=("a", "a"))
    with pytest.raises(ValueError, match="outside"):
        cohen_agreement(["a"], ["b"], categories=("a",))


def test_batch_join_and_ordinal_guard(toy_response: ResponseAnnotation) -> None:
    # Temporarily using purpose=research tests the join path; these remain toy unit data.
    other_data = toy_response.model_dump(mode="json") | {
        "annotation_id": "ann-toy-b",
        "annotator_id": "rater-b1",
    }
    other_data["labels"]["practical_grounding"] = "minimal"
    batch = AnnotationBatch(
        kind="annotation_batch",
        schema_version="1.0",
        purpose="research",
        annotations=(toy_response, ResponseAnnotation.model_validate(other_data)),
    )
    result = batch_agreement(
        batch,
        kind="response",
        field="practical_grounding",
        raters=("rater-a1", "rater-b1"),
        weights="linear",
    )
    assert result.n_used == 1
    unratable = toy_response.model_dump(mode="json") | {
        "annotation_uncertainty": "unratable",
        "needs_adjudication": True,
    }
    excluded_batch = AnnotationBatch(
        kind="annotation_batch",
        schema_version="1.0",
        purpose="research",
        annotations=(ResponseAnnotation.model_validate(unratable), batch.annotations[1]),
    )
    excluded = batch_agreement(
        excluded_batch,
        kind="response",
        field="practical_grounding",
        raters=("rater-a1", "rater-b1"),
    )
    assert excluded.n_excluded == 1 and excluded.n_used == 0
    with pytest.raises(ValueError, match="draft ordinal"):
        batch_agreement(
            batch,
            kind="response",
            field="epistemic_framing",
            raters=("rater-a1", "rater-b1"),
            weights="linear",
        )
    with pytest.raises(ValueError, match="same rater/unit"):
        duplicate = toy_response.model_dump(mode="json") | {"annotation_id": "ann-repeat"}
        batch_agreement(
            AnnotationBatch(
                kind="annotation_batch",
                schema_version="1.0",
                purpose="research",
                annotations=(*batch.annotations, ResponseAnnotation.model_validate(duplicate)),
            ),
            kind="response",
            field="practical_grounding",
            raters=("rater-a1", "rater-b1"),
        )
