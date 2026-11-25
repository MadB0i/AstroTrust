"""Runs the local small-model baseline benchmark across the standardized scenarios.

Generates validated LocalAttempt records saved in data/runs/local/ with exact hashes.
Uses Qwen2.5-0.5B-Instruct on local GTX 1650 via tools/hf_local_adapter.py.
"""

import sys
from pathlib import Path

from astrotrust.benchmark.models import Condition, GenerationSettings
from astrotrust.collector.service import Collector
from astrotrust.collector.store import RunStore
from astrotrust.research.local import (
    CommandAdapter,
    LocalRequest,
    save_inference,
)

ROOT = Path(".")
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_HASH = "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe"
TOKENIZER_HASH = "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
RUNTIME_DESC = "PyTorch 2.6.0+cu124 on NVIDIA GeForce GTX 1650 (4 GB VRAM)"
OUTPUT_DIR = Path("data/runs/local")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    collector = Collector(ROOT, RunStore(Path("data/pilot/manual-runs/collector.sqlite3")))

    # Python command adapter
    python_exe = sys.executable
    adapter_cmd = (python_exe, "tools/hf_local_adapter.py")
    adapter = CommandAdapter(adapter_cmd, timeout=120)

    # 1. Career Matrix (3 belief conditions x 3 replicates = 9 runs)
    career_conditions = [
        ("neutral", 1),
        ("neutral", 2),
        ("neutral", 3),
        ("positive_expectation", 1),
        ("positive_expectation", 2),
        ("positive_expectation", 3),
        ("negative_expectation", 1),
        ("negative_expectation", 2),
        ("negative_expectation", 3),
    ]

    total_runs = 0
    print(f"Starting Local Baseline benchmark runs for {MODEL_NAME}...")

    for belief, run_num in career_conditions:
        cond = Condition(belief=belief)
        prompt = collector.prompt("atb-career-001", cond)
        out_file = OUTPUT_DIR / f"attempt-career-{belief}-run{run_num}.json"

        if out_file.exists():
            print(f"Skipping already existing run: {out_file.name}")
            continue

        req = LocalRequest(
            schema_version="local-request-1.0",
            operation="inference_only",
            study_phase="exploratory_pilot",
            requested_model=MODEL_NAME,
            model_artifact_sha256=MODEL_HASH,
            tokenizer_artifact_sha256=TOKENIZER_HASH,
            runtime_description=RUNTIME_DESC,
            prompt=prompt,
            settings=GenerationSettings(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=512,
                seed=42 + run_num,
                provider_parameters={},
            ),
            run_number=run_num,
        )

        print(f"Executing: atb-career-001 | belief={belief} | run={run_num} -> {out_file.name}")
        attempt = save_inference(req, adapter, ROOT, out_file)
        print(
            f"  Completed! Status: {attempt.run.status} | "
            f"Response SHA: {(attempt.response_sha256 or '')[:12]}..."
        )
        total_runs += 1

    # 2. Cross-domain scenarios in neutral condition
    other_scenarios = [
        "atb-education-002",
        "atb-relationships-003",
        "atb-finance-004",
        "atb-health-005",
        "atb-relocation-006",
        "atb-family-007",
        "atb-everyday-008",
    ]

    for sc_id in other_scenarios:
        out_file = OUTPUT_DIR / f"attempt-{sc_id}-neutral-run1.json"
        if out_file.exists():
            print(f"Skipping already existing run: {out_file.name}")
            continue

        cond = Condition(belief="neutral")
        prompt = collector.prompt(sc_id, cond)

        req = LocalRequest(
            schema_version="local-request-1.0",
            operation="inference_only",
            study_phase="exploratory_pilot",
            requested_model=MODEL_NAME,
            model_artifact_sha256=MODEL_HASH,
            tokenizer_artifact_sha256=TOKENIZER_HASH,
            runtime_description=RUNTIME_DESC,
            prompt=prompt,
            settings=GenerationSettings(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=512,
                seed=42,
                provider_parameters={},
            ),
            run_number=1,
        )

        print(f"Executing: {sc_id} | belief=neutral | run=1 -> {out_file.name}")
        attempt = save_inference(req, adapter, ROOT, out_file)
        print(
            f"  Completed! Status: {attempt.run.status} | "
            f"Response SHA: {(attempt.response_sha256 or '')[:12]}..."
        )
        total_runs += 1

    print(f"\nAll benchmark runs completed! Total newly executed runs: {total_runs}")


if __name__ == "__main__":
    main()
