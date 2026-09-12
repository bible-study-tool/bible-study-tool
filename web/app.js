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
  languagesPanel: $("#panel-languages"),
  main: $(".app-main"),
  paneDivider: $("#pane-divider"),
  readingPane: $("#reading-pane"),
  sidePane: $(".pane-side"),
  focusModeBtn: $("#focus-mode-btn"),
  exitZoomBtn: $("#exit-zoom-btn"),
  tabs: document.querySelectorAll(".tab"),
  openWizardBtn: $("#open-wizard-btn"),
  wizardModal: $("#setup-wizard-modal"),
  wizardCloseBtn: $("#wizard-close-btn"),
  wizardSkipBtn: $("#wizard-skip-btn"),
  wizardBackBtn: $("#wizard-back-btn"),
  wizardNextBtn: $("#wizard-next-btn"),
  wizardFinishBtn: $("#wizard-finish-btn"),
  autoUpdateToggle: $("#auto-update-toggle"),
  zebraToggle: $("#zebra-toggle"),
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
  let saved = null;
  try {
    saved = localStorage.getItem("abst.theme");
  } catch (_) {}
  const defaultTheme = data.default_theme || "sepia";
  const current = saved || defaultTheme;
  if (els.theme) {
    els.theme.innerHTML = "";
    for (const t of themeCatalog) {
      const opt = document.createElement("option");
      opt.value = t.id;
      opt.textContent = t.name;
      els.theme.appendChild(opt);
    }
  }
  if (!saved) {
    // Respect the OS preference on first visit; prefs win afterwards.
    setTheme(matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : defaultTheme);
  } else {
    setTheme(current);
  }
}

function setTheme(id) {
  if (!themeCatalog.some((t) => t.id === id)) id = "sepia";
  document.documentElement.dataset.theme = id;
  try {
    localStorage.setItem("abst.theme", id);
  } catch (_) {}
  if (els.theme) els.theme.value = id;
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
  const textSpan = document.createElement("span");
  textSpan.className = "verse-text";
  textSpan.textContent = v.text;
  item.appendChild(textSpan);
  // Lightweight Strong's markers show only when we have them (cursor: pointer).
  if (v.strongs_list && v.strongs_list.length) {
    const sup = document.createElement("sup");
    sup.className = "strongs strongs-tag";
    const rawCode = String(v.strongs_list[0]);
    const normCode = rawCode.startsWith("H") || rawCode.startsWith("G") ? rawCode : `H${rawCode}`;
    sup.textContent = ` ${normCode}`;
    sup.setAttribute("role", "button");
    sup.setAttribute("tabindex", "0");
    const labelText = `Inspect original-language nuances for ${normCode} (Verse ${v.verse})`;
    sup.title = labelText;
    sup.setAttribute("aria-label", labelText);
    const openNuance = () => {
      switchTab("languages");
      if (els.languagesPanel) {
        const targetCard = els.languagesPanel.querySelector(`details.morph-card[data-verse="${v.verse}"][data-strongs="${normCode}"]`) ||
                           els.languagesPanel.querySelector(`details.morph-card[data-strongs="${normCode}"]`) ||
                           els.languagesPanel.querySelector(`details.morph-card[data-verse="${v.verse}"]`);
        if (targetCard) {
          targetCard.open = true;
          targetCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }
    };
    sup.addEventListener("click", openNuance);
    sup.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openNuance();
      }
    });
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
  renderLanguages(p);
  els.hint.textContent = "";
  els.statusLeft.textContent = p.ref;
  els.input.value = p.ref;
}

function bindMasterToggle(panel, btnSelector, cardSelector) {
  const btn = panel.querySelector(btnSelector);
  if (!btn) return;
  btn.addEventListener("click", () => {
    const cards = panel.querySelectorAll(cardSelector);
    const anyClosed = Array.from(cards).some((c) => !c.open);
    cards.forEach((c) => { c.open = anyClosed; });
    btn.textContent = anyClosed ? "Collapse All" : "Expand All";
  });
}

