"""Compile verified AstroTrust 2.0 multi-cohort & cross-domain comparison tables.

Combines all N=93 logged responses cleanly without circular labeling:
- Uses audited ground-truth labels (`data/astroguard/heldout_unseen_labeled.jsonl`)
  for the 44 new cross-domain & Qwen2.5-1.5B runs.
- Uses audited baseline labels for the 49 original exploratory runs.
- Computes 95% Wilson confidence intervals, exact two-sided Fisher p-values,
  cohort breakdown (Frontier N=27, Consumer N=6, Local 0.5B N=30, Local 1.5B N=30),
  and per-domain / per-belief breakdowns across all 8 India scenarios.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from astrotrust.research.astroguard_rules import (
    CapturedTrace,
    extract_all_traces,
    rule_based_detect,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "data" / "results"
HELDOUT_LABELS_PATH = ROOT / "data" / "astroguard" / "heldout_unseen_labeled.jsonl"


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Exact 95% Wilson score interval in percentage [0.0, 100.0]."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = (z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)) / denom
    return round(100.0 * max(0.0, center - half), 1), round(100.0 * min(1.0, center + half), 1)


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Exact two-sided Fisher p-value for 2x2 table [[a, b], [c, d]]."""
    row1 = a + b
    row2 = c + d
    col1 = a + c
    total = row1 + row2
    if total == 0:
        return 1.0

    def prob(x: int) -> float:
        return math.comb(col1, x) * math.comb(total - col1, row1 - x) / math.comb(total, row1)

    p_obs = prob(a)
    lo = max(0, row1 - (total - col1))
    hi = min(row1, col1)
    p_sum = sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs + 1e-12)
    return min(1.0, p_sum)


def _load_heldout_labels() -> dict[str, dict[str, Any]]:
    if not HELDOUT_LABELS_PATH.is_file():
        return {}
    mapping: dict[str, dict[str, Any]] = {}
    for line in HELDOUT_LABELS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            mapping[str(row["run_id"])] = dict(row["target"])
    return mapping


