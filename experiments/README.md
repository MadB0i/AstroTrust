# Experimental workflow

AstroTrust 2.0 separates frontier manual capture, consumer apps and local inference.
Local private frontier outputs exist; consumer collection remains pending. An
[inference-only local interface](../docs/local-models.md) accepts an explicitly
supplied runtime without provider SDKs or automatic downloads. No real local-model
experiment, training or held-out AstroGuard result is included. See the
[research plan](../docs/ASTROTRUST-2.0-PLAN.md).

Use reviewed
scenarios and `render_prompt(..., research_use=True)` only after a frozen protocol.
The present prompt CLI is a development preview, and local attempts remain pilot data.

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
