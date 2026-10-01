# WP-042: Neural Model Provenance Sourcing, Developer Bootstrap Hydration, and GUI Vector Management

status: open
scope: Pillar C (C1, C2, C7), Pillar D (D1, D3), Pillar G (G6), Pillar P (Desktop) — Complete the end-to-end lifecycle for local neural semantic embeddings: pin ONNX model provenance in PROVENANCE.md, hydrate whole-Bible embeddings during developer bootstrap, package model/vector sidecars for desktop release bundles, expose in-app model download and user library vectorization in the GUI, and reorganize the Settings modal with collapsible shortcuts.
priority: high

## Objective

Deliver complete architectural and user-facing closure for local neural embeddings (ADR-029, WP-040) across three distinct user classes:
1. **Developers & CI Environments:** Fresh clones running `./bootstrap.sh --data` must automatically fetch the pinned INT8 ONNX model and hydrate the pre-computed whole-Bible vector database (`data/embeddings.db`, 31,102 verses) without manual intervention, allowing all hybrid search tests and validators to pass strictly.
2. **Desktop End-Users (Zero-Setup):** Native desktop installers (.dmg, .deb, .AppImage, .exe) bundle the pre-computed Scripture vector database and quantized model in the app sidecar, providing instant out-of-the-box `✦ Hybrid` search without setup friction.
3. **Non-Technical Students & Pastors (GUI-Driven Management):** Users who import external study materials (Spirit of Prophecy, commentaries, or personal notes) cannot and should not be expected to open a terminal or run CLI commands. The GUI Settings modal must display neural model status, provide a one-click in-app model downloader if weights are missing, offer a progress-tracked "Vectorize Library & Notes" action to index user content locally into isolated storage (`data/library_embeddings.db`), and tidy the Settings modal by tucking keyboard shortcuts into a collapsible drawer.

## Inputs (read these first)
- `docs/decisions/ADR-029-zero-pytorch-local-neural-embeddings-and-hybrid-search.md` (Zero-PyTorch ONNX, local dense vectors, Tri-Brid RRF)
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md` (Zero-waste stewardship, no bloated 2 GB PyTorch runtimes)
- `docs/decisions/ADR-024-gui-first-architecture-tui-as-mode.md` (GUI-first desktop experience)
- `docs/decisions/ADR-025-visual-identity-and-anti-slop-design-charter.md` (Study Room Desk serenity, anti-slop rules)
- `docs/decisions/ADR-027-content-level-sqlite-integrity.md` (SQLite canonical integrity verification)
- `docs/decisions/ADR-028-tauri-desktop-packaging-and-native-window.md` (Tauri desktop sidecars & native packaging)
- `docs/wp/WP-040-neural-embeddings-and-hybrid-search.md` (Local neural semantic embeddings engine)
- `scripts/build_embeddings.py` (Whole-Bible vector generation pipeline)
- `scripts/fetch_sources.sh` (Cryptographically pinned source data fetcher)
- `scripts/bootstrap.sh` (One-command environment setup)
- `search/linking/onnx_embedder.py` (ONNX Runtime CPU embedding engine)
- `search/corpus/hybrid_search.py` (Vector store and Tri-Brid RRF ranker)
- `web/index.html`, `web/app.js`, `web/styles.css` (Workstation Settings modal)

---

## Architectural & UX Principles

1. **Integrated Core vs. User-Provided Content Boundary:**
   - **Canonical Scripture Embeddings (`data/embeddings.db`):** 31,102 verses are pre-computed, pinned, and distributed with desktop bundles. `✦ Hybrid` mode is the default search mode.
   - **User Library Embeddings (`data/library_embeddings.db`):** External, non-canonical, or copyrighted texts (e.g., imported Spirit of Prophecy / Ellen G. White writings, personal notes) are vectorized **locally on-device on demand** via the GUI into a separate database, preserving copyright boundaries (ADR-002, ADR-023) and zero-cloud privacy. Canonical `data/embeddings.db` is never modified by user ingest.
2. **Zero-Terminal Expectation for End Users:**
   Non-technical users must never be forced to `cd` into application directories, run Python scripts, or install CLI tools to manage search models or vectorize imported books. All model lifecycle actions must be accessible via clear, accessible GUI controls with real-time progress feedback.
3. **Fail-Closed Verification, Resilient Fallback:**
   Downloaded neural model files must match cryptographic SHA-256 pins in `data/PROVENANCE.md`. If model weights are missing at runtime, the search engine degrades gracefully to lexical BM25 matching rather than crashing, while the UI informs the user and offers a one-click download.
4. **Serene, Uncluttered Settings Ergonomics (ADR-025):**
   The Settings modal must remain tidy and focused. Extensive references (such as keyboard shortcuts) should be collapsed by default under an expandable `<details>` accordion so users can quickly access operational settings (font scaling, updates, library feeds, neural models) without excessive scrolling.

---

## Tasks

- [x] ### Task 1: Neural Model Provenance & Upstream Pinning (`data/PROVENANCE.md`, `scripts/fetch_sources.sh`)
  - Pin the official Hugging Face quantized multilingual transformer assets in `data/PROVENANCE.md` with upstream commit hash (revision `761b726dd34fb83930e26aab4e9ac3899aa1fa78`):
    - Upstream: `https://huggingface.co/Xenova/multilingual-e5-small`
    - Relative paths (relative to `data/` for `fetch_sources.sh`):
      - `models/multilingual-e5-small/model_quantized.onnx` (`f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193`)
      - `models/multilingual-e5-small/tokenizer.json` (`0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39`)
  - Update `scripts/fetch_sources.sh` to fetch from `https://huggingface.co/Xenova/multilingual-e5-small/resolve/761b726dd34fb83930e26aab4e9ac3899aa1fa78/...` and cryptographically verify files.
  - Ensure `--check` mode verifies model files when present.

