"""Loopback-only stdlib HTTP server; bundled assets, no telemetry or remote requests."""

from __future__ import annotations

import hmac
import json
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlsplit

from pydantic import ValidationError

from astrotrust.annotations.models import condition_id
from astrotrust.benchmark.models import Condition
from astrotrust.benchmark.prompts import digest
from astrotrust.collector import COLLECTOR_VERSION, INSTRUMENT_VERSION
from astrotrust.collector.exports import ExportFormat, export, parse_json, single_report
from astrotrust.collector.models import CaptureRequest, CorrectionRequest, ManualRun
from astrotrust.collector.service import Collector, progress
from astrotrust.collector.store import DuplicateCapture, RunStore

MAX_BODY = 16 * 1024 * 1024


def summary(run: ManualRun) -> dict[str, object]:
    m = run.metadata
    return {
        "run_id": run.run_id,
        "scenario_id": run.canonical_prompt.scenario_id,
        "condition_id": run.condition_id,
        "provider": m.provider,
        "product": m.product,
        "model_label": m.model_label,
        "run_number": m.run_number,
        "timestamp": m.timestamp,
        "response_length": len(run.raw_response),
        "capture_status": f"Complete: {m.response_complete}; truncated: {m.visibly_truncated}",
    }


class CollectorServer(ThreadingHTTPServer):
    def __init__(self, collector: Collector, port: int) -> None:
        if not 0 <= port <= 65535:
            raise ValueError("Port must be between 0 and 65535 (0 chooses a free local port)")
        self.collector = collector
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_port}"


