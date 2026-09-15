# WP-036: Interactive Whole-Bible Cross-Reference Workstation UI

status: done
scope: Pillar D (Application & Workstation UX), ADR-017, ADR-018, ADR-024, ADR-025, ADR-026
priority: high
decisions: [ADR-013](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md), [ADR-024](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-024-gui-first-architecture-tui-as-mode.md), [ADR-025](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-025-visual-identity-and-anti-slop-design-charter.md), [ADR-026](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-026-treasury-of-scripture-knowledge-cross-references.md)

---

## 1. Objective

Surface the ~340,000 whole-Bible Treasury of Scripture Knowledge (TSK) cross-references across both the Web GUI (Study Room Desk) and Textual TUI workstations, providing instant reciprocal navigation, quick-glance verse previews, and clear visual distinction between curated theological notes (Layer A) and canonical TSK cross-references (Layer B).

---

## 2. Background

With [WP-035](file:///home/archvm/projects/bible-study-tool/docs/wp/WP-035-treasury-of-scripture-knowledge-tsk-integration.md) ingesting TSK into `data/bible.db`, every verse in the Bible has structured cross references. This work package surfaces those cross references in the user interface in accordance with [ADR-025](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-025-visual-identity-and-anti-slop-design-charter.md) (Anti-Slop Design Charter: dignified typography, progressive disclosure, WCAG AAA contrast, zero frosted glass or laggy animations).

---

## 3. Implementation Plan

### Phase 1 — Web Server API & Passage Payload Injection
* [x] Add `GET /api/xrefs?verse=...&limit=25` endpoint to `search/ui/web_server.py`:
  - Returns JSON list of cross references with target verse text snippet, testament, book name, and vote score.
* [x] Update `StudyService.get_passage_study()` to attach TSK cross-reference summaries directly to each `VerseStudy` payload.
* [x] Expose `xrefs_url: "/api/xrefs"` in `GET /api/health`.

### Phase 2 — Web GUI Cross-Reference Inspector
* [x] In `web/index.html` & `web/app.js`:
  - Added Cross-Refs tab (`#panel-xrefs`) with full ARIA attributes (`aria-controls`, `aria-labelledby`).
  - **Section 1: Curated Theological Links (Layer A)** — high-touch annotations rendered as cards with category label and target chips.
  - **Section 2: Canonical Cross References (Layer B)** — vote-ranked TSK connections rendered as interactive chips with text preview.
  - Clicking any cross-reference chip calls `navigate(targetRef)` or `openCommentaryChapterByToken()` for EGW tokens.
  - Event delegation on `.xrefs-workspace` eliminates per-card listener closures.
  - Keyboard shortcuts: `x` / `3` open Cross-Refs workstation.
* [x] In `web/styles.css`:
  - Styled TSK chips using design tokens (`.xref-card`, `.xref-votes-pill`, `.xref-snippet`).
  - Strict compliance with ADR-025: WCAG AAA contrast, no blur, `@media (prefers-reduced-motion: reduce)`.

### Phase 3 — Textual TUI Integration
* [x] In `search/ui/app.py`:
  - Added Tab 6 (`6: Cross-Refs`) with keybindings `6` and `x`.
  - Displays Layer A Curated notes then Layer B TSK references with target, preview, and vote counts.
  - `action_tab_xrefs()` navigates Layer A first (EGW tokens routed to commentary), then Layer B as fallback.
  - Integrated into dirty-tab lazy rendering lifecycle.

### Phase 4 — Testing & Verification
* [x] In `search/ui/test_web.py`:
  - Tests `/api/xrefs` with valid reference, limits, min_votes, and missing-param 400.
  - Tests Web DOM elements, ARIA attributes, JS event delegation, and EGW routing guard.
* [x] In `search/ui/test_textual.py`:
  - Tests Tab 6 rendering, dirty state tracking, and navigation action.

---

## 4. Acceptance Criteria

1. [x] Navigating to any verse in Genesis, Psalms, Isaiah, or Revelation in the Web UI immediately renders its ranked TSK cross-references.
2. [x] Clicking a TSK cross reference smoothly navigates to that passage.
3. [x] The Textual TUI displays TSK cross-references in Tab 6 for any selected verse.
4. [x] All automated web and TUI tests pass; `bash scripts/verify_all.sh` exits 0.

## 5. Completion Notes

- 763 tests collected and passing (70 web + 38 TUI + remainder corpus/integration).
- `bash scripts/verify_all.sh` → ALL CHECKS PASSED ✔.
- Subagent code review completed: 2 bugs fixed (EGW `openCommentaryToken` → `openCommentaryChapterByToken`; Layer A/B priority inversion in TUI), 2 improvements applied (event delegation, ARIA `aria-controls`/`aria-labelledby`).
- Committed: `feat(ui): interactive whole-bible cross-reference workstation (WP-036)`.
