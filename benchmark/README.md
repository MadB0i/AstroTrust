# AstroTrustBench development protocol

This is an instrument-development snapshot, not a final benchmark release. JSON
source files are one scenario per file. Python models in `astrotrust/benchmark/models.py`
are authoritative; `schema/records.schema.json` is their portable structural export.
Python additionally checks cross-field rules that JSON Schema alone does not express.
Regenerate with `python tools/export_schema.py`; CI checks drift.

## Scenario identity and taxonomy

IDs use `atb-<domain>-<three-digit-number>`, for example `atb-career-001`.
Numbers are permanent opaque identifiers, not rankings; IDs are never reassigned.
Revise wording by incrementing scenario `revision` and each changed language's
`revision`. Change the ID if the underlying situation/domain changes. Never edit
a released version in place. Major schema changes need an explicit migration;
unsupported `schema_version` values fail rather than being interpreted optimistically.

| Domain | Fixture | Stakes |
| --- | --- | --- |
| career | Job interview | medium |
| education | Admission application | medium |
| relationships | Relationship conversation | medium |
| finance | Business loan decision | high |
| health | Pending clinical evaluation | high |
| relocation | Move to another city | medium |
| family | Family gathering | low |
| everyday | Leisure outing | low |

`relocation` covers migration/relocation; `everyday` covers everyday decisions.
Stakes reflect plausible consequences and reversibility **in this scenario**.
Low means limited reversible material consequences; medium means meaningful costs
or social/planning consequences; high means potentially substantial financial,
health or other difficult-to-reverse consequences. These are contextual draft
classifications, not domain defaults, safety verdicts or desired response labels.
Every fixture supplies a rationale. The development set has 2 low, 4 medium and
2 high stakes scenarios, chosen by taxonomy before model runs. It is neither
population-weighted nor exhaustive. Future sampling and expert review must address
coverage across stakes within domains and avoid selecting only dramatic cases.

## Fields and controlled rendering

A scenario records schema version, stable ID/revision, title, domain, stakes/rationale,
synthetic profile, nullable synthetic birth context, allowed experimental levels,
expected languages, localized text, researcher notes and provenance. No expected
prediction field is allowed; unknown fields fail validation. All fixtures omit
birth information to avoid introducing calculation prerequisites. If later needed,
birth context must be invented, justified, included consistently in localized prompt
context and independently reviewed; the renderer does not compute or infer it.

The six template slots are profile, situation, belief, emotion, personalization and
question. Each appears once. The profile and situation remain visible at both
personalization levels; the manipulation is the explicit request to address this
person, not a change in available information. This operationalization is narrower
than birth-data personalization. A changed-information experiment needs a separate
documented protocol.

`belief_conditions()` yields exactly three conditions with all other dimensions
held fixed. Defaults are English, emotionally neutral, generic framing. Rendering
these gives **24 English development prompts**, not responses. The schema permits
2 emotion × 2 personalization levels, but the CLI does not silently expand a
factorial design. Researchers must specify their contrasts and interactions in an
experiment manifest. No conclusions can follow from unreviewed emotional phrasing.

`research_use=True` in `render_prompt` rejects draft text. The CLI intentionally
previews development text, so it is not an approved-run entry point. Reviewer
metadata are records of a process, not proof that review occurred; verify those
records before freezing the instrument.

## Language protocol

`expected_languages` lists `en`, `hi`, `as`; `language_variants` contains available
text only. `languages/registry.json` is a descriptive status inventory, not a
translation source. Missing variants fail rendering. Never substitute English for
a missing language or silently auto-translate. Each language must contain all
belief, emotional and personalization frames, shared context and baseline question.

For Hindi and Assamese, use fluent human translators/reviewers to preserve outcome
direction, pragmatic force, uncertainty, vulnerability and personalization. Record
translation provenance, disagreements, adjudication and revision in review records;
use pseudonymous reviewer IDs. Machine assistance, if used, must be disclosed and
human-reviewed. Independently review English, too. Back-translation can aid review
but cannot alone establish equivalence. Cross-language effects may reflect wording,
cultural pragmatics or model capability, not just belief framing.

## Validation boundary

`python -m astrotrust validate benchmark/scenarios` rejects malformed JSON, duplicate
JSON keys or scenario IDs, unknown fields, invalid domains/stakes/languages, missing
fields, incomplete/duplicate condition levels and unsupported schema versions.
It loads the versioned template and renders the matched trios for available languages.
PII-like regex warnings screen email, some phone/identifier patterns and precise
dates without printing matched values. They miss names, unusual formats and many
identifiers, and can flag invented text. Manual provenance/privacy review is required.
Successful validation establishes structure and renderability, not scientific readiness.
