# WP-014: Whole-Bible Macula SQLite Architecture (Pillar B, ADR-0014)

status: completed
scope: Scalable, normalized SQLite database engine (`data/macula.db`) indexing tokens, syntactic clauses, constituent participant roles, Strong's alignments, and semantic domains across the biblical canon (ADR-0013, ADR-0014).
priority: high

## Objective
Evolve the Macula linguistic layer from single-book in-memory JSON (`macula-genesis.json`)
into a disk-backed, zero-dependency, normalized SQLite architecture (`data/macula.db`).
Provide sub-millisecond query performance across the full biblical canon (<15 MB RAM),
unlock relational syntactic queries (such as participant role queries by grammatical function),
and provide transparent dual-mode fallback to `lexicons/macula-genesis.json` in offline CI.

## Inputs (read these first)
- `ROADMAP.md` (Pillar B)
- `docs/decisions/ADR-0012-macula-hebrew-linguistic-integration.md`
- `docs/decisions/ADR-0013-design-principles-stewardship-and-scalability.md`
- `docs/decisions/ADR-0014-whole-bible-macula-sqlite-architecture.md`
- `search/macula/extract.py` & `search/macula/lookup.py`
- `scripts/macula_lookup.py`

## Tasks
- [x] Implement `search/macula/db.py`:
  - SQLite schema (`verses`, `clauses`, `constituents`, `tokens`, `strongs_crosswalk`).
  - B-tree indices on `tokens(strongs)`, `tokens(lxx_strongs)`, `tokens(verse_id)`, `constituents(role COLLATE NOCASE)`, `constituents(role_label COLLATE NOCASE)`.
  - Transactional bulk compiler inserting whole books with high throughput.
  - Query API: `lookup_strongs`, `lookup_verse`, `lookup_lxx`, `search_by_domain`, and `search_by_role`.
- [x] Implement builder CLI in `search/macula/build_db.py`:
  - Compiles `data/macula.db` from raw XML or JSON artifacts.
- [x] Update `search/macula/lookup.py` and `scripts/macula_lookup.py`:
  - Auto-detect `data/macula.db` with seamless fallback to `lexicons/macula-genesis.json`.
  - Add `--role` flag to CLI for participant role queries.
- [x] Create comprehensive test suite in `search/macula/test_db.py`.
- [x] Verify test suite with `bash scripts/verify_all.sh`.
- [x] Subagent review by `code-reviewer`.

## Acceptance criteria
- [x] SQLite database builds cleanly and indexes all 1,533 Genesis verses, 7,007 clauses, and 43,063 tokens.
- [x] Relational queries by Strong's, verse, LXX, domain, and role execute in <5 ms.
- [x] Tests verify 100% parity between SQLite queries and JSON fallback queries.
- [x] All tests passing (301 tests), verify_all.sh green.

