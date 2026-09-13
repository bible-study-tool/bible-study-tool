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
  prophecyPanel: $("#panel-prophecy"),
  tabProphecy: document.querySelector("button.tab[data-tab='prophecy']"),
  prophecySearchInput: $("#prophecy-search-input"),
  prophecyCategoryFilter: $("#prophecy-category-filter"),
  prophecyBookFilter: $("#prophecy-book-filter"),
  prophecyResetBtn: $("#prophecy-reset-btn"),
  prophecyCountBadge: $("#prophecy-count-badge"),
  prophecyZoomBtn: $("#prophecy-zoom-btn"),
  prophecyInContext: $("#prophecy-in-context"),
  prophecyTableBody: $("#prophecy-table-body"),
  prophecyEmptyState: $("#prophecy-empty-state"),
  sanctuaryPanel: $("#panel-sanctuary"),
  tabSanctuary: document.querySelector("button.tab[data-tab='sanctuary']"),
  sanctuaryStageSlider: $("#sanctuary-stage-slider"),
  sanctuaryStageBtns: document.querySelectorAll(".sanctuary-stage-btn"),
  sanctuaryStageBadge: $("#sanctuary-stage-badge"),
  sanctuaryZoomBtn: $("#sanctuary-zoom-btn"),
  sanctuarySvg: $("#sanctuary-svg"),
  sanctuaryDetailCard: $("#sanctuary-detail-card"),
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

function createRefChip(ref, className = "prophecy-ref-link") {
  const link = document.createElement("button");
  link.type = "button";
  link.className = className;
  link.textContent = ref;
  link.title = `Read ${ref} in Scripture view`;
  link.addEventListener("click", () => {
    if (els.input) els.input.value = ref;
    navigate(ref);
    if (els.main && els.main.classList.contains("zoom-side")) {
      toggleSideZoom(false);
    }
  });
  return link;
}

function highlightProphecySymbolInLexicon(symbolId) {
  if (els.main && els.main.classList.contains("focus-mode")) {
    toggleFocusMode(false);
  }
  switchTab("prophecy");
  let targetRow = $(`#prophecy-row-${symbolId}`);
  if (!targetRow) {
    resetProphecyFilters();
    targetRow = $(`#prophecy-row-${symbolId}`);
  }
  if (targetRow) {
    document.querySelectorAll(".prophecy-table tr.highlight-symbol").forEach((r) => r.classList.remove("highlight-symbol"));
    targetRow.classList.add("highlight-symbol");
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    targetRow.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth", block: "center" });
    setTimeout(() => targetRow.classList.remove("highlight-symbol"), 3000);
  }
}

function toggleProphecyInlineCard(verseItem, v, sym, badgeBtn) {
  const cardId = `prophecy-card-${v.verse}-${sym.id}`;
  const existingCard = verseItem.querySelector(`.prophecy-inline-card[data-symbol-id="${sym.id}"]`);
  if (existingCard) {
    existingCard.remove();
    badgeBtn.setAttribute("aria-expanded", "false");
    badgeBtn.classList.remove("badge-active");
    return;
  }

  // Close any other open cards in this verse
  verseItem.querySelectorAll(".prophecy-inline-card").forEach((c) => c.remove());
  verseItem.querySelectorAll(".prophecy-verse-badge").forEach((b) => {
    b.setAttribute("aria-expanded", "false");
    b.classList.remove("badge-active");
  });

  badgeBtn.setAttribute("aria-expanded", "true");
  badgeBtn.classList.add("badge-active");

  const card = document.createElement("div");
  card.className = "prophecy-inline-card";
  card.id = cardId;
  card.dataset.symbolId = sym.id;
  card.setAttribute("role", "region");
  card.setAttribute("aria-label", `Prophetic symbol definition for ${sym.symbol}`);

  const catLower = (sym.category || "").toLowerCase();
  const isKey = sym.is_proof && !sym.is_anchor;

  card.innerHTML = `
    <div class="prophecy-card-header">
      <div class="prophecy-card-title-group">
        <span class="prophecy-card-icon" aria-hidden="true">◈</span>
        <strong class="prophecy-card-title">${escapeHtml(sym.symbol)}</strong>
        <span class="category-badge cat-${catLower}">${escapeHtml(sym.category)}</span>
        <span class="prophecy-card-role-tag">${isKey ? "Defining Key / Proof Text" : "Apocalyptic Anchor"}</span>
      </div>
      <button type="button" class="prophecy-card-close" aria-label="Close card" title="Close card (Esc)">✕</button>
    </div>

    <div class="prophecy-card-section">
      <span class="prophecy-card-label">Biblical Meaning:</span>
      <div class="prophecy-card-meaning">${escapeHtml(sym.meaning)}</div>
    </div>

    <div class="prophecy-card-section">
      <span class="prophecy-card-label">Primary Proof Texts (Defining Passages):</span>
      <div class="prophecy-card-refs prophecy-card-proofs"></div>
    </div>

    ${(sym.canonical_anchors && sym.canonical_anchors.length > 0) ? `
      <div class="prophecy-card-section">
        <span class="prophecy-card-label">Apocalyptic Anchors:</span>
        <div class="prophecy-card-refs prophecy-card-anchors"></div>
      </div>
    ` : ""}

    ${sym.sda_consensus ? `
      <details class="prophecy-card-consensus">
        <summary class="prophecy-consensus-summary">Historical Consensus</summary>
        <div class="prophecy-consensus-body">${escapeHtml(sym.sda_consensus)}</div>
      </details>
    ` : ""}

    <div class="prophecy-card-footer">
      <button type="button" class="btn-tool btn-goto-lexicon">View in Prophetic Lexicon ➔</button>
    </div>
  `;

  // Attach close listener
  const closeBtn = card.querySelector(".prophecy-card-close");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      card.remove();
      badgeBtn.setAttribute("aria-expanded", "false");
      badgeBtn.classList.remove("badge-active");
      badgeBtn.focus();
    });
  }

  // Populate proof text ref chips
  const proofsContainer = card.querySelector(".prophecy-card-proofs");
  if (proofsContainer) {
    for (const ref of (sym.proof_texts || [])) {
      proofsContainer.appendChild(createRefChip(ref));
    }
  }

  // Populate anchor ref chips
  const anchorsContainer = card.querySelector(".prophecy-card-anchors");
  if (anchorsContainer) {
    for (const ref of (sym.canonical_anchors || [])) {
      anchorsContainer.appendChild(createRefChip(ref));
    }
  }

  // Attach Go to Lexicon button
  const gotoLexiconBtn = card.querySelector(".btn-goto-lexicon");
  if (gotoLexiconBtn) {
    gotoLexiconBtn.addEventListener("click", () => highlightProphecySymbolInLexicon(sym.id));
  }

  verseItem.appendChild(card);
}

