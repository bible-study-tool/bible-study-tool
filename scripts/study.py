#!/usr/bin/env python3
"""Unified human-friendly CLI and TUI for Adventist Bible Study Tool (WP-021, WP-022, ADR-017, ADR-018).

Provides an integrated, beautiful terminal interface for Scripture reading,
original language syntactic exploration (Macula), Strong's concordances,
and Spirit of Prophecy commentary.

Usage:
  python scripts/study.py                       Launch full-screen Textual TUI workstation (default)
  python scripts/study.py --theme dracula       Launch Textual TUI with Dracula theme
  python scripts/study.py --curses              Launch classic curses TUI fallback
  python scripts/study.py read "John 3:16"      Read scripture passage with verse formatting
  python scripts/study.py study "Rev 14:6-7"    Deep study view (Scripture + Syntax + Lexicon + EGW)
  python scripts/study.py word H1254            Word study (Hebrew/Greek lemma, definition, LXX)
  python scripts/study.py search "covenant"     Unified search across Bible and commentary
  python scripts/study.py egw "PP.57.1"         Look up EGW citation or search topics
  python scripts/study.py shell                 Launch interactive readline REPL
  python scripts/study.py tui                   Explicitly launch TUI workstation
"""

from __future__ import annotations

import sys
from search.ui.cli import (
    DEFAULT_THEME,
    TEXTUAL_AVAILABLE,
    THEMES,
    launch_interactive_tui as _launch_interactive_tui,
    main,
)

if __name__ == "__main__":
    raise SystemExit(main())
