# AstroTrustBench early benchmark card

**Status:** instrument-v0.1; software 0.1.0.dev0; schema 1.0; development fixtures only. No model runs,
performance results or independent linguistic/construct validation.

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
context; only one fixture per domain; English-only text; unknown annotation reliability;
unvalidated stakes taxonomy and constructs; no human trust/reliance measurements.
The tool cannot verify that reviewer declarations correspond to an adequate process.
There is no evidence of model behaviour until actual responses are collected.
The draft annotation handbook and two pending construction-review bundles are available,
but no independent reviews or agreement estimates have been collected. The health
fixture's revision 2 clarifies its opposing expectations; eight base scenarios remain.
See the [instrument audit](instrument-audit.md) and [expansion gate](scale-up-gate.md).

**Future validation:** independent cultural and subject-context review, translation
adjudication, confound checks, balanced sampling, preregistration, replicated runs,
human rubric pilots and reliability/validity studies. Publish limitations and all
selection/exclusion rules before interpreting results.

**Distribution:** current synthetic fixtures, code and documentation are MIT. Future
human data and model-response corpora need their own consent/contract/privacy and
licensing review. Versions, hashes and provenance must accompany releases.
