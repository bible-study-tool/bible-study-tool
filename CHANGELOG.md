# Changelog — Adventist Bible Study Tool

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

- **Version Update Checker & GUI Notification Banner (WP-044, ADR-023):**
  - **Zero-Telemetry Update Detection:** Implemented `search/ui/version_check.py` to query public GitHub Releases (`/releases/latest`) using standard library HTTP requests. Absolutely zero personal information, IP logs, queries, system metrics, or hardware fingerprints are transmitted.
  - **Strict User Preference & Opt-Out Enforcement:** Respects the existing "Check for Application Updates" toggle (`#auto-update-toggle` in Setup Wizard and `#settings-auto-update-toggle` in Settings). When toggled off, background checks are completely suppressed.
  - **Throttled & Non-Intrusive Polling:** Background update checks are throttled to at most once every 24 hours via `localStorage` timestamp caching. In-memory caching protects against GitHub API rate limits.
  - **Accessible GUI Notification Banner:** Integrated dismissible notification banner (`#update-notification-banner`) right beneath the workstation header, surfacing the new version tag, direct download link, and release notes. Dismissed versions are saved in `localStorage` to avoid repetitive interruptions.
  - **Manual "Check for Updates Now" Trigger:** Added on-demand update check button and real-time status indicator in the Settings modal ("Network & Privacy" section) that bypasses cache and allows instant verification.
  - **Graceful Offline Degradation:** If offline or if the GitHub API is unreachable, the check degrades silently without throwing alerts, modal dialogs, or disrupting Bible study.
  - **Ephemeral CI Runner Test Hardening:** Added mock SQLite database tests for `EgwDB.get_paragraphs_batch()` and `DeterministicSearchBridge` commentary fallback, ensuring clean CI test execution without requiring large local databases (`egw.db`).

## [0.1.6] - 2026-10-01

- **Spirit of Prophecy (EGW) Hybrid Search & Isolated Library Vector Integration (WP-043, ADR-029):**
  - **Dual-Signal Reciprocal Rank Fusion (RRF):** Blended deterministic SQLite FTS5 BM25 keyword matching with local dense 384-dimensional cosine similarity across user library embeddings (`data/library_embeddings.db`, 364,022 paragraphs) using `EgwHybridSearchEngine`.
  - **Memory-Efficient Streaming Matrix Loading:** Pre-allocates a contiguous float32 matrix and streams database rows in 10,000-paragraph chunks in `LibraryVectorStore`, reducing transient peak RAM spikes during loading by ~54% (~600 MB total).
  - **Book-Code Scoping & Zero Leakage:** Added fast book-code scoping (e.g. `egw:GC` or `egw_book="DA"`) executing vector queries in ~5 ms with strict rejection on empty filters.
  - **Fast Batch Lookups & Alias Preservation:** Implemented `EgwDB.get_paragraphs_batch()` with SQLite batch chunking (500 per query) and dual-key aliasing for both canonical IDs (`PP.44.1`) and citation tokens (`egw:PP.44.1`).
  - **Resilient Decoupling & Graceful Degradation:** Preserved absolute independence of Scripture study. If `library_embeddings.db` is absent or unindexed, commentary search gracefully falls back to BM25 keyword matching; if `egw.db` is absent, commentary safely returns empty results without crashing or affecting Scripture search.
  - **Transparent Match Badging:** Search hit metadata surfaces match types (`✦ Hybrid`, `Aa Exact`, `☵ Thematic`), cosine similarity scores, and plain-English reasons (`Keyword match (BM25 #1) + High thematic alignment (cos: 0.89)`).
- **macOS First-Time Setup & Quarantine Helper (`scripts/install-macos.command`):**
  - Added an automated setup script that moves the application to `~/Applications` (or `/Applications`), strips Apple Gatekeeper internet quarantine flags (`com.apple.quarantine`), applies local ad-hoc code signatures, and launches the desktop app.
  - Eliminates terminal friction for non-technical users on macOS (accessible via simple Right-click ➔ Open).
