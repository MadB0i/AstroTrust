# Coordinated Consumer-Safety Disclosure Notice — Reva (Mohalla Tech / ShareChat)

- **To:** Mohalla Tech Pvt. Ltd. (ShareChat / Reva) Security, Trust & Compliance Team
- **From:** Rupjyoti Talukdar (`contact.rupjyoti26@gmail.com`, ORCID: `0009-0003-4755-2531`), Independent Researcher, AstroTrust Research Collective ([GitHub](https://github.com/MadB0i/AstroTrust))
- **Disclosure Window:** 90-day coordinated disclosure (30-day initial acknowledgment requested prior to public release)
- **Pinned Build & Session Audited:**
  - `Reva.apk` (`in.mohalla.reva`, `v2026.24.2`, versionCode `2026242`, `38,405,425` bytes, SHA-256: `d399c180003c497cb4dec8b3543c28f162fe425e24e4e0051ee7a25805ae28e7`)
  - Live Android capture session on November 11, 2026 IST (single fictional-profile test transaction of `INR 1`, with the UPI Autopay mandate immediately revoked after capture; zero real-user data).

## Summary of Technical Findings

During an academic audit of AI astrology consumer flows ([ethics.md](../ethics.md); binary metadata recorded in [apk_forensic_summary.json](../../data/results/apk_forensic_summary.json)), `Reva` produced well-calibrated conversational text explicitly noting that astrology cannot reliably predict hiring outcomes (`reflective_only`). However, the surrounding billing flow exhibited a high-risk recurring-mandate UX pattern:

1. **Nominal `INR 1` Trial Initiating a 5-Year `INR 699` UPI Autopay Mandate:**
   - Completing the introductory `INR 1` trial checkout initiated a recurring Paytm UPI Autopay mandate (`PAYTMSUBS...` to `Sharechat`) authorized up to **`INR 699` ("As presented")** over a **five-year window (November 11, 2026 to 2031)**.
   - Immediately after delivering one chat response, the application locked further dialogue behind an immediate `INR 699 / 3 months` paywall (`"Trial expired. Reva has your answers ready..."`).
   - Static inspection of `Reva.apk` (`v2026.24.2`) confirms subscription gateway integration (`/payments-api-gateway/v1/subscriptions/`, `revaastro.in`) alongside Android 14 `DETECT_SCREEN_CAPTURE=True`.

## Recommended Remediation

1. **Decouple Introductory Trials from Recurring UPI Autopay Mandates:** Treat `INR 1` onboarding trials strictly as one-time UPI Intent/Collect payments without silently pre-authorizing multi-year recurring `INR 699` debits.
2. **Explicit Unbundled Recurring Consent:** Present any `INR 699 / 3 months` subscription authorization on a separate, clearly labeled opt-in checkout step after trial expiration, aligning with RBI e-mandate transparency norms and India's CCPA *Guidelines for Prevention and Regulation of Dark Patterns, 2023* (*Subscription Trap* and *Bait and Switch*).
3. **Restrict Screen-Capture Detection:** Limit `DETECT_SCREEN_CAPTURE` / `FLAG_SECURE` to payment/OTP surfaces rather than subscription pricing and consultation views.
