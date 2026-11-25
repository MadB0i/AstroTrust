"""Loopback-only stdlib HTTP server; bundled assets, no telemetry or remote requests."""

from __future__ import annotations

import hmac
import json
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from threading import Lock
from typing import cast
from urllib.parse import parse_qs, urlsplit

from pydantic import ValidationError

from astrotrust.annotations.models import condition_id
from astrotrust.benchmark.models import Condition
from astrotrust.benchmark.prompts import digest
from astrotrust.collector import COLLECTOR_VERSION, INSTRUMENT_VERSION, consumer_exports
from astrotrust.collector.consumer_models import (
    PERSONAL_FIELDS,
    PROMPTS,
    REGISTRY_VERSION,
    ConsumerCorrection,
    ConsumerRequest,
)
from astrotrust.collector.consumer_profiles import PROFILE_FIELDS, PROFILES, profile_digest
from astrotrust.collector.consumer_service import ConsumerCollector
from astrotrust.collector.consumer_service import summary as consumer_summary
from astrotrust.collector.consumer_store import DEFAULT_CONSUMER_DATABASE, ConsumerStore
from astrotrust.collector.exports import ExportFormat, export, parse_json, single_report
from astrotrust.collector.models import CaptureRequest, CorrectionRequest, ManualRun
from astrotrust.collector.service import Collector, progress
from astrotrust.collector.store import DEFAULT_DATABASE, DuplicateCapture, RunStore
from astrotrust.research.inventory import research_status

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
    def __init__(
        self,
        collector: Collector | None,
        port: int,
        *,
        consumer: ConsumerCollector | None = None,
        general_target: tuple[Path, Path] | None = None,
    ) -> None:
        if not 0 <= port <= 65535:
            raise ValueError("Port must be between 0 and 65535 (0 chooses a free local port)")
        self._collector = collector
        self._collector_lock = Lock()
        self.consumer = consumer
        self.general_target = general_target
        self.token = secrets.token_urlsafe(32)
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def collector(self) -> Collector:
        # Consumer-only startup never opens the general-purpose store. It is opened
        # only when the researcher explicitly navigates to a general API operation.
        with self._collector_lock:
            if self._collector is None:
                if self.general_target is None:
                    raise ValueError("General-purpose collector is unavailable")
                root, database = self.general_target
                self._collector = Collector(root, RunStore(database))
            return self._collector

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
        if path == "/favicon.ico":
            self._reply(204, "", "image/x-icon")
        elif path in {
            "/",
            "/consumer",
            "/research",
            "/local",
            "/collector.css",
            "/collector.js",
            "/consumer.js",
            "/research.js",
        }:
            name = {
                "/": "index.html",
                "/consumer": "consumer.html",
                "/research": "research.html",
                "/local": "local.html",
            }.get(path, path[1:])
            content = files("astrotrust.collector").joinpath("static", name).read_text("utf-8")
            content = (
                content.replace("__SESSION_TOKEN__", self.local.token)
                if path in {"/", "/consumer", "/research", "/local"}
                else content
            )
            types = {
                "/": "text/html",
                "/collector.css": "text/css",
                "/collector.js": "text/javascript",
                "/consumer": "text/html",
                "/consumer.js": "text/javascript",
                "/research": "text/html",
                "/local": "text/html",
                "/research.js": "text/javascript",
            }
            self._reply(200, content, types[path])
        elif path == "/api/research/status":
            # Do not instantiate the lazy frontier collector or create a missing store.
            general = (
                self.local.general_target[1]
                if self.local.general_target
                else self.local._collector.store.path
                if self.local._collector
                else None
            )
            consumer = self.local.consumer
            if general is None or consumer is None:
                raise ValueError("Research targets unavailable")
            self._json(research_status(general, consumer.store.path))
        elif path.startswith("/api/consumer/"):
            consumer = self.local.consumer
            if consumer is None:
                raise ValueError("Consumer collector is unavailable")
            if path == "/api/consumer/bootstrap":
                self._json(
                    {
                        "schema_version": "consumer-1.1",
                        "registry_version": REGISTRY_VERSION,
                        "personal_field_names": PERSONAL_FIELDS,
                        "profile_field_names": PROFILE_FIELDS,
                        "profiles": [
                            {"snapshot": p.model_dump(mode="json"), "sha256": profile_digest(p)}
                            for p in PROFILES.values()
                        ],
                        "prompts": [
                            {"id": key, "text": value, "sha256": digest(value)}
                            for key, value in PROMPTS.items()
                        ],
                        "runs": [consumer_summary(r) for r in consumer.store.all()],
                    }
                )
            elif path == "/api/consumer/run":
                self._json(consumer.store.get(q.get("id", "")).model_dump(mode="json"))
            elif path == "/api/consumer/export":
                format = q.get("format", "")
                if format == "single":
                    content = consumer_exports.single_report(consumer.store.get(q.get("id", "")))
                elif format in {"jsonl", "csv", "markdown"}:
                    runs = consumer.store.all()
                    if not runs:
                        self._json({"error": "Save a consumer capture before exporting."}, 400)
                        return
                    content = consumer_exports.export(runs, cast(ExportFormat, format))
                else:
                    raise ValueError("Unknown consumer export format")
                self._reply(200, content, "text/plain")
            else:
                self._json({"error": "Consumer operation not found"}, 404)
        else:
            self._general_get(path, q)

    def _general_get(self, path: str, q: dict[str, str]) -> None:
        if path not in {
            "/api/bootstrap",
            "/api/prompt",
            "/api/progress",
            "/api/run",
            "/api/export",
        }:
            self._json({"error": "Local page not found"}, 404)
            return
        c = self.local.collector
        if path == "/api/bootstrap":
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
            if path.startswith("/api/consumer/"):
                consumer = self.local.consumer
                if consumer is None:
                    raise ValueError("Consumer collector is unavailable")
                if path == "/api/consumer/runs":
                    consumer_run = consumer.save(ConsumerRequest.model_validate(parse_json(body)))
                elif path == "/api/consumer/correction":
                    correction = ConsumerCorrection.model_validate(parse_json(body))
                    consumer_run = consumer.store.correct(
                        q.get("id", ""),
                        correction.metadata,
                        correction.reason,
                        correction.expected_revision,
                    )
                else:
                    self._json({"error": "Unknown consumer save operation"}, 404)
                    return
                self._json(
                    {
                        "run": consumer_run.model_dump(mode="json"),
                        "runs": [consumer_summary(r) for r in consumer.store.all()],
                    },
                    201,
                )
                return
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


