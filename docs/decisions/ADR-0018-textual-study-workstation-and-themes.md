# ADR-0018: Textual Study Workstation and Theme System

**Status:** Accepted · **Date:** 2026-09-04

## Context

1. **Curses Ceiling (ADR-0017 review):** WP-021 delivered a standard-library curses TUI.
   While zero-dependency, curses reaches immediate structural limits for a serious study
   workstation:
   - Manual coordinate math and text-clipping arithmetic on every window resize.
   - Brittle cross-terminal mouse wheel and click event handling.
   - Lack of a native asynchronous event loop and background worker model (`@work`).
   - Absence of modern UI components: native tabs, collapsible accordions, modal dialogs,
     command palette, and rich Markdown rendering for commentary.
2. **User Experience & Scalability:** Users studying Scripture require a smooth, responsive,
   mouse-friendly application with modern terminal aesthetics. Terminal transparency
   (preserving the user's desktop wallpaper and terminal palette) is highly valued,
   alongside standard beloved developer themes (Dracula, Catppuccin, Tokyo Night, Nord,
   Gruvbox, Solarized).
3. **Open-Source Standard (ADR-0013):** Textual (built by Textualize / Will McGugan) is the
   modern Python standard for terminal desktop applications. It provides full async workers,
   CSS styling (`TCSS`), rich widget hierarchies, and mouse events without requiring a C or
   Rust compilation toolchain.

## Decision

1. **Adopt Textual for Interactive Study Workstation (`search/ui/app.py`):**
   - Implement the interactive study interface using Textual.
   - Run SQLite queries and linguistic lookups in asynchronous worker threads (`@work`),
     ensuring the UI remains at 120 FPS without dropped frames.
   - Dual-pane layout: Scripture Reader (left) + Tabbed Study Inspector (right) with
     Original Syntax, Strong's Concordance, Spirit of Prophecy (Markdown), and Search.
   - Mouse interaction: click-to-select verses, click-to-lookup Strong's numbers, and
     smooth wheel scrolling.
   - Fast passage jump modal (`g` / `Ctrl+P`) and unified search modal (`/`).
2. **Theme System with Transparent Default (`search/ui/themes.py`):**
   - Provide a theme engine where **Transparent** is the default (using `background: transparent;`
     in TCSS to honor the user's terminal emulator theme).
   - Bundle popular standard themes: Dracula, Catppuccin Mocha, Tokyo Night, Nord,
     Gruvbox Dark, Solarized Dark.
   - Allow cycling themes on the fly via hotkey (`t`).
3. **Graceful Fallback & Headless Stability:**
   - Standalone CLI subcommands (`study.py read`, `study.py study`, `study.py search`, etc.)
     continue to operate directly with fast ANSI output.
   - If Textual is not installed or the environment is a dumb terminal, fallback seamlessly
     to the interactive readline shell.

## Consequences

- Delivers a state-of-the-art terminal Bible study workstation with growth potential.
- Adds `textual` to package dependencies in `pyproject.toml`.
- Retains sub-millisecond query performance enabled by the Step 1 SQLite index optimizations.
