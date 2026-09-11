# ADR-024: GUI-First Architecture — Local Web UI as Primary Face, TUI as a Mode

* **Status:** Accepted
* **Date:** 2026-09-07
* **Scope:** Pillar D (Application / UX), Pillar P (Public Distribution), WP-029
* **Deciders:** Project Maintainer
* **Consulted:** [ADR-008](ADR-008-future-architecture-and-packaging.md) (three-tier architecture), [ADR-013](ADR-013-design-principles-stewardship-and-scalability.md) (design principles), [ADR-017](ADR-017-terminal-user-interface-and-unified-study-cli.md) (TUI), [ADR-018](ADR-018-textual-study-workstation-and-themes.md) (themes), [ADR-023](ADR-023-zero-python-distribution-and-packaging.md) (distribution), AGENTS.md, ROADMAP.md
* **Informs:** Pillar D (UX), Pillar P (distribution), WP-029

---

## Context

The tool's mission is to make serious Bible study accessible to the **largest
possible audience** — pastors, Sabbath School teachers, grandmothers, students,
seekers. The Textual TUI (ADR-017, ADR-018) was never the end goal: it was a
**development vehicle** — faster and cheaper to build than a GUI, which let the
platform be pressure-tested early. That bet paid off: using the TUI surfaced
gaps that improved not just the interaction layer but the underlying database
and tool features.

But a text-based interface is not the face for the widest audience:

* A terminal window signals "developer tool" to non-technical users, and the
  aesthetics — however polished — read as niche, even ugly, to many.
* Existing tools such as e-SWORD — a great project that has faithfully served
  Bible students for decades — illustrate the flip side: because it has been
  around so long, its interface still carries the look of its early days, and
  its density can itself become a barrier to study.
* The platform's own tension is visible in WP-029: *"Target User: never opened
  a terminal"* next to a delivery mechanism that opens one.

What the TUI proved (placement, focus mode, tabs, dense multi-pane study, theme
optionality) is worth keeping; its limitations are not. The engine — SQLite +
FTS5, Macula, lexicons, corpus, validators — is already UI-agnostic and needs no
changes for a new face.

## Decision

We adopt a **GUI-first architecture**: a local web application becomes the
primary face of the tool, with the TUI retained as a first-class *mode*.

### 1. Local web app as the primary face

The engine runs locally and serves a static HTML/CSS/JS frontend over
`localhost`, opened automatically in the user's default browser. Two hosts,
one engine, one frontend asset set:

* **Phase 1 — browser tab:** the launcher starts the hidden engine, waits for
  readiness, opens the default browser. Cheapest possible distribution; ships
  first. No terminal appears anywhere.
* **Phase 2 — embedded window (Tauri):** the same frontend renders inside a
  native frame. The frozen engine runs as a Tauri **sidecar** child process
  (`externalBin`). Feels like a real desktop app; better for non-technical
  users. The frontend is identical, so Phase 2 is a packaging upgrade, not a
  rewrite.

### 2. TUI becomes a mode / nightly channel

The Textual TUI and `textual-web` mode ship with the same release as a
first-class mode for users who enjoy the aesthetic. New features land there
first — it doubles as the nightly/beta channel inside the stable release.
It is not a maintenance orphan: it remains the feature pipeline and the
lowest-friction way to try work-in-progress.

### 3. The GUI is a re-imagining, not a reskin

The web frontend keeps what the TUI proved — dense multi-pane layout, focus
mode, tabbed inspector, keyboard-first study — but is designed as a native web
experience, not a GUI copy of the TUI.

### 4. Theme optionality is preserved

The TUI's theme system (ADR-018) becomes CSS design tokens (custom
properties). Themes are sets of token values; light and dark ship by default,
with a theme gallery possible later. No single "white or grey" monoculture.

### 5. No-build frontend to start

Hand-crafted HTML/CSS/JS with a design-token system; **no React-ecosystem
build step** until a proven need (ADR-013). A static frontend served by the
engine is the cheapest thing that scales.

