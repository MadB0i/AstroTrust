# Consumer astrology service collector

For actual collection, use the [concise manual checklist](CONSUMER-COLLECTION-CHECKLIST.md)
and [live readiness verification](CONSUMER-COLLECTION-READINESS.md). The latter records
the observed Windows clipboard limitation and the isolated synthetic dry run.

AstroTrust 2.0 keeps this workflow active as **Consumer apps** at `/consumer`.
Navigation also exposes **Research overview**, **Frontier models**, and **Local
models**. The consumer-1.1 profile registry, hashing and storage protocol remain
unchanged. Collection was pending (zero local captures) at the 17 October 2026 audit.

This is a second exploratory workflow for manually pasted outputs from astrology
apps and websites. General-purpose LLM captures, their `manual-1.0` schema, canonical
prompts, exports and 27-slot matrix remain separate. No scraping, API integration,
model requests, scoring or automatic anonymization is performed.

## Start and storage

From `D:\Projects\AstroTrust`:

```powershell
uv run --locked python -m astrotrust collect-consumer
```

Open **http://127.0.0.1:8766/consumer**. The server binds only to loopback. Stop with
Ctrl+C. Override `--port` if occupied; the printed URL always gives the actual port.
Consumer SQLite defaults to:

```text
D:\Projects\AstroTrust\data\pilot\consumer-app-runs\collector.sqlite3
```

`--root` selects the repository root; `--database` selects a consumer database.
Keep alternate stores under ignored `data/pilot/` or outside Git. Consumer startup
opens only the consumer database. Navigating to the general-purpose workflow opens
the existing general database on demand. The standard `collect` launcher also
provides `/consumer` at `http://127.0.0.1:8765/consumer`, using the same default
consumer datastore. Avoid running concurrent collectors against a research store
unless needed; SQLite transactions and revision conflicts still prevent overwrite.

## Capture procedure

1. Choose `consumer-career-p1` or `consumer-career-p2` and **Copy Prompt**. These are
   the supplied fixed English career prompts, without surrounding quotation marks.
   Registry version is `consumer-career-1.0`; no controlled scenario/condition is implied.
2. Visit the service manually. Record its exact observed name, access method
   (`web`, `iOS`, `Android`, `desktop`, `other`), cost (`free`, `free_trial`, `paid`,
   `unknown`), visible AI/human claims and response type. Unknown remains unknown.
3. Select only names of personal fields requested. Never record values. The
   closed vocabulary includes DOB, date of birth, birth date, birth time, time of
   birth, birthplace, place of birth, gender, sex, name, current location, zodiac
   sign, relationship status, occupation, email and phone number. Selecting `email`
   records only the word `email`, never an address. Unlisted labels require an
   explicit vocabulary update; do not encode them or values into another field.
4. Explicitly select `consumer-profile-001` if synthetic profile fields were supplied,
   or `not_used` if no profile information was supplied. Use only the read-only fixed
   registry values below. Check which fields were **actually submitted**, separately
   from requested field names. Unsolicited supplied inputs must still be recorded;
   a requested field that was withheld must not be marked supplied. Never use real
   personal birth details or a custom profile.
5. Record the exact submitted prompt. If it differs from the registry, supply a
   deviation reason; the registry snapshot and its hash remain alongside it.
6. Choose the interaction scope explicitly. `initial_prompt_only` requires `not_used`;
   `prompt_and_fixed_profile_only` requires a used profile and means no additional
   exchange beyond the initial prompt and listed synthetic fields. For `multi_step`
   or `unknown`, select `protocol_note` or `transcript` and paste an exact interaction
   record. Record follow-up questions/answers, chronology, extra non-profile inputs,
   visible defaults and material omissions without inventing missing content. Never
   supply real personal details to answer an extra question. The record and its hash
   become immutable, and exports explicitly avoid initial-prompt-only attribution.
7. Paste the final raw response verbatim. The form retains exact plain-text clipboard
   strings, including CRLF and lone CR, separately from the textarea's LF display.
   Edits preserve line endings in unchanged portions. Copying from the service
   may already have lost content, formatting or line endings; document anomalies.
   Do not reconstruct missing source material. Empty responses can record failures.
8. Check the proposed timestamp and timezone. Timestamp requires an ISO-8601 UTC
   offset; timezone is an observed descriptive label. Response pasting refreshes
   the proposed time until it is manually edited.
9. Record completeness, visible truncation, additional-information requests and
   refusal/avoidance. Notes are for anomalies/provenance, without scientific judgment.
   Enter a model/engine label only when the service explicitly shows it.
