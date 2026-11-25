# Consumer collector implementation and verification

This is the historical `consumer-1.0` implementation report. The subsequent required
synthetic-profile and interaction provenance update is verified in
[synthetic-profile-verification.md](synthetic-profile-verification.md). Use that report
and the current [collector guide](consumer-collector.md) for schema `consumer-1.1`.

Verified locally on 2026-10-05, Asia/Calcutta. Changes remain uncommitted; no push
was performed. Usage and export instructions are in [consumer-collector.md](consumer-collector.md).

## Audit and architecture decision

The original collector uses frozen Pydantic `Record` types, a stdlib loopback HTTP
server, bundled HTML/CSS/JavaScript, SQLite `runs`/`snapshots`, contiguous metadata
histories, canonical prompt snapshots and UTF-8 SHA-256. Existing imports are atomic,
exports are lossless and output paths reject overwrite. Its `ManualRun` requires a
controlled `Prompt`/condition and run numbers 1–3; reserved service metadata lacks
the consumer access/cost/type choices and permits arbitrary field-name text.

A separate consumer schema, fixed prompt registry, route/API and default SQLite
database therefore provide the safest separation. Transaction connections, Git
provenance, digest, JSON parsing, Markdown fences and CSV escaping are reused.
The original model/schema and exporter functions remain unchanged. General coverage
now explicitly filters source category, and general saves reject consumer categories.
There is no migration, recapture, re-export or scientific reinterpretation of the
existing pilot. New consumer records do not use the controlled condition matrix.

Before editing, five existing files were fingerprinted: the 27-run SQLite database,
both existing exported pilot files, the original manual schema and controlled prompt
template. The final SHA-256 comparison passed for all five. Read-only SQL confirmed
27 original runs before and after; captured content was not scored or interpreted.
Fingerprints and confirmation are local ignored artifacts:
`data/pilot/consumer-integrity-before.json` and `consumer-integrity-after.json`.

Consumer records use `consumer-1.0`, a separate `consumer-` UUID namespace and
`source_category=consumer_astrology_service` at record and metadata levels.
New tables are `consumer_runs` and `consumer_snapshots`. Datastore family checks
refuse the opposite workflow before writable access. Consumer startup lazily leaves
the general datastore unopened until a general API operation is explicitly requested.

## Files changed

| Files | Purpose |
| --- | --- |
| `astrotrust/collector/consumer_models.py` | Consumer schema, fixed prompt registry, closed personal-field-name vocabulary and integrity validators |
| `astrotrust/collector/consumer_store.py` | Separate SQLite tables, duplicate identity, atomic import and revision snapshots |
| `astrotrust/collector/consumer_service.py` | Consumer capture assembly, hashes and ledger summaries |
| `astrotrust/collector/consumer_exports.py` | Consumer JSONL, CSV, Markdown and portable validation |
| `astrotrust/collector/static/consumer.html`, `consumer.js` | Form, privacy notice, ledger, raw evidence display, revisions, draft guards and exact clipboard preservation |
| `astrotrust/collector/static/index.html`, `collector.css` | Workflow navigation and its active indication, preserving existing design tokens |
| `astrotrust/collector/server.py` | Consumer routes/API, lazy general initialization and separate database selection |
| `astrotrust/collector/store.py` | Shared SQLite connection handling and read-only datastore-family guard; original tables unchanged |
| `astrotrust/collector/service.py` | Shared code-provenance helper, category-specific coverage and general save guard |
| `astrotrust/collector/cli.py`, `astrotrust/__main__.py` | `collect-consumer` launcher and separate export/validate/import commands |
| `benchmark/schema/consumer-run.schema.json`, `tools/export_consumer_schema.py` | New generated consumer schema and drift check |
| `tests/test_consumer_collector.py`, `tests/test_collector.py` | Consumer validation/integrity and full synthetic 27-run separation regressions |
| `tools/check_consumer_ui.py` | Offline browser, export, accessibility, privacy and exact clipboard regression |
| `.github/workflows/checks.yml` | Consumer schema drift check added to existing CI |
| `README.md`, `docs/manual-collector.md`, `docs/consumer-collector.md`, this report | Startup, separation, architecture, exports, audit and verification documentation |

