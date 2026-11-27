"""Unit tests for tools/analyze_capture.py using strictly synthetic fixtures."""

from __future__ import annotations

import gzip
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "analyze_capture.py"


def _load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("analyze_capture_tool", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tnet_encode(val: Any) -> bytes:
    if isinstance(val, bytes):
        return f"{len(val)}:".encode("ascii") + val + b","
    if isinstance(val, str):
        raw = val.encode("utf-8")
        return f"{len(raw)}:".encode("ascii") + raw + b";"
    if isinstance(val, bool):
        b = b"true" if val else b"false"
        return f"{len(b)}:".encode("ascii") + b + b"!"
    if isinstance(val, int):
        b = str(val).encode("ascii")
        return f"{len(b)}:".encode("ascii") + b + b"#"
    if val is None:
        return b"0:~"
    if isinstance(val, list):
        inner = b"".join(_tnet_encode(item) for item in val)
        return f"{len(inner)}:".encode("ascii") + inner + b"]"
    if isinstance(val, dict):
        inner = b"".join(_tnet_encode(k) + _tnet_encode(v) for k, v in val.items())
        return f"{len(inner)}:".encode("ascii") + inner + b"}"
    raise TypeError(f"Unsupported type: {type(val)}")


def test_har_capture_filtering_overlap_and_redaction(tmp_path: Path) -> None:
    tool = _load_tool()

    # SYNTHETIC TEST FIXTURE — NOT REAL CAPTURE DATA
    catalog = [
        {"name": "Synthetic Pay", "package_name": "com.phonepe.app"},
        {"name": "Synthetic Wallet", "package_name": "net.one97.paytm"},
        {"name": "Synthetic Unsent", "package_name": "com.tinder"},
    ]
    catalog_path = tmp_path / "synthetic_apppackges.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    secret_tokens = [
        "SYNTH-BEARER-SECRET-XYZ",
        "SYNTH-DEV-998877",
        "SYNTH-HW-445566",
        "SYNTH-ANON-778899",
        "SYNTH-FCM-112233",
        "9876543210",
        "919811122233",
        "88776655",
        "sid=SYNTHCOOKIE123",
        "12345678-1234-1234-1234-1234567890ab",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzeW50aCJ9.signaturesynth1",
    ]

    har = {
        "log": {
            "version": "1.2",
            "entries": [
                {
                    "startedDateTime": "2026-11-25T10:00:00Z",
                    "request": {
                        "method": "GET",
                        "url": "https://example.org/healthcheck",
                        "headers": [{"name": "Host", "value": "example.org"}],
                    },
                    "response": {"status": 200},
                },
                {
                    "startedDateTime": "2026-11-25T10:01:00Z",
                    "request": {
                        "method": "POST",
                        "url": (
                            "https://api.prod.astrotalk.in/AstroTalk/user/apps/installed"
                            "?device_id=SYNTH-DEV-998877&fcmId=SYNTH-FCM-112233"
                            "&token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzeW50aCJ9.signaturesynth1"
                        ),
                        "headers": [
                            {"name": "Authorization", "value": "Bearer SYNTH-BEARER-SECRET-XYZ"},
                            {"name": "id", "value": "88776655"},
                            {"name": "hardware_id", "value": "SYNTH-HW-445566"},
                            {"name": "anonymousid", "value": "SYNTH-ANON-778899"},
                            {"name": "Cookie", "value": "sid=SYNTHCOOKIE123"},
                            {"name": "Content-Type", "value": "application/json"},
                        ],
                        "postData": {
                            "mimeType": "application/json",
                            "text": json.dumps(
                                {
                                    "device_id": "12345678-1234-1234-1234-1234567890ab",
                                    "phone": "+919811122233",
                                    "apps": [
                                        {"package_name": "com.phonepe.app", "name": "PhonePe"},
                                        {
                                            "package_name": "com.example.synthetic.unlisted",
                                            "name": "Synthetic Extra",
                                        },
                                    ],
                                }
                            ),
                        },
                    },
                    "response": {"status": 200},
                },
                {
                    "startedDateTime": "2026-11-25T10:02:00Z",
                    "request": {
                        "method": "POST",
                        "url": "https://api.prod.astrotalk.in/AstrotalkPayments/user/save/user-upi-apps",
                        "headers": [{"name": "Host", "value": "api.prod.astrotalk.in"}],
                        "postData": {
                            "mimeType": "application/json",
                            "text": json.dumps(
                                {
                                    "mobile": "9876543210",
                                    "upiApps": [{"appPackage": "net.one97.paytm"}],
                                }
                            ),
                        },
                    },
                    "response": {"status": 200},
                },
            ],
        }
    }
    har_path = tmp_path / "synthetic_device.har"
    har_path.write_text(json.dumps(har), encoding="utf-8")

    summary = tool.analyze_capture(
        har_path,
        catalog_path=catalog_path,
        apk_path=None,
        is_synthetic=True,
    )
    assert summary["provenance"] == "SYNTHETIC_FIXTURE"
    assert summary["total_requests_parsed"] == 3
    assert summary["astrotalk_host_request_count"] == 2
    assert summary["tracker_endpoint_match_count"] == 2

    comp = summary["package_comparison"]
    assert comp["total_unique_packages_sent"] == 3
    assert comp["overlap_with_catalog_count"] == 2
    assert comp["sent_packages"] == [
        "com.phonepe.app",
        "com.example.synthetic.unlisted",
        "net.one97.paytm",
    ]
    assert comp["overlap_packages"] == ["com.phonepe.app", "net.one97.paytm"]
    assert comp["non_catalog_packages"] == ["com.example.synthetic.unlisted"]

    out_dir = tmp_path / "out_captures"
    json_out, md_out = tool.write_capture_outputs(summary, out_dir=out_dir)
    serialized = json_out.read_text("utf-8") + "\n" + md_out.read_text("utf-8")

    assert "[REDACTED]" in serialized
    for secret in secret_tokens:
        assert secret not in serialized


