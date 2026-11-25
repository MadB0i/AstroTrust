# Analysis workflow

No scientific estimates, figures or findings are claimed. The implemented
[capture summary](../docs/response-analysis.md) verifies hash-linked sidecar labels
and reports descriptive category counts by exact source and evaluator. With no
annotations it emits no scores. It does not rewrite evidence or calculate validated
BCAS/ADRS, rank models, infer user behavior or produce automatic reference labels.

Define contrasts, aggregation units,
uncertainty methods, exclusions, failure handling and multiple-comparison policy
before interpreting model runs. Account for repeated conditions/replicates nested
within scenarios; prompts are not independent population samples.

Preserve individual annotations, adjudication records and rubric revisions. BCAS
and ADRS have no numeric formula yet. Establish validity and reliability before
choosing a summary scale. Keep development/validation material distinct and report
language/domain differences and ambiguous cases. Derived artifacts belong in ignored
`analysis/outputs/` with reproducible scripts and input/version provenance when added.
