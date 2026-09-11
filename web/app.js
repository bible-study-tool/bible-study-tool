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
};

/* ---- Theme management (design tokens via [data-theme], ADR-024 §4) ---- */

let themeCatalog = [];

async function loadThemes() {
  const data = await api("/api/health");
  themeCatalog = data.themes || [];
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

const urlParams = new URLSearchParams(window.location.search);
const initialRef = urlParams.get("ref") || "Genesis 1:1-3";
loadThemes().then(() => navigate(initialRef)).catch((err) => {
  showError("Engine not reachable — is the local server running? " + err.message);
});