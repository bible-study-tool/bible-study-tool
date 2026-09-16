# WP-029: Zero-Python Distribution — "Open the Book" Installer

status: done
scope: Pillar P (Public Distribution) — package the full study tool as a single downloadable application that requires no Python, no terminal fluency, and no configuration from the end user. GUI-first local web app (ADR-024) with the TUI retained as a mode.
priority: high

## Objective

> *"What's the point of having the word and not sharing it?"*

The Adventist Bible Study Tool has reached a level of theological depth and usability that makes it genuinely valuable to anyone who wants to study Scripture seriously — pastors, Sabbath School teachers, academy students, interested seekers, anyone. But right now, the installation requirement is `git clone` + `python -m venv` + `pip install` + `bash scripts/...`. That gates the tool behind a Python/terminal literacy barrier that most of our intended audience will never cross.

This work package designs and implements a distribution path that a pastor, a grandmother, or a teenager with no computer science background can follow to get the full workstation running in under five minutes — **without ever seeing a terminal**.

Per **ADR-024**, the primary face is a **local web application** (engine serves a static HTML/CSS/JS frontend on `localhost`, opened in the default browser). The Textual TUI / `textual-web` ships as a mode for users who enjoy the aesthetic and as the nightly/beta channel. Phase 2 of ADR-024 (embedded native window via Tauri) is explicitly out of scope here — this package delivers Phase 1 (browser tab), keeping the same frontend assets so Phase 2 later becomes a packaging-only change.

## The Target User

- Never opened a terminal
- Does not know what Python is
- Runs Windows, macOS, or a mainstream Linux desktop (Ubuntu, Fedora)
- Has enough disk space for the app + databases (~550 MB total)
- Can follow a "download this file, double-click it" instruction
- Can read a one-page illustrated quick-start card

## Architecture (per ADR-024)

```
┌─────────────────────────────────────────────┐
│  Frozen engine (PyInstaller/Nuitka binary)  │
│  - starts hidden, no console                │
│  - serves frontend + API on localhost       │
│  - sidecar data/ folder (bible.db,          │
│    macula.db, lexicons/)                    │
└──────────────┬──────────────────────────────┘
               │ localhost
┌──────────────▼──────────────────────────────┐
│  Default browser (Phase 1)                  │
│  = same assets later in Tauri frame (P2)    │
│  HTML/CSS/JS + design tokens (themes)       │
└─────────────────────────────────────────────┘
```

Key properties:
- **No terminal, ever.** Browser opens; engine stays in background; quit = clean shutdown.
- **Binary and data are separate.** Small launcher binary + `data/` folder alongside. Binary and data update independently.
- **One frontend, two hosts.** The exact same assets render in a browser (Phase 1) and in a Tauri native frame (Phase 2, later).
- **Theme optionality** from the TUI (ADR-018) is preserved as CSS design tokens; light + dark ship by default.

## Proposed Distribution Approach

### Option A — Frozen Engine + Sidecar Data + Browser Launcher (Recommended)

Bundle the Python runtime, all dependencies, and the engine into a small self-contained executable per platform. On first run it starts the hidden engine, waits for readiness, and opens the default browser to the study tool. Data lives in a `data/` folder alongside the binary (not inside it).

| Platform | Output | Size estimate |
|---|---|---|
| Windows | `AdventistBibleStudy.exe` + `data/` | binary ~40–60 MB; data ~500 MB |
| macOS | `AdventistBibleStudy.app` (zipped) + `data/` | binary ~50–70 MB; data ~500 MB |
| Linux | `AdventistBibleStudy.AppImage` + `data/` | binary ~40–60 MB; data ~500 MB |

**Why sidecar (not bundled):** bundling ~500 MB of SQLite inside the executable would (a) force a full re-extract to a temp dir on every launch in onefile mode, (b) re-download the whole binary on any data change, and (c) contradict the "~80–130 MB binary" claim the old ADR-023 draft made. Sidecar keeps startup fast, updates small, and the numbers honest. A single combined installer (binary + data zipped together) is still offered for the grandmother path — it's the same artifact, just one download.