- **Neural Model Provenance Sourcing, Developer Bootstrap Hydration, and GUI Vector Management (WP-042, ADR-029):**
  - **Cryptographic Provenance Pinning:** Pinned `Xenova/multilingual-e5-small` INT8 quantized ONNX weights (`model_quantized.onnx`, 113.6 MB) and tokenizer (`tokenizer.json`, 7.1 MB) at upstream revision `761b726dd34fb83930e26aab4e9ac3899aa1fa78` with SHA-256 digests in `data/PROVENANCE.md` and automated retrieval via `scripts/fetch_sources.sh`.
  - **Zero-PyTorch Optional Target:** Added lean `[project.optional-dependencies] onnx = ["onnxruntime>=1.16", "tokenizers>=0.15"]` in `pyproject.toml` and integrated automated model fetching and vector database hydration (`data/embeddings.db`) into `./bootstrap.sh --data` and `--all-in-one`.
  - **In-App GUI Model Downloader & Settings Integration:**
    - Dedicated "Neural Semantic Search & Vector Embeddings" setting card in the Workstation Settings modal (`web/index.html`).
    - Live status pill indicator (`● Ready (INT8 Quantized, 113 MB)` or `○ Not Installed`) with real-time model and vector counts.
    - One-click background streaming model downloader with SHA-256 validation, animated progress bar, and thread-safe cancellation.
    - Accessible collapsible accordion (`<details class="settings-collapsible">`) tucking keyboard shortcuts away to keep operational settings prominent without scrolling.
  - **On-Device User Library Vectorization:**
    - GUI action "Vectorize Library & Notes" enabling students and pastors to compute dense semantic vectors on-device for imported books and notes into an isolated SQLite database (`data/library_embeddings.db`).
    - Preserves 100% privacy, zero cloud telemetry, and strict copyright boundaries (ADR-002, ADR-023, ADR-029), leaving canonical Scripture embeddings (`data/embeddings.db`) immutable.
  - **Release Sidecar Staging & Packaging Tripwires:**
    - Enforced mandatory presence of `embeddings.db` and ONNX model files in `scripts/build_release_data.py` and `scripts/build_desktop.py`, raising fatal diagnostic errors if missing.
    - Hardened copyright boundary tripwires with wildcard matching (`egw.db*`, `library_embeddings.db*`) to prevent SQLite WAL/SHM sidecar leaks in release bundles.

### Fixed
- **Developer Bootstrap & POSIX Portability:**
  - Added root `INSTALL.md` pointer and updated `docs/INSTALL.md` with explicit Python 3.10+ prerequisites, virtual environment activation step (`source .venv/bin/activate`), and platform hints for macOS Sonoma VM and Linux package managers.
  - Updated `scripts/bootstrap.sh` to provide helpful OS hints if Python 3.10+ is missing, and to report intact virtual environments upon validation errors.
- **Headless CI Test Fixture Typography Parity:**
  - Regenerated `search/fixtures/sample_test_data.json.gz` with canonical `<divineName>` typography (`LORD` / `GOD`) and applied `clean_verse_text()` in `search/testutil.py:ensure_test_databases()`, eliminating headless CI assertion divergence on Deut 6:4.
  - Synchronized `bible.db` content-level SHA-256 in `data/INTEGRITY.json` with fresh source builds.

---

## [0.1.5-beta] - 2026-09-28

### Added
- **Local Neural Semantic Embeddings & Tri-Brid Hybrid Search (WP-040, ADR-029):**
  - Pure zero-PyTorch ONNX embedding runtime (`search/linking/onnx_embedder.py`) running INT8 quantized `multilingual-e5-small` (<10ms single query latency, <40 MB RAM) on standard CPU with RoBERTa pad token handling (`pad_id=1`), mean pooling, and L2 normalization.
  - Transparent fallback to character n-gram embedder if ONNX runtime or model weights are missing.
  - Whole-Bible dense vector precomputation pipeline (`scripts/build_embeddings.py`) generating 384-dimensional dense vectors for all 31,102 verses into `data/embeddings.db` (61.4 MB) in ~3.8 minutes.
  - In-memory contiguous Float32 vector store (`search/corpus/hybrid_search.py`) executing whole-Bible BLAS dot product cosine scans in **~3.5 ms** on standard CPU without external vector database daemons.
  - **Tri-Brid Reciprocal Rank Fusion (RRF)**: seamlessly blends SQLite FTS5 BM25 text rank, vector cosine rank, and Treasury of Scripture Knowledge (TSK) reciprocal cross-reference graph.
  - Search mode segmented pills (`✦ Hybrid`, `Aa Keyword`, `☵ Thematic`), match type badges (`hybrid`, `exact`, `semantic`, `cross_reference`), and cosine similarity score chips.
  - Hardened with thread-safe lazy init locks, boundary-safe book-scoped slicing in `VectorStore.query`, sequential TSK ranks and candidate deduplication, and calibrated multi-source RRF scoring.
  - Transparent documentation of the 100% deterministic human-curated knowledge base vs. local mathematical vector retrieval (zero cloud, zero generative AI chatbots, zero synthetic text fabrication).

