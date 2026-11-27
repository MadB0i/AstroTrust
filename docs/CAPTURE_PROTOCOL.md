# Network Capture Protocol (`mitmproxy` & HAR)

This protocol defines how to verify client-side telemetry from a researcher-controlled test device using `mitmproxy` or HAR exports and process captures offline with [tools/analyze_capture.py](../tools/analyze_capture.py). See [ethics.md](ethics.md) and [data/README.md](../data/README.md) for research boundaries.

## 1. Strict Safety & Privacy Rules

* **Isolated Test Hardware Only:** Use a dedicated wipeable Android test phone or clean Android emulator reserved for lab work. Never intercept traffic on a primary phone.
* **Fictional Account Only:** Sign in using a freshly created test account and fixed fictional profile attributes (`consumer-profile-001` in [consumer-collector.md](consumer-collector.md)). Do not enter real birth details, personal phone numbers, real payment credentials, or personal UPI mandates.
* **Clean App Inventory:** Do not install personal banking, messaging, or health apps on the capture device. If testing whether specific package categories trigger payloads, install benign public apps or mock package stubs strictly for the test session.
* **Keep Raw Captures Local:** Never commit raw `.flow`, `.mitm`, or `.har` files or unredacted outputs to Git; store them only in local Git-ignored folders such as `data/captures/`.

## 2. Workstation Setup (`mitmproxy`)

1. Install `mitmproxy` in an isolated workstation environment (separate from minimal CI dependencies if preferred).
2. Start a recording proxy bound to your local lab LAN interface:

```powershell
mitmdump -w D:\ASTRO\captures\test_session.flow --listen-port 8080
```

Alternatively, launch `mitmweb --listen-port 8080` if you want to inspect live requests and click **File $\rightarrow$ Save / Export HAR** cleanly.

## 3. Test Device Setup & Recording

1. Connect the Android test device to the same isolated lab Wi-Fi network.
2. Configure **Wi-Fi $\rightarrow$ Modify network $\rightarrow$ Manual Proxy** pointing to the workstation IP and port `8080`.
3. Open `http://mitm.it` in the test phone's browser and install the **mitmproxy CA certificate** for VPN & apps (note: Android 7+ apps that do not trust user CAs unless running inside an emulator/debuggable environment may require standard system-CA lab setup without bypassing third-party access controls on external servers).
4. Launch the target app (e.g., `Astrotalk`), sign in with the fictional test identity, wait through initial onboarding/home-screen initialization (when background checks such as `execute_24h_check` run), and close the session cleanly.
5. Stop `mitmdump` (`Ctrl+C`) so the `.flow` file flushes cleanly to disk, and immediately remove the manual Wi-Fi proxy from the phone.

## 4. Offline Redaction & Analysis

Run [tools/analyze_capture.py](../tools/analyze_capture.py) on the captured `.flow` or `.har` file. It automatically strips and replaces `Authorization` headers, `id`/session headers, bearer/JWT tokens, UUID/hex device IDs, and phone numbers with `[REDACTED]` before writing outputs under `data/captures/`:

```powershell
python tools/analyze_capture.py D:\ASTRO\captures\test_session.flow
```

Optional overrides:
* `--apppackges PATH`: compare extracted package names against a standalone JSON copy of `assets/apppackges.json` instead of `--apk` (which defaults to `D:\ASTRO\Astrotalk.apk`).
* `--out-dir DIR`: change output directory (defaults to `data/captures/`).

Review both `<stem>_summary.json` and `<stem>_report.md` manually before citing metrics or archiving derived tables outside your workstation.
