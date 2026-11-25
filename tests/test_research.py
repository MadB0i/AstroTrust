"""Pivot regressions use synthetic sentinels; never collect or label real model outputs."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from threading import Thread
from typing import get_args

import pytest
from test_collector import http, metadata, request
from test_consumer_collector import request as consumer_request

from astrotrust.__main__ import main
from astrotrust.annotations.models import ResponseAnnotation, ResponseField
from astrotrust.benchmark.models import Condition, GenerationSettings
from astrotrust.benchmark.prompts import digest
from astrotrust.collector.consumer_service import ConsumerCollector
from astrotrust.collector.consumer_store import ConsumerStore
from astrotrust.collector.models import ManualRun
from astrotrust.collector.server import make_server
from astrotrust.collector.service import Collector
from astrotrust.collector.store import RunStore
from astrotrust.research.analysis import CaptureAnnotation, summarize
from astrotrust.research.inventory import read_captures, research_status
from astrotrust.research.local import (
    CommandAdapter,
    InferenceResult,
    LocalAttempt,
    LocalRequest,
    run_inference,
    save_inference,
)
from astrotrust.research.splits import SplitManifest
from astrotrust.validation.files import canonical_json, read_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def collector(tmp_path: Path) -> Collector:
    return Collector(ROOT, RunStore(tmp_path / "frontier.sqlite3"))


def test_status_missing_and_read_only_revision_validation(
    collector: Collector, tmp_path: Path
) -> None:
    missing = tmp_path / "missing" / "consumer.sqlite3"
    assert research_status(collector.store.path, missing)["consumer"]["captures"] is None
    assert not missing.parent.exists()
    run = collector.save(request(collector))
    corrected = collector.store.correct(
        run.run_id, metadata(capture_note="Synthetic revision"), "test", 1
    )
    before = collector.store.path.read_bytes()
    assert read_captures(collector.store.path) == (corrected,)
    assert collector.store.path.read_bytes() == before
    status = research_status(collector.store.path, missing)
    assert status["frontier"]["captures"] == 1 and status["frontier"]["snapshots"] == 2
    assert status["local"]["captures"] is None
    # A validly hashed but rewritten old snapshot still breaks append-only history.
    corrupted = run.model_dump(mode="json")
    corrupted["raw_response"] = "Changed synthetic evidence"
    corrupted["response_sha256"] = digest(corrupted["raw_response"])
    with sqlite3.connect(collector.store.path) as db:
        db.execute("UPDATE snapshots SET record=? WHERE revision=1", (json.dumps(corrupted),))
    assert research_status(collector.store.path, missing)["frontier"]["state"] == "error"


def test_workstation_routes_auth_and_lazy_frontier_preservation(tmp_path: Path) -> None:
    general, consumer = tmp_path / "general.sqlite3", tmp_path / "consumer.sqlite3"
    with make_server(ROOT, general, 0, consumer_database=consumer, start_consumer=True) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            consumer_before = consumer.read_bytes()
            for route in ("/research", "/local", "/", "/consumer"):
                code, content = http(server, route)
                assert code == 200
                for target in ("/research", "/consumer", "/local"):
                    assert f'href="{target}"' in content
                assert 'href="/survey"' not in content
            assert http(server, "/survey")[0] == 404
            assert http(server, "/api/survey")[0] == 404
            assert http(server, "/api/research/status", authorized=False)[0] == 403
            assert http(server, "/api/research/status", origin="https://foreign.example")[0] == 403
            code, content = http(server, "/api/research/status")
            assert code == 200
            status = json.loads(content)
            assert status["frontier"]["state"] == "unavailable"
            assert status["consumer"]["captures"] == 0
            assert not general.exists() and server._collector is None
            assert consumer.read_bytes() == consumer_before
            assert server.consumer is not None
            server.consumer.save(consumer_request())
            server.collector.save(request(server.collector))
            general_before, consumer_before = general.read_bytes(), consumer.read_bytes()
            code, content = http(server, "/api/research/status")
            assert code == 200
            status = json.loads(content)
            assert status["frontier"]["captures"] == status["consumer"]["captures"] == 1
            assert (
                general.read_bytes() == general_before and consumer.read_bytes() == consumer_before
            )
        finally:
            server.shutdown()
            thread.join()


def test_inventory_detects_missing_snapshots_instead_of_reporting_zero(
    collector: Collector,
    tmp_path: Path,
) -> None:
    collector.save(request(collector))
    with sqlite3.connect(collector.store.path) as db:
        db.execute("DELETE FROM snapshots")
    status = research_status(collector.store.path, tmp_path / "missing.sqlite3")
    assert status["frontier"]["captures"] is None
    assert status["frontier"]["state"] == "error"


def capture_annotation(
    collector: Collector,
    toy: ResponseAnnotation,
) -> tuple[ManualRun, CaptureAnnotation]:
    run = collector.save(request(collector))
    annotation = CaptureAnnotation(
        schema_version="capture-annotation-1.0",
        annotation_id="synthetic-human-a",
        run_id=run.run_id,
        capture_schema="manual-1.0",
        capture_sha256=digest(canonical_json(run)),
        response_sha256=run.response_sha256,
        origin="human",
        evaluator_id="rater-toy",
        evaluator_provenance="Synthetic schema sentinel, not a human judgment",
        timestamp=toy.timestamp,
        rubric_version="draft-1.0",
        uncertainty="clear",
        needs_adjudication=False,
        labels=toy.labels,
        support=toy.support,
    )
    return run, annotation


def test_annotation_summary_separates_model_votes_and_has_no_invented_scores(
    collector: Collector,
    toy_response: ResponseAnnotation,
) -> None:
    run, human = capture_annotation(collector, toy_response)
    machine = CaptureAnnotation.model_validate(
        human.model_dump()
        | {
            "annotation_id": "synthetic-model-a",
            "origin": "model",
            "evaluator_id": "toy-model",
        }
    )
    report = summarize((run,), (human, machine))
    assert report["human_annotated_captures"] == report["model_judged_captures"] == 1
    assert len(report["label_counts"]) == 2 * len(get_args(ResponseField))  # type: ignore[arg-type]
    assert report == summarize((run,), (machine, human))
    empty = summarize((run,))
    assert empty["annotations"] == 0 and empty["label_counts"] == []
    assert "score" not in empty and "ground_truth" not in empty
    with pytest.raises(ValueError, match="Duplicate"):
        summarize((run,), (human, human))


@pytest.mark.parametrize(
    "mutation",
    [
        {"capture_sha256": "0" * 64},
        {"response_sha256": "0" * 64},
        {"run_id": "missing"},
        {"capture_schema": "consumer-1.1"},
    ],
)
def test_annotation_rejects_stale_or_wrong_capture(
    collector: Collector,
    toy_response: ResponseAnnotation,
    mutation: dict[str, object],
) -> None:
    run, annotation = capture_annotation(collector, toy_response)
    bad = CaptureAnnotation.model_validate(annotation.model_dump() | mutation)
    with pytest.raises(ValueError):
        summarize((run,), (bad,))


def test_annotation_checks_exact_response_excerpt(
    collector: Collector,
    toy_response: ResponseAnnotation,
) -> None:
    run, annotation = capture_annotation(collector, toy_response)
    raw = annotation.model_dump()
    raw["support"]["astrological_claim"]["evidence"] = [
        {
            "response_id": run.run_id,
            "start": 0,
            "end": 4,
            "excerpt": "FAKE",
        }
    ]
    with pytest.raises(ValueError, match="excerpt"):
        summarize((run,), (CaptureAnnotation.model_validate(raw),))
    raw["support"]["astrological_claim"]["evidence"][0]["excerpt"] = run.raw_response[:4]
    assert summarize((run,), (CaptureAnnotation.model_validate(raw),))["annotations"] == 1


def test_consumer_annotation_keeps_protocol_and_source_distinct(
    tmp_path: Path,
    collector: Collector,
    toy_response: ResponseAnnotation,
) -> None:
    frontier, original = capture_annotation(collector, toy_response)
    consumer = ConsumerCollector(ROOT, ConsumerStore(tmp_path / "consumer.sqlite3"))
    capture = consumer.save(consumer_request())
    annotation = CaptureAnnotation.model_validate(
        original.model_dump()
        | {
            "annotation_id": "synthetic-consumer-a",
            "run_id": capture.run_id,
            "capture_schema": "consumer-1.1",
            "capture_sha256": digest(canonical_json(capture)),
            "response_sha256": capture.response_sha256,
        }
    )
    report = summarize((frontier, capture), (original, annotation))
    assert report["captures"] == report["human_annotated_captures"] == 2
    groups = report["label_counts"]
    assert isinstance(groups, list)
    assert {row["group"][1] for row in groups} == {
        "general_purpose_llm",
        "consumer_astrology_service",
    }
    before = consumer.store.path.read_bytes()
    assert read_captures(consumer.store.path, consumer=True) == (capture,)
    assert consumer.store.path.read_bytes() == before


def split_member(number: int, split: str) -> dict[str, object]:
    return {
        "run_id": f"synthetic-{number}",
        "source": "local",
        "scenario_family": f"family-{number}",
        "scenario_sha256": digest(f"scenario-{number}"),
        "prompt_sha256": digest(f"prompt-{number}"),
        "response_sha256": digest(f"response-{number}"),
        "split": split,
    }


@pytest.mark.parametrize(
    "field",
    [
        "scenario_family",
        "scenario_sha256",
        "prompt_sha256",
        "response_sha256",
        "run_id",
    ],
)
def test_splits_reject_leakage_across_sources_and_pilot(field: str) -> None:
    a, b = split_member(1, "pilot"), split_member(2, "test")
    manifest = {
        "schema_version": "splits-1.0",
        "policy": "scenario-family-disjoint",
        "rationale": "Synthetic leakage test",
        "members": [a, b],
    }
    assert len(SplitManifest.model_validate(manifest).members) == 2
    b[field], b["source"] = a[field], "consumer"
    with pytest.raises(ValueError):
        SplitManifest.model_validate(manifest)


class SentinelAdapter:
    name = "synthetic-sentinel-only"
    calls = 0

    def generate(self, request: LocalRequest) -> InferenceResult:
        self.calls += 1
        return InferenceResult(
            raw_response="  SYNTHETIC; NOT A MODEL OUTPUT\r\nঅসমীয়া\r ",
            returned_model_identifier=None,
            model_version=None,
            observed_settings={},
        )


@pytest.fixture
def local_request(collector: Collector) -> LocalRequest:
    return LocalRequest(
        schema_version="local-request-1.0",
        operation="inference_only",
        study_phase="exploratory_pilot",
        requested_model="synthetic-sentinel",
        model_artifact_sha256=digest("toy-model"),
        tokenizer_artifact_sha256=digest("toy-tokenizer"),
        runtime_description="No runtime; test only",
        prompt=collector.prompt("atb-career-001", Condition()),
        settings=GenerationSettings(
            temperature=0, top_p=1, max_output_tokens=100, seed=1, provider_parameters={}
        ),
        run_number=1,
    )


def test_local_inference_is_explicit_lossless_and_exclusive(
    local_request: LocalRequest,
    tmp_path: Path,
) -> None:
    adapter = SentinelAdapter()
    output = tmp_path / "attempt.json"
    attempt = save_inference(local_request, adapter, ROOT, output)
    assert LocalAttempt.model_validate(read_json(output)) == attempt
    assert attempt.response_sha256 == digest(attempt.run.raw_response or "")
    assert attempt.run.raw_response == "  SYNTHETIC; NOT A MODEL OUTPUT\r\nঅসমীয়া\r "
    with pytest.raises(FileExistsError):
        save_inference(local_request, adapter, ROOT, output)
    assert adapter.calls == 1
    assert main(["research", "validate-local", str(output)]) == 0
    raw = attempt.model_dump(mode="json")
    raw["run"]["raw_response"] = "tampered"
    with pytest.raises(ValueError, match="hash mismatch"):
        LocalAttempt.model_validate(raw)
    with pytest.raises(ValueError):
        LocalRequest.model_validate(local_request.model_dump() | {"operation": "train"})


@pytest.mark.parametrize(
    "failure",
    [ValueError("synthetic"), OSError("synthetic"), subprocess.TimeoutExpired("synthetic", 0.01)],
)
def test_local_failures_are_saved_not_retried(
    local_request: LocalRequest,
    tmp_path: Path,
    failure: Exception,
) -> None:
    class FailingAdapter:
        name = "synthetic-failure"

        def generate(self, request: LocalRequest) -> InferenceResult:
            raise failure

    attempt = save_inference(local_request, FailingAdapter(), ROOT, tmp_path / "failure.json")
    assert attempt.run.status == "failed" and attempt.run.raw_response is None
    assert attempt.response_sha256 is None and attempt.run.error


def test_command_adapter_contract_and_cli(local_request: LocalRequest, tmp_path: Path) -> None:
    adapter = tmp_path / "synthetic_adapter.py"
    adapter.write_text(
        "import json,sys\nrequest=json.load(sys.stdin)\n"
        "assert request['operation']=='inference_only'\n"
        "print(json.dumps({'raw_response':'SYNTHETIC ONLY', 'returned_model_identifier':None, "
        "'model_version':None,'observed_settings':{}}))\n",
        encoding="utf-8",
    )
    result = run_inference(local_request, CommandAdapter((sys.executable, str(adapter))), ROOT)
    assert result.run.status == "completed" and result.run.raw_response == "SYNTHETIC ONLY"
    request_path, output = tmp_path / "request.json", tmp_path / "cli-attempt.json"
    request_path.write_text(canonical_json(local_request), "utf-8")
    assert (
        main(
            [
                "research",
                "infer-local",
                str(request_path),
                "--output",
                str(output),
                "--adapter-command",
                sys.executable,
                str(adapter),
            ]
        )
        == 0
    )
    assert output.exists()
    assert (
        main(
            [
                "research",
                "infer-local",
                str(request_path),
                "--output",
                str(output),
                "--adapter-command",
                sys.executable,
                str(adapter),
            ]
        )
        == 1
    )
