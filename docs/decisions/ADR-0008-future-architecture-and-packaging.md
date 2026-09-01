# ADR-0008: Future architecture & packaging direction (proposed)

**Status:** Proposed · **Date:** 2026-09-01

## Context

Session-level token burn in curation (reading multi-thousand-line JSONs into
context) exposed workflow friction; deterministic tooling
(`scripts/curate_context.py`, `scripts/wp_check.py`, data-driven corpus tests)
remedied it and became the de facto service layer. Separately, the project is
CLI-only, which blocks non-developer contributors (reviewers of AI content,
Bible students). This ADR records the brainstormed direction for the project's
future as the backend of an application; it is **not** an accepted decision.

## Proposed direction (uncommitted)

1. **Three-tier headless engine** (today's repo becomes Tier 1):
   - **Tier 1 — deterministic data & validation:** `materials/`, `lexicons/`,
     `correlations/`, F1-F4 validators, generators (unchanged, source of truth).
   - **Tier 2 — local service layer:** a localhost-only API (e.g. stdlib HTTP
     or FastAPI) exposing `/verse`, `/search`, `/curate-context`,
     `/validate`, `/status` backed by the existing modules.
   - **Tier 3 — UI clients:** desktop study app (readers) and a local web
     "Curator/Reviewer Studio" (contributors: side-by-side AI review, live
     F1-F4 badges, patch/PR export).

2. **Tooling maps directly to API endpoints:** `curate_context.py` →
   `/curate-context`; `wp_check.py` → live validator badge; data-driven
   `test_corpus.py` → self-scaling validation for new books/chapters.

3. **Tiered packaging:** end-users get a self-contained binary (Tauri or
   PyInstaller — no Python install); curators get the local web studio with
   git-based export; devs keep the CLI repo. A plain `.zip` of the Python
   repo is **not** a distribution path — it recreates the pipx/numpy
   environment friction seen in practice.

4. **Git + PROVENANCE remain the source of truth.** The UI operates on
   committed artifacts only; checksums and lineage are preserved.

## Consequences

* Lower contributor friction for AI-content review (the audience we want).
* Reuses today's tooling; no wasted work if the vision shifts.
* Risks: engineering cost, schema changes rippling to a UI, premature scope
  creep. Mitigation: finish Genesis 1 curation → packaging (G5) → UI (D).
* Open sub-decisions (not yet made): UI framework, API framework, packaging
  tool, local-binary distribution channel.

Related: ADR-0001 (deterministic/AI boundary), ADR-0005 (integrity before
scale), ADR-0006 (provenance/generated artifacts).