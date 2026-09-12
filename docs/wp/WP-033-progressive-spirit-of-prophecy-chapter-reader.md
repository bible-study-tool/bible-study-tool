# WP-033: Progressive Spirit of Prophecy Narrative Navigation & Chapter Reader

status: open
scope: Pillar A (Commentary / EGW Corpus), Pillar D (Immersive Reading) — Progressive disclosure commentary hierarchy from compact chips to full-chapter immersive reading.
priority: medium

## Objective

Eliminate visual clutter in the commentary inspector by displaying compact, single-line reference chips by default, while enabling one-click transitions into a full contextual chapter reader that can be maximized with `z` for uninterrupted study.

## Inputs (read these first)
- `docs/decisions/ADR-025-visual-identity-and-anti-slop-design-charter.md`
- `search/linking/egw.py`
- `web/` (workstation components)

## Tasks

### Phase 1 — Compact Reference Chip Redesign
- [ ] Refactor commentary listings in inspector: display book code, chapter, paragraph, and a 1-line summary chip.
- [ ] Provide direct "Read Full Chapter" trigger on each chip.

### Phase 2 — Contextual Chapter Reader Drawer
- [ ] Add `get_chapter(book_code: str, chapter_num: int) -> list[dict[str, Any]]` helper to `EgwDB` in `search/linking/egw.py`.
- [ ] Build a full-chapter commentary reader pane in the workstation.
- [ ] Clicking a reference chip opens the exact chapter in the reader, automatically scrolling to and highlighting the target paragraph.

### Phase 3 — Panel Zoom Integration (`z`)
- [ ] Allow pressing `z` (or `Shift + F`) while in the chapter reader to expand it into an immersive reading canvas.

### Phase 4 — Sequential Chapter Traversal & Pagination
- [ ] Add Previous Chapter / Next Chapter navigation buttons.
- [ ] Maintain pagination fidelity matching the official physical book print pages.

### Phase 5 — Verification & Validation
- [ ] Tests ensuring paragraph anchoring, offline database query performance, and state persistence.
- [ ] Run `scripts/verify_all.sh`.

## Conventions that apply
- ADR-013 (Stewardship and Scalability)
- ADR-024 (GUI-First Architecture)
- ADR-025 (Anti-Slop Charter)

## Acceptance criteria
- [ ] Inspector commentary tab shows clean, single-line chips rather than massive wall-of-text dumps.
- [ ] Clicking a chip loads the full chapter with the relevant paragraph highlighted.
- [ ] Pressing `z` maximizes the chapter reader for sustained, distraction-free reading.
