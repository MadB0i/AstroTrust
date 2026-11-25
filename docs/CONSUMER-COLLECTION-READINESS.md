# Consumer collection readiness verification

17 October 2026 · actual local application, existing code and protocols

No application/source/schema changes were made in this preparation session. New
files are collection instructions, this report, and ignored verification artifacts.

## Live application

The previous saved PID/log was stale: no Python collector was listening on 8766.
The installed project interpreter started the existing `collect-consumer` command
on `127.0.0.1:8766`, using the original consumer and frontier stores. Current launched
PID: **4780**, recorded in `data/pilot/collection-readiness/server.pid`. It remains
running; no unrelated process was stopped. PID values are session-specific.

Headless Edge exercised the real running server, with saved writes blocked on the
live browser context. Research Overview displayed **27 frontier / 0 consumer**.
All four workflow links worked. The frontier collector loaded its prompt, 27-record
ledger and coverage; its live JSONL export matched the historical store and a
retrieved record matched its complete source snapshot. Consumer Collection loaded
`consumer-1.1`, both fixed prompts and the correct profile hash; Copy Prompt returned
the exact registry text. Desktop/mobile screenshots were inspected, with no page
overflow or uncaught page errors observed. No actual app was contacted or evaluated.

## Historical evidence and classification

All **57 protected fingerprints** matched the pivot manifest before and after live
verification and dry-run testing, including original SQLite and exports. The
27-record original JSONL matches the latest historical store records. No metadata,
raw text, collection history, schema or profile registry was relabeled or rewritten.

All 27 records explicitly declare `schema_version=manual-1.0`,
`source_category=general_purpose_llm` and `study_phase=exploratory_pilot`. They belong
in the Frontier workflow as general-purpose frontend captures, separate from
consumer astrology services, local-model baselines and held-out data. “Frontier” is
an application section name, not an authenticated flagship-model/capability claim.

| Observed product | Exact recorded UI label | Captures |
| --- | --- | --- |
| ChatGPT | `GPT5.5` | 9 |
| Claude | `Haiku-4.5` | 3 |
| Claude | `Sonnet-5.5` | 6 |
| Gemini | `3.5 Flash-Lite` | 3 |
| Gemini | `3.8 Flash` | 6 |

These labels are preserved observations, not independently verified model versions.
The corpus spans five labels; 27 total captures does not mean a uniform completed
three-model experiment. The existing ledger correctly keeps exact labels separate.
For all 27, account tier is null and special mode, browsing, memory, completeness
and truncation observations are unknown. All recorded capture timestamps include
offsets. Missing observations were not backfilled from guesses or current app state.

## Exactly one isolated synthetic-profile dry run

The same application/server and Consumer UI saved **one** synthetic test record
in `data/pilot/collection-readiness/isolated-synthetic-dry-run/consumer.sqlite3`.
Its app label is **SYNTHETIC DRY RUN — NO APP CONTACTED**, and its note and response
explicitly identify testing. Run ID: `consumer-7c03981edceb45d187d54958244017af`.
Capture timestamp: `2026-10-17T08:20:02+05:30`. No real service output or model result
was manufactured. The isolated frontier store is empty; the actual consumer store
remains empty. Do not import this test store/export into research datasets.

Verified against stored/reopened/exported JSON:

- Fixed `consumer-profile-001`, version/snapshot/hash and requested-versus-supplied
  date of birth, birth time and birthplace. Gender was not submitted.
- Exact registry prompt, multi-step transcript and final synthetic response,
  including Unicode, whitespace, response hash and interaction hash.
- Capture offset `+05:30`, observed timezone, timezone-aware metadata-history time,
  collector/software version, source revision and dirty-worktree provenance.
- Undisclosed model stays null; AI/human claims and cost stay unknown.
- Missing app name was blocked in the UI before submission. Server requests missing
  profile ID, interaction mode, service name or timestamp returned **400**. A timestamp
  without offset and a multi-step capture without transcript also returned **400**.
- Repeating the same app/prompt/run identity returned **409**; count remained one.
  Follow-up verification left the saved dry-run database unchanged.

The initial test assertion comparing the intended string with saved text failed.
Investigation using **actual Windows/Edge paste events** showed that lone carriage
returns became CRLF before the collector received them. Saved raw response and
transcript exactly matched delivered clipboard data and their hashes. The initial
record was retained unchanged, not repaired or replaced. Intended and delivered
strings are preserved separately in the ignored dry-run folder. Source-byte identity
is therefore **not** established; this is a concrete clipboard limitation.

## Boundaries before actual app collection

The collector workflow is operational; no preservation or software blocker was found
for supported captures. App-specific access, settings and synthetic-input acceptance
are not verified because no consumer app was selected or contacted. Prespecify
service selection, repeats, ordering and stopping criteria before judging responses.
Pause if an app requires real identity or unsupported inputs. The closed requested
field vocabulary does not include every possible app field (for example timezone);
do not silently extend it or hide values under a different field name.

Clipboard/report omissions and historical unknown settings limit reproducibility.
Independent review, rubric validation and any scientific comparisons remain pending.
No full regression-suite rerun is claimed in this session: application code was
unchanged and verification targeted the actual running workflows and isolated dry run.
No training, downloads, new features, commit, push or release occurred.

[Concise manual checklist and exact startup command](CONSUMER-COLLECTION-CHECKLIST.md).
Detailed checks: `data/pilot/collection-readiness/verification.json`; live screenshots
and the labelled `SYNTHETIC-ONLY.jsonl` are alongside it. Those local artifacts are
Git ignored and contain no newly collected real app response.
