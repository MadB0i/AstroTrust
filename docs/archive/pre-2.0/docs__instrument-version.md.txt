# Research instrument checkpoint

**Internal instrument designation: `instrument-v0.1`.** This is a development
checkpoint for independent construction review, not a published benchmark release.

It identifies eight synthetic development scenarios, 24 English belief-framing
prompts, existing emotion/personalization wording alternatives, the draft annotation
handbook, and the offline review/annotation workflow. The health scenario and English
wording are revision 2; the other scenarios remain revision 1. There are no model
results, validated BCAS/ADRS scores, independent reviews or participant study.
English-only text does not mean the planned multilingual scope has been abandoned.

Different version fields serve different purposes:

| Identifier | Value | Meaning |
| --- | --- | --- |
| Instrument checkpoint | `instrument-v0.1` | This bounded research instrument before human construction review |
| Python/software citation version | `0.1.0.dev0` | Development package, not a benchmark result/release |
| Record schemas | `1.0` | Record structure; Python enforces additional cross-field rules |
| Annotation rubric | `draft-1.0` | Unvalidated label meanings and boundaries |
| Prompt template | `atb-controlled`, version `1.0` | Controlled rendering specification in `controlled-v1.json` |
| Review ordering/import/summary algorithms | `review-export-1`, `review-import-1`, `review-summary-1` | Reproduction and interpretation of artifacts |

The first Git commit is the immutable source snapshot for this checkpoint. No tag,
release, DOI or scientific result is created. Refer to its commit SHA when retrieving
sources or regenerating keys. The instrument checkpoint is distinct from a frozen
hypothesis/sampling design, which is still pending.

Keep dispatched reviewer files unchanged. After adjudication, revise the scenario
and affected language revision explicitly, record the reason and old/new hashes,
re-review changed wording, and create a new instrument checkpoint when appropriate.
Git retains prior wording; never replace the old review packet or hide disagreements.
The [scale-up gate](scale-up-gate.md) remains blocked.
