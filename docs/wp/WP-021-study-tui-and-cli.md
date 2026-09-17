# WP-021: Interactive Terminal User Interface (TUI) & Unified Study CLI

status: complete
scope: Build a zero-dependency, human-friendly, interactive Terminal User Interface (TUI) and unified CLI (`scripts/study.py`) bringing together Scripture reading, original language syntax & semantic frames (Macula), Strong's lexicons, and Spirit of Prophecy (EGW) correlations into an intuitive terminal Bible study environment.
priority: high

## Objective
Deliver an interactive terminal experience for personal and pastoral Bible study.
Enable full-screen passage navigation, original language exploration, Strong's concordance lookups,
and commentary correlations in an integrated curses interface, alongside a rich, polished CLI and
interactive readline REPL.

## Inputs (read these first)
- `ROADMAP.md` (Pillar D: Goals D3, D4)
- `docs/decisions/ADR-017-terminal-user-interface-and-unified-study-cli.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `search/corpus/extract_kjv.py` (`BibleDB`)
- `search/macula/db.py` (`MaculaSqliteDB`)
- `search/macula/enrichment.py` (`get_verse_semantic_frame`, `get_translation_equivalences`)
- `search/linking/egw.py` (`EgwDB`)
- `lexicons/strongs-lexicon.json`

## Tasks
- [x] Implement Unified Study Service (`search/ui/study_service.py`):
  - Consolidate `BibleDB`, `MaculaSqliteDB`, `EgwDB`, and Strong's lexicon into a high-level API.
  - Provide `get_passage_study(passage_ref)` with English text, Macula syntax frames, Strong's glosses, and top EGW cross-references.
  - Provide `search_unified(query)` searching both Scripture and EGW writings with BM25 ranking.
  - Provide `word_study(strongs_or_lemma)` combining dictionary definition, transliteration, Bible occurrences, and Septuagint (LXX) translation equivalences.
- [x] Implement Human-Friendly Formatting Engine (`search/ui/formatting.py`):
  - ANSI terminal styling with auto-detection of TTY and color support.
  - Unicode box-drawing panels, colored verse numbers, Strong's tags, and tables.
- [x] Implement Interactive Readline REPL Shell (`search/ui/shell.py`):
  - Interactive prompt with persistent history and tab-completion.
  - Commands: `read <ref>`, `study <ref>`, `search <query>`, `word <strongs>`, `egw <query>`, `next`, `prev`, `help`, `quit`.
- [x] Implement Full-Screen Curses TUI (`search/ui/tui.py`):
  - Zero external dependencies using standard library `curses`.
  - Top header with active reference, translation, and mode.
  - Left/Top pane: scrollable Scripture reader with optional Strong's tags (`s`).
  - Right/Bottom pane: tabbed study inspector (1: Syntax & Frames, 2: Lexicon, 3: Spirit of Prophecy, 4: Search).
  - Bottom command bar with quick jump (`g` for goto passage, `n`/`p` for chapter navigation, `/` for search, `?` for help).
  - Graceful fallback to readline shell if terminal is too small or non-interactive.
- [x] Implement Unified CLI Entry Point (`scripts/study.py`):
  - Subcommands: `read`, `study`, `search`, `word`, `egw`, `frame`, `shell`, `tui`.
  - Default invocation (`python scripts/study.py`) launches the TUI directly.
- [x] Add `search.ui` to `pyproject.toml`.
- [x] Comprehensive unit test suite (`search/ui/test_ui.py`, 27 tests).
- [x] Verification with `scripts/verify_all.sh` (438 tests passing).
- [x] Subagent review by `code-reviewer`.

## Acceptance criteria
- [x] Interactive curses TUI runs with zero external dependencies and smooth navigation across the 66-book Bible.
- [x] Deep study view (`study.py study`) renders English text, original language frames, Strong's definitions, and EGW correlations.
- [x] Interactive readline shell (`study.py shell`) functional in all terminal environments.
- [x] All tests passing in `scripts/verify_all.sh` with clean code review.
