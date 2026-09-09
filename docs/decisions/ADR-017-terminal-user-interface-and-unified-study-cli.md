# ADR-017: Interactive Terminal User Interface (TUI) and Unified Study CLI

**Status:** Accepted · **Date:** 2026-09-04

## Context

1. **Foundational Engines Assembled:** Across WP-013 through WP-020, the repository has
   assembled comprehensive data layers:
   - Whole-Bible English text (KJV, all 66 books, 31,102 verses) with BM25 search
     and reverse Strong's index in `data/bible.db` (WP-019).
   - Whole-Bible original language linguistic syntax (Hebrew MT and Greek NT Nestle 1904,
     131,765 clauses, 338,218 constituents, 815,870 tokens) with semantic participant
     frames in `data/macula.db` (WP-018, WP-020).
   - Full Spirit of Prophecy / Adventist pioneer corpus with BM25 full-text search
     and canonical citation resolution in `data/egw.db` (WP-013, WP-016, WP-017).
   - Lexical concordances and glosses (`lexicons/strongs-lexicon.json`, `strongs-list.json`,
     TBESH, TBESG).
2. **Fragmented CLI Surface:** Previously, accessing these rich datasets required executing
   disparate standalone utility scripts (`scripts/bible_lookup.py`, `scripts/macula_lookup.py`,
   `scripts/egw_lookup.py`, `scripts/backup.py`). While functionally sound, this does not
   provide an intuitive, cohesive study experience for a student or pastor sitting down
   to study Scripture.
3. **Zero-Dependency Constraint (ADR-013):** Heavy terminal frameworks (e.g. `textual`,
   `rich`, `prompt_toolkit`) introduce large dependency trees, build wheels, and breaking API
   changes. We require a rock-solid, zero-dependency TUI and CLI built purely on Python's
   standard library (`curses`, `readline`, `sqlite3`, `argparse`) that runs out of the box
   on any standard Linux, macOS, BSD, or WSL terminal.

## Decision

1. **Unified Study CLI (`scripts/study.py`):**
   - Provide a single, polished command-line interface for all study workflows:
     * `python scripts/study.py` (default): Launches the interactive full-screen TUI.
     * `python scripts/study.py read <ref>`: Clean passage reader with verse formatting and optional Strong's tags (`-s`).
     * `python scripts/study.py study <ref>`: Comprehensive multi-dimensional study view combining English text, original language syntactic frames, Strong's lexical definitions, and Spirit of Prophecy cross-references.
     * `python scripts/study.py search <query>`: Unified search across both Bible and commentary corpuses.
     * `python scripts/study.py word <strongs>`: Deep lexical word study with definitions, transliterations, and Septuagint (LXX) equivalences.
     * `python scripts/study.py egw <query_or_token>`: Direct citation lookup or topic search across EGW writings.
     * `python scripts/study.py shell`: Interactive readline REPL with tab-completion and persistent history.
     * `python scripts/study.py tui`: Explicit launch of full-screen terminal interface.
2. **Interactive Terminal User Interface (`search/ui/tui.py`):**
   - Implement an interactive curses TUI featuring:
     * **Top Status Header:** Active passage reference, translation tag, and mode indicator.
     * **Main Reader Pane:** Scrollable Scripture text with verse numbers and toggleable inline Strong's concordance tags (`s`).
     * **Study Inspector Pane:** Tabbed inspector displaying:
       - Tab 1 (`Syntax`): Original language clause hierarchy and semantic participant frames (Agent/Subject, Action/Predicate Verb, Patient/Object, Prepositional context).
       - Tab 2 (`Lexicon`): Strong's dictionary definitions, transliterations, and glosses for words in the active verse.
       - Tab 3 (`Commentary`): Correlated Ellen G. White paragraphs and annotations.
       - Tab 4 (`Search`): Live interactive search results.
     * **Hotkeys & Navigation:** Intuitive navigation (`g` goto passage, `n`/`p` next/prev chapter, `Tab` toggle panes, `1-4` switch inspector tabs, `/` search, `q` quit).
3. **Graceful Degradation & Interactive Shell (`search/ui/shell.py`):**
   - If the terminal lacks curses support or the terminal window is constrained (<80x24), the application drops seamlessly into an ANSI-colorized interactive readline shell without crashing.
4. **Decoupled Study Service (`search/ui/study_service.py`):**
   - Consolidates queries across `BibleDB`, `MaculaSqliteDB`, `EgwDB`, and `strongs-lexicon.json` into typed data models (`PassageStudy`, `VerseStudy`, `WordStudyResult`, `UnifiedSearchResult`).

## Consequences

- Delivers a unified, beautiful, and human-friendly Bible study experience on the terminal.
- Zero new runtime dependencies; pure standard library.
- Fast sub-millisecond local SQLite queries with no network latency.
- Fulfills Roadmap Pillar D goals (D3 reading experience, D4 CLI polish).