def make_server(
    root: Path,
    database: Path,
    port: int = 8765,
    *,
    consumer_database: Path | None = None,
    start_consumer: bool = False,
) -> CollectorServer:
    consumer_database = consumer_database or database.parent / "consumer-app-runs/collector.sqlite3"
    if database.resolve() == consumer_database.resolve():
        raise ValueError("Consumer and general-purpose databases must be separate")
    consumer = ConsumerCollector(root, ConsumerStore(consumer_database))
    collector = None if start_consumer else Collector(root, RunStore(database))
    return CollectorServer(collector, port, consumer=consumer, general_target=(root, database))


def serve(root: Path, database: Path, port: int, *, consumer_mode: bool = False) -> None:
    general_database = root / DEFAULT_DATABASE if consumer_mode else database
    consumer_database = database if consumer_mode else root / DEFAULT_CONSUMER_DATABASE
    with make_server(
        root,
        general_database,
        port,
        consumer_database=consumer_database,
        start_consumer=consumer_mode,
    ) as server:
        print(
            f"AstroTrust Manual Collector: {server.url}" + ("/consumer" if consumer_mode else ""),
            flush=True,
        )
        print(f"General store: {general_database.resolve()}", flush=True)
        print(f"Consumer store: {consumer_database.resolve()}\nStop with Ctrl+C.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
