"""Headless workstation UI regression with synthetic, isolated stores and local axe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Any

from playwright.sync_api import expect, sync_playwright

from astrotrust.collector.server import make_server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/pilot/research-ui-check"))
    parser.add_argument("--browser-channel", default="msedge")
    parser.add_argument("--axe-script", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    evidence: dict[str, Any] = {}
    with TemporaryDirectory(prefix="synthetic-workstation-", dir=output) as temp:
        general, consumer = Path(temp) / "general.sqlite3", Path(temp) / "consumer.sqlite3"
        with make_server(
            Path(__file__).resolve().parents[1],
            general,
            0,
            consumer_database=consumer,
            start_consumer=True,
        ) as server:
            before = consumer.read_bytes()
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(
                        headless=True, channel=args.browser_channel
                    )
                    context = browser.new_context(reduced_motion="reduce")
                    page = context.new_page()
                    errors: list[str] = []
                    external: list[str] = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.on(
                        "request",
                        lambda r: (
                            external.append(r.url) if not r.url.startswith(server.url) else None
                        ),
                    )
                    for route in ("research", "local"):
                        page.goto(f"{server.url}/{route}")
                        page.wait_for_load_state("networkidle")
                        expect(
                            page.get_by_role("link", name="Research overview", exact=True)
                        ).to_be_visible()
                        expect(
                            page.get_by_role("link", name="Local models", exact=True)
                        ).to_be_visible()
                        assert not page.get_by_role("link", name="Survey", exact=True).count()
                        if route == "research":
                            expect(page.locator("#frontier-state")).to_have_text(
                                "Store unavailable"
                            )
                            expect(page.locator("#consumer-count")).to_have_text("0")
                            assert not general.exists() and server._collector is None
                        page.evaluate(args.axe_script.read_text("utf-8"))
                        for name, width, height in (("desktop", 1440, 900), ("mobile", 390, 844)):
                            page.set_viewport_size({"width": width, "height": height})
                            assert page.evaluate(
                                "document.documentElement.scrollWidth <= innerWidth"
                            )
                            violations = page.evaluate(
                                "async () => (await axe.run(document)).violations"
                            )
                            assert not violations, [(v["id"], v["impact"]) for v in violations]
                            page.screenshot(
                                path=str(output / f"{route}-{name}.png"),
                                full_page=True,
                                animations="disabled",
                                caret="hide",
                            )
                        evidence[route] = page.evaluate("""() => Object.fromEntries(
                          ['fontSize','fontFamily','borderRadius','boxShadow','color','padding']
                          .map(p => [p,[...new Set([...document.querySelectorAll('*')]
                          .map(e => getComputedStyle(e)[p]))]]))""")
                        page.locator("body").click(position={"x": 1, "y": 1})
                        for _ in range(15):
                            page.keyboard.press("Tab")
                            focused = page.evaluate("""() => {
                              const e=document.activeElement,s=getComputedStyle(e);
                              return {tag:e.tagName,outline:s.outlineStyle}; }""")
                            if focused["tag"] != "BODY":
                                assert focused["outline"] != "none", focused
                    page.goto(f"{server.url}/research")
                    expect(page.locator("#consumer-count")).to_have_text("0")
                    page.route("**/api/research/status", lambda r: r.fulfill(status=500, body="{}"))
                    page.get_by_role("button", name="Refresh evidence status").click()
                    expect(page.locator("#status-error")).to_be_visible()
                    expect(page.locator("#status-notice")).to_contain_text("may be stale")
                    expect(page.locator("#consumer-count")).to_have_text("0")
                    expect(
                        page.get_by_role("button", name="Refresh evidence status")
                    ).to_be_enabled()
                    page.unroute("**/api/research/status")
                    page.get_by_role("button", name="Refresh evidence status").click()
                    expect(page.locator("#status-error")).to_be_hidden()
                    assert consumer.read_bytes() == before and not general.exists()
                    assert not errors and not external, (errors, external)
                    context.close()
                    browser.close()
            finally:
                server.shutdown()
                thread.join()
    evidence.update(
        {
            "read_only_lazy_store": True,
            "axe_violations": [],
            "responsive_widths": [1440, 390],
            "keyboard_focus": True,
            "error_retry_preserves_counts": True,
            "external_requests": external,
            "page_errors": errors,
            "screen_reader": "Not tested with an actual assistive-technology client",
        }
    )
    (output / "ui-check.json").write_text(json.dumps(evidence, indent=2) + "\n", "utf-8")
    print("Research UI passed: read-only counts, two viewports, keyboard, axe and error recovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
