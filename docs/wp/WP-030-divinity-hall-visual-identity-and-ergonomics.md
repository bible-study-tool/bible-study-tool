# WP-030: Divinity Hall Visual Identity & Workspace Ergonomics

status: open
scope: Pillar D (GUI / UX) — Foundation layout, draggable split pane, focus modes, warm sepia design tokens, typography, and progressive disclosure primitives.
priority: high

## Objective

Transform the local web interface into the "Divinity Hall Desk" environment defined in ADR-025: implement the draggable 65/35 split, the `f` Scripture Focus Mode, the `z` / `Shift + F` panel zoom, tab double-click maximize, distinct typographic tokens, and collapsible morphology controls.

## Inputs (read these first)
- `docs/decisions/ADR-025-visual-identity-and-anti-slop-design-charter.md`
- `docs/decisions/ADR-024-gui-first-architecture-tui-as-mode.md`
- `web/index.html`
- `web/styles.css`
- `web/app.js`

## Tasks

### Phase 1 — Draggable Split Pane & Layout System
- [x] Insert explicit pane divider `#pane-divider` with accessibility roles in `web/index.html`.
- [x] Implement pointer event listeners (`pointerdown`, `pointermove`, `pointerup`, `setPointerCapture`) in `web/app.js`.
- [x] Constrain resizing between 40% and 80% Scripture width.
- [x] Implement double-click on divider to restore default 65/35 ratio.
- [x] Persist split position to `localStorage` (`abst.split_percent`).
- [x] Style divider in `web/styles.css` with subtle hover cues and `cursor: col-resize`.

### Phase 2 — Distraction-Free Modes (`f` and `z`)
- [ ] Implement global shortcut guard ignoring single-key navigation when focus is inside editable elements (`input`, `textarea`, `select`, `[contenteditable]`).
- [ ] Shortcut `f`: toggles Scripture Focus Mode (collapses inspector pane, centers reading column to 65–75ch).
- [ ] Shortcut `z` / `Shift + F`: toggles Panel Zoom for whichever panel or tab has active focus.
- [ ] Tab double-click: expands active study tab to full-width workstation; `Escape` restores split view.

### Phase 3 — Palette, Tokens & Header Cleanup
- [ ] Relocate theme picker out of top header into Settings modal (⚙).
- [ ] Define CSS custom properties for Core Accent Palette (Deep Indigo, Muted Gold, Quiet Olive) and warm sepia light/dark substrates.
- [ ] Establish distinct color tokens for Scripture text, verse numbers, and Strong's concordances.
- [ ] Implement togglable alternating verse zebra shading (default: off).

### Phase 4 — Progressive Disclosure Primitives
- [ ] Refactor dense Hebrew/Greek morphology and translation equivalents behind semantic `<details><summary>` progressive disclosure controls (`▸`/`▾`).

### Phase 5 — Verification & Accessibility
- [ ] Verify WCAG AAA contrast across light sepia and dark walnut substrates.
- [ ] Add automated tests in `search/ui/test_web.py` for DOM structure, classes, and divider attributes.
- [ ] Ensure `scripts/verify_all.sh` is green.

## Conventions that apply
- ADR-013 (Stewardship and Scalability)
- ADR-024 (GUI-First Architecture)
- ADR-025 (Visual Identity & Anti-Slop Charter)
- AGENTS.md Non-negotiable 2 (One step at a time)

## Acceptance criteria
- [ ] Dragging divider smoothly resizes panels; double-click snaps back to 65/35.
- [ ] Shortcut `f` cleanly enters/exits Scripture Focus Mode.
- [ ] Shortcut `z` / `Shift + F` maximizes active panel; `Escape` restores.
- [ ] Header is uncluttered, retaining only navigation, search, and Settings button.
- [ ] Dense morphological listings default to collapsed state with disclosure toggle.
