# Changelog — Adventist Bible Study Tool

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.2-alpha] - 2026-09-17

### Added
- **Treasury of Scripture Knowledge (TSK) Whole-Bible Cross-References (ADR-026, WP-035, WP-036):**
  - Interactive Cross-Refs tab in Web Workstation (keyboard shortcut `x`) with complete TUI Tab 6 parity.
  - Ingested ~345,000 scripture-interpreting-scripture links spanning all 66 canonical books and 31,102 verses into `data/bible.db`.
  - Two-layer cross-reference architecture:
    - Layer A: Curated theological cross-references with SDA doctrinal tags, notes, and direct bidirectional links.
    - Layer B: Whole-Bible TSK cross-references grouped by phrase/concept with live reciprocal lookups.
  - Real-time keyword filter, directionality toggle, and one-click Scripture navigation.

- **Unified Cross-Source BM25 Search Engine (C4 Phases 1–3, ADR-028):**
  - High-performance BM25 ranking across three distinct corpuses: Curated theological entries, Bible Scripture verses (all translations), and Ellen G. White Spirit of Prophecy commentary.
  - Faceted and filtered search API (`/api/search`) with score normalization, highlighted snippets, and multi-field relevance scoring.
  - Sub-millisecond sidecar-free search execution without locking or external daemon dependencies.

- **Curation Velocity Dashboard & Verifiable Terminal Manifest (WP-037):**
  - Terminal-based progress manifest accessible via `python -m search.corpus.manifest` and `bible-study manifest`.
  - Canonical coverage metrics, word counts, and verification seals across Old Testament, New Testament, and Spirit of Prophecy corpuses.

- **Multi-Platform Standalone Release Packaging Pipeline (WP-029, ADR-024):**
  - Automated GitLab CI release pipeline building standalone zero-Python distributions for:
    - Linux x86_64 (`.tar.gz`)
    - Windows x86_64 (`.zip` on SaaS runner)
    - macOS Apple Silicon & Intel (`.tar.gz` on SaaS M1 runner)
  - Portable release artifact publishing via GitLab CLI (`glab`) using POSIX positional parameters for Alpine Linux compatibility.

### Changed & Fixed
- **Two-Layer Cryptographic Data Integrity (ADR-027, WP-029):**
  - Implemented semantic content-level SQLite verification (`data/INTEGRITY.json`) via `search.validation.db_integrity`.
  - Solves SQLite byte-level reproducibility variance across OS toolchains while cryptographically guaranteeing table and row integrity.
  - Rigorous sidecar-free read hygiene: enforced `query_only=ON`, `mode=ro`, and WAL-aware connection pooling to prevent unwanted `.db-shm` and `.db-wal` generation in user directories or read-only release mounts.
- **Visual Tour & Documentation Modernization:**
  - Added comprehensive Visual Tour gallery (`docs/VISUAL_TOUR.md`) featuring 12 high-resolution screenshots of the Study Room workstation and all 8 comprehension tools.
  - Modernized `README.md`, `docs/USER_GUIDE.md`, `docs/INSTALL.md`, `CONTRIBUTION_STANDARDS.md`, `NOTICE.md`, and `docs/HOW_TO_STUDY_THE_BIBLE.md`.
  - Updated audience terminology across all guides to welcoming, non-exclusionary language ("Non-technical users" / "Non-developers").

## [0.1.1-alpha] - 2026-09-15

### Added
- **Study Room Visual Identity & Workspace Ergonomics (ADR-025, WP-030):**
  - Draggable 65/35 split-pane layout with pointer capture, keyboard adjustments (Left/Right arrows, Home/Enter), and persisted user ratio.
  - Distraction-free Focus Mode (`f`) and full-width side workstation Panel Zoom (`z`).
  - Study Room Desk warm sepia default substrate and Dark Walnut night substrate.
  - Subtle organic wood and paper grain textures (`--desk-grain`, `--paper-grain`).
  - Strict WCAG AAA text contrast (>= 7.0:1) and Anti-Slop Charter adherence (zero frosted glass, zero bouncy animations).
  - Alternating verse zebra-shading option persisted in settings.

- **Master Historicist Prophetic Lexicon & Apocalyptic Symbol Chaining (WP-031):**
  - Canonical 25-symbol historicist dataset (`data/prophetic_lexicon.json`) covering Day-Year Principle, 1260 Days, 70 Weeks, 2300 Days, Beasts, Horns, Waters, and Trumpets.
  - Master Prophetic Table workstation tab with real-time text search, category filters, and prophetic book filters.
  - In-context prophetic symbol badge buttons (◈) and inline proof-text cards with direct Scripture navigation.
  - Plain-English original-language theological nuance engine for Hebrew verbal stems and Greek aspects/voices (`/api/nuance`).

- **Sanctuary Typology Blueprint & Chronological Plan of Salvation (WP-032, FB #24):**
  - Full typological knowledge graph (`data/sanctuary_schema.json`) covering Courtyard, Holy Place, Most Holy Place, 6 furniture stations, and sacrificial services (Tamid / Yom Kippur).
  - Responsive inline SVG architectural blueprint of the Tabernacle with interactive furniture inspection cards.
  - 4-stage chronological Plan of Salvation stepper/slider (Cross AD 31 ➔ Heavenly Intercession ➔ 1844 Judgment ➔ Consummation).
  - In-context sanctuary verse badges linking Scripture directly to sanctuary stations.

- **Progressive Spirit of Prophecy Commentary & Chapter Reader (WP-033):**
  - Commentary tab with progressive disclosure: compact reference chips ➔ full-chapter contextual reading drawers.
  - Printed book pagination breaks with target paragraph centering.
  - Sequential chapter traversal (‹ Prev / Next ›) and reader zoom.
  - Zero-telemetry user book ingestion via drag-and-drop dropzones in Settings and Commentary tabs (`/api/import-books`).

### Changed & Fixed
- Bare book search navigation now defaults to Chapter 1 (`Genesis`, `Revelations`, `1 Chron.`).
- Scripture reading pane renders complete Strong's concordance tags across all words/tokens in a verse.
- Translations comparison tab cards no longer crush under flexbox layout constraints (`flex-shrink: 0`).
- Dedicated "+ Feed Books" dropzone in Workspace Settings with animated progress indicator.
- Languages tab updated to full TUI parity: Hebrew/Greek original text banner, word-level lexicon cards, English gloss first.
- Header chapter navigation buttons styled with solid opaque substrate backgrounds.
- Cryptographic sidecar data bundle integrity manifest `data/SHA256SUMS` added and verified.

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

[0.1.2-alpha]: https://gitlab.com/bible-study-tool/adventist-bible-study-tool/-/releases/v0.1.2-alpha
[0.1.1-alpha]: https://gitlab.com/bible-study-tool/adventist-bible-study-tool/-/releases/v0.1.1-alpha
[0.1.0-alpha]: https://gitlab.com/bible-study-tool/adventist-bible-study-tool/-/releases/v0.1.0-alpha