function renderVerse(v) {
  const item = document.createElement("div");
  item.className = "verse-item";
  item.dataset.verse = String(v.verse);
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

  // Canonical prophetic symbol badges
  if (v.prophetic_symbols && v.prophetic_symbols.length > 0) {
    const badgesSpan = document.createElement("span");
    badgesSpan.className = "verse-prophecy-badges";
    for (const sym of v.prophetic_symbols) {
      const badge = document.createElement("button");
      badge.type = "button";
      const catLower = (sym.category || "").toLowerCase();
      badge.className = `prophecy-verse-badge cat-${catLower}`;
      badge.dataset.symbolId = sym.id;
      badge.dataset.verse = String(v.verse);
      badge.title = `${sym.symbol} (${sym.category}): ${sym.meaning} — Click to inspect in-context definition`;
      badge.setAttribute("aria-expanded", "false");
      badge.setAttribute("aria-controls", `prophecy-card-${v.verse}-${sym.id}`);
      badge.setAttribute("aria-label", `Prophetic symbol: ${sym.symbol}`);

      badge.innerHTML = `
        <span class="badge-icon" aria-hidden="true">◈</span>
        <span class="badge-name">${escapeHtml(sym.symbol)}</span>
        ${sym.is_proof && !sym.is_anchor ? '<span class="badge-proof-label">Key</span>' : ''}
      `;

      badge.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleProphecyInlineCard(item, v, sym, badge);
      });

      badgesSpan.appendChild(badge);
    }
    item.appendChild(badgesSpan);
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
  if (els.prophecyInContext) {
    els.prophecyInContext.hidden = true;
    els.prophecyInContext.innerHTML = "";
  }
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
    updateProphecyInContext(pass.ref);
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
    if (els.prophecyZoomBtn) els.prophecyZoomBtn.textContent = "⤡ Split View";
    if (els.sanctuaryZoomBtn) els.sanctuaryZoomBtn.textContent = "⤡ Split View";
    if (els.statusLeft) {
      els.statusLeft.textContent = "Panel Zoom active — press 'z' or Esc to restore split";
    }
  } else {
    els.main.classList.remove("zoom-side");
    if (els.exitZoomBtn) els.exitZoomBtn.hidden = true;
    if (els.prophecyZoomBtn) els.prophecyZoomBtn.textContent = "⤢ Maximize";
    if (els.sanctuaryZoomBtn) els.sanctuaryZoomBtn.textContent = "⤢ Maximize";
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
  if (els.prophecyZoomBtn) els.prophecyZoomBtn.textContent = "⤢ Maximize";
  if (els.sanctuaryZoomBtn) els.sanctuaryZoomBtn.textContent = "⤢ Maximize";
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

    // Escape: close open inline cards or exit any active distraction-free mode
    if (e.key === "Escape") {
      const openCard = document.querySelector(".prophecy-inline-card");
      if (openCard) {
        e.preventDefault();
        const symbolId = openCard.dataset.symbolId;
        const parentVerse = openCard.closest(".verse-item");
        openCard.remove();
        if (parentVerse) {
          const badge = parentVerse.querySelector(`.prophecy-verse-badge[data-symbol-id="${symbolId}"]`);
          if (badge) {
            badge.setAttribute("aria-expanded", "false");
            badge.classList.remove("badge-active");
            badge.focus();
          }
        }
        return;
      }
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


/* ---- Master Prophetic Key Table Workstation (WP-031 Phase 3) ---- */

let cachedPropheticLexicon = null;
let currentProphecyPassageRef = null;

async function loadPropheticLexicon() {
  try {
    const data = await api("/api/prophetic");
    // Precompute searchable string on load for zero-allocation real-time filtering
    for (const s of (data.symbols || [])) {
      s._searchable = [
        s.symbol || "",
        s.meaning || "",
        s.category || "",
        ...(s.books || []),
        s.sda_consensus || "",
        ...(s.proof_texts || []),
        ...(s.canonical_anchors || []),
        ...(s.strongs || []),
      ].join(" ").toLowerCase();
    }
    cachedPropheticLexicon = data;
    renderProphecyTable(data.symbols);
  } catch (err) {
    if (els.prophecyTableBody) {
      els.prophecyTableBody.innerHTML = `<tr><td colspan="4" class="tab-hint">Cannot load prophetic lexicon: ${escapeHtml(err.message)}</td></tr>`;
    }
  }
}

function renderProphecyTable(symbols) {
  if (!els.prophecyTableBody) return;
  els.prophecyTableBody.innerHTML = "";

  if (!symbols || symbols.length === 0) {
    if (els.prophecyEmptyState) els.prophecyEmptyState.hidden = false;
    if (els.prophecyCountBadge) els.prophecyCountBadge.textContent = "0 symbols";
    return;
  }

  if (els.prophecyEmptyState) els.prophecyEmptyState.hidden = true;
  if (els.prophecyCountBadge) {
    els.prophecyCountBadge.textContent = `${symbols.length} symbol${symbols.length === 1 ? "" : "s"}`;
  }

  const fragment = document.createDocumentFragment();

  for (const s of symbols) {
    const tr = document.createElement("tr");
    tr.id = `prophecy-row-${s.id}`;
    tr.dataset.symbolId = s.id;

    // 1. Symbol column
    const tdSymbol = document.createElement("td");
    tdSymbol.className = "prophecy-col-symbol";

    const headerDiv = document.createElement("div");
    headerDiv.className = "symbol-header";

    const nameSpan = document.createElement("span");
    nameSpan.className = "symbol-name";
    nameSpan.textContent = s.symbol;
    headerDiv.appendChild(nameSpan);

    const catBadge = document.createElement("span");
    const catLower = (s.category || "").toLowerCase();
    catBadge.className = `category-badge cat-${catLower}`;
    catBadge.textContent = s.category;
    headerDiv.appendChild(catBadge);

    tdSymbol.appendChild(headerDiv);

    // Strong's codes
    if (s.strongs && s.strongs.length > 0) {
      const strongsDiv = document.createElement("div");
      strongsDiv.className = "symbol-strongs";
      for (const code of s.strongs) {
        const strongsBtn = document.createElement("button");
        strongsBtn.type = "button";
        strongsBtn.className = "prophecy-strongs-tag";
        strongsBtn.textContent = code;
        strongsBtn.title = `Inspect ${code} in Languages tab`;
        strongsBtn.addEventListener("click", () => {
          switchTab("languages");
          if (els.languagesPanel) {
            const targetCard = els.languagesPanel.querySelector(`details.morph-card[data-strongs="${code}"]`);
            if (targetCard) {
              targetCard.open = true;
              targetCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
          }
        });
        strongsDiv.appendChild(strongsBtn);
      }
      tdSymbol.appendChild(strongsDiv);
    }

    // Historical consensus
    if (s.sda_consensus) {
      const consensusDetails = document.createElement("details");
      consensusDetails.className = "prophecy-consensus-details";
      consensusDetails.innerHTML = `
        <summary class="prophecy-consensus-summary">Historical Consensus</summary>
        <div class="prophecy-consensus-body">${escapeHtml(s.sda_consensus)}</div>
      `;
      tdSymbol.appendChild(consensusDetails);
    }

    // 2. Meaning column
    const tdMeaning = document.createElement("td");
    tdMeaning.className = "prophecy-col-meaning";
    const meaningDiv = document.createElement("div");
    meaningDiv.className = "symbol-meaning";
    meaningDiv.textContent = s.meaning;
    tdMeaning.appendChild(meaningDiv);

    if (s.books && s.books.length > 0) {
      const booksDiv = document.createElement("div");
      booksDiv.className = "symbol-books";
      for (const b of s.books) {
        const bSpan = document.createElement("span");
        bSpan.className = "prophecy-book-tag";
        bSpan.textContent = b;
        booksDiv.appendChild(bSpan);
      }
      tdMeaning.appendChild(booksDiv);
    }

    // 3. Proof Texts column
    const tdProofs = document.createElement("td");
    tdProofs.className = "prophecy-col-proofs";
    const proofsList = document.createElement("div");
    proofsList.className = "prophecy-ref-list";
    for (const ref of (s.proof_texts || [])) {
      proofsList.appendChild(createRefChip(ref));
    }
    tdProofs.appendChild(proofsList);

    // 4. Apocalyptic Anchors column
    const tdAnchors = document.createElement("td");
    tdAnchors.className = "prophecy-col-anchors";
    const anchorsList = document.createElement("div");
    anchorsList.className = "prophecy-ref-list";
    for (const ref of (s.canonical_anchors || [])) {
      anchorsList.appendChild(createRefChip(ref));
    }
    tdAnchors.appendChild(anchorsList);

    tr.appendChild(tdSymbol);
    tr.appendChild(tdMeaning);
    tr.appendChild(tdProofs);
    tr.appendChild(tdAnchors);
    fragment.appendChild(tr);
  }

  els.prophecyTableBody.appendChild(fragment);
}

function filterProphecySymbols() {
  if (!cachedPropheticLexicon) return;
  const q = (els.prophecySearchInput ? els.prophecySearchInput.value : "").trim().toLowerCase();
  const cat = (els.prophecyCategoryFilter ? els.prophecyCategoryFilter.value : "").trim();
  const book = (els.prophecyBookFilter ? els.prophecyBookFilter.value : "").trim().toLowerCase();

  const qTerms = q ? q.split(/\s+/) : [];

  const filtered = (cachedPropheticLexicon.symbols || []).filter((s) => {
    if (cat && s.category !== cat) return false;
    if (book && !(s.books || []).some((b) => (b || "").toLowerCase() === book)) return false;
    if (qTerms.length > 0) {
      const searchable = s._searchable || [
        s.symbol || "",
        s.meaning || "",
        s.category || "",
        ...(s.books || []),
        s.sda_consensus || "",
        ...(s.proof_texts || []),
        ...(s.canonical_anchors || []),
        ...(s.strongs || []),
      ].join(" ").toLowerCase();
      if (!qTerms.every((term) => searchable.includes(term))) {
        return false;
      }
    }
    return true;
  });

  renderProphecyTable(filtered);
}

function resetProphecyFilters() {
  if (els.prophecySearchInput) els.prophecySearchInput.value = "";
  if (els.prophecyCategoryFilter) els.prophecyCategoryFilter.value = "";
  if (els.prophecyBookFilter) els.prophecyBookFilter.value = "";
  filterProphecySymbols();
}

async function updateProphecyInContext(passageRef) {
  if (!els.prophecyInContext || !passageRef) return;
  currentProphecyPassageRef = passageRef;
  try {
    const data = await api(`/api/prophetic?ref=${encodeURIComponent(passageRef)}`);
    if (currentProphecyPassageRef !== passageRef) return; // Discard stale out-of-order response
    const matched = data.symbols || [];
    if (matched.length > 0) {
      els.prophecyInContext.hidden = false;
      els.prophecyInContext.innerHTML = `
        <div class="prophecy-in-context-header">In-Context Symbols for <strong>${escapeHtml(passageRef)}</strong> (${matched.length}):</div>
        <div class="prophecy-in-context-tags">
          ${matched.map((s) => `
            <button type="button" class="prophecy-context-tag" data-symbol-id="${escapeHtml(s.id)}" title="${escapeHtml(s.meaning || "")}">
              ${escapeHtml(s.symbol)} <span class="category-badge cat-${(s.category || "").toLowerCase()}">${escapeHtml(s.category || "")}</span>
            </button>
          `).join("")}
        </div>
      `;
      els.prophecyInContext.querySelectorAll(".prophecy-context-tag").forEach((btn) => {
        btn.addEventListener("click", () => {
          highlightProphecySymbolInLexicon(btn.dataset.symbolId);
        });
      });
      if (els.tabProphecy) {
        els.tabProphecy.innerHTML = `Prophecy <span class="prophecy-count-badge tab-count-badge">${matched.length}</span>`;
      }
    } else {
      els.prophecyInContext.hidden = true;
      els.prophecyInContext.innerHTML = "";
      if (els.tabProphecy) {
        els.tabProphecy.textContent = "Prophecy";
      }
    }
  } catch (_e) {
    // Fail soft if offline or error
  }
}

function initProphecyWorkstation() {
  if (els.prophecySearchInput) els.prophecySearchInput.addEventListener("input", filterProphecySymbols);
  if (els.prophecyCategoryFilter) els.prophecyCategoryFilter.addEventListener("change", filterProphecySymbols);
  if (els.prophecyBookFilter) els.prophecyBookFilter.addEventListener("change", filterProphecySymbols);
  if (els.prophecyResetBtn) els.prophecyResetBtn.addEventListener("click", resetProphecyFilters);
  if (els.prophecyZoomBtn) {
    els.prophecyZoomBtn.addEventListener("click", () => toggleSideZoom());
  }
  loadPropheticLexicon();
}


/* ---- Sanctuary Typology Blueprint & Plan of Salvation Workstation (WP-032) ---- */

let cachedSanctuaryData = null;
let activeSanctuaryStage = 0; // 0 = All, 1 = Cross, 2 = Intercession, 3 = 1844 Judgment, 4 = Consummation
let selectedSanctuaryStationId = null;
const SANCTUARY_STATION_ORDER = [
  "altar_of_burnt_offering",
  "laver",
  "table_of_shewbread",
  "golden_lampstand",
  "altar_of_incense",
  "ark_of_the_covenant",
];

const createSanctuaryRefChip = (ref) => createRefChip(ref, "sanctuary-ref-chip");

function renderSanctuaryOverview() {
  if (!els.sanctuaryDetailCard) return;
  els.sanctuaryDetailCard.innerHTML = `
    <div class="sanctuary-card-header">
      <div class="sanctuary-card-title-group">
        <h3 class="sanctuary-card-title">The Sanctuary: Blueprint of the Plan of Salvation</h3>
        <div class="sanctuary-card-hebrew">
          <strong>מִקְדָּשׁ (Miqdash)</strong> — <em>"And let them make me a sanctuary; that I may dwell among them." (Exodus 25:8)</em>
        </div>
      </div>
      <span class="badge-compartment comp-holy_place">Fundamental Belief #24</span>
    </div>

    <div class="sanctuary-reality-callout">
      <span class="sanctuary-reality-label">The Central Doctrine</span>
      <p class="sanctuary-reality-text">"The scripture which above all others had been both the foundation and the central pillar of the advent faith was the declaration: 'Unto two thousand and three hundred days; then shall the sanctuary be cleansed.'" (The Great Controversy, p. 409)</p>
    </div>

    <div class="sanctuary-section">
      <span class="sanctuary-section-label">Spatial &amp; Chronological Progression</span>
      <p class="sanctuary-section-text">
        The Hebrew Tabernacle is God's pedagogical diagram of redemption across three spatial spheres and four chronological stages:
        <br><strong>1. Courtyard (Earth):</strong> Justification by faith through Christ's unrepeatable sacrifice at the Cross (AD 31) and regeneration (Laver).
        <br><strong>2. Holy Place (Heavenly Sanctuary):</strong> Christ's ongoing high-priestly mediation, daily intercession, and the ministry of the Spirit and Word (AD 31–1844).
        <br><strong>3. Most Holy Place (Heavenly Throne):</strong> The final cleansing of the sanctuary, antitypical Day of Atonement, and Investigative Judgment (1844+).
      </p>
    </div>

    <div class="sanctuary-section">
      <span class="sanctuary-section-label">How to Study</span>
      <p class="sanctuary-section-text">
        Click any sacred furniture station on the blueprint or use the <strong>Plan of Salvation</strong> timeline slider above to trace salvation history from the Cross to the Earth Made New. Click any Scripture reference to jump directly to the biblical text.
      </p>
    </div>
  `;
}

function renderSanctuaryStationDetail(s) {
  if (!els.sanctuaryDetailCard) return;
  const comp = cachedSanctuaryData && cachedSanctuaryData.compartments.find((c) => c.id === s.compartment);
  const compName = comp ? comp.name : s.compartment;

  els.sanctuaryDetailCard.innerHTML = `
    <div class="sanctuary-card-header">
      <div class="sanctuary-card-title-group">
        <h3 class="sanctuary-card-title">${escapeHtml(s.name)} (${escapeHtml(s.common_name)})</h3>
        <div class="sanctuary-card-hebrew">
          <strong>${escapeHtml(s.hebrew_name)}</strong> — <em>${escapeHtml(s.transliteration)}</em>
          ${(s.strongs || []).map(sc => `<button type="button" class="sanctuary-strongs-chip" data-strongs="${escapeHtml(sc)}">${escapeHtml(sc)}</button>`).join(" ")}
        </div>
      </div>
      <span class="badge-compartment comp-${escapeHtml(s.compartment)}">${escapeHtml(compName)}</span>
    </div>

    <div class="sanctuary-reality-callout">
      <span class="sanctuary-reality-label">Spiritual Reality</span>
      <p class="sanctuary-reality-text">${escapeHtml(s.spiritual_reality)}</p>
    </div>

    <div class="sanctuary-section">
      <span class="sanctuary-section-label">Theological Meaning</span>
      <p class="sanctuary-section-text">${escapeHtml(s.theological_meaning)}</p>
    </div>

    <div class="sanctuary-section">
      <span class="sanctuary-section-label">Priestly Service &amp; Daily/Yearly Ministry</span>
      <p class="sanctuary-section-text">${escapeHtml(s.priestly_service)}</p>
    </div>

    <div class="sanctuary-section">
      <span class="sanctuary-section-label">Sacred Materials &amp; Position</span>
      <p class="sanctuary-section-text">${escapeHtml(s.materials)}. <em>${escapeHtml(s.position)}</em></p>
    </div>

    <div class="sanctuary-consensus-quote">
      <strong>Adventist Theological Consensus:</strong>
      <p style="margin: 4px 0 0 0;">${escapeHtml(s.sda_consensus)}</p>
    </div>

    <div class="sanctuary-ref-grid">
      <div class="sanctuary-ref-column">
        <span class="sanctuary-section-label">Old Testament Types &amp; Institution</span>
        <div class="sanctuary-ref-chips" id="sanctuary-ot-chips"></div>
      </div>
      <div class="sanctuary-ref-column">
        <span class="sanctuary-section-label">New Testament Fulfillment (Antitype)</span>
        <div class="sanctuary-ref-chips" id="sanctuary-nt-chips"></div>
      </div>
    </div>
  `;

  // Wire Strong's chips
  els.sanctuaryDetailCard.querySelectorAll(".sanctuary-strongs-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchTab("languages");
      const morphCard = document.querySelector(`.morph-card[data-strongs="${btn.dataset.strongs}"]`);
      if (morphCard) {
        morphCard.open = true;
        morphCard.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
  });

  // Wire Scripture chips
  const otWrap = els.sanctuaryDetailCard.querySelector("#sanctuary-ot-chips");
  if (otWrap && s.ot_passages) {
    for (const ref of s.ot_passages) {
      otWrap.appendChild(createSanctuaryRefChip(ref));
    }
  }

  const ntWrap = els.sanctuaryDetailCard.querySelector("#sanctuary-nt-chips");
  if (ntWrap && s.nt_fulfillment) {
    for (const ref of s.nt_fulfillment) {
      ntWrap.appendChild(createSanctuaryRefChip(ref));
    }
  }
}

function renderSanctuaryStageDetail(stageNumber) {
  if (!els.sanctuaryDetailCard) return;
  if (stageNumber === 0) {
    renderSanctuaryOverview();
    return;
  }
  if (!cachedSanctuaryData || !cachedSanctuaryData.plan_of_salvation) return;
  const phase = cachedSanctuaryData.plan_of_salvation.find((p) => p.stage_number === stageNumber);
  if (!phase) return;

  els.sanctuaryDetailCard.innerHTML = `
    <div class="sanctuary-card-header">
      <div class="sanctuary-card-title-group">
        <h3 class="sanctuary-card-title">Stage ${phase.stage_number}: ${escapeHtml(phase.title)}</h3>
        <div class="sanctuary-card-hebrew">
          <strong>Prophetic Timeline:</strong> <em>${escapeHtml(phase.prophetic_time)}</em>
        </div>
      </div>
      <span class="badge-compartment comp-${escapeHtml(phase.symbolic_compartment || 'courtyard')}">Stage ${phase.stage_number}</span>
    </div>

    <div class="sanctuary-reality-callout">
      <span class="sanctuary-reality-label">Historical Event</span>
      <p class="sanctuary-reality-text">${escapeHtml(phase.historical_event)}</p>
    </div>

    <div class="sanctuary-section">
      <span class="sanctuary-section-label">Theological Significance</span>
      <p class="sanctuary-section-text">${escapeHtml(phase.theological_significance)}</p>
    </div>

    ${phase.symbolic_furniture && phase.symbolic_furniture.length > 0 ? `
      <div class="sanctuary-section">
        <span class="sanctuary-section-label">Associated Sacred Furniture Articles</span>
        <div class="sanctuary-ref-chips" id="sanctuary-phase-furniture-chips"></div>
      </div>
    ` : ""}

    <div class="sanctuary-section">
      <span class="sanctuary-section-label">Scriptural Anchors &amp; Prophetic Keys</span>
      <div class="sanctuary-ref-chips" id="sanctuary-stage-anchors"></div>
    </div>
  `;

  if (phase.symbolic_furniture && phase.symbolic_furniture.length > 0) {
    const furnWrap = els.sanctuaryDetailCard.querySelector("#sanctuary-phase-furniture-chips");
    if (furnWrap) {
      for (const stId of phase.symbolic_furniture) {
        const st = cachedSanctuaryData.stations.find((s) => s.id === stId);
        if (st) {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "sanctuary-ref-chip";
          btn.textContent = `Inspect ${st.common_name}`;
          btn.addEventListener("click", () => selectSanctuaryStation(st.id));
          furnWrap.appendChild(btn);
        }
      }
    }
  }

  const anchorWrap = els.sanctuaryDetailCard.querySelector("#sanctuary-stage-anchors");
  if (anchorWrap && phase.biblical_anchors) {
    for (const ref of phase.biblical_anchors) {
      anchorWrap.appendChild(createSanctuaryRefChip(ref));
    }
  }
}

function selectSanctuaryStation(stationId) {
  selectedSanctuaryStationId = stationId;
  document.querySelectorAll(".sanctuary-station-node").forEach((node) => {
    const isSelected = node.dataset.stationId === stationId;
    node.classList.toggle("selected", isSelected);
    node.setAttribute("aria-pressed", String(isSelected));
  });

  if (!cachedSanctuaryData) return;
  const st = cachedSanctuaryData.stations.find((s) => s.id === stationId);
  if (st) {
    renderSanctuaryStationDetail(st);
  }
}

function setPlanOfSalvationStage(stageNumber) {
  activeSanctuaryStage = stageNumber;
  selectedSanctuaryStationId = null;
  document.querySelectorAll(".sanctuary-station-node").forEach((node) => {
    node.classList.remove("selected");
    node.setAttribute("aria-pressed", "false");
  });

  if (els.sanctuaryStageSlider) els.sanctuaryStageSlider.value = stageNumber;

  els.sanctuaryStageBtns.forEach((btn) => {
    const isActive = parseInt(btn.dataset.stage, 10) === stageNumber;
    btn.classList.toggle("active", isActive);
    btn.setAttribute("aria-pressed", String(isActive));
  });

  const stageLabels = [
    "Full Tabernacle Blueprint",
    "Stage 1: AD 31 Cross — Justification",
    "Stage 2: Heavenly Intercession",
    "Stage 3: 1844 Investigative Judgment",
    "Stage 4: Consummation — Earth Made New",
  ];
  if (els.sanctuaryStageBadge) {
    els.sanctuaryStageBadge.textContent = stageLabels[stageNumber] || "Sanctuary Blueprint";
  }

  // Update station highlighting / dimming
  const stageStations = {
    0: SANCTUARY_STATION_ORDER,
    1: ["altar_of_burnt_offering", "laver"],
    2: ["table_of_shewbread", "golden_lampstand", "altar_of_incense"],
    3: ["ark_of_the_covenant"],
    4: SANCTUARY_STATION_ORDER,
  };

  const activeSet = new Set(stageStations[stageNumber] || SANCTUARY_STATION_ORDER);

  document.querySelectorAll(".sanctuary-station-node").forEach((node) => {
    const isStageMember = activeSet.has(node.dataset.stationId);
    if (stageNumber === 0 || stageNumber === 4) {
      node.classList.remove("is-dimmed");
      node.classList.add("is-highlighted");
    } else {
      node.classList.toggle("is-dimmed", !isStageMember);
      node.classList.toggle("is-highlighted", isStageMember);
    }
  });

  // Update salvation path geometry
  const pathEl = document.querySelector("#svg-salvation-path");
  if (pathEl) {
    const paths = {
      0: "M 60,250 L 180,250 L 340,250 L 470,250 L 550,250 L 660,250 L 730,250 L 800,250",
      1: "M 60,250 L 180,250 L 340,250",
      2: "M 60,250 L 180,250 L 340,250 L 470,250 L 550,250 L 660,250",
      3: "M 60,250 L 180,250 L 340,250 L 470,250 L 550,250 L 660,250 L 730,250 L 800,250",
      4: "M 60,250 L 180,250 L 340,250 L 470,250 L 550,250 L 660,250 L 730,250 L 800,250",
    };
    pathEl.setAttribute("d", paths[stageNumber] || paths[0]);
    pathEl.style.opacity = stageNumber === 0 ? "0.55" : "0.9";
  }

  // Display stage details
  renderSanctuaryStageDetail(stageNumber);
}

function cycleSanctuaryStation(delta) {
  let currentIndex = SANCTUARY_STATION_ORDER.indexOf(selectedSanctuaryStationId);
  let nextIndex;
  if (currentIndex === -1) {
    nextIndex = delta > 0 ? 0 : SANCTUARY_STATION_ORDER.length - 1;
  } else {
    nextIndex = (currentIndex + delta + SANCTUARY_STATION_ORDER.length) % SANCTUARY_STATION_ORDER.length;
  }
  const nextId = SANCTUARY_STATION_ORDER[nextIndex];
  selectSanctuaryStation(nextId);
  const nextNode = document.querySelector(`#station-${nextId}`);
  if (nextNode) nextNode.focus();
}

function renderSanctuaryBlueprint(data) {
  if (!els.sanctuarySvg) return;

  // Build bronze perimeter fence posts
  let fencePosts = "";
  for (let x = 60; x <= 940; x += 80) {
    fencePosts += `<circle class="svg-courtyard-post" cx="${x}" cy="40" r="3" />`;
    fencePosts += `<circle class="svg-courtyard-post" cx="${x}" cy="460" r="3" />`;
  }
  for (let y = 40; y <= 460; y += 70) {
    if (y < 170 || y > 330) {
      fencePosts += `<circle class="svg-courtyard-post" cx="60" cy="${y}" r="3" />`;
    }
    fencePosts += `<circle class="svg-courtyard-post" cx="940" cy="${y}" r="3" />`;
  }

  els.sanctuarySvg.innerHTML = `
    <defs>
      <marker id="salvation-marker" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
        <path d="M 0,1 L 5,3 L 0,5 Z" fill="var(--secondary)" />
      </marker>
    </defs>

    <!-- Courtyard Ground & Boundary Fence -->
    <rect class="svg-bg-courtyard" x="60" y="40" width="880" height="420" rx="6" />
    <rect class="svg-courtyard-fence" x="60" y="40" width="880" height="420" rx="6" />
    ${fencePosts}

    <!-- Gate of the Courtyard (East Screen) -->
    <line class="svg-gate-screen" x1="60" y1="170" x2="60" y2="330" />

    <!-- Cardinal Orientation Labels -->
    <text class="svg-orient-text" x="40" y="254" transform="rotate(-90 40 254)">EAST (ENTRANCE)</text>
    <text class="svg-orient-text" x="500" y="26">NORTH</text>
    <text class="svg-orient-text" x="500" y="482">SOUTH</text>
    <text class="svg-orient-text" x="965" y="254" transform="rotate(90 965 254)">WEST</text>

    <!-- Courtyard Label -->
    <text class="svg-compartment-text" x="80" y="70">COURTYARD (EARTH / JUSTIFICATION)</text>

    <!-- Tabernacle Tent Outer Wall & Chambers -->
    <rect class="svg-tent-outer" x="470" y="120" width="400" height="260" rx="4" />

    <!-- Holy Place Chamber -->
    <rect class="svg-holy-place" x="470" y="120" width="260" height="260" />
    <text class="svg-compartment-text" x="485" y="142">HOLY PLACE (SANCTIFICATION / DAILY)</text>

    <!-- Holy Place Door Veil -->
    <line class="svg-tent-door" x1="470" y1="170" x2="470" y2="330" />

    <!-- The Veil (Katapetasma) -->
    <line class="svg-veil" x1="730" y1="120" x2="730" y2="380" />

    <!-- Most Holy Place Chamber -->
    <rect class="svg-most-holy-place" x="730" y="120" width="140" height="260" />
    <text class="svg-compartment-text" x="742" y="142">MOST HOLY</text>
    <text class="svg-compartment-text" x="742" y="156" style="font-size: 9px;">(YEARLY / 1844)</text>

    <!-- Directional Salvation Path -->
    <path id="svg-salvation-path" class="svg-salvation-path" marker-end="url(#salvation-marker)"
          d="M 60,250 L 180,250 L 340,250 L 470,250 L 550,250 L 660,250 L 730,250 L 800,250" />

    <!-- Sacred Furniture Stations -->
    <g id="sanctuary-stations-group">
      <!-- 1. Altar of Burnt Offering (Courtyard) -->
      <g class="sanctuary-station-node" id="station-altar_of_burnt_offering" data-station-id="altar_of_burnt_offering"
         role="button" tabindex="0" aria-pressed="false" aria-label="Altar of Burnt Offering: The Cross of Christ &amp; Justification">
        <rect class="station-halo" x="135" y="205" width="90" height="90" rx="6" />
        <rect class="furniture-bronze" x="145" y="215" width="70" height="70" rx="2" />
        <polygon class="furniture-bronze" points="145,215 139,207 148,215" />
        <polygon class="furniture-bronze" points="215,215 221,207 215,223" />
        <polygon class="furniture-bronze" points="145,285 139,293 153,285" />
        <polygon class="furniture-bronze" points="215,285 221,293 207,285" />
        <rect class="furniture-grate" x="156" y="226" width="48" height="48" fill="none" />
        <line class="furniture-grate" x1="168" y1="226" x2="168" y2="274" />
        <line class="furniture-grate" x1="180" y1="226" x2="180" y2="274" />
        <line class="furniture-grate" x1="192" y1="226" x2="192" y2="274" />
        <line class="furniture-grate" x1="156" y1="238" x2="204" y2="238" />
        <line class="furniture-grate" x1="156" y1="250" x2="204" y2="250" />
        <line class="furniture-grate" x1="156" y1="262" x2="204" y2="262" />
        <text class="station-label" x="180" y="318">Brazen Altar</text>
        <text class="station-sublabel" x="180" y="332">Mizbach Ha'olah</text>
      </g>

      <!-- 2. Brazen Laver (Courtyard) -->
      <g class="sanctuary-station-node" id="station-laver" data-station-id="laver"
         role="button" tabindex="0" aria-pressed="false" aria-label="Brazen Laver: Cleansing, Regeneration &amp; Baptism">
        <circle class="station-halo" cx="340" cy="250" r="42" />
        <circle class="furniture-bronze" cx="340" cy="250" r="30" />
        <circle class="furniture-water" cx="340" cy="250" r="22" />
        <circle cx="340" cy="250" r="12" fill="none" stroke="#244b6e" stroke-width="0.8" stroke-dasharray="3 2" />
        <text class="station-label" x="340" y="318">The Laver</text>
        <text class="station-sublabel" x="340" y="332">Kiyyor Nechoshet</text>
      </g>

      <!-- 3. Table of Shewbread (Holy Place - North) -->
      <g class="sanctuary-station-node" id="station-table_of_shewbread" data-station-id="table_of_shewbread"
         role="button" tabindex="0" aria-pressed="false" aria-label="Table of Shewbread: Christ the Bread of Life &amp; Word of God">
        <rect class="station-halo" x="510" y="145" width="80" height="70" rx="6" />
        <rect class="furniture-gold" x="520" y="155" width="60" height="40" rx="2" />
        <rect x="523" y="158" width="54" height="34" fill="none" stroke="#735712" stroke-width="0.8" stroke-dasharray="2 1" />
        <!-- 12 loaves in 2 rows of 6 -->
        <circle cx="528" cy="168" r="3" fill="#8c6218" />
        <circle cx="536" cy="168" r="3" fill="#8c6218" />
        <circle cx="544" cy="168" r="3" fill="#8c6218" />
        <circle cx="552" cy="168" r="3" fill="#8c6218" />
        <circle cx="560" cy="168" r="3" fill="#8c6218" />
        <circle cx="568" cy="168" r="3" fill="#8c6218" />
        <circle cx="528" cy="182" r="3" fill="#8c6218" />
        <circle cx="536" cy="182" r="3" fill="#8c6218" />
        <circle cx="544" cy="182" r="3" fill="#8c6218" />
        <circle cx="552" cy="182" r="3" fill="#8c6218" />
        <circle cx="560" cy="182" r="3" fill="#8c6218" />
        <circle cx="568" cy="182" r="3" fill="#8c6218" />
        <text class="station-label" x="550" y="210">Shewbread Table</text>
        <text class="station-sublabel" x="550" y="222">Lechem Happanim</text>
      </g>

      <!-- 4. Golden Lampstand (Holy Place - South) -->
      <g class="sanctuary-station-node" id="station-golden_lampstand" data-station-id="golden_lampstand"
         role="button" tabindex="0" aria-pressed="false" aria-label="Golden Lampstand (Menorah): The Holy Spirit &amp; Light of the World">
        <rect class="station-halo" x="510" y="285" width="80" height="75" rx="6" />
        <line x1="535" y1="340" x2="565" y2="340" stroke="#735712" stroke-width="2.5" stroke-linecap="round" />
        <line x1="550" y1="340" x2="550" y2="300" stroke="#735712" stroke-width="2.5" />
        <path d="M 550,330 Q 550,314 542,302" fill="none" stroke="#735712" stroke-width="1.8" />
        <path d="M 550,330 Q 550,314 558,302" fill="none" stroke="#735712" stroke-width="1.8" />
        <path d="M 550,324 Q 550,310 534,302" fill="none" stroke="#735712" stroke-width="1.8" />
        <path d="M 550,324 Q 550,310 566,302" fill="none" stroke="#735712" stroke-width="1.8" />
        <path d="M 550,318 Q 550,306 524,302" fill="none" stroke="#735712" stroke-width="1.8" />
        <path d="M 550,318 Q 550,306 576,302" fill="none" stroke="#735712" stroke-width="1.8" />
        <!-- 7 lamps and flames -->
        <ellipse cx="524" cy="301" rx="2.5" ry="1.5" class="furniture-gold" />
        <ellipse cx="534" cy="301" rx="2.5" ry="1.5" class="furniture-gold" />
        <ellipse cx="542" cy="301" rx="2.5" ry="1.5" class="furniture-gold" />
        <ellipse cx="550" cy="301" rx="2.5" ry="1.5" class="furniture-gold" />
        <ellipse cx="558" cy="301" rx="2.5" ry="1.5" class="furniture-gold" />
        <ellipse cx="566" cy="301" rx="2.5" ry="1.5" class="furniture-gold" />
        <ellipse cx="576" cy="301" rx="2.5" ry="1.5" class="furniture-gold" />
        <circle cx="524" cy="296" r="2" class="furniture-flame" />
        <circle cx="534" cy="296" r="2" class="furniture-flame" />
        <circle cx="542" cy="296" r="2" class="furniture-flame" />
        <circle cx="550" cy="296" r="2" class="furniture-flame" />
        <circle cx="558" cy="296" r="2" class="furniture-flame" />
        <circle cx="566" cy="296" r="2" class="furniture-flame" />
        <circle cx="576" cy="296" r="2" class="furniture-flame" />
        <text class="station-label" x="550" y="354">Golden Lampstand</text>
        <text class="station-sublabel" x="550" y="366">Menorah</text>
      </g>

      <!-- 5. Altar of Incense (Holy Place - Before the Veil) -->
      <g class="sanctuary-station-node" id="station-altar_of_incense" data-station-id="altar_of_incense"
         role="button" tabindex="0" aria-pressed="false" aria-label="Altar of Incense: Continual Intercession &amp; Merits of Christ">
        <rect class="station-halo" x="630" y="218" width="60" height="64" rx="6" />
        <rect class="furniture-gold" x="640" y="228" width="40" height="40" rx="2" />
        <polygon class="furniture-gold" points="640,228 637,223 644,228" />
        <polygon class="furniture-gold" points="680,228 683,223 676,228" />
        <polygon class="furniture-gold" points="640,268 637,273 644,268" />
        <polygon class="furniture-gold" points="680,268 683,273 676,268" />
        <path class="furniture-incense-vapor" d="M 655,232 Q 652,224 656,218 T 653,208" />
        <path class="furniture-incense-vapor" d="M 665,232 Q 668,224 664,218 T 667,208" />
        <text class="station-label" x="660" y="284">Altar of Incense</text>
        <text class="station-sublabel" x="660" y="296">Mizbach Haqqetoret</text>
      </g>

      <!-- 6. Ark of the Covenant & Mercy Seat (Most Holy Place) -->
      <g class="sanctuary-station-node" id="station-ark_of_the_covenant" data-station-id="ark_of_the_covenant"
         role="button" tabindex="0" aria-pressed="false" aria-label="Ark of the Covenant &amp; Mercy Seat: The Law, Grace &amp; Judgment">
        <rect class="station-halo" x="760" y="215" width="80" height="70" rx="6" />
        <ellipse class="furniture-glory" cx="800" cy="245" rx="32" ry="22" />
        <line x1="768" y1="250" x2="832" y2="250" stroke="#735712" stroke-width="1.2" stroke-linecap="round" />
        <rect class="furniture-gold" x="775" y="235" width="50" height="30" rx="2" />
        <rect x="773" y="233" width="54" height="4" fill="#d4ad57" stroke="#735712" stroke-width="0.8" />
        <!-- Cherubim facing each other -->
        <circle cx="782" cy="229" r="3" class="furniture-cherub" />
        <path d="M 782,232 Q 788,220 798,223" fill="none" stroke="#735712" stroke-width="1.8" stroke-linecap="round" />
        <circle cx="818" cy="229" r="3" class="furniture-cherub" />
        <path d="M 818,232 Q 812,220 802,223" fill="none" stroke="#735712" stroke-width="1.8" stroke-linecap="round" />
        <text class="station-label" x="800" y="280">Ark &amp; Mercy Seat</text>
        <text class="station-sublabel" x="800" y="292">Aron Habberit</text>
      </g>
    </g>
  `;

  // Attach event listeners to all station nodes
  els.sanctuarySvg.querySelectorAll(".sanctuary-station-node").forEach((node) => {
    node.addEventListener("click", () => {
      selectSanctuaryStation(node.dataset.stationId);
    });

    node.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        selectSanctuaryStation(node.dataset.stationId);
      }
    });
  });
}

