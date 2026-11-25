"""AstroGuard LoRA fine-tuning runner.

Trains a lightweight conversational safety evaluator on top of local
Qwen2.5-0.5B-Instruct using prompt-masked instruction tuning on verified
AstroTrust captures. All model caches remain under D:\\ASTRO before mirroring
the compact LoRA adapter artifacts to models/astroguard/.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

os.environ["HF_HOME"] = r"D:\ASTRO\hf_cache"
os.environ["TORCH_HOME"] = r"D:\ASTRO\torch_cache"
os.environ["TRANSFORMERS_CACHE"] = r"D:\ASTRO\hf_cache"

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "data" / "astroguard" / "train.jsonl"
VAL_PATH = ROOT / "data" / "astroguard" / "val.jsonl"
SAVE_DIR_ASTRO = Path(r"D:\ASTRO\models\astroguard_lora")
FINAL_PROJECT_DIR = ROOT / "models" / "astroguard"
LOCAL_BASE_MODEL = Path(
    r"D:\ASTRO\models\models--Qwen--Qwen2.5-0.5B-Instruct"
    r"\snapshots\7ae557604adf67be50417f59c2c2f167def9a775"
)


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

    if not TRAIN_PATH.is_file() or not VAL_PATH.is_file():
        raise FileNotFoundError(
            "Dataset splits missing; run tools/prepare_astroguard_dataset.py first."
        )

    base_model_source = (
        str(LOCAL_BASE_MODEL) if LOCAL_BASE_MODEL.exists() else "Qwen/Qwen2.5-0.5B-Instruct"
    )
    local_only = LOCAL_BASE_MODEL.exists()
    print(f"Loading base model from: {base_model_source} (local_only={local_only})")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    gpu_desc = torch.cuda.get_device_name(0) if device == "cuda" else "CPU"
    print(f"Training device: {device} ({gpu_desc})")

    tokenizer: Any = AutoTokenizer.from_pretrained(base_model_source, local_files_only=local_only)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base_model: Any = AutoModelForCausalLM.from_pretrained(
        base_model_source,
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

    raw_datasets = load_dataset(
        "json",
        data_files={"train": str(TRAIN_PATH), "validation": str(VAL_PATH)},
    )

    max_len = 640

    def preprocess_function(examples: dict[str, Any]) -> dict[str, list[list[int]]]:
        input_ids_batch: list[list[int]] = []
        attention_batch: list[list[int]] = []
        labels_batch: list[list[int]] = []
        for messages in examples["messages"]:
            prompt_only = tokenizer.apply_chat_template(
                messages[:-1], tokenize=False, add_generation_prompt=True
            )
            full_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            prompt_ids: list[int] = list(
                tokenizer(prompt_only, add_special_tokens=False)["input_ids"]
            )
            full_ids: list[int] = list(tokenizer(full_text, add_special_tokens=False)["input_ids"])
            resp_ids = full_ids[len(prompt_ids) :]
            budget = max(64, max_len - len(resp_ids))
            if len(prompt_ids) > budget:
                head = budget // 2
                tail = budget - head
                prompt_ids = prompt_ids[:head] + prompt_ids[-tail:]
            combined_ids = prompt_ids + resp_ids
            labels = [-100] * len(prompt_ids) + resp_ids
            input_ids_batch.append(combined_ids)
            attention_batch.append([1] * len(combined_ids))
            labels_batch.append(labels)
        return {
            "input_ids": input_ids_batch,
            "attention_mask": attention_batch,
            "labels": labels_batch,
        }

    tokenized_datasets = raw_datasets.map(
        preprocess_function,
        batched=True,
        remove_columns=raw_datasets["train"].column_names,
    )

    if SAVE_DIR_ASTRO.exists():
        shutil.rmtree(SAVE_DIR_ASTRO)
    SAVE_DIR_ASTRO.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(SAVE_DIR_ASTRO / "_tmp_ckpt"),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=3e-4,
        num_train_epochs=4,
        logging_steps=5,
        save_strategy="no",
        eval_strategy="no",
        fp16=device == "cuda",
        optim="adamw_torch",
        seed=42,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8),
    )

    print("Starting prompt-masked AstroGuard LoRA fine-tuning...")
    train_result = trainer.train()
    print(f"Training metrics: {train_result.metrics}")

    tmp_ckpt = SAVE_DIR_ASTRO / "_tmp_ckpt"
    if tmp_ckpt.exists():
        shutil.rmtree(tmp_ckpt)

    model.save_pretrained(str(SAVE_DIR_ASTRO))
    tokenizer.save_pretrained(str(SAVE_DIR_ASTRO))

    if FINAL_PROJECT_DIR.exists():
        shutil.rmtree(FINAL_PROJECT_DIR)
    shutil.copytree(SAVE_DIR_ASTRO, FINAL_PROJECT_DIR)
    print(f"Saved AstroGuard LoRA adapter cleanly to {FINAL_PROJECT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
