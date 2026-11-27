"""Train class-balanced AstroGuard-LoRA (0.5B) strictly on dev train split.

Oversamples minority unsafe/hybrid examples inside `data/astroguard/train.jsonl`
(never touching `heldout_unseen_labeled.jsonl`) to test whether class balancing
alleviates majority-class SAFE_CALIBRATED verdict collapse.
"""

from __future__ import annotations

import json
import os
import random
import shutil
from pathlib import Path
from typing import Any

os.environ["HF_HOME"] = r"D:\ASTRO\hf_cache"
os.environ["TORCH_HOME"] = r"D:\ASTRO\torch_cache"
os.environ["TRANSFORMERS_CACHE"] = r"D:\ASTRO\hf_cache"

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "data" / "astroguard" / "train.jsonl"
BALANCED_TRAIN_PATH = ROOT / "data" / "astroguard" / "train_balanced.jsonl"
SAVE_DIR_ASTRO = Path(r"D:\ASTRO\models\astroguard_balanced")
FINAL_PROJECT_DIR = ROOT / "models" / "astroguard_balanced"
LOCAL_BASE_MODEL = Path(
    r"D:\ASTRO\models\models--Qwen--Qwen2.5-0.5B-Instruct"
    r"\snapshots\7ae557604adf67be50417f59c2c2f167def9a775"
)


def build_balanced_train(seed: int = 42) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in TRAIN_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    balanced: list[dict[str, Any]] = []
    for row in rows:
        verdict = row["target"]["safety_verdict"]
        if verdict == "SAFE_CALIBRATED":
            repeats = 1
        elif verdict in ("UNSAFE_COMMERCIAL_TRAP", "HYBRID_CALIBRATED_WITH_COMMERCIAL_HOOK"):
            repeats = 4
        else:
            repeats = 3
        for _ in range(repeats):
            balanced.append(row)
    random.Random(seed).shuffle(balanced)
    BALANCED_TRAIN_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in balanced) + "\n",
        encoding="utf-8",
    )
    return balanced


def main() -> int:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Trainer,
        TrainingArguments,
    )

    if not TRAIN_PATH.is_file():
        raise FileNotFoundError("Missing data/astroguard/train.jsonl")

    balanced_rows = build_balanced_train(seed=42)
    safe_cnt = sum(1 for r in balanced_rows if r["target"]["safety_verdict"] == "SAFE_CALIBRATED")
    print(
        f"Prepared balanced train split: total={len(balanced_rows)} "
        f"(SAFE={safe_cnt}, UNSAFE/HYBRID={len(balanced_rows) - safe_cnt})"
    )

    base_src = str(LOCAL_BASE_MODEL) if LOCAL_BASE_MODEL.exists() else "Qwen/Qwen2.5-0.5B-Instruct"
    local_only = LOCAL_BASE_MODEL.exists()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer: Any = AutoTokenizer.from_pretrained(base_src, local_files_only=local_only)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model: Any = AutoModelForCausalLM.from_pretrained(
        base_src,
        dtype=torch.float16 if device == "cuda" else torch.float32,
        local_files_only=local_only,
    )
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],
    )
    model: Any = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    raw_ds = load_dataset("json", data_files={"train": str(BALANCED_TRAIN_PATH)})
    max_len = 640

    def preprocess(examples: dict[str, Any]) -> dict[str, list[list[int]]]:
        in_ids: list[list[int]] = []
        attn: list[list[int]] = []
        lbls: list[list[int]] = []
        for messages in examples["messages"]:
            prompt_only = tokenizer.apply_chat_template(
                messages[:-1], tokenize=False, add_generation_prompt=True
            )
            full_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            p_ids: list[int] = list(tokenizer(prompt_only, add_special_tokens=False)["input_ids"])
            f_ids: list[int] = list(tokenizer(full_text, add_special_tokens=False)["input_ids"])
            r_ids = f_ids[len(p_ids) :]
            budget = max(64, max_len - len(r_ids))
            if len(p_ids) > budget:
                head = budget // 2
                tail = budget - head
                p_ids = p_ids[:head] + p_ids[-tail:]
            comb = p_ids + r_ids
            in_ids.append(comb)
            attn.append([1] * len(comb))
            lbls.append([-100] * len(p_ids) + r_ids)
        return {"input_ids": in_ids, "attention_mask": attn, "labels": lbls}

    tok_ds = raw_ds.map(preprocess, batched=True, remove_columns=raw_ds["train"].column_names)
    if SAVE_DIR_ASTRO.exists():
        shutil.rmtree(SAVE_DIR_ASTRO)
    SAVE_DIR_ASTRO.mkdir(parents=True, exist_ok=True)

    args = TrainingArguments(
        output_dir=str(SAVE_DIR_ASTRO / "_tmp_ckpt"),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=3e-4,
        num_train_epochs=4,
        logging_steps=10,
        save_strategy="no",
        eval_strategy="no",
        fp16=device == "cuda",
        optim="adamw_torch",
        seed=42,
        report_to="none",
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tok_ds["train"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8),
    )
    res = trainer.train()
    print(f"Balanced training metrics: {res.metrics}")

    tmp_ckpt = SAVE_DIR_ASTRO / "_tmp_ckpt"
    if tmp_ckpt.exists():
        shutil.rmtree(tmp_ckpt)

    model.save_pretrained(str(SAVE_DIR_ASTRO))
    tokenizer.save_pretrained(str(SAVE_DIR_ASTRO))

    if FINAL_PROJECT_DIR.exists():
        shutil.rmtree(FINAL_PROJECT_DIR)
    shutil.copytree(SAVE_DIR_ASTRO, FINAL_PROJECT_DIR)
    print(f"Saved balanced AstroGuard LoRA -> {FINAL_PROJECT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
