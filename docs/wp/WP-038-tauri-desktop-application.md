# WP-038: Native Desktop Application (Tauri Packaging & GUI Window)

status: complete
scope: Pillar P (P1), Pillar D (D1) — package the study workstation as a true native desktop application using Tauri v2, providing standard macOS (.dmg/.app) and Windows (.msi/.exe) installers that eliminate terminal usage for non-technical users.
priority: high

## Objective

Deliver **Phase 2 of ADR-024 and ADR-028**: an embedded desktop window application powered by Tauri that bundles our existing zero-build `web/` workstation and supervises the frozen Python engine (`bible-study`) as a background sidecar. 

A non-technical user (pastor, Sabbath School teacher, student, grandmother) must be able to download a single `.dmg` on macOS or `.exe`/`.msi` on Windows, double-click it, and study Scripture in a dedicated native window without ever opening a terminal, seeing a shell prompt, or typing a command.

## Background & Friction Report

During the multi-platform alpha testing (`v0.1.3-alpha`), real-world feedback from a non-technical volunteer on macOS demonstrated that loose binary archives (`.tar.gz`) and terminal scripts (`open-macos.command` / `cd`) create an unacceptable usability barrier. A user who has never opened a terminal was forced to wrestle with directory navigation and file permissions. 

Per **ADR-024** and **ADR-028**, Tauri encapsulates the application into a native desktop shell (`.dmg` on macOS, `.msi`/`.exe` on Windows, `.AppImage` on Linux) with zero modifications to the existing `web/` HTML/CSS/JS frontend.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Tauri Desktop Application                                  │
│  - Native window frame (WebKit / WebView2 / WebKitGTK)     │
│  - Bundles web/ frontend directly (zero-build HTML/CSS/JS)   │
│  - Rust core supervises the background engine               │
└──────────────────────────────┬──────────────────────────────┘
                               │ spawns & health-checks
┌──────────────────────────────▼──────────────────────────────┐
│  bible-study sidecar engine (localhost:PORT)                │
│  - Serves REST API (/api/passage, /api/xrefs, etc.)         │
│  - Reads sidecar data/ (bible.db, macula.db, lexicons/)     │
│  - Clean shutdown when Tauri window closes                  │
└─────────────────────────────────────────────────────────────┘
```

## Inputs (read these first)
- [ADR-024](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-024-gui-first-architecture-tui-as-mode.md) — GUI-First Architecture, Phase 1 vs Phase 2
- [ADR-028](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-028-tauri-desktop-packaging-and-native-window.md) — Tauri Desktop Packaging and Native Window Architecture
- `web/` — Static HTML/CSS/JS workstation frontend
- `search/ui/web_server.py` — Engine server and API endpoints
- `scripts/build_release.py` — Standalone binary packaging pipeline

## Implementation Phases

### Phase 1 — Tauri Workspace Setup (`src-tauri/`)
- [x] Initialize `src-tauri/` project structure:
  - `src-tauri/Cargo.toml` with `tauri` dependencies and sidecar features
  - `src-tauri/tauri.conf.json` configured:
    - App title: "Adventist Bible Study"
    - Identifier: `org.biblestudytool.desktop`
    - `frontendDist`: `../web`
    - Window dimensions: 1280x860 (minimum 900x600)
    - Theme background color matching Study Room Desk (`#1c1815` / `#fbf8f2`)
  - `src-tauri/capabilities/` or permissions for Tauri v2
  - App icons in `src-tauri/icons/`

### Phase 2 — Rust Supervisor & Sidecar Lifecycle
- [x] Implement sidecar process manager in `src-tauri/src/`:
  - Locate `bible-study` executable (packaged sidecar or relative path in dev mode)
  - Find an available open port on `127.0.0.1`
  - Spawn `bible-study --server --port <PORT> --no-browser`
  - Poll `http://127.0.0.1:<PORT>/api/health` until ready
  - Forward port configuration to the frontend webview
  - Implement clean termination handler (SIGTERM / TerminateProcess) on window exit

### Phase 3 — Web Client Integration
- [x] Ensure `web/app.js` transparently detects its backend origin:
  - If running in Tauri webview with dynamic port, route API requests to `http://127.0.0.1:<PORT>`
  - Retain default relative `/api/...` for browser-tab execution
  - Add native window controls or focus integration where appropriate

### Phase 4 — Packaging & Build Script Automation
- [x] Create `scripts/build_desktop.py` (or extend `scripts/build_release.py`):
  - Builds the frozen `bible-study` executable first
  - Places it in the Tauri sidecar target location
  - Invokes `cargo tauri build` to generate platform installers:
    - macOS: `Adventist Bible Study.dmg` + `.app`
    - Windows: `AdventistBibleStudy-Setup.exe` / `.msi`
    - Linux: `adventist-bible-study.AppImage` / `.deb`
  - Verifies generated installer integrity

### Phase 5 — CI Matrix Integration & Automated Releases
- [x] Update `.github/workflows/release.yml`:
  - Add Rust toolchain setup step (`dtolnay/rust-toolchain@stable`)
  - Run Tauri desktop build job across `macos-latest`, `windows-latest`, and `ubuntu-latest`
  - Upload native desktop installers (`.dmg`, `.exe`/`.msi`, `.AppImage`) as GitHub release assets alongside existing zero-Python archives

## Acceptance Criteria
- [x] Running the desktop app opens a native application window rendering the Study Room Desk interface.
- [x] No terminal or shell window appears during launch or execution on macOS or Windows.
- [x] Quitting the desktop application terminates the background `bible-study` server process cleanly.
- [x] `web/` assets remain 100% zero-build (no npm/vite/webpack build step required).
- [x] Automated tests verify Tauri configuration and sidecar lifecycle integrity.
- [x] `bash scripts/verify_all.sh` remains 100% green.
