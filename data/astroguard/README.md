# AstroGuard Dataset Splits (Local Regeneration)

Generated JSONL split files (`train.jsonl`, `val.jsonl`, `all_labeled.jsonl`) are intentionally Git-ignored in accordance with [data/README.md](../README.md) so raw third-party model outputs and proprietary consumer app transcripts are not redistributed in the public source tree.

To regenerate the verified stratified splits locally from your captured stores:

```powershell
python tools/prepare_astroguard_dataset.py
```

Aggregate evaluation metrics and confusion statistics without raw transcripts are preserved in [data/results/astroguard_eval.json](../results/astroguard_eval.json).