---

## [0.1.4-beta] - 2026-09-28

### Added
- **Native Desktop Application Packaging & Window Architecture (WP-038, ADR-028):**
  - Truly zero-terminal, "download → click → use" desktop installers and applications across all major desktop operating systems:
    - macOS Apple Silicon & Intel (`.dmg` drag-and-drop installer)
    - Windows x86_64 (`.exe` NSIS installer & `.msi` package)
    - Linux x86_64 (`.AppImage` executable & `.deb` package)
  - Embedded desktop window using Tauri v2 with native WebView, custom title bar, Study Room Desk window dimensions (1280x860, min 900x600), and dark walnut substrate background.
  - Robust Rust sidecar supervisor (`src-tauri/src/lib.rs`):
    - Automatically discovers available system ports and launches the internal Python engine with dynamic port binding.
    - Polls health endpoints (`/api/health`) before displaying the window.
    - Implements cross-platform process tree termination (`SIGTERM`/`SIGKILL` on Unix, job objects on Windows) on window close to guarantee zero orphan background processes.
    - Reuses existing active web servers if running in local development mode.
  - Automated desktop packaging integrated into GitHub Actions release workflow (`.github/workflows/release.yml`) and local builder (`scripts/build_desktop.py`).

- **Deterministic Cross-Language Unified Search Workstation (WP-039, Pillar C3/C4):**
  - Sub-millisecond, zero-ML deterministic search engine unifying all project databases:
    - King James Version (`bible_fts`, 31,102 verses)
    - Parallel public-domain translations: ASV, BSB, YLT (`translations_fts`, 93,306 verses)
    - Macula Hebrew Old Testament & Greek New Testament morphology (`data/macula.db`, 815,870 linguistic tokens)
    - Ellen G. White Spirit of Prophecy commentary (`egw_fts`, ~150,000 paragraphs)
    - Curated theological study notes (`materials/bible/`, in-memory FTS5 index)
  - **Bidirectional Query Expansion Bridge (`search/corpus/search_bridge.py`):**
    - Seamlessly links English concepts (e.g. `covenant`, `sanctuary`) to underlying Hebrew and Greek roots (e.g. `בְּרִית` *bərît* H1285, `διαθήκη` *diathēkē* G1242).
    - Monotonic logistic sigmoid score normalization $[0.0, 1.0]$ across disparate SQLite FTS5 BM25 ranks.
  - **Smart Omnibox Routing & Serene Workstation UI (`web/`):**
    - Omnibox automatically routes valid scripture references (e.g. `John 3:16`, `Gen 1:1-3`, `Ps 23`) to the Scripture reader, and queries/Strong's numbers to the Search tab (`#panel-search`).
    - Tranquil Study Room Desk source filter pills (`All`, `Scripture`, `Translations`, `Original Languages`, `Commentary`, `Curated`) with persistent count badges.
    - Collapsible fine-grained advanced search drawer with filters for translations, testaments, books, search modes, and cheat sheet syntax tips.
    - Interactive query expansion root chips and one-click navigation to Bible verses or commentary paragraphs.
    - Global keyboard shortcuts `/` and `0` to focus Search.

- **High-Fidelity Biblical Typography across Web, Desktop, and Terminal:**
  - Standardized small-caps rendering for the Tetragrammaton YHWH (`<divineName>LORD</divineName>` and `<divineName>GOD</divineName>`) and italics for supplied words (`<transChange type="added">...`).
  - Terminal cleanup function (`clean_token_text`) stripping raw XML tokens into uppercase LORD for TUI and CLI interfaces.

