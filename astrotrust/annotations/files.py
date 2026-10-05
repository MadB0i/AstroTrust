"""Offline structural and optional source/evidence validation."""

from collections.abc import Iterable
from pathlib import Path

from astrotrust.annotations.models import (
    AnnotationBatch,
    EvidenceSpan,
    FieldSupport,
    ResponseAnnotation,
    reference_from_run,
)
from astrotrust.benchmark.models import ModelRun
from astrotrust.validation.files import read_json


def load_batch(path: Path) -> AnnotationBatch:
    return AnnotationBatch.model_validate(read_json(path))


def load_runs(path: Path) -> dict[str, ModelRun]:
    files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    if not files:
        raise ValueError("no run JSON files found")
    runs: dict[str, ModelRun] = {}
    responses: set[str] = set()
    for file in files:
        run = ModelRun.model_validate(read_json(file))
        if run.run_id in runs or run.response_id in responses:
            raise ValueError("duplicate run/response ID in source store")
        runs[run.run_id] = run
        responses.add(run.response_id)
    return runs


def _check_span(evidence: EvidenceSpan, responses: dict[str, str]) -> None:
    text = responses[evidence.response_id]
    if evidence.end > len(text) or text[evidence.start : evidence.end] != evidence.excerpt:
        raise ValueError("evidence bounds/excerpt do not match the raw response")


def validate_sources(batch: AnnotationBatch, runs: dict[str, ModelRun]) -> None:
    for annotation in batch.annotations:
        refs = (
            (annotation.target,)
            if isinstance(annotation, ResponseAnnotation)
            else annotation.targets
        )
        selected: list[ModelRun] = []
        responses: dict[str, str] = {}
        for ref in refs:
            run = runs.get(ref.run_id)
            if run is None or reference_from_run(run) != ref:
                raise ValueError("annotation reference does not match a source run")
            if run.status != "completed" or run.raw_response is None:
                raise ValueError("response annotations require a completed source run")
            selected.append(run)
            responses[ref.response_id] = run.raw_response
        supports: Iterable[FieldSupport]
        if isinstance(annotation, ResponseAnnotation):
            if not responses[annotation.target.response_id].strip() and (
                annotation.annotation_uncertainty != "unratable"
            ):
                raise ValueError("empty response must be explicitly marked unratable")
            supports = annotation.support.values()
        else:
            _check_run_controls(selected)
            supports = (s for c in annotation.contrasts for s in c.support.values())
        for support in supports:
            for evidence in support.evidence:
                _check_span(evidence, responses)


def _check_run_controls(runs: list[ModelRun]) -> None:
    def controls(run: ModelRun) -> tuple[object, ...]:
        return (
            run.provider,
            run.requested_model,
            run.returned_model_identifier,
            run.model_version,
            run.generation_settings,
            run.run_number,
            tuple(message for message in run.prompt.messages if message.role != "user"),
        )

    if any(controls(run) != controls(runs[0]) for run in runs[1:]):
        raise ValueError("matched runs differ in model/settings/replicate/non-user context")


def annotation_refs(batch: AnnotationBatch) -> int:
    return len(
        {
            ref.response_id
            for a in batch.annotations
            for ref in ((a.target,) if isinstance(a, ResponseAnnotation) else a.targets)
        }
    )
