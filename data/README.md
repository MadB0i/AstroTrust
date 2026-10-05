# Data governance and licensing

The current public data are fictional benchmark JSON in `benchmark/scenarios/`.
Those fixtures, code and documentation use MIT. That choice permits reuse of the
development instrument; it does **not** license future participant data automatically.

Never casually commit raw human survey responses. `data/raw/`, `data/private/` and
`data/runs/` are ignored as convenience safeguards, not access controls. Do not store
names, exact birth details, health records, contact information, linkage keys or
private conversations in public fixtures. Use approved storage/access/retention
processes for any human data, rather than relying on Git ignores.

Future public human-study releases require appropriate consent, minimization,
anonymization/disclosure-risk review and separately documented terms. Pseudonymization
alone may not prevent reidentification. Restrict or aggregate data when appropriate;
document withdrawals and sharing limits. Synthetic fixtures, generated responses,
annotator metadata and participant responses have different governance requirements.

Generated response redistribution also needs provider-terms review. Human annotation
records should use pseudonymous IDs and store identifying reviewer/annotator linkage
outside this public repository. Record evidence/review metadata without publishing
unnecessary personal information. No human or generated response data are included now.

## Manual frontend pilot captures

The [manual collector](../docs/manual-collector.md) stores raw exploratory responses
locally in `data/pilot/manual-runs/collector.sqlite3`. Use `data/pilot/exports/` for
JSONL/CSV/Markdown research backups; the entire `data/pilot/` tree is Git ignored.
Browser downloads use the browser's configured directory, so move them to an
appropriate private location before working with them inside the checkout.

No real pilot outputs are supplied or automatically committed. Store only synthetic
user-context prompts and copied response text with observed frontend settings; never
store login credentials, account identities, cookies, keys or browser sessions.
Review accidental sensitive text before any sharing. Captures remain exploratory,
without validated BCAS/ADRS or scientific conclusions. Local export does not authorize
redistribution of provider or proprietary astrology-service outputs, and MIT licensing
of the code/fixtures does not automatically license those outputs or participant data.
SQLite is plaintext: Git ignores are neither privacy guarantees nor access controls.