- [x] ### Task 2: Developer Bootstrap Hydration & Strict Testing (`scripts/bootstrap.sh`, `pyproject.toml`, `search/corpus/test_search_bridge.py`)
  - Ensure zero-PyTorch ONNX dependencies (`onnxruntime>=1.16`, `tokenizers>=0.15`) are installed during `--data` or as a lean `[project.optional-dependencies] onnx` target without pulling in PyTorch or `sentence-transformers` (ADR-013, ADR-029).
  - Update `scripts/bootstrap.sh`:
    - In `--data` and `--all-in-one` modes, ensure `data/models/` is fetched/verified via `fetch_sources.sh`.
    - Add compilation of `data/embeddings.db` via `python scripts/build_embeddings.py` (idempotent: skip if already present and valid).
  - Restore the strict test assertion in `search/corpus/test_search_bridge.py`:
    - `test_search_modes_hybrid_vs_keyword` must strictly assert `"rrf_score"` presence when running in a fully hydrated environment.

- [x] ### Task 3: Backend Model Status & Vectorization Endpoints (`search/ui/study_service.py`, `search/ui/web_server.py`)
  - Define isolated storage for user library vectors in `data/library_embeddings.db` (`paragraphs(paragraph_id TEXT PRIMARY KEY, vector BLOB, magnitude REAL)`), ensuring canonical `data/embeddings.db` remains untouched and copyright boundaries are preserved (ADR-002, ADR-023).
  - Implement REST API endpoints:
    - `GET /api/model/status`: Returns JSON reporting `model_available` (bool), `model_name` (str), `model_size_mb` (float), `download_in_progress` (bool), `download_percent` (float), `scripture_embeddings_count` (int), and `user_library_embeddings_count` (int).
    - `POST /api/model/download`: Initiates background streaming download of pinned model weights with SHA-256 verification and thread-safe progress tracking.
    - `POST /api/library/vectorize`: Rejects if model is not installed (400); otherwise initiates background vectorization of imported library paragraphs (`egw.db` or imported books) into `data/library_embeddings.db`.
    - `GET /api/library/vectorize/progress`: Polls status of active library vectorization (`is_running`, `total`, `processed`, `percent`, `eta_seconds`, `error`).

- [x] ### Task 4: GUI Settings Integration & Collapsible Ergonomics (`web/index.html`, `web/app.js`, `web/styles.css`)
  - In `web/index.html` (Settings Modal):
    - Add a dedicated **"Neural Semantic Search & Vector Embeddings"** section *before* Keyboard Navigation & Shortcuts.
    - Include:
      - Model Status pill badge (`● Ready (INT8 Quantized, 113 MB)` or `○ Not Installed`).
      - One-click **"Download Neural Model"** button with a progress bar (active if model is missing).
      - Status of Scripture embeddings (31,102 verses) and User Library embeddings.
      - One-click **"Vectorize Library & Notes"** button with a live progress bar.
    - Wrap the **"Keyboard Navigation & Shortcuts"** section in an accessible, collapsible `<details class="settings-collapsible">` container with `<summary>`, defaulting to closed so operational settings remain visible without scrolling.
  - In `web/app.js`:
    - Fetch model and vector status upon opening the Settings modal.
    - Handle "Download Neural Model" and "Vectorize Library" actions with progress polling and notification toasts.
  - In `web/styles.css`:
    - Style the neural model setting card, progress bars, and collapsible shortcuts accordion according to the Study Room Desk warm aesthetic (ADR-025).

- [ ] ### Task 5: Packaging & Release Sidecar Staging Verification (`scripts/build_release_data.py`, `scripts/build_desktop.py`)
  - In `scripts/build_release_data.py`, enforce that release bundling strictly requires `data/models/` and `data/embeddings.db`, raising a fatal exit if missing rather than silently emitting an incomplete bundle.
  - Ensure desktop packaging (`scripts/build_desktop.py`) stages the verified neural model files and `embeddings.db` into `src-tauri/binaries/data/` while strictly excluding copyrighted user content (`egw.db`, `library_embeddings.db`) per ADR-002 and ADR-028.

---

## Conventions that Apply

- **Deterministic core as source of truth (AGENTS.md Non-negotiable 1):** Vector embeddings are local mathematical projections; canonical Scripture text and human-curated correlations remain the immutable source of truth.
- **Fail fast, never silently accept (Non-negotiable 3):** Model downloads fail immediately on SHA-256 checksum mismatches.
- **Zero-Waste Stewardship (ADR-013):** Inference uses quantized INT8 ONNX running locally on CPU (<40 MB RAM, <20ms single query latency). No PyTorch runtime or GPU dependencies.
- **Serene Visual Identity (ADR-025):** The Study Room Desk remains free of noisy popups, flashing banners, or visual slop.

---

## Acceptance Criteria

- [x] `data/PROVENANCE.md` records pinned URLs and SHA-256 checksums for `model_quantized.onnx` and `tokenizer.json`.
- [x] `scripts/fetch_sources.sh` downloads and verifies model files with zero errors.
- [x] `./bootstrap.sh --data` on a clean checkout hydrates `bible.db`, `macula.db`, and `embeddings.db`.
- [ ] All 929+ automated tests and F1–F6 integrity validators pass with `bash scripts/verify_all.sh`.
- [x] `GET /api/model/status` reports model and vector counts accurately.
- [x] The Settings modal displays the Neural Semantic Search card before Keyboard Shortcuts.
- [x] Keyboard Shortcuts in Settings are neatly tucked inside an accessible, collapsible `<details>` container.
- [x] Clicking "Vectorize Library" runs local on-device embedding generation with visible progress.
