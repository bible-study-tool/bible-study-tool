# ADR-028: Tauri Desktop Packaging and Native Window Architecture

* **Status:** Accepted
* **Date:** 2026-09-27
* **Scope:** Pillar D (Application / UX), Pillar P (Public Distribution), WP-038
* **Deciders:** Project Maintainer
* **Consulted:** [ADR-008](ADR-008-future-architecture-and-packaging.md) (three-tier architecture), [ADR-013](ADR-013-design-principles-stewardship-and-scalability.md) (design principles & stewardship), [ADR-023](ADR-023-zero-python-distribution-and-packaging.md) (packaging), [ADR-024](ADR-024-gui-first-architecture-tui-as-mode.md) (GUI-first & Tauri phase 2), [ADR-025](ADR-025-visual-identity-and-anti-slop-design-charter.md) (Study Room Desk identity), AGENTS.md, ROADMAP.md
* **Informs:** Pillar D (UX), Pillar P (distribution), WP-038

---

## Context

Phase 1 of [ADR-024](ADR-024-gui-first-architecture-tui-as-mode.md) delivered a local web application running on `localhost` and opened automatically in the user's default browser via a standalone frozen executable (`v0.1.3-alpha`). This successfully eliminated Python and terminal dependencies from the installation requirement.

However, real-world testing with non-technical users (specifically on macOS) revealed acute usability friction:
1. **Loose Binary Confusion:** Distributing a `.tar.gz` archive with a loose Unix executable (`bible-study`) and helper scripts (`open-macos.command`) does not match the platform conventions users understand. Non-technical users expect standard native installers (`.dmg` drag-and-drop to `/Applications` on macOS, `.msi` / `.exe` setup on Windows).
2. **Terminal Infiltration:** When an archive is extracted, double-clicking raw binaries or resolving Gatekeeper quarantine prompts (`xattr -cr`) forced non-technical users to open a terminal for the first time in their lives and struggle with `cd` navigation. This directly violates the "grandmother path" established in ADR-024 (*"Target User: never opened a terminal"*).
3. **Browser Tab Disconnect:** While a browser tab works, it lacks native OS window identity (Dock / Taskbar presence, dedicated Cmd+Tab switcher, native window frame and menus, isolation from unrelated browser tabs and browser crashes).

ADR-024 §1 explicitly anticipated this and designated Tauri as **Phase 2**:
> *"Phase 2 — embedded window (Tauri): the same frontend renders inside a native frame. The frozen engine runs as a Tauri sidecar child process (`externalBin`). Feels like a real desktop app; better for non-technical users. The frontend is identical, so Phase 2 is a packaging upgrade, not a rewrite."*

## Decision

We adopt **Tauri v2** to package the Adventist Bible Study Tool as a native desktop application with an embedded window and an automated sidecar lifecycle.

### 1. Embedded Native Window Architecture

* **Window Shell:** Tauri provides a lightweight native desktop window backed by the operating system's native webview engine:
  - macOS: WebKit (`WKWebView`)
  - Windows: Microsoft Edge WebView2
  - Linux: WebKitGTK
* **Zero-Build Frontend Preservation (ADR-013, ADR-024 §5):** Tauri is configured with `frontendDist: "../web"`. The existing hand-crafted, high-performance HTML/CSS/JS frontend in `web/` is embedded directly into the application without introducing Node.js build tools (no Webpack, Vite, or npm bundle churn).
* **Native OS Integration:** The application runs with a dedicated Dock/Taskbar icon, native title bar matching the "Study Room Desk" dark/light palette, and OS-standard shortcut handling (Cmd+Q, Cmd+W, Alt+F4).

### 2. Sidecar Engine Lifecycle & Management

The frozen Python engine (`bible-study` executable) runs as an external sidecar process managed entirely by Tauri:

```
┌──────────────────────────────────────────────────────────────┐
│  Tauri Native Application (.app / .exe)                      │
│                                                              │
│  ┌─────────────────────────┐      ┌──────────────────────┐  │
│  │ Native Webview Window   │◄────►│ Local HTTP / REST    │  │
│  │ web/ (Study Room Desk)  │      │ http://127.0.0.1:PORT│  │
│  └─────────────────────────┘      └──────────▲───────────┘  │
│                                              │               │
│  ┌───────────────────────────────────────────┴────────────┐  │
│  │ Tauri Rust Core (Process Supervisor)                   │  │
│  │ - Finds available local port                           │  │
│  │ - Spawns sidecar: bible-study --server --port PORT     │  │
│  │ - Health-checks /api/health before showing window      │  │
│  │ - Clean SIGTERM / TerminateProcess on app quit         │  │
│  └───────────────────────────────┬────────────────────────┘  │
└──────────────────────────────────┼───────────────────────────┘
                                   │ sidecar invocation
                    ┌──────────────▼─────────────┐
                    │  bible-study[.exe]         │
                    │  + data/ (sidecar bundle)  │
                    └────────────────────────────┘
```

1. **Ephemeral Local Port Binding:** To prevent port collisions with other local services (or multiple instances), Tauri selects an open localhost port (or accepts a configurable fallback), passing it via `--port <PORT>` to the sidecar.
2. **Supervised Health Handshake:** Tauri keeps the window hidden or displays a subtle loading splash while polling `GET /api/health`. Once `200 OK` is returned, the main study workstation is presented.
3. **Guaranteed Clean Shutdown:** When the native window is closed or the application is terminated, Tauri's Rust supervisor terminates the child sidecar process, preventing zombie server processes.

### 3. Distribution Packaging Matrix

Tauri replaces raw `.tar.gz` loose binary archives with platform-standard native installers:

| Platform | Native Installer | End-User Experience |
|---|---|---|
| **macOS** | `.dmg` Disk Image + `.app` Bundle | Drag `Bible Study.app` into `/Applications`. Double-click to open. |
| **Windows** | `.msi` (WiX) or NSIS `.exe` Installer | Run setup wizard, desktop & start menu shortcuts created. |
| **Linux** | `.AppImage` / `.deb` Package | Single executable AppImage or native Debian package. |

The sidecar `data/` folder (biblical SQLite databases, Macula linguistics, and verified lexicons per ADR-024 §7 & ADR-027) is colocated within the application bundle structure (`Contents/Resources/data` on macOS, app directory on Windows/Linux).

## Consequences

### Positive
* **100% Elimination of Terminal Friction:** Non-technical readers (the "grandmother path") never see a terminal, shell prompt, `cd` command, or quarantine attribute.
* **Double-Click Simplicity:** Standard `.dmg` and `.exe` installers restore the familiar desktop app installation flow expected by non-programmers.
* **Zero Frontend Rewrites:** The existing, proven `web/` workstation (warm sepia desk, split pane, focus mode, sanctuary blueprint, prophetic key table, TSK cross-references) drops directly into the Tauri window.
* **Resource Efficiency (ADR-013):** Tauri avoids the 150+ MB RAM and disk bloat of Chromium/Electron by using the OS-native webview.

### Negative / Trade-offs
* **Rust Toolchain in CI:** Release workflows require `cargo` and Tauri CLI tooling in addition to Python. (Both GitHub Actions and GitLab CI runners support Rust natively).
* **Platform Packaging Nuances:** Code signing and notarization certificates (Apple Developer ID, Windows Authenticode) are still needed to completely silence OS warnings for internet downloads, though `.dmg` format dramatically improves the gatekeeper experience.
