"""Run cross-domain (8 scenarios x 3 belief frames) & multi-scale local benchmarks.

Generates verified `local-attempt-1.0` records under `data/runs/local/` without
overwriting any existing `0.5B` pilot runs:
1. Completes missing `positive_expectation` / `negative_expectation` runs for
   `Qwen/Qwen2.5-0.5B-Instruct` across scenarios `002`..`008` (+14 -> 30 total).
2. Evaluates `Qwen/Qwen2.5-1.5B-Instruct` across the matching 30-run design
   (9 career replicates + 21 cross-domain contrasts).

All HuggingFace model weights and caches remain strictly under `D:\\ASTRO`.
"""

from __future__ import annotations

import gc
import hashlib
import os
from pathlib import Path
from typing import Any, Literal

os.environ["HF_HOME"] = r"D:\ASTRO\hf_cache"
os.environ["TORCH_HOME"] = r"D:\ASTRO\torch_cache"
os.environ["TRANSFORMERS_CACHE"] = r"D:\ASTRO\hf_cache"

from astrotrust.benchmark.models import Condition, GenerationSettings
from astrotrust.collector.service import Collector
from astrotrust.collector.store import RunStore
from astrotrust.research.local import InferenceResult, LocalRequest, save_inference

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "runs" / "local"
RUNTIME_DESC = "PyTorch 2.6.0+cu124 on NVIDIA GeForce GTX 1650 (4 GB VRAM, warm fp16)"

QWEN_05B_SNAPSHOT = Path(
    r"D:\ASTRO\models\models--Qwen--Qwen2.5-0.5B-Instruct"
    r"\snapshots\7ae557604adf67be50417f59c2c2f167def9a775"
)
QWEN_05B_MODEL_HASH = "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe"
QWEN_05B_TOK_HASH = "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"

