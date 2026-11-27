# Coordinated Vulnerability & Privacy Disclosure Notice — Astrotalk / Pandit Ji

- **To:** Astrotalk Security, Privacy & Product Integrity Team
- **From:** Rupjyoti Talukdar (`contact.rupjyoti26@gmail.com`, ORCID: `0009-0003-4755-2531`), Independent Researcher, AstroTrust Research Collective ([GitHub](https://github.com/MadB0i/AstroTrust))
- **Disclosure Window:** 90-day coordinated disclosure (30-day initial acknowledgment requested prior to public manuscript/artifact release)
- **Pinned Builds Audited:**
  - `Astrotalk.apk` (`com.astrotalk`, `v1.1.545`, versionCode `545`, `89,910,970` bytes, SHA-256: `527331d1c60a953cb0a9613438e967f398d970e9767349f0cbccfbd56ecffe3d`)
  - `Pandit Ji.apk` (`com.astrology.panditji`, `v1.1.421`, versionCode `421`, `97,030,138` bytes, SHA-256: `d08a504021748671f03df7b6cc21d18fd6dbb1e73ef6ae0c369b71dc42b1b647`)

## Summary of Technical Findings

During non-destructive static binary inspection ([tools/audit_apks.py](../../tools/audit_apks.py)), isolated Android 14 emulator proxy testing ([CAPTURE_PROTOCOL.md](../CAPTURE_PROTOCOL.md)), and synthetic-profile consumer sessions (`consumer-profile-001` / fictional chat inputs; zero real user records), we identified three technical and consumer-trust issues:

### 1. 787-App Package Enumeration Without `QUERY_ALL_PACKAGES` (`Astrotalk v1.1.545`)
- `AndroidManifest.xml` omits `android.permission.QUERY_ALL_PACKAGES` (`False`), yet declares **823 `<package>` tags** (**804** unique package names) inside `<queries>`.
- Bundled asset `assets/apppackges.json` (`63,591` bytes) enumerates **787** distinct consumer applications, with **787/787 (100.0%)** mirrored verbatim into manifest `<queries>`. Targeted categories include banking/UPI (113), rival astrology apps (103), OTT/media (90), real-money gambling/betting (49), dating/matrimony (46), stock/crypto trading (38), consumer loans/BNPL/gold loans (36), health/wearables (34), EdTech/job portals (26), reproductive health/mental therapy (16), gig-economy driver apps (9), and Indian government ID/welfare apps (8).
- `classes3.dex` (`com.astrotalk.utils.ExternalPackageTracker` / `u0`, gated by `SharedPreferences` flag `"execute_24h_check"`) invokes `PackageManager.getInstalledPackages()` and targets Retrofit `@POST("user/apps/installed")` (`com.astrotalk.controller.b.S3`) alongside `@POST("/AstrotalkPayments/user/save/user-upi-apps")` (`O1`).
- In an isolated Android 14 emulator test capture (`mitmproxy v12.3.1`, unauthenticated guest session), dismissing login from `ChatAstrologerlistActivity` immediately triggered `POST https://payments-api.astrotalk.in/AstrotalkPayments/user/save/user-upi-apps` (`{"upiAppsData":[]}`, HTTP 403).

### 2. Cross-App Session / Test-Handle Leakage (`Astrotalk` $\leftrightarrow$ `Pandit Ji`)
- `Pandit Ji.apk` (`v1.1.421`) shares **6,193 ZIP paths (86.99%)** and **3,172 byte- and CRC32-identical files (44.56%)** with `Astrotalk.apk`, alongside `1,470` `"astrotalk"` strings in DEX.
- On a separate live installation of `Pandit Ji`, the upsell banner greeted our test device with the exact internal handle registered exclusively on `Astrotalk` (`[REDACTED_TEST_HANDLE]`), rendered identical Kundali chart degrees (`Asc 24.14, Sa 8.95, Me 25.46`), and played the **byte-identical 16-second female TTS voice note** despite displaying an elderly male sage avatar (`"Chalo, main aapki kundli dekh rahi hoon"`).
- Note: `Pandit Ji.apk` contains **zero** `assets/apppackges.json`, zero `ExternalPackageTracker`, and only 26 standard `<queries>` entries.

### 3. Post-Session Per-Minute Pricing Surge (`Astrotalk` Paid Session)
- Following a paid session (`INR 11.81` via Google Pay), the displayed consultation rate shifted immediately from `INR 5/min` to `INR 19/min`, stranding an unusable `INR 15` wallet balance without another top-up.

## Recommended Remediation

1. **Remove Non-Essential `<queries>` & Package Telemetry:** Restrict `<queries>` strictly to active payment PSPs/UPI intents required at checkout, and deprecate `assets/apppackges.json` and `ExternalPackageTracker` (`user/apps/installed`) to align with Google Play package visibility rules and India's DPDP Act, 2023 purpose-limitation and data-minimization obligations.
2. **Isolate Tenant Session & Account Namespaces:** Decouple `com.astrology.panditji` account/upsell banners and media assets from `com.astrotalk` backend state, and fix persona avatar/gender mismatch bugs.
3. **Lock Upfront Session Rates:** Display unambiguous per-minute pricing prior to wallet recharge without post-session surges stranding small remaining balances (India CCPA 2023 *Drip Pricing* / *Bait and Switch* compliance).
