# AstroTrustBench early benchmark card

**Status:** instrument-v0.1; software 0.1.0.dev0; controlled record schemas `manual-1.0`, `consumer-1.1`, and `local-attempt-1.0`. The verified workspace corpus contains **93** exploratory captures across three cohorts: 27 frontier web captures (`atb-career-001`), 6 live consumer sessions across 5 Indian Android apps (`Astrotalk`, `Pandit Ji`, `Reva`, `AstroSage`, `AstroTime`) paired with static binary forensics across all 5 non-empty APKs (`data/results/apk_forensic_summary.json`) and a live `mitmproxy` emulator protocol (`CAPTURE_PROTOCOL.md`), plus 60 local open-weight runs (`30` `Qwen2.5-0.5B-Instruct` and `30` `Qwen2.5-1.5B-Instruct`) spanning all 8 India scenarios × 3 belief frames. AstroTrust 2.0 expands empirical evaluation without changing `instrument-v0.1` scenario IDs; non-circular `AstroGuard` evaluation uses 44 manually audited unseen cross-domain and `1.5B` runs (`data/astroguard/heldout_unseen_labeled.jsonl`).
The previous card is [archived](archive/README.md).

**Purpose and intended use:** develop a controlled instrument to examine differences
in LLM responses to expressed astrological beliefs. Suitable now for testing record
validation and prompt isolation. A reviewed, frozen release could support research
comparisons within a documented model-run protocol.

**Out of scope:** astrology prediction accuracy, horoscopes, advice services,
diagnosis, believer intelligence/rationality, model danger rankings, population-level
trust estimates, automated decisions about people and human-study deployment.

**Composition:** eight invented adult situations in India, one per domain: career,
education, relationships, finance, health, relocation, family and everyday decisions.
Two low, four medium and two high stakes, with per-scenario rationales. No names,
exact birth details, participant records or correct astrological outcomes. They were
authored with AI assistance against the stated taxonomy before any model evaluation;
development review is not independent human validation.

**Conditions:** three belief frames, two emotional frames and two personalization
frames. The default preview is 24 English prompts in eight matched belief trios.
No full-factorial study, sample-size adequacy or respondent corpus is implied.

**Languages:** English drafts available; Hindi and Assamese pending. Human review
metadata are required for research-use rendering. Translation review must address
meaning and pragmatic force; successful parsing is not an equivalence test.

**Risks:** prompts may elicit discouraging or overconfident advice, including high-stakes
advice. Cultural stereotypes or linguistic confounds can enter fixture wording and
annotations. A small synthetic set can support overstated generalizations. Regex
privacy screening is incomplete. Reviewers may find some advice distressing.

**Known limitations:** coarse adult profiles; no tradition-specific or birth-chart
context; eight fictional English scenarios with Hindi/Assamese translations pending;
unknown multi-rater reliability (blind 40-unit coder packet exportable via
`tools/export_blind_coding_batch.py`, independent second-coder Cohen's kappa still
pending human annotation); unvalidated stakes taxonomy; no human trust measurements.
Frontier and consumer sessions center on `atb-career-001`, whereas local `0.5B` and
`1.5B` baselines cover all 8 domains × 3 belief contrasts. Consumer packet capture on an
isolated Android 14 emulator verified `POST /AstrotalkPayments/user/save/user-upi-apps`
in unauthenticated guest mode; authenticated `user/apps/installed` transmission awaits
a test login session.
See the [instrument audit](instrument-audit.md), [capture protocol](CAPTURE_PROTOCOL.md),
and [expansion gate](scale-up-gate.md).

**Future validation:** independent cultural and subject-context review, translation
adjudication, confound checks, balanced sampling, preregistration, replicated runs,
human rubric pilots and reliability/validity studies. Publish limitations and all
selection/exclusion rules before interpreting results.

**Distribution:** current synthetic fixtures, code and documentation are MIT. Future
annotation metadata and model-response corpora need their own access/contract/privacy
and licensing review. Public survey data are outside scope. Versions, hashes and
provenance must accompany any separately authorized releases.
