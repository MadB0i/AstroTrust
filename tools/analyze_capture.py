"""Analyze mitmproxy flow dumps or HAR captures from an isolated test device.

Performs four tasks cleanly offline:
1. Lists requests targeting hosts containing "astrotalk".
2. Identifies requests whose path contains "user/apps/installed" or
   "save/user-upi-apps".
3. Extracts package-name lists from request bodies and compares them against
   Astrotalk's `assets/apppackges.json` catalog (from APK or JSON file).
4. Redacts Authorization/id headers, bearer/JWT tokens, device IDs, and phone
   numbers before writing any JSON summary or Markdown report under
   `data/captures/`.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import importlib.util
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APK_PATH = Path(r"D:\ASTRO\Astrotalk.apk")
DEFAULT_OUT_DIR = ROOT / "data" / "captures"
TARGET_PATHS = ("user/apps/installed", "save/user-upi-apps")
REDACTED = "[REDACTED]"

_SENSITIVE_HEADER_KEYS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-auth-token",
        "x-access-token",
        "x-refresh-token",
        "x-api-key",
        "x-device-id",
        "device-id",
        "device_id",
        "deviceid",
        "hardware-id",
        "hardware_id",
        "hardwareid",
        "anonymous-id",
        "anonymous_id",
        "anonymousid",
        "fcm-id",
        "fcm_id",
        "fcmid",
        "android-id",
        "android_id",
        "advertising-id",
        "gaid",
        "idfa",
        "imei",
        "token",
        "session",
        "phone",
        "mobile",
        "msisdn",
        "id",
    }
)

_SENSITIVE_FIELD_SUBSTRINGS = (
    "authorization",
    "token",
    "bearer",
    "secret",
    "cookie",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "session",
    "device_id",
    "deviceid",
    "hardware_id",
    "hardwareid",
    "anonymous_id",
    "anonymousid",
    "fcm_id",
    "fcmid",
    "userwithoutloginid",
    "android_id",
    "androidid",
    "advertising_id",
    "appsflyer_id",
    "appsflyerid",
    "gaid",
    "idfa",
    "imei",
    "udid",
    "phone",
    "mobile",
    "msisdn",
    "otp",
)

_SENSITIVE_EXACT_FIELD_NAMES = frozenset({"id", "uid", "user_id", "userid", "ad_id", "uuid"})

_PKG_RE = re.compile(r"^[a-zA-Z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}\b")
_BEARER_RE = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9\-._~+/=]{6,}")
_IN_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[- ]?)?[6-9]\d{4}[- ]?\d{5}(?!\d)")
_INTL_PHONE_RE = re.compile(r"(?<!\w)\+\d{1,3}[- ]?\d{7,12}(?!\w)")
_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_HEX_TOKEN_RE = re.compile(r"\b[0-9a-fA-F]{24,}\b")


@dataclass(frozen=True)
class CapturedRequest:
    """Normalized HTTP request record extracted from HAR or mitmproxy dumps."""

    index: int
    method: str
    scheme: str
    host: str
    path: str
    url: str
    headers: tuple[tuple[str, str], ...]
    body_text: str
    mime_type: str
    status: int | None = None
    timestamp: str | None = None


def _is_sensitive_key(name: str, *, for_header: bool = False) -> bool:
    low = name.strip().lower()
    if for_header and low in _SENSITIVE_HEADER_KEYS:
        return True
    if low in _SENSITIVE_EXACT_FIELD_NAMES:
        return True
    return any(part in low for part in _SENSITIVE_FIELD_SUBSTRINGS)


def redact_text(value: str) -> str:
    """Scrub bearer/JWT tokens, UUIDs, long hex IDs, and phone numbers in text."""
    text = _BEARER_RE.sub(r"\1 [REDACTED]", value)
    text = _JWT_RE.sub(REDACTED, text)
    text = _UUID_RE.sub(REDACTED, text)
    text = _HEX_TOKEN_RE.sub(REDACTED, text)
    text = _IN_PHONE_RE.sub(REDACTED, text)
    text = _INTL_PHONE_RE.sub(REDACTED, text)
    return text


def redact_json_value(obj: Any, parent_key: str = "") -> Any:
    """Recursively redact sensitive keys and pattern-matched strings in JSON."""
    if isinstance(obj, dict):
        return {
            str(k): (
                REDACTED
                if _is_sensitive_key(str(k)) and v is not None
                else redact_json_value(v, str(k))
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_json_value(item, parent_key) for item in obj]
    if isinstance(obj, str):
        if parent_key and _is_sensitive_key(parent_key):
            return REDACTED
        return redact_text(obj)
    return obj


def redact_headers(headers: tuple[tuple[str, str], ...]) -> dict[str, str]:
    """Redact sensitive headers while retaining non-sensitive diagnostic headers."""
    cleaned: dict[str, str] = {}
    for k, v in headers:
        if _is_sensitive_key(k, for_header=True):
            cleaned[k] = REDACTED
        else:
            cleaned[k] = redact_text(v)
    return cleaned


def redact_url(raw_url: str) -> str:
    """Redact sensitive query parameter values and inline IDs in a URL."""
    parts = urlsplit(raw_url)
    if parts.query:
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        safe_pairs = [(k, REDACTED if _is_sensitive_key(k) else redact_text(v)) for k, v in pairs]
        query = urlencode(safe_pairs)
    else:
        query = ""
    safe_path = redact_text(parts.path)
    return urlunsplit((parts.scheme, parts.netloc, safe_path, query, ""))


def _parse_tnetstring(data: bytes, offset: int = 0) -> tuple[Any, int]:
    """Parse one mitmproxy tnetstring value starting at `offset`."""
    colon = data.find(b":", offset)
    if colon == -1:
        raise ValueError(f"Malformed tnetstring frame at byte {offset}")
    length = int(data[offset:colon])
    start = colon + 1
    end = start + length
    if end >= len(data):
        raise ValueError(f"Truncated tnetstring payload at byte {offset}")
    payload = data[start:end]
    tag = chr(data[end])
    next_off = end + 1

    if tag == ",":
        return payload, next_off
    if tag == ";":
        return payload.decode("utf-8", errors="replace"), next_off
    if tag == "#":
        return int(payload), next_off
    if tag == "^":
        return float(payload), next_off
    if tag == "!":
        return payload == b"true", next_off
    if tag == "~":
        return None, next_off
    if tag == "]":
        items: list[Any] = []
        pos = 0
        while pos < len(payload):
            val, pos = _parse_tnetstring(payload, pos)
            items.append(val)
        return items, next_off
    if tag == "}":
        mapping: dict[Any, Any] = {}
        pos = 0
        while pos < len(payload):
            k, pos = _parse_tnetstring(payload, pos)
            v, pos = _parse_tnetstring(payload, pos)
            key = k.decode("utf-8", "replace") if isinstance(k, bytes) else k
            mapping[key] = v
        return mapping, next_off
    raise ValueError(f"Unsupported tnetstring type tag {tag!r} at byte {end}")


def _decode_bytes(raw: bytes | str | None, *, gzip_hint: bool = False) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    buf = raw
    if gzip_hint or buf.startswith(b"\x1f\x8b"):
        try:
            buf = gzip.decompress(buf)
        except OSError:
            pass
    return buf.decode("utf-8", errors="replace")


def _extract_host_header(headers: tuple[tuple[str, str], ...]) -> str:
    for k, v in headers:
        if k.lower() == "host":
            return v.split(":", 1)[0]
    return ""


def _parse_mitm_tnetstring_stream(raw_bytes: bytes) -> list[CapturedRequest]:
    """Decode binary mitmproxy `.flow`/`.mitm` frames cleanly without mitmproxy."""
    requests: list[CapturedRequest] = []
    pos = 0
    idx = 0
    while pos < len(raw_bytes):
        frame, pos = _parse_tnetstring(raw_bytes, pos)
        if not isinstance(frame, dict) or frame.get("type") not in (b"http", "http"):
            continue
        req = frame.get("request")
        if not isinstance(req, dict):
            continue
        raw_headers = req.get("headers") or []
        headers: list[tuple[str, str]] = []
        mime = ""
        is_gzip = False
        for pair in raw_headers:
            if isinstance(pair, list | tuple) and len(pair) == 2:
                hk = _decode_bytes(pair[0])
                hv = _decode_bytes(pair[1])
                headers.append((hk, hv))
                if hk.lower() == "content-type":
                    mime = hv
                elif hk.lower() == "content-encoding" and "gzip" in hv.lower():
                    is_gzip = True

        scheme = _decode_bytes(req.get("scheme")) or "https"
        host = _decode_bytes(req.get("host")) or _decode_bytes(req.get("pretty_host"))
        if not host:
            host = _decode_bytes(req.get("authority")).split(":", 1)[0]
        if not host:
            host = _extract_host_header(tuple(headers))
        path_raw = _decode_bytes(req.get("path")) or "/"
        method = (_decode_bytes(req.get("method")) or "GET").upper()
        body_text = _decode_bytes(req.get("content"), gzip_hint=is_gzip)

        resp = frame.get("response")
        status: int | None = None
        if isinstance(resp, dict) and isinstance(resp.get("status_code"), int):
            status = int(resp["status_code"])

        ts_val = req.get("timestamp_start")
        ts_str = str(ts_val) if ts_val is not None else None
        full_url = f"{scheme}://{host}{path_raw}" if host else path_raw
        clean_path = urlsplit(full_url).path

        requests.append(
            CapturedRequest(
                index=idx,
                method=method,
                scheme=scheme,
                host=host.lower(),
                path=clean_path,
                url=full_url,
                headers=tuple(headers),
                body_text=body_text,
                mime_type=mime,
                status=status,
                timestamp=ts_str,
            )
        )
        idx += 1
    return requests


def _parse_with_mitmproxy_lib(path: Path) -> list[CapturedRequest]:
    """Use installed `mitmproxy.io.FlowReader` if available."""
    io_mod = importlib.import_module("mitmproxy.io")
    http_mod = importlib.import_module("mitmproxy.http")
    requests: list[CapturedRequest] = []
    with path.open("rb") as fh:
        reader = io_mod.FlowReader(fh)
        for idx, flow in enumerate(reader.stream()):
            if not isinstance(flow, http_mod.HTTPFlow):
                continue
            req = flow.request
            headers = tuple((str(k), str(v)) for k, v in req.headers.items(multi=True))
            mime = str(req.headers.get("content-type", ""))
            body = req.get_text(strict=False) or ""
            status = int(flow.response.status_code) if flow.response is not None else None
            requests.append(
                CapturedRequest(
                    index=idx,
                    method=str(req.method).upper(),
                    scheme=str(req.scheme),
                    host=str(req.pretty_host).lower(),
                    path=urlsplit(str(req.url)).path,
                    url=str(req.url),
                    headers=headers,
                    body_text=body,
                    mime_type=mime,
                    status=status,
                    timestamp=str(getattr(req, "timestamp_start", "") or "") or None,
                )
            )
    return requests


def _decode_har_post_data(post_data: dict[str, Any]) -> tuple[str, str]:
    text = str(post_data.get("text") or "")
    mime = str(post_data.get("mimeType") or "")
    encoding = str(post_data.get("encoding") or "").lower()
    if encoding == "base64" and text:
        try:
            raw = base64.b64decode(text)
            return _decode_bytes(raw), mime
        except ValueError:
            return text, mime
    if not text and isinstance(post_data.get("params"), list):
        pairs = [
            (str(p.get("name", "")), str(p.get("value", "")))
            for p in post_data["params"]
            if isinstance(p, dict)
        ]
        return urlencode(pairs), mime or "application/x-www-form-urlencoded"
    return text, mime


def _parse_har(raw_text: str) -> list[CapturedRequest]:
    payload = json.loads(raw_text)
    entries = payload.get("log", {}).get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("HAR JSON missing log.entries list")

    requests: list[CapturedRequest] = []
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        req = entry.get("request", {})
        if not isinstance(req, dict):
            continue
        raw_url = str(req.get("url") or "")
        parts = urlsplit(raw_url)
        headers = tuple(
            (str(h.get("name", "")), str(h.get("value", "")))
            for h in req.get("headers", [])
            if isinstance(h, dict)
        )
        host = (parts.hostname or _extract_host_header(headers)).lower()
        post_data = req.get("postData") or {}
        body_text, mime = (
            _decode_har_post_data(post_data) if isinstance(post_data, dict) else ("", "")
        )
        resp = entry.get("response") or {}
        status = int(resp["status"]) if isinstance(resp, dict) and "status" in resp else None
        requests.append(
            CapturedRequest(
                index=idx,
                method=str(req.get("method") or "GET").upper(),
                scheme=parts.scheme or "https",
                host=host,
                path=parts.path,
                url=raw_url,
                headers=headers,
                body_text=body_text,
                mime_type=mime,
                status=status,
                timestamp=str(entry.get("startedDateTime") or "") or None,
            )
        )
    return requests


def load_capture(path: Path) -> list[CapturedRequest]:
    """Load HTTP requests from either a HAR JSON file or mitmproxy flow dump."""
    if not path.is_file():
        raise FileNotFoundError(f"Capture file not found: {path}")
    raw = path.read_bytes()
    if not raw.strip():
        return []

    stripped = raw.lstrip()
    if stripped.startswith(b"{"):
        return _parse_har(raw.decode("utf-8"))

    if (
        importlib.util.find_spec("mitmproxy") is not None
        and importlib.util.find_spec("mitmproxy.io") is not None
    ):
        return _parse_with_mitmproxy_lib(path)
    return _parse_mitm_tnetstring_stream(raw)


def load_target_catalog(
    catalog_path: Path | None = None,
    apk_path: Path | None = DEFAULT_APK_PATH,
) -> tuple[dict[str, str], str]:
    """Load `{package_name: app_name}` from a JSON file or Astrotalk APK asset."""
    if catalog_path is not None:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        return _normalize_catalog(raw), str(catalog_path)
    if apk_path is not None and apk_path.is_file():
        with zipfile.ZipFile(apk_path) as zf:
            if "assets/apppackges.json" in zf.namelist():
                raw = json.loads(zf.read("assets/apppackges.json").decode("utf-8"))
                return _normalize_catalog(raw), f"{apk_path}!assets/apppackges.json"
    return {}, "unavailable"


def _normalize_catalog(raw: object) -> dict[str, str]:
    if not isinstance(raw, list):
        raise ValueError("Target package catalog must be a JSON list")
    catalog: dict[str, str] = {}
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("package_name"), str):
            catalog[item["package_name"]] = str(item.get("name") or item["package_name"])
        elif isinstance(item, str) and _PKG_RE.match(item):
            catalog[item] = item
    return catalog


def _collect_packages_from_obj(obj: Any, found: list[str]) -> None:
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, str) and _PKG_RE.match(item.strip()):
                found.append(item.strip())
            else:
                _collect_packages_from_obj(item, found)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            is_pkg_field = (
                "package" in kl
                or "pkg" in kl
                or kl in ("appid", "app_id", "bundle_id", "identifier")
            ) and "device" not in kl
            if is_pkg_field and isinstance(v, str) and _PKG_RE.match(v.strip()):
                found.append(v.strip())
            elif isinstance(v, dict | list):
                _collect_packages_from_obj(v, found)


def extract_package_names(body_text: str, mime_type: str = "") -> list[str]:
    """Extract ordered Android package names from JSON or form request bodies."""
    text = body_text.strip()
    if not text:
        return []

    found: list[str] = []
    if text.startswith(("{", "[")) or "json" in mime_type.lower():
        try:
            parsed = json.loads(text)
            _collect_packages_from_obj(parsed, found)
            if found:
                return list(dict.fromkeys(found))
        except json.JSONDecodeError:
            pass

    if "x-www-form-urlencoded" in mime_type.lower() or ("=" in text and not text.startswith("{")):
        for key, val in parse_qsl(text, keep_blank_values=False):
            if "package" in key.lower() or "app" in key.lower():
                stripped = val.strip()
                if stripped.startswith(("[", "{")):
                    try:
                        _collect_packages_from_obj(json.loads(stripped), found)
                        continue
                    except json.JSONDecodeError:
                        pass
                for part in stripped.split(","):
                    cand = part.strip()
                    if _PKG_RE.match(cand):
                        found.append(cand)
        if found:
            return list(dict.fromkeys(found))

    return []


def _summarize_body_redacted(body_text: str, mime_type: str) -> Any:
    text = body_text.strip()
    if not text:
        return None
    if text.startswith(("{", "[")) or "json" in mime_type.lower():
        try:
            return redact_json_value(json.loads(text))
        except json.JSONDecodeError:
            pass
    if "x-www-form-urlencoded" in mime_type.lower():
        pairs = [
            [k, REDACTED if _is_sensitive_key(k) else redact_text(v)]
            for k, v in parse_qsl(text, keep_blank_values=True)
        ]
        return pairs
    return redact_text(text[:500])


def analyze_capture(
    capture_path: Path,
    *,
    catalog_path: Path | None = None,
    apk_path: Path | None = DEFAULT_APK_PATH,
    is_synthetic: bool = False,
) -> dict[str, Any]:
    """Inspect all HTTP requests and compile a redacted analysis dictionary."""
    requests = load_capture(capture_path)
    catalog, catalog_source = load_target_catalog(catalog_path, apk_path)
    catalog_set = set(catalog)

    astrotalk_requests: list[dict[str, Any]] = []
    tracker_requests: list[dict[str, Any]] = []
    all_sent_ordered: list[str] = []

    for req in requests:
        is_astrotalk_host = "astrotalk" in req.host.lower()
        low_target = f"{req.path} {req.url}".lower()
        matched_routes = [route for route in TARGET_PATHS if route in low_target]
        is_tracker_route = bool(matched_routes)

        base_entry = {
            "index": req.index,
            "method": req.method,
            "host": req.host,
            "path": req.path,
            "url": redact_url(req.url),
            "status": req.status,
            "timestamp": req.timestamp,
            "headers": redact_headers(req.headers),
        }

        if is_astrotalk_host:
            astrotalk_requests.append(base_entry)

        if is_tracker_route:
            sent = extract_package_names(req.body_text, req.mime_type)
            all_sent_ordered.extend(sent)
            sent_set = set(sent)
            overlap = sorted(sent_set & catalog_set) if catalog_set else []
            not_in_catalog = sorted(sent_set - catalog_set) if catalog_set else list(sent)
            tracker_requests.append(
                {
                    **base_entry,
                    "matched_targets": matched_routes,
                    "sent_package_count": len(sent),
                    "overlap_with_apppackges_count": len(overlap) if catalog_set else None,
                    "sent_packages": sent,
                    "overlap_packages": overlap,
                    "non_catalog_packages": not_in_catalog,
                    "redacted_body_preview": _summarize_body_redacted(req.body_text, req.mime_type),
                }
            )

    unique_sent = list(dict.fromkeys(all_sent_ordered))
    unique_sent_set = set(unique_sent)
    overlap_all = sorted(unique_sent_set & catalog_set) if catalog_set else []
    non_catalog_all = sorted(unique_sent_set - catalog_set) if catalog_set else list(unique_sent)

    return {
        "capture_file": capture_path.name,
        "provenance": "SYNTHETIC_FIXTURE" if is_synthetic else "DEVICE_TEST_CAPTURE",
        "redacted": True,
        "total_requests_parsed": len(requests),
        "astrotalk_host_request_count": len(astrotalk_requests),
        "astrotalk_host_requests": astrotalk_requests,
        "tracker_endpoint_match_count": len(tracker_requests),
        "tracker_endpoint_requests": tracker_requests,
        "catalog_source": catalog_source,
        "catalog_package_count": len(catalog_set),
        "package_comparison": {
            "total_unique_packages_sent": len(unique_sent),
            "overlap_with_catalog_count": len(overlap_all) if catalog_set else None,
            "overlap_pct_of_sent": (
                round(100.0 * len(overlap_all) / len(unique_sent), 2)
                if catalog_set and unique_sent
                else 0.0
            ),
            "overlap_pct_of_catalog": (
                round(100.0 * len(overlap_all) / len(catalog_set), 2) if catalog_set else None
            ),
            "sent_packages": unique_sent,
            "overlap_packages": overlap_all,
            "non_catalog_packages": non_catalog_all,
        },
    }


def render_markdown_report(summary: dict[str, Any]) -> str:
    """Format a concise redacted Markdown summary report."""
    comp = summary["package_comparison"]
    lines = [
        f"# Capture Analysis Report: `{summary['capture_file']}`",
        "",
        f"- **Provenance:** `{summary['provenance']}`",
        f"- **Redaction Applied:** `{summary['redacted']}` (headers, tokens, device IDs, phones)",
        f"- **Total Parsed Requests:** {summary['total_requests_parsed']}",
        f"- **Requests to Hosts Containing `astrotalk`:** "
        f"{summary['astrotalk_host_request_count']}",
        "- **Matched Tracker Endpoints (`user/apps/installed` or `save/user-upi-apps`):** "
        f"{summary['tracker_endpoint_match_count']}",
        f"- **Target Catalog (`assets/apppackges.json`):** "
        f"{summary['catalog_package_count']} packages (`{summary['catalog_source']}`)",
        "",
        "## 1. Requests to `astrotalk` Hosts",
        "",
    ]
    if summary["astrotalk_host_requests"]:
        lines.extend(
            [
                "| # | Method | Host | Path | Status |",
                "| ---: | :--- | :--- | :--- | ---: |",
            ]
        )
        for req in summary["astrotalk_host_requests"]:
            st = str(req["status"]) if req["status"] is not None else "-"
            lines.append(
                f"| {req['index']} | `{req['method']}` | `{req['host']}` | `{req['path']}` | {st} |"
            )
    else:
        lines.append("No requests targeting hosts containing `astrotalk` were found.")

    lines.extend(["", "## 2. Tracker Endpoint Package Comparison", ""])
    lines.append(f"- **Unique Packages Sent:** {comp['total_unique_packages_sent']}")
    if summary["catalog_package_count"]:
        lines.append(
            f"- **Overlap with `assets/apppackges.json`:** "
            f"{comp['overlap_with_catalog_count']} "
            f"({comp['overlap_pct_of_sent']}% of sent; "
            f"{comp['overlap_pct_of_catalog']}% of catalog)"
        )
    else:
        lines.append("- **Overlap with `assets/apppackges.json`:** Catalog unavailable")

    if comp["sent_packages"]:
        lines.extend(["", "### Sent Package Names", ""])
        for pkg in comp["sent_packages"]:
            tag = "in `apppackges.json`" if pkg in comp["overlap_packages"] else "not in catalog"
            lines.append(f"- `{pkg}` ({tag})")
    else:
        lines.append("\nNo package-name payloads were observed in matched endpoints.")

    return "\n".join(lines) + "\n"


def write_capture_outputs(
    summary: dict[str, Any],
    out_dir: Path = DEFAULT_OUT_DIR,
    stem: str | None = None,
) -> tuple[Path, Path]:
    """Write redacted JSON summary and Markdown report under `data/captures/`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base_stem = stem or Path(str(summary["capture_file"])).stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", base_stem).strip("_") or "capture"
    json_path = out_dir / f"{safe_stem}_summary.json"
    md_path = out_dir / f"{safe_stem}_report.md"
    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown_report(summary), encoding="utf-8")
    return json_path, md_path


