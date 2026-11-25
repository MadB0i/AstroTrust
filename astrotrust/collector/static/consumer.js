"use strict";
const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="collector-token"]').content;
const metadataKeys = [
  "service_name", "access_method", "cost", "ai_generated_claimed",
  "human_involvement_claimed", "response_type", "observed_model_label",
  "repeat_identity", "timestamp", "timezone", "response_complete",
  "visibly_truncated", "asked_more_information", "refusal_or_avoidance", "capture_note",
];
let prompts = [], profiles = [], records = [], activePrompt, dirty = false, saved = false;
let timeEdited = false, pendingAction, guardOpener, detailRun, detailOpener, saving = false;
let correctionDirty = false;
// Textareas display CRLF as LF. Keep clipboard strings separately so the saved
// evidence and hashes retain exact clipboard line endings as well as Unicode.
const verbatim = new Map();
function sourceOffset(source, displayOffset) {
  let sourceIndex = 0, displayIndex = 0;
  while (sourceIndex < source.length && displayIndex < displayOffset) {
    if (source[sourceIndex] === "\r" && source[sourceIndex + 1] === "\n") sourceIndex++;
    sourceIndex++; displayIndex++;
  }
  return sourceIndex;
}
function syncVerbatim(id) {
  const element = $(id), old = verbatim.get(id);
  if (!old) { verbatim.set(id, { raw: element.value, display: element.value }); return; }
  const next = element.value;
  if (old.display === next) return;
  let start = 0, end = 0;
  while (start < old.display.length && start < next.length && old.display[start] === next[start]) start++;
  while (end < old.display.length - start && end < next.length - start &&
         old.display[old.display.length - 1 - end] === next[next.length - 1 - end]) end++;
  const raw = old.raw.slice(0, sourceOffset(old.raw, start)) +
    next.slice(start, next.length - end) +
    old.raw.slice(sourceOffset(old.raw, old.display.length - end));
  verbatim.set(id, { raw, display: next });
}
function exactValue(id) { syncVerbatim(id); return verbatim.get(id).raw; }
for (const id of ["exact_prompt", "raw_response", "exact_interaction"]) {
  $(id).addEventListener("input", () => syncVerbatim(id));
  $(id).addEventListener("paste", (event) => {
    if (!event.clipboardData || $(id).disabled) return;
    event.preventDefault();
    syncVerbatim(id);
    const element = $(id), old = verbatim.get(id), clipboard = event.clipboardData.getData("text/plain");
    const start = element.selectionStart, end = element.selectionEnd;
    const raw = old.raw.slice(0, sourceOffset(old.raw, start)) + clipboard +
      old.raw.slice(sourceOffset(old.raw, end));
    element.setRangeText(clipboard, start, end, "end");
    verbatim.set(id, { raw, display: element.value });
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
function announce(message) { $("notice").textContent = message; }
function error(message) {
  $("error").textContent = message;
  $("error").hidden = false;
  $("error").focus();
}
async function api(path, body) {
  const response = await fetch(`/api/consumer/${path}`, {
    headers: { "X-Collector-Token": token, "Content-Type": "application/json" },
    ...(body === undefined ? {} : { method: "POST", body: JSON.stringify(body) }),
  });
  const data = await response.json();
  if (!response.ok) {
    for (const field of data.fields || []) {
      const id = field.replace(/^metadata\./, "").split(".")[0];
      const element = $(id === "personal_fields_requested" ? "corrected-meta" : id);
      if (element) {
        element.setAttribute("aria-invalid", "true");
        if (element.closest("#capture")) element.setAttribute("aria-describedby", "error");
      }
    }
    throw new Error(data.error || "Could not save or load. Keep your entries and retry.");
  }
  return data;
}
function clock() {
  const date = new Date(), minutes = -date.getTimezoneOffset();
  const offset = `${minutes >= 0 ? "+" : "-"}${String(Math.floor(Math.abs(minutes) / 60)).padStart(2, "0")}:${String(Math.abs(minutes) % 60).padStart(2, "0")}`;
  $("timestamp").value = new Date(date.getTime() + minutes * 60000).toISOString().slice(0, -1) + offset;
  $("timezone").value = `${Intl.DateTimeFormat().resolvedOptions().timeZone} (UTC${offset})`;
}
function setPrompt(id) {
  activePrompt = prompts.find((p) => p.id === id);
  $("prompt_id").value = id;
  $("prompt").value = activePrompt.text;
  $("exact_prompt").value = activePrompt.text;
  verbatim.set("exact_prompt", { raw: activePrompt.text, display: activePrompt.text });
  $("protocol_deviation").value = "";
  $("prompt-hash").textContent = `consumer-career-1.0 · SHA-256 ${activePrompt.sha256}`;
}
function selectedProfile() {
  return profiles.find((p) => p.snapshot.profile_id === $("profile_id").value);
}
function profileUI() {
  const profile = selectedProfile(), enabled = Boolean(profile);
  $("gender_required").disabled = !enabled && !$("gender_required").checked;
  $("profile-provenance").textContent = profile
    ? `${profile.snapshot.research_input_label} · ${profile.snapshot.profile_version} · SHA-256 ${profile.sha256}`
    : "No profile selected for submission. Choose the fixed profile or explicitly record not_used.";
  for (const input of document.querySelectorAll("#profile-fields input")) {
    const permitted = enabled && (input.value !== "gender" || $("gender_required").checked);
    input.disabled = !permitted && !input.checked;
    const value = $(`profile-value-${input.value}`);
    if (input.value === "gender") value.textContent = permitted ? "male" : "Available only when service requires gender";
    $(`copy-profile-${input.value}`).disabled = !permitted;
  }
}
$("profile_id").addEventListener("change", profileUI);
$("gender_required").addEventListener("change", profileUI);
function interactionUI() {
  const initial = ["initial_prompt_only", "prompt_and_fixed_profile_only"].includes($("interaction_mode").value);
  const hasText = exactValue("exact_interaction") !== "";
  $("exact_interaction").required = !initial;
  $("interaction_record_type").disabled = initial && !hasText;
  if (initial && !hasText) $("interaction_record_type").value = "not_applicable";
  // Keep entered text visible if the researcher changes attribution; never silently drop it.
}
$("interaction_mode").addEventListener("change", interactionUI);
$("exact_interaction").addEventListener("input", interactionUI);
function guarded(action, opener) {
  if (!dirty) { action(); return; }
  pendingAction = action;
  guardOpener = opener;
  $("discard-dialog").showModal();
  $("keep").focus();
}
$("keep").onclick = () => $("discard-dialog").close();
$("discard").onclick = () => {
  const action = pendingAction;
  dirty = false;
  $("discard-dialog").close();
  action?.();
};
$("discard-dialog").addEventListener("close", () => {
  pendingAction = undefined;
  guardOpener?.focus();
});
$("capture").addEventListener("input", (event) => {
  if (!saved && event.target.id !== "prompt_id") dirty = true;
});
for (const id of ["timestamp", "timezone"]) $(id).addEventListener("input", () => { timeEdited = true; });
$("raw_response").addEventListener("paste", () => { if (!timeEdited) clock(); });
$("prompt_id").addEventListener("change", () => {
  const next = $("prompt_id").value;
  $("prompt_id").value = activePrompt.id;
  guarded(() => { reset(); setPrompt(next); }, $("prompt_id"));
});
for (const link of document.querySelectorAll('nav a[href^="/"]')) {
  link.addEventListener("click", (event) => {
    if (!dirty) return;
    event.preventDefault();
    guarded(() => { location.href = link.href; }, link);
  });
}
window.addEventListener("beforeunload", (event) => {
  if (dirty || correctionDirty) { event.preventDefault(); event.returnValue = ""; }
});
function reset() {
  $("capture").reset();
  verbatim.clear();
  for (const el of $("capture").querySelectorAll("input,select,textarea,button")) el.disabled = false;
  for (const el of document.querySelectorAll('[aria-invalid="true"]')) el.removeAttribute("aria-invalid");
  dirty = false; saved = false; timeEdited = false;
  setPrompt(activePrompt?.id || prompts[0].id);
  clock();
  profileUI();
  interactionUI();
  $("error").hidden = true;
  $("save-status").textContent = "Raw prompt and response become immutable after saving.";
}
$("another").onclick = () => guarded(() => { reset(); $("service_name").focus(); }, $("another"));
$("copy").onclick = async () => {
  try {
    await navigator.clipboard.writeText(activePrompt.text);
    announce("Exact consumer registry prompt copied.");
  } catch {
    $("prompt").focus(); $("prompt").select();
    announce("Clipboard unavailable. The registry prompt is selected; use Ctrl+C or your copy command.");
  }
};
function renderLedger() {
  $("saved-count").textContent = records.length;
  $("run-table").replaceChildren();
  for (const run of records) {
    const row = document.createElement("tr");
    const cell = document.createElement("td"), button = document.createElement("button");
    button.textContent = run.service_name;
    button.type = "button";
    if (detailRun?.run_id === run.run_id) detailOpener = button;
    button.addEventListener("click", () => openDetail(run.run_id, button));
    cell.append(button); row.append(cell);
    for (const value of [run.prompt_id, run.run_number, `${run.timestamp} · ${run.timezone}`, run.response_complete]) {
      const td = document.createElement("td"); td.textContent = value; row.append(td);
    }
    $("run-table").append(row);
  }
  $("table-empty").hidden = records.length > 0;
  $("table-empty").textContent = "No consumer captures saved yet. Choose a prompt and manually paste a service response above.";
  for (const button of document.querySelectorAll("[data-export]")) button.disabled = records.length === 0;
}
function metadata() {
  const result = { source_category: "consumer_astrology_service", run_number: Number($("run_number").value) };
  for (const key of metadataKeys) result[key] = $(key).value;
  for (const key of ["observed_model_label", "repeat_identity", "capture_note"]) {
    if (result[key] === "") result[key] = null;
  }
  result.personal_fields_requested = [...document.querySelectorAll('#personal-fields input:checked')].map((el) => el.value);
  return result;
}
$("capture").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (saved || saving || !activePrompt) return;
  saving = true;
  $("error").hidden = true;
  for (const el of document.querySelectorAll('[aria-invalid="true"]')) el.removeAttribute("aria-invalid");
  const button = $("save"); button.disabled = true; button.setAttribute("aria-busy", "true");
  $("save-status").textContent = "Saving capture…";
  try {
    const data = await api("runs", {
      prompt_id: activePrompt.id, registry_prompt_sha256: activePrompt.sha256,
      exact_prompt: exactValue("exact_prompt"),
      protocol_deviation: $("protocol_deviation").value === "" ? null : $("protocol_deviation").value,
      raw_response: exactValue("raw_response"), metadata: metadata(),
      profile_id: $("profile_id").value,
      profile_version: selectedProfile()?.snapshot.profile_version || null,
      profile_sha256: selectedProfile()?.sha256 || null,
      profile_fields_submitted: [...document.querySelectorAll("#profile-fields input:checked")].map((el) => el.value),
      gender_required: $("gender_required").checked,
      interaction_mode: $("interaction_mode").value,
      interaction_record_type: $("interaction_record_type").value,
      exact_interaction: exactValue("exact_interaction") === "" ? null : exactValue("exact_interaction"),
    });
    records = data.runs; dirty = false; saved = true;
    renderLedger();
    for (const el of $("capture").querySelectorAll("input,select,textarea,button")) el.disabled = true;
    $("another").disabled = false;
    $("save-status").textContent = "Saved. Raw evidence is locked; use Start another capture for the next run.";
    announce(`Consumer capture saved: ${data.run.run_id}`);
  } catch (exc) {
    error(`${exc.message} Your unsaved entries are retained.`);
    $("save-status").textContent = "Capture was not saved. Review the error and retry.";
    button.disabled = false;
  } finally { saving = false; button.removeAttribute("aria-busy"); }
});
function renderDetail(run) {
  detailRun = run;
  $("detail-prompt").textContent = run.exact_prompt;
  $("detail-response").textContent = run.raw_response;
  const scope = run.interaction_mode === "initial_prompt_only"
    ? "Researcher reported the initial prompt only, without profile inputs."
    : run.interaction_mode === "prompt_and_fixed_profile_only"
      ? "The final response uses the initial prompt and listed fixed synthetic profile inputs."
      : "Do not attribute the final response to the initial prompt alone.";
  $("detail-interaction-mode").textContent = `Interaction mode: ${run.interaction_mode}; record type: ${run.interaction_record_type}. ${scope}`;
  $("detail-interaction").textContent = run.exact_interaction === null ? "No additional interaction recorded." : run.exact_interaction;
  $("detail-record").textContent = JSON.stringify(run, null, 2);
}
async function openDetail(id, opener) {
  try {
    renderDetail(await api(`run?id=${encodeURIComponent(id)}`));
    detailOpener = opener;
    $("correction-form").hidden = true;
    correctionDirty = false;
    $("detail-dialog").showModal();
    $("detail-title").focus();
  } catch (exc) { error(exc.message); }
}
$("close-detail").onclick = () => {
  if (correctionDirty) {
    $("correction-error").textContent = "Save the revision or use Cancel metadata correction before closing.";
    $("corrected-meta").focus();
    return;
  }
  $("detail-dialog").close();
};
$("detail-dialog").addEventListener("cancel", (event) => {
  if (correctionDirty) { event.preventDefault(); $("close-detail").click(); }
});
$("detail-dialog").addEventListener("close", () => detailOpener?.focus());
$("correct").onclick = () => {
  if (!$("correction-form").hidden) { $("corrected-meta").focus(); return; }
  $("corrected-meta").value = JSON.stringify(detailRun.metadata, null, 2);
  $("correction-reason").value = "";
  $("correction-error").textContent = "";
  $("correction-form").hidden = false;
  $("corrected-meta").focus();
};
$("correction-form").addEventListener("input", () => { correctionDirty = true; });
$("cancel-revision").onclick = () => {
  correctionDirty = false; $("correction-form").hidden = true; $("correct").focus();
};
$("correction-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("save-revision"); button.disabled = true;
  for (const el of $("correction-form").querySelectorAll('[aria-invalid="true"]')) el.removeAttribute("aria-invalid");
  try {
    let revised;
    try { revised = JSON.parse($("corrected-meta").value); }
    catch { throw new Error("Correct the metadata JSON syntax and retry; entries are retained."); }
    const data = await api(`correction?id=${encodeURIComponent(detailRun.run_id)}`, {
      expected_revision: detailRun.history.length, reason: $("correction-reason").value, metadata: revised,
    });
    renderDetail(data.run); records = data.runs; renderLedger(); correctionDirty = false;
    $("correction-form").hidden = true; $("correct").focus();
    announce("Consumer metadata revision saved; raw prompt and response are unchanged.");
  } catch (exc) { $("correction-error").textContent = exc.message; }
  finally { button.disabled = false; }
});
async function download(format, id, button) {
  button.disabled = true; button.setAttribute("aria-busy", "true");
  try {
    const response = await fetch(`/api/consumer/export?format=${format}${id ? `&id=${encodeURIComponent(id)}` : ""}`, {
      headers: { "X-Collector-Token": token },
    });
    if (!response.ok) throw new Error((await response.json()).error);
    const blob = await response.blob(), url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url; link.download = `consumer-pilot-${id || new Date().toISOString().replace(/[:.]/g, "-")}.${format === "markdown" || format === "single" ? "md" : format}`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    announce("Consumer export downloaded with service names preserved.");
  } catch (exc) { error(`${exc.message} Retry the export after checking the local collector.`); }
  finally { button.disabled = false; button.removeAttribute("aria-busy"); }
}
for (const button of document.querySelectorAll("[data-export]")) button.onclick = () => download(button.dataset.export, null, button);
$("single-export").onclick = () => download("single", detailRun.run_id, $("single-export"));
async function bootstrap() {
  $("reload").disabled = true;
  try {
    const data = await api("bootstrap");
    if (!prompts.length) {
      prompts = data.prompts;
      profiles = data.profiles;
      for (const p of profiles) $("profile_id").append(new Option(`${p.snapshot.profile_id} · FICTIONAL / SYNTHETIC`, p.snapshot.profile_id));
      const profile = profiles[0].snapshot;
      $("profile-fields").replaceChildren(...data.profile_field_names.map((name) => {
        const row = document.createElement("div"), label = document.createElement("label");
        const input = document.createElement("input"), value = document.createElement("p");
        const copy = document.createElement("button");
        label.className = "check"; input.type = "checkbox"; input.value = name;
        label.append(input, document.createTextNode(`Submitted ${name}`));
        value.id = `profile-value-${name}`; value.className = "mono wrap";
        value.textContent = name === "gender" ? "Available only when service requires gender" : profile[name];
        copy.type = "button"; copy.id = `copy-profile-${name}`; copy.textContent = `Copy ${name}`;
        copy.onclick = async () => {
          try { await navigator.clipboard.writeText(profile[name]); announce(`Fixed synthetic ${name} copied. Mark it submitted only after actually supplying it.`); }
          catch { announce(`Clipboard unavailable. Copy the displayed fixed ${name} value manually.`); }
        };
        row.append(label, value, copy); return row;
      }));
      $("prompt_id").replaceChildren(...prompts.map((p) => new Option(p.id, p.id)));
      $("personal-fields").replaceChildren(...data.personal_field_names.map((name) => {
        const label = document.createElement("label"), input = document.createElement("input");
        label.className = "check"; input.type = "checkbox"; input.value = name;
        label.append(input, document.createTextNode(name)); return label;
      }));
      reset();
    }
    records = data.runs; renderLedger(); $("error").hidden = true;
    announce("Consumer ledger loaded.");
  } catch (exc) { error(`${exc.message} Use Refresh ledger to retry; form entries are retained.`); }
  finally { $("reload").disabled = false; }
}
$("reload").onclick = bootstrap;
bootstrap();