### 6. Design references (what "pretty but not overkill" looks like)

| Project | What to borrow |
|---|---|
| **Obsidian** | Local-first, plain files, knowledge graph, themes, dense side panels — the closest architectural echo; we already have corpus-as-markdown + WordGraph |
| **NotebookLM** | Study-flow model: source panel, notes, generated study material side-by-side (roadmap goal D1) |
| **YouVersion** | Reading simplicity — the "grandma path," one clear reading surface |
| **Logos / Olive Tree** | Scholarly density done right: multi-pane, original-language access without intimidation |
| **Notion** | Command palette / quick actions for study notes and annotations |

### 7. Sidecar data architecture & release bundle layout

The release artifact separates the application engine from large biblical and linguistic datasets:

```
<dist_root>/
├── bible-study              # Standalone executable (~40–70 MB)
└── data/                    # Sidecar data bundle (~430 MB raw; ~120 MB compressed)
    ├── bible.db             # Whole-Bible SQLite (31,102 verses, KJV + BSB/ASV/YLT + Strong's + FTS5)
    ├── macula.db            # Linguistic SQLite (Hebrew OT + Greek NT syntax & discourse)
    ├── SHA256SUMS           # Cryptographic integrity hashes for all bundled data files
    └── lexicons/            # Curated derived JSON lexicons
        ├── strongs-lexicon.json
        ├── strongs-list.json
        ├── tbesh-glosses.json
        └── tbesg-glosses.json
```

**Copyright boundary (ADR-002, ADR-023):** `data/egw.db` is strictly excluded from release archives. Public-domain historical works (10 titles) are offered post-install via one-click download, and an explicit link-out to [egwwritings.org](https://m.egwwritings.org/) provides access to the complete research corpus.

## Consequences

### Positive
* Reaches the mission audience: no terminal, no Python, no technical literacy —
  a browser is the one "terminal" every user already knows.
* **Packaging friction drops** (vs. ADR-023's TUI-binary plan): no terminal
  dependency on any platform, no console/unicode quirks, and Linux
  double-click works because the browser opens — no terminal needs to attach.
* **Sidecar vs. Monolithic Binary Decision:**
  * *Eliminates startup extraction lag:* A monolithic 500 MB frozen executable would force PyInstaller to extract half a gigabyte to a temporary directory on every launch, causing multi-second startup delays, disk thrashing, and crashes on systems with small RAM disks or restricted `/tmp` partitions.
  * *Bandwidth-efficient incremental updates:* Engine updates (<50 MB) download independently without forcing users to re-download immutable 430 MB biblical and linguistic databases on every patch.
  * *Cryptographic provenance audit (ADR-006):* Users and downstream auditors can inspect and verify individual SQLite and lexicon checksums directly via `SHA256SUMS` without extracting a packed binary.
  * *Clean copyright boundary:* Isolating databases to a sidecar folder provides a clear, natural home for post-install commentary downloads without modifying the executable.
* Cross-platform simplifies: the engine is already cross-platform, Tauri is
  cross-platform, and the frontend is just HTML/CSS/JS.
* The TUI investment is preserved and stays valuable as the nightly channel.
* Aligns with and partially activates ADR-008's three-tier vision (engine →
  local service layer → UI clients).

### Negative / Trade-offs
* Webview rendering differs slightly per platform (Windows WebView2, macOS
  WebKit, Linux WebKitGTK) — a minor concern for a text/panel study tool;
  mitigated by testing against real browsers first.
* Browser-tab mode feels less "app-like" than a native window — accepted for
  Phase 1, resolved by Phase 2 (Tauri).
* A localhost server must be lifecycle-managed (start hidden, wait-ready,
  clean shutdown) — new, small engineering surface.
* Frontend work (HTML/CSS/JS) is a new skill area for the project.

## Open sub-decisions (not blocking)

* Frontend framework, if any, once a build step is proven necessary.
* WebSocket vs. HTTP polling for the Phase 1 frontend↔engine channel.
* Flatpak (Flathub) as a Linux distribution channel beyond AppImage.