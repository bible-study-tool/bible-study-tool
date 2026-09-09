# ADR-023: Zero-Python Distribution & Standalone Desktop Packaging (Pillar P)

> **Partially superseded by [ADR-024](ADR-024-gui-first-architecture-tui-as-mode.md).**
> ADR-024 moves the primary user face from a frozen TUI binary to a local web
> app (engine serving static HTML/CSS/JS on `localhost`; Tauri embedded window
> later), with the TUI retained as a mode/nightly channel. The copyright
> boundary, offline-first guarantees, and auto-update behavior in this ADR
> remain in force; the binary-size claims (§below) and Windows Terminal note
> are superseded — see WP-029 for the current plan.

* **Status:** Proposed
* **Date:** 2026-09-06
* **Scope:** Pillar P (Public Distribution), WP-029
* **Consulted:** AGENTS.md, ROADMAP.md, NOTICE.md, ADR-002, ADR-011, ADR-013, ADR-017, ADR-018

---

## Context

The Adventist Bible Study Tool has matured into an offline-first biblical study workstation offering multi-translation comparison, Greek/Hebrew verbal stems and syntax trees, discourse analysis, Scripture-interpreting-Scripture Old Testament citation anchors, and full-text Spirit of Prophecy commentary.

However, running the tool currently requires developer tooling: `git clone`, Python 3.10+, virtual environment creation, pip package installation, and terminal execution. This forms a steep barrier for non-technical users (pastors, elders, teachers, seekers, and students).

Our governing mission requires that the Word be freely accessible to anyone capable of downloading a file and clicking it.

## Decision

We establish **Pillar P (Public Distribution)** with a standalone, frozen-binary distribution strategy alongside an offline-first setup wizard.

### 1. Standalone Binary Artifacts
We will build standalone executables using PyInstaller / Nuitka:
* **Windows:** `AdventistBibleStudy.exe` (native on Windows 11; Windows 10 supported with recommendation for Windows Terminal).
* **macOS:** `AdventistBibleStudy.app` / zip archive (Universal/ARM64 + x86_64).
* **Linux:** `AdventistBibleStudy.AppImage` (standalone, no system Python dependency).

### 2. Pre-Bundled Data vs. Copyright Boundaries
* **Bundled inside release artifact:**
  * Public domain Bibles (`data/bible.db`: KJV 1769 with Strong's, ASV 1901, BSB 2020, YLT 1898 — 31,102 verses).
  * Open linguistic datasets (`data/macula.db`: Clear-Bible Macula Hebrew WLC and Greek Nestle 1904 syntax trees and morphology).
  * Curated lexicons and concordances (`lexicons/`: BDB, Abbott-Smith, STEPBible TBESH/TBESG, WordGraph).
* **Excluded from release binary (copyright clean):**
  * `data/egw.db` is strictly excluded from binary distribution per [NOTICE.md](../../NOTICE.md) and [ADR-002](ADR-002-licensing-and-content-sourcing.md).
  * Post-install, the user is offered a one-click download of public domain historical editions (pre-1929: 10 works including *The Great Controversy*, *Patriarchs and Prophets*, *The Desire of Ages*).
  * The app includes an explicit, prominent link-out to [egwwritings.org](https://m.egwwritings.org/) for complete research across copyrighted writings.

### 3. Setup Wizard & Offline-First Guarantees
* The app must be fully functional immediately upon launch, even with zero network connectivity.
* If offline on first launch, setup completes smoothly without error, with a gentle reminder that public-domain commentary can be downloaded anytime later when connected.
* **Auto-Update**: Enabled by default via lightweight GitLab Releases API polling, but prominently surfaced in the first-run welcome wizard with an immediate opt-out toggle.

## Consequences

### Positive
* Zero terminal or Python knowledge required to install and study deeply.
* Preserves 100% offline functionality, privacy, and zero telemetry.
* Strict compliance with copyright law (MIT/CC BY 4.0 license cleanliness).
* Automated CI builds on version tags (`v*`).

### Negative / Trade-offs
* Cross-platform release builds require platform-specific CI runners or matrix builds.
* Binary bundle sizes will be approximately 80–130 MB due to embedded Python runtime and SQLite databases.
