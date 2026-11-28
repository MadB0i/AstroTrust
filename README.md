# AstroTrust 2.0: Calibration Without Safety

*Auditing Epistemic Reliance, Dark Patterns, and App Harvesting in Indian AI Astrology Apps*

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24623712.svg)](https://doi.org/10.5281/zenodo.24623712)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0003--4755--2531-A6CE39?logo=orcid&logoColor=white)](https://orcid.org/0009-0003-4755-2531)
[![Release v2.0.0](https://img.shields.io/badge/Release-v2.0.0-2EA44F?logo=github&logoColor=white)](https://github.com/MadB0i/AstroTrust/releases/tag/v2.0.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Read the Full Paper on Zenodo (PDF, 11 pages):** [**`https://doi.org/10.5281/zenodo.24623712`**](https://doi.org/10.5281/zenodo.24623712)
>
> **GitHub Release:** [**`v2.0.0` (Preprint PDF + Audit Suite)**](https://github.com/MadB0i/AstroTrust/releases/tag/v2.0.0) · **LaTeX Sources:** [`paper/`](paper/README.md) · **Author:** [Rupjyoti Talukdar](https://orcid.org/0009-0003-4755-2531)

## Why This Audit Matters

Text-only AI safety benchmarks evaluate chat bubbles in isolation and miss product-level risks such as checkout traps and background telemetry. In Indian consumer AI astrology apps, an interface can emit cautious, calibrated guidance inside the chat window while billing flows and Android binaries introduce undisclosed financial and privacy hazards. AstroTrust 2.0 pairs conversational evaluation with mobile static forensics and live network inspection in one reproducible suite.

## Key Findings at a Glance

- **Multi-cohort empirical audit (93 sessions):** Evaluated frontier web LLMs (`ChatGPT`, `Claude`, `Gemini`), local open-weight models (`Qwen2.5`), and live sessions across five Indian consumer AI astrology apps (`Astrotalk`, `Pandit Ji`, `Reva`, `AstroSage`, `AstroTime`).
- **Calibrated text vs. commercial dark patterns:** Half of audited consumer app sessions issued calibrated, non-directive disclaimers in chat, yet every consumer session displayed billing or UX pressure patterns under India's CCPA 2023 framework—including INR 1 trials binding five-year INR 699 UPI Autopay mandates, post-session INR 5 to 19/min rate surges stranding small wallet balances, and countdown timers with synthetic engagement counters.
- **Five-APK static forensics and sister-clone contrast:** Without declaring `QUERY_ALL_PACKAGES`, `Astrotalk` mirrors a bundled 787-package target list (`assets/apppackges.json`) into manifest `<queries>` to check installed banking, loan, gambling, and health apps, whereas a shared-codebase sister clone (`Pandit Ji`, 86.99% file overlap) declares 26 `<queries>` and omits the tracker; Android 14 proxy inspection verified pre-login telemetry to payments/UPI endpoints.
- **Dual-layer defense framework (`AstroGuard` + `AstroAudit`):** Pairs text-level guardrails (`AstroGuard`) with APK manifest, asset, and billing inspection (`AstroAudit`), alongside reproducible offline scripts examining out-of-domain generalization and compact classifier failure modes.

*Full methodology, statistical analysis, figures, and SHA-256 verification digests are in the [published preprint on Zenodo](https://doi.org/10.5281/zenodo.24623712).*

## What's Inside This Repo

| Path | Purpose |
| :--- | :--- |
| [`astrotrust/`](astrotrust/) | Core audit package: benchmark scenarios, `AstroGuard` rules, schemas, and analysis |
| [`paper/`](paper/README.md) | Camera-ready PDF ([`paper/main.pdf`](paper/main.pdf), matching Zenodo MD5), LaTeX sources, figures |
| [`tools/`](tools/) | Static APK analyzer ([`audit_apks.py`](tools/audit_apks.py)), figure builders, non-circular eval, CI checks |
| [`tests/`](tests/) | Offline test suite covering schemas, metrics, capture redaction, and doc integrity |
| [`data/`](data/README.md) | Aggregate audit summaries only (**no third-party APKs or real-user data are redistributed**) |

## Quick Start

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/):

```bash
uv sync --locked --extra dev
uv run --locked --extra dev python -m pytest
uv run --locked --extra dev ruff check . && uv run --locked --extra dev mypy astrotrust tests tools
uv run --locked python tools/check_research_docs.py
```

For full audit workflows, figure regeneration, and local model setup, see [`docs/methodology.md`](docs/methodology.md) and [`paper/README.md`](paper/README.md).

## Ethics & Observational Scope

This repository documents an independent, non-destructive academic audit of publicly distributed binaries and observable app behavior captured at the stated versions and dates. All test runs used synthetic personas and small, bounded test payments with zero real-user data, zero human subjects, and zero backend probing; see [`docs/ethics.md`](docs/ethics.md) and Section 8 of the [Zenodo preprint](https://doi.org/10.5281/zenodo.24623712).

## Citation

If you build on AstroTrust 2.0, cite the Zenodo preprint ([`CITATION.cff`](CITATION.cff)):

```bibtex
@misc{talukdar2026calibration,
  author       = {Talukdar, Rupjyoti},
  title        = {Calibration Without Safety: Auditing Epistemic Reliance, Dark Patterns, and App Harvesting in Indian AI Astrology Apps},
  year         = {2026},
  month        = nov,
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.24623712},
  url          = {https://doi.org/10.5281/zenodo.24623712},
  note         = {Concept DOI (all versions): 10.5281/zenodo.24623711; Code: https://github.com/MadB0i/AstroTrust; ORCID: 0009-0003-4755-2531}
}
```

## Contact & License

- **Author:** Rupjyoti Talukdar — Independent Researcher, AstroTrust Research Collective (Assam, India) · `contact.rupjyoti26@gmail.com` · [ORCID `0009-0003-4755-2531`](https://orcid.org/0009-0003-4755-2531)
- **License:** Code, documentation, and synthetic fixtures are released under the [MIT License](LICENSE); third-party binaries, vendor names, and excluded logs remain outside redistribution.
