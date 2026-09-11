/* Adventist Bible Study Tool — frontend logic (no build step, no deps).
 *
 * Talks to the local engine over fetch() JSON (ADR-024 Phase 1 channel).
 * Everything here is self-contained vanilla JS so the same files serve in a
 * browser tab now and inside a Tauri frame later.
 */
"use strict";

const $ = (sel) => document.querySelector(sel);

const els = {
  form: $("#ref-form"),
  input: $("#ref-input"),
  go: $("#go-btn"),
  prev: $("#prev-btn"),
  next: $("#next-btn"),
  theme: $("#theme-select"),
  title: $("#passage-title"),
  subtitle: $("#passage-subtitle"),
  verses: $("#verses"),
  hint: $("#status-hint"),
  statusLeft: $("#status-left"),
  statusRight: $("#status-right"),
  translationsPanel: $("#panel-translations"),
  tabs: document.querySelectorAll(".tab"),
  openWizardBtn: $("#open-wizard-btn"),
  wizardModal: $("#setup-wizard-modal"),
  wizardCloseBtn: $("#wizard-close-btn"),
  wizardSkipBtn: $("#wizard-skip-btn"),
  wizardBackBtn: $("#wizard-back-btn"),
  wizardNextBtn: $("#wizard-next-btn"),
  wizardFinishBtn: $("#wizard-finish-btn"),
  autoUpdateToggle: $("#auto-update-toggle"),
  verifyStatusIcon: $("#verify-status-icon"),
  verifyStatusText: $("#verify-status-text"),
  verifyErrorBox: $("#verify-error-box"),
  egwStatusMsg: $("#egw-status-msg"),
  wizardSteps: document.querySelectorAll(".wizard-step"),
  stepIndicators: document.querySelectorAll(".step-indicator"),
};

/* ---- Theme management (design tokens via [data-theme], ADR-024 §4) ---- */

let themeCatalog = [];
let currentWizardStep = 1;
let egwAvailable = false;

async function loadThemes() {
  const data = await api("/api/health");
  themeCatalog = data.themes || [];
  egwAvailable = !!data.egw_available;
  updateEgwStatus();
  const saved = localStorage.getItem("abst.theme");
  const current = saved || data.default_theme || "light";
  els.theme.innerHTML = "";
  for (const t of themeCatalog) {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.name;
    els.theme.appendChild(opt);
  }
  if (!saved) {
    // Respect the OS preference on first visit; prefs win afterwards.
    setTheme(matchMedia("(prefers-color-scheme: dark)").matches ? "transparent" : "light");
  } else {
    setTheme(current);
  }
}

function setTheme(id) {
  if (!themeCatalog.some((t) => t.id === id)) id = "light";
  document.documentElement.dataset.theme = id;
  localStorage.setItem("abst.theme", id);
  els.theme.value = id;
  els.statusRight.textContent = `theme: ${id}`;
}

/* ---- tiny fetch helper ---- */

async function api(path) {
  const res = await fetch(path);
  let data = null;
  try { data = await res.json(); } catch (_e) { /* non-JSON error body */ }
  if (!res.ok) {
    throw new Error((data && data.error) || `request failed (${res.status})`);
  }
  return data;
}

/* ---- rendering ---- */

function renderVerse(v) {
  const item = document.createElement("p");
  item.className = "verse-item";
  const num = document.createElement("span");
  num.className = "verse-num";
  num.textContent = `${v.verse}`;
  item.appendChild(num);
  item.appendChild(document.createTextNode(v.text));
  // Lightweight Strong's markers show only when we have them (cursor: help).
  if (v.strongs_list && v.strongs_list.length) {
    const sup = document.createElement("sup");
    sup.className = "strongs";
    sup.textContent = ` H${v.strongs_list[0]}`;
    item.appendChild(sup);
  }
  return item;
}