10. **Save Consumer Capture** locks raw evidence. Errors retain form entries. Use
   **Start another capture** for the next planned run. Run numbers are positive
   integers independent of the general-purpose three-repeat matrix; an optional
   repeat identity describes the planned session without identifying an account.
11. Open a service in the ledger to see exact text, hashes and complete provenance.
    Metadata corrections require a reason and expected revision, retain original
    metadata, and cannot change raw prompt/response, prompt ID, supplied profile
    evidence or exact interaction evidence. Document an erroneous input-provenance
    entry in a metadata revision note; do not manufacture an independent repeat.

## Fixed synthetic profile registry

**FICTIONAL / SYNTHETIC RESEARCH INPUT — NOT PARTICIPANT DATA.** This profile was
explicitly specified as fictional research input. It is not collected participant
data, and no identity is associated with it.

| Registry property | Fixed value |
| --- | --- |
| `profile_id` | `consumer-profile-001` |
| `profile_version` | `consumer-profile-1.0` |
| `date_of_birth` | `1998-02-12` |
| `birth_time` | `10:30` |
| `birthplace` | `Guwahati, Assam, India` |
| `timezone` | `Asia/Kolkata` |
| `gender` | `male`, only when the service requires gender |

The source registry is `astrotrust/collector/consumer_profiles.py`. Its frozen typed
snapshot and read-only mapping prevent custom values and runtime replacement. Future
revisions must preserve old registry entries and hashes; change IDs/versions explicitly
rather than silently editing an existing profile.

Use the per-field copy controls for exact values. Mark a field supplied only after it
was actually entered into the service. In particular, a service may infer a timezone
from birthplace; do not mark `timezone` supplied if you did not explicitly supply it.
The gender value/copy control remains unavailable until the researcher marks that the
service requires gender. Supplying `gender` also requires an original requested-field
label of `gender` or `sex`. All other requested fields, including fields outside this
profile, remain observations and do not gain fabricated profile values.

Every capture stores `profile_id`, `profile_version`, `profile_snapshot`,
`profile_sha256`, `profile_fields_submitted` and `gender_required` (the explicit
permission attestation for using gender). A used profile must have at least one
supplied field. The server resolves the snapshot from the registry; request bodies
cannot submit or override birth values. The full snapshot includes the conditional
gender value for reproducibility, but only `profile_fields_submitted` identifies
which values were actually provided. For `not_used`, version/snapshot/hash are null
and submitted fields are empty.

Snapshot SHA-256 uses UTF-8 `canonical_json`: sorted keys, two-space JSON indentation,
unescaped Unicode and a final LF. The initial snapshot hash is
`b2ddf58dbcd59a43a3b111efe242b0067c04d4bac3096b26d7e91fc6032a31ef`.
This fixed hash is regression-tested. Capture timestamp timezone remains a separate
observation and never replaces the synthetic birth timezone.

The page displays:

> Do not enter account credentials, emails, phone numbers, API keys, cookies,
> or actual personal birth details. Record field names only.

Fields and raw pasted outputs outside the fixed field-name vocabulary are free text;
the collector cannot guarantee that they contain no sensitive data. Inspect what is
pasted before saving and inspect exports before sharing. Unsaved drafts live only in
the tab; navigation warns, but crashes cannot guarantee recovery.

## Architecture and integrity

- Separate frozen Pydantic types: `ConsumerRequest`, `ConsumerMetadata`,
  `ConsumerRevision`, `ConsumerCorrection`, `ConsumerRun`.
- Consumer record `kind=consumer_astrology_capture`, `schema_version=consumer-1.1`,
  and `source_category=consumer_astrology_service` at both record and metadata levels.
- New schema: `benchmark/schema/consumer-run.schema.json`. The existing
  `manual-run.schema.json`, controlled instrument schema and prompt matrix need no migration.
- `consumer-1.1` requires explicit profile and interaction provenance. The real
  consumer store was confirmed empty before this change; SQLite table layout needs
  no migration. Imports lacking this evidence (`consumer-1.0`) are rejected rather
  than inventing `not_used`, a profile or a single-step history. Old files are not
  automatically rewritten. General-purpose `manual-1.0` remains unchanged.
- Consumer SQLite tables `consumer_runs` and `consumer_snapshots`. General and
  consumer store constructors reject the other's tables before a writable connection;
  the server rejects selecting the same database for both workflows.
- Shared connection/transaction handling, code provenance, strict JSON parsing,
  UTF-8 SHA-256, collision-safe Markdown fences and reversible CSV formula escaping.
  Existing exporters retain their formats and consumer exports use separate functions.
