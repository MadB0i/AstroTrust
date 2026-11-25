# Synthetic profile provenance verification

Verified locally on 2026-10-05, Asia/Calcutta. This updates the consumer collector to
`consumer-1.1` / `consumer-collector-0.2` before real consumer collection. Changes
remain uncommitted; no push was performed. The current procedure is in
[consumer-collector.md](consumer-collector.md).

## Result

The fixed registry contains `consumer-profile-001`, version `consumer-profile-1.0`:
1998-02-12, 10:30, Guwahati, Assam, India, Asia/Kolkata, with male supplied only when
the service requires gender. The registry, UI and exports label it **FICTIONAL /
SYNTHETIC RESEARCH INPUT — NOT PARTICIPANT DATA**.

Every consumer capture requires an explicit profile selection, the exact submitted
field keys, the frozen snapshot/version/hash, and an explicit interaction scope.
Requested personal-field names remain separate metadata. `not_used` requires empty
submitted keys and null snapshot/version/hash. Custom profile IDs, birth values,
snapshot overrides, missing provenance and stale hashes are rejected. Gender supply
requires the service-required attestation and an original requested gender/sex label.

Multi-step or unknown histories require an exact protocol note or transcript and its
UTF-8 SHA-256. Clipboard CRLF, lone CR and Unicode are retained. Additional history
cannot be hidden under a single-step scope; supplied profile fields cannot be
attributed to the initial prompt alone. Raw input and interaction evidence remain
immutable through metadata revisions. JSONL, CSV, single-record JSON and Markdown
preserve the evidence; Markdown states the scope and limitations of attribution.

The fixed snapshot hash is
`b2ddf58dbcd59a43a3b111efe242b0067c04d4bac3096b26d7e91fc6032a31ef`.
It is explicitly regression-tested. Hash serialization is documented in the guide.
No SQLite table migration is needed; the real consumer store was empty. Imports of
`consumer-1.0` or records missing the new evidence are rejected without inventing
provenance. The existing `manual-1.0` schema and captures are unchanged.

## Implementation

| Files | Change |
| --- | --- |
| `astrotrust/collector/consumer_profiles.py` | Frozen typed registry, read-only mapping and canonical digest |
| `consumer_models.py`, `consumer_service.py`, `server.py` in the collector package | Required provenance, integrity validation, server-resolved snapshots and bootstrap registry |
| `astrotrust/collector/consumer_exports.py` | Lossless profile/interaction evidence and accurate attribution |
| `astrotrust/collector/static/consumer.html`, `consumer.js` | Fixed-value copy controls, submitted-field choices, conditional gender and exact interaction capture |
| `benchmark/schema/consumer-run.schema.json`, `tools/export_consumer_schema.py` | Regenerated schema `consumer-1.1` |
| `tests/test_consumer_collector.py`, `tests/test_collector.py`, `tools/check_consumer_ui.py` | Validation, corruption, import, API, revision, export and browser regressions |
| `README.md`, collector guides and this report | Procedure, registry, schema compatibility and research limits |

## Full verification

All repository checks passed, plus both browser checks and packaging:

| Check | Result |
| --- | --- |
| Python 3.12 full pytest suite | 218 passed in 14.32 s |
| Python 3.14 full pytest suite | 218 passed in 14.32 s |
| Ruff formatting | 79 files already formatted |
| Ruff lint | All checks passed |
| mypy | No issues in 48 source files |
| Benchmark scenario validation | 8 scenarios / 24 prompts valid |
| Instrument, manual and consumer schema drift checks | Passed |
| Review example and pending review bundles | Passed |
| General collector browser regression | Passed |
| Consumer collector browser regression | Passed |
| Source distribution and wheel build | Passed; registry module and consumer UI included, no pilot data packaged |
| Original pilot integrity | All five protected file fingerprints unchanged; 27 general-purpose runs |

There are 41 additional Python cases beyond the previous 177-test implementation.
The browser tests use native Python Playwright and installed Edge, with the local
axe script. At 1440, 768 and 390 px, neither workflow had horizontal overflow, axe
violations, unexpected console errors or external requests. Keyboard checks cover
90 consumer controls and 35 general controls. Synthetic saves, reopening, duplicate
rejection, retained failed drafts, revisions and four exports passed. The consumer
check additionally verifies conditional gender, requested/supplied separation,
fixed snapshot/hash, explicit unused profile and exact multi-step transcript hash.
Desktop/mobile screenshots were visually inspected. Test runtime stores were removed.
An actual screen-reader client was not tested.

The local consumer collector was restarted after verification at
`http://127.0.0.1:8766/consumer` (PID 2520, recorded in the ignored
`data/pilot/consumer-server.pid`). Live HTTP and authenticated bootstrap checks
confirmed `consumer-1.1`, the fixed profile version/hash and zero consumer captures.
Refresh an already-open page to receive the new form and session token. The original
pilot fingerprint check was repeated after restart.

Reproduce from the repository root:

```powershell
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
uv run --locked --extra dev --extra ui python tools/check_collector_ui.py --browser-channel msedge --axe-script data/pilot/ui-tools/package/axe.min.js --output data/pilot/profile-general-ui-check
uv run --locked --extra dev --extra ui python tools/check_consumer_ui.py --browser-channel msedge --axe-script data/pilot/ui-tools/package/axe.min.js --output data/pilot/profile-ui-check
uv build --out-dir data/pilot/consumer-build-check
.venv/Scripts/python.exe data/pilot/verify-consumer-integrity.py
git diff --check
```

The Python 3.14 environment, local axe script, integrity helper and private baseline
fingerprints already exist under ignored `data/pilot/`; they are local verification
artifacts, not packaged prerequisites. CI installs locked development dependencies
separately on Python 3.12 and 3.14. Browser reports/screenshots are in
`data/pilot/profile-ui-check/` and `data/pilot/profile-general-ui-check/`.

## Research limits

The fixed profile records intended synthetic inputs. It does not authenticate what
a researcher actually entered into an external service or control service geocoding,
calendar interpretation, hidden defaults, backend versions or generation settings.
Exact interaction records document available exchanges and declared omissions; they
cannot recover missing source content. Free-text evidence still requires privacy
review: never paste real personal birth details, credentials or account identifiers.
This remains an exploratory manual collector, without automated service interaction,
response scoring or scientific conclusions.
