# AstroTrust

**Work in progress — research foundation, without model runs or results.**

AstroTrust studies observable model behaviour around astrological beliefs, with an
initial India-focused context. **AstroTrustBench** is its controlled, multilingual
benchmark component. The working paper direction is *When AI Reads the Stars:
Trust, Personalization, and Sycophancy in AI-Generated Astrological Advice in India*.
This is a research direction, not a published paper.

The research question is: how do large language models respond to astrological
beliefs, and can personalization, user framing, confidence, or source presentation
influence trust and willingness to rely on AI-generated astrological advice?

This repository neither endorses nor rejects astrology, judges believers, nor
assumes AI is manipulative. It measures responses under specified conditions.
It does not calculate charts or define correct astrological predictions.

## Current instrument

The internal checkpoint is [instrument-v0.1](docs/instrument-version.md): English-only
development fixtures at the construction-review stage, without validated metrics,
model results or a participant study. This is not a published benchmark release.
Two [pending human-review bundles](reviews/pending/README.md) are prepared; independent
review is still pending and [benchmark expansion is blocked](docs/scale-up-gate.md).

Eight fictional development scenarios cover career, education, relationships,
finance, health, relocation, family and everyday decisions. Each can render a
matched English trio: neutral, positive expectation and negative expectation.
Only the belief sentence changes. Emotion and personalization are separately
represented; they must be tested in matched comparisons rather than mixed into
belief contrasts. Shared context is essential: otherwise an apparent belief effect
could be caused by changed facts, emotional tone or requests.

English text is a development draft. Hindi (`hi`) and Assamese (`as`) are expected
languages with translations pending. No multilingual equivalence is claimed.
All research-use rendering requires recorded human review. Structural validation
does not establish construct validity, ethical readiness or linguistic equivalence.

BCAS (Belief-Conditioned Agreement Score) and ADRS (Astrological Decision Reliance
Score) are provisional constructs represented by qualitative annotation records.
There is no numerical scoring formula, validated scale, judge or leaderboard.
The [draft annotation handbook](docs/annotation-handbook.md) now distinguishes
response labels from matched comparisons. An ordinal reliance component is a draft
rubric, without an ADRS aggregate. The [review workflow](reviews/README.md) provides
partially blinded construction-review packets, annotation validation, two-rater
agreement and separate adjudication records. No actual human reviews exist yet.
Response analysis alone cannot measure human trust or actual reliance.

## Local use

Python 3.12 or newer is required. From the repository root, with `uv` installed:

```powershell
uv sync --locked --extra dev
uv run --locked --extra dev python -m astrotrust validate benchmark/scenarios
uv run --locked --extra dev python -m astrotrust inspect atb-career-001
uv run --locked --extra dev python -m pytest
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev ruff check .
uv run --locked --extra dev mypy astrotrust tests tools
uv run --locked --extra dev python tools/export_schema.py --check
uv run --locked --extra dev python tools/check_review_example.py
uv run --locked --extra dev python tools/check_review_bundles.py
```

Alternatively, `python -m pip install -e ".[dev]"` supports development with pip;
it resolves dependency ranges rather than reproducing the committed `uv.lock`.
Installation may access package indexes; the tests, validation and renderer work
offline after dependencies are installed. No provider credentials are needed.
The JSON sources are deliberately repository assets, not bundled wheel data;
CLI defaults assume the repository root, with path overrides available.

## Repository map

| Path | Role |
| --- | --- |
| `benchmark/` | Scenario JSON, template, language registry, exported schema and protocol |
| `astrotrust/benchmark/` | Typed conditions, scenarios, prompts and future run records |
| `astrotrust/validation/` | Strict loading, duplicate detection and limited privacy warnings |
| `astrotrust/metrics/` | Provisional human-observation interfaces |
| `astrotrust/annotations/` | Versioned response/comparison records, agreement and adjudication |
| `astrotrust/reviews/`, `reviews/` | Offline construction-review exporter, example and blank forms |
| `astrotrust/collector/` | Offline manual frontend pilot capture, immutable raw text and portable exports |
| `docs/` | Methodology, benchmark card, ethics and terminology |
| `experiments/` | Future run protocol; no API integration |
| `survey/` | Scope boundary for a later consented human study |
| `data/`, `analysis/` | Governance and future analysis constraints |
| `tests/`, `tools/` | Offline invariants and schema export |

## Exploratory manual capture

The [AstroTrust Manual Collector](docs/manual-collector.md) captures responses that a
researcher manually copies from public frontends. Launch from the repository root:

```powershell
uv run --locked python -m astrotrust collect
```

Open the printed local URL. Choose a scenario/condition, copy its exact prompt,
manually start a fresh frontend conversation, paste its complete response and record
the exact UI model label/settings. A local SQLite store preserves raw text, hashes
and metadata revision history; JSONL, CSV and full Markdown reports provide exports.
Raw pilot files under `data/pilot/` are Git ignored. No model request, scraping or
scoring is performed. The initial 27-slot matrix starts empty. Collection remains
**Exploratory Pilot — not frozen benchmark data** and satisfies no human-review gate.
The collector has a separate `manual-1.0` schema; `instrument-v0.1` is unchanged.

**Do not inspect or score earlier responses while deciding whether to continue collection.**

## Reproducibility and limits

Source revisions, explicit conditions, template versions, prompt hashes and complete
message snapshots connect a future response to its inputs. Run records preserve
provider/model identifiers, settings, replicate number, timezone-aware timestamp,
raw response, evaluator version, code revision and environment record. Unknown
provider details stay null. Deterministic rendering does not imply deterministic
remote generation, even with a seed. Provider updates and defaults require capture.

These eight fixtures exercise the instrument. Their adult contexts and deliberately
coarse profiles do not represent India, particular traditions, or the distribution
of astrological use. Wording and stakes assignments need independent review.
There is no sample-size claim, effect estimate, human study or fabricated output.

## Next milestones

1. Independently review the eight English scenarios using the construction-review packet.
2. Review the handbook and high-stakes boundaries; define translation/review roles
   before producing Hindi and Assamese equivalents.
3. Prespecify a small response-annotation pilot, including agreement criteria and
   category coverage; assess handbook usability and provisional constructs.
4. Satisfy the [proposed scale-up gate](docs/scale-up-gate.md), then freeze and
   preregister the expansion design before broader model runs. Retain all revisions
   and attempted runs; human-review multilingual equivalents before research use.
5. Design a separately approved, consented randomized human study of trust and reliance.

Code, documentation and the current synthetic fixtures use MIT; future participant
data require separate consent, governance and licensing. See [data governance](data/README.md),
[methodology](docs/methodology.md), [benchmark card](docs/benchmark-card.md) and
[ethics](docs/ethics.md). `CITATION.cff` identifies the software using the verified
repository-owner handle; personal attribution requires maintainer confirmation
and no DOI or publication is asserted.
