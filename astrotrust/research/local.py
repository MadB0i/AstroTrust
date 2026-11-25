"""Inference-only boundary. Adapters are supplied explicitly; nothing downloads a model."""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Literal, Protocol, Self
from uuid import uuid4

from pydantic import Field, model_validator

from astrotrust.benchmark.models import Digest, GenerationSettings, ModelRun, Prompt, Record, Text
from astrotrust.benchmark.prompts import digest
from astrotrust.collector.exports import parse_json
from astrotrust.collector.service import code_provenance
from astrotrust.validation.files import canonical_json


class LocalRequest(Record):
    schema_version: Literal["local-request-1.0"]
    operation: Literal["inference_only"]
    study_phase: Literal["exploratory_pilot"]
    requested_model: Text
    model_artifact_sha256: Digest
    tokenizer_artifact_sha256: Digest
    runtime_description: Text  # Version, quantization, hardware and chat-template details.
    prompt: Prompt  # Exact complete messages and existing instrument provenance.
    settings: GenerationSettings
    run_number: Annotated[int, Field(strict=True, ge=1)]


class InferenceResult(Record):
    raw_response: str
    returned_model_identifier: Text | None
    model_version: Text | None
    observed_settings: dict[str, str | int | float | bool | None]


class InferenceAdapter(Protocol):
    name: str

    def generate(self, request: LocalRequest) -> InferenceResult: ...


class CommandAdapter:
    """One JSON request on stdin, one JSON result on stdout; shell execution is disabled."""

    name = "explicit-command-1.0"

    def __init__(self, command: tuple[str, ...], timeout: float = 120) -> None:
        if not command or timeout <= 0:
            raise ValueError("An explicit adapter command and positive timeout are required")
        self.command, self.timeout = command, timeout

    def generate(self, request: LocalRequest) -> InferenceResult:
        result = subprocess.run(
            self.command,
            input=request.model_dump_json(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=self.timeout,
            check=False,
            shell=False,
        )
        if result.returncode:
            raise ValueError(f"Adapter failed with exit status {result.returncode}")
        return InferenceResult.model_validate(parse_json(result.stdout))


class LocalAttempt(Record):
    schema_version: Literal["local-attempt-1.0"]
    study_phase: Literal["exploratory_pilot"]
    request: LocalRequest
    request_sha256: Digest
    adapter: Text
    adapter_command: tuple[str, ...] | None
    run: ModelRun
    response_sha256: Digest | None
    observed_settings: dict[str, str | int | float | bool | None]
    code_worktree_dirty: bool | None
    environment: dict[str, str]

    @model_validator(mode="after")
    def integrity(self) -> Self:
        expected_response = None if self.run.raw_response is None else digest(self.run.raw_response)
        if self.request_sha256 != digest(canonical_json(self.request)):
            raise ValueError("Local request hash mismatch")
        if self.response_sha256 != expected_response:
            raise ValueError("Local response hash mismatch")
        if (
            self.run.prompt != self.request.prompt
            or self.run.requested_model != self.request.requested_model
            or self.run.generation_settings != self.request.settings
            or self.run.run_number != self.request.run_number
            or self.run.provider != "local"
        ):
            raise ValueError("Local run does not match its inference request")
        return self


def run_inference(request: LocalRequest, adapter: InferenceAdapter, root: Path) -> LocalAttempt:
    revision, dirty = code_provenance(root)
    result = None
    failure = None
    try:
        result = InferenceResult.model_validate(adapter.generate(request).model_dump())
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        # Do not leak provider stdout, stderr, paths or possibly sensitive prompt text.
        failure = (
            f"Inference adapter failed ({type(exc).__name__}); retain attempt and inspect locally"
        )
    run = ModelRun(
        schema_version="1.0",
        run_id=f"local-{uuid4().hex}",
        response_id=f"local-response-{uuid4().hex}",
        prompt=request.prompt,
        provider="local",
        requested_model=request.requested_model,
        returned_model_identifier=result.returned_model_identifier if result else None,
        model_version=result.model_version if result else None,
        generation_settings=request.settings,
        run_number=request.run_number,
        timestamp=datetime.now(UTC),
        evaluator_version="local-inference-1.0",
        status="completed" if result else "failed",
        raw_response=result.raw_response if result else None,
        error=failure,
        code_revision=revision or "unknown",
        environment_record="embedded:environment",
    )
    return LocalAttempt(
        schema_version="local-attempt-1.0",
        study_phase="exploratory_pilot",
        request=request,
        request_sha256=digest(canonical_json(request)),
        adapter=adapter.name,
        adapter_command=adapter.command if isinstance(adapter, CommandAdapter) else None,
        run=run,
        response_sha256=digest(result.raw_response) if result else None,
        observed_settings=result.observed_settings if result else {},
        code_worktree_dirty=dirty,
        environment={
            "python": sys.version,
            "platform": platform.platform(),
            "astrotrust": version("astrotrust"),
            "pydantic": version("pydantic"),
        },
    )


def save_inference(
    request: LocalRequest, adapter: InferenceAdapter, root: Path, output: Path
) -> LocalAttempt:
    # Reserve output before inference. Existing records are never replaced or run again by accident.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as file:
        attempt = run_inference(request, adapter, root)
        file.write(canonical_json(attempt))
    return attempt
