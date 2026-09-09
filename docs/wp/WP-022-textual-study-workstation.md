# WP-022: Modern Textual Study Workstation & Theme System

status: complete
scope: Build a modern, highly responsive, mouse-enabled terminal study workstation using Textual (`search/ui/app.py`), with terminal background transparency as default, popular standard themes (Dracula, Catppuccin, Tokyo Night, Nord, Gruvbox, Solarized), asynchronous background query workers, passage navigation, and multi-tabbed original language & commentary inspection.
priority: high

## Objective
Deliver a fast, fluid, modern terminal application for in-depth Scripture study, resolving the performance limitations and primitive interaction of curses while preserving full offline capability and visual beauty.

## Inputs (read these first)
- `ROADMAP.md` (Pillar D: Goals D3, D4)
- `docs/decisions/ADR-018-textual-study-workstation-and-themes.md`
- `docs/decisions/ADR-017-terminal-user-interface-and-unified-study-cli.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `search/ui/study_service.py` (`StudyService`)
- `search/corpus/extract_kjv.py` (`BibleDB`)
- `search/macula/db.py` (`MaculaSqliteDB`)
- `search/linking/egw.py` (`EgwDB`)

## Tasks
- [x] Add `textual` dependency to `pyproject.toml` and `.venv`.
- [x] Implement Theme System (`search/ui/themes.py`):
  - Transparent (default, preserves host terminal colors and background).
  - Dracula, Catppuccin Mocha, Tokyo Night, Nord, Gruvbox Dark, Solarized Dark.
  - Theme manager with hotkey toggle (`t`).
- [x] Implement Modern Textual Workstation (`search/ui/app.py`):
  - Top header with passage reference and active theme indicator.
  - Left Scripture Reader pane: smooth scrolling, colored verse markers, Strong's concordance tags toggle (`s`), click-to-inspect verse.
  - Right Study Inspector pane with native Textual tabs:
    - Tab 1 (`Syntax`): Original Hebrew/Greek text and Macula clause semantic frames.
    - Tab 2 (`Lexicon`): Strong's lexical definitions, transliterations, and occurrence counts.
    - Tab 3 (`Commentary`): Ellen G. White Spirit of Prophecy commentary with rich Markdown rendering.
    - Tab 4 (`Search`): Live interactive search results with instant preview.
  - Asynchronous query loading (`@work`) for non-blocking UI.
  - Passage jump modal dialog (`g` / `Ctrl+P`).
  - Search modal dialog (`/`).
  - Keyboard navigation (vi-keys `j`/`k`, `n`/`p` for chapter navigation, `f` for focus mode, `q` to quit).
  - Mouse click and scroll wheel support.
- [x] Wire Textual App into `scripts/study.py` (with fallback to curses/shell).
- [x] Comprehensive unit tests for themes and Textual components (`search/ui/test_textual.py`).
- [x] Verify full integrity with `scripts/verify_all.sh`.
- [x] Subagent review by `code-reviewer`.

## Acceptance Criteria
- [x] Textual workstation launches with default transparent background respecting host terminal.
- [x] Instant theme switching (`t`) across standard developer themes.
- [x] Sub-millisecond navigation without UI stutter or freezing (async workers).
- [x] Full mouse support (verse click, scroll wheel, tab clicks).
- [x] All tests in `scripts/verify_all.sh` passing green.