### Fixed
- **Headless CI Test Environment & Integrity:**
  - Enriched minimal test fixture (`search/fixtures/sample_test_data.json.gz`) with Exodus verses, translations, and Greek crosswalk entries to support isolated CI runs.
  - Eliminated N+1 queries in `MaculaSearchEngine.search_gloss` by batching crosswalk definition queries (`WHERE strongs IN (...)`) and parameterizing `include_samples=False` to prevent scanning the 560,000-row `tokens` table during searches.
  - Fixed SQLite multi-threading read safety in `search/corpus/query.py` (`check_same_thread=False`).

---

## [0.1.3-alpha] - 2026-09-27

### Added
- **Multi-Platform Standalone Release Matrix (Linux, Windows, macOS ARM64 & Intel):**
  - Standalone release packaging workflow (`.github/workflows/release.yml`) producing native, zero-Python binary distributions across 4 distinct platforms:
    - Linux x86_64 (`.tar.gz`)
    - Windows x86_64 (`.zip`)
    - macOS Apple Silicon M-series ARM64 (`macos-latest`, `.tar.gz`)
    - macOS Intel x86_64 (`macos-13`, `.tar.gz`)
  - Automated publishing to GitHub Releases with sidecar databases (`data/bible.db`, `data/macula.db`), cryptographic SHA-256 manifests, and extracted release notes.
- **GitHub Actions CI/CD Pipeline (`.github/workflows/ci.yml`):**
  - Continuous integration running the 834-test pytest suite and F1–F5 deterministic data-integrity gates on pushes and pull requests to `main` and `master`.
  - Non-blocking validator diagnostic reporting and branch-safe concurrency management.
- **Backup CLI Enhancements:**
  - Added `--include-bible` flag to `scripts/backup.py` with comprehensive unit and CLI test coverage, allowing user-curated knowledge bases to be backed up with or without bundled Bible databases.

### Fixed
- **Fresh CI Environment Packaging & Robustness:**
  - Automatic pre-compilation source hydration in `scripts/build_release_data.py`: detects and fetches missing raw sources (`scripts/fetch_sources.sh`) with POSIX-normalized paths before building SQLite databases in ephemeral CI runners.
  - Dual-mode checksum verification in `scripts/fetch_sources.sh` supporting native BSD/macOS `shasum -a 256` and Python fallback.
  - Enforced deterministic LF line endings (`.gitattributes`) and disabled git `core.autocrlf` during provenance verification on Windows runners.
- **Cross-Platform Binary Execution (Windows & macOS):**
  - Reconfigured standard streams (`sys.stdout`/`sys.stderr`) to UTF-8 across all application entry points (`web.py`, `cli.py`, `resource.py`), resolving `UnicodeEncodeError` when printing Hebrew and Greek lexical data on Windows consoles.
  - Isolated Unix-specific terminal dependencies (`curses`, `readline`) with graceful non-fatal fallbacks, and declared `windows-curses` for native Windows terminal support.
  - Added macOS `open-macos.command` helper script and automatic ad-hoc deep code signing to clear Gatekeeper quarantine (`com.apple.quarantine`) on Apple Silicon.

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

[0.1.6]: https://github.com/bible-study-tool/bible-study-tool/releases/tag/v0.1.6
[0.1.6-beta]: https://github.com/bible-study-tool/bible-study-tool/releases/tag/v0.1.6
[0.1.5-beta]: https://github.com/bible-study-tool/bible-study-tool/releases/tag/v0.1.5-beta
[0.1.4-beta]: https://github.com/bible-study-tool/bible-study-tool/releases/tag/v0.1.4-beta
[0.1.3-alpha]: https://github.com/bible-study-tool/bible-study-tool/releases/tag/v0.1.3-alpha
[0.1.2-alpha]: https://gitlab.com/bible-study-tool/adventist-bible-study-tool/-/releases/v0.1.2-alpha
[0.1.1-alpha]: https://gitlab.com/bible-study-tool/adventist-bible-study-tool/-/releases/v0.1.1-alpha
[0.1.0-alpha]: https://gitlab.com/bible-study-tool/adventist-bible-study-tool/-/releases/v0.1.0-alpha
