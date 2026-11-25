# AstroTrust 2.0 — research plan

17 October 2026 · independent research · unvalidated instrument · exploratory data

## Scope and rationale

Primary question: **How reliably do AI systems distinguish astrology-based beliefs
from evidence-supported advice, particularly in consequential decision-making scenarios?**
The unit of study is an AI-system response in a documented interaction. The project
does not test astrology's predictive validity, measure public opinion or infer
human trust, reliance, harm or benefit from response text.

The public participant survey was discontinued by the researcher's scope decision
to concentrate on reproducible system evaluation. No participant questionnaire,
recruitment program, consent form or public survey application was implemented.
This is not evidence that human research lacks value or that a survey failed.
Historical proposals are [archived with their original bytes](archive/README.md).
Independent construction review, annotation and adjudication continue; they are
measurement-quality work, not the abandoned public survey.

## A. Frontier model evaluation

Preserve the 27 manually collected exploratory responses, all SQLite snapshots,
exact prompts, settings observations and original JSONL/Markdown exports. At this
audit the captures concern one career scenario, three belief conditions, three
frontend products and three replicate slots per product/condition. Record counts
do not establish 27 independent units or adequate sample size. Frontend labels
are observed UI text; model versions and sampling defaults may be unknown.

Keep `manual-1.0`, `instrument-v0.1`, template hashes and collection history intact.
Do not convert captures into controlled API runs: hidden context and frontend
settings cannot be reconstructed. Analyze with separate, hash-linked
[capture annotation sidecars](response-analysis.md). Preserve exact evidence spans,
uncertainty, independent evaluator votes, and rubric versions. Descriptive label
counts are implemented; numerical BCAS/ADRS scoring remains undefined and unvalidated.
Matched comparison annotation in the existing controlled-run workflow remains intact.
Manual matched comparisons require a separately reviewed extension that accounts
for hidden settings and protocol deviations; no automatic conversion is provided.

The existing stopping rule remains: do not inspect or score earlier responses while
deciding whether to continue collection. The pivot does not retrospectively freeze
the pilot or authorize adaptive stopping. Record a closure/next-wave decision first.

## B. Consumer astrology app evaluation

Keep the working collector, separate database, fixed prompt registry,
`consumer-1.1` schema and fixed fictional profile snapshot/version/hash. Zero consumer
captures were present at audit; collection remains pending. Never enter real birth
details or loosen `not_used`, requested-versus-submitted fields, gender gating,
interaction mode, exact transcript/protocol note, or immutable interaction hash rules.

For each service capture, record the observed app identity, access/cost/type,
AI/human involvement claims, field requests, exact submitted prompt and profile,
additional steps, raw response and timestamp. Underlying model identity is unknown
unless actually disclosed; no backend identity is inferred from a service's marketing.
Record configuration observations and omissions in existing metadata/protocol notes;
do not introduce a schema change to manufacture comparability.

Compare descriptive advice patterns by protocol and service. Disclose differences
in prompt, profile, account/session settings, app updates and interaction histories.
Do not pool consumer outputs into frontier matrix slots or present them as identical
controlled model conditions. Preserve all attempted captures, failures and deviations.

## C. Local small-model baselines

The [local inference interface](local-models.md) is implemented with a Python Protocol
and an explicitly supplied command adapter. It has no provider SDK dependency,
automatic downloads, cloud endpoint or training path. Synthetic test adapters verify
the interface; they are not model experiments. Qwen and Gemma are possible future
families, not selected or evaluated checkpoints.

Start with a pinned, already installed model and tokenizer; record artifact hashes,
quantization, runtime/version, chat template, hardware, exact messages and decoding
settings. Use the same documented conditions where feasible and describe any extra
system instructions. Save each completion and failure in a new `local-attempt-1.0`
file, including the original request, hashes, runtime description, settings,
code revision/dirty status and environment. Current requests are exploratory only.
Independent review and protocol freeze are still required before confirmatory use.

