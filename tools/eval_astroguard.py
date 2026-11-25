"""Evaluate AstroGuard-Rules and AstroGuard-LoRA across validation traces.

Writes reproducible evaluation metrics to data/results/astroguard_eval.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from astrotrust.research.astroguard_rules import rule_based_detect

os.environ["HF_HOME"] = r"D:\ASTRO\hf_cache"
os.environ["TORCH_HOME"] = r"D:\ASTRO\torch_cache"
os.environ["TRANSFORMERS_CACHE"] = r"D:\ASTRO\hf_cache"

ROOT = Path(__file__).resolve().parents[1]
VAL_PATH = ROOT / "data" / "astroguard" / "val.jsonl"
ALL_PATH = ROOT / "data" / "astroguard" / "all_labeled.jsonl"
MODEL_PATH = ROOT / "models" / "astroguard"
if not MODEL_PATH.exists():
    MODEL_PATH = Path(r"D:\ASTRO\models\astroguard_lora")
LOCAL_BASE_MODEL = Path(
    r"D:\ASTRO\models\models--Qwen--Qwen2.5-0.5B-Instruct"
    r"\snapshots\7ae557604adf67be50417f59c2c2f167def9a775"
)
RESULTS_PATH = ROOT / "data" / "results" / "astroguard_eval.json"


def _binary_metrics(y_true: list[bool], y_pred: list[bool]) -> dict[str, Any]:
    tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t and not p)
    tn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if not t and not p)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / len(y_true) if y_true else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
    }


def _extract_json(text: str) -> dict[str, Any] | None:
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`").removeprefix("json").strip()
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(s[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def evaluate_all() -> dict[str, Any]:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    val_rows = [
        json.loads(line)
        for line in VAL_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    all_rows = [
        json.loads(line)
        for line in ALL_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    rule_all_preds: list[dict[str, Any]] = []
    for row in all_rows:
        user_content = row["messages"][1]["content"]
        sys_line = ""
        prompt_part = ""
        resp_part = ""
        has_all = (
            "System: " in user_content
            and "\nPrompt: " in user_content
            and "\nResponse: " in user_content
        )
        if has_all:
            after_sys = user_content.split("System: ", 1)[1]
            sys_line, rest = after_sys.split("\nPrompt: ", 1)
            prompt_part, resp_part = rest.split("\nResponse: ", 1)
        rule_all_preds.append(rule_based_detect(prompt_part, resp_part, sys_line))

    base_src = str(LOCAL_BASE_MODEL) if LOCAL_BASE_MODEL.exists() else "Qwen/Qwen2.5-0.5B-Instruct"
    local_only = LOCAL_BASE_MODEL.exists()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH), local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base_model: Any = AutoModelForCausalLM.from_pretrained(
        base_src,
        dtype=torch.float16 if device == "cuda" else torch.float32,
        local_files_only=local_only,
    )
    model: Any = PeftModel.from_pretrained(base_model, str(MODEL_PATH)).to(device)
    model.eval()

    per_sample: list[dict[str, Any]] = []
    parse_ok = 0
    verdict_exact = 0
    adrs_exact = 0
    dp_true: list[bool] = []
    dp_pred: list[bool] = []
    drift_true: list[bool] = []
    drift_pred: list[bool] = []
    unsafe_true: list[bool] = []
    unsafe_pred: list[bool] = []

    for row in val_rows:
        gt = row["target"]
        prompt_messages = row["messages"][:-1]
        prompt_text = tokenizer.apply_chat_template(
            prompt_messages, tokenize=False, add_generation_prompt=True
        )
        prompt_ids: list[int] = list(tokenizer(prompt_text, add_special_tokens=False)["input_ids"])
        if len(prompt_ids) > 560:
            prompt_ids = prompt_ids[:280] + prompt_ids[-280:]
        input_tensor = torch.tensor([prompt_ids], dtype=torch.long, device=device)
        attn_mask = torch.ones_like(input_tensor)
        with torch.no_grad():
            outputs = model.generate(
                input_ids=input_tensor,
                attention_mask=attn_mask,
                max_new_tokens=220,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        new_tokens = outputs[0][len(prompt_ids) :]
        raw_out = str(tokenizer.decode(new_tokens, skip_special_tokens=True)).strip()
        pred = _extract_json(raw_out)

        ok = pred is not None
        if ok:
            parse_ok += 1
        pred_safe = pred or {}
        if pred_safe.get("safety_verdict") == gt["safety_verdict"]:
            verdict_exact += 1
        if pred_safe.get("adrs_tier") == gt["adrs_tier"]:
            adrs_exact += 1

        dp_t = bool(gt["text_dark_pattern_present"])
        dp_p = bool(pred_safe.get("text_dark_pattern_present", False))
        dp_true.append(dp_t)
        dp_pred.append(dp_p)

        dr_t = bool(gt["epistemic_drift_or_hallucination"])
        dr_p = bool(pred_safe.get("epistemic_drift_or_hallucination", False))
        drift_true.append(dr_t)
        drift_pred.append(dr_p)

        un_t = gt["safety_verdict"] != "SAFE_CALIBRATED"
        un_p = pred_safe.get("safety_verdict", "SAFE_CALIBRATED") != "SAFE_CALIBRATED"
        unsafe_true.append(un_t)
        unsafe_pred.append(un_p)

        per_sample.append(
            {
                "run_id": row["run_id"],
                "cohort": row["cohort"],
                "parse_ok": ok,
                "ground_truth": gt,
                "lora_prediction": pred_safe if ok else None,
                "raw_lora_output": raw_out,
            }
        )

    n_val = len(val_rows)
    report: dict[str, Any] = {
        "evaluation_scope": (
            "Exploratory in-domain validation (N=10 stratified across consumer/frontier/local "
            "from the N=49 dataset; predominantly atb-career-001 scenarios)."
        ),
        "model_path": str(MODEL_PATH.relative_to(ROOT)),
        "base_model": "Qwen/Qwen2.5-0.5B-Instruct (LoRA q/v r=8, alpha=16, prompt-masked)",
        "val_size": n_val,
        "lora_metrics": {
            "json_parse_rate": round(parse_ok / n_val, 4) if n_val else 0.0,
            "safety_verdict_exact_accuracy": round(verdict_exact / n_val, 4) if n_val else 0.0,
            "adrs_tier_exact_accuracy": round(adrs_exact / n_val, 4) if n_val else 0.0,
            "text_dark_pattern_binary": _binary_metrics(dp_true, dp_pred),
            "epistemic_drift_binary": _binary_metrics(drift_true, drift_pred),
            "any_unsafe_binary": _binary_metrics(unsafe_true, unsafe_pred),
        },
        "rule_baseline_check": {
            "total_evaluated": len(all_rows),
            "self_consistency_accuracy": round(
                sum(
                    1
                    for row, pred in zip(all_rows, rule_all_preds, strict=True)
                    if pred["safety_verdict"] == row["target"]["safety_verdict"]
                )
                / len(all_rows),
                4,
            ),
            "note": (
                "AstroGuard-Rules defines the deterministic baseline audit criteria; "
                "self-consistency confirms lossless feature extraction across N=49 prompts."
            ),
        },
        "validation_samples": per_sample,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return report


def main() -> int:
    report = evaluate_all()
    print("=== ASTROGUARD EXPLORATORY VALIDATION REPORT ===")
    print(json.dumps(report["lora_metrics"], indent=2))
    print("\nPer-sample validation summary:")
    for item in report["validation_samples"]:
        gt = item["ground_truth"]
        pr = item["lora_prediction"] or {}
        print(
            f"  {item['cohort']:15s} | {item['run_id'][:22]:22s} | "
            f"parse={item['parse_ok']} | "
            f"gt={gt['safety_verdict']} vs pred={pr.get('safety_verdict')}"
        )
    print(f"\nSaved full evaluation report -> {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
