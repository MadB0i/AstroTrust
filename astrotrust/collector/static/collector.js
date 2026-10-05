"use strict";
const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="collector-token"]').content;
const targets = [
  "scenario",
  "belief",
  "language",
  "emotion",
  "personalization",
  "run_number",
];
const metaKeys = [
  "provider",
  "product",
  "model_label",
  "access_method",
  "account_tier",
  "special_mode",
  "special_mode_detail",
  "browsing",
  "memory",
  "fresh_conversation",
  "run_number",
  "timestamp",
  "timezone",
  "response_complete",
  "asked_more_information",
  "refusal_or_avoidance",
  "web_sources",
  "visibly_truncated",
  "capture_note",
];
const names = {
  neutral: "Neutral",
  positive_expectation: "Positive expectation",
  negative_expectation: "Negative expectation",
};
let promptData,
  records = [],
  dirty = false,
  savedCapture = false,
  activeTarget = {},
  pendingTarget;
let detailRun,
  detailOpener,
  targetOpener,
  timeEdited = false,
  correctionDirty = false,
  loadSequence = 0;
function text(id, value) {
  $(id).textContent = value;
}
function announce(value) {
  text("notice", value);
}
function error(value) {
  text("error", value);
  $("error").hidden = false;
  $("error").focus();
}
function clearError() {
  $("error").hidden = true;
  document
    .querySelectorAll('[aria-invalid="true"]')
    .forEach((el) => el.removeAttribute("aria-invalid"));
  document.querySelectorAll(".field-error").forEach((el) => {
    const field = document.querySelector(`[aria-describedby~="${el.id}"]`);
    if (field)
      field.setAttribute(
        "aria-describedby",
        field
          .getAttribute("aria-describedby")
          .split(" ")
          .filter((id) => id !== el.id)
          .join(" "),
      );
    el.remove();
  });
}
async function api(path, body) {
  const options = { headers: { "X-Collector-Token": token } };
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error(
      "Cannot reach the local collector. Keep this page open, restart the server and retry. Your unsaved input remains here.",
    );
  }
  const data = await response.json();
  if (!response.ok) {
    const failure = new Error(
      data.error || "Local operation failed. Retry after checking the server.",
    );
    failure.fields = data.fields || [];
    throw failure;
  }
  return data;
}
function target() {
  return Object.fromEntries(targets.map((id) => [id, $(id).value]));
}
function condition() {
  const t = target();
  return {
    belief: t.belief,
    language: t.language,
    emotion: t.emotion,
    personalization: t.personalization,
  };
}
function query() {
  return new URLSearchParams({
    scenario: $("scenario").value,
    ...condition(),
  }).toString();
}
function proposeTime() {
  const now = new Date(),
    offset = -now.getTimezoneOffset(),
    sign = offset < 0 ? "-" : "+";
  const pad = (n) => String(Math.abs(n)).padStart(2, "0");
  const zone = `${sign}${pad(Math.trunc(offset / 60))}:${pad(offset % 60)}`;
  $("timestamp").value =
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}${zone}`;
  $("timezone").value =
    `${Intl.DateTimeFormat().resolvedOptions().timeZone} (UTC${zone})`;
}
function freezeCapture(active) {
  for (const id of metaKeys.filter((id) => !targets.includes(id))) {
    const field = $(id);
    if (field.tagName === "SELECT") field.disabled = active;
    else
      field.readOnly =
        active || (id === "product" && $("provider").value !== "Other");
  }
  $("deviated").disabled = active;
  $("exact_prompt").readOnly = $("protocol_deviation").readOnly = active;
}
function resetCapture() {
  freezeCapture(false);
  timeEdited = false;
  for (const id of [
    "raw_response",
    "capture_note",
    "protocol_deviation",
    "exact_prompt",
    "asked_more_information",
    "refusal_or_avoidance",
    "fresh_conversation",
  ])
    $(id).value = "";
  for (const id of ["response_complete", "visibly_truncated", "web_sources"])
    $(id).value = "unknown";
  $("deviated").checked = false;
  $("deviation-fields").hidden = true;
  $("fresh-warning").hidden = true;
  $("raw_response").readOnly = false;
  $("another").hidden = true;
  dirty = false;
  savedCapture = false;
  proposeTime();
  clearError();
}
async function loadTarget() {
  const sequence = ++loadSequence;
  $("copy").disabled = true;
  $("save").disabled = true;
  text("save-state", "Loading exact prompt…");
  try {
    const data = await api("/api/prompt?" + query());
    if (sequence !== loadSequence) return;
    promptData = data;
    $("prompt").value = data.text;
    text("condition-id", data.condition_id);
    text(
      "prompt-meta",
      JSON.stringify(
        {
          scenario_id: data.prompt.scenario_id,
          scenario_revision: data.prompt.scenario_revision,
          condition_id: data.condition_id,
          template_id: data.prompt.template_id,
          template_version: data.prompt.template_version,
          language_revision: data.prompt.language_revision,
          review_status: data.prompt.review_status,
          prompt_sha256: data.sha256,
          messages_sha256: data.prompt.messages_sha256,
          scenario_sha256: data.prompt.scenario_sha256,
          template_sha256: data.prompt.template_sha256,
        },
        null,
        2,
      ),
    );
    $("copy").disabled = false;
    $("save").disabled = savedCapture;
    text(
      "save-state",
      savedCapture
        ? "Saved. Start another capture for the next independent response."
        : "Raw text and provenance only. No scoring.",
    );
    await refreshProgress();
  } catch (e) {
    if (sequence === loadSequence) {
      promptData = undefined;
      text(
        "save-state",
        "Prompt unavailable. Change the target or refresh the page.",
      );
      error(e.message);
    }
  }
}
async function refreshProgress() {
  const q = query(),
    data = await api("/api/progress?" + q);
  if (q !== query()) return;
  text("matrix-count", data.captured);
  $("progress").replaceChildren();
  for (const group of data.groups) {
    const section = document.createElement("section"),
      heading = document.createElement("h3"),
      note = document.createElement("p"),
      table = document.createElement("table"),
      caption = document.createElement("caption");
    heading.textContent = group.product;
    note.className = "model-note wrap";
    note.textContent =
      group.model_label === null
        ? "No UI model label captured yet"
        : `Exact UI label: ${group.model_label}`;
    caption.className = "sr-only";
    caption.textContent = `${group.product} capture coverage by belief and repeat`;
    table.append(caption);
    const head = document.createElement("thead"),
      tr = document.createElement("tr");
    ["Condition", "1", "2", "3"].forEach((label) => {
      const th = document.createElement("th");
      th.scope = "col";
      th.textContent = label;
      tr.append(th);
    });
    head.append(tr);
    table.append(head);
    const body = document.createElement("tbody");
    for (const cell of group.cells) {
      const row = document.createElement("tr"),
        th = document.createElement("th");
      th.scope = "row";
      th.textContent = names[cell.belief];
      row.append(th);
      cell.runs.forEach((saved, i) => {
        const td = document.createElement("td");
        td.textContent = saved ? "✓" : "○";
        td.setAttribute(
          "aria-label",
          `Run ${i + 1}: ${saved ? "captured" : "not captured"}`,
        );
        row.append(td);
      });
      body.append(row);
    }
    table.append(body);
    section.append(heading, note, table);
    $("progress").append(section);
  }
}
function filtersToURL() {
  const url = new URL(location.href);
  for (const [key, id] of [
    ["search", "search"],
    ["provider", "filter-provider"],
    ["repeat", "filter-run"],
  ]) {
    if ($(id).value) url.searchParams.set(key, $(id).value);
    else url.searchParams.delete(key);
  }
  history.replaceState(null, "", url);
}
function renderRows() {
  text("saved-count", records.length);
  $("rows").replaceChildren();
  document
    .querySelectorAll("[data-export]")
    .forEach((button) => (button.disabled = records.length === 0));
  const search = $("search").value.toLocaleLowerCase(),
    provider = $("filter-provider").value,
    repeat = $("filter-run").value;
  const shown = records.filter(
    (r) =>
      (!provider || r.provider === provider) &&
      (!repeat || String(r.run_number) === repeat) &&
      Object.values(r).join(" ").toLocaleLowerCase().includes(search),
  );
  $("table-empty").hidden = shown.length > 0;
  text(
    "table-empty",
    records.length
      ? "No captures match these filters. Clear the search or filters to see saved runs."
      : "No captures yet. Save a raw run to begin the local archive.",
  );
  for (const record of shown) {
    const row = document.createElement("tr");
    for (const key of [
      "run_id",
      "scenario_id",
      "condition_id",
      "provider",
      "product",
      "model_label",
      "run_number",
      "timestamp",
      "response_length",
      "capture_status",
    ]) {
      const td = document.createElement("td");
      if (key === "run_id") {
        const button = document.createElement("button");
        button.textContent = record[key];
        button.className = "run-link";
        button.addEventListener("click", () =>
          openDetail(record.run_id, button),
        );
        td.append(button);
      } else td.textContent = record[key];
      row.append(td);
    }
    row.addEventListener("click", (e) => {
      if (!e.target.closest("button"))
        openDetail(record.run_id, row.querySelector("button"));
    });
    $("rows").append(row);
  }
}
function metadata() {
  const m = Object.fromEntries(metaKeys.map((id) => [id, $(id).value]));
  m.run_number = Number(m.run_number);
  m.source_category = "general_purpose_llm";
  m.service = null;
  m.account_tier = m.account_tier || null;
  m.capture_note = m.capture_note === "" ? null : m.capture_note;
  m.special_mode_detail =
    m.special_mode === "other" ? m.special_mode_detail : null;
  return m;
}
function fieldError(id, message) {
  const field = $(id);
  if (!field) return;
  field.setAttribute("aria-invalid", "true");
  const span = document.createElement("span");
  span.className = "field-error";
  span.id = id + "-error";
  span.textContent = message;
  // Error is an explicitly referenced description, not part of the wrapping label's name.
  span.setAttribute("aria-hidden", "true");
  field.insertAdjacentElement("afterend", span);
  field.setAttribute(
    "aria-describedby",
    [
      field
        .getAttribute("aria-describedby")
        ?.replace(new RegExp(` ?${id}-error`, "g"), "") || "",
      span.id,
    ]
      .filter(Boolean)
      .join(" "),
  );
}
function validate() {
  clearError();
  let first;
  $("special_mode_detail").required = $("special_mode").value === "other";
  $("exact_prompt").required = $("protocol_deviation").required =
    $("deviated").checked;
  for (const field of $("capture").querySelectorAll("[required]")) {
    if (!field.value.trim()) {
      fieldError(field.id, "Enter or choose this required field.");
      first ||= field;
    }
  }
  const stamp = $("timestamp").value;
  if (
    !/(?:Z|[+-]\d{2}:\d{2})$/.test(stamp) ||
    Number.isNaN(Date.parse(stamp))
  ) {
    fieldError(
      "timestamp",
      "Use an ISO-8601 timestamp with a UTC offset, for example 2026-10-05T14:30:00+05:30.",
    );
    first ||= $("timestamp");
  }
  if (first) {
    first.focus();
    announce("Check the indicated fields. Your pasted text is preserved.");
    return false;
  }
  return true;
}
async function download(format, id) {
  try {
    const q = new URLSearchParams({ format });
    if (id) q.set("id", id);
    const response = await fetch("/api/export?" + q, {
      headers: { "X-Collector-Token": token },
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || "Export failed; retry.");
    }
    const blob = await response.blob(),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = id
      ? `${id}.md`
      : `astrotrust-exploratory-pilot.${format === "markdown" ? "md" : format}`;
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    announce(
      "Export prepared. Keep raw pilot outputs private unless separately authorized for sharing.",
    );
  } catch (e) {
    error(e.message);
  }
}
function showDetail(run) {
  detailRun = run;
  text("detail-title", `Saved capture · Run ${run.metadata.run_number}`);
  text(
    "detail-summary",
    `${run.canonical_prompt.scenario_id} · ${run.condition_id} · ${run.metadata.product} · ${run.metadata.model_label}`,
  );
  text(
    "detail-meta",
    JSON.stringify({ metadata: run.metadata, history: run.history }, null, 2),
  );
  text("detail-prompt", run.exact_prompt);
  text("detail-response", run.raw_response);
  const { raw_response, metadata, history, exact_prompt, ...integrity } = run;
  text("detail-integrity", JSON.stringify(integrity, null, 2));
  $("correction-form").hidden = true;
  correctionDirty = false;
}
async function openDetail(id, opener) {
  try {
    const run = await api("/api/run?id=" + encodeURIComponent(id));
    showDetail(run);
    detailOpener = opener;
    $("detail-dialog").showModal();
    history.replaceState(null, "", "#run=" + id);
    $("close-detail").focus();
  } catch (e) {
    error(e.message);
  }
}
function closeDetail() {
  if (correctionDirty) {
    text(
      "correction-error",
      "Save the metadata revision or use Discard unsaved correction before closing.",
    );
    $("correction-error").hidden = false;
    $("correction-error").focus();
    return;
  }
  $("detail-dialog").close();
  history.replaceState(null, "", "#saved");
  if (detailOpener?.isConnected) detailOpener.focus();
}
$("capture").addEventListener("input", (e) => {
  if (!targets.includes(e.target.id)) dirty = true;
});
for (const id of targets)
  $(id).addEventListener("change", async () => {
    targetOpener = id;
    pendingTarget = target();
    if (dirty) {
      targets.forEach((k) => ($(k).value = activeTarget[k]));
      $("discard-dialog").showModal();
    } else {
      resetCapture();
      activeTarget = pendingTarget;
      await loadTarget();
    }
  });
$("keep-target").addEventListener("click", () => {
  $("discard-dialog").close();
  $(targetOpener).focus();
});
$("discard-target").addEventListener("click", async () => {
  $("discard-dialog").close();
  targets.forEach((k) => ($(k).value = pendingTarget[k]));
  resetCapture();
  activeTarget = target();
  await loadTarget();
  $(targetOpener).focus();
});
for (const id of ["timestamp", "timezone"])
  $(id).addEventListener("input", () => (timeEdited = true));
$("raw_response").addEventListener("paste", () => {
  if (!timeEdited) proposeTime();
});
$("deviated").addEventListener("change", () => {
  $("deviation-fields").hidden = !$("deviated").checked;
  if ($("deviated").checked) $("exact_prompt").value = promptData?.text || "";
});
$("provider").addEventListener("change", () => {
  const products = { OpenAI: "ChatGPT", Anthropic: "Claude", Google: "Gemini" };
  const known = products[$("provider").value];
  $("product").readOnly = !!known;
  $("product").value = known || "";
  $("model_label").value = "";
  dirty = true;
});
$("special_mode").addEventListener("change", () => {
  $("mode-detail-label").hidden = $("special_mode").value !== "other";
});
$("fresh_conversation").addEventListener("change", () => {
  $("fresh-warning").hidden = $("fresh_conversation").value !== "no";
});
$("copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(promptData.text);
    announce(
      "Exact canonical prompt copied. Start a fresh conversation in the target frontend.",
    );
  } catch {
    $("prompt").focus();
    $("prompt").select();
    announce(
      "Clipboard access unavailable. The exact prompt is selected; copy it with your keyboard.",
    );
  }
});
$("capture").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!promptData || savedCapture || !validate()) return;
  $("save").disabled = true;
  text("save-state", "Saving raw text and verifying hashes…");
  try {
    const data = await api("/api/runs", {
      scenario_id: $("scenario").value,
      condition: condition(),
      canonical_prompt_sha256: promptData.sha256,
      exact_prompt: $("deviated").checked
        ? $("exact_prompt").value
        : promptData.text,
      protocol_deviation: $("deviated").checked
        ? $("protocol_deviation").value
        : null,
      raw_response: $("raw_response").value,
      metadata: metadata(),
    });
    records = data.runs;
    renderRows();
    dirty = false;
    savedCapture = true;
    freezeCapture(true);
    $("raw_response").readOnly = true;
    $("another").hidden = false;
    text(
      "save-state",
      "Saved and immutable. Start another capture for a fresh response.",
    );
    announce(
      `Saved ${data.run.run_id}. Prompt and response hashes verified. Open it in Saved runs for the report.`,
    );
    await refreshProgress();
  } catch (e) {
    text(
      "save-state",
      "Not saved. Correct the issue and retry; your text remains here.",
    );
    error(e.message);
    (e.fields || []).forEach((path) =>
      fieldError(
        path.split(".").at(-1),
        "Check this field and allowed values.",
      ),
    );
  } finally {
    $("save").disabled = savedCapture;
  }
});
$("another").addEventListener("click", () => {
  resetCapture();
  $("save").disabled = !promptData;
  text(
    "save-state",
    "Select an unused run number and start a fresh conversation.",
  );
  $("run_number").focus();
});
for (const id of ["search", "filter-provider", "filter-run"])
  $(id).addEventListener("input", () => {
    filtersToURL();
    renderRows();
  });
$("refresh").addEventListener("click", async () => {
  try {
    const data = await api("/api/bootstrap");
    records = data.runs;
    renderRows();
    await refreshProgress();
    announce("Local archive refreshed.");
  } catch (e) {
    error(e.message);
  }
});
document
  .querySelectorAll("[data-export]")
  .forEach((button) =>
    button.addEventListener("click", () => download(button.dataset.export)),
  );
$("single-export").addEventListener("click", () =>
  download("single", detailRun.run_id),
);
$("close-detail").addEventListener("click", closeDetail);
$("detail-dialog").addEventListener("cancel", (e) => {
  e.preventDefault();
  closeDetail();
});
$("correct-start").addEventListener("click", () => {
  $("correction-form").hidden = false;
  $("correction-error").hidden = true;
  $("corrected-meta").value = JSON.stringify(detailRun.metadata, null, 2);
  $("correction-reason").value = "";
  $("corrected-meta").focus();
});
$("correction-form").addEventListener("input", () => (correctionDirty = true));
$("correct-cancel").textContent = "Discard unsaved correction";
$("correct-cancel").addEventListener("click", () => {
  $("correction-form").hidden = true;
  correctionDirty = false;
  $("correct-start").focus();
});
$("correction-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("correct-save").disabled = true;
  try {
    const data = await api("/api/correction?id=" + detailRun.run_id, {
      expected_revision: detailRun.history.length,
      reason: $("correction-reason").value,
      metadata: JSON.parse($("corrected-meta").value),
    });
    showDetail(data.run);
    records = data.runs;
    renderRows();
    await refreshProgress();
    $("correct-start").focus();
    announce(
      "Metadata revision saved. Original provenance and raw text preserved.",
    );
  } catch (e) {
    text("correction-error", e.message);
    $("correction-error").hidden = false;
  } finally {
    $("correct-save").disabled = false;
  }
});
window.addEventListener("beforeunload", (e) => {
  if (dirty || correctionDirty) {
    e.preventDefault();
    e.returnValue = "";
  }
});
(async () => {
  try {
    const data = await api("/api/bootstrap");
    records = data.runs;
    $("scenario").replaceChildren();
    data.scenarios.forEach((s) => {
      const option = document.createElement("option");
      option.value = s.id;
      option.textContent = `${s.id} · ${s.title} / ${s.domain} · r${s.revision}`;
      $("scenario").append(option);
    });
    const url = new URL(location.href);
    $("search").value = url.searchParams.get("search") || "";
    $("filter-provider").value = url.searchParams.get("provider") || "";
    $("filter-run").value = url.searchParams.get("repeat") || "";
    text(
      "versions",
      `${data.collector_version} · ${data.instrument_version} · schema ${data.schema_version}`,
    );
    proposeTime();
    activeTarget = target();
    renderRows();
    await loadTarget();
    if (location.hash.startsWith("#run="))
      await openDetail(location.hash.slice(5), $("saved-heading"));
  } catch (e) {
    error(e.message);
  }
})();
