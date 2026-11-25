# Overleaf LaTeX Project (`AstroTrust 2.0`)

This directory is pre-formatted for direct compilation in **Overleaf** using **`pdfLaTeX`** (standard TeX Live packages: `newtxtext`, `newtxmath`, `tabularx`, `booktabs`, `seqsplit`, `xurl`, `fancyhdr`, `tikz`, `pgfplots`, `natbib`, `balance`).

## Two Fastest Ways to Compile on Overleaf

1. **Direct ZIP Upload:** Upload `D:\ASTRO\astrotrust_overleaf.zip` via **Overleaf $\rightarrow$ New Project $\rightarrow$ Upload Project** and click **Recompile**.
2. **GitHub Import:** Connect Overleaf to `https://github.com/MadB0i/AstroTrust`, open `paper/`, set **Compiler = pdfLaTeX** and **Main document = `main.tex`**, and click **Recompile**.

## Included Source Tree

- [main.tex](main.tex) — Primary two-column Overleaf manuscript with preprint header/footer, ragged-right `tabularx` column types, and clickable links.
- [sections/01_intro_related.tex](sections/01_intro_related.tex) — Abstract, Introduction, Proof Table, and Indian Regulatory Context.
- [sections/02_benchmark_apps.tex](sections/02_benchmark_apps.tex) — AstroTrust 2.0 Benchmark Protocol and Live Consumer Audit ($N=6$).
- [sections/03_apk_forensics.tex](sections/03_apk_forensics.tex) — APK Forensics, Vector TikZ Pipeline (`fig:pipeline`), 787-App Bar Chart (`fig:taxonomy`), and Natural Experiment vs.\ `Pandit Ji`.
- [sections/04_eval_astroguard.tex](sections/04_eval_astroguard.tex) — Tripartite Comparison ($N=49$), Fisher/Wilson Statistics, Dissociation Plot (`fig:dissociation`), `Qwen2.5-0.5B` Instability, and `AstroGuard` Diagnostics.
- [sections/05_discussion_appendix.tex](sections/05_discussion_appendix.tex) — Limitations, India Policy Proposals, and Full 64-Character SHA-256 Table (`tab:hashes`).
- [references.bib](references.bib) — 13 verified BibTeX entries (`plainnat` style).
