"""Synthetic sentinels only; no collected or fabricated model responses."""

from __future__ import annotations

import csv
import io
import json
import subprocess
from collections.abc import Iterator
from http.client import HTTPConnection
from pathlib import Path
from threading import Thread

import pytest
from pydantic import ValidationError

from astrotrust.__main__ import main
from astrotrust.benchmark.models import Condition
from astrotrust.benchmark.prompts import belief_conditions, digest
from astrotrust.collector.exports import (
    csv_export,
    jsonl,
    load_csv,
    load_jsonl,
    markdown_report,
    single_report,
)
from astrotrust.collector.models import (
    STATUS,
    CaptureMetadata,
    CaptureRequest,
    ManualRun,
    ServiceMetadata,
)
from astrotrust.collector.server import CollectorServer, make_server
from astrotrust.collector.service import Collector, progress
from astrotrust.collector.store import DuplicateCapture, RunStore

ROOT = Path(__file__).resolve().parents[1]
RAW = (
    "  [Synthetic development response — not model output]\n\n"
    "## শিৰোনাম / शीर्षक\n- `item`\n`````\n<script>window.UNSAFE=true</script>\n \n"
)


@pytest.fixture
def collector(tmp_path: Path) -> Collector:
    return Collector(ROOT, RunStore(tmp_path / "pilot.sqlite3"))


def metadata(**changes: object) -> CaptureMetadata:
    return CaptureMetadata.model_validate(
        {
            "source_category": "general_purpose_llm",
            "service": None,
            "provider": "OpenAI",
            "product": "ChatGPT",
            "model_label": "  Synthetic UI label / v?  ",
            "access_method": "web",
            "account_tier": None,
            "special_mode": "unknown",
            "special_mode_detail": None,
            "browsing": "unknown",
            "memory": "unknown",
            "fresh_conversation": "yes",
            "run_number": 1,
            "timestamp": "2026-10-05T14:30:00+05:30",
            "timezone": "Asia/Calcutta (UTC+05:30)",
            "response_complete": "unknown",
            "asked_more_information": "no",
            "refusal_or_avoidance": "no",
            "web_sources": "unknown",
            "visibly_truncated": "unknown",
            "capture_note": "  Synthetic collection anomaly note  ",
        }
        | changes
    )


def request(collector: Collector, *, raw: str = RAW, **changes: object) -> CaptureRequest:
    p = collector.prompt("atb-career-001", Condition())
    return CaptureRequest.model_validate(
        {
            "scenario_id": p.scenario_id,
            "condition": p.condition,
            "canonical_prompt_sha256": digest(p.messages[0].content),
            "exact_prompt": p.messages[0].content,
            "protocol_deviation": None,
            "raw_response": raw,
            "metadata": metadata(),
        }
        | changes
    )


def test_exact_capture_hashes_versions_and_reopen(collector: Collector) -> None:
    run = collector.save(request(collector))
    saved = RunStore(collector.store.path).get(run.run_id)
    assert saved == run
    assert saved.raw_response == RAW
    assert saved.metadata.model_label == "  Synthetic UI label / v?  "
    assert saved.metadata.capture_note == "  Synthetic collection anomaly note  "
    assert saved.response_sha256 == digest(RAW)
    assert saved.prompt_sha256 == digest(saved.canonical_text)
    assert saved.exact_prompt == collector.prompt("atb-career-001", Condition()).messages[0].content
    assert saved.schema_version == "manual-1.0"
    assert saved.instrument_version == "instrument-v0.1"
    assert STATUS == saved.research_status


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider", "invalid"),
        ("run_number", "1"),
        ("run_number", True),
        ("run_number", 4),
        ("model_label", " "),
        ("timestamp", "2026-10-05T14:30:00"),
        ("timestamp", "invalid"),
        ("fresh_conversation", "unknown"),
        ("asked_more_information", "unknown"),
        ("special_mode", "other"),
        ("account_email", "not allowed"),
    ],
)
def test_invalid_metadata(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        metadata(**{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "model_label",
        "timestamp",
        "timezone",
        "provider",
        "product",
        "response_complete",
        "asked_more_information",
    ],
)
def test_missing_required_metadata(field: str) -> None:
    values = metadata().model_dump()
    del values[field]
    with pytest.raises(ValidationError, match=field):
        CaptureMetadata.model_validate(values)


def test_duplicate_atomic_import_and_distinct_repeats(collector: Collector) -> None:
    first = collector.save(request(collector))
    with pytest.raises(DuplicateCapture):
        collector.save(request(collector))
    second = collector.save(request(collector, metadata=metadata(run_number=2)))
    assert first.run_id != second.run_id
    third = ManualRun.model_validate(second.model_dump() | {"run_id": "manual-" + "a" * 32})
    other = ManualRun.model_validate(first.model_dump() | {"run_id": "manual-" + "b" * 32})
    clean = RunStore(collector.store.path.parent / "import.sqlite3")
    with pytest.raises(DuplicateCapture):
        clean.insert_many((third, second, other))
    assert clean.all() == ()


def test_revision_preserves_raw_original_and_conflict_protection(collector: Collector) -> None:
    first = collector.save(request(collector))
    revised = collector.store.correct(
        first.run_id, metadata(browsing="automatic"), "Synthetic correction reason", 1
    )
    assert revised.raw_response == first.raw_response
    assert revised.exact_prompt == first.exact_prompt
    assert revised.response_sha256 == first.response_sha256
    assert revised.history[0].metadata.browsing == "unknown"
    assert revised.metadata.browsing == "automatic"
    assert len(revised.history) == 2
    with pytest.raises(ValueError, match="Record changed"):
        collector.store.correct(first.run_id, metadata(), "Stale correction", 1)
    collector.save(request(collector, metadata=metadata(run_number=2)))
    with pytest.raises(DuplicateCapture):
        collector.store.correct(first.run_id, metadata(run_number=2), "Conflicting correction", 2)
    assert collector.store.get(first.run_id) == revised


def test_canonical_immutability_deviation_and_stale_hash(collector: Collector) -> None:
    before = (ROOT / "benchmark/prompts/controlled-v1.json").read_bytes()
    canonical = request(collector)
    changed = canonical.model_dump() | {"exact_prompt": canonical.exact_prompt + "\nModified text"}
    with pytest.raises(ValidationError, match="deviation"):
        collector.save(CaptureRequest.model_validate(changed))
    run = collector.save(
        CaptureRequest.model_validate(changed | {"protocol_deviation": "Synthetic deviation"})
    )
    assert run.canonical_text == canonical.exact_prompt
    assert run.exact_prompt != run.canonical_text
    with pytest.raises(ValueError, match="stale"):
        collector.save(request(collector, canonical_prompt_sha256="0" * 64))
    assert before == (ROOT / "benchmark/prompts/controlled-v1.json").read_bytes()


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "99"),
        ("response_sha256", "0" * 64),
        ("prompt_sha256", "0" * 64),
        ("canonical_text", "changed"),
        ("condition_id", "positive"),
        ("research_status", "Frozen benchmark"),
        ("unexpected", "field"),
        ("history", []),
    ],
)
def test_record_integrity_rejects_corruption(
    collector: Collector, field: str, value: object
) -> None:
    run = collector.save(request(collector))
    with pytest.raises(ValidationError):
        ManualRun.model_validate(run.model_dump() | {field: value})


@pytest.mark.parametrize(
    "raw",
    [
        RAW,
        "",
        " \r\n\t",
        "=SYNTHETIC()",
        "  =SYNTHETIC()",
        "'Synthetic",
        "@Synthetic",
        "[Synthetic development response — not model output]\u2028Unicode\u0085separator\u2029",
    ],
)
def test_jsonl_csv_lossless_roundtrip_and_complete_reports(collector: Collector, raw: str) -> None:
    run = collector.save(request(collector, raw=raw))
    runs = (run,)
    assert load_jsonl(jsonl(runs)) == runs
    assert load_csv(csv_export(runs)) == runs
    assert jsonl(runs) == jsonl(runs)
    assert jsonl(runs).count("\n") == 1
    for report in (markdown_report(runs), single_report(run)):
        assert STATUS in report and raw in report and run.exact_prompt in report
        assert run.response_sha256 in report and run.prompt_sha256 in report
        assert run.metadata.model_label in report
    if raw == RAW:
        assert "``````text" in single_report(run)
    rows = list(csv.DictReader(io.StringIO(csv_export(runs), newline="")))
    if raw.startswith("="):
        assert rows[0]["raw_response"] == "'" + raw
    rows[0]["metadata_model_label"] = "tampered"
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    with pytest.raises(ValueError, match="flattened fields"):
        load_csv(output.getvalue())


def test_import_rejects_duplicates_and_duplicate_json_keys(collector: Collector) -> None:
    run = collector.save(request(collector))
    with pytest.raises(ValueError, match="Duplicate run"):
        load_jsonl(jsonl((run,)) * 2)
    with pytest.raises(ValueError, match="Duplicate key"):
        load_jsonl('{"kind":"manual_frontend_run","kind":"duplicate"}')
    with pytest.raises(ValueError, match="Nonstandard JSON"):
        load_jsonl('{"unknown":NaN}')
    with pytest.raises(ValueError, match="collector CSV header"):
        load_csv('"wrong","header"\n')
    assert load_jsonl(jsonl(())) == ()
    assert load_csv(csv_export(())) == ()
    assert STATUS in csv_export(()) and STATUS in markdown_report(())


def test_zero_matrix_and_exact_label_separation(collector: Collector) -> None:
    baseline = Condition()
    empty = progress((), "atb-career-001", baseline)
    assert empty["planned_captures"] == 27 and empty["captured"] == 0
    groups = empty["groups"]
    assert isinstance(groups, list) and len(groups) == 3
    assert sum(len(cell["runs"]) for g in groups for cell in g["cells"]) == 27
    assert not any(done for g in groups for cell in g["cells"] for done in cell["runs"])
    collector.save(request(collector))
    collector.save(request(collector, metadata=metadata(model_label="Synthetic different label")))
    after = progress(collector.store.all(), "atb-career-001", baseline)
    assert after["captured"] == 2
    assert (
        progress(collector.store.all(), "atb-career-001", baseline, scenario_sha256="0" * 64)[
            "captured"
        ]
        == 0
    )
    assert isinstance(after["groups"], list) and len(after["groups"]) == 4
    assert (
        progress(collector.store.all(), "atb-career-001", Condition(emotion="distressed"))[
            "captured"
        ]
        == 0
    )