function renderPassage(p) {
  els.title.textContent = p.ref;
  els.subtitle.textContent =
    `${p.book_name} — ${p.start_chapter}:${p.start_verse}–${p.end_chapter}:${p.end_verse}` +
    (p.verses.length ? ` · ${p.verses.length} verse${p.verses.length === 1 ? "" : "s"}` : "");
  els.verses.innerHTML = "";
  for (const v of p.verses) els.verses.appendChild(renderVerse(v));
  renderTranslations(p);
  els.hint.textContent = "";
  els.statusLeft.textContent = p.ref;
  els.input.value = p.ref;
}

function renderTranslations(pass) {
  const panels = pass.verses.slice(0, 12).map((v) => {
    const extra = Object.entries(v.translations || {});
    if (!extra.length) return `<p class="tab-hint">No additional translations for verse ${v.verse}.</p>`;
    const lines = extra.map(
      ([t, text]) => `<p><strong>[${escapeHtml(t)}]</strong> ${escapeHtml(text)}</p>`
    ).join("");
    return `<div class="verse-extra"><span class="verse-num">${v.verse}</span>${lines}</div>`;
  }).join("");
  els.translationsPanel.innerHTML = panels || "<p class='tab-hint'>Loading…</p>";
}

function showError(message) {
  els.statusLeft.textContent = "error";
  els.hint.textContent = message;
  els.verses.innerHTML = "";
  els.translationsPanel.innerHTML = "<p class='tab-hint'>No data.</p>";
}

/* small escaping helper (never trust fetched text into innerHTML unescaped) */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* ---- navigation ---- */

async function navigate(ref) {
  try {
    const pass = await api(`/api/passage?ref=${encodeURIComponent(ref)}&eager=0`);
    renderPassage(pass);
  } catch (err) {
    showError(String(err.message || err));
  }
}

/* ---- Setup Wizard (WP-029 Phase 4) ---- */

function updateEgwStatus() {
  if (!els.egwStatusMsg) return;
  if (egwAvailable) {
    els.egwStatusMsg.innerHTML = "<strong>Status:</strong> Historical commentary database (<code>egw.db</code>) is active and available.";
  } else {
    els.egwStatusMsg.innerHTML = "<strong>Status:</strong> Commentary database is not pre-bundled to keep distribution packages clean.";
  }
}

function setWizardStep(step) {
  currentWizardStep = Math.max(1, Math.min(4, step));
  els.wizardSteps.forEach((s, idx) => {
    s.hidden = (idx + 1) !== currentWizardStep;
  });
  els.stepIndicators.forEach((ind, idx) => {
    const stepNum = idx + 1;
    ind.classList.remove("active", "completed");
    if (stepNum === currentWizardStep) {
      ind.classList.add("active");
      ind.setAttribute("aria-current", "step");
    } else {
      ind.removeAttribute("aria-current");
      if (stepNum < currentWizardStep) {
        ind.classList.add("completed");
      }
    }
  });

  if (els.wizardBackBtn) els.wizardBackBtn.hidden = currentWizardStep === 1;
  if (currentWizardStep === 4) {
    if (els.wizardNextBtn) els.wizardNextBtn.hidden = true;
    if (els.wizardFinishBtn) {
      els.wizardFinishBtn.hidden = false;
      els.wizardFinishBtn.focus();
    }
  } else {
    if (els.wizardNextBtn) els.wizardNextBtn.hidden = false;
    if (els.wizardFinishBtn) els.wizardFinishBtn.hidden = true;
  }
}

