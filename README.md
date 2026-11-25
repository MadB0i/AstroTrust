# AstroTrust 2.0

**Independent research in progress. Evidence collection is exploratory; no validated
benchmark scores or published findings are claimed.**

AstroTrust evaluates how AI systems handle astrology-related beliefs, uncertain
claims and consequential advice. Its primary question is: **How reliably do AI
systems distinguish astrology-based beliefs from evidence-supported advice,
particularly in consequential decision-making scenarios?** The study evaluates
system behavior. Public opinion and real-world user effects are outside its scope.
It does not test whether astrology predictions are scientifically valid.
India-focused fictional contexts do not represent a population or tradition.

The public participant survey has been discontinued as a research-scope decision.
It is no longer a deliverable, prerequisite or collection workflow. Independent
construction review, response annotation and adjudication remain essential.
See the [revised plan](docs/ASTROTRUST-2.0-PLAN.md),
[migration audit](docs/ASTROTRUST-PIVOT-AUDIT.md) and
[superseded proposal archive](docs/archive/README.md).

## Research workstation

```powershell
uv sync --locked --extra dev
uv run --locked python -m astrotrust collect
```

Open the printed URL, then select **Research overview** (`/research`). Frontier
captures remain at `/`; consumer collection remains at `/consumer`; local baseline
instructions are at `/local`. The overview reads the selected stores without
writing or creating the lazily opened frontier store. Missing or unreadable stores
show unavailable status rather than a fabricated zero.

| Study arm | Implemented | Evidence status (25 November 2026) |
| --- | --- | --- |
| Frontier models | [Manual collector](docs/manual-collector.md), SQLite snapshots, exports, [draft label analysis](docs/response-analysis.md) | 27 local exploratory captures (`atb-career-001` across ChatGPT, Claude, Gemini); original JSONL/Markdown exports preserved (`data/pilot/`, Git ignored) |
| Consumer astrology apps | [Separate collector](docs/consumer-collector.md), `consumer-1.1` profiles, static APK auditor (`tools/audit_apks.py`) | 6 live exploratory captures across 5 Android apps (`Astrotalk`, `Pandit Ji`, `Reva`, `AstroSage`, `AstroTime`) + binary forensic audit (`data/results/apk_forensic_summary.json`) |
| Local small models | [Inference-only adapter interface](docs/local-models.md), HuggingFace adapter (`tools/hf_local_adapter.py`) | 16 local `Qwen/Qwen2.5-0.5B-Instruct` baseline inference runs (`data/runs/local/`, Git ignored) |
| AstroGuard | [Experimental design](docs/ASTROTRUST-2.0-PLAN.md), rule baseline + LoRA trainer (`tools/train_astroguard.py`) | Exploratory deterministic baseline (`N=49`) + prompt-masked `Qwen2.5-0.5B-LoRA` prototype (`models/astroguard/`, evaluated in `data/results/astroguard_eval.json`; out-of-domain scenario-family evaluation still pending) |

Full working manuscript: [LaTeX paper (`paper/main.tex`)](paper/README.md) · [Markdown draft (`docs/paper_draft.md`)](docs/paper_draft.md) · [Manuscript outline](docs/research-paper-outline.md) · [Empirical comparison table](data/results/empirical_comparison_table.md)

These are verified local inventory counts, not packaged research data or performance
results. A fresh clone contains no captured outputs. The overview refreshes actual
store counts; this dated table is an audit observation. Exact frontend model labels
are observations, not authenticated backend identities. Unknown settings remain
unknown. Consumer protocols, account configuration and interaction histories differ
from the frontier matrix; comparisons must disclose those differences.

For consumer-first startup:

```powershell
uv run --locked python -m astrotrust collect-consumer
```

Open the printed `/consumer` URL. This keeps the frontier database unopened until a
frontier API operation is requested. Consumer captures require the fixed fictional
profile or explicit `not_used`, submitted-field names, and exact multi-step protocol
evidence where applicable. Keep `consumer-1.1` and profile hashes unchanged.

**Do not inspect or score earlier responses while deciding whether to continue collection.**
This pivot adds analysis capability; it does not close the pilot, authorize adaptive
stopping or relabel existing evidence as confirmatory or held-out data.

