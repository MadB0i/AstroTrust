"""Merge completed coder CSV sheets into AnnotationBatch JSON and compute Cohen's kappa.

Converts completed CSV rows (`rater02_coding_sheet.csv` and `rater01_coding_sheet.csv`,
or optional `--use-disk-rater1` for `decision_reliance` on already-audited runs) into a
schema-valid `AnnotationBatch` at `data/private/annotations/independent.json`, then runs:
  1. `astrotrust annotations validate`
  2. `astrotrust annotations agreement` (linear-weighted kappa on `decision_reliance`)
  3. `astrotrust annotations agreement` (nominal kappa on `epistemic_framing`)
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, get_args

from astrotrust.annotations.agreement import AgreementReport, batch_agreement
from astrotrust.annotations.models import (
    RUBRIC_VERSION,
    AnnotationBatch,
    EvidenceSpan,
    FieldSupport,
    ResponseAnnotation,
    ResponseField,
    ResponseLabels,
    ResponseRef,
    condition_id,
    reference_from_run,
)
from astrotrust.benchmark.models import Condition, ModelRun, PromptTemplate, Scenario
from astrotrust.benchmark.prompts import digest
from astrotrust.validation.files import canonical_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KEY = ROOT / "reviews" / "generated" / "blind_coder_key_PRIVATE.json"
DEFAULT_PACKET = ROOT / "reviews" / "generated" / "blind_second_coder_packet.json"
DEFAULT_R2_CSV = ROOT / "reviews" / "generated" / "rater02_coding_sheet.csv"
DEFAULT_R1_CSV = ROOT / "reviews" / "generated" / "rater01_coding_sheet.csv"
DEFAULT_OUT_JSON = ROOT / "data" / "private" / "annotations" / "independent.json"

LOCAL_DIR = ROOT / "data" / "runs" / "local"
FRONTIER_JSONL = ROOT / "data" / "pilot" / "exports" / "pilot-2026-10-05.jsonl"
CONSUMER_DB = ROOT / "data" / "pilot" / "consumer-app-runs" / "collector.sqlite3"
CAREER_SCENARIO = ROOT / "benchmark" / "scenarios" / "atb-career-001.json"
CONTROLLED_TEMPLATE = ROOT / "benchmark" / "prompts" / "controlled-v1.json"
HELDOUT_JSONL = ROOT / "data" / "astroguard" / "heldout_unseen_labeled.jsonl"
ALL_LABELED_JSONL = ROOT / "data" / "astroguard" / "all_labeled.jsonl"


def _load_source_refs_and_texts() -> tuple[dict[str, ResponseRef], dict[str, str]]:
    """Build exact `ResponseRef` provenance records across local, frontier, and consumer runs."""
    refs: dict[str, ResponseRef] = {}
    texts: dict[str, str] = {}

    if LOCAL_DIR.is_dir():
        for path in sorted(LOCAL_DIR.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            run = ModelRun.model_validate(payload["run"])
            refs[path.stem] = reference_from_run(run)
            texts[path.stem] = run.raw_response or ""

    if FRONTIER_JSONL.is_file():
        for line in FRONTIER_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            cp = rec["canonical_prompt"]
            cond = Condition.model_validate(cp["condition"])
            run_id = str(rec["run_id"])
            resp_sha = str(rec["response_sha256"])
            refs[run_id] = ResponseRef(
                scenario_id=str(cp["scenario_id"]),
                scenario_revision=int(cp["scenario_revision"]),
                scenario_sha256=str(cp["scenario_sha256"]),
                template_sha256=str(cp["template_sha256"]),
                messages_sha256=str(cp["messages_sha256"]),
                run_id=run_id,
                response_id=f"resp-{resp_sha[:16]}",
                condition=cond,
                condition_id=condition_id(cond),
            )
            texts[run_id] = str(rec.get("raw_response") or "")

    if CONSUMER_DB.is_file() and CAREER_SCENARIO.is_file() and CONTROLLED_TEMPLATE.is_file():
        scenario = Scenario.model_validate(json.loads(CAREER_SCENARIO.read_text(encoding="utf-8")))
        template = PromptTemplate.model_validate(
            json.loads(CONTROLLED_TEMPLATE.read_text(encoding="utf-8"))
        )
        scen_sha = digest(canonical_json(scenario))
        tmpl_sha = digest(canonical_json(template))
        cond = Condition(
            belief="neutral", emotion="neutral", personalization="generic", language="en"
        )
        cond_str = condition_id(cond)

        conn = sqlite3.connect(CONSUMER_DB)
        rows = conn.execute(
            "SELECT run_id, revision, record FROM consumer_snapshots ORDER BY run_id, revision"
        ).fetchall()
        conn.close()
        latest: dict[str, tuple[int, dict[str, Any]]] = {}
        for rid, rev, raw in rows:
            rec = json.loads(raw)
            if rid not in latest or int(rev) > latest[rid][0]:
                latest[rid] = (int(rev), rec)

        for rid, (_, rec) in latest.items():
            resp_sha = str(rec["response_sha256"])
            refs[rid] = ResponseRef(
                scenario_id=scenario.scenario_id,
                scenario_revision=scenario.revision,
                scenario_sha256=scen_sha,
                template_sha256=tmpl_sha,
                messages_sha256=str(rec["prompt_sha256"]),
                run_id=rid,
                response_id=f"resp-{resp_sha[:16]}",
                condition=cond,
                condition_id=cond_str,
            )
            texts[rid] = str(rec.get("raw_response") or "")

    return refs, texts


def _load_disk_rater1_reliance() -> dict[str, tuple[str, str, str]]:
    """Load existing researcher-audited/baseline ADRS labels for rater-01 decision_reliance."""
    out: dict[str, tuple[str, str, str]] = {}
    for path in (ALL_LABELED_JSONL, HELDOUT_JSONL):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rid = str(row["run_id"])
            adrs = str(row["target"]["adrs_tier"])
            quote = str(row.get("evidence_quote") or "")
            note = str(row.get("audit_note") or row.get("annotation_basis") or "disk_audit")
            out[rid] = (adrs, quote, note)
    return out


def _read_csv_rows(csv_path: Path) -> dict[str, dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            bid = (row.get("blind_id") or "").strip()
            if bid:
                rows[bid] = {k: (v or "").strip() for k, v in row.items()}
        return rows


def _norm_uncertainty(raw_val: str) -> str:
    low = raw_val.strip().lower()
    if low in ("", "clear"):
        return "clear"
    if low == "unratable":
        return "unratable"
    return "uncertain"


def _build_annotation(
    *,
    annotator_id: str,
    blind_id: str,
    ref: ResponseRef,
    raw_response: str,
    decision_reliance: str,
    epistemic_framing: str,
    practical_grounding: str,
    evidence_quote: str,
    uncertainty_raw: str,
    notes: str,
    timestamp_iso: str,
) -> ResponseAnnotation:
    if not decision_reliance:
        raise ValueError(f"{annotator_id} missing decision_reliance for {blind_id}")
    framing_val = epistemic_framing or "unclear"
    grounding_val = practical_grounding or "unclear"
    uncertainty = _norm_uncertainty(uncertainty_raw)
    if decision_reliance == "unclear" or framing_val == "unclear":
        if uncertainty == "clear":
            uncertainty = "uncertain"
    needs_adj = uncertainty != "clear"

    spans: tuple[EvidenceSpan, ...] = ()
    if evidence_quote and evidence_quote in raw_response:
        start = raw_response.index(evidence_quote)
        spans = (
            EvidenceSpan(
                response_id=ref.response_id,
                start=start,
                end=start + len(evidence_quote),
                excerpt=evidence_quote,
            ),
        )

    belief_rel = "not_applicable" if ref.condition.belief == "neutral" else "unclear"
    labels = ResponseLabels(
        astrological_claim="unclear",
        belief_relationship=belief_rel,
        epistemic_framing=framing_val,
        practical_grounding=grounding_val,
        decision_reliance=decision_reliance,
        reliance_stance="unclear",
        prediction_uncertainty="unclear",
        action_recommendation="unclear",
        emotional_affirmation="unclear",
        acknowledgment_without_endorsement="unclear",
        guidance_displacement="unclear",
    )

    reason_base = notes or f"Human CSV coding ({blind_id}); secondary fields left unclear."
    support: dict[ResponseField, FieldSupport] = {}
    for field in get_args(ResponseField):
        if field in ("decision_reliance", "epistemic_framing", "practical_grounding") and spans:
            support[field] = FieldSupport(evidence=spans, reason=reason_base)
        elif field == "belief_relationship" and belief_rel == "not_applicable":
            support[field] = FieldSupport(evidence=(), reason="Neutral prior condition.")
        else:
            support[field] = FieldSupport(evidence=(), reason=reason_base)

    rater_slug = annotator_id.replace("-", "")
    return ResponseAnnotation(
        schema_version="1.0",
        annotation_id=f"ann-{rater_slug}-{blind_id}",
        annotator_id=annotator_id,
        rubric_version=RUBRIC_VERSION,
        timestamp=datetime.fromisoformat(timestamp_iso),
        annotation_uncertainty=uncertainty,
        needs_adjudication=needs_adj,
        rationale=reason_base,
        kind="response",
        target=ref,
        labels=labels,
        support=support,
    )


def merge_and_score(
    *,
    key_path: Path = DEFAULT_KEY,
    rater2_csv: Path = DEFAULT_R2_CSV,
    rater1_csv: Path | None = None,
    use_disk_rater1: bool = False,
    out_path: Path = DEFAULT_OUT_JSON,
    timestamp_iso: str | None = None,
) -> tuple[AnnotationBatch, dict[str, Any]]:
    """Merge coder CSVs into an AnnotationBatch JSON and compute Cohen's kappa."""
    key_data = json.loads(key_path.read_text(encoding="utf-8"))
    mapping: list[dict[str, str]] = list(key_data["mapping"])
    refs, texts = _load_source_refs_and_texts()
    r2_rows = _read_csv_rows(rater2_csv)

    r1_rows: dict[str, dict[str, str]] | None = None
    disk_r1: dict[str, tuple[str, str, str]] = {}
    if rater1_csv is not None and rater1_csv.is_file():
        r1_rows = _read_csv_rows(rater1_csv)
    elif use_disk_rater1:
        disk_r1 = _load_disk_rater1_reliance()
    else:
        raise ValueError(
            "Provide completed --rater1-csv (recommended for both decision_reliance and "
            "epistemic_framing) or pass --use-disk-rater1 for decision_reliance only."
        )

    ts = timestamp_iso or datetime.now().astimezone().isoformat(timespec="seconds")
    annotations: list[ResponseAnnotation] = []

    for entry in mapping:
        bid = entry["blind_id"]
        rid = entry["run_id"]
        if rid not in refs:
            raise KeyError(f"Source run not found for {bid}: {rid}")
        if bid not in r2_rows:
            raise KeyError(f"Missing {bid} in {rater2_csv}")

        ref = refs[rid]
        raw_resp = texts[rid]
        row2 = r2_rows[bid]
        annotations.append(
            _build_annotation(
                annotator_id="rater-02",
                blind_id=bid,
                ref=ref,
                raw_response=raw_resp,
                decision_reliance=row2.get("decision_reliance", ""),
                epistemic_framing=row2.get("epistemic_framing", ""),
                practical_grounding=row2.get("practical_grounding", ""),
                evidence_quote=row2.get("evidence_quote", ""),
                uncertainty_raw=row2.get("annotation_uncertainty", "clear"),
                notes=row2.get("notes", ""),
                timestamp_iso=ts,
            )
        )

        if r1_rows is not None:
            if bid not in r1_rows:
                raise KeyError(f"Missing {bid} in {rater1_csv}")
            row1 = r1_rows[bid]
            annotations.append(
                _build_annotation(
                    annotator_id="rater-01",
                    blind_id=bid,
                    ref=ref,
                    raw_response=raw_resp,
                    decision_reliance=row1.get("decision_reliance", ""),
                    epistemic_framing=row1.get("epistemic_framing", ""),
                    practical_grounding=row1.get("practical_grounding", ""),
                    evidence_quote=row1.get("evidence_quote", ""),
                    uncertainty_raw=row1.get("annotation_uncertainty", "clear"),
                    notes=row1.get("notes", ""),
                    timestamp_iso=ts,
                )
            )
        else:
            if rid not in disk_r1:
                raise KeyError(f"Disk rater-01 label missing for {rid}")
            adrs, quote, note = disk_r1[rid]
            annotations.append(
                _build_annotation(
                    annotator_id="rater-01",
                    blind_id=bid,
                    ref=ref,
                    raw_response=raw_resp,
                    decision_reliance=adrs,
                    epistemic_framing="unclear",
                    practical_grounding="unclear",
                    evidence_quote=quote,
                    uncertainty_raw="uncertain",
                    notes=f"Disk audited rater-01 ADRS ({note}); epistemic_framing not coded.",
                    timestamp_iso=ts,
                )
            )

    batch = AnnotationBatch(
        kind="annotation_batch",
        schema_version="1.0",
        purpose="research",
        annotations=tuple(annotations),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(canonical_json(batch), encoding="utf-8")

    rel_res = batch_agreement(
        batch,
        kind="response",
        field="decision_reliance",
        raters=("rater-01", "rater-02"),
        weights="linear",
    )
    fram_res = batch_agreement(
        batch,
        kind="response",
        field="epistemic_framing",
        raters=("rater-01", "rater-02"),
        weights="nominal",
    )

    batch_digest = digest(canonical_json(batch))
    reports = {
        "decision_reliance_linear": AgreementReport(
            schema_version="1.0",
            algorithm_version="agreement-1",
            input_sha256=batch_digest,
            rubric_version=RUBRIC_VERSION,
            annotation_level="response",
            field="decision_reliance",
            raters=("rater-01", "rater-02"),
            exclusion_policy=("incomparable", "not_applicable", "unclear", "overall_unratable"),
            result=rel_res,
        ).model_dump(mode="json"),
        "epistemic_framing_nominal": AgreementReport(
            schema_version="1.0",
            algorithm_version="agreement-1",
            input_sha256=batch_digest,
            rubric_version=RUBRIC_VERSION,
            annotation_level="response",
            field="epistemic_framing",
            raters=("rater-01", "rater-02"),
            exclusion_policy=("incomparable", "not_applicable", "unclear", "overall_unratable"),
            result=fram_res,
        ).model_dump(mode="json"),
    }
    return batch, reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--rater2-csv", type=Path, default=DEFAULT_R2_CSV)
    parser.add_argument(
        "--rater1-csv",
        type=Path,
        default=None,
        help="Completed rater-01 CSV sheet (defaults to checking --use-disk-rater1)",
    )
    parser.add_argument(
        "--use-disk-rater1",
        action="store_true",
        help="Use existing disk audited ADRS labels for rater-01 decision_reliance",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_JSON)
    args = parser.parse_args(argv)

    r1_csv = args.rater1_csv
    if r1_csv is None and not args.use_disk_rater1 and DEFAULT_R1_CSV.is_file():
        # Only auto-select rater01_coding_sheet.csv if the user actually filled labels in it.
        first_rows = _read_csv_rows(DEFAULT_R1_CSV)
        if first_rows and all(r.get("decision_reliance") for r in first_rows.values()):
            r1_csv = DEFAULT_R1_CSV

    batch, reports = merge_and_score(
        key_path=args.key,
        rater2_csv=args.rater2_csv,
        rater1_csv=r1_csv,
        use_disk_rater1=args.use_disk_rater1,
        out_path=args.out,
    )
    rel = reports["decision_reliance_linear"]["result"]
    fram = reports["epistemic_framing_nominal"]["result"]
    print(f"Validated AnnotationBatch ({len(batch.annotations)} records) -> {args.out}")
    print(
        f"decision_reliance (linear): n_used={rel['n_used']}/{rel['n_total']}, "
        f"agree={rel['percent_agreement']}%, kappa={rel['kappa']}"
    )
    print(
        f"epistemic_framing (nominal): n_used={fram['n_used']}/{fram['n_total']}, "
        f"agree={fram['percent_agreement']}%, kappa={fram['kappa']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
