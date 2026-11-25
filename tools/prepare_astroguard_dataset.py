"""Prepare non-empty AstroGuard dataset splits from verified AstroTrust captures."""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

from astrotrust.research.astroguard_rules import (
    SYSTEM_PROMPT,
    CapturedTrace,
    extract_all_traces,
    rule_based_detect,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "astroguard"
OUTPUT_TRAIN = OUTPUT_DIR / "train.jsonl"
OUTPUT_VAL = OUTPUT_DIR / "val.jsonl"
OUTPUT_ALL = OUTPUT_DIR / "all_labeled.jsonl"


def build_chat_example(trace: CapturedTrace) -> dict[str, Any]:
    """Convert a trace into an instruction-tuning message record with audited target."""
    if not trace.response.strip():
        raise ValueError(f"Empty raw_response encountered for {trace.run_id}")
    if not trace.prompt.strip():
        raise ValueError(f"Empty prompt encountered for {trace.run_id}")

    prompt_snippet = trace.prompt.strip()
    if len(prompt_snippet) > 900:
        prompt_snippet = "...\n" + prompt_snippet[-900:]

    target = rule_based_detect(trace.prompt, trace.response, trace.source_name)
    text_hash = hashlib.sha256(trace.response.encode("utf-8")).hexdigest()[:16]

    clean_source = re.sub(r"\s+", " ", trace.source_name).strip()
    user_msg = (
        f"Analyze this AI astrology interaction:\n"
        f"System: {clean_source}\n"
        f"Prompt: {prompt_snippet}\n"
        f"Response: {trace.response.strip()}"
    )

    return {
        "run_id": trace.run_id,
        "cohort": trace.cohort,
        "scenario_id": trace.scenario_id,
        "condition_id": trace.condition_id,
        "response_sha256_prefix": text_hash,
        "annotation_basis": "exploratory_deterministic_audit",
        "session_flags": list(trace.session_flags),
        "target": target,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)},
        ],
    }


def stratified_split(
    records: list[dict[str, Any]], seed: int = 42
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Stratify by cohort + safety_verdict so small cohorts appear in both splits."""
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        key = f"{rec['cohort']}::{rec['target']['safety_verdict']}"
        buckets.setdefault(key, []).append(rec)

    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []
    for key in sorted(buckets):
        items = list(buckets[key])
        rng.shuffle(items)
        if len(items) == 1:
            train.extend(items)
        else:
            n_val = max(1, round(len(items) * 0.2))
            val.extend(items[:n_val])
            train.extend(items[n_val:])

    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def main() -> int:
    traces = extract_all_traces()
    if not traces:
        raise RuntimeError("No traces found across SQLite, JSONL, or local runs.")

    examples = [build_chat_example(t) for t in traces]
    train, val = stratified_split(examples, seed=42)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for out_path, rows in ((OUTPUT_TRAIN, train), (OUTPUT_VAL, val), (OUTPUT_ALL, examples)):
        with out_path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Extracted {len(examples)} verified non-empty traces:")
    for cohort in ("consumer_app", "frontier_llm", "local_open_llm"):
        t_cnt = sum(1 for r in train if r["cohort"] == cohort)
        v_cnt = sum(1 for r in val if r["cohort"] == cohort)
        print(f"  {cohort:15s}: total={t_cnt + v_cnt:2d} (train={t_cnt:2d}, val={v_cnt:2d})")
    print(f"Wrote {len(train)} train rows -> {OUTPUT_TRAIN}")
    print(f"Wrote {len(val)} val rows -> {OUTPUT_VAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
