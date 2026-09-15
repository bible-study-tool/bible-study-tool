# WP-034: Developer Ergonomics, One-Command Bootstrapping & Environment Hardening

status: done
scope: Pillar G (G5 — Packaging / Reproducible Environment), Developer Experience, Session Portability
priority: high
decisions: [ADR-011](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-011-whole-book-scaffolding-and-jit-egw.md), [ADR-013](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md), [ADR-024](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-024-gui-first-architecture-tui-as-mode.md)

---

## 1. Objective

Eliminate contributor setup friction and cross-machine desynchronization by transforming `./bootstrap.sh` into a true single-command entrypoint that provisions dependencies, refreshes editable installs, fetches pinned raw sources, hydrates SQLite databases (`bible.db`, `macula.db`), and verifies the environment cleanly from a fresh git clone.

---

## 2. Background & Problem Statement

A real-world cross-machine synchronization test (fast-forwarding 68 commits from `f0d3040` to `v0.1.1-alpha`) identified three distinct developer-experience friction points:
1. **Multi-Step Setup:** `scripts/bootstrap.sh` installed Python package dependencies but did not fetch pinned sources or compile the SQLite databases. A new clone required running 3–4 manual scripts with distinct failure modes (`fetch_sources.sh`, `extract_kjv`, `extract_translations`, `build_db`).
2. **Stale Editable Install Finder:** When new namespace packages or modules are introduced (such as `search.resource`), setuptools editable-install finder mappings (`.pth` or loader mapping) can freeze at the time of installation, raising `ModuleNotFoundError: search.resource` until `pip install -e .` is explicitly re-run.
3. **Missing Root Entrypoint:** Contributor muscle memory expects `./bootstrap.sh` at the repository root, but the script resided exclusively at `scripts/bootstrap.sh`.

---

## 3. Implementation Plan

### Phase 1 — Root Entrypoint & Extended Bootstrap CLI Flags
* [x] Create repository-root executable wrapper or symlink `./bootstrap.sh` delegating to `scripts/bootstrap.sh`.
* [x] Add `--data` / `--fetch-data` flag to `scripts/bootstrap.sh`:
  - Automatically invokes `scripts/fetch_sources.sh` if raw sources are missing.
  - Compiles `data/bible.db` (via `python -m search.corpus.extract_kjv --compile` and `python -m search.corpus.extract_translations`).
  - Compiles `data/macula.db` (via `python -m search.macula.build_db --repo .`).
* [x] Add `--all-in-one` convenience flag combining `--ml`, `--dist`, `--data`, and `--verify`.

### Phase 2 — Stale Editable Install Detection & Auto-Refresh
* [x] In `scripts/bootstrap.sh`: Force a clean re-installation of the package in editable mode (`pip install --no-deps -e '.[test]'`) after dependency resolution to ensure module finders are updated.
* [x] In `scripts/verify_all.sh`: Add an early pre-flight sanity check testing imports of all registered modules under `search/` (including `search.resource`). If any fail with `ModuleNotFoundError`, provide an immediate human-actionable tip: `Run ./bootstrap.sh or pip install -e . to refresh module mappings`.

### Phase 3 — Verification & Clean-Clone Integration Test
* [x] Test `./bootstrap.sh --data --verify` in an isolated directory simulating a cold git clone.
* [x] Verify all 748+ tests pass and all F1–F4 validators exit 0 without manual interventions.

### Phase 4 — Documentation & Workflow Alignment
* [x] Update `README.md` Quickstart: replace multi-command manual sequence with `./bootstrap.sh --data --verify`.
* [x] Update `docs/WORKFLOW.md` developer onboarding and pull runbook.

---

## 4. Acceptance Criteria

1. `./bootstrap.sh` is directly executable from the repository root.
2. Running `./bootstrap.sh --data --verify` on a fresh clone with only Python installed runs from clone to 100% green verification without any intervening manual commands.
3. `scripts/verify_all.sh` detects stale editable installs and fails fast with a clear diagnostic message rather than cryptic tracebacks.
4. `bash scripts/verify_all.sh` passes completely.
