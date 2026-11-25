# Empirical Comparison Table: AstroTrust 2.0 Benchmark

| Evaluation Metric | Frontier Models (ChatGPT, Claude, Gemini) | Consumer Astrology Apps (5 Apps / 6 Runs) | Local Open Baseline (`Qwen2.5-0.5B-Instruct`) |
| :--- | :--- | :--- | :--- |
| **Sample Size ($N$)** | 27 captures (`atb-career-001`) | 6 live sessions | 16 local inference runs |
| **Calibration / `reflective_only`** | 27/27 (`100.0%`) | 3/6 (`50.0%`) | 9/16 (`56.2%`) |
| **Explicit Hallucination / Misread** | 0.0% (0/27) | 16.7% (1/6) | **50.0% (8/16)** |
| **Any Epistemic Instability** | 0.0% (0/27) | 16.7% (1/6) | **62.5% (10/16)** |
| **Mid-Sentence Token Truncation** | 0.0% (0/27) | N/A (paywall cutoffs: 3/6) | **43.8% (7/16)** |
| **Commercial Dark Pattern Rate** | 0.0% (0/27) | **100.0% (6/6)** | 0.0% (0/16) |
| **Barnum / Retention Hooks** | 0.0% (0/27) | **83.3% (5/6)** | 0.0% (0/16) |
| **Targeted APK Surveillance** | None | **787 target packages** (`assets/apppackges.json` -> `ExternalPackageTracker` in Astrotalk) | None |
| **Mean Response Length** | 2003.8 chars | 637.5 chars | 2624.1 chars |

## Core Tripartite Dissociation Finding

1. **Surface Epistemic Calibration $\neq$ Consumer Product Safety:** Three consumer responses (Reva, AstroSage, paid Astrotalk) emitted epistemically calibrated disclaimers in text (`reflective_only`), yet every tested consumer app (`6/6` runs, `5/5` apps) embedded structural monetization dark patterns (₹1->₹699 5-year UPI Autopay mandates, ₹5->₹19/min dynamic surge pricing stranding balances, `0:16` Zeigarnik audio cliffhangers, 60s auto-close cashback triggers, fake `1,176,176` review counters).
2. **Small Open-Weight Models Exhibit Zero Dark Patterns Yet High Epistemic Instability:** `Qwen2.5-0.5B-Instruct` generated `0` commercial hooks but exhibited 62.5% (10/16) epistemic risk (50.0% (8/16) explicit zodiac/age/instruction hallucinations and 43.8% (7/16) mid-sentence token cutoffs).
3. **Static Binary Surveillance:** `Astrotalk.apk` (`v1.1.545`, code `545`) bundles `assets/apppackges.json` enumerating **787 target applications** mirrored inside `<queries>` (`823` tags, `804` unique packages) and exfiltrated via `ExternalPackageTracker` -> `POST user/apps/installed`, whereas sister reskin `Pandit Ji.apk` (`v1.1.421`, code `421`) shares `6,193` paths (`86.99%`) yet omits `ExternalPackageTracker`.
