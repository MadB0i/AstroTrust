# Pending English construction review — researcher instructions

These are frozen **uncompleted** bundles for `instrument-v0.1`. No reviewer has
been recruited, contacted or represented as having completed a review by this tooling.

| Bundle | Seed | Delivery contents |
| --- | --- | --- |
| `reviewer-a/` | `20261007` | `instructions.md`, `packet.md`, `feedback.md`, optional `packet.json` and `feedback.template.json` |
| `reviewer-b/` | `20261008` | The same five files, with a different scenario/candidate order |

These seeds differ from the public illustrative example. Send each person only
their own folder, with a private return channel and deadline supplied separately.
Do not send this README, the other bundle, the repository, example or keys. Confirm
that two independent people can assess the English/contextual wording; record their
relevant competence and any prior exposure privately. They need no Python or Git.

Assigned stakes, internal scenario/condition labels, researcher rationales and
expected interpretations are absent from each delivery folder. Reviewers independently
propose stakes. Prompt semantics remain visible and the source repository is public,
so this is partial metadata blinding, not guaranteed concealment against consultation.
Someone already familiar with the instrument needs that exposure disclosed; new
opaque IDs do not erase familiarity. Do not treat random order as statistical
counterbalancing or proof of independence.

## Regenerate packets and private keys

Use the checkpoint commit's sources in a separate checkout when later wording changes.
Both output paths must be new. These commands reproduce delivery files and recreate
keys without committing the private keys:

```powershell
python -m astrotrust review export benchmark/scenarios --seed 20261007 --output reviews/generated/reviewer-a --mapping reviews/private/key-a.json
python -m astrotrust review export benchmark/scenarios --seed 20261008 --output reviews/generated/reviewer-b --mapping reviews/private/key-b.json
python tools/check_review_bundles.py
```

The checked-in `pending/` folders are delivery snapshots, not writable workspaces.
`reviews/private/`, `reviews/generated/` and `reviews/submissions/` are ignored;
ignores do not replace access controls, suitable storage or agreed data handling.
Retain keys privately during review, or regenerate them from the source snapshot.

## Receive, validate and compare

Retain each returned file unchanged in restricted storage. The organizer assigns
pseudonyms privately; no real names or personal histories belong in the scoring file.
Copy returned files to ignored `reviews/submissions/returned-a.md` and `returned-b.md`
(JSON is also supported). Then run:

```powershell
python -m astrotrust review import reviews/submissions/returned-a.md --packet reviews/pending/reviewer-a/packet.json --output reviews/private/import-a
python -m astrotrust review import reviews/submissions/returned-b.md --packet reviews/pending/reviewer-b/packet.json --output reviews/private/import-b
python -m astrotrust review validate reviews/private/import-a/feedback.json --packet reviews/pending/reviewer-a/packet.json
python -m astrotrust review validate reviews/private/import-b/feedback.json --packet reviews/pending/reviewer-b/packet.json
python -m astrotrust review summarize --feedback reviews/private/import-a/feedback.json reviews/private/import-b/feedback.json --mappings reviews/private/key-a.json reviews/private/key-b.json > reviews/private/construction-summary.json
```

These are **future-use commands**, not records of completed reviews. Import refuses
existing output directories, preserves exact original bytes, and writes normalized
feedback plus a receipt with original/feedback/packet hashes. It validates all eight
items, including explicit skips, one pseudonym, timestamp and label/note requirements.
Formatting failures leave the returned original untouched: ask for a separate corrected
copy or document a checked transcription, preserving both versions and their linkage.
The Markdown parser expects the supplied table structure; JSON is an alternative.

Summary verifies keys against source snapshots, joins different blinded IDs to the
same scenario, and refuses mixed source versions, examples or identical reviewer
pseudonyms. It reports completed/skipped counts, label counts, unresolved flags and
field/stakes/status disagreements. Skips are not comparable judgments. It does not
compute effect sizes, kappa, model quality, BCAS/ADRS or overall readiness. Inspect
notes and agreeing issue flags too; a lack of disagreement can coexist with defects.

## Explicit construction adjudication

1. Preserve independent originals/imports and summary before discussion.
2. An adjudicator reviews each concern against full prompts and both original notes.
   Record the scenario/revision, original submission/receipt hashes, reviewer labels,
   final decision (`retain`, `revise`, `re-review`, or `unresolved`), reasoning,
   adjudicator pseudonym and actual timezone-aware timestamp in a separate private log.
   Distinguish construction decisions from later response-annotation adjudication.
3. Do not automatically convert feedback into scenario edits. Agree a concrete change
   explicitly; increment scenario and affected English revisions, record old/new hashes
   and rationale, and make a later Git commit preserving the checkpoint's wording.
4. Re-review changed variants and unresolved high-stakes/isolation concerns. Preserve
   inconvenient judgments and excluded/skipped items. Update gate evidence explicitly;
   two completed forms alone cannot pass the scientific scale-up gate.

Only approved, minimized public summaries may be versioned after governance review.
Actual submissions, identities, linkage keys and private adjudication notes stay private
by default. No messages are sent to reviewers automatically.