def test_mitmproxy_flow_stream_with_apk_catalog_and_cli(tmp_path: Path) -> None:
    # SYNTHETIC TEST FIXTURE — NOT REAL CAPTURE DATA
    apk_path = tmp_path / "synthetic_astrotalk.apk"
    with zipfile.ZipFile(apk_path, "w") as zf:
        zf.writestr(
            "assets/apppackges.json",
            json.dumps([{"name": "Groww", "package_name": "com.nextbillion.groww"}]),
        )

    gzip_body = gzip.compress(
        json.dumps([{"packageName": "com.nextbillion.groww"}]).encode("utf-8")
    )
    frame = _tnet_encode(
        {
            b"type": b"http",
            b"request": {
                b"method": b"POST",
                b"scheme": b"https",
                b"host": b"api-astrobuddy.astrotalk.in",
                b"path": b"/AstroTalk/user/apps/installed?device_id=SYNTHDEVICE999",
                b"headers": [
                    [b"Authorization", b"Bearer SYNTH-FLOW-SECRET"],
                    [b"Content-Encoding", b"gzip"],
                    [b"Content-Type", b"application/json"],
                ],
                b"content": gzip_body,
                b"timestamp_start": 1764000000,
            },
            b"response": {b"status_code": 200},
        }
    )
    flow_path = tmp_path / "synthetic_capture.flow"
    flow_path.write_bytes(frame)

    out_dir = tmp_path / "captures"
    proc = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            str(flow_path),
            "--apk",
            str(apk_path),
            "--out-dir",
            str(out_dir),
            "--synthetic",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "com.nextbillion.groww" in proc.stdout
    assert "SYNTH-FLOW-SECRET" not in proc.stdout
    assert "SYNTHDEVICE999" not in proc.stdout

    summary_file = out_dir / "synthetic_capture_summary.json"
    report_file = out_dir / "synthetic_capture_report.md"
    assert summary_file.is_file() and report_file.is_file()

    combined = summary_file.read_text("utf-8") + report_file.read_text("utf-8")
    assert "SYNTH-FLOW-SECRET" not in combined
    assert "SYNTHDEVICE999" not in combined
    data = json.loads(summary_file.read_text("utf-8"))
    assert data["package_comparison"]["overlap_with_catalog_count"] == 1