No large model download or training is authorized by this plan. A runtime-specific
adapter and model installation are pending researcher choices, not hidden defaults.

## D. AstroGuard — proposed experimental extension

AstroGuard is a proposed response classifier or small-model adaptation for flagging
potentially misleading or unsafe astrology-based advice. It is not a trained,
validated, deployed or proven safety system. Its task is advice-content assessment,
not scoring believers or deciding whether a person should receive services.

Prespecify label meanings using the draft handbook: unsupported certainty,
astrology's role in consequential action, practical grounding, professional-guidance
displacement, and ambiguous or mixed advice. Disclaimers, astrology mentions or
skepticism alone must not determine a safety label. Final operational definitions
need independent subject-context review and examples/counterexamples.

| Candidate | Planned experiment | Status |
| --- | --- | --- |
| Deterministic rules | Versioned patterns with explicit evidence spans and abstention; select thresholds only on training/validation material | Proposed; no performance claims |
| Untuned small model | Frozen classifier prompt and decoding; record exact model and judge outputs separately from human references | Interface prepared; classifier experiment pending |
| Optional fine-tuned model | Adapt only after approval, sufficient independently annotated data and split freeze; document objective, checkpoints and training data | Proposed; no training implementation |
| Held-out evaluation | Compare all frozen candidates on the same untouched scenario families, with leakage audit and independent reference labels | Pending; no results |

Report per-class precision/recall and confusion matrices only when real reference
labels exist, along with abstention coverage, consequential-domain errors, subgroup
limitations and false alarms on respectful acknowledgment. Predefine handling of
uncertain/unratable cases, failures and evaluator disagreements. If uncertainty
intervals become appropriate, justify scenario-level dependence and resampling
before analysis. Do not invent sample sizes, effect sizes, intervals or improvements.
Fine-tuning may fail or worsen performance; compare it with both simpler baselines.

## Data separation and reference judgments

The 27 captures are pilot evidence, not training or held-out evaluation data.
Maintain four separate roles: exploratory pilot, training, validation and held-out
test. Assign whole scenario families before model/prompt/rule selection; keep all
belief variants, replicates, languages, paraphrases and related consumer prompts
together, even across scenario revisions and systems. Use a versioned split manifest
with rationale and hashes. `research validate-splits` rejects shared family, scenario
hash, prompt hash or response hash across roles and duplicate run assignments.
It checks declared provenance, not semantic equivalence or whether the researcher
has already seen material. Review family groupings and corpus completeness manually.
Pilot material must not later be relabeled as an untouched test set.

Keep manually annotated reference judgments, model judgments and later adjudications
in separate records. Human labels are fallible references; measure agreement and
preserve disagreement before adjudication. A model's self-assessment is not verified
ground truth. Do not train or tune using held-out responses, labels or paraphrases.
Training adapters and split generation are not implemented.

## Roadmap and implementation boundary

1. Completed engineering: preserve evidence/instruments, retire survey scope, update
   workstation navigation, add read-only inventory, capture label summaries,
   split validation and opt-in inference interface.
2. Pending collection: consumer app captures under the unchanged fixed-profile
   protocol; record a prespecified collection schedule and completion criteria.
3. Pending measurement: independent construction review and handbook calibration;
   define the pilot closure, annotation panel, exclusions and analysis protocol.
4. Pending experiments: choose an installed local checkpoint/runtime and run an
   inference-only pilot after recording the model/protocol manifest.
5. Proposed extension: review AstroGuard definitions, collect disjoint annotated
   families, freeze baselines, then conduct held-out evaluation. Adaptation requires
   separate approval. No automatic promotion from software tests to research readiness.

The [scale-up gate](scale-up-gate.md) remains in force. English fixtures are drafts;
Hindi/Assamese equivalents remain pending. All deviations, failed attempts and
inconvenient findings must be retained. The [paper outline](research-paper-outline.md)
separates implemented methods, exploratory evidence and planned experiments.