**Engine entrypoint:** add a public `def main()` (or equivalent) at the web-server entry — `search.ui.app` currently has no `main()`, only `run_textual_app()` under `if __name__ == "__main__":`. The `[project.scripts]` entry must point at a real callable. The TUI stays reachable via its own entry/mode flag (`--tui` or `textual-web`).

**Database distribution:** pre-built `data/bible.db` (KJV/ASV/BSB/YLT, 31,102 verses), `data/macula.db`, and `lexicons/` ship in the sidecar `data/` folder. `data/egw.db` is NOT bundled (copyright); the installer shows a one-click "Download Spirit of Prophecy public domain texts" button post-install.

**Signing (critical path, not a setup note):**
- Windows: unsigned binaries trigger SmartScreen "Windows protected your PC" — the exact non-technical user we target abandons there. Use code signing (Azure Trusted Signing OSS-friendly options, or traditional certs ~$100–300/yr).
- macOS: unsigned apps show "Apple cannot check it for malicious software." Proper fix = Apple Developer ID ($99/yr) + notarization.
- This is a real cost/process decision and must be an explicit work-package item.

### Option B — Docker / Container Image

A `Dockerfile` that produces a container running the workstation in a web-based terminal (ttyd or wetty), accessible at `http://localhost:8080`. Useful for servers, NAS devices (Synology, QNAP), or technically confident users who want isolation.

**Constraint:** Requires Docker Desktop — still a technical barrier. Option B is a good companion to A, not a replacement.

### Option C — GitHub/GitLab Releases with Install Script

A `install.sh` (macOS/Linux) and `install.ps1` (Windows) that:
1. Downloads the correct Python if needed (using `uv` or the official python.org installer)
2. Creates the venv and installs the package
3. Builds the databases
4. Creates a desktop shortcut / launcher

Simpler to maintain than a frozen binary but still requires some terminal interaction.

**Recommendation:** Ship Option A for Windows and macOS first (highest user count among non-technical users), then Option C as a fallback for Linux. Option B for power users.

## Implementation Tasks

### Phase 0 — Web Frontend Foundation
- [x] Stand up the static frontend skeleton (HTML/CSS/JS, no build step, per ADR-024 §5) served by the engine on `localhost` — `web/` (index.html, styles.css, app.js) + `search/ui/web_server.py` (stdlib ThreadingHTTPServer; `python -m search.ui.web_server`). Phase 0 cutoff: no terminal, browser-tab host. EGW commentary is deliberately **absent from the web API** (copyright-light per ADR-002/023; the TUI/CLI still render it against the local egw.db).
- [x] Define CSS design tokens (color, spacing, type) with light + dark theme variants (TUI theme parity: all 7 TUI palettes ported as `[data-theme]` sets + web-native light/sepia) — `web/styles.css`
- [ ] Port the TUI's proven layout concepts (dense multi-pane, focus mode, tabbed inspector) into the web layout — as a re-imagining, not a reskin (ADR-024 §3) — *partial: reading pane + tab-bar placeholders shipped; the full dense/focus-mode port is its own later step*
- [x] Frontend ↔ engine channel: HTTP fetch (JSON) on `localhost` implemented (`/api/health|passage|translations`); WebSocket remains unevaluated (ADR-024 open sub-decision)

