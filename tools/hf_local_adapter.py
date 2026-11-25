"""Local inference adapter for AstroTrust 2.0.

Consumes a LocalRequest JSON on stdin and writes an InferenceResult JSON on stdout.
Uses HuggingFace Transformers with cache directed exclusively to D:\\ASTRO.
"""

import json
import os
import sys
from pathlib import Path

# Force all caches and downloads to D:\ASTRO
os.environ["HF_HOME"] = r"D:\ASTRO\hf_cache"
os.environ["TORCH_HOME"] = r"D:\ASTRO\torch_cache"
os.environ["TRANSFORMERS_CACHE"] = r"D:\ASTRO\hf_cache"

LOCAL_SNAPSHOT = Path(
    r"D:\ASTRO\models\models--Qwen--Qwen2.5-0.5B-Instruct"
    r"\snapshots\7ae557604adf67be50417f59c2c2f167def9a775"
)


def run_adapter() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.stderr.write("Empty stdin request\n")
            sys.exit(1)

        request_data = json.loads(raw_input)
        requested_model = request_data.get("requested_model", "Qwen/Qwen2.5-0.5B-Instruct")
        prompt = request_data.get("prompt", {})
        messages = prompt.get("messages", [])
        settings = request_data.get("settings", {})

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = "cuda" if torch.cuda.is_available() else "cpu"

        if LOCAL_SNAPSHOT.exists():
            model_source = str(LOCAL_SNAPSHOT)
            local_only = True
        else:
            model_source = requested_model
            local_only = False

        tokenizer = AutoTokenizer.from_pretrained(
            model_source,
            local_files_only=local_only,
            trust_remote_code=True,
        )

        model = AutoModelForCausalLM.from_pretrained(
            model_source,
            dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
            local_files_only=local_only,
            trust_remote_code=True,
        )

        # Format input messages
        formatted_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = tokenizer(formatted_prompt, return_tensors="pt").to(device)

        max_tokens = settings.get("max_output_tokens") or settings.get("max_tokens") or 512
        temperature = settings.get("temperature", 0.7)
        top_p = settings.get("top_p", 0.9)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else None,
                top_p=top_p if temperature > 0 else None,
                do_sample=temperature > 0,
                pad_token_id=tokenizer.eos_token_id,
            )

        new_tokens = outputs[0][inputs["input_ids"].shape[1] :]
        response_text = tokenizer.decode(new_tokens, skip_special_tokens=True)

        result = {
            "raw_response": response_text,
            "returned_model_identifier": requested_model,
            "model_version": getattr(model.config, "transformers_version", "transformers"),
            "observed_settings": {
                "device": device,
                "gpu_name": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
            },
        }

        sys.stdout.write(json.dumps(result, ensure_ascii=False))
        sys.stdout.flush()

    except Exception as e:
        sys.stderr.write(f"Inference error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    run_adapter()