function renderTranslations(pass) {
  if (!els.translationsPanel) return;
  const versesWithTranslations = pass.verses.filter(
    (v) => v.translations && Object.keys(v.translations).length > 0
  );

  if (!versesWithTranslations.length) {
    els.translationsPanel.innerHTML = `
      <div class="panel-toolbar">
        <span>Comparative Translations</span>
      </div>
      <p class="tab-hint">No comparative translations available for ${escapeHtml(pass.ref)}.</p>
    `;
    return;
  }

  const allInitiallyOpen = versesWithTranslations.length <= 1;
  const toolbar = `
    <div class="panel-toolbar">
      <span>Comparative Translations · ${versesWithTranslations.length} verse${versesWithTranslations.length === 1 ? "" : "s"}</span>
      <button type="button" class="btn-disclosure-toggle" id="toggle-all-translations">${allInitiallyOpen ? "Collapse All" : "Expand All"}</button>
    </div>
  `;

  const cards = versesWithTranslations.map((v, idx) => {
    const extra = Object.entries(v.translations || {});
    const lines = extra.map(([t, text]) => `
      <div class="translation-row">
        <span class="translation-badge">[${escapeHtml(t.toUpperCase())}]</span>
        <span class="translation-text">${escapeHtml(text)}</span>
      </div>
    `).join("");

    // First verse defaults to open; subsequent verses default to collapsed per progressive disclosure
    const isOpen = idx === 0 ? "open" : "";
    return `
      <details class="disclosure-card translation-card" ${isOpen}>
        <summary class="disclosure-summary">
          <span class="disclosure-arrow" aria-hidden="true">▸</span>
          <span class="verse-num">${v.verse}</span>
          <span class="translation-snippet">${escapeHtml(v.text.slice(0, 50))}${v.text.length > 50 ? "…" : ""}</span>
          <span class="translation-count-badge">${extra.length} versions</span>
        </summary>
        <div class="disclosure-body">
          ${lines}
        </div>
      </details>
    `;
  }).join("");

  els.translationsPanel.innerHTML = toolbar + cards;
  bindMasterToggle(els.translationsPanel, "#toggle-all-translations", "details.translation-card");
}

function renderLanguages(pass) {
  if (!els.languagesPanel) return;
  const versesWithNuances = pass.verses.filter(
    (v) => v.verbal_nuances && v.verbal_nuances.length > 0
  );

  if (!versesWithNuances.length) {
    els.languagesPanel.innerHTML = `
      <div class="panel-toolbar">
        <span>Original Languages</span>
      </div>
      <p class="tab-hint">No verbal nuances or morphological entries indexed for ${escapeHtml(pass.ref)}.</p>
    `;
    return;
  }

  const toolbar = `
    <div class="panel-toolbar">
      <span>Original Languages · ${versesWithNuances.length} verse${versesWithNuances.length === 1 ? "" : "s"}</span>
      <button type="button" class="btn-disclosure-toggle" id="toggle-all-languages">Expand All</button>
    </div>
  `;

  const sections = versesWithNuances.map((v) => {
    const nuances = v.verbal_nuances || [];

    const cards = nuances.map((n) => `
      <details class="disclosure-card morph-card" data-strongs="${escapeHtml(n.strongs)}" data-verse="${v.verse}">
        <summary class="disclosure-summary">
          <span class="disclosure-arrow" aria-hidden="true">▸</span>
          <span class="morph-surface">${escapeHtml(n.text || n.lemma)}</span>
          <span class="morph-lemma">(${escapeHtml(n.lemma)})</span>
          <span class="morph-stem-badge">${escapeHtml(n.stem_or_tense)}</span>
          <span class="morph-strongs-badge">${escapeHtml(n.strongs)}</span>
        </summary>
        <div class="disclosure-body">
          <div class="morph-summary-row">
            <span class="morph-plain-summary">${escapeHtml(n.plain_summary)}</span>
          </div>
          ${n.theological_nuance ? `
          <div class="morph-theological-card">
            <strong class="theological-label">Theological Nuance</strong>
            <p class="theological-text">${escapeHtml(n.theological_nuance)}</p>
          </div>` : ""}
          <div class="morph-details-grid">
            <div class="detail-item"><span class="detail-key">Aspect:</span> <span class="detail-val">${escapeHtml(n.aspect_meaning || "—")}</span></div>
            <div class="detail-item"><span class="detail-key">Voice:</span> <span class="detail-val">${escapeHtml(n.voice || "—")}</span></div>
            <div class="detail-item"><span class="detail-key">Code:</span> <code class="detail-code">${escapeHtml(n.morph_code)}</code></div>
            <div class="detail-item"><span class="detail-key">Gloss:</span> <em class="detail-val">${escapeHtml(n.gloss || "—")}</em></div>
          </div>
        </div>
      </details>
    `).join("");

    return `
      <div class="verse-language-group">
        <div class="verse-language-header">
          <span class="verse-num">${v.verse}</span>
          <span class="verse-language-snippet">${escapeHtml(v.text.slice(0, 50))}${v.text.length > 50 ? "…" : ""}</span>
        </div>
        ${cards}
      </div>
    `;
  }).join("");

  els.languagesPanel.innerHTML = toolbar + sections;
  bindMasterToggle(els.languagesPanel, "#toggle-all-languages", "details.morph-card");
}