### Phase 1 — Audit & Freeze Preparation
- [x] Audit all `import` chains for dynamic imports, `__file__` path assumptions, and anything that breaks in a frozen context
- [x] Replace any `Path(__file__).parent` relative lookups with a `_resource_path()` helper that is PyInstaller-aware (`search/resource.py`: `get_app_dir`, `get_data_dir`, `get_web_dir`, `get_lexicons_dir`, `data_path`, `lexicon_path`, `resource_path`; refactored `backup.py`, `extract.py`, `macula/db.py`, `linking/egw.py`, `study_service.py`, `web_server.py`)
- [x] Add a real `main()` entrypoint for the web server (the code had no `def main()` — only `run_textual_app()` under `if __name__ == "__main__":`); `search.ui.web_server.main()` now exists and boots the server. Residual: wire `[project.scripts]` (next line).
- [x] Add `pyproject.toml` `[project.scripts]` entry: `bible-study = "search.ui.web:main"` (web entry) — keep TUI reachable via a `--tui` mode flag or separate script (`study = "search.ui.cli:main"`)
- [x] Confirm Textual works frozen for the TUI *mode* (known to work; verified in `search/ui/test_freeze.py` with native, headless, and remote web drivers)
- [x] Add a frozen `textual-web` / `textual serve` smoke test to Phase 3's platform matrix (verifies the TUI-as-nightly-channel claim end-to-end, not just in a dev venv)

### Phase 2 — Data Bundling Strategy & Provenance
- [x] Define a `data/` sidecar bundle layout: `bible.db`, `macula.db`, `lexicons/` (all pre-built and gitignored raw → committed derived)
- [x] Write `scripts/build_release_data.sh` — builds all databases from pinned sources and packages them into `dist/data/`
- [x] **Define release-bundle provenance explicitly (ADR-006/027):** SQLite DBs are verified by canonical **content** hash (`data/INTEGRITY.json`, ADR-027) — not bytes, which are not reproducible across toolchains — and JSON artifacts by byte `SHA256SUMS`; record the release data bundle's hashes in `data/PROVENANCE.md`; the installer verifies the data bundle before first run and on updates
- [x] Resolve and record the bundled-vs-sidecar split as a decision (this WP chooses sidecar; document why in ADR-024 consequences)

### Phase 3 — Launcher, Spec & Build Pipeline
- [x] Write the launcher: start hidden engine → wait for `localhost` readiness → open default browser → clean shutdown on app close (`search/ui/web.py`)
- [x] Write `bible_study.spec` (PyInstaller spec file) for the engine (or Nuitka for better performance/fewer AV false positives)
- [x] Add `scripts/build_release.sh` — cross-platform release build producing binary + `dist/data/` + `SHA256SUMS`
- [x] Test frozen artifact:
  - Linux x86_64 verified (cleanly executes `--help`, `--version`, Scripture reading, Strong's word concordance, and background HTTP server)
  - TUI mode smoke test (`--tui` and interactive study shell fallback) verified on frozen binary
- [x] Add a `.gitlab-ci.yml` `release` stage that builds artifacts on tagged commits and uploads to GitLab Releases

### Phase 4 — User-Facing Installer Experience & Setup Wizard
- [x] `docs/INSTALL.md` — one-page illustrated guide: "Download → Open → Start studying" (no terminal, no chmod, no Windows Terminal note needed — the browser is the surface)
- [x] First-run welcome setup wizard (inside the web app itself):
  - Step 1: Data bundle verification (content-level for `bible.db`/`macula.db` via `INTEGRITY.json` per ADR-027; byte-level for `lexicons/` via `SHA256SUMS`)
  - Step 2: Auto-update preferences toggle (enabled by default; wording explicit that only a version check is sent — no telemetry, per ADR-023)
  - Step 3: Spirit of Prophecy (EGW) public-domain content (10 historical works). If online: "Download with one click". If offline: "Skip for now — you can download anytime later from Settings/Menu when connected."
  - Step 4: External resources link card: prominent link out to [egwwritings.org](https://m.egwwritings.org/) for the complete, copyrighted Spirit of Prophecy research library.
- [x] Update `docs/USER_GUIDE.md` with the zero-Python installer path as the primary entry point (terminal / git clone method as "advanced developer setup")

### Phase 5 — ADR & Governance
- [x] Update ADR-023 to reference ADR-024 (distribution mechanism changed from frozen-TUI-binary to local-web-app); fix its size claims (binary ~40–70 MB + ~500 MB sidecar data)
- [x] Update `ROADMAP.md` Pillar D (D1/D5) and Pillar P entries to reflect GUI-first architecture (ADR-024)
- [x] Tag the first public release `v0.1.0-alpha` with GitLab Releases + changelog

## Acceptance Criteria
- A non-technical user (e.g. elementary school teacher or pastor) can get the workstation running on Windows or macOS by double-clicking a downloaded release — with no terminal ever visible and no Windows Terminal dependency.
- Default browser opens the study tool automatically; closing the app (or quitting from within it) shuts the engine down cleanly.
- Setup wizard works 100% offline without failing if no internet connection is present at first launch.
- Auto-update is enabled by default but easily toggled off during initial setup; update check sends nothing but a version request (zero telemetry).
- Release data bundle hash is verified before first run and on updates; bundle SHA-256 recorded in `data/PROVENANCE.md` (ADR-006).
- The frozen engine binary passes test suite verification (`AdventistBibleStudy --test`).
- `data/egw.db` is NOT pre-bundled (copyright clean); one-click download of public domain works is offered post-install alongside official egwwritings.org links.
- Release artifact = binary + sidecar `data/`: binary < 80 MB compressed; data bundle ~500 MB with documented integrity manifests (`INTEGRITY.json` content + `SHA256SUMS` bytes, ADR-027).
- TUI mode (`--tui` / `textual-web`) still launches and passes smoke tests from the same release.
- GitLab CI builds artifacts automatically on `v*` tags.
- **Signing decision made and recorded** (Windows SmartScreen + macOS Gatekeeper) — cost/process accepted or explicitly deferred with a documented risk note.

## Confirmed Architecture Decisions
1. **GUI-first (ADR-024):** local web app is the primary face; browser tab now (Phase 1), Tauri embedded window later (Phase 2). TUI retained as a mode/nightly channel.
2. **Sidecar data, not bundled:** binary and `data/` folder are separate; they update independently; size claims are honest (~40–70 MB binary + ~500 MB data).
3. **Signing is critical path:** Windows SmartScreen and macOS Gatekeeper are real abandonment points for non-technical users; a decision (accept cost or defer with risk note) is required, not a setup footnote.
4. **Auto-Update Behavior:** Enabled by default via GitLab Releases API check, but explicitly presented with a toggle in the initial welcome wizard so users have immediate control. Wording is explicit that it sends only a version check (no telemetry).
5. **EGW Integration & Legality:** Offline-first design. Pre-1929 public-domain works available via one-click download when online. If offline during setup, setup finishes cleanly with a gentle reminder. Official link-out to egwwritings.org provided in the UI for complete research.

## Notes / findings
- Review feedback (ADR-023/WP-029 grounding pass) surfaced: missing `main()` entrypoint, size-estimate contradiction (80–130 MB binary vs ~500 MB data), undefined release-bundle provenance, and Windows Terminal dependency. All four are addressed above: real web entrypoint (Phase 1), sidecar split (Phase 2), explicit integrity manifests — `INTEGRITY.json` content-level for SQLite DBs + `SHA256SUMS` byte-level for JSON, per ADR-027 (Phase 2) — and browser-based surface removes terminal friction (Architecture).
- Windows Defender / AV false positives on packed-Python executables remain a real risk; Nuitka (fewer false positives) preferred over PyInstaller if benchmarks confirm, and code signing (Phase 4/5) is the mitigation.
- Phase 0 (frontend + server skeleton) landed via `search/ui/web_server.py` + `web/` (index.html/styles.css/app.js). 17 tests for the web surface (`search/ui/test_web.py`: 14 HTTP integration + 3 serializer unit tests), stdlib-only, no build step, no deps. The JSON serializer drops heavy per-verse enrichment by default (semantic frames, nuances, citations) and serializes per-verse on demand via `?eager=1` — matches the "no telemetry, no premature weight" principle. EGW commentary is excluded from the wire entirely (copyright-light web API; TUI/CLI parity unchanged). Genesis 1:1 smoke-tested: KJV + 4 translations served.
- No `main()` existed for a web face before this phase; `web_server.main()` now boots the server (Phase 1 still wires `[project.scripts]`).