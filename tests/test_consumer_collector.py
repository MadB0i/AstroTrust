"""Synthetic consumer evidence only; tests never collect service outputs."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest
from pydantic import ValidationError

from astrotrust.__main__ import main
from astrotrust.benchmark.prompts import digest
from astrotrust.collector import consumer_exports as exports
from astrotrust.collector.consumer_models import (
    PROMPTS,
    ConsumerMetadata,
    ConsumerRequest,
    ConsumerRun,
)
from astrotrust.collector.consumer_profiles import PROFILE_VERSION, PROFILES, profile_digest
from astrotrust.collector.consumer_service import ConsumerCollector
from astrotrust.collector.consumer_store import ConsumerStore
from astrotrust.collector.exports import load_jsonl as load_general_jsonl
from astrotrust.collector.store import DuplicateCapture, RunStore

ROOT = Path(__file__).resolve().parents[1]
RAW = (
    "  [Synthetic consumer sentinel]\r\nশিৰোনাম / शीर्षक\n`````\n"
    "<script>window.UNSAFE=true</script>\n \t"
)


def metadata(**changes: object) -> ConsumerMetadata:
    return ConsumerMetadata.model_validate(
        {
            "source_category": "consumer_astrology_service",
            "service_name": "  Synthetic exact service / v?  ",
            "access_method": "web",
            "cost": "unknown",
            "ai_generated_claimed": "unknown",
            "human_involvement_claimed": "unknown",
            "response_type": "unknown",
            "personal_fields_requested": ["DOB", "birth time", "birthplace", "gender"],
            "run_number": 1,
            "timestamp": "2026-10-05T20:30:00+05:30",
            "timezone": "Asia/Calcutta (UTC+05:30)",
            "response_complete": "unknown",
            "visibly_truncated": "unknown",
            "asked_more_information": "no",
            "refusal_or_avoidance": "no",
            "capture_note": "A fixed fictional profile was used.",
        }
        | changes
    )


def request(**changes: object) -> ConsumerRequest:
    return ConsumerRequest.model_validate(
        {
            "prompt_id": "consumer-career-p1",
            "registry_prompt_sha256": digest(PROMPTS["consumer-career-p1"]),
            "exact_prompt": PROMPTS["consumer-career-p1"],
            "raw_response": RAW,
            "metadata": metadata(),
            "profile_id": "consumer-profile-001",
            "profile_version": PROFILE_VERSION,
            "profile_sha256": profile_digest(PROFILES["consumer-profile-001"]),
            "profile_fields_submitted": ["date_of_birth", "birth_time", "birthplace", "timezone"],
            "gender_required": False,
            "interaction_mode": "prompt_and_fixed_profile_only",
            "interaction_record_type": "not_applicable",
            "exact_interaction": None,
        }
        | changes
    )


@pytest.fixture
def collector(tmp_path: Path) -> ConsumerCollector:
    return ConsumerCollector(ROOT, ConsumerStore(tmp_path / "consumer.sqlite3"))


@pytest.mark.parametrize(
    "raw", [RAW, "", " \r\n\t", "=SYNTHETIC()", "'Synthetic", "@Synthetic", "\u2028\u0085\u2029"]
)
def test_lossless_storage_and_exports(collector: ConsumerCollector, raw: str) -> None:
    exact = PROMPTS["consumer-career-p1"] + "\r\n  Synthetic deviation\t"
    run = collector.save(
        request(raw_response=raw, exact_prompt=exact, protocol_deviation="Synthetic deviation")
    )
    runs = (run,)
    assert ConsumerStore(collector.store.path).get(run.run_id) == run
    assert run.raw_response == raw and run.exact_prompt == exact
    assert run.response_sha256 == digest(raw) and run.prompt_sha256 == digest(exact)
    assert run.source_category == run.metadata.source_category == "consumer_astrology_service"
    assert run.metadata.service_name == "  Synthetic exact service / v?  "
    assert exports.load_jsonl(exports.jsonl(runs)) == runs
    assert exports.load_csv(exports.csv_export(runs)) == runs
    assert exports.jsonl(runs).count("\n") == 1
    for report in (exports.markdown_report(runs), exports.single_report(run)):
        assert raw in report and exact in report
        assert run.metadata.service_name in report and run.response_sha256 in report
        # Markdown includes a complete JSON record for exact reconstruction.
        lines = [line for line in report.split("\n") if line.startswith('{"code_revision"')]
        assert any(ConsumerRun.model_validate_json(line) == run for line in lines)
    with pytest.raises(ValueError):
        load_general_jsonl(exports.jsonl(runs))


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_category", "general_purpose_llm"),
        ("service_name", " "),
        ("access_method", "mobile_app"),
        ("cost", "premium"),
        ("ai_generated_claimed", "probably"),
        ("human_involvement_claimed", "probably"),
        ("response_type", "prediction"),
        ("run_number", 0),
        ("run_number", True),
        ("run_number", "1"),
        ("timestamp", "2026-10-05T20:30:00"),
        ("timestamp", "invalid"),
        ("timezone", " "),
        ("response_complete", "partially"),
        ("visibly_truncated", "partially"),
        ("asked_more_information", "unknown"),
        ("refusal_or_avoidance", "unknown"),
        ("observed_model_label", " "),
        ("account_credentials", "forbidden"),
    ],
)
def test_metadata_validation(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        metadata(**{field: value})


@pytest.mark.parametrize(
    "value",
    [
        ["DOB: 1990-01-01"],
        ["1990-01-01"],
        ["birth time = 08:30"],
        ["birthplace: Delhi"],
        ["example@example.org"],
        ["DOB", "DOB"],
        {"DOB": "1990-01-01"},
        ["api_key=synthetic"],
    ],
)
def test_personal_fields_allow_names_only(value: object) -> None:
    with pytest.raises(ValidationError):
        metadata(personal_fields_requested=value)
    assert metadata(personal_fields_requested=[]).personal_fields_requested == ()


@pytest.mark.parametrize(
    "field",
    [
        "service_name",
        "access_method",
        "cost",
        "ai_generated_claimed",
        "human_involvement_claimed",
        "response_type",
        "personal_fields_requested",
        "timestamp",
        "timezone",
        "run_number",
        "response_complete",
        "visibly_truncated",
        "asked_more_information",
        "refusal_or_avoidance",
        "source_category",
    ],
)
def test_required_metadata(field: str) -> None:
    values = metadata().model_dump()
    del values[field]
    with pytest.raises(ValidationError):
        ConsumerMetadata.model_validate(values)


def test_allowed_access_cost_types_and_repeat(collector: ConsumerCollector) -> None:
    for access in ("web", "iOS", "Android", "desktop", "other"):
        assert metadata(access_method=access).access_method == access
    for cost in ("free", "free_trial", "paid", "unknown"):
        assert metadata(cost=cost).cost == cost
    assert metadata(response_type="other").response_type == "other"
    assert metadata(run_number=4, repeat_identity="synthetic-session-4").run_number == 4


def test_duplicate_atomic_import_revisions_and_conflicts(
    collector: ConsumerCollector, tmp_path: Path
) -> None:
    first = collector.save(request())
    original_bytes = collector.store.path.read_bytes()
    with pytest.raises(DuplicateCapture):
        collector.save(request(raw_response="Different synthetic raw text"))
    assert collector.store.path.read_bytes() == original_bytes
    second = collector.save(request(metadata=metadata(run_number=2)))
    revised = collector.store.correct(
        first.run_id, metadata(cost="free_trial"), "Synthetic correction", 1
    )
    assert len(revised.history) == 2
    assert revised.history[0].metadata.cost == "unknown"
    assert revised.metadata.cost == "free_trial"
    assert (
        revised.raw_response,
        revised.exact_prompt,
        revised.response_sha256,
        revised.prompt_sha256,
    ) == (
        first.raw_response,
        first.exact_prompt,
        first.response_sha256,
        first.prompt_sha256,
    )
    with collector.store._connect() as db:
        record = db.execute(
            "SELECT record FROM consumer_snapshots WHERE run_id=? AND revision=1", (first.run_id,)
        ).fetchone()
    assert ConsumerRun.model_validate_json(record[0]) == first
    with pytest.raises(ValueError, match="Record changed"):
        collector.store.correct(first.run_id, metadata(), "Stale", 1)
    with pytest.raises(DuplicateCapture):
        collector.store.correct(first.run_id, metadata(run_number=2), "Conflict", 2)
    assert collector.store.get(first.run_id) == revised
    clean = ConsumerStore(tmp_path / "import.sqlite3")
    with pytest.raises(DuplicateCapture):
        clean.insert_many((revised, second, revised))
    assert clean.all() == ()
    clean.insert_many(exports.load_jsonl(exports.jsonl((revised, second))))
    assert clean.get(first.run_id) == revised


@pytest.mark.parametrize(
    "field,value",
    [
        ("raw_response", "tampered"),
        ("exact_prompt", "tampered"),
        ("response_sha256", "0" * 64),
        ("registry_prompt", "tampered"),
        ("registry_prompt_sha256", "0" * 64),
        ("schema_version", "manual-1.0"),
        ("source_category", "general_purpose_llm"),
        ("history", []),
        ("registry_version", "unknown"),
        ("research_status", "validated"),
    ],
)
def test_import_corruption(collector: ConsumerCollector, field: str, value: object) -> None:
    run = collector.save(request())
    with pytest.raises(ValidationError):
        ConsumerRun.model_validate(run.model_dump() | {field: value})


def test_registry_prompt_ids_hashes_and_deviation(collector: ConsumerCollector) -> None:
    for key, text in PROMPTS.items():
        run = collector.save(
            request(prompt_id=key, exact_prompt=text, registry_prompt_sha256=digest(text))
        )
        assert run.registry_prompt == text and run.prompt_sha256 == digest(text)
    with pytest.raises(ValueError, match="stale"):
        collector.save(request(registry_prompt_sha256="0" * 64))
    with pytest.raises(ValidationError, match="deviation"):
        collector.save(
            request(exact_prompt="Changed synthetic prompt", metadata=metadata(run_number=2))
        )
    with pytest.raises(ValidationError):
        request(prompt_id="atb-career-001")


def test_exports_reject_tampering_and_duplicates(collector: ConsumerCollector) -> None:
    run = collector.save(request())
    with pytest.raises(ValueError, match="Duplicate"):
        exports.load_jsonl(exports.jsonl((run,)) * 2)
    with pytest.raises(ValueError, match="Duplicate key"):
        exports.load_jsonl('{"kind":"consumer_astrology_capture","kind":"duplicate"}')
    with pytest.raises(ValueError, match="Nonstandard"):
        exports.load_jsonl('{"kind":NaN}')
    rows = list(csv.DictReader(io.StringIO(exports.csv_export((run,)), newline="")))
    rows[0]["metadata_service_name"] = "tampered"
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    with pytest.raises(ValueError, match="flattened"):
        exports.load_csv(output.getvalue())


def test_workflow_database_guards_preserve_bytes(tmp_path: Path) -> None:
    general_path, consumer_path = tmp_path / "general.sqlite3", tmp_path / "consumer.sqlite3"
    RunStore(general_path)
    ConsumerStore(consumer_path)
    before = {p: p.read_bytes() for p in (general_path, consumer_path)}
    with pytest.raises(ValueError, match="separate"):
        ConsumerStore(general_path)
    with pytest.raises(ValueError, match="separate"):
        RunStore(consumer_path)
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_cli_roundtrip_and_no_overwrite(collector: ConsumerCollector, tmp_path: Path) -> None:
    run = collector.save(request())
    output = tmp_path / "consumer.jsonl"
    args = ["collect-consumer", "--database", str(collector.store.path)]
    assert main(args + ["export", "--format", "jsonl", "--output", str(output)]) == 0
    assert main(["collect-consumer", "validate", str(output)]) == 0
    assert main(["collect", "validate", str(output)]) == 1
    assert main(args + ["export", "--format", "jsonl", "--output", str(output)]) == 1
    target = tmp_path / "import.sqlite3"
    assert main(["collect-consumer", "--database", str(target), "import", str(output)]) == 0
    assert ConsumerStore(target).get(run.run_id) == run
    for format, suffix in (("markdown", "md"), ("csv", "csv")):
        assert (
            main(
                args
                + ["export", "--format", format, "--output", str(tmp_path / f"consumer.{suffix}")]
            )
            == 0
        )
    assert exports.load_export(tmp_path / "consumer.csv") == (run,)
    with pytest.raises(ValueError, match="Markdown"):
        exports.load_export(tmp_path / "consumer.md")


def test_fixed_fictional_registry_and_snapshot(collector: ConsumerCollector) -> None:
    profile = PROFILES["consumer-profile-001"]
    assert profile.date_of_birth == "1998-02-12"
    assert profile.birth_time == "10:30"
    assert profile.birthplace == "Guwahati, Assam, India"
    assert profile.timezone == "Asia/Kolkata"
    assert profile.gender == "male" and profile.gender_use == "only_when_service_requires_gender"
    assert profile.profile_version == "consumer-profile-1.0"
    assert "FICTIONAL / SYNTHETIC RESEARCH INPUT" in profile.research_input_label
    assert "NOT PARTICIPANT DATA" in profile.research_input_label
    assert (
        profile_digest(profile)
        == "b2ddf58dbcd59a43a3b111efe242b0067c04d4bac3096b26d7e91fc6032a31ef"
    )
    run = collector.save(request())
    assert run.schema_version == "consumer-1.1"
    assert run.profile_snapshot == profile and run.profile_sha256 == profile_digest(profile)
    assert "gender" not in run.profile_fields_submitted
    assert "gender" in run.metadata.personal_fields_requested
    # Requested labels and submitted registry keys represent different observations.
    assert "DOB" in run.metadata.personal_fields_requested
    assert "date_of_birth" in run.profile_fields_submitted
    assert exports.load_csv(exports.csv_export((run,))) == (run,)
    assert exports.load_jsonl(exports.jsonl((run,))) == (run,)


def test_explicit_not_used_has_no_snapshot(collector: ConsumerCollector) -> None:
    run = collector.save(
        request(
            profile_id="not_used",
            profile_version=None,
            profile_sha256=None,
            profile_fields_submitted=[],
            interaction_mode="initial_prompt_only",
            metadata=metadata(
                personal_fields_requested=[], capture_note="Synthetic no-profile capture"
            ),
        )
    )
    assert run.profile_id == "not_used" and run.profile_snapshot is None
    assert run.profile_sha256 is None and run.profile_version is None
    assert run.profile_fields_submitted == ()
    assert exports.load_jsonl(exports.jsonl((run,))) == (run,)
    assert exports.load_csv(exports.csv_export((run,))) == (run,)


@pytest.mark.parametrize(
    "changes",
    [
        {"profile_id": "real-profile"},
        {"profile_id": "none"},
        {"profile_id": "not_used"},
        {"profile_fields_submitted": []},
        {"profile_fields_submitted": ["date_of_birth", "date_of_birth"]},
        {"profile_fields_submitted": ["1998-02-12"]},
        {"profile_fields_submitted": ["date_of_birth=2000-01-01"]},
        {"profile_fields_submitted": ["gender"]},
        {"profile_version": None},
        {"profile_version": "consumer-profile-9.0"},
        {"profile_sha256": None},
        {"profile_sha256": "0" * 64},
        {"date_of_birth": "2000-01-01"},
        {"birth_time": "12:00"},
        {"profile_snapshot": {"date_of_birth": "2000-01-01"}},
        {"gender_required": "yes"},
    ],
)
def test_reject_custom_or_inconsistent_profile_inputs(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        request(**changes)


@pytest.mark.parametrize(
    "field",
    [
        "profile_id",
        "profile_version",
        "profile_sha256",
        "profile_fields_submitted",
        "gender_required",
        "interaction_mode",
        "interaction_record_type",
        "exact_interaction",
    ],
)
def test_explicit_profile_and_interaction_choices_required(field: str) -> None:
    values = request().model_dump()
    del values[field]
    with pytest.raises(ValidationError):
        ConsumerRequest.model_validate(values)


def test_gender_only_when_required(collector: ConsumerCollector) -> None:
    run = collector.save(request(profile_fields_submitted=["gender"], gender_required=True))
    assert run.profile_snapshot is not None and run.profile_snapshot.gender == "male"
    assert run.profile_fields_submitted == ("gender",)
    with pytest.raises(ValidationError, match="originally requested"):
        collector.save(
            request(
                profile_fields_submitted=["gender"],
                gender_required=True,
                metadata=metadata(run_number=2, personal_fields_requested=[]),
            )
        )
    # 'sex' is an allowed observed requested label; supplied registry field remains 'gender'.
    sex_label = collector.save(
        request(
            profile_fields_submitted=["gender"],
            gender_required=True,
            metadata=metadata(run_number=2, personal_fields_requested=["sex"]),
        )
    )
    assert sex_label.profile_fields_submitted == ("gender",)


@pytest.mark.parametrize(
    "mode,kind",
    [
        ("multi_step", "transcript"),
        ("multi_step", "protocol_note"),
        ("unknown", "transcript"),
        ("unknown", "protocol_note"),
    ],
)
def test_exact_interaction_hash_roundtrips(
    collector: ConsumerCollector,
    mode: str,
    kind: str,
) -> None:
    interaction = (
        "  [Synthetic protocol sentinel]\r\nSERVICE: Which fictional city?\r\n"
        "RESEARCHER: Guwahati, Assam, India\n`````\n<script>window.UNSAFE=true</script>\r\n \t"
    )
    run = collector.save(
        request(
            interaction_mode=mode,
            interaction_record_type=kind,
            exact_interaction=interaction,
        )
    )
    assert run.exact_interaction == interaction and run.interaction_sha256 == digest(interaction)
    assert exports.load_jsonl(exports.jsonl((run,))) == (run,)
    assert exports.load_csv(exports.csv_export((run,))) == (run,)
    report = exports.single_report(run)
    assert interaction in report and "do not attribute" in report
    assert run.interaction_sha256 is not None and run.profile_sha256 is not None
    assert run.interaction_sha256 in report and run.profile_sha256 in report
    assert "Exact initial submitted prompt" in report
    assert "NOT PARTICIPANT DATA" in report


@pytest.mark.parametrize(
    "changes",
    [
        {"interaction_mode": "multi_step"},
        {"interaction_mode": "unknown"},
        {"interaction_record_type": "transcript"},
        {"exact_interaction": "Unacknowledged additional steps"},
        {
            "interaction_mode": "multi_step",
            "interaction_record_type": "transcript",
            "exact_interaction": " ",
        },
        {"interaction_mode": "multi_step", "exact_interaction": "Exact note"},
        {"interaction_mode": "invented"},
        {"interaction_mode": "initial_prompt_only"},
    ],
)
def test_cannot_hide_or_omit_interaction_provenance(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        request(**changes)


def test_profile_and_interaction_evidence_cannot_be_revised(collector: ConsumerCollector) -> None:
    first = collector.save(
        request(
            interaction_mode="multi_step",
            interaction_record_type="protocol_note",
            exact_interaction="  Synthetic exact protocol note\r\n ",
        )
    )
    revised = collector.store.correct(
        first.run_id,
        metadata(cost="paid"),
        "Synthetic metadata correction",
        1,
    )
    assert first.profile_snapshot is not None
    for field in (
        "profile_id",
        "profile_version",
        "profile_snapshot",
        "profile_sha256",
        "profile_fields_submitted",
        "gender_required",
        "interaction_mode",
        "interaction_record_type",
        "exact_interaction",
        "interaction_sha256",
    ):
        assert getattr(first, field) == getattr(revised, field)
    for changed in (
        {"profile_snapshot": None},
        {"profile_sha256": "0" * 64},
        {"exact_interaction": "tampered"},
        {"interaction_sha256": "0" * 64},
        {"schema_version": "consumer-1.0"},
        {"profile_snapshot": first.profile_snapshot.model_dump() | {"date_of_birth": "2000-01-01"}},
    ):
        with pytest.raises(ValidationError):
            ConsumerRun.model_validate(first.model_dump() | changed)
    with pytest.raises(DuplicateCapture):
        collector.save(
            request(
                profile_id="not_used",
                profile_version=None,
                profile_sha256=None,
                profile_fields_submitted=[],
                interaction_mode="initial_prompt_only",
            )
        )
