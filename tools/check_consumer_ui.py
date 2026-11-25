"""Offline consumer browser regression with temporary synthetic stores only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from astrotrust.benchmark.prompts import digest
from astrotrust.collector.consumer_exports import load_csv, load_jsonl
from astrotrust.collector.consumer_models import PROMPTS
from astrotrust.collector.consumer_profiles import PROFILES, profile_digest
from astrotrust.collector.server import make_server

RAW = (
    "  [Synthetic consumer response — not service output]\n\n"
    "## শিৰোনাম / शीर्षक\n`````\n<script>window.UNSAFE=true</script>\n \n"
)


def fill_capture(page: Page) -> None:
    page.get_by_label("Service / app name", exact=True).fill("  Synthetic exact service / v?  ")
    page.get_by_label("Asked for more information", exact=True).select_option("no")
    page.get_by_label("Refusal / avoidance", exact=True).select_option("no")
    page.get_by_label("DOB", exact=True).check()
    page.get_by_label("birth time", exact=True).check()
    page.get_by_label("Profile used", exact=True).select_option("consumer-profile-001")
    page.get_by_label("Submitted date_of_birth", exact=True).check()
    page.get_by_label("Submitted birth_time", exact=True).check()
    page.get_by_label("Interaction mode", exact=True).select_option("prompt_and_fixed_profile_only")
    page.get_by_label("Capture note (optional)", exact=False).fill(
        "A fixed fictional profile was used."
    )
    page.get_by_label("Raw response", exact=True).fill(RAW)


def check(page: Page, url: str, output: Path, downloads: Path, axe: Path) -> dict[str, object]:
    page.set_default_timeout(8000)
    errors: list[str] = []
    external: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(url) else None)
    page.goto(url + "/consumer")
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("button", name="Copy Prompt", exact=True)).to_be_enabled()
    expect(page.locator("#saved-count")).to_have_text("0")
    expect(page.locator("#table-empty")).to_contain_text("No consumer captures")
    assert page.locator("#progress").count() == 0
    assert "actual personal birth details. Record field names only." in page.inner_text("main")
    assert page.locator('#personal-fields input:not([type="checkbox"])').count() == 0
    page.get_by_label("Prompt ID", exact=True).select_option("consumer-career-p2")
    expect(page.locator("#prompt")).to_have_value(PROMPTS["consumer-career-p2"])
    assert not page.locator("#discard-dialog").is_visible()
    page.get_by_role("button", name="Copy Prompt", exact=True).click()
    expect(page.locator("#notice")).to_contain_text("Exact consumer registry prompt copied")
    assert page.evaluate("navigator.clipboard.readText()") == PROMPTS["consumer-career-p2"]
    page.get_by_label("Prompt ID", exact=True).select_option("consumer-career-p1")
    page.evaluate(axe.read_text("utf-8"))
    styles: dict[str, Any] = page.evaluate("""() => Object.fromEntries(
      ['fontSize','fontFamily','borderRadius','boxShadow','color'].map(p => [p,
       [...new Set([...document.querySelectorAll('*')].map(e => getComputedStyle(e)[p]))]]))""")
    for name, width, height in (
        ("desktop", 1440, 900),
        ("tablet", 768, 1024),
        ("mobile", 390, 844),
    ):
        page.set_viewport_size({"width": width, "height": height})
        page.evaluate("window.scrollTo(0, 0)")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), name
        violations = page.evaluate("async () => (await axe.run(document)).violations")
        assert not violations, [(v["id"], v["impact"]) for v in violations]
        page.screenshot(
            path=str(output / f"consumer-{name}.png"),
            full_page=True,
            animations="disabled",
            caret="hide",
        )
        page.screenshot(
            path=str(output / f"consumer-{name}-viewport.png"), animations="disabled", caret="hide"
        )
    page.set_viewport_size({"width": 1440, "height": 900})
    page.locator("body").click(position={"x": 1, "y": 1})
    keyboard = []
    for _ in range(90):
        page.keyboard.press("Tab")
        item: dict[str, object] = page.evaluate("""() => {
          const e=document.activeElement, s=getComputedStyle(e);
          return {tag:e.tagName,id:e.id,outline:s.outlineStyle}; }""")
        keyboard.append(item)
        if item["tag"] != "BODY":
            assert item["outline"] != "none", item
    page.get_by_role("button", name="Save Consumer Capture", exact=True).click()
    assert not page.locator("#service_name").evaluate("e => e.checkValidity()")
    fill_capture(page)
    expect(page.locator("#profile-provenance")).to_contain_text(
        "FICTIONAL / SYNTHETIC RESEARCH INPUT"
    )
    assert not page.locator("#profile-value-gender").inner_text() == "male"
    assert page.get_by_role("button", name="Copy gender", exact=True).is_disabled()
    assert page.get_by_label("Submitted gender", exact=True).is_disabled()
    page.get_by_role("button", name="Copy date_of_birth", exact=True).click()
    expect(page.locator("#notice")).to_contain_text("Fixed synthetic date_of_birth copied")
    assert page.evaluate("navigator.clipboard.readText()") == "1998-02-12"
    page.get_by_label("Prompt ID", exact=True).select_option("consumer-career-p2")
    expect(page.get_by_role("dialog", name="Discard unsaved capture?")).to_be_visible()
    page.get_by_role("button", name="Keep collecting", exact=True).click()
    assert page.locator("#raw_response").input_value() == RAW
    assert page.locator("#prompt_id").input_value() == "consumer-career-p1"
    page.get_by_role("link", name="Frontier models", exact=True).click()
    expect(page.locator("#discard-dialog")).to_be_visible()
    page.keyboard.press("Escape")
    assert page.locator("#raw_response").input_value() == RAW
    page.get_by_role("button", name="Refresh ledger", exact=True).click()
    expect(page.locator("#reload")).to_be_enabled()
    assert page.locator("#raw_response").input_value() == RAW
    page.route(
        "**/api/consumer/runs",
        lambda r: r.fulfill(
            status=500,
            json={"error": "Synthetic disk failure; retry after checking storage."},
        ),
    )
    page.get_by_role("button", name="Save Consumer Capture", exact=True).click()
    expect(page.get_by_role("alert").first).to_contain_text("Synthetic disk failure")
    assert page.locator("#raw_response").input_value() == RAW
    page.unroute("**/api/consumer/runs")
    page.get_by_role("button", name="Save Consumer Capture", exact=True).click()
    expect(page.locator("#saved-count")).to_have_text("1")
    assert page.locator("#raw_response").is_disabled()
    assert page.evaluate("window.UNSAFE") is None
    page.reload()
    page.wait_for_load_state("networkidle")
    expect(page.locator("#saved-count")).to_have_text("1")
    page.get_by_role("button", name="Synthetic exact service / v?", exact=True).click()
    expect(page.locator("#detail-dialog")).to_be_visible()
    assert page.locator("#detail-response").inner_text() == RAW
    assert page.locator("#detail-prompt").inner_text() == PROMPTS["consumer-career-p1"]
    page.evaluate(axe.read_text("utf-8"))
    assert not page.evaluate("async () => (await axe.run(document)).violations")
    page.get_by_role("button", name="Correct metadata with history", exact=True).click()
    revised = json.loads(page.locator("#corrected-meta").input_value())
    revised["personal_fields_requested"] = ["DOB: 1990-01-01"]
    page.locator("#corrected-meta").fill(json.dumps(revised))
    page.locator("#correction-reason").fill("Synthetic privacy rejection check")
    page.get_by_role("button", name="Save Metadata Revision", exact=True).click()
    expect(page.locator("#correction-error")).to_contain_text("personal_fields_requested")
    revised["personal_fields_requested"] = ["DOB", "birth time"]
    revised["cost"] = "free_trial"
    page.locator("#corrected-meta").fill(json.dumps(revised))
    page.get_by_role("button", name="Save Metadata Revision", exact=True).click()
    expect(page.locator("#correction-form")).not_to_be_visible()
    assert page.locator("#detail-response").inner_text() == RAW
    reports = {}
    with page.expect_download() as pending:
        page.get_by_role("button", name="Export Run Report", exact=True).click()
    pending.value.save_as(downloads / "single.md")
    reports["single"] = (downloads / "single.md").read_text("utf-8")
    page.set_viewport_size({"width": 390, "height": 844})
    assert not page.evaluate("async () => (await axe.run(document)).violations")
    assert page.locator("#detail-dialog").evaluate("e => e.scrollWidth <= e.clientWidth")
    page.screenshot(
        path=str(output / "consumer-detail-mobile.png"), animations="disabled", caret="hide"
    )
    page.keyboard.press("Escape")
    assert page.get_by_role("button", name="Synthetic exact service / v?", exact=True).evaluate(
        "e => e===document.activeElement"
    )
    for format, label, suffix in (
        ("jsonl", "JSONL · authoritative", "jsonl"),
        ("csv", "CSV", "csv"),
        ("markdown", "Combined Markdown", "md"),
    ):
        with page.expect_download() as pending:
            page.get_by_role("button", name=label, exact=True).click()
        path = downloads / f"consumer.{suffix}"
        pending.value.save_as(path)
        with path.open(encoding="utf-8", newline="") as file:
            reports[format] = file.read()
    runs = load_jsonl(reports["jsonl"])
    assert len(runs) == 1 and load_csv(reports["csv"]) == runs
    run = runs[0]
    assert run.raw_response == RAW and run.exact_prompt == PROMPTS["consumer-career-p1"]
    assert run.response_sha256 == digest(RAW) and run.prompt_sha256 == digest(run.exact_prompt)
    assert run.metadata.service_name == "  Synthetic exact service / v?  "
    assert run.metadata.personal_fields_requested == ("DOB", "birth time")
    assert run.profile_id == "consumer-profile-001"
    assert run.profile_fields_submitted == ("date_of_birth", "birth_time")
    assert run.profile_snapshot == PROFILES["consumer-profile-001"]
    assert run.profile_sha256 == profile_digest(PROFILES["consumer-profile-001"])
    assert run.exact_interaction is None and run.interaction_mode == "prompt_and_fixed_profile_only"
    assert len(run.history) == 2 and run.history[0].metadata.cost == "unknown"
    for format in ("single", "markdown"):
        assert RAW in reports[format] and run.prompt_sha256 in reports[format]
    fill_capture(page)
    page.get_by_role("button", name="Save Consumer Capture", exact=True).click()
    expect(page.locator("#error")).to_contain_text("already exists")
    assert page.locator("#raw_response").input_value() == RAW
    page.get_by_role("button", name="Start another capture", exact=True).click()
    page.get_by_role("button", name="Discard and continue", exact=True).click()
    fill_capture(page)
    page.locator("#run_number").fill("2")
    clipboard_raw = RAW.replace("\n", "\r\n") + "Lone carriage return\rEnd"
    clipboard_prompt = PROMPTS["consumer-career-p1"] + "\r\n[Synthetic deviation]"
    clipboard_interaction = (
        "  SERVICE: Which fictional city?\r\nRESEARCHER: Guwahati, Assam, India\r\n"
        "`````\n<script>window.UNSAFE=true</script>\r\n \t"
    )
    page.get_by_label("Interaction mode", exact=True).select_option("multi_step")
    page.get_by_label("Interaction record type", exact=True).select_option("transcript")
    for id, content in (
        ("raw_response", clipboard_raw),
        ("exact_prompt", clipboard_prompt),
        ("exact_interaction", clipboard_interaction),
    ):
        page.evaluate(
            """({id,content}) => {
          const e=document.getElementById(id), data=new DataTransfer();
          e.focus(); e.select(); data.setData('text/plain',content);
          e.dispatchEvent(new ClipboardEvent('paste', {
            clipboardData:data,bubbles:true,cancelable:true}));
        }""",
            {"id": id, "content": content},
        )
    # Editing an unrelated suffix also retains earlier clipboard CRLF sequences.
    page.locator("#raw_response").press("End")
    page.locator("#raw_response").press("!")
    clipboard_raw += "!"
    page.locator("#protocol_deviation").fill("Synthetic exact clipboard test")
    page.get_by_role("button", name="Save Consumer Capture", exact=True).click()
    expect(page.locator("#saved-count")).to_have_text("2")
    complete = page.evaluate("""async () => {
      const r=await fetch('/api/consumer/export?format=jsonl',{
        headers:{'X-Collector-Token':document.querySelector('meta[name="collector-token"]').content}});
      return await r.text(); }""")
    second = next(r for r in load_jsonl(complete) if r.metadata.run_number == 2)
    assert second.raw_response == clipboard_raw and second.exact_prompt == clipboard_prompt
    assert second.response_sha256 == digest(clipboard_raw)
    assert second.prompt_sha256 == digest(clipboard_prompt)
    assert second.exact_interaction == clipboard_interaction
    assert second.interaction_sha256 == digest(clipboard_interaction)
    # Protocol evidence is literal text in detail, with explicit additional-interaction attribution.
    # Ledger order is by run ID; select the multi-step run by its repeat number.
    button = (
        page.locator("#run-table tr")
        .filter(has=page.get_by_role("cell", name="2", exact=True))
        .get_by_role("button")
    )
    button.click()
    expect(page.locator("#detail-interaction-mode")).to_contain_text("Do not attribute")
    assert page.locator("#detail-interaction").text_content() == clipboard_interaction
    assert page.evaluate("window.UNSAFE") is None
    page.keyboard.press("Escape")
    # Explicit no-profile capture, separate from requested fields and prior profile snapshots.
    page.get_by_role("button", name="Start another capture", exact=True).click()
    fill_capture(page)
    page.locator("#run_number").fill("3")
    page.get_by_label("Submitted date_of_birth", exact=True).uncheck()
    page.get_by_label("Submitted birth_time", exact=True).uncheck()
    page.get_by_label("Profile used", exact=True).select_option("not_used")
    page.get_by_label("Interaction mode", exact=True).select_option("initial_prompt_only")
    page.get_by_label("Capture note (optional)", exact=False).fill("Synthetic no-profile capture")
    page.get_by_role("button", name="Save Consumer Capture", exact=True).click()
    expect(page.locator("#saved-count")).to_have_text("3")
    not_used = page.evaluate("""async () => {
      const r=await fetch('/api/consumer/export?format=jsonl',{
        headers:{'X-Collector-Token':document.querySelector('meta[name="collector-token"]').content}});
      return await r.text(); }""")
    third = next(r for r in load_jsonl(not_used) if r.metadata.run_number == 3)
    assert third.profile_id == "not_used" and third.profile_snapshot is None
    assert third.profile_fields_submitted == () and third.profile_sha256 is None
    page.get_by_role("link", name="Frontier models", exact=True).click()
    expect(page.locator("#matrix-count")).to_have_text("0")
    expect(page.locator("#saved-count")).to_have_text("0")
    expect(page.locator("#progress td")).to_have_count(27)
    unexpected = [e for e in errors if not any(status in e for status in ("500", "409", "400"))]
    assert not unexpected, unexpected
    assert not external, external
    return {
        "synthetic_capture_saved_reopened": True,
        "consumer_separation": True,
        "exports_verified": list(reports),
        "exact_hashes_and_strings": True,
        "field_names_only": True,
        "revision_history": True,
        "duplicate_rejected": True,
        "failure_input_preserved": True,
        "clipboard_crlf_and_lone_cr_preserved": True,
        "fixed_profile_snapshot_version_hash": True,
        "requested_and_supplied_fields_separate": True,
        "gender_gated": True,
        "explicit_not_used": True,
        "multi_step_transcript_exact_hash": True,
        "unsaved_navigation_guard": True,
        "axe_violations": [],
        "keyboard_controls_checked": len(keyboard),
        "computed_style_values": styles,
        "external_requests": external,
        "unexpected_console_errors": unexpected,
        "screen_reader": "Not tested with an actual assistive-technology client",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/pilot/consumer-ui-check"))
    parser.add_argument("--browser-channel", default="chromium")
    parser.add_argument("--axe-script", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="synthetic-runtime-", dir=output) as temp:
        downloads = Path(temp)
        with make_server(
            Path(__file__).resolve().parents[1], downloads / "general.sqlite3", 0
        ) as server:
            before = server.collector.store.path.read_bytes()
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
            assert server.collector.store.path.read_bytes() == before
    result["synthetic_runtime_cleaned"] = True
    (output / "ui-check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(
        "Consumer UI passed: four exports, exact hashes, privacy, separation, "
        "revisions, keyboard and axe."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