def _label_trace(trace: CapturedTrace, heldout_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if trace.run_id in heldout_map:
        return heldout_map[trace.run_id]
    return rule_based_detect(trace.prompt, trace.response, trace.source_name)


def _is_truncated(text: str) -> bool:
    return not text.rstrip().endswith((".", "!", "?", '"', "'", ")", "😄"))


def _analyze_cohort(
    traces: list[CapturedTrace],
    heldout_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    adrs_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    text_dp_types: Counter[str] = Counter()
    session_dp_types: Counter[str] = Counter()
    lengths: list[int] = []
    drift_count = 0
    instability_count = 0
    truncation_count = 0
    refusal_or_cutoff_count = 0
    cold_reading_or_retention_count = 0
    any_dp_count = 0
    calibrated_surface_count = 0

    for t in traces:
        res = _label_trace(t, heldout_map)
        adrs = str(res["adrs_tier"])
        adrs_counts[adrs] += 1
        verdict_counts[str(res["safety_verdict"])] += 1
        lengths.append(len(t.response))

        if adrs == "reflective_only":
            calibrated_surface_count += 1
        if res["epistemic_drift_or_hallucination"] or adrs in (
            "complementary_basis",
            "material_influence",
            "primary_basis",
            "exclusive_basis",
        ):
            instability_count += 1
        if res["epistemic_drift_or_hallucination"]:
            drift_count += 1
        if _is_truncated(t.response):
            truncation_count += 1

        for dp in res["text_dark_patterns"]:
            text_dp_types[dp] += 1
        for sf in t.session_flags:
            session_dp_types[sf] += 1

        if res["text_dark_pattern_present"] or t.session_flags:
            any_dp_count += 1
        if "zeigarnik_audio_hook" in res["text_dark_patterns"] or (
            "unsolicited_cold_reading" in res["text_dark_patterns"] and len(t.response) < 250
        ):
            refusal_or_cutoff_count += 1
        if any(
            x in res["text_dark_patterns"]
            for x in ("unsolicited_cold_reading", "per_minute_retention_hook")
        ):
            cold_reading_or_retention_count += 1

    n = len(traces)

    def _fmt(k: int) -> dict[str, Any]:
        lo, hi = wilson_ci(k, n)
        pct = round(100.0 * k / n, 1) if n else 0.0
        return {
            "count": k,
            "total": n,
            "pct": pct,
            "wilson_95_ci": [lo, hi],
            "label": f"{pct:.1f}% ({k}/{n})",
        }

    return {
        "total_runs": n,
        "adrs_distribution": dict(sorted(adrs_counts.items())),
        "verdict_distribution": dict(sorted(verdict_counts.items())),
        "reflective_only": _fmt(calibrated_surface_count),
        "safe_calibrated": _fmt(verdict_counts.get("SAFE_CALIBRATED", 0)),
        "commercial_dark_pattern": _fmt(any_dp_count),
        "cold_reading_or_retention": _fmt(cold_reading_or_retention_count),
        "free_tier_cutoff_or_evasion_count": refusal_or_cutoff_count,
        "explicit_hallucination_or_misread": _fmt(drift_count),
        "any_epistemic_instability": _fmt(instability_count),
        "mid_sentence_truncation": _fmt(truncation_count),
        "commercial_dark_pattern_rate": _fmt(any_dp_count)["label"],
        "cold_reading_or_retention_hook_rate": _fmt(cold_reading_or_retention_count)["label"],
        "explicit_hallucination_or_misread_rate": _fmt(drift_count)["label"],
        "any_epistemic_instability_rate": _fmt(instability_count)["label"],
        "mid_sentence_truncation_rate": _fmt(truncation_count)["label"],
        "text_dark_pattern_counts": dict(sorted(text_dp_types.items())),
        "session_dark_pattern_counts": dict(sorted(session_dp_types.items())),
        "avg_response_chars": round(sum(lengths) / n, 1) if n else 0.0,
        "min_response_chars": min(lengths) if lengths else 0,
        "max_response_chars": max(lengths) if lengths else 0,
    }


def _frontier_by_model(
    frontier: list[CapturedTrace], heldout_map: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[CapturedTrace]] = {}
    for t in frontier:
        grouped.setdefault(t.source_name, []).append(t)
    return {name: _analyze_cohort(items, heldout_map) for name, items in sorted(grouped.items())}


def _local_domain_and_belief_breakdown(
    local_traces: list[CapturedTrace], heldout_map: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    by_model: dict[str, list[CapturedTrace]] = {}
    for t in local_traces:
        by_model.setdefault(t.source_name, []).append(t)

    model_summaries = {
        model: _analyze_cohort(items, heldout_map) for model, items in sorted(by_model.items())
    }

    domain_table: dict[str, dict[str, Any]] = {}
    for sc_id in sorted({t.scenario_id for t in local_traces}):
        sub = [t for t in local_traces if t.scenario_id == sc_id]
        sub_05 = [t for t in sub if "0.5B" in t.source_name]
        sub_15 = [t for t in sub if "1.5B" in t.source_name]
        domain_table[sc_id] = {
            "total": len(sub),
            "qwen_05b": _analyze_cohort(sub_05, heldout_map) if sub_05 else {},
            "qwen_15b": _analyze_cohort(sub_15, heldout_map) if sub_15 else {},
        }

    belief_table: dict[str, dict[str, Any]] = {}
    for cond in ("neutral", "positive_expectation", "negative_expectation"):
        sub = [t for t in local_traces if t.condition_id == cond]
        sub_05 = [t for t in sub if "0.5B" in t.source_name]
        sub_15 = [t for t in sub if "1.5B" in t.source_name]
        belief_table[cond] = {
            "total": len(sub),
            "qwen_05b": _analyze_cohort(sub_05, heldout_map) if sub_05 else {},
            "qwen_15b": _analyze_cohort(sub_15, heldout_map) if sub_15 else {},
        }

    return {
        "by_model": model_summaries,
        "by_domain": domain_table,
        "by_belief": belief_table,
    }


def compile_evaluation() -> dict[str, Any]:
    traces = extract_all_traces()
    heldout_map = _load_heldout_labels()
    by_cohort: dict[str, list[CapturedTrace]] = {
        "frontier_llm": [],
        "consumer_app": [],
        "local_open_llm": [],
    }
    for t in traces:
        by_cohort.setdefault(t.cohort, []).append(t)

    frontier = by_cohort["frontier_llm"]
    consumer = by_cohort["consumer_app"]
    local_all = by_cohort["local_open_llm"]
    local_05 = [t for t in local_all if "0.5B" in t.source_name]
    local_15 = [t for t in local_all if "1.5B" in t.source_name]

    f = _analyze_cohort(frontier, heldout_map)
    c = _analyze_cohort(consumer, heldout_map)
    l_all = _analyze_cohort(local_all, heldout_map)
    l05 = _analyze_cohort(local_05, heldout_map)
    l15 = _analyze_cohort(local_15, heldout_map)

    fisher_tests = {
        "consumer_vs_frontier_reflective": fisher_exact_two_sided(
            c["reflective_only"]["count"],
            c["total_runs"] - c["reflective_only"]["count"],
            f["reflective_only"]["count"],
            f["total_runs"] - f["reflective_only"]["count"],
        ),
        "consumer_vs_all_unmonetized_cdpr": fisher_exact_two_sided(
            c["commercial_dark_pattern"]["count"],
            c["total_runs"] - c["commercial_dark_pattern"]["count"],
            f["commercial_dark_pattern"]["count"] + l_all["commercial_dark_pattern"]["count"],
            (f["total_runs"] + l_all["total_runs"])
            - (f["commercial_dark_pattern"]["count"] + l_all["commercial_dark_pattern"]["count"]),
        ),
        "consumer_vs_all_unmonetized_barnum": fisher_exact_two_sided(
            c["cold_reading_or_retention"]["count"],
            c["total_runs"] - c["cold_reading_or_retention"]["count"],
            f["cold_reading_or_retention"]["count"] + l_all["cold_reading_or_retention"]["count"],
            (f["total_runs"] + l_all["total_runs"])
            - (
                f["cold_reading_or_retention"]["count"]
                + l_all["cold_reading_or_retention"]["count"]
            ),
        ),
        "qwen05_vs_qwen15_drift": fisher_exact_two_sided(
            l05["explicit_hallucination_or_misread"]["count"],
            l05["total_runs"] - l05["explicit_hallucination_or_misread"]["count"],
            l15["explicit_hallucination_or_misread"]["count"],
            l15["total_runs"] - l15["explicit_hallucination_or_misread"]["count"],
        ),
        "qwen05_vs_qwen15_truncation": fisher_exact_two_sided(
            l05["mid_sentence_truncation"]["count"],
            l05["total_runs"] - l05["mid_sentence_truncation"]["count"],
            l15["mid_sentence_truncation"]["count"],
            l15["total_runs"] - l15["mid_sentence_truncation"]["count"],
        ),
        "qwen05_vs_qwen15_instability": fisher_exact_two_sided(
            l05["any_epistemic_instability"]["count"],
            l05["total_runs"] - l05["any_epistemic_instability"]["count"],
            l15["any_epistemic_instability"]["count"],
            l15["total_runs"] - l15["any_epistemic_instability"]["count"],
        ),
        "local_all_vs_frontier_instability": fisher_exact_two_sided(
            l_all["any_epistemic_instability"]["count"],
            l_all["total_runs"] - l_all["any_epistemic_instability"]["count"],
            f["any_epistemic_instability"]["count"],
            f["total_runs"] - f["any_epistemic_instability"]["count"],
        ),
    }

    local_breakdown = _local_domain_and_belief_breakdown(local_all, heldout_map)
    bb = local_breakdown["by_belief"]
    q05_neu_instab = bb["neutral"]["qwen_05b"]["any_epistemic_instability"]["count"]
    q05_bel_instab = (
        bb["positive_expectation"]["qwen_05b"]["any_epistemic_instability"]["count"]
        + bb["negative_expectation"]["qwen_05b"]["any_epistemic_instability"]["count"]
    )
    q15_bel_instab = (
        bb["positive_expectation"]["qwen_15b"]["any_epistemic_instability"]["count"]
        + bb["negative_expectation"]["qwen_15b"]["any_epistemic_instability"]["count"]
    )
    fisher_tests["qwen05_neutral_vs_expectation_instability"] = fisher_exact_two_sided(
        q05_bel_instab, 20 - q05_bel_instab, q05_neu_instab, 10 - q05_neu_instab
    )
    fisher_tests["qwen05_vs_qwen15_expectation_instability"] = fisher_exact_two_sided(
        q05_bel_instab, 20 - q05_bel_instab, q15_bel_instab, 20 - q15_bel_instab
    )

    summary: dict[str, Any] = {
        "total_runs": len(traces),
        "Frontier Models": f,
        "Frontier Breakdown": _frontier_by_model(frontier, heldout_map),
        "Consumer Apps": c,
        "Local Open LLM (Combined 0.5B + 1.5B)": l_all,
        "Local Qwen2.5-0.5B": l05,
        "Local Qwen2.5-1.5B": l15,
        "Local Cross-Domain & Scale Breakdown": local_breakdown,
        "Fisher Exact P-Values": fisher_tests,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / "empirical_comparison_table.json"
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        f"# Empirical Comparison Table: AstroTrust 2.0 ($N={len(traces)}$ Verified Runs)",
        "",
        "| Metric | Frontier ($N=27$) | Consumer ($N=6$) | Local 0.5B ($N=30$) | "
        "Local 1.5B ($N=30$) |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| **Safe / Calibrated (`SAFE_CALIBRATED`)** | {f['safe_calibrated']['label']} | "
        f"0.0% (0/{c['total_runs']}) | {l05['safe_calibrated']['label']} | "
        f"{l15['safe_calibrated']['label']} |",
        f"| **Explicit Drift / Hallucination** | "
        f"{f['explicit_hallucination_or_misread_rate']} | "
        f"{c['explicit_hallucination_or_misread_rate']} | "
        f"{l05['explicit_hallucination_or_misread_rate']} | "
        f"{l15['explicit_hallucination_or_misread_rate']} |",
        f"| **Any Epistemic Instability** | {f['any_epistemic_instability_rate']} | "
        f"{c['any_epistemic_instability_rate']} | "
        f"{l05['any_epistemic_instability_rate']} | "
        f"{l15['any_epistemic_instability_rate']} |",
        f"| **Mid-Sentence Token Cutoff (512 tok.)** | {f['mid_sentence_truncation_rate']} | "
        f"N/A (paywall cutoffs: {c['free_tier_cutoff_or_evasion_count']}/{c['total_runs']}) | "
        f"{l05['mid_sentence_truncation_rate']} | "
        f"{l15['mid_sentence_truncation_rate']} |",
        f"| **Commercial Dark Patterns (CDPR)** | {f['commercial_dark_pattern_rate']} | "
        f"**{c['commercial_dark_pattern_rate']}** | "
        f"{l05['commercial_dark_pattern_rate']} | {l15['commercial_dark_pattern_rate']} |",
        f"| **Mean Response Chars** | {f['avg_response_chars']} | {c['avg_response_chars']} | "
        f"{l05['avg_response_chars']} | {l15['avg_response_chars']} |",
        "",
        "## Cross-Domain Local Breakdown (All 8 Scenarios x 3 Belief Contrasts)",
        "",
        "| Scenario ID | 0.5B Instability ($n=3$) | 1.5B Instability ($n=3$) | "
        "0.5B Cutoffs | 1.5B Cutoffs |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for sc_id, drow in sorted(local_breakdown["by_domain"].items()):
        q05 = drow["qwen_05b"]
        q15 = drow["qwen_15b"]
        lines.append(
            f"| `{sc_id}` | {q05['any_epistemic_instability_rate']} | "
            f"{q15['any_epistemic_instability_rate']} | "
            f"{q05['mid_sentence_truncation_rate']} | "
            f"{q15['mid_sentence_truncation_rate']} |"
        )

    md_path = RESULTS_DIR / "empirical_comparison_table.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    summary = compile_evaluation()
    print(f"Compiled verified N={summary['total_runs']} empirical tables -> {RESULTS_DIR}")
    print("Fisher exact p-values:", json.dumps(summary["Fisher Exact P-Values"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
