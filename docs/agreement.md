# Agreement methods and limits

Agreement describes consistency of **independent labels**, not truth, construct
validity, model quality, BCAS or ADRS magnitude. Never include adjudicated labels
as if independent. The CLI declines synthetic/example batches. Only tests use
toy arrays with known arithmetic; they are not scientific findings.

## Supported two-rater summaries

For a selected annotation level and label field, join records on exact response/run
IDs, or on a neutral/expectation response-ID pair. Reject duplicate labels for the
same rater/unit. Never mix response and comparison labels. Schema/rubric versions
are fixed for this draft; later incompatible versions require separate analyses.

- **Percent agreement:** exact matches / usable pairs, reported as a percentage.
  This descriptive companion can be high when one category dominates.
- **Nominal Cohen's kappa:** `1 - observed_disagreement / expected_disagreement`,
  where expected disagreement uses the two separate empirical rater marginals.
  Nominal mismatch costs one and a match zero. Appropriate for the handbook's
  unordered labels, including epistemic framing and action category.
- **Linear or quadratic weighted Cohen's kappa:** the same disagreement ratio with
  costs `abs(i-j)/(K-1)` or its square over the **complete prespecified order**.
  Enabled only for response `practical_grounding` and `decision_reliance`, whose
  draft orders are explicit. Unobserved intermediate categories remain in that order.

These formulations and available weighting conventions match the documented
[Cohen kappa interface](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html).
The implementation uses only the standard library; scikit-learn is not a dependency.
No provider evaluator or judge model is involved.

Missing rater records are reported as `n_missing`; a pair containing `unclear`,
`not_applicable`, `incomparable` or an overall unratable annotation is reported as
`n_excluded`. Those are not mapped
onto the ordinal order or silently treated as agreement. Both counts are retained
alongside `n_total` and `n_used`. Missing takes precedence when both reasons apply.
Review exclusion patterns separately: conditional agreement can overstate reliability
if difficult material is often excluded. The direct library utility can retain
ambiguity as nominal categories using `exclude=frozenset()`, under a prespecified
alternative analysis; the default CLI exclusion policy is fixed and disclosed.

Kappa is null with an explicit reason when no usable pairs remain or expected
disagreement is zero. A constant unanimous category can have 100% percent agreement
and undefined kappa; do not substitute kappa=1. Retain the category order, confusion
matrix and counts to audit the calculation. No confidence interval, universal
“acceptable” cutoff, significance test or automatic pass/fail gate is implemented.
CLI output is a JSON report retaining input-batch hash, rubric/algorithm versions,
annotation level/field, selected pseudonyms and exclusion policy; status notes go
to stderr. Keep the command and original inputs with the report.

Linear weighting provisionally treats rank steps as equal costs; quadratic weights
penalize large gaps more strongly. Neither proves equally spaced psychological units.
Choose/report weighting before inspecting agreement, preferably alongside nominal
agreement and the confusion table. The draft ADRS order itself still needs review.

## More raters and dependent material

Fleiss' nominal kappa assumes a suitable common category-count design with a fixed
number of ratings per item; it is not a drop-in replacement for named-rater weighted
agreement, missing panels or response/trio nesting. See the documented
[Fleiss kappa assumptions](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.fleiss_kappa.html).
It is not implemented before the actual annotation panel is specified.

For multiple named raters, missingness or ordinal designs, preregister an appropriate
statistic (for example, a suitable Krippendorff alpha design) after specifying the
measurement distance and sampling unit. Do not average pairwise kappas as though
that were automatically multi-rater reliability. Repeated responses/conditions and
the two contrasts from one trio share scenarios; descriptive agreement can summarize
them, but uncertainty estimates must respect that dependence, for example with a
reviewed scenario-cluster resampling plan. No such inferential procedure is assumed here.

Currently there are no real response annotations, so no scientific agreement estimate
can be reported. Pilot criteria and category coverage must be set before inspecting
future pilot results; tests establish arithmetic and joins only.
