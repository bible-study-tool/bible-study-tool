# WP-024: Textual Workstation Performance & Biblical Comprehension Tools

status: open
scope: Eliminate interaction-layer sluggishness via the persistent viewport pattern and lazy tab rendering (Phase 1), then implement plain-English verbal stems and multi-translation view (Phase 2-3).
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
- [ ] Create `search/corpus/grammar_nuance.py` to decompose Hebrew (Qal, Niphal, Piel, Hiphil, Hitpael) and Greek (Aorist, Present, Perfect, Middle) verbal morphology into plain-English theological explanations.
- [ ] Surface verbal nuance callout cards in the Lexicon and Syntax inspector tabs.

### Phase 3: Multi-Translation Parallel Engine
- [ ] Ingest public-domain ASV and WEB into `data/bible.db`.
- [ ] Implement translation comparison card and side-by-side toggle (`v`).

## Acceptance Criteria
- [ ] Verse cursor movement (`j`/`k`, up/down) is instantaneous with zero DOM allocations on keypress.
- [ ] Inactive tabs are never rendered during cursor movement.
- [ ] Switching tabs updates the viewport immediately with the active verse data.
- [ ] All 474+ tests pass clean via `bash scripts/verify_all.sh`.
