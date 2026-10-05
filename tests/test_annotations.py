"""All records in these tests are explicitly toy schema data, not human observations."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from astrotrust.__main__ import main
from astrotrust.annotations.adjudication import adjudicate, verify_originals
from astrotrust.annotations.files import validate_sources
from astrotrust.annotations.models import AnnotationBatch, ComparisonAnnotation, ResponseAnnotation
from astrotrust.benchmark.models import ModelRun
from astrotrust.validation.files import canonical_json


def _batch(*annotations: ResponseAnnotation | ComparisonAnnotation) -> AnnotationBatch:
    return AnnotationBatch(
        kind="annotation_batch",
        schema_version="1.0",
        purpose="synthetic_example",
        annotations=annotations,
    )


def test_annotation_roundtrip_and_source_validation(
    toy_response: ResponseAnnotation,
    toy_comparison: ComparisonAnnotation,
    toy_runs: tuple[ModelRun, ...],
) -> None:
    batch = _batch(toy_response, toy_comparison)
    assert AnnotationBatch.model_validate_json(canonical_json(batch)) == batch
    validate_sources(batch, {run.run_id: run for run in toy_runs})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "2.0"),
        ("rubric_version", "validated"),
        ("annotator_id", "real name"),
        ("timestamp", "2026-10-05T12:00:00"),
    ],
)
def test_bad_annotation_metadata(toy_response: ResponseAnnotation, field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        ResponseAnnotation.model_validate(toy_response.model_dump(mode="json") | {field: value})


def test_unknown_labels_fields_and_unit_separation(toy_response: ResponseAnnotation) -> None:
    data = toy_response.model_dump(mode="json")
    data["labels"]["decision_reliance"] = 3
    with pytest.raises(ValidationError, match="decision_reliance"):
        ResponseAnnotation.model_validate(data)
    data = toy_response.model_dump(mode="json")
    data["labels"]["sycophancy"] = True
    with pytest.raises(ValidationError, match="Extra inputs"):
        ResponseAnnotation.model_validate(data)
    with pytest.raises(ValidationError):
        ComparisonAnnotation.model_validate(toy_response.model_dump(mode="json"))
    data = toy_response.model_dump(mode="json")
    data["target"]["condition_id"] = "invented"
    with pytest.raises(ValidationError, match="condition_id"):
        ResponseAnnotation.model_validate(data)
    data = toy_response.model_dump(mode="json")
    data["labels"]["belief_relationship"] = "agrees"
    with pytest.raises(ValidationError, match="neutral prior"):
        ResponseAnnotation.model_validate(data)


def test_support_and_uncertainty_required(toy_response: ResponseAnnotation) -> None:
    data = toy_response.model_dump(mode="json")
    del data["support"]["practical_grounding"]
    with pytest.raises(ValidationError, match="every response label"):
        ResponseAnnotation.model_validate(data)
    data = toy_response.model_dump(mode="json")
    data["annotation_uncertainty"] = "uncertain"
    with pytest.raises(ValidationError, match="needs_adjudication"):
        ResponseAnnotation.model_validate(data)


def test_validation_errors_do_not_echo_private_input(toy_response: ResponseAnnotation) -> None:
    data = toy_response.model_dump(mode="json") | {"annotator_id": "example@example.invalid"}
    with pytest.raises(ValidationError) as error:
        ResponseAnnotation.model_validate(data)
    assert "example@example.invalid" not in str(error.value)


def test_cli_adjudication_writes_separate_file_and_verifies_sources(
    toy_response: ResponseAnnotation,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    other = ResponseAnnotation.model_validate(
        toy_response.model_dump(mode="json")
        | {
            "annotation_id": "ann-cli-other",
            "annotator_id": "rater-b1",
        }
    )
    final = ResponseAnnotation.model_validate(
        toy_response.model_dump(mode="json")
        | {
            "annotation_id": "ann-cli-final",
            "annotator_id": "rater-c1",
        }
    )
    originals_path = tmp_path / "originals.json"
    final_path = tmp_path / "final.json"
    output = tmp_path / "adjudication.json"
    originals_path.write_text(canonical_json(_batch(toy_response, other)), encoding="utf-8")
    final_path.write_text(canonical_json(_batch(final)), encoding="utf-8")
    before = originals_path.read_bytes()
    command = [
        "annotations",
        "adjudicate",
        str(originals_path),
        str(final_path),
        "--ids",
        toy_response.annotation_id,
        other.annotation_id,
        "--adjudication-id",
        "adj-cli-toy",
        "--reason",
        "Toy CLI verification only.",
        "--timestamp",
        "2026-10-05T00:00:00Z",
        "--output",
        str(output),
    ]
    assert main(command) == 0
    assert originals_path.read_bytes() == before
    assert main(["annotations", "validate", str(output), "--originals", str(originals_path)]) == 0
    assert "originals verified" in capsys.readouterr().out
    assert main(command) == 1
    assert originals_path.read_bytes() == before
    capsys.readouterr()
    assert (
        main(
            [
                "annotations",
                "agreement",
                str(output),
                "--kind",
                "response",
                "--field",
                "decision_reliance",
                "--raters",
                "rater-a1",
                "rater-b1",
            ]
        )
        == 1
    )
    assert "not adjudicated" in capsys.readouterr().err


def test_comparison_requires_matching_context(toy_comparison: ComparisonAnnotation) -> None:
    data = toy_comparison.model_dump(mode="json")
    data["targets"][1]["scenario_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="context"):
        ComparisonAnnotation.model_validate(data)
    data = toy_comparison.model_dump(mode="json")
    data["contrasts"] = data["contrasts"][:1]
    with pytest.raises(ValidationError, match="one contrast"):
        ComparisonAnnotation.model_validate(data)
    data = toy_comparison.model_dump(mode="json")
    data["targets"] = data["targets"][1:]
    with pytest.raises(ValidationError, match="neutral"):
        ComparisonAnnotation.model_validate(data)
    # A pair is a distinct supported unit, with exactly one neutral/variant contrast.
    data = toy_comparison.model_dump(mode="json")
    data["targets"] = data["targets"][:2]
    data["contrasts"] = data["contrasts"][:1]
    assert len(ComparisonAnnotation.model_validate(data).contrasts) == 1


def test_evidence_exactness_and_model_control(
    toy_response: ResponseAnnotation,
    toy_comparison: ComparisonAnnotation,
    toy_runs: tuple[ModelRun, ...],
) -> None:
    data = toy_response.model_dump(mode="json")
    evidence = {
        "response_id": toy_response.target.response_id,
        "start": 0,
        "end": 3,
        "excerpt": "TOY",
    }
    data["support"]["astrological_claim"]["evidence"] = [evidence]
    annotated = ResponseAnnotation.model_validate(data)
    runs = {run.run_id: run for run in toy_runs}
    validate_sources(_batch(annotated), runs)
    data["support"]["astrological_claim"]["evidence"][0]["excerpt"] = "BAD"
    with pytest.raises(ValueError, match="excerpt"):
        validate_sources(_batch(ResponseAnnotation.model_validate(data)), runs)
    data["support"]["astrological_claim"]["evidence"][0]["response_id"] = "wrong-response"
    with pytest.raises(ValidationError, match="target response"):
        ResponseAnnotation.model_validate(data)
    changed = toy_runs[1].model_dump(mode="json")
    changed["generation_settings"]["seed"] = 99
    runs[toy_runs[1].run_id] = ModelRun.model_validate(changed)
    with pytest.raises(ValueError, match="model/settings"):
        validate_sources(_batch(toy_comparison), runs)


def test_duplicate_and_conflicting_records(toy_response: ResponseAnnotation) -> None:
    with pytest.raises(ValidationError, match="duplicate annotation IDs"):
        _batch(toy_response, toy_response)
    other = toy_response.model_dump(mode="json")
    other["annotation_id"] = "ann-other"
    other["target"]["messages_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="conflicting provenance"):
        _batch(toy_response, ResponseAnnotation.model_validate(other))


def test_adjudication_preserves_originals_and_detects_changes(
    toy_response: ResponseAnnotation,
    tmp_path: Path,
) -> None:
    other_data = toy_response.model_dump(mode="json") | {
        "annotation_id": "ann-toy-b",
        "annotator_id": "rater-b1",
    }
    other_data["labels"]["practical_grounding"] = "minimal"
    other = ResponseAnnotation.model_validate(other_data)
    final = ResponseAnnotation.model_validate(
        toy_response.model_dump(mode="json")
        | {"annotation_id": "ann-toy-final", "annotator_id": "rater-c1"}
    )
    source_path = tmp_path / "independent.json"
    source_path.write_text(canonical_json(_batch(toy_response, other)), encoding="utf-8")
    before = source_path.read_bytes()
    record = adjudicate(
        (toy_response, other),
        final,
        adjudication_id="adj-toy",
        reason="Toy resolution only.",
        timestamp=datetime.fromisoformat("2026-10-05T00:00:00+00:00"),
        purpose="synthetic_example",
    )
    assert source_path.read_bytes() == before
    verify_originals(record, (toy_response, other))
    other_data["rationale"] = "Changed after decision."
    with pytest.raises(ValueError, match="changed"):
        verify_originals(record, (toy_response, ResponseAnnotation.model_validate(other_data)))
    with pytest.raises(ValueError, match="original IDs"):
        adjudicate(
            (toy_response, other),
            toy_response,
            adjudication_id="adj-bad",
            reason="toy",
            timestamp=record.timestamp,
        )


def test_cli_annotations_and_no_example_agreement(
    toy_response: ResponseAnnotation,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "toy.json"
    path.write_text(canonical_json(_batch(toy_response)), encoding="utf-8")
    assert main(["annotations", "validate", str(path)]) == 0
    assert "source runs/evidence unchecked" in capsys.readouterr().out
    assert (
        main(
            [
                "annotations",
                "agreement",
                str(path),
                "--kind",
                "response",
                "--field",
                "decision_reliance",
                "--raters",
                "rater-a1",
                "rater-b1",
            ]
        )
        == 1
    )
    assert "disabled" in capsys.readouterr().err
