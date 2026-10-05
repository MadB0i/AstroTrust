"""Headless local UI check with a temporary synthetic store, never a research database.

Install the optional ui dependencies and a Chromium browser first. Provide an already
installed local axe-core script: this tool makes no external requests. Screenshots and
the check report are written to --output; synthetic SQLite/download files are removed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from astrotrust.benchmark.prompts import digest
from astrotrust.collector.exports import load_csv, load_jsonl
from astrotrust.collector.server import make_server

RAW = (
    "  [Synthetic development response — not model output]\n\n"
    "## শিৰোনাম / शीर्षक\n- `sentinel`\n<script>window.UNSAFE=true</script>\n \n"
)


def fill_capture(page: Page) -> None:
    page.get_by_label("Model label shown in UI", exact=False).fill("  Synthetic UI label / v?  ")
    page.get_by_role("combobox", name="New conversation used", exact=True).select_option("yes")
    page.get_by_role(
        "combobox", name="Asked for additional information instead of answering?", exact=True
    ).select_option("no")
    page.get_by_role("combobox", name="Refused or avoided the request?", exact=True).select_option(
        "no"
    )
    page.get_by_label("Paste complete model response", exact=False).fill(RAW)


def check(page: Page, url: str, output: Path, downloads: Path, axe: Path) -> dict[str, object]:
    page.set_default_timeout(8000)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console", lambda message: errors.append(message.text) if message.type == "error" else None
    )
    external: list[str] = []
    page.on(
        "request",
        lambda request: external.append(request.url) if not request.url.startswith(url) else None,
    )
    page.goto(url)
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("button", name="Copy Prompt", exact=True)).to_be_enabled()
    expect(page.locator("#saved-count")).to_have_text("0")
    expect(page.locator("#matrix-count")).to_have_text("0")
    assert page.locator("#progress td").count() == 27
    assert page.locator('#language option[value="hi"]').evaluate("e => e.disabled")
    assert page.locator('#language option[value="as"]').evaluate("e => e.disabled")
    styles = page.evaluate(
        """() => Object.fromEntries(
          ['fontSize','fontFamily','borderRadius','boxShadow','color'].map(p => [p,
            [...new Set([...document.querySelectorAll('*')].map(e => getComputedStyle(e)[p]))]
          ]))"""
    )
    for name, width, height in (
        ("desktop", 1440, 1000),
        ("tablet", 768, 1024),
        ("mobile", 390, 844),
    ):
        page.set_viewport_size({"width": width, "height": height})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            f"{name}: page overflow"
        )
        page.screenshot(
            path=str(output / f"collector-{name}.png"),
            full_page=True,
            animations="disabled",
            caret="hide",
        )
        page.screenshot(
            path=str(output / f"collector-{name}-viewport.png"), animations="disabled", caret="hide"
        )
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.evaluate(axe.read_text("utf-8"))
    accessibility: dict[str, Any] = page.evaluate("async () => await axe.run(document)")
    assert not accessibility["violations"], [
        (v["id"], v["impact"]) for v in accessibility["violations"]
    ]
    page.set_viewport_size({"width": 390, "height": 844})
    assert not page.evaluate("async () => (await axe.run(document)).violations")
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.locator("body").click(position={"x": 1, "y": 1})
    keyboard: list[dict[str, object]] = []
    for _ in range(35):
        page.keyboard.press("Tab")
        item: dict[str, object] = page.evaluate(
            """() => {const e=document.activeElement,s=getComputedStyle(e);
              return {tag:e.tagName,id:e.id,outline:s.outlineStyle,width:s.outlineWidth};}"""
        )
        keyboard.append(item)
        assert item["outline"] != "none", item
    canonical = page.get_by_label("Exact canonical prompt").input_value()
    page.get_by_role("button", name="Copy Prompt", exact=True).click()
    expect(page.locator("#notice")).to_contain_text("Exact canonical prompt copied")
    copied = page.evaluate("navigator.clipboard.readText()")
    # Windows clipboard converts LF to CRLF; only this documented platform change is allowed.
    assert copied.replace("\r\n", "\n") == canonical
    page.get_by_role("button", name="Save Raw Run", exact=True).click()
    expect(page.locator("#model_label")).to_have_attribute("aria-invalid", "true")
    fill_capture(page)
    page.get_by_role("combobox", name="Belief condition", exact=True).select_option(
        "positive_expectation"
    )
    expect(page.get_by_role("dialog", name="Discard unsaved capture?")).to_be_visible()
    page.get_by_role("button", name="Keep collecting this target").click()
    assert page.locator("#raw_response").input_value() == RAW
    assert page.locator("#belief").input_value() == "neutral"
    page.get_by_role("combobox", name="Belief condition", exact=True).select_option(
        "positive_expectation"
    )
    page.get_by_role("button", name="Discard and change target").click()
    expect(page.locator("#save")).to_be_enabled()
    assert page.locator("#raw_response").input_value() == ""
    page.get_by_role("combobox", name="Belief condition", exact=True).select_option("neutral")
    expect(page.locator("#condition-id")).to_contain_text("belief-neutral")
    fill_capture(page)
    page.route(
        "**/api/runs",
        lambda route: route.fulfill(
            status=500, json={"error": "Synthetic disk failure; retry after checking storage."}
        ),
    )
    page.get_by_role("button", name="Save Raw Run", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("Synthetic disk failure")
    assert page.locator("#raw_response").input_value() == RAW
    page.unroute("**/api/runs")
    page.get_by_role("button", name="Save Raw Run", exact=True).click()
    expect(page.locator("#saved-count")).to_have_text("1")
    expect(page.locator("#matrix-count")).to_have_text("1")
    assert page.evaluate("window.UNSAFE") is None
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.locator("#saved-count")).to_have_text("1")
    page.get_by_role("button", name="manual-", exact=False).click()
    expect(page.get_by_role("dialog", name="Saved capture", exact=False)).to_be_visible()
    assert page.locator("#detail-response").inner_text() == RAW
    assert page.locator("#detail-prompt").inner_text() == canonical
    page.evaluate(axe.read_text("utf-8"))  # Fresh page after reopen/reload.
    detail_violations = page.evaluate("""async () => (await axe.run(document)).violations.map(v =>
      ({id:v.id, impact:v.impact, targets:v.nodes.map(n => n.target)}))""")
    page.screenshot(path=str(output / "collector-detail.png"), animations="disabled", caret="hide")
    assert not detail_violations, detail_violations
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator("#detail-dialog").evaluate("e => e.scrollWidth <= e.clientWidth")
    assert not page.evaluate("async () => (await axe.run(document)).violations")
    page.screenshot(
        path=str(output / "collector-detail-mobile.png"), animations="disabled", caret="hide"
    )
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.keyboard.press("Escape")
    expect(page.locator("#detail-dialog")).not_to_be_visible()
    assert page.locator(".run-link").evaluate("e => e === document.activeElement")
    page.get_by_role("button", name="manual-", exact=False).click()
    page.get_by_role("button", name="Correct metadata with history").click()
    revised = json.loads(page.locator("#corrected-meta").input_value())
    revised["capture_note"] = "Synthetic metadata correction — not model output"
    page.locator("#corrected-meta").fill(json.dumps(revised, ensure_ascii=False, indent=2))
    page.get_by_label("Correction reason", exact=True).fill("Synthetic provenance correction test")
    page.get_by_role("button", name="Save Metadata Revision", exact=True).click()
    expect(page.locator("#correction-form")).not_to_be_visible()
    assert page.locator("#detail-response").inner_text() == RAW
    reports: dict[str, str] = {}
    with page.expect_download() as pending:
        page.get_by_role("button", name="Export Run Report", exact=True).click()
    pending.value.save_as(downloads / "single.md")
    reports["single"] = (downloads / "single.md").read_text("utf-8")
    page.get_by_role("button", name="Close run detail", exact=True).click()
    for format, name, suffix in (
        ("jsonl", "JSONL · preferred", "jsonl"),
        ("csv", "CSV", "csv"),
        ("markdown", "Combined Markdown", "md"),
    ):
        with page.expect_download() as pending:
            page.get_by_role("button", name=name, exact=True).click()
        path = downloads / f"combined.{suffix}"
        pending.value.save_as(path)
        with path.open(encoding="utf-8", newline="") as file:
            reports[format] = file.read()
    runs = load_jsonl(reports["jsonl"])
    assert len(runs) == 1 and load_csv(reports["csv"]) == runs
    run = runs[0]
    assert len(run.history) == 2
    assert run.raw_response == RAW and run.exact_prompt == canonical
    assert run.response_sha256 == digest(RAW) and run.prompt_sha256 == digest(canonical)
    for key in ("single", "markdown"):
        assert RAW in reports[key] and canonical in reports[key]
        assert run.prompt_sha256 in reports[key] and run.response_sha256 in reports[key]
    fill_capture(page)
    page.get_by_role("button", name="Save Raw Run", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("already exists")
    assert page.locator("#raw_response").input_value() == RAW
    page.get_by_label("Search metadata", exact=True).fill("no-matching-synthetic-label")
    expect(page.locator("#table-empty")).to_contain_text("No captures match")
    # Expected mocked 500 and duplicate 409 are browser console diagnostics, not JS failures.
    unexpected = [e for e in errors if "500" not in e and "409" not in e]
    assert not unexpected, unexpected
    assert not external, external
    return {
        "synthetic_capture_saved_reopened": True,
        "exports_verified": list(reports),
        "hashes_and_exact_strings": True,
        "revision_history": True,
        "duplicate_rejected": True,
        "failure_input_preserved": True,
        "unsaved_target_guard": True,
        "axe_violations": [],
        "keyboard_controls_checked": len(keyboard),
        "computed_style_values": styles,
        "external_requests": external,
        "unexpected_console_errors": unexpected,
        "screen_reader": "Not tested with an actual assistive-technology client",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/pilot/ui-check"))
    parser.add_argument("--browser-channel", default="chromium")
    parser.add_argument("--axe-script", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="synthetic-runtime-", dir=output) as temp:
        downloads = Path(temp)
        with make_server(
            Path(__file__).resolve().parents[1], downloads / "collector.sqlite3", 0
        ) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(
                        headless=True, channel=args.browser_channel
                    )
                    context = browser.new_context(
                        permissions=["clipboard-read", "clipboard-write"], reduced_motion="reduce"
                    )
                    try:
                        result = check(
                            context.new_page(), server.url, output, downloads, args.axe_script
                        )
                    finally:
                        context.close()
                        browser.close()
            finally:
                server.shutdown()
                thread.join()
    result["synthetic_runtime_cleaned"] = True
    (output / "ui-check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print("Collector UI check passed; four exports/hash/text verified; synthetic runtime removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