async function verifyBundle() {
  if (!els.verifyStatusIcon || !els.verifyStatusText) return;
  els.verifyStatusIcon.className = "verify-icon status-pending";
  els.verifyStatusIcon.innerHTML = "&#9679;";
  els.verifyStatusText.textContent = "Verifying sidecar data bundle (SHA256SUMS)…";
  if (els.verifyErrorBox) {
    els.verifyErrorBox.hidden = true;
    els.verifyErrorBox.textContent = "";
  }

  try {
    const res = await api("/api/verify-bundle");
    if (res.valid) {
      els.verifyStatusIcon.className = "verify-icon status-success";
      els.verifyStatusIcon.innerHTML = "&#10004;";
      els.verifyStatusText.textContent = "All databases and lexicons cryptographically verified ✔";
    } else {
      els.verifyStatusIcon.className = "verify-icon status-error";
      els.verifyStatusIcon.innerHTML = "&#9888;";
      els.verifyStatusText.textContent = "Data bundle verification encountered issues:";
      if (els.verifyErrorBox) {
        els.verifyErrorBox.hidden = false;
        els.verifyErrorBox.textContent = (res.errors || []).join("\n") || "Checksum mismatch detected.";
      }
    }
  } catch (err) {
    els.verifyStatusIcon.className = "verify-icon status-error";
    els.verifyStatusIcon.innerHTML = "&#9888;";
    els.verifyStatusText.textContent = "Unable to verify data bundle: " + (err.message || err);
  }
}

function openWizard() {
  if (els.wizardModal && typeof els.wizardModal.showModal === "function") {
    if (!els.wizardModal.open) {
      els.wizardModal.showModal();
    }
    setWizardStep(1);
    verifyBundle();
  }
}

function closeWizard() {
  if (els.wizardModal && typeof els.wizardModal.close === "function") {
    if (els.wizardModal.open) {
      els.wizardModal.close();
    }
  }
}

function completeWizard() {
  try {
    localStorage.setItem("abst.setup_completed", "true");
  } catch (_) {
    /* ignore storage errors in restricted contexts */
  }
  closeWizard();
}

function initAutoUpdate() {
  if (!els.autoUpdateToggle) return;
  let saved = null;
  try {
    saved = localStorage.getItem("abst.auto_update");
  } catch (_) {}
  if (saved !== null) {
    els.autoUpdateToggle.checked = saved === "true";
  } else {
    els.autoUpdateToggle.checked = true;
    try {
      localStorage.setItem("abst.auto_update", "true");
    } catch (_) {}
  }
  els.autoUpdateToggle.addEventListener("change", () => {
    try {
      localStorage.setItem("abst.auto_update", String(els.autoUpdateToggle.checked));
    } catch (_) {}
  });
}

/* ---- wiring ---- */

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const ref = els.input.value.trim();
  if (ref) navigate(ref);
});

els.theme.addEventListener("change", () => setTheme(els.theme.value));

els.prev.disabled = true; // wired when the API exposes next/prev (Phase 0 +)
els.next.disabled = true;

for (const tab of els.tabs) {
  tab.addEventListener("click", () => {
    for (const t of els.tabs) t.setAttribute("aria-selected", String(t === tab));
    document.querySelectorAll(".tab-body").forEach((body) => {
      body.hidden = body.id !== `panel-${tab.dataset.tab}`;
    });
  });
}

if (els.openWizardBtn) els.openWizardBtn.addEventListener("click", openWizard);
if (els.wizardCloseBtn) els.wizardCloseBtn.addEventListener("click", closeWizard);
if (els.wizardSkipBtn) els.wizardSkipBtn.addEventListener("click", completeWizard);
if (els.wizardFinishBtn) els.wizardFinishBtn.addEventListener("click", completeWizard);
if (els.wizardBackBtn) els.wizardBackBtn.addEventListener("click", () => setWizardStep(currentWizardStep - 1));
if (els.wizardNextBtn) els.wizardNextBtn.addEventListener("click", () => setWizardStep(currentWizardStep + 1));

initAutoUpdate();
if (!localStorage.getItem("abst.setup_completed")) {
  openWizard();
}

const urlParams = new URLSearchParams(window.location.search);
const initialRef = urlParams.get("ref") || "Genesis 1:1-3";
loadThemes().then(() => navigate(initialRef)).catch((err) => {
  showError("Engine not reachable — is the local server running? " + err.message);
});