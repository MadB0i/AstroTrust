# Capture Outputs Directory (`data/captures/`)

Generated JSON summaries (`*_summary.json`), Markdown reports (`*_report.md`), and any local `.flow` / `.har` captures placed here are intentionally Git-ignored (except this `README.md`) to prevent accidental leakage of test headers, tokens, device IDs, or proprietary traffic.

Run the analyzer against a test-device flow dump or HAR file using:

```powershell
python tools/analyze_capture.py PATH_TO_CAPTURE.flow
```

See [docs/CAPTURE_PROTOCOL.md](../../docs/CAPTURE_PROTOCOL.md) for the full capture setup and redaction procedure.