class Handler(BaseHTTPRequestHandler):
    @property
    def local(self) -> CollectorServer:
        return cast(CollectorServer, self.server)

    def log_message(self, format: str, *args: object) -> None:
        pass  # No URLs, raw records or request body in logs.

    def _reply(self, status: int, content: str, content_type: str = "application/json") -> None:
        raw = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; "
            "style-src 'self'; connect-src 'self'; img-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(raw)

    def _json(self, value: object, status: int = 200) -> None:
        self._reply(status, json.dumps(value, ensure_ascii=False, allow_nan=False))

    def _authorized(self, api: bool) -> bool:
        allowed = {self.local.url, f"http://localhost:{self.local.server_port}"}
        origin = self.headers.get("Origin")
        host = self.headers.get("Host")
        if f"http://{host}" not in allowed or (origin and origin not in allowed):
            self._json({"error": "Use the collector's printed local URL."}, 403)
            return False
        if api and not hmac.compare_digest(
            self.headers.get("X-Collector-Token", "").encode("utf-8"),
            self.local.token.encode("ascii"),
        ):
            self._json({"error": "Collector session expired. Reload the local page."}, 403)
            return False
        return True

    def _query(self) -> tuple[str, dict[str, str]]:
        parsed = urlsplit(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        if any(len(values) != 1 for values in query.values()):
            raise ValueError("Duplicate query parameter")
        return parsed.path, {key: values[0] for key, values in query.items()}

    @staticmethod
    def _condition(query: dict[str, str]) -> Condition:
        return Condition.model_validate(
            {
                k: query[k]
                for k in ("belief", "emotion", "personalization", "language")
                if k in query
            }
        )

    def do_GET(self) -> None:
        if not self._authorized(self.path.startswith("/api/")):
            return
        try:
            self._get()
        except (ValueError, OSError, sqlite3.Error):
            self._json(
                {
                    "error": "Cannot read this target or local store. Check the selection "
                    "and directory permissions, then retry."
                },
                400,
            )

    def _get(self) -> None:
        path, q = self._query()
        c = self.local.collector
        if path == "/favicon.ico":
            self._reply(204, "", "image/x-icon")
        elif path in {"/", "/collector.css", "/collector.js"}:
            name = "index.html" if path == "/" else path[1:]
            content = files("astrotrust.collector").joinpath("static", name).read_text("utf-8")
            content = (
                content.replace("__SESSION_TOKEN__", self.local.token) if path == "/" else content
            )
            types = {
                "/": "text/html",
                "/collector.css": "text/css",
                "/collector.js": "text/javascript",
            }
            self._reply(200, content, types[path])
        elif path == "/api/bootstrap":
            self._json(
                {
                    "scenarios": [
                        {
                            "id": s.scenario_id,
                            "title": s.title,
                            "domain": s.domain,
                            "revision": s.revision,
                            "languages": list(s.language_variants),
                        }
                        for s in c.scenarios
                    ],
                    "collector_version": COLLECTOR_VERSION,
                    "instrument_version": INSTRUMENT_VERSION,
                    "schema_version": "manual-1.0",
                    "runs": [summary(r) for r in c.store.all()],
                }
            )
        elif path == "/api/prompt":
            prompt = c.prompt(q.get("scenario", ""), self._condition(q))
            self._json(
                {
                    "prompt": prompt.model_dump(mode="json"),
                    "condition_id": condition_id(prompt.condition),
                    "text": prompt.messages[0].content,
                    "sha256": digest(prompt.messages[0].content),
                }
            )
        elif path == "/api/progress":
            condition = self._condition(q)
            scenario_id = q.get("scenario", "")
            source = c.prompt(scenario_id, condition)
            self._json(
                progress(
                    c.store.all(), scenario_id, condition, scenario_sha256=source.scenario_sha256
                )
            )
        elif path == "/api/run":
            self._json(c.store.get(q.get("id", "")).model_dump(mode="json"))
        elif path == "/api/export":
            format = q.get("format", "")
            if format not in {"jsonl", "csv", "markdown", "single"}:
                raise ValueError("Unknown export format")
            if format == "single":
                content = single_report(c.store.get(q.get("id", "")))
            else:
                runs = c.store.all()
                if not runs:
                    self._json(
                        {"error": "No captures saved yet. Save a raw run before exporting."}, 400
                    )
                    return
                content = export(runs, cast(ExportFormat, format))
            self._reply(200, content, "text/plain")
        else:
            self._json({"error": "Local page not found"}, 404)

    def do_POST(self) -> None:
        if not self._authorized(True):
            return
        try:
            if self.headers.get("Content-Type") != "application/json":
                raise ValueError("Send application/json")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                self._json(
                    {
                        "error": "Capture exceeds the 16 MiB request limit; preserve it "
                        "externally and document this anomaly."
                    },
                    413,
                )
                return
            body = self.rfile.read(length).decode("utf-8")
            path, q = self._query()
            c = self.local.collector
            if path == "/api/runs":
                run = c.save(CaptureRequest.model_validate(parse_json(body)))
            elif path == "/api/correction":
                request = CorrectionRequest.model_validate(parse_json(body))
                run = c.store.correct(
                    q.get("id", ""), request.metadata, request.reason, request.expected_revision
                )
            else:
                self._json({"error": "Unknown save operation"}, 404)
                return
            self._json(
                {"run": run.model_dump(mode="json"), "runs": [summary(r) for r in c.store.all()]},
                201,
            )
        except ValidationError as exc:
            fields = [".".join(map(str, e["loc"])) or "record" for e in exc.errors()]
            self._json(
                {
                    "error": "Check required fields and allowed values: " + ", ".join(fields),
                    "fields": fields,
                },
                400,
            )
        except DuplicateCapture as exc:
            self._json({"error": str(exc)}, 409)
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)
        except (OSError, sqlite3.Error):
            self._json(
                {
                    "error": "Save failed. Your input is still on screen. Check disk space "
                    "and directory permissions, then retry."
                },
                500,
            )


def make_server(root: Path, database: Path, port: int = 8765) -> CollectorServer:
    return CollectorServer(Collector(root, RunStore(database)), port)


def serve(root: Path, database: Path, port: int) -> None:
    with make_server(root, database, port) as server:
        print(f"AstroTrust Manual Collector: {server.url}", flush=True)
        print(f"Local store: {database.resolve()}\nExploratory only. Stop with Ctrl+C.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
