# AstroTrust 2.0 — pivot audit and preservation record

17 October 2026 · `D:\Projects\AstroTrust` · independent research scope migration

## Starting state and inventory

The audit began with an existing working tree containing substantial uncommitted
consumer-collector work. Those changes were treated as existing user work, not
discarded, reset or claimed as newly built by this pivot. Existing modifications
included README, CLI/server/store/service integration, collector styling, tests
and CI; new consumer modules, UI, schema, docs and browser tools were already present.
No applicable `AGENTS.md` was found in the repository or checked parent paths.

Repository-wide file inventory, keyword searches, route/CLI/schema/test inspection,
documentation review and read-only SQLite/export validation preceded implementation.
Searches included survey/questionnaire/Google Forms/recruitment/consent/participant
terms, historical no-results claims, navigation and paper/planning references.
Ignored environments, caches and build products were identified separately from
research evidence; their installed old README metadata are generated historical
copies, not active research authority. No TeX, PDF, DOCX or other manuscript was found.

| Component | Finding | Decision |
| --- | --- | --- |
| Public questionnaire/Google Forms | No form, URL, public page or connector found | No integration to remove |
| Survey scaffolding | `survey/README.md` proposed a deferred future human study | Preserve exact bytes in deprecated archive; remove active file |
| Recruitment/consent | No recruitment script, consent form, participant dataset or survey schema/workflow found | No evidence or operational code deleted |
| Survey-dependent claims | Root question/title and milestone proposed human trust/reliance experiments; methodology/ethics/data docs carried future-study dependencies | Replace active scope and roadmap; archive prior document bytes |
| Reviewer/annotation tooling | Independent construction review, blank feedback, draft labels, agreement and adjudication | Preserve; distinct from public survey |
| Frontier collector | Operational stdlib loopback server, SQLite snapshots, exact-label coverage, three export formats and single-run reports | Retain protocol and direct `/` route |
| Consumer collector | Existing working consumer-1.1 extension with fixed profile, provenance/hash rules and separate store | Retain protocol, schema, registry and `/consumer` route |
| Stored evidence | 27 frontier runs/27 snapshots; original JSONL has 27 validated records; consumer store empty | Verify read-only; preserve exact bytes |
| Instrument | Eight scenarios, controlled template, language registry, schema and review packets | Preserve identity/hashes and draft/review gates |
| Existing UI | Field-notebook theme, capture form, ledger, dialogs, accessible labels, responsive layouts | Extend existing UI/navigation; no framework rebuild |
| Local baselines/AstroGuard | No local runtime abstraction or trained classifier present | Add inference boundary and split validation; document AstroGuard as proposed |
| Paper | Working-paper direction in README only | Preserve title in archive; add explicitly draft system-evaluation outline |

No survey implementation was imported by application code, packaging, tests or CI.
Consequently there was no survey dead code to delete after dependency analysis.
The only removed active source asset is the archived scope README. Remaining
survey mentions explain discontinuation, historical context or the boundary from
independent reviewer work. Synthetic-profile “NOT PARTICIPANT DATA” labels are
protocol evidence and intentionally remain unchanged.

## Evidence preservation and architectural changes

Before changes to active research documents, originals were copied byte-for-byte
to `docs/archive/pre-2.0/` and indexed in [archive status](archive/README.md). Text
suffixes prevent old relative links and instructions being presented as active
navigation. Dated foundation/instrument/first-snapshot/collector audits remain
historical records. The instrument-version document adds an explicit current-scope
notice without redefining the checkpoint. Annotation label meanings remain draft.

`tools/check_pivot_integrity.py` recorded 57 protected file fingerprints in ignored
`data/pilot/pivot-integrity-before.json`. This includes both SQLite databases,
original exports, every benchmark JSON/schema, reviewer packets/forms, manual record
models, consumer models and fixed profile registry. Final verification confirms
all recorded fingerprints unchanged. A previous consumer-integrity manifest's five
protected hashes were also retained; no raw response was edited, normalized or rescored.
Both SQLite stores pass `PRAGMA quick_check`; record validation checks text/profile/
interaction hashes and revision histories. Original frontier exports validate
under the unchanged manual schema. The pilot remains exploratory, not confirmatory,
training or held-out data. Integrity hashes cannot establish remote origin.

Logical implementation phases:

1. Audit and preservation: inventory, baseline tests, read-only evidence checks,
   protected fingerprint manifest and archive copies.
2. Active scope: new [research plan](ASTROTRUST-2.0-PLAN.md), revised README,
   methodology, benchmark card, data/ethics/analysis/experiments guidance, roadmap
   and [paper outline](research-paper-outline.md). Remove public-survey dependency.
3. Workstation: shared navigation exposes overview, frontier, consumer and local
   workflows while preserving existing collection URLs and functionality.
   `/api/research/status` requires the existing session token and reads databases
   in SQLite read-only mode. It does not open/create the lazy frontier store.
   Missing/error counts are null; local experiment counts are not invented.
4. Evaluation architecture: separate hash-linked capture sidecars with draft
   labels and source-verified excerpts; deterministic per-evaluator category counts;
   human/model origin separation; no fabricated scores or automatic ground truth.
   Existing controlled-run annotation/agreement/adjudication remains unchanged.
5. Baseline architecture: inference-only Python Protocol and explicit stdio adapter,
   versioned requests/attempts, exclusive output files, complete message/settings/
   runtime/environment provenance and retained failures. Split manifests reject
   declared scenario-family/hash leakage across pilot/train/validation/test roles.
