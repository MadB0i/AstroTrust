# LaTeX Manuscript Source (`AstroTrust 2.0`)

This directory contains the self-contained LaTeX source for the working paper:

*`Calibration Without Safety: Auditing Epistemic Reliance, Monetization Dark Patterns, and Installed-App Harvesting in AI Astrology Apps in India`*

## Contents

- [main.tex](main.tex) — Primary two-column driver document (uses standard TeX packages + vector `tikz`/`pgfplots` figures with zero external binary figure dependencies).
- [sections/01_intro_related.tex](sections/01_intro_related.tex) — Abstract, Introduction, Proof Roadmap, and Related Work & Indian Regulatory Context.
- [sections/02_benchmark_apps.tex](sections/02_benchmark_apps.tex) — AstroTrust 2.0 Protocol, Deviation Disclosures, and Consumer App Audit ($N=6$ live sessions).
- [sections/03_apk_forensics.tex](sections/03_apk_forensics.tex) — Static APK Reverse Engineering, Pipeline TikZ Diagram, 787-App pgfplots Chart, and `Astrotalk` vs. `Pandit Ji` Natural Experiment.
- [sections/04_eval_astroguard.tex](sections/04_eval_astroguard.tex) — Tripartite Comparative Evaluation ($N=49$), Fisher Exact Tests, `Qwen2.5-0.5B` Instability Analysis, and Dual-Layer `AstroGuard` Diagnostic.
- [sections/05_discussion_appendix.tex](sections/05_discussion_appendix.tex) — Limitations, Policy Proposals, and SHA-256 Cryptographic Inventory.
- [references.bib](references.bib) — Verified BibTeX bibliography.

## Building Locally or on Overleaf

Upload the entire `paper/` directory to Overleaf (with `pdflatex` compiler) or compile locally with:

```powershell
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

All figures (`tikz` and `pgfplots`) and tables (`booktabs` / `tabularx`) render natively without extra downloads, and currency uses `INR~` for full `pdflatex` ASCII safety.
