# Consumer astrology-app collection checklist

Verified 17 October 2026. This is manual exploratory collection under the existing
`consumer-1.1` / `consumer-career-1.0` protocol. No protocol or UI redesign is required.

## Start and select the correct workflow

The collector is already running on port 8766 in this session. Do not start a second
instance on the same port. For a later start, after stopping the previous collector:

```powershell
Set-Location -LiteralPath 'D:\Projects\AstroTrust'
& '.\.venv\Scripts\python.exe' -m astrotrust collect-consumer --root 'D:\Projects\AstroTrust' --database 'data/pilot/consumer-app-runs/collector.sqlite3' --port 8766
```

This uses the installed environment without syncing or downloading dependencies.

- [Research Overview](http://127.0.0.1:8766/research)
- [Consumer Collection](http://127.0.0.1:8766/consumer)
- [Historical frontier collector](http://127.0.0.1:8766/)

The actual consumer database is `data/pilot/consumer-app-runs/collector.sqlite3`;
the historical database stays at `data/pilot/manual-runs/collector.sqlite3`.
Never select or import the isolated dry-run database for real collection.

## For each planned capture

1. **Plan first.** Write down apps, exact prompts, repeat counts, order, fresh-session
   procedure and stopping criteria before assessing responses. Keep partial outputs,
   refusals and failures. Do not select extra runs based on whether you like an answer.
2. **Choose and copy the prompt.** On Consumer Collection select
   `consumer-career-p1` or `consumer-career-p2`, choose the planned run number, and
   click **Copy Prompt**. Paste it into the app yourself. Save the exact submitted
   text; if modified, record a deviation reason. Do not call the frontier workflow.
3. **Identify the app as observed.** Enter its exact name, access method, cost/access,
   response type and visible AI/human claims. Record version, account tier, settings,
   session history/defaults and collection anomalies in the note or protocol record
   where available; these do not all have dedicated fields. Enter an engine/model
   label only if explicitly displayed; otherwise leave it blank. Unknown is valid.
4. **Use only fixed fictional inputs.** Select requested field **names** separately
   from fields actually supplied. Choose `consumer-profile-001` if any fixed profile
   fields were submitted, or `not_used` if none were submitted. Fixed values:
   DOB **1998-02-12**, time **10:30**, birthplace **Guwahati, Assam, India**, birth
   timezone **Asia/Kolkata**. Supply/mark only values actually needed and entered.
   Gender **male** is permitted only when required, with gender/sex recorded as
   requested. Do not invent names, custom birth values or additional profile inputs.
5. **Preserve the interaction.** Use `initial_prompt_only` only for no-profile,
   no-extra-exchange runs; use `prompt_and_fixed_profile_only` for just the prompt
   and supplied fixed fields. For additional exchanges choose `multi_step`; for
   incomplete history choose `unknown`. These require an exact transcript or protocol
   note. Preserve turn order, questions, answers, defaults and omissions. Never
   reconstruct missing wording or claim a partial note is a complete transcript.
6. **Paste the final response verbatim.** Keep uncertainty, caveats, citations as
   copied, refusal and truncation. Check text for private information before saving.
   Confirm the capture timestamp with UTC offset, e.g. `+05:30`, and observed timezone.
   This is the capture time, separate from fictional birth timezone. Record
   completeness, truncation, information requests and avoidance honestly.
7. **Save once and inspect.** Click **Save Consumer Capture**, reopen its ledger
   entry and check prompt, response, interaction, profile, timestamp and provenance.
   Duplicate identity is exact **app name + prompt ID + run number**. Do not change
   spelling or increment a number merely to bypass rejection. Use a new number only
   for a genuinely planned independent repeat. Corrections require a reason and
   preserve history; raw text and profile/interaction evidence cannot be edited.
8. **Export and validate.** Save authoritative JSONL after each session using a new
   filename, retain a private backup and validate it. Browser downloads go to the
   browser's download folder; move them to approved private storage. Example:

```powershell
& '.\.venv\Scripts\python.exe' -m astrotrust collect-consumer export --format jsonl --output 'data/pilot/consumer-exports/consumer-20261017-session001.jsonl'
& '.\.venv\Scripts\python.exe' -m astrotrust collect-consumer validate 'data/pilot/consumer-exports/consumer-20261017-session001.jsonl'
```

## Limits and stop conditions

- No real birth details, account identifiers, credentials, emails, phone numbers,
  cookies or keys in any free-text field or export. If an app requires unsupported
  personal inputs or an unlisted requested-field name, pause that capture and record
  the limitation; do not improvise a profile or change the locked vocabulary.
- Windows/Edge clipboard testing changed lone CR to CRLF **before paste**. The
  collector preserved delivered text exactly, but cannot prove original app-byte
  identity or retain all visual/report content. Note transformations/omissions and
  retain an original private report/screenshot when permitted; never fabricate gaps.
- Timezone labels are descriptive, not cross-checked against their UTC offsets.
  Manually verify them. Git ignores do not encrypt SQLite or restrict local access;
  review privacy and service redistribution terms before sharing any output.
- App identities/model claims and hashes do not authenticate a backend, human
  involvement or independence. These two career prompts are exploratory; app outputs
  are not automatically controlled comparisons with the historical frontier data.

See [verification and limitations](CONSUMER-COLLECTION-READINESS.md) and the full
[consumer protocol](consumer-collector.md).
