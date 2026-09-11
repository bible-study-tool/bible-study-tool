# ADR-023: Zero-Python Distribution & Standalone Desktop Packaging (Pillar P)

> **Partially superseded by [ADR-024](ADR-024-gui-first-architecture-tui-as-mode.md).**
> ADR-024 moves the primary user face from a frozen TUI binary to a local web
> app (engine serving static HTML/CSS/JS on `localhost`; Tauri embedded window
> later), with the TUI retained as a mode/nightly channel. The copyright
> boundary, offline-first guarantees, and auto-update behavior in this ADR
> remain in force; the sections below have been updated to reflect the GUI-first
> architecture, sidecar data layout, and verified size metrics.

* **Status:** Accepted (Partially superseded by ADR-024)
* **Date:** 2026-09-06 (Updated 2026-09-11)
* **Scope:** Pillar P (Public Distribution), WP-029
* **Consulted:** AGENTS.md, ROADMAP.md, NOTICE.md, ADR-002, ADR-006, ADR-011, ADR-013, ADR-017, ADR-018, ADR-024

---

## Context

The Adventist Bible Study Tool has matured into an offline-first biblical study workstation offering multi-translation comparison, Greek/Hebrew verbal stems and syntax trees, discourse analysis, Scripture-interpreting-Scripture Old Testament citation anchors, and full-text Spirit of Prophecy commentary.

However, running the tool originally required developer tooling: `git clone`, Python 3.10+, virtual environment creation, pip package installation, and terminal execution. This forms a steep barrier for non-technical users (pastors, elders, teachers, seekers, and students).

Our governing mission requires that the Word be freely accessible to anyone capable of downloading a file and clicking it.

## Decision

We establish **Pillar P (Public Distribution)** with a standalone, zero-Python distribution strategy alongside an offline-first setup wizard.

### 1. Standalone Binary Artifacts & GUI-First Entrypoint (ADR-024)
As finalized in ADR-024, the primary interface is a **GUI-first local web application** rather than a terminal window. The executable (`bible-study` / `bible-study.exe`) launches a background engine and automatically opens the user's default web browser to `http://localhost:8000`:
* **Windows:** `bible-study.exe` (native on Windows 10 & 11; no Windows Terminal requirement).
* **macOS:** `bible-study` standalone executable (ARM64 Apple Silicon + x86_64 Intel).
* **Linux:** `bible-study` standalone executable (x86_64, zero external Python dependency).
* **TUI Mode:** Retained as an accessible mode via `bible-study --tui` and console script `study`.

### 2. Sidecar Data Architecture & Honest Size Claims
Rather than bundling 430 MB of SQLite databases into a monolithic PyInstaller binary (which would cause severe 500 MB extraction delays to `/tmp` on every launch), we adopt a **sidecar data layout** (`dist/data/`):
* **Standalone Engine Binary:** ~34 MB compressed (~70 MB uncompressed) containing frozen Python 3.14 runtime, standard library, and compiled study services.
* **Sidecar Data Bundle:** ~121 MB compressed tar.gz (~430 MB uncompressed databases and lexicons):
  * Public domain Bibles (`data/bible.db`: KJV 1769 with Strong's, ASV 1901, BSB 2020, YLT 1898 — 31,102 verses).
  * Open linguistic datasets (`data/macula.db`: Clear-Bible Macula Hebrew WLC and Greek Nestle 1904 syntax trees and morphology).
  * Curated lexicons and concordances (`lexicons/`: BDB, Abbott-Smith, STEPBible TBESH/TBESG, WordGraph).
  * Cryptographic manifest (`data/SHA256SUMS`) verified via `search.resource.verify_data_bundle()` (ADR-006).
* **Excluded from release binary (copyright clean):**
  * `data/egw.db` is strictly excluded from binary distribution per [NOTICE.md](../../NOTICE.md) and [ADR-002](ADR-002-licensing-and-content-sourcing.md).
  * Post-install, the user is offered a one-click download of public domain historical editions (pre-1929: 10 works including *The Great Controversy*, *Patriarchs and Prophets*, *The Desire of Ages*).
  * The app includes an explicit, prominent link-out to [egwwritings.org](https://m.egwwritings.org/) for complete research across copyrighted writings.

### 3. Setup Wizard & Offline-First Guarantees
* The app is fully functional immediately upon launch, even with zero network connectivity.
* A first-run Setup Wizard modal greets users, automatically verifies data bundle checksums, explains privacy sovereignty, and introduces basic navigation.
* If offline on first launch, setup completes smoothly without error, with a gentle reminder that public-domain commentary can be downloaded anytime later when connected.
* **Auto-Update**: Enabled by default via lightweight GitLab Releases API polling, but prominently surfaced in the first-run welcome wizard with an immediate opt-out toggle and explicit zero-telemetry guarantee.

### 4. Code Signing Decision (Windows SmartScreen & macOS Gatekeeper)
* Commercial code signing certificates (such as Windows EV certificates at $400+/year and Apple Developer Program at $99/year) represent significant recurring financial overhead for a free, open-source ministry project.
* **Decision:** Code signing is explicitly **deferred** for initial alpha/beta releases.
* **Mitigation & Transparency:** A dedicated, illustrated installation guide ([`docs/INSTALL.md`](../INSTALL.md)) provides step-by-step instructions for clicking "More info" → "Run anyway" on Windows SmartScreen and Right-Click → "Open" on macOS Gatekeeper. SHA-256 release checksums are published with every release for independent verification.

## Consequences

### Positive
* Zero terminal or Python knowledge required to install and study deeply.
* Instant engine startup with zero `/tmp` unpacking overhead on subsequent runs.
* Binary updates (~34 MB) can be distributed independently of static sidecar data (~121 MB).
* Preserves 100% offline functionality, privacy sovereignty, and zero telemetry.
* Strict compliance with copyright law (MIT code / CC BY 4.0 content / clean commentary boundary).
* Automated CI builds on version tags (`v*`).

### Negative / Trade-offs
* Users encounter one-time SmartScreen / Gatekeeper security prompts on initial launch.
* Standalone distribution requires maintaining build scripts (`scripts/build_release.sh`) and PyInstaller specs (`bible_study.spec`).
