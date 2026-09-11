# Changelog — Adventist Bible Study Tool

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0-alpha] - 2026-09-11

### Added
- **GUI-First Local Web Study Workstation (ADR-024, WP-029):**
  - Zero-Python standalone launcher (`bible-study`) that spins up the background engine and automatically opens the user's default browser to `http://localhost:8000`.
  - Multi-translation parallel Scripture comparison (King James Version 1769, American Standard Version 1901, Berean Standard Bible 2020, and Young's Literal Translation 1898) across all 31,102 verses.
  - Interactive Strong's concordance integration with hover and inspection capabilities for Biblical Hebrew and Koine Greek.
  - Built-in theme selector with 9 palettes (light, sepia, transparent, dracula, catppuccin mocha, tokyo night, nord, gruvbox dark, solarized dark).
  - First-run welcome Setup Wizard modal (`<dialog id="setup-wizard-modal">`) with accessible 4-step onboarding:
    1. Cryptographic sidecar data bundle integrity audit against `SHA256SUMS`.
    2. Updates & privacy settings with an uncompromising zero-telemetry guarantee (ADR-023).
    3. Historical 10 public-domain Ellen G. White works overview with offline skip option (ADR-002).
    4. Study tips and external resource links to [egwwritings.org](https://m.egwwritings.org/) for the complete copyrighted research library.
  - Persistent `⚙ Setup` button in the header to reopen verification and settings at any time.

- **Standalone Release & Build Pipeline (ADR-006, ADR-024):**
  - Unified cross-platform build script `scripts/build_release.sh` freezing the engine with PyInstaller (`bible_study.spec`).
  - Sidecar data bundle packaging via `scripts/build_release_data.sh` (`bible.db`, `macula.db`, `lexicons/`, `SHA256SUMS`).
  - Standalone release package sizes: ~34 MB compressed engine binary + ~121 MB compressed sidecar data archive (~430 MB uncompressed).
  - Automated GitLab CI release pipeline (`.gitlab-ci.yml`) triggering release builds and artifact uploads on version tags (`v*`).

- **Interactive Textual Study Workstation (ADR-017, ADR-018, ADR-020):**
  - Full-screen terminal study workstation accessible via `bible-study --tui` and console script `study`.
  - Sub-millisecond persistent viewport switching across Syntax & Frames, Lexicons & Strong's, EGW Commentary, Parallel Translations, and Word Search findings.
  - Plain-English Hebrew verbal stems (Qal, Niphal, Piel, Hiphil, Hitpael) and Greek theological nuances (Aorist Middle, Perfect Passive).
  - Pauline argument flow and discourse marker analysis (`search/corpus/discourse_flow.py`).
  - Scripture-interpreting-Scripture Old Testament citation anchors (`search/corpus/ot_citations.py`).

- **Documentation & Quick Start:**
  - One-page illustrated user guide: [`docs/INSTALL.md`](docs/INSTALL.md) ("Download → Double-click → Start studying") for Windows 10/11, macOS, and Linux.
  - Comprehensive User & Study Guide: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).
  - Architectural Decision Records: [ADR-023](docs/decisions/ADR-023-zero-python-distribution-and-packaging.md) and [ADR-024](docs/decisions/ADR-024-gui-first-architecture-tui-as-mode.md).

- **Linguistic Core & Data Integrity:**
  - Complete Macula Hebrew OT and Greek NT morphology database (`data/macula.db`).
  - Curated Strong's Greek/Hebrew concordances and STEPBible TBESH/TBESG glosses (`lexicons/`).
  - Deterministic Source Agreement Layer (`correlations/agreement-ledger.json`, `correlations/apparatus-genesis*.json`).
  - F1–F4 automated validators (schema, Strong's, cross-references, dead-link audit).
  - 645 automated unit and integration tests passing in CI.

[0.1.0-alpha]: https://gitlab.com/adventist-bible-study/bible-study-tool/-/releases/v0.1.0-alpha
