# Review and annotation workflow

Construction review evaluates prompts, not nonexistent responses. The committed
`examples/seed-20261005/` bundle demonstrates export from the eight current invented
scenarios: 24 English belief prompts plus two two-option wording sets per scenario.
It contains **no human feedback or model responses**. Its feedback form is pending.
Publicly committing its researcher key permits demonstration/reproduction; real
reviewers should receive only a fresh reviewer folder and not this repository/key.
The two fresh [pending bundles and import/adjudication process](pending/README.md)
are the current dispatch checkpoint. Reviewers can fill Markdown without Python/Git.

## Construction review now

```powershell
python -m astrotrust review export benchmark/scenarios --seed 20261005 --output reviews/generated/reviewer-a --mapping reviews/private/key-a.json
python -m astrotrust review validate reviews/generated/reviewer-a/feedback.template.json --packet reviews/generated/reviewer-a/packet.json
```

Both output paths must be new. Mapping inside the reviewer directory is rejected;
exports refuse overwrite. Share only the five reviewer-folder files: `packet.md`,
`packet.json`, `feedback.template.json`, `instructions.md` and `feedback.md`.
Use a separately recorded seed
per reviewer if counterbalancing order; never let one reviewer see several versions
of the same packet during independent review. Code sorts stable SHA-256 keys derived
from the explicit seed and scope: scenario, candidate, additional set and option order
are randomized reproducibly across platforms. Exporter version, seed, original
scenario/template snapshots and variant mappings stay in the separate researcher key.
There is no randomized assignment of participants or human survey here.

Blinding hides internal scenario/title/domain/condition fields, proposed stakes,
researcher notes, source provenance and metric names. Necessary prompt content
remains visible, and may reveal domain/framing. The form names the reviewed constructs
because reviewers must assess isolation; this is partial metadata blinding, not
concealment of what is being compared. Stakes are independently proposed before
researcher classification/rationale is disclosed. A public example is unsuitable
for a reviewer who has already studied its key.

Reviewers use `acceptable`, `issue`, `unclear` or `not_applicable` for each question:
understandability, plausibility, belief isolation, added facts, leading wording,
emotion/personalization isolation, stakes, cultural respect, translation clarity,
stereotypes and high-stakes handling. Explain issues/ambiguities in field-specific
notes and flag adjudication. Set `reviewer_id` to a pseudonym, record an actual
timezone-aware timestamp, propose stakes, mark completed (or explicitly skipped),
and change batch purpose to `private_review` in a **separate copy**. The validator
rejects pending judgments in a completed submission. Review the scenario's English
only; translation clarity flags possible future problems, not Hindi/Assamese equivalence.
The packet includes self-contained field definitions and completion instructions.
`stakes_plausibility` judges whether context supports the reviewer's independently
proposed classification; researchers compare it with the hidden label only afterward.

Keep independent submissions in ignored `reviews/submissions/` or `reviews/private/`.
Identity linkage, private comments and consent/access records must not be committed
automatically. These ignores are not privacy/access controls. After independent
completion, researchers use the keys to join reviews by original scenario/revision
and document adjudication/revisions separately, preserving each original. No human
review has happened merely because a form parses. Do not ask whether astrology is true.

## Response annotation later

Read [annotation handbook](../docs/annotation-handbook.md). `templates/` contains
unfinished response and trio JSON forms. Their null placeholders intentionally
fail submission validation; they do not invent runs or reference answers.
When actual responses exist, copy a form into ignored `data/private/annotations/`,
fill every field/support, and obtain exact targets with
`astrotrust.annotations.models.reference_from_run(validated_run)`.
Use one batch per independently collected set, then assemble a combined batch
without overwriting source files. Real names are not annotation fields.

```powershell
python -m astrotrust annotations validate data/private/annotations/independent.json --runs data/runs/pilot
python -m astrotrust annotations agreement data/private/annotations/independent.json --kind response --field decision_reliance --raters rater-a1 rater-b1 --weights linear --runs data/runs/pilot
python -m astrotrust annotations agreement data/private/annotations/independent.json --kind comparison --field conclusion_direction --raters rater-a1 rater-b1 --runs data/runs/pilot
```

These are future-use command examples, not executed experiments or reports. Source
validation checks completed runs, target provenance, spans/excerpts, and matched
model/settings/replicate/non-user context. Verify actual user prompt control against
the frozen sources too. Without `--runs`, validation is explicitly structural only.
Agreement is descriptive, conditional on usable labels, and rejects example batches;
see [methods and exclusions](../docs/agreement.md). No BCAS/ADRS aggregate is calculated.

## Adjudication without overwrite

Save one proposed final annotation in a separate batch, with a new annotation ID
and adjudicator pseudonym. Select the original annotation IDs for exactly that unit:

```powershell
python -m astrotrust annotations adjudicate data/private/annotations/independent.json data/private/annotations/proposed-final.json --ids ann-a1 ann-b1 --adjudication-id adj-001 --reason "Recorded resolution of the label disagreement" --timestamp 2026-10-05T12:00:00+05:30 --output data/private/annotations/adjudication-001.json
python -m astrotrust annotations validate data/private/annotations/adjudication-001.json --originals data/private/annotations/independent.json --runs data/runs/pilot
```

The timestamp above illustrates syntax; use the actual adjudication time. The output
must not exist; source files remain unchanged. The new record stores final labels,
original IDs/hashes, decision reason and timestamp. Clarification/version proposals
are supported by the `adjudicate` library function. They require a reviewed handbook/
schema revision before changed meanings are applied; no silent retroactive migration.
Adjudicated records cannot be passed to the agreement command as independent labels.

Only intentionally synthetic examples, blank templates, reviewed documentation and
explicitly approved, suitably governed public releases belong in Git. Never commit
actual reviewer identities or private feedback by default. No networking, provider
client, paid service, spreadsheet UI, database or web app is needed.
