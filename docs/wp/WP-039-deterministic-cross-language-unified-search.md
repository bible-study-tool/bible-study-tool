# WP-039: Deterministic Cross-Language & Unified Multi-Database Search

status: in-progress
scope: Pillar C (C3, C4), Pillar D (D1, D3, D4) — Implement a 100% deterministic, zero-ML, sub-millisecond search engine unifying all project databases (bible.db KJV + parallel translations ASV/BSB/YLT, macula.db Hebrew/Greek lemmas & semantic domains, egw.db Spirit of Prophecy, and materials/ curated notes) with bidirectional query expansion (English <-> Strong's <-> Hebrew/Greek Lemma <-> TSK), smart omnibox routing, fine-grained search filters and advanced syntax, and a serene Study Room Desk search workstation.
priority: high

## Objective
Unify all textual and linguistic databases in the Adventist Bible Study Tool under a single, fast, deterministic search engine. Provide a smart omnibox that routes passage references to Scripture and free text/Strong's numbers to a dedicated Search workstation. Equip scholars with both intuitive source filter pills and deep, fine-grained query capabilities (advanced syntax like `book:`, `testament:`, `translation:`, `strong:`, `domain:`, `egw:`, exact `"quotes"`, boolean operators, and collapsible options) without visually polluting the tranquil Study Room aesthetic.

## Inputs (read these first)
- `data/bible.db`: `verses` (KJV 31,102 verses, indexed in `bible_fts`) and `translation_verses` (ASV, BSB, YLT 93,306 verses)
- `data/macula.db`: `tokens` (815,870 rows with lemma, morph, gloss, Louw-Nida and SDBH domains) and `strongs_crosswalk` (13,538 entries)
- `data/egw.db`: `paragraphs` (~150,000+ commentary paragraphs, indexed in `egw_fts`)
- `materials/`: curated markdown notes indexed in-memory via `entries_fts`
- `lexicons/`: Strong's lexicon and TBES definitions
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md` (Zero ML / stewardship)
- `docs/decisions/ADR-024-gui-first-architecture-tui-as-mode.md` (Zero-build frontend)
- `docs/decisions/ADR-025-visual-identity-and-anti-slop-design-charter.md` (Typography & quiet UI)
- `docs/decisions/ADR-027-sqlite-storage-and-single-file-verification.md` (FTS virtual table exclusion from checksums)

## Tasks
- [ ] Task 1: Multi-Translation SQLite FTS indexing in `search/corpus/extract_kjv.py` (`ensure_translations_fts()`, multi-translation `search()`) + unit tests in `search/corpus/test_translations_fts.py`.
- [ ] Task 2: Macula Lexical & Semantic Search Engine in `search/macula/search.py` (Strong's lookup, Greek/Hebrew lemma and gloss matching, transliteration, Louw-Nida & SDBH domain search) + unit tests in `search/macula/test_search.py`.
- [ ] Task 3: Deterministic Query Expansion Bridge & Advanced Syntax Parser in `search/corpus/search_bridge.py` (`DeterministicSearchBridge`, query classifier, lexical expansion, operator parsing for `book:`, `testament:`, `translation:`, `strong:`, `domain:`, `egw:`, exact `"quotes"`, boolean logic, BM25 score normalization) + unit tests in `search/corpus/test_search_bridge.py`.
- [ ] Task 4: REST API & Study Service integration in `search/ui/study_service.py` and `search/ui/web_server.py` (`/api/search` endpoint with query, expansion, categorized counts, facets) + unit tests in `search/ui/test_search_api.py`.
- [ ] Task 5: Web & Desktop Workstation UI in `web/index.html`, `web/app.js`, `web/styles.css`:
  - Smart omnibox routing: references navigate to Scripture reader; free-text/Strong's auto-routes to Search workstation tab.
  - `#tab-search` and `#panel-search` workstation container.
  - Source filter pills: All, Scripture, Translations, Original Languages, Commentary, Curated.
  - Collapsible Advanced Search drawer: fine-grained dropdowns/checkboxes and syntax cheat sheet tips.
  - Query expansion chip banner (discovered Hebrew/Greek roots and Strong's numbers).
  - High-fidelity biblical typography rendering and instant navigation into Scripture or Commentary.
  - Unit tests in `search/ui/test_web.py`.
- [ ] Task 6: CLI & Terminal enhancements in `search/ui/cli.py` and `search/ui/shell.py` for unified multi-database search results.
- [ ] Task 7: Full verification with `scripts/verify_all.sh`, subagent code review, and git synchronization.

## Conventions that apply
- **Deterministic core (AGENTS.md Non-negotiable 1):** Zero external ML downloads, zero network calls during search.
- **Data integrity (ADR-027):** Virtual FTS tables do not invalidate `data/INTEGRITY.json` canonical hashes.
- **Zero-build assets (ADR-024):** No npm or compilation required in `web/`.
- **Anti-slop visual charter (ADR-025):** WCAG AAA contrast, serene literary aesthetics, progressive disclosure for advanced features.

## Acceptance criteria
- [ ] `ensure_translations_fts()` creates and indexes ASV, BSB, and YLT verses without affecting canonical integrity.
- [ ] Macula search resolves Strong's codes (`H7225`, `G2424`), lemmas, transliterations, and semantic domains.
- [ ] Query expansion bridge links English terms (e.g. `covenant`, `sanctuary`) to Strong's codes and Greek/Hebrew lemmas.
- [ ] Advanced syntax (`book:`, `testament:`, `translation:`, `strong:`, `domain:`, `egw:`, `"quotes"`) properly filters results.
- [ ] Top omnibox routes valid references to Scripture view and search queries to the Search tab.
- [ ] Web and desktop search workstation displays source filter pills, collapsible advanced options, expansion chips, and highlighted snippets.
- [ ] Clicking a verse or commentary result navigates directly to that passage or chapter.
- [ ] `bash scripts/verify_all.sh` remains 100% green with all new tests passing.

## Notes / findings
- FTS5 virtual tables in SQLite are explicitly omitted from canonical table hashing in `search/validation/db_integrity.py` (`CANONICAL_TABLES = {"books", "verses", "notes", "topics", "tokens", "strongs_crosswalk", "paragraphs"}`). Creating `translations_fts` preserves cryptographic integrity.