6. Verification: backend, schema/packet reproduction, collector browser regressions,
   new workstation responsive/keyboard/axe/error-retry tests and evidence recheck.

Loopback binding, Host/Origin checks, session token, CSP, no-store headers, text-only
response rendering, no payload logging, duplicate rejection, transactional imports,
metadata revision history and cross-store guards remain active. No provider SDK or
project dependency was added; only the project description changed in packaging
metadata. `uv.lock` is unchanged. No real model inference, model download, training,
destructive migration, commit, push or release was performed.

## Verification results

| Check | Result |
| --- | --- |
| Existing baseline tests | 218 passed on Python 3.12.13 |
| Full suite after pivot | 238 passed on Python 3.12.13; synthetic stores only |
| Ruff format/lint | Passed |
| Mypy | Passed across application, tests and tools |
| Scenario/template validation | 8 scenarios, 24 default development prompts; no validity certification |
| All three exported schemas | No drift: controlled records, manual-1.0, consumer-1.1 |
| Review artifacts | Example/templates reproduce; both pending bundles reproduce; no completed reviews |
| Frontier browser regression | Passed: save/reopen, four exports, exact strings/hashes, revisions, duplicate rejection, error preservation, keyboard/axe |
| Consumer browser regression | Passed: fixed profile and interaction hashes, requested/submitted fields, gender gating, not_used, raw line endings, four exports, revisions, separation, navigation guard, keyboard/axe |
| New research/local screens | Passed at 1440×900 and 390×844; actual/missing counts, read-only lazy store, retry/stale state, keyboard and axe |
| Visual inspection | Desktop/mobile captures inspected for frontier, consumer, overview and local screens; no overflow or overlapping controls observed |
| Protected evidence/instrument fingerprints | 57 unchanged; 27 frontier captures and original exports preserved; consumer count remains 0 |
| Real export analysis without sidecars | 27 captures, 0 annotations, no category counts, no generated scores |
| Local wheel/source build | Passed; research modules and new UI assets included, private evidence excluded |
| Active documentation file links | Resolve in all 28 checked documents; historical source copies intentionally remain text |

The initial sandbox test attempts hit restricted default temporary directories and
loopback sockets. Re-running with a workspace-local test directory and approved
loopback access passed; no assertion was skipped or safeguard weakened. One initial
new-screen axe finding identified an unlabeled status area outside a landmark;
adding named status regions resolved it, and the full browser check passed.
An actual screen-reader client was not tested; these checks are not WCAG certification.

The first offline packaging attempt lacked the existing declared `setuptools` build
requirement in cache. Building with that declared build requirement succeeded;
the final build then reproduced offline. Build logs and archives remain under ignored
`data/pilot/pivot-build*`; no distribution was published or project dependency added.

Visual review: the first impression is a local research ledger with navigation to
the three evidence streams. The heading leads into actual status rather than a
performance claim. The field-notebook direction is consistent with the existing
collectors: warm paper, teal rules, Georgia headings, readable body text and mono
provenance. Computed research/local screens use four type sizes (12.8, 16, 20,
31.25 px), square borders and no shadows. New spacing uses the existing token scale.
The ledger stacks on mobile; navigation and controls remain visible. The initial
status-region accessibility defect was fixed. No remaining blocking visual issue
was observed; actual screen-reader verification remains a manual follow-up.

Reproduction commands (after existing dependencies/browser/axe are installed):

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp=data/pilot/pivot-check-tests --tb=short
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m mypy astrotrust tests tools
.venv/Scripts/python.exe tools/check_pivot_integrity.py verify --manifest data/pilot/pivot-integrity-before.json
.venv/Scripts/python.exe tools/check_collector_ui.py --browser-channel msedge --axe-script data/pilot/ui-tools/package/axe.min.js --output data/pilot/pivot-frontier-ui
.venv/Scripts/python.exe tools/check_consumer_ui.py --browser-channel msedge --axe-script data/pilot/ui-tools/package/axe.min.js --output data/pilot/pivot-consumer-ui
.venv/Scripts/python.exe tools/check_research_ui.py --browser-channel msedge --axe-script data/pilot/ui-tools/package/axe.min.js --output data/pilot/pivot-research-ui
```

Screenshot/check reports remain ignored in the three UI output directories. Browser
tests use fresh synthetic databases and remove their runtime data. The actual stores
were inspected only in read-only connections by this pivot's evidence checks.
The fingerprint manifest is intentionally local; create a new manifest before a
later authorized evidence-changing collection session rather than expecting old
database-byte fingerprints to remain equal after new captures.

## Remaining boundaries and next steps

No preservation/destructive-operation blocker required modifying evidence or a
locked protocol. Consumer collection remains pending and fully operational.
Independent construction review, human response annotation, rubric validation,
translations, design freeze and broader sampling remain research work. There is no
validated BCAS/ADRS formula to implement; the safe reproducible output is draft
categorical analysis, not an invented numerical score. Native manual-capture
matched-comparison annotation needs a reviewed extension rather than fabricated
API provenance. No scores or model comparisons were inferred from the real pilot.

Choose and document an installed model/runtime before real local inference. The
command boundary cannot prove an arbitrary supplied program avoids training or
downloads; use an explicitly approved inference-only runtime. Model/tokenizer hashes
are declarations until checked by that runtime. Split validation checks declared
identities/hashes, not undisclosed data, semantic paraphrases or prior exposure.
Optional fine-tuning and held-out AstroGuard results remain proposed.

Restart an already running collector to load the new server routes, then use
Research overview. Existing unrelated/live server processes were not terminated.
No public site deployment, thread messaging or release is part of this migration.
