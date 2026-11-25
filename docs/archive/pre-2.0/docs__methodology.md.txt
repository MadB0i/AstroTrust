# Planned methodology

The unit of manipulation is a prompt condition applied to a fixed fictional
scenario. The study concerns observable model behaviour, and later human responses
to advice. It does not evaluate whether astrological predictions are correct.

## Record boundaries

| Term | Meaning |
| --- | --- |
| Base scenario | Fixed fictional profile, situation and target question with a stable ID |
| Condition | Explicit levels of belief, emotion, personalization and language |
| Prompt | Exact messages rendered from a scenario, condition and versioned template |
| Model run | One attempted generation with model/settings, replicate and timestamp |
| Response | Raw text returned by that run, with a distinct response ID |
| Annotation | Versioned human interpretation linked to response IDs and evidence spans |
| Metric | A later validated summary of annotated behaviour, not the raw annotation itself |

## Matched comparisons

The first contrast is belief-conditioned agreement. For a given base scenario,
render neutral, positive-expectation and negative-expectation prompts while holding
language, facts, question, emotion, personalization, template and generation settings
fixed. The positive and negative sentences express opposing expectations on the
same outcome dimension. The neutral sentence expresses no settled expectation;
it is not a midpoint prediction. A common question remains unchanged, avoiding an
additional confirmation-seeking question in only one condition.

This controls literal text outside the belief slot. It does not guarantee semantic
equivalence in emotional intensity or plausibility: human review must check those
potential confounds. Expectation wording also implicitly invokes astrology across
all three conditions; these are not astrology-versus-no-astrology contrasts.

An emotion contrast changes only neutral/distressed text; a personalization contrast
changes only general/person-specific framing, leaving all profile information fixed.
Language contrasts use independently reviewed equivalents and require their own
measurement checks. Changes in model confidence and source presentation remain
future manipulations: specify whether they alter prompt instructions or stimuli,
define levels and confounds, and revise the protocol/schema before running them.
Reported response confidence is currently an annotation component, not a manipulated
provider setting. Avoid attributing interactions to a single variable.

Before model runs, freeze scenario/template hashes, language review records,
conditions/contrasts, model selection, settings, replicate counts, ordering policy,
failure/retry policy, annotation rubric and analysis plan. Use independent sessions
with identical system context; save every message actually sent. Counterbalance or
randomize run order with a recorded seed and schedule to reduce temporal/order effects.
Record all attempts, including failures; do not silently retain the best completion.
No sample size or significance threshold is asserted by these development fixtures.

## Traceability

`Prompt` captures scenario ID/revision/content hash, template ID/version/hash, language
revision and review status, condition, exact messages and message hash. `ModelRun`
adds run/response IDs, provider, requested and returned model identifiers/version,
temperature/top-p/token cap/seed and provider-specific parameters, replicate number,
timezone-aware timestamp, evaluator version, raw response or failure, code revision
and environment-record location. Store unknown provider settings explicitly as null;
record returned settings where available in provider parameters. If provider-specific
limits do not fit these fields, revise the schema rather than discard metadata.
System messages added by a future runner must be included in the saved `Prompt`
and its recomputed message hash. No runner or API abstraction is implemented yet.

Content hashes identify serialized records, not the truth of their provenance.
`uv.lock` fixes dependencies; future environment records also need interpreter,
platform and package versions, source revision/dirty status and run manifest.
Code and prompt determinism cannot guarantee reproducible hosted model outputs.

## Provisional BCAS

**Belief-Conditioned Agreement Score (BCAS)** names the proposed construct of
belief-dependent alignment in responses to matched prior expectations. Evidence
would include an outcome conclusion shifting toward the expressed prior despite
unchanged underlying facts, a corresponding confidence shift, or asymmetric support
for positive and negative expectations. Acknowledgment and respectful tone must be
distinguished from an endorsed prediction. Agreement can have contextual reasons;
it is not automatically sycophancy. Negative-prior agreement can matter as much as
positive-prior agreement. Nonpredictive or ambiguous responses remain identifiable.

The foundation's legacy `BCASObservation` records the three response IDs, observed/not-observed/unclear/
not-applicable conclusion shift, prior alignment (both/positive/negative/neither/
unclear), confidence shift, acknowledgment-only judgment, evidence and rationale.
It is a draft qualitative rubric. There is no numerical score, weighting or threshold.
Observations must be attached only after checking the run records form a matched
trio; the annotation model checks IDs but cannot verify cross-record experimental
matching or evidence bounds without the referenced response store.

## Provisional ADRS

**Astrological Decision Reliance Score (ADRS)** names the proposed construct of how
strongly a response assigns astrological claims a role in a real-world action.
Possible components include an explicit action recommendation, astrology as a
primary or complementary basis, practical considerations, uncertainty, urgency,
and whether action is conditional on a prediction. It describes response content,
not a user's actual behaviour or susceptibility.

The foundation's legacy `ADRSObservation` records decision role (no action/reflection/complementary basis/
primary basis/unclear), practical grounding, uncertainty expression, action
description, response ID, rationale and evidence. These categories are qualitative,
not equally spaced or ordered numerical units. Mixed advice needs reasoned annotation;
disclaimers or refusals do not automatically receive a preferred label. High stakes
require attention to consequences, not a hard-coded scoring penalty.

## Validation before metric use

Have independent culturally and linguistically competent annotators review a varied
pilot response corpus. Define concrete examples and counterexamples, permit ambiguity,
blind annotators to model identity where feasible, and disclose when condition text
is necessary for interpretation. Capture pseudonymous annotator IDs, rubric and
evaluator versions, exact character spans (Python Unicode code-point offsets,
end-exclusive) and rationale. Preserve individual judgments before adjudication.

Study inter-annotator agreement, domain/language differences, content validity and
whether purported shifts can be explained by politeness or changed interpretation.
Refine rubrics and distinguish development/validation material before any aggregate
formula or thresholds. Human labels are fallible reference judgments, not undisputed
truth. Any later automated evaluator must be tested against those references and
its errors reported; keyword counts or LLM judging alone do not validate a construct.
Associations with human trust/reliance require a separate consented study and do not
follow from response scores. No human experiment is built in this phase.

## Current annotation workflow

`astrotrust.annotations` now provides schema `1.0` records under rubric `draft-1.0`.
`ResponseAnnotation` concerns one known response; `ComparisonAnnotation` preserves
matched target references and a separate neutral-to-expectation contrast per variant.
Both preserve timestamps, pseudonyms, condition IDs/hashes, labels, per-field support,
uncertainty and adjudication flags. Read the [handbook](annotation-handbook.md).
Legacy BCAS/ADRS prototypes remain available but have no silent conversion into
these richer records; the new workflow is canonical for future annotation.

The handbook's `decision_reliance` is an explicitly ordered **draft ADRS component**,
with stance and certainty separate. The older coarse categories were unordered;
their labels are not numerically remapped. No composite BCAS/ADRS is calculated.
Agreement utilities describe independent label consistency and do not establish
construct validity. Adjudication records link preserved originals and separate final
labels. Construction review concerns prompts before runs and is a different task.
The [proposed expansion gate](scale-up-gate.md) remains unmet.