BeliefName = Literal["neutral", "positive_expectation", "negative_expectation"]
BELIEFS: tuple[BeliefName, ...] = ("neutral", "positive_expectation", "negative_expectation")
OTHER_SCENARIOS: tuple[str, ...] = (
    "atb-education-002",
    "atb-relationships-003",
    "atb-finance-004",
    "atb-health-005",
    "atb-relocation-006",
    "atb-family-007",
    "atb-everyday-008",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class WarmHFAdapter:
    """In-process HuggingFace causal LM adapter implementing `InferenceAdapter`."""

    name = "warm-hf-transformers-1.0"

    def __init__(self, model_name: str, local_snapshot: Path | None = None) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        src = str(local_snapshot) if local_snapshot and local_snapshot.exists() else model_name
        local_only = bool(local_snapshot and local_snapshot.exists())

        self.tokenizer: Any = AutoTokenizer.from_pretrained(
            src, local_files_only=local_only, trust_remote_code=True
        )
        model: Any = AutoModelForCausalLM.from_pretrained(
            src,
            dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
            local_files_only=local_only,
            trust_remote_code=True,
        )
        if hasattr(model, "eval"):
            model.eval()
        self.model: Any = model
        self.model_sha256, self.tokenizer_sha256 = self._resolve_hashes(model_name, local_snapshot)

    def _resolve_hashes(self, model_name: str, local_snapshot: Path | None) -> tuple[str, str]:
        if (
            model_name == "Qwen/Qwen2.5-0.5B-Instruct"
            and local_snapshot
            and local_snapshot.exists()
        ):
            return QWEN_05B_MODEL_HASH, QWEN_05B_TOK_HASH

        from huggingface_hub import snapshot_download

        snap_dir = Path(snapshot_download(model_name, local_files_only=True))
        safetensors = sorted(snap_dir.glob("*.safetensors"))
        if len(safetensors) == 1:
            m_hash = _sha256_file(safetensors[0])
        elif safetensors:
            h = hashlib.sha256()
            for sf in safetensors:
                h.update(f"{sf.name}:{_sha256_file(sf)}\n".encode("ascii"))
            m_hash = h.hexdigest()
        else:
            m_hash = _sha256_file(snap_dir / "config.json")
        tok_file = snap_dir / "tokenizer.json"
        t_hash = (
            _sha256_file(tok_file)
            if tok_file.is_file()
            else _sha256_file(snap_dir / "tokenizer_config.json")
        )
        return m_hash, t_hash

    def generate(self, request: LocalRequest) -> InferenceResult:
        import torch
        from transformers import set_seed

        messages = [{"role": m.role, "content": m.content} for m in request.prompt.messages]
        formatted = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(formatted, return_tensors="pt").to(self.device)
        s = request.settings
        if s.seed is not None:
            set_seed(int(s.seed))
        temp_val = 0.0 if s.temperature is None else float(s.temperature)
        top_p_val = 1.0 if s.top_p is None else float(s.top_p)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=int(s.max_output_tokens or 512),
                temperature=temp_val if temp_val > 0 else None,
                top_p=top_p_val if temp_val > 0 else None,
                do_sample=temp_val > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        new_tokens = outputs[0][inputs["input_ids"].shape[1] :]
        text = str(self.tokenizer.decode(new_tokens, skip_special_tokens=True))
        return InferenceResult(
            raw_response=text,
            returned_model_identifier=request.requested_model,
            model_version=str(getattr(self.model.config, "transformers_version", "transformers")),
            observed_settings={
                "device": self.device,
                "gpu_name": torch.cuda.get_device_name(0) if self.device == "cuda" else "cpu",
                "temperature": s.temperature,
                "top_p": s.top_p,
                "max_tokens": s.max_output_tokens,
                "seed": s.seed,
            },
        )

    def close(self) -> None:
        import torch

        del self.model
        del self.tokenizer
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def _build_run_matrix(prefix: str) -> list[tuple[str, BeliefName, int, int, Path]]:
    """Return ordered `(scenario_id, belief, run_number, seed, output_path)` specs."""
    specs: list[tuple[str, BeliefName, int, int, Path]] = []
    for belief in BELIEFS:
        for run_num in (1, 2, 3):
            stem = (
                f"attempt-career-{belief}-run{run_num}.json"
                if not prefix
                else f"attempt-{prefix}-career-{belief}-run{run_num}.json"
            )
            specs.append(("atb-career-001", belief, run_num, 42 + run_num, OUTPUT_DIR / stem))
    for sc_id in OTHER_SCENARIOS:
        for belief in BELIEFS:
            stem = (
                f"attempt-{sc_id}-{belief}-run1.json"
                if not prefix
                else f"attempt-{prefix}-{sc_id}-{belief}-run1.json"
            )
            specs.append((sc_id, belief, 1, 42, OUTPUT_DIR / stem))
    return specs


def _run_matrix_for_model(
    collector: Collector,
    model_name: str,
    prefix: str,
    local_snapshot: Path | None = None,
) -> int:
    specs = _build_run_matrix(prefix)
    pending = [spec for spec in specs if not spec[4].exists()]
    if not pending:
        print(f"[{model_name}] All {len(specs)} matrix runs already exist.")
        return 0

    adapter = WarmHFAdapter(model_name, local_snapshot=local_snapshot)
    new_runs = 0
    try:
        for sc_id, belief, run_num, seed, out_file in pending:
            prompt = collector.prompt(sc_id, Condition(belief=belief))
            req = LocalRequest(
                schema_version="local-request-1.0",
                operation="inference_only",
                study_phase="exploratory_pilot",
                requested_model=model_name,
                model_artifact_sha256=adapter.model_sha256,
                tokenizer_artifact_sha256=adapter.tokenizer_sha256,
                runtime_description=RUNTIME_DESC,
                prompt=prompt,
                settings=GenerationSettings(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=512,
                    seed=seed,
                    provider_parameters={},
                ),
                run_number=run_num,
            )
            attempt = save_inference(req, adapter, ROOT, out_file)
            print(
                f"[{model_name}] {sc_id} {belief} r{run_num} -> "
                f"{attempt.run.status} ({len(attempt.run.raw_response or '')} chars)"
            )
            new_runs += 1
    finally:
        adapter.close()
    return new_runs


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    collector = Collector(
        ROOT, RunStore(ROOT / "data" / "pilot" / "manual-runs" / "collector.sqlite3")
    )

    total = 0
    total += _run_matrix_for_model(
        collector,
        "Qwen/Qwen2.5-0.5B-Instruct",
        prefix="",
        local_snapshot=QWEN_05B_SNAPSHOT,
    )
    total += _run_matrix_for_model(
        collector,
        "Qwen/Qwen2.5-1.5B-Instruct",
        prefix="qwen15b",
        local_snapshot=None,
    )
    print(f"Completed cross-domain benchmark expansion. Newly generated runs: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