## Instrument and analysis boundaries

[instrument-v0.1](docs/instrument-version.md) remains locked at eight fictional
development scenarios and 24 default English prompts. Hindi and Assamese are
pending, and no multilingual equivalence is claimed. Literal matched contrasts
change only the belief sentence; emotion and personalization require separate
controlled comparisons. Research-use rendering still requires human review.

The [draft annotation handbook](docs/annotation-handbook.md) and
[independent reviewer bundles](reviews/pending/README.md) remain intact.
BCAS and ADRS are provisional constructs without a validated numerical aggregate.
Capture annotation sidecars verify snapshot hashes and response excerpts, retain
individual evaluator votes, and keep model judgments separate from human judgments.
Descriptive category counts are available; they do not establish construct validity,
actual trust, safety improvements or causal effects. The [scale-up gate](docs/scale-up-gate.md)
still requires independent review and a prespecified design.

```powershell
uv run --locked python -m astrotrust research status
uv run --locked python -m astrotrust research summarize data/pilot/exports/pilot-2026-10-05.jsonl
uv run --locked python -m astrotrust research infer-local --help
uv run --locked python -m astrotrust research validate-splits PATH_TO_MANIFEST.json
```

The summary command above requires the existing private local export. It returns no
research labels until actual annotation sidecars are supplied. No model is downloaded
or contacted by status, validation, summary or UI navigation. Local inference runs
only through an explicitly supplied adapter; no training implementation is included.

## Reproducibility and repository map

| Path | Role |
| --- | --- |
| `benchmark/`, `astrotrust/benchmark/` | Versioned scenarios, conditions, prompts, hashes and schemas |
| `astrotrust/collector/` | Preserved frontier and consumer capture workflows and local UI |
| `astrotrust/research/` | Read-only inventory, capture label summaries, split checks and local inference |
| `astrotrust/annotations/`, `astrotrust/metrics/` | Existing annotation, agreement, adjudication and legacy draft constructs |
| `astrotrust/reviews/`, `reviews/` | Independent construction review, frozen packets and blank forms |
| `docs/` | [Methodology](docs/methodology.md), plan, audit, [paper outline](docs/research-paper-outline.md) and protocol guidance |
| `data/`, `analysis/`, `experiments/` | Governance, analysis boundaries and experiments |
| `docs/archive/` | Explicitly superseded survey-era proposals and original document bytes |
| `tests/`, `tools/`, `.github/` | Integrity, compatibility, UI checks and CI |

Raw text, canonical and submitted prompts, settings observations, all metadata
revisions and original exports are retained. New analysis uses separate artifacts;
it never rewrites collection history. Keep pilot, training, validation and held-out
test families disjoint, including related translations/paraphrases and consumer
variants. Hash checks aid reproducibility but cannot authenticate remote origins.
See [data governance](data/README.md), [ethics](docs/ethics.md) and
[benchmark card](docs/benchmark-card.md).

## Verification

Python 3.12+ is required. After installing locked dependencies, checks run offline:

```powershell
uv run --locked --extra dev python -m pytest
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev ruff check .
uv run --locked --extra dev mypy astrotrust tests tools
uv run --locked python -m astrotrust validate benchmark/scenarios
uv run --locked python tools/export_schema.py --check
uv run --locked python tools/export_collector_schema.py --check
uv run --locked python tools/export_consumer_schema.py --check
uv run --locked python tools/check_review_example.py
uv run --locked python tools/check_review_bundles.py
uv run --locked python tools/check_research_docs.py
```

Optional browser checks use the existing `ui` extra, an installed Chromium-compatible
browser and a local axe script; commands and limitations are in the migration audit.
CLI defaults assume this repository's assets; path overrides remain available.

Code, documentation and fictional fixtures use MIT. Generated outputs and identifying
reviewer records need separate access and redistribution decisions; Git ignores are
not access controls. `CITATION.cff` identifies development software without a published
paper or DOI. AstroTrust 2.0 names the research pivot, not a new instrument version,
package release or claim that planned experiments have been completed.