def _print_console_summary(summary: dict[str, Any], json_path: Path, md_path: Path) -> None:
    print(f"Capture: {summary['capture_file']} ({summary['provenance']})")
    print(f"Astrotalk-host requests: {summary['astrotalk_host_request_count']}")
    for req in summary["astrotalk_host_requests"]:
        print(f"  - [{req['method']}] {req['host']}{req['path']} (status={req['status']})")
    print(f"Tracker-endpoint matches: {summary['tracker_endpoint_match_count']}")
    comp = summary["package_comparison"]
    print(
        f"Packages sent: {comp['total_unique_packages_sent']} | "
        f"Catalog ({summary['catalog_package_count']}): "
        f"overlap={comp['overlap_with_catalog_count']}"
    )
    for pkg in comp["sent_packages"]:
        status_note = (
            "overlap: in apppackges.json"
            if pkg in comp["overlap_packages"]
            else "not in apppackges.json"
        )
        print(f"  - {pkg} ({status_note})")
    print(f"Wrote redacted JSON -> {json_path}")
    print(f"Wrote redacted Markdown -> {md_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="Path to mitmproxy flow dump or HAR file")
    parser.add_argument(
        "--apppackges",
        type=Path,
        default=None,
        help="Optional path to extracted assets/apppackges.json",
    )
    parser.add_argument(
        "--apk",
        type=Path,
        default=DEFAULT_APK_PATH,
        help=(
            "Optional APK path containing assets/apppackges.json "
            "(default: D:\\ASTRO\\Astrotalk.apk)"
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for redacted JSON & Markdown reports (default: data/captures/)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Mark report metadata explicitly as SYNTHETIC_FIXTURE",
    )
    args = parser.parse_args(argv)

    summary = analyze_capture(
        args.capture,
        catalog_path=args.apppackges,
        apk_path=args.apk,
        is_synthetic=bool(args.synthetic),
    )
    json_path, md_path = write_capture_outputs(summary, out_dir=args.out_dir)
    _print_console_summary(summary, json_path, md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
