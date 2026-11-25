# Reproducible capture annotation and analysis

`astrotrust.research.analysis` supports immutable `manual-1.0` and `consumer-1.1`
captures without inventing API settings or replacing existing annotation workflows.
The existing `astrotrust.annotations` schema and agreement/adjudication commands
continue to apply to controlled `ModelRun` records. There is no silent conversion.

Use the draft handbook for independent labels. Store each `CaptureAnnotation` in a
separate private JSON file with schema `capture-annotation-1.0`, unique annotation
ID, source run ID/schema, SHA-256 of `canonical_json(capture)`, response hash,
`origin=human|model`, evaluator pseudonym or model identity, evaluator provenance,
timezone-aware timestamp, `rubric_version=draft-1.0`, uncertainty and adjudication
flag. `labels` uses the existing `ResponseLabels`; `support` must justify every
existing response field with exact evidence or an absence/uncertainty reason.

Evidence `response_id` is the capture's run ID (manual captures have no separate
response ID). Offsets are Python Unicode code points, end-exclusive; excerpts must
match the untouched response exactly. Empty responses require `unratable`. Neutral
frontier priors require `belief_relationship=not_applicable`. A metadata revision
changes the snapshot hash: explicitly review/relink a derived annotation to the
chosen snapshot rather than changing the old sidecar.

For schema inspection without generating any research labels:

```powershell
python -c "import json; from astrotrust.research.analysis import CaptureAnnotation; print(json.dumps(CaptureAnnotation.model_json_schema(), indent=2))"
python -m astrotrust research summarize data/pilot/exports/pilot-2026-10-05.jsonl
python -m astrotrust research summarize data/pilot/exports/pilot-2026-10-05.jsonl --annotations data/private/annotations/capture-a.json data/private/annotations/capture-b.json
```

The CLI currently accepts frontier JSONL/CSV exports. The Python `summarize` function
also accepts validated consumer captures; use `consumer_exports.load_export` and
keep source protocols separate. Consumer matched-belief metrics are not implied by
the fixed app prompts. No consumer backend/model identity is inferred.

The deterministic report hashes source snapshots and annotation inputs and counts
categories by capture schema and source category, exact provider/product/model/condition (or
service/prompt/mode/profile), judgment origin, evaluator, field and label. Input
ordering does not change hashes. Duplicate run IDs, annotation IDs or multiple votes
from the same evaluator for one capture are rejected; select revisions explicitly.
No annotations produces zero annotated captures and no category counts, not a
fabricated score. Human and model judgments remain separate; no majority vote,
ground-truth promotion, automatic adjudication, BCAS/ADRS aggregate, model ranking
or confidence interval is calculated. Uncertain/unratable votes remain visible;
define exclusions before analysis, not after seeing favorable outcomes.

This does not relax the collector's existing stopping rule. Close/prespecify the
pilot before examining response content to decide further collection. Freeze a
reviewed analysis protocol before interpreting these exploratory labels.