function showError(message) {
  els.statusLeft.textContent = "error";
  els.hint.textContent = message;
  els.verses.innerHTML = "";
  if (els.translationsPanel) els.translationsPanel.innerHTML = "<p class='tab-hint'>No data.</p>";
  if (els.languagesPanel) els.languagesPanel.innerHTML = "<p class='tab-hint'>No data.</p>";
}

/* small escaping helper (never trust fetched text into innerHTML unescaped) */
function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* ---- navigation ---- */

async function navigate(ref) {
  try {
    const pass = await api(`/api/passage?ref=${encodeURIComponent(ref)}&eager=1`);
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

function openWizard(initialStep = 1) {
  if (els.wizardModal && typeof els.wizardModal.showModal === "function") {
    if (!els.wizardModal.open) {
      els.wizardModal.showModal();
    }
    const targetStep = typeof initialStep === "number" ? initialStep : 1;
    setWizardStep(targetStep);
    if (targetStep === 1) {
      verifyBundle();
    }
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

function initZebraShading() {
  if (!els.zebraToggle || !els.verses) return;
  let saved = null;
  try {
    saved = localStorage.getItem("abst.zebra_shading");
  } catch (_) {}
  const isEnabled = saved === "true";
  els.zebraToggle.checked = isEnabled;
  els.verses.classList.toggle("zebra-shading", isEnabled);

  els.zebraToggle.addEventListener("change", () => {
    const enabled = els.zebraToggle.checked;
    els.verses.classList.toggle("zebra-shading", enabled);
    try {
      localStorage.setItem("abst.zebra_shading", String(enabled));
    } catch (_) {}
  });
}

/* ---- Split Pane Resizer (ADR-025 / WP-030 Phase 1) ---- */

const DEFAULT_SPLIT = 65;
const MIN_SPLIT = 40;
const MAX_SPLIT = 80;

function setSplit(percent, persist = true) {
  if (!els.main || !els.paneDivider) return;
  percent = Math.min(MAX_SPLIT, Math.max(MIN_SPLIT, percent));
  els.main.style.setProperty("--split-percent", `${percent.toFixed(2)}%`);
  els.paneDivider.setAttribute("aria-valuenow", String(Math.round(percent)));
  if (persist) {
    try {
      localStorage.setItem("abst.split_percent", percent.toFixed(2));
    } catch (_) {}
  }
}

function resetSplit() {
  if (!els.main || !els.paneDivider) return;
  els.main.style.removeProperty("--split-percent");
  els.paneDivider.setAttribute("aria-valuenow", String(DEFAULT_SPLIT));
  try {
    localStorage.removeItem("abst.split_percent");
  } catch (_) {}
}

function initPaneResizer() {
  if (!els.main || !els.paneDivider) return;

  try {
    const saved = parseFloat(localStorage.getItem("abst.split_percent"));
    if (!isNaN(saved) && saved >= MIN_SPLIT && saved <= MAX_SPLIT) {
      setSplit(saved, false);
    }
  } catch (_) {}

  let isDragging = false;
  let dragRect = null;

  els.paneDivider.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return; // Primary mouse button only
    isDragging = true;
    dragRect = els.main.getBoundingClientRect();
    try {
      els.paneDivider.setPointerCapture(e.pointerId);
    } catch (_) {}
    els.main.classList.add("is-resizing");
    document.body.style.userSelect = "none";
  });

  els.paneDivider.addEventListener("pointermove", (e) => {
    if (!isDragging || !dragRect || dragRect.width <= 0) return;
    const percent = ((e.clientX - dragRect.left) / dragRect.width) * 100;
    setSplit(percent, false); // Performance: no synchronous localStorage in frame loop
  });

  const stopDrag = (e) => {
    if (!isDragging) return;
    isDragging = false;
    dragRect = null;
    try {
      els.paneDivider.releasePointerCapture(e.pointerId);
    } catch (_) {}
    els.main.classList.remove("is-resizing");
    document.body.style.removeProperty("user-select");

    // Persist final position once upon drag completion
    const current = parseFloat(els.main.style.getPropertyValue("--split-percent"));
    if (!isNaN(current)) {
      try {
        localStorage.setItem("abst.split_percent", current.toFixed(2));
      } catch (_) {}
    }
  };

  els.paneDivider.addEventListener("pointerup", stopDrag);
  els.paneDivider.addEventListener("pointercancel", stopDrag);

  els.paneDivider.addEventListener("dblclick", () => {
    resetSplit();
  });

  // WAI-ARIA APG compliant separator keyboard navigation
  els.paneDivider.addEventListener("keydown", (e) => {
    const current = parseFloat(els.main.style.getPropertyValue("--split-percent")) || DEFAULT_SPLIT;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      setSplit(current - 2, true);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      setSplit(current + 2, true);
    } else if (e.key === "Home") {
      e.preventDefault();
      setSplit(MIN_SPLIT, true);
    } else if (e.key === "End") {
      e.preventDefault();
      setSplit(MAX_SPLIT, true);
    } else if (e.key === "Enter") {
      e.preventDefault();
      resetSplit();
    }
  });
}

/* ---- Focus & Panel Zoom Modes (ADR-025 / WP-030 Phase 2) ---- */

function isInputFocused() {
  const el = document.activeElement;
  if (!el) return false;
  const tag = el.tagName ? el.tagName.toLowerCase() : "";
  return tag === "input" || tag === "textarea" || tag === "select" || el.isContentEditable;
}

function restoreStatusBar() {
  if (els.statusLeft && els.title) {
    els.statusLeft.textContent = els.title.textContent || "";
  }
}

function toggleFocusMode(forceState) {
  if (!els.main) return;
  const shouldFocus = forceState !== undefined ? forceState : !els.main.classList.contains("focus-mode");
  if (shouldFocus) {
    els.main.classList.remove("zoom-side");
    if (els.exitZoomBtn) els.exitZoomBtn.hidden = true;
    els.main.classList.add("focus-mode");
    if (els.focusModeBtn) {
      els.focusModeBtn.setAttribute("aria-pressed", "true");
      els.focusModeBtn.title = "Exit Scripture Focus Mode (f or Esc)";
    }
    if (els.statusLeft) {
      els.statusLeft.textContent = "Focus Mode active — press 'f' or Esc to restore panels";
    }
  } else {
    els.main.classList.remove("focus-mode");
    if (els.focusModeBtn) {
      els.focusModeBtn.setAttribute("aria-pressed", "false");
      els.focusModeBtn.title = "Toggle Scripture Focus Mode (f)";
    }
    restoreStatusBar();
  }
}

function toggleSideZoom(forceState) {
  if (!els.main) return;
  const shouldZoom = forceState !== undefined ? forceState : !els.main.classList.contains("zoom-side");
  if (shouldZoom) {
    els.main.classList.remove("focus-mode");
    if (els.focusModeBtn) {
      els.focusModeBtn.setAttribute("aria-pressed", "false");
      els.focusModeBtn.title = "Toggle Scripture Focus Mode (f)";
    }
    els.main.classList.add("zoom-side");
    if (els.exitZoomBtn) els.exitZoomBtn.hidden = false;
    if (els.statusLeft) {
      els.statusLeft.textContent = "Panel Zoom active — press 'z' or Esc to restore split";
    }
  } else {
    els.main.classList.remove("zoom-side");
    if (els.exitZoomBtn) els.exitZoomBtn.hidden = true;
    restoreStatusBar();
  }
}

function exitDistractionFreeModes() {
  if (!els.main) return;
  const wasActive = els.main.classList.contains("focus-mode") || els.main.classList.contains("zoom-side");
  if (!wasActive) return;
  els.main.classList.remove("focus-mode");
  els.main.classList.remove("zoom-side");
  if (els.focusModeBtn) {
    els.focusModeBtn.setAttribute("aria-pressed", "false");
    els.focusModeBtn.title = "Toggle Scripture Focus Mode (f)";
  }
  if (els.exitZoomBtn) els.exitZoomBtn.hidden = true;
  restoreStatusBar();
}

function initFocusAndZoomModes() {
  if (els.focusModeBtn) {
    els.focusModeBtn.addEventListener("click", () => toggleFocusMode());
  }

  if (els.exitZoomBtn) {
    els.exitZoomBtn.addEventListener("click", () => exitDistractionFreeModes());
  }

  // Double-clicking any study tab toggles full-width side workstation
  for (const tab of els.tabs) {
    tab.addEventListener("dblclick", (e) => {
      e.preventDefault();
      toggleSideZoom();
    });
  }

  // Global keyboard shortcut dispatcher with input focus guard
  window.addEventListener("keydown", (e) => {
    // If wizard modal is open, do not intercept single-key navigation
    if (els.wizardModal && els.wizardModal.open) return;

    // Guard: ignore single-key shortcuts while typing in editable elements
    if (isInputFocused()) {
      if (e.key === "Escape") {
        document.activeElement.blur();
      }
      return;
    }

    // Ignore if browser modifier keys (Ctrl/Meta/Alt) are held
    if (e.ctrlKey || e.metaKey || e.altKey) return;

    // 'f' or 'F' without Shift: toggle Scripture Focus Mode
    if (!e.shiftKey && (e.key === "f" || e.key === "F")) {
      e.preventDefault();
      toggleFocusMode();
      return;
    }

    // 'z' or 'Z' OR Shift + 'F' / 'f': toggle Panel Zoom
    if ((e.key === "z" || e.key === "Z") || (e.shiftKey && (e.key === "f" || e.key === "F"))) {
      e.preventDefault();
      const inSidePane = els.sidePane && els.sidePane.contains(document.activeElement);
      const isCurrentlyZoomed = els.main && (els.main.classList.contains("zoom-side") || els.main.classList.contains("focus-mode"));
      if (isCurrentlyZoomed) {
        exitDistractionFreeModes();
      } else if (inSidePane) {
        toggleSideZoom(true);
      } else {
        toggleFocusMode(true);
      }
      return;
    }

    // Escape: exit any active distraction-free mode
    if (e.key === "Escape") {
      if (els.main && (els.main.classList.contains("focus-mode") || els.main.classList.contains("zoom-side"))) {
        e.preventDefault();
        exitDistractionFreeModes();
      }
    }
  });
}

/* ---- wiring ---- */

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const ref = els.input.value.trim();
  if (ref) navigate(ref);
});