def test_existing_conditions_and_unavailable_languages(collector: Collector) -> None:
    for c in belief_conditions():
        assert collector.prompt("atb-career-001", c).condition == c
    for language in ("hi", "as", "zz"):
        with pytest.raises(ValueError):
            collector.prompt("atb-career-001", Condition.model_validate({"language": language}))
    with pytest.raises(ValidationError):
        request(collector, condition={"belief": "invented"})


def test_future_service_claims_not_backend_inference() -> None:
    service = ServiceMetadata(
        service_name="Synthetic unnamed service",
        ai_generated_claimed="unknown",
        human_involvement_claimed="unknown",
        cost="unknown",
        response_type="unknown",
        personal_fields_requested=("birth-date",),
    )
    m = metadata(source_category="consumer_astrology_service", provider="Other", service=service)
    assert m.service == service
    with pytest.raises(ValidationError):
        metadata(service=service)
    assert metadata(fresh_conversation="no").fresh_conversation == "no"


def test_cli_export_validate_import_and_ignored_data(collector: Collector, tmp_path: Path) -> None:
    collector.save(request(collector))
    output = tmp_path / "pilot.jsonl"
    args = ["collect", "--database", str(collector.store.path)]
    assert main(args + ["export", "--format", "jsonl", "--output", str(output)]) == 0
    assert main(["collect", "validate", str(output)]) == 0
    assert main(args + ["export", "--format", "jsonl", "--output", str(output)]) == 1
    target = tmp_path / "import.sqlite3"
    assert main(["collect", "--database", str(target), "import", str(output)]) == 0
    assert RunStore(target).all() == collector.store.all()
    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_bytes(b"Synthetic invalid database sentinel")
    assert (
        main(
            [
                "collect",
                "--database",
                str(corrupt),
                "export",
                "--format",
                "jsonl",
                "--output",
                str(tmp_path / "invalid.jsonl"),
            ]
        )
        == 1
    )
    assert (
        main(
            [
                "collect",
                "--root",
                str(ROOT),
                "--database",
                str(tmp_path / "invalid-port.sqlite3"),
                "--port",
                "65536",
            ]
        )
        == 1
    )
    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "data/pilot/manual-runs/collector.sqlite3",
            "data/pilot/exports/pilot.jsonl",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert len(ignored.stdout.splitlines()) == 2
    tracked = subprocess.run(
        ["git", "ls-files", "data/pilot"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert tracked.stdout == ""


@pytest.fixture
def server(tmp_path: Path) -> Iterator[CollectorServer]:
    with make_server(ROOT, tmp_path / "http.sqlite3", port=0) as instance:
        thread = Thread(target=instance.serve_forever, daemon=True)
        thread.start()
        try:
            yield instance
        finally:
            instance.shutdown()
            thread.join()


def http(
    server: CollectorServer,
    path: str,
    *,
    body: str | None = None,
    authorized: bool = True,
    origin: str | None = None,
    host: str | None = None,
) -> tuple[int, str]:
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    headers = {"Content-Type": "application/json"}
    if authorized:
        headers["X-Collector-Token"] = server.token
    if origin:
        headers["Origin"] = origin
    if host:
        headers["Host"] = host
    connection.request(
        "POST" if body is not None else "GET",
        path,
        body=body.encode("utf-8") if body is not None else None,
        headers=headers,
    )
    response = connection.getresponse()
    result = response.status, response.read().decode("utf-8")
    connection.close()
    return result


def test_loopback_security_and_http_capture(server: CollectorServer) -> None:
    assert server.server_address[0] == "127.0.0.1"
    assert http(server, "/")[0] == 200
    assert http(server, "/api/bootstrap", authorized=False)[0] == 403
    assert http(server, "/api/bootstrap", origin="https://foreign.example")[0] == 403
    assert http(server, "/", host="foreign.example")[0] == 403
    assert http(server, "/../pyproject.toml")[0] == 404
    assert http(server, "/api/export?format=jsonl")[0] == 400
    payload = request(server.collector).model_dump_json()
    code, response = http(server, "/api/runs", body=payload)
    assert code == 201
    run = ManualRun.model_validate(json.loads(response)["run"])
    assert run.raw_response == RAW
    assert http(server, "/api/runs", body=payload)[0] == 409
    assert http(server, "/api/runs", body='{"unexpected":true}')[0] == 400
    assert http(server, "/api/runs", body='{"metadata":{},"metadata":{}}')[0] == 400
    _, exported = http(server, "/api/export?format=jsonl")
    assert load_jsonl(exported) == (run,)
