# WP-024: Textual Workstation Performance & Biblical Comprehension Tools

status: completed
scope: Eliminate interaction-layer sluggishness via the persistent viewport pattern and lazy tab rendering (Phase 1), then implement plain-English verbal stems (Phase 2) and multi-translation parallel engine (Phase 3).
priority: high

## Objective
Deliver a fluid, instant, 60 FPS terminal study workstation (<1ms per verse step) and advance the project's North Star of deep biblical comprehension by providing plain-English theological verb nuances and translation comparisons (per ADR-0013 and ADR-0020).

## Inputs
- `ROADMAP.md` (Pillars B, D)
- `docs/decisions/ADR-0020-persistent-viewport-workstation-and-comprehension-engine.md`
- `docs/decisions/ADR-0019-accessible-original-languages-and-commentary-integration.md`
- `docs/decisions/ADR-0018-textual-study-workstation-and-themes.md`
- `docs/decisions/ADR-0013-design-principles-stewardship-and-scalability.md`
- `search/ui/app.py`
- `search/ui/study_service.py`
- `search/ui/themes.py`

## Tasks

### Phase 1: Interaction Performance & Persistent Viewports (Immediate Step)
- [x] Replace dynamic widget mounting/unmounting in `search/ui/app.py` with persistent `Static` viewports (`#syntax-body`, `#lexicon-body`, `#commentary-body`, `#search-body`).
- [x] Implement lazy tab rendering: on cursor step, update only the active tab; track dirty state for inactive tabs so they update on activation.
- [x] Pre-render tab contents into Rich `Group` / `Text` / `Table` renderables, reducing per-step latency to <1ms.
- [x] Batch mount verse widgets during passage load to eliminate sequential layout reflows.
- [x] Add async headless tests in `search/ui/test_textual.py` validating instantaneous navigation and lazy rendering.
- [x] Verify full test suite with `bash scripts/verify_all.sh`.
- [x] Subagent review with `code-reviewer`.

### Phase 2: Plain-English Verbal Stems & Theological Nuances
- [x] Create `search/corpus/grammar_nuance.py` to decompose Hebrew (Qal, Niphal, Piel, Hiphil, Hitpael) and Greek (Aorist, Present, Perfect, Middle) verbal morphology into plain-English theological explanations.
- [x] Surface verbal nuance callout cards in the Lexicon and Syntax inspector tabs.
- [x] Add comprehensive test suites (`search/corpus/test_grammar_nuance.py`, `search/ui/test_ui.py`, `search/ui/test_textual.py`).
- [x] Subagent review with `code-reviewer`.

### Phase 3: Multi-Translation Parallel Engine
- [x] Pinned upstream public-domain translations (ASV 1901, BSB 2020, YLT 1898) with SHA-256 provenance in `data/PROVENANCE.md` and `scripts/fetch_sources.sh`.
- [x] Extended `BibleDB` (`search/corpus/extract_kjv.py`) with `translations` and `translation_verses` schema and batch queries (`get_verse_translations`, `get_chapter_translations`).
- [x] Implemented ingestion engine in `search/corpus/extract_translations.py` (ingested 31,102 verses each for ASV, BSB, and YLT).
- [x] Integrated into `VerseStudy.translations` and `StudyService` with chapter-level batch prefetching.
- [x] Surfaced in Textual workstation:
  - Inspector Tab 4: `Parallel` (`tab-parallel`) with full translation comparison cards.
  - Reader Pane toggle: `v` key toggles stacked parallel translation lines under each verse.
- [x] Added unit and async tests (`search/corpus/test_extract_translations.py`, `search/ui/test_ui.py`, `search/ui/test_textual.py`).
- [x] Full verification with `bash scripts/verify_all.sh` (511 tests passing clean).
- [x] Subagent review with `code-reviewer`.

## Acceptance Criteria
- [x] Verse cursor movement (`j`/`k`, up/down) is instantaneous with zero DOM allocations on keypress.
- [x] Inactive tabs are never rendered during cursor movement.
- [x] Switching tabs updates the viewport immediately with the active verse data.
- [x] Parallel translations (KJV, BSB, ASV, YLT) are available both as an inspector comparison tab and stacked reader view.
- [x] All 511 tests pass clean via `bash scripts/verify_all.sh`.