No dependency specification or lockfile changes were needed. All pilot data,
screenshots, synthetic runtime artifacts, builds and logs stay under Git-ignored
`data/pilot/`. Browser-test databases and downloads were temporary and removed by
their test harnesses; the real consumer store was started empty, with zero captures.

## Final results

| Verification | Result |
| --- | --- |
| Original pre-change suite, Python 3.12.13 | 110 passed |
| Final suite, Python 3.12.13 | 177 passed in 10.28 seconds |
| Final suite, Python 3.14.5 | 177 passed in 10.02 seconds |
| Added regressions | 67: 65 consumer tests plus 2 general/separation tests |
| Ruff format and lint | Passed; 77 Python files formatted |
| Strict mypy | Passed; 47 source files |
| Scenario validation | 8 scenarios, 24 development prompts |
| Existing instrument and manual schema checks | Passed; original schemas unchanged |
| New consumer schema check | Passed |
| Review example and both pending bundle checks | Passed |
| Existing browser workflow | Passed; four exports, hashes, revisions, failures, duplicates, keyboard and axe |
| Consumer browser workflow | Passed; four exports, hashes, names-only validation, revisions, duplicates, draft guards and separation |
| Consumer exact clipboard regression | CRLF and lone CR retained in both prompt/response; unrelated edits preserve earlier line endings |
| Consumer accessibility/responsive checks | Zero axe violations at 1440, 768 and 390 pixels; 50 keyboard traversal steps; no page overflow |
| Browser external requests / unexpected errors | Zero; expected simulated save errors were accounted for |
| Package build | Source distribution and wheel built; wheel includes all new consumer modules and assets, no pilot data |
| Original pilot protection | All five fingerprints unchanged; original count still 27 |
| Live consumer page | HTTP 200 at `http://127.0.0.1:8766/consumer`; real consumer count 0 |

During development, initial failures were fixed: an expected exception assertion
needed to account for the existing importer's `ValueError` wrapper; select labels
needed stable accessible names; the mobile ledger needed a focusable scroll region;
and a browser assertion needed to wait for the asynchronously loaded matrix cells.
The final checks above passed after those repairs.

Desktop/mobile screenshots were actually inspected using the interface-review skill.
The page reads as a consumer research form, leads to prompt selection/copying, retains
the existing notebook palette/type/spacing, shows the privacy notice prominently and
reflows into one column on mobile. The ledger scrolls within its own region. Raw HTML
sentinels display as literal text. The fixed field vocabulary is intentionally long;
it prevents field values from being smuggled into free-text labels. Actual screen-reader
testing was unavailable and is not claimed.

## Exact verification commands run

Commands below were run from `D:\Projects\AstroTrust`. The 3.14 command uses the
already available local 3.14 verification environment. Browser tests use the installed
Edge engine and local axe script, with no remote test requests.

```powershell
# Original baseline before implementation
uv run --locked --extra dev python -m pytest -q

# Development formatting and schema generation
uv run --locked --extra dev ruff check . --fix
uv run --locked --extra dev ruff format .
uv run --locked --extra dev python tools/export_consumer_schema.py

# Final automated suite (also rerun after the last connection-resource correction)
uv run --locked --extra dev python -m pytest -q --tb=short
data/pilot/python314-env/Scripts/python.exe -m pytest -q --tb=short
uv run --locked --extra dev ruff format --check .
uv run --locked --extra dev ruff check .
uv run --locked --extra dev mypy astrotrust tests tools
uv run --locked --extra dev python -m astrotrust validate benchmark/scenarios
uv run --locked --extra dev python tools/export_schema.py --check
uv run --locked --extra dev python tools/export_collector_schema.py --check
uv run --locked --extra dev python tools/export_consumer_schema.py --check
uv run --locked --extra dev python tools/check_review_example.py
uv run --locked --extra dev python tools/check_review_bundles.py

# Browser helpers inspected through --help before execution
uv run --locked --extra dev --extra ui python tools/check_collector_ui.py --help
uv run --locked --extra dev --extra ui python tools/check_consumer_ui.py --help
.venv/Scripts/python.exe C:/Users/rupjy/.agents/skills/testing-webapps/scripts/with_server.py --help
uv run --locked --extra dev --extra ui python tools/check_collector_ui.py --browser-channel msedge --axe-script data/pilot/ui-tools/package/axe.min.js --output data/pilot/general-regression-ui-check
uv run --locked --extra dev --extra ui python tools/check_consumer_ui.py --browser-channel msedge --axe-script data/pilot/ui-tools/package/axe.min.js

# Packaging and preservation
uv build --out-dir data/pilot/consumer-build-check
.venv/Scripts/python.exe data/pilot/verify-consumer-integrity.py
git diff --check
git status --short
git ls-files --modified --others --exclude-standard
```

The local preservation helper compares every initial file hash, checks the original
run count through read-only SQLite, verifies bundled consumer assets in the wheel,
and writes the final result. Source inspection used `rg`, `Get-Content` and
`Get-ChildItem`; no provider/service content was fetched. Tests exercise CLI export,
validate and import against temporary synthetic stores rather than producing an
empty or invented research export in the real consumer store.

## Live startup and export commands

The consumer server was started as a hidden local process (PID 20536):

```powershell
$consumerProcess = Start-Process -FilePath 'D:\Projects\AstroTrust\.venv\Scripts\python.exe' -ArgumentList '-m','astrotrust','collect-consumer' -WorkingDirectory 'D:\Projects\AstroTrust' -WindowStyle Hidden -RedirectStandardOutput 'D:\Projects\AstroTrust\data\pilot\consumer-server.log' -RedirectStandardError 'D:\Projects\AstroTrust\data\pilot\consumer-server.err.log' -PassThru
$consumerProcess.Id | Set-Content -LiteralPath 'D:\Projects\AstroTrust\data\pilot\consumer-server.pid'
```

To stop this process: `Stop-Process -Id 20536`. To start later in your own terminal:

```powershell
uv run --locked python -m astrotrust collect-consumer
```

Exact URL: **http://127.0.0.1:8766/consumer**.
Default database: **D:\Projects\AstroTrust\data\pilot\consumer-app-runs\collector.sqlite3**.

After saving real consumer captures, export to new filenames:

```powershell
uv run --locked python -m astrotrust collect-consumer export --format jsonl --output data/pilot/consumer-exports/pilot.jsonl
uv run --locked python -m astrotrust collect-consumer export --format markdown --output data/pilot/consumer-exports/pilot.md
uv run --locked python -m astrotrust collect-consumer export --format csv --output data/pilot/consumer-exports/pilot.csv
uv run --locked python -m astrotrust collect-consumer validate data/pilot/consumer-exports/pilot.jsonl
```

Opening the localhost page was requested through the app's browser-panel tool; the
app returned `queued`. Direct HTTP verification and read-only count verification
succeeded. Server logs contain startup paths, never request bodies or response content.

## Remaining research limitations

The pilot is exploratory; the consumer prompt pair is not part of the 27-run design
and is not a validated instrument. Service claims do not verify hidden models, human
involvement or independent generation. Prespecification of sampling, fictional-profile
procedure, repeat identity and stopping rules remains a researcher responsibility.
Hash integrity does not authenticate frontend origin or restore information lost
before the clipboard paste. The field vocabulary may need reviewed expansion; other
free-text fields cannot guarantee absence of personal data. Exact service spellings
define duplicate identity and are not automatically merged. Timezone labels are
descriptive, without timezone-database cross-validation. Files are not encrypted.
Anonymization, redistribution and actual screen-reader review remain separate steps.
