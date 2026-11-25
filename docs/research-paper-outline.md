# Working manuscript outline — AstroTrust 2.0

* **Full working manuscript:** [paper_draft.md](paper_draft.md)
* **Empirical benchmark tables:** [empirical_comparison_table.md](../data/results/empirical_comparison_table.md) ([GitHub](https://github.com/MadB0i/AstroTrust/blob/main/data/results/empirical_comparison_table.md))
* **Static APK forensic summary:** [apk_forensic_summary.json](../data/results/apk_forensic_summary.json) ([GitHub](https://github.com/MadB0i/AstroTrust/blob/main/data/results/apk_forensic_summary.json))
* **Repository:** https://github.com/MadB0i/AstroTrust

**Working Title:** *Surface Calibration, Predatory Funnels, and Device Surveillance: An Empirical Audit of Epistemic Reliance, Dark Patterns, and Privacy Harvesting in AI Astrology Applications*

### Manuscript Structure & Verified Evidence Map

1. **Abstract & Introduction:**
   - Central tripartite dissociation thesis: **Surface Epistemic Calibration != Consumer Product Safety**.
   - Research questions (`RQ1`–`RQ4`) spanning epistemic boundary adherence, belief-conditioned sycophancy, dark-pattern monetization, and binary device surveillance.
2. **Related Work & Regulatory Grounding:**
   - Empirical astrology tests ([Carlson, 1985](https://www.nature.com/articles/318419a0)) and personal-validation cold reading (Forer, 1949; Barnum effect).
   - LLM sycophancy and RLHF preference alignment (Perez et al., 2022; Sharma et al., ICLR 2024).
   - Dark pattern taxonomies (Gray et al., CHI 2018; Mathur et al., CSCW 2019) and India's CCPA *Guidelines for Prevention and Regulation of Dark Patterns* (Nov 2023).
   - Mobile installed-app fingerprinting privacy (Seneviratne et al., 2014/2015), Android 11+ `<queries>` vs. `QUERY_ALL_PACKAGES` Play Store policy, and RBI Digital Lending restrictions on installed-app harvesting.
3. **AstroTrust 2.0 Benchmark & Multi-Layer Audit Protocol:**
   - Eight canonical scenarios across three stakes tiers (`atb-career-001` through `atb-everyday-008`), controlled belief contrasts (`neutral`, `positive_expectation`, `negative_expectation`), provisional constructs (`ADRS`, `BCAS`; see [terminology.md](terminology.md)), and cryptographic SHA-256 chain of custody (`manual-1.0`, `consumer-1.1`, `local-request-1.0`).
   - Transparent disclosure of exploratory pilot status and synthetic profile deviation (`consumer-profile-001` snapshot vs. `"Rohan Sharma"` interactive inputs).
4. **Live Consumer App Audit ($N=6$ Sessions, 5 Android Apps):**
   - **Astrotalk (`Ritu Ji` free & paid ₹11.81):** `0:16` Zeigarnik audio cliffhanger, `FLAG_SECURE`, post-session `₹5/min -> ₹19/min` surge leaving `₹15` orphaned balance, retention questions closing calibrated text.
   - **Pandit Ji (sister reskin):** Identical `"Hi Jagira"` banner, shared planetary chart (`Asc 24.14, Sa 8.95, Me 25.46`), byte-identical `0:16` female audio paired with male rishi avatar (`"dekh rahi hoon"`), `FLAG_SECURE`, `"2025"` year mismatch, upsell to `'Astro Alokik'`.
   - **Reva (`ShareChat` / `Mohalla Tech`):** Surface-calibrated `reflective_only` text paired with `₹1` initial payment binding a 5-year `₹699` recurring UPI Autopay mandate (`PAYTMSUBS6111125150547561489`) and immediate `₹699 / 3 months` paywall.
   - **AstroSage Kundli (`Rahasya Veda`):** `1m30s` free timer (`₹1/min -> ₹19/min`), synthetic `"1 Years of Experience"` and `"1,176,176 reviews"` counter, calibrated career answer ending with salary-package hook.
   - **AstroTime (`Elitegem Global`):** Unprompted Barnum cold-reading (`"aap kaafi emotional bhi ho..."`) within 30–60s, `60s` inactivity auto-close, `100% Cashback` recharge prompt, shared onboarding phrasing despite separate React Native stack.
5. **Static APK Forensics & Natural Experiment (`Astrotalk` vs. `Pandit Ji`, `Reva`, `AstroTime`):**
   - `Astrotalk.apk` (`com.astrotalk`, `v1.1.545`, code `545`, `89.91 MB`) embeds `assets/apppackges.json` (**787 target applications**) and mirrors **787/787** inside `<queries>` (`823` `<package>` tags, `804` unique, `QUERY_ALL_PACKAGES=False`).
   - Decompiled DEX engine `com.astrotalk.utils.ExternalPackageTracker` (`u0` gated by `"execute_24h_check"`) invokes `PackageManager.getInstalledPackages` and uploads matches via Retrofit `@POST("user/apps/installed")` (`S3`), alongside `@POST("/AstrotalkPayments/user/save/user-upi-apps")` (`O1`).
   - Exhaustive 16-domain taxonomy of all `787` targets (including `103` astrology/competitor apps, `113` banking/UPI apps, `49` gambling/betting, `46` dating/matrimony, `38` trading/crypto, `36` loans/credit, `16` reproductive/fertility/therapy apps, `9` gig-worker driver apps, `8` govt welfare/ID apps, `8` AI assistants).
   - Binary diff vs. sister clone `Pandit Ji.apk` (`v1.1.421`, code `421`): `6,193` overlapping ZIP paths (`86.99%` of Pandit Ji), `3,172` byte-identical files (`44.56%`), `1,470` `"astrotalk"` strings in DEX, yet only `26` `<queries>` entries and no `ExternalPackageTracker`.
   - Hermes RN inspection (`Reva`: `DETECT_SCREEN_CAPTURE`, `/payments-api-gateway/v1/subscriptions/...`, `revaastro.in`; `AstroTime`: `apis.theastrotime.com`, `posthog.theastrotime.com`, `cloud-api.livekit.io`; `AstroSage AI.apk`: empty `0`-byte download stub).
6. **Comparative Evaluation Across $N=49$ Traces:**
   - Frontier LLMs ($N=27$ across ChatGPT `GPT5.5`, Claude `Haiku-4.5`/`Sonnet-5.5`, Gemini `3.5 Flash-Lite`/`3.8 Flash`): `100%` `reflective_only`, `0%` dark patterns, honest disclosure of Hinglish session leak and truncated paste artifact.
   - Local open baseline (`Qwen/Qwen2.5-0.5B-Instruct`, $N=16$): `0%` dark patterns yet `62.5% (10/16)` epistemic instability (`50.0% (8/16)` explicit zodiac/hallucination/misread, `43.8% (7/16)` mid-sentence cutoff at 512 tokens).
7. **Dual-Layer Defense (`AstroGuard` + `AstroAudit`) & Validation:**
   - Layer 1 conversational evaluation (`AstroGuard-Rules` baseline + prompt-masked `AstroGuard-LoRA` on verified non-empty traces; in-domain stratified validation metrics).
   - Layer 2 billing/UI/APK inspection proving text-only classifiers cannot detect covert UPI mandates (`Reva`) or background package harvesting (`Astrotalk`).
8. **Ethics, Governance, Limitations & Policy Recommendations.**
