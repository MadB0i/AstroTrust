# Future model experiments

No provider client, paid API connection or model output is included. Use reviewed
scenarios and `render_prompt(..., research_use=True)` only after a frozen protocol.
The present CLI is a development preview.

A future experiment manifest must list scenario/template revisions and hashes,
language reviews, explicit conditions/contrasts, model/provider identifiers,
generation settings, replicate counts, seeded/counterbalanced ordering, shared
system messages, failure/retry rules, exclusions and annotation/evaluator versions.
Keep independent conversations and save all actual messages in `Prompt`, including
runner-added instructions; recompute hashes. Validate each attempt as `ModelRun`.
Each retry is another attempt, not an overwrite. Do not silently filter failures.

Schema field `run_number` indexes prespecified replicates per scenario/condition/
model/settings combination. `run_id` and `response_id` must be globally unique in
the experiment store. The current single-record validator does not check uniqueness
across a future store; the runner must do so. A failed attempt reserves its IDs and
has an error with null response; a completion retains raw text without rewriting it.

Store local runs under ignored `data/runs/`. Decide retention and redistribution
under provider terms before public release. No sample outputs are fabricated here.