- Duplicate identity: **exact service name + prompt ID + run number**. A repeat
  identity is descriptive metadata, not a bypass. Imports are atomic and never
  overwrite evidence. Corrections use append-only snapshots and reject stale revisions
  or a new identity that conflicts with another capture.
- Raw strings and hashes are immutable through collector operations. Metadata
  histories are contiguous, ordered and retained in full. Local Git revision/dirty
  state and software/collector versions document capture software provenance.
- Exact interaction text is preserved and hashed with the same verbatim clipboard
  handling as prompt/response, including CRLF and lone CR. `multi_step` and `unknown`
  histories require a nonblank exact note/transcript. Single-step scopes reject such
  extra evidence, preventing it from being hidden by a contradictory mode selection.
- `/api/consumer/*` is separate from the existing API. Consumer records never count
  toward the general matrix; legacy consumer-tagged manual records are also excluded
  from coverage. General save requests reject consumer source categories.
- Existing loopback Host/Origin checks, session token, no-store responses, payload-free
  logs, 16 MiB body limit and content security policy also cover consumer operations.

## Exports and portable validation

All commands use only the consumer datastore. Choose new output filenames: existing
files fail instead of being overwritten. Exports retain exact service names and
complete metadata/revision histories; anonymization is a later analysis decision.

```powershell
uv run --locked python -m astrotrust collect-consumer export --format jsonl --output data/pilot/consumer-exports/pilot.jsonl
uv run --locked python -m astrotrust collect-consumer export --format markdown --output data/pilot/consumer-exports/pilot.md
uv run --locked python -m astrotrust collect-consumer export --format csv --output data/pilot/consumer-exports/pilot.csv
uv run --locked python -m astrotrust collect-consumer validate data/pilot/consumer-exports/pilot.jsonl
uv run --locked python -m astrotrust collect-consumer validate data/pilot/consumer-exports/pilot.csv
uv run --locked python -m astrotrust collect-consumer --database data/pilot/consumer-import/collector.sqlite3 import data/pilot/consumer-exports/pilot.jsonl
uv run --locked python -m astrotrust collect-consumer export --format markdown --run-id consumer-REPLACE_WITH_REAL_ID --output data/pilot/consumer-exports/single.md
```

JSONL is authoritative: complete records and exact UTF-8 string hashes. CSV carries
flat fields plus `record_json`, using the existing explicit reversible formula-safe
encoding; validation checks every flat field against the record. Markdown includes
fenced exact prompt/response and complete JSON provenance. Fence framing adds a
newline; reconstruct exact strings from embedded JSON or JSONL. Markdown is a report,
not an import format. Browser exports include all consumer captures and download to
the browser's download folder. General JSONL/CSV cannot import as consumer records
and consumer exports cannot import as general records.

All formats include the fixed profile ID/version/snapshot/hash, actual supplied field
keys, interaction scope and exact additional-interaction text/hash. Requested fields
remain in separate metadata. Markdown shows synthetic-input and interaction sections
explicitly; it does not label a profile-dependent or multi-step response as caused
by the initial prompt alone. Service names remain unchanged.

## Research limitations

These are exploratory pilot captures, not frozen benchmark data. The two prompts
are not a validated new scientific instrument or part of the existing 27-run design.
BCAS/ADRS remain unvalidated; no scores or conclusions are produced. Prespecify
service selection, collection order, fictional-profile procedure, repeat plan and
stopping rules independently of observed responses. Retain partial/refusal/failure
captures rather than selectively replacing them.

The fixed profile improves input reproducibility; it does not control service-side
geocoding, calendar conventions, default timezone interpretation or undisclosed
settings. Record relevant visible transformations/defaults and extra exchanges in
the protocol record. A note can document incomplete evidence; it is not a substitute
for claiming a complete transcript. Structured input fields reject real/custom birth
values, but free-text prompt/response/interaction fields still require researcher
privacy review. Do not paste real personal values into them.

Visible service claims and model labels do not verify hidden generation mechanisms,
human involvement, backend identity or independence. Exact observed name spelling
defines duplicate identity, so different spellings are not automatically merged.
Hashes detect stored inconsistency; they do not authenticate the service or recover
source bytes, images, citation widgets, clipboard omissions or earlier transformations.
Timezone labels are observed text; offset presence is validated, but labels are not
cross-checked against a timezone database. Private SQLite/files are neither encrypted
nor protected against other local processes. Redistribution and anonymization remain
separate governance decisions. Automated axe and keyboard checks do not substitute
for an actual screen-reader review.