function initSanctuaryKeyboardNavigation() {
  const container = document.querySelector(".sanctuary-blueprint-container");
  if (!container) return;

  container.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      cycleSanctuaryStation(1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      cycleSanctuaryStation(-1);
    } else if (e.key === "Escape") {
      if (selectedSanctuaryStationId) {
        e.preventDefault();
        e.stopPropagation();
        selectedSanctuaryStationId = null;
        document.querySelectorAll(".sanctuary-station-node").forEach((node) => {
          node.classList.remove("selected");
          node.setAttribute("aria-pressed", "false");
        });
        renderSanctuaryStageDetail(activeSanctuaryStage);
      }
    }
  });
}

async function loadSanctuaryData() {
  try {
    const data = await api("/api/sanctuary");
    cachedSanctuaryData = data;
    renderSanctuaryBlueprint(data);
    renderSanctuaryOverview();
  } catch (err) {
    console.error("Failed to load sanctuary data:", err);
  }
}

function initSanctuaryWorkstation() {
  if (els.sanctuaryStageSlider) {
    els.sanctuaryStageSlider.addEventListener("input", () => {
      const val = parseInt(els.sanctuaryStageSlider.value, 10);
      setPlanOfSalvationStage(val);
    });
  }

  els.sanctuaryStageBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const stage = parseInt(btn.dataset.stage, 10);
      setPlanOfSalvationStage(stage);
    });
  });

  if (els.sanctuaryZoomBtn) {
    els.sanctuaryZoomBtn.addEventListener("click", () => toggleSideZoom());
  }

  initSanctuaryKeyboardNavigation();
  loadSanctuaryData();
}

initPaneResizer();
initFocusAndZoomModes();
initAutoUpdate();
initZebraShading();
initProphecyWorkstation();
initSanctuaryWorkstation();
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