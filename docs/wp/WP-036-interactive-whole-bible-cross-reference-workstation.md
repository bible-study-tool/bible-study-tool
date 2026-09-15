# WP-036: Interactive Whole-Bible Cross-Reference Workstation UI

status: open
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
* [ ] Add `GET /api/xrefs?verse=...&limit=25` endpoint to `search/ui/web_server.py`:
  - Returns JSON list of cross references with target verse text snippet, testament, book name, and vote score.
* [ ] Update `StudyService.get_passage_study()` to attach TSK cross-reference summaries directly to each `VerseStudy` payload.
* [ ] Expose `xrefs_url: "/api/xrefs"` in `GET /api/health`.

### Phase 2 — Web GUI Cross-Reference Inspector
* [ ] In `web/index.html` & `web/app.js`:
  - Enhance the Cross References tab (`#panel-refs`):
    - **Section 1: Curated Theological Links (Layer A)** — high-touch annotations with Spirit of Prophecy and covenant themes.
    - **Section 2: Canonical Cross References (Layer B)** — vote-ranked TSK connections rendered as interactive chips.
  - Render target verse text preview beneath or alongside each chip on hover/focus.
  - Clicking any cross-reference chip calls `navigate(targetRef)`, immediately centering the target Scripture in the reading pane.
* [ ] In `web/styles.css`:
  - Style TSK chips using design tokens (`.xref-chip`, `.xref-votes-badge`, `.xref-preview-card`).
  - Strict compliance with ADR-025: WCAG AAA contrast, no blur, `@media (prefers-reduced-motion: reduce)`.

### Phase 3 — Textual TUI Integration
* [ ] In `search/ui/app.py`:
  - Populate Tab 3 (`Cross References`) using `StudyService.get_verse_cross_references(...)` for any active verse.
  - Display ranked target reference, target verse text snippet, and relevance votes.
  - Hitting `Enter` on any cross-reference row jumps the reading viewport directly to that reference.

### Phase 4 — Testing & Verification
* [ ] In `search/ui/test_web.py`:
  - Test `/api/xrefs` with valid reference, limits, and non-existent reference.
  - Test Web DOM elements and JavaScript click/navigation handlers for TSK chips.
* [ ] In `search/ui/test_textual.py`:
  - Test cross-reference panel rendering for Genesis 1:1 and non-curated passages (e.g. Genesis 4:9, Revelation 12:1).

---

## 4. Acceptance Criteria

1. Navigating to any verse in Genesis, Psalms, Isaiah, or Revelation in the Web UI immediately renders its ranked TSK cross-references.
2. Clicking a TSK cross reference smoothly navigates to that passage.
3. The Textual TUI displays TSK cross-references in Tab 3 for any selected verse.
4. All automated web and TUI tests pass; `bash scripts/verify_all.sh` exits 0.
