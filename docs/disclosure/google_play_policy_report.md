# Google Play Package Visibility Policy Report — `<queries>` Enumeration

- **To:** Google Play Trust & Safety / Android Package Visibility Policy Team
- **From:** Rupjyoti Talukdar (`contact.rupjyoti26@gmail.com`, ORCID: `0009-0003-4755-2531`), Independent Researcher, AstroTrust Research Collective ([GitHub](https://github.com/MadB0i/AstroTrust))
- **Date:** November 26, 2026
- **Subject App:** `Astrotalk` (`com.astrotalk`, `v1.1.545`, versionCode `545`, `89,910,970` bytes, SHA-256: `527331d1c60a953cb0a9613438e967f398d970e9767349f0cbccfbd56ecffe3d`)
- **Natural-Experiment Control:** `Pandit Ji` (`com.astrology.panditji`, `v1.1.421`, versionCode `421`, `97,030,138` bytes, SHA-256: `d08a504021748671f03df7b6cc21d18fd6dbb1e73ef6ae0c369b71dc42b1b647`)

## Technical Summary

While auditing five Indian Android astrology applications ([audit_apks.py](../../tools/audit_apks.py); outputs in [apk_forensic_summary.json](../../data/results/apk_forensic_summary.json)), we observed a structured bypass of Android 11+ (API level 30+) package visibility controls and Google Play's `QUERY_ALL_PACKAGES` policy:

1. **Manifest `<queries>` Mirroring of a 787-App Target List:**
   - `Astrotalk.apk` (`v1.1.545`) does **not** declare `android.permission.QUERY_ALL_PACKAGES` (`has_query_all_packages = false`), avoiding Google Play Console's restricted-permission justification review.
   - Instead, its compiled binary `AndroidManifest.xml` declares **823 `<package>` elements** (**804 unique package IDs**) inside `<queries>`.
   - Exact set comparison against bundled asset `assets/apppackges.json` (`63,591` bytes, **787** distinct `{"name", "package_name"}` objects) establishes **787/787 (100.0%)** coverage inside `<queries>`. Only 17 remaining entries in `<queries>` are standard payment/login/maps SDK dependencies.
2. **Sensitive Domains Enumerated:**
   - The 787-app catalog spans **113** banking/UPI/remittance apps, **103** rival astrology apps, **90** OTT/media apps, **49** real-money gambling/betting apps, **46** dating/matrimony apps, **38** stock/crypto apps, **36** consumer loan/BNPL/gold-loan apps, **34** health/insurance/wearable apps, **26** EdTech/job portals, **18** devotional apps, **16** reproductive-health/pregnancy/mental-therapy apps (`Flo`, `Clue`, `Premom`, `BetterHelp`, `Talkspace`), **9** gig-driver/delivery partner apps, **8** Indian government ID/welfare apps (`DigiLocker`, `mAadhaar`, `PM-KISAN GoI`), and **8** AI assistants.
3. **Bytecode Discovery & Network Upload Chain:**
   - `classes3.dex` (`com.astrotalk.utils.ExternalPackageTracker` / `u0`, gated by `"execute_24h_check"`) calls `PackageManager.getInstalledPackages()` and targets `@POST("user/apps/installed")` (`com.astrotalk.controller.b.S3`) alongside `@POST("/AstrotalkPayments/user/save/user-upi-apps")` (`O1`).
   - An isolated Android 14 emulator proxy test ([CAPTURE_PROTOCOL.md](../CAPTURE_PROTOCOL.md)) verified live pre-login execution of `POST /AstrotalkPayments/user/save/user-upi-apps` (`{"upiAppsData":[]}`, HTTP 403).
4. **Control Comparison (`Pandit Ji v1.1.421`):**
   - `Pandit Ji` shares `6,193` ZIP entries (`86.99%`) and `3,172` identical files (`44.56%`) with `Astrotalk`, yet declares only **26** standard `<queries>` entries and contains zero `apppackges.json` or `ExternalPackageTracker`, confirming deliberate per-product profiling on `com.astrotalk`.

## Suggested Play Store Policy Action

Flag APKs declaring large static `<queries>` enumerations (e.g., $>50$ unrelated non-PSP/non-sharing consumer package IDs) for `QUERY_ALL_PACKAGES`-equivalent Google Play Console policy review to close large-scale manifest enumeration workarounds.
