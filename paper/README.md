# Overleaf LaTeX Project (`AstroTrust 2.0`)

This directory is pre-formatted for direct compilation via local **`pdfLaTeX`** (MiKTeX / TeX Live) or **Overleaf** using packages `newtxtext`, `newtxmath`, `newtxtt`, `tabularx`, `booktabs`, `seqsplit`, `url`, `fancyhdr`, `tikz`, `pgfplots`, `natbib`, `graphicx`.

## Rebuilding Figures & Compiling Locally or on Overleaf

1. **Regenerate Figures & Compile Locally (`pdfLaTeX`):**
   - `python tools/make_evidence_strip.py` -> writes `paper/figures/fig_consumer_evidence.png`
   - `python tools/make_paper_figures.py --out-dir paper/figures` -> writes vector `fig_app_taxonomy.pdf` and `fig_four_cohort.pdf`
   - Compile `paper/main.tex` with `pdflatex main && bibtex main && pdflatex main && pdflatex main`.
2. **GitHub Import on Overleaf:** Connect Overleaf to `https://github.com/MadB0i/AstroTrust`, open `paper/`, set **Compiler = pdfLaTeX** and **Main document = `main.tex`**, and click **Recompile**.

## Included Source Tree

- [main.tex](main.tex) — Primary two-column manuscript with running header/footer, PDF metadata (`\hypersetup`), `newtxtt` clean zeroes, slash/dot URL breaking, and clickable links.
- [sections/01_intro_related.tex](sections/01_intro_related.tex) — Abstract, Introduction, Proof Table, and Indian Regulatory Context.
- [sections/02_benchmark_apps.tex](sections/02_benchmark_apps.tex) — AstroTrust 2.0 Benchmark Protocol, Live Consumer Audit ($N=6$), and 3-panel visual evidence figure (`figures/fig_consumer_evidence.png`).
- [sections/03_apk_forensics.tex](sections/03_apk_forensics.tex) — APK Forensics, Vector TikZ Pipeline (`fig:pipeline`), Vector 787-App Bar Chart (`figures/fig_app_taxonomy.pdf`), and Natural Experiment vs.\ `Pandit Ji`.
- [sections/04_eval_astroguard.tex](sections/04_eval_astroguard.tex) — Tripartite Comparison ($N=93$), Fisher/Wilson Statistics, Vector Cohort Dissociation Plot (`figures/fig_four_cohort.pdf`), `Qwen2.5` Scale Effects, and Non-Circular `AstroGuard` Diagnostics ($N=44$).
- [sections/05_discussion_appendix.tex](sections/05_discussion_appendix.tex) — Limitations, India Policy Proposals, Research Ethics & Observational Scope, Conclusion, and Full 64-Character SHA-256 Table (`tab:hashes`).
- [references.bib](references.bib) — 14 verified BibTeX entries (`plainnat` style).
