"""Export a blinded, shuffled second-coder annotation packet under reviews/generated/.

Withholds model, vendor, and cohort identities so an independent human co-rater
can annotate responses against docs/annotation-handbook.md, enabling two-rater
Cohen's kappa computation via `python -m astrotrust annotations agreement`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from astrotrust.annotations.models import (
    GROUNDING_ORDER,
    RELIANCE_ORDER,
    RUBRIC_VERSION,
)
from astrotrust.research.astroguard_rules import extract_all_traces

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "reviews" / "generated"


def export_blind_packet(
    out_dir: Path = DEFAULT_OUT_DIR,
    seed: int = 20261125,
    max_items: int = 40,
) -> tuple[Path, Path]:
    """Create anonymized JSON packet + Markdown worksheet for independent coding."""
    traces = extract_all_traces()
    if not traces:
        raise RuntimeError("No captured traces found to export.")

    rng = random.Random(seed)
    by_cohort: dict[str, list[Any]] = {}
    for tr in traces:
        by_cohort.setdefault(tr.cohort, []).append(tr)

    selected: list[Any] = []
    # Include all consumer runs plus balanced frontier and local cross-domain runs
    consumer = sorted(by_cohort.get("consumer_app", []), key=lambda t: t.run_id)
    selected.extend(consumer)

    remaining = max(0, max_items - len(selected))
    frontier = sorted(by_cohort.get("frontier_llm", []), key=lambda t: t.run_id)
    local = sorted(by_cohort.get("local_open_llm", []), key=lambda t: t.run_id)
    rng.shuffle(frontier)
    rng.shuffle(local)

    half = remaining // 2
    selected.extend(frontier[:half])
    selected.extend(local[: remaining - half])
    rng.shuffle(selected)

    packet_items: list[dict[str, Any]] = []
    mapping_rows: list[dict[str, str]] = []
    for idx, tr in enumerate(selected, start=1):
        blind_id = f"unit-{idx:03d}"
        resp_sha = hashlib.sha256(tr.response.encode("utf-8")).hexdigest()
        packet_items.append(
            {
                "blind_id": blind_id,
                "scenario_id": tr.scenario_id,
                "condition_id": tr.condition_id,
                "prompt": tr.prompt,
                "raw_response": tr.response,
                "response_sha256": resp_sha,
                "labels": {
                    "decision_reliance": None,
                    "practical_grounding": None,
                    "epistemic_framing": None,
                    "reliance_stance": None,
                    "guidance_displacement": None,
                    "text_dark_pattern_present": None,
                    "epistemic_drift_or_hallucination": None,
                    "annotation_uncertainty": "clear",
                    "notes": "",
                },
            }
        )
        mapping_rows.append(
            {
                "blind_id": blind_id,
                "run_id": tr.run_id,
                "cohort": tr.cohort,
                "source_name": tr.source_name,
                "response_sha256": resp_sha,
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    packet_path = out_dir / "blind_second_coder_packet.json"
    key_path = out_dir / "blind_coder_key_PRIVATE.json"
    md_path = out_dir / "blind_second_coder_worksheet.md"

    packet_payload = {
        "schema_version": "1.0",
        "rubric_version": RUBRIC_VERSION,
        "seed": seed,
        "item_count": len(packet_items),
        "allowed_values": {
            "decision_reliance": list(RELIANCE_ORDER) + ["unclear", "not_applicable"],
            "practical_grounding": list(GROUNDING_ORDER) + ["unclear", "not_applicable"],
            "epistemic_framing": [
                "none",
                "entertainment",
                "cultural_interpretation",
                "uncertain_prediction",
                "confident_prediction",
                "deterministic",
                "mixed",
                "unclear",
                "not_applicable",
            ],
            "reliance_stance": ["discourages", "no_position", "encourages", "mixed", "unclear"],
            "guidance_displacement": [
                "displaces",
                "supplements",
                "no_position",
                "mixed",
                "unclear",
            ],
            "text_dark_pattern_present": [True, False],
            "epistemic_drift_or_hallucination": [True, False],
        },
        "items": packet_items,
    }
    packet_path.write_text(
        json.dumps(packet_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    key_path.write_text(
        json.dumps({"seed": seed, "mapping": mapping_rows}, indent=2) + "\n", encoding="utf-8"
    )

    md_lines = [
        "# Blind Second-Coder Annotation Worksheet",
        "",
        f"- **Rubric:** `{RUBRIC_VERSION}` (see `docs/annotation-handbook.md`)",
        f"- **Units:** `{len(packet_items)}` masked prompt-response pairs (`seed={seed}`)",
        "- **Instructions:** Share ONLY `blind_second_coder_packet.json` and this worksheet "
        "with the second human annotator (`rater-02`). Withhold `blind_coder_key_PRIVATE.json` "
        "until both raters finish independent coding.",
        "",
        "Allowed `decision_reliance` tiers: `" + "`, `".join(RELIANCE_ORDER) + "`",
        "",
    ]
    for item in packet_items:
        md_lines.extend(
            [
                f"## {item['blind_id']} ({item['scenario_id']} | `{item['condition_id']}`)",
                "",
                "**Prompt:**",
                "",
                "```text",
                item["prompt"].strip(),
                "```",
                "",
                "**Response:**",
                "",
                "```text",
                item["raw_response"].strip(),
                "```",
                "",
                "- `decision_reliance`: ",
                "- `practical_grounding`: ",
                "- `epistemic_framing`: ",
                "- `text_dark_pattern_present`: ",
                "- `epistemic_drift_or_hallucination`: ",
                "",
            ]
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return packet_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=20261125)
    parser.add_argument("--max-items", type=int, default=40)
    args = parser.parse_args()

    packet_path, md_path = export_blind_packet(
        out_dir=args.out_dir, seed=args.seed, max_items=args.max_items
    )
    print(f"Wrote blind JSON packet -> {packet_path}")
    print(f"Wrote readable worksheet -> {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
