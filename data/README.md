# Data governance and licensing

The current public data are fictional benchmark JSON in `benchmark/scenarios/`.
Those fixtures, code and documentation use MIT. That choice permits reuse of the
development instrument; it does not automatically license generated service outputs.

The public survey is discontinued. `data/raw/`, `data/private/` and
`data/runs/` are ignored as convenience safeguards, not access controls. Do not store
names, exact birth details, health records, contact information, linkage keys or
private conversations in public fixtures. Use approved storage/access/retention
processes for any human data, rather than relying on Git ignores.

Synthetic fixtures, generated responses and private annotator metadata have different
governance requirements. Preserve pseudonymous judgments and store identity linkage
privately. Pseudonymization alone may not prevent reidentification; document access,
retention and sharing limits. Survey-era governance wording is [archived](../docs/archive/README.md).

Generated response redistribution also needs provider-terms review. Human annotation
records should use pseudonymous IDs and store identifying reviewer/annotator linkage
outside this public repository. Record evidence/review metadata without publishing
unnecessary personal information. The public source tree contains no real response
corpus. The local ignored store contains 27 frontier captures and original exports;
the consumer store is empty at the 17 October 2026 audit.

## Manual frontend pilot captures

The [manual collector](../docs/manual-collector.md) stores raw exploratory responses
locally in `data/pilot/manual-runs/collector.sqlite3`. Use `data/pilot/exports/` for
JSONL/CSV/Markdown research backups; the entire `data/pilot/` tree is Git ignored.
Browser downloads use the browser's configured directory, so move them to an
appropriate private location before working with them inside the checkout.

Real local pilot outputs are preserved, never automatically committed. Store only synthetic
user-context prompts and copied response text with observed frontend settings; never
store login credentials, account identities, cookies, keys or browser sessions.
Review accidental sensitive text before any sharing. Captures remain exploratory,
without validated BCAS/ADRS or scientific conclusions. Local export does not authorize
redistribution of provider or proprietary astrology-service outputs, and MIT licensing
of the code/fixtures does not automatically license those outputs.
SQLite is plaintext: Git ignores are neither privacy guarantees nor access controls.

## Derived artifacts and split roles

Keep capture annotation sidecars under `data/private/annotations/`, local inference
attempts under `data/runs/local/`, and derived reports under `analysis/outputs/`.
Do not overwrite SQLite, exported raw captures or old sidecars to update analysis.
Hash input snapshots and record code/rubric/algorithm versions. Human reference
judgments and model-generated judgments remain distinct and are never silently merged.

Separate pilot, training, validation and held-out test roles by scenario family,
including revisions, translations, conditions, replicates and consumer variants.
The 27 exploratory captures remain pilot evidence. Split manifests must record
provenance/hashes and undergo semantic review; see [local-model guidance](../docs/local-models.md).