if (els.theme) els.theme.addEventListener("change", () => setTheme(els.theme.value));

els.prev.disabled = true; // wired when the API exposes next/prev (Phase 0 +)
els.next.disabled = true;

function switchTab(tabName) {
  for (const t of els.tabs) {
    t.setAttribute("aria-selected", String(t.dataset.tab === tabName));
  }
  document.querySelectorAll(".tab-body").forEach((body) => {
    body.hidden = body.id !== `panel-${tabName}`;
  });
}

for (const tab of els.tabs) {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
}

if (els.openWizardBtn) {
  els.openWizardBtn.addEventListener("click", () => {
    let completed = false;
    try {
      completed = localStorage.getItem("abst.setup_completed") === "true";
    } catch (_) {}
    openWizard(completed ? 2 : 1);
  });
}
if (els.wizardCloseBtn) els.wizardCloseBtn.addEventListener("click", closeWizard);
if (els.wizardSkipBtn) els.wizardSkipBtn.addEventListener("click", completeWizard);
if (els.wizardFinishBtn) els.wizardFinishBtn.addEventListener("click", completeWizard);
if (els.wizardBackBtn) els.wizardBackBtn.addEventListener("click", () => setWizardStep(currentWizardStep - 1));
if (els.wizardNextBtn) els.wizardNextBtn.addEventListener("click", () => setWizardStep(currentWizardStep + 1));

initPaneResizer();
initFocusAndZoomModes();
initAutoUpdate();
initZebraShading();
let setupCompleted = false;
try {
  setupCompleted = localStorage.getItem("abst.setup_completed") === "true";
} catch (_) {}
if (!setupCompleted) {
  openWizard();
}

const urlParams = new URLSearchParams(window.location.search);
const initialRef = urlParams.get("ref") || "Genesis 1:1-3";
loadThemes().then(() => navigate(initialRef)).catch((err) => {
  showError("Engine not reachable — is the local server running? " + err.message);
});