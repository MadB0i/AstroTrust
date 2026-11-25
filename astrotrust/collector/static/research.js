"use strict";
const refresh = document.getElementById("refresh-status");
const notice = document.getElementById("status-notice");
const error = document.getElementById("status-error");
const token = document.querySelector('meta[name="collector-token"]').content;
const states = { captured: "Exploratory captures saved · analysis pending", pending: "Collection pending", unavailable: "Store unavailable", error: "Store verification failed" };
refresh.addEventListener("click", loadStatus);
async function loadStatus() {
  refresh.disabled = true;
  refresh.setAttribute("aria-busy", "true");
  notice.textContent = "Checking local evidence stores…";
  error.hidden = true;
  try {
    const response = await fetch("/api/research/status", { headers: { "X-Collector-Token": token }, signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error("Cannot load the evidence inventory. Reload this local page, then retry.");
    const data = await response.json();
    for (const arm of ["frontier", "consumer"]) {
      document.getElementById(`${arm}-count`).textContent = data[arm].captures ?? "—";
      document.getElementById(`${arm}-state`).textContent = states[data[arm].state] || "Status unknown";
    }
    notice.textContent = "Local inventory checked. Counts are collection records, not evaluation results.";
    if ([data.frontier, data.consumer].some(arm => arm.state === "error")) {
      throw new Error("One store could not be verified. Check its path and integrity before analysis, then refresh.");
    }
  } catch (failure) {
    // Previous values remain visible, but must not be mistaken for a fresh inventory.
    notice.textContent = "Inventory unavailable. Any previously displayed counts may be stale.";
    error.textContent = failure.name === "TimeoutError" ? "The local store check timed out. Check the server, then refresh evidence status." : failure.message;
    error.hidden = false;
  } finally {
    refresh.disabled = false;
    refresh.removeAttribute("aria-busy");
  }
}
loadStatus();
