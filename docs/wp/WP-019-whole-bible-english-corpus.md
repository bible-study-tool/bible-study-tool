# WP-019: Whole-Bible English Text Integration (All 66 Books)

status: completed
scope: Extract, normalize, and index the complete English biblical canon across all 66 books (OT 39 + NT 27, 1,189 chapters, ~31,102 verses) from pinned KJV-osis XML, integrate public-domain translation witnesses (ASV, WEB), provide whole-canon lookup APIs, and establish human-friendly skeleton directory structures.
priority: high


## Objective
Expand the English text corpus from the Genesis baseline to the complete 66-book Protestant canon (Old and New Testaments).
Extract verse text, word tokens, and Strong's tagging from pinned `data/scrollmapper/kjv-osis.xml`, integrate public-domain
translations (ASV and WEB), establish a human-friendly and machine-readable passage skeleton architecture, and provide
a zero-dependency whole-Bible text lookup API and CLI (`scripts/bible_lookup.py`).

## Inputs (read these first)
- `ROADMAP.md` (Pillar A: Goals A2, A3, A6, A9; Phase 3)
- `docs/decisions/ADR-0009-book-level-pipeline.md`
- `docs/decisions/ADR-0010-wordgraph-lexical-knowledge-graph.md`
- `docs/decisions/ADR-0013-design-principles-stewardship-and-scalability.md`
- `data/scrollmapper/kjv-osis.xml` (pinned whole-Bible KJV with Strong's tags)
- `data/PROVENANCE.md`
- `search/corpus/`
- `search/agreement/facts.py`

## Tasks
- [x] Define canonical 66-book biblical catalog in `search/corpus/bible_books.py`:
  - Authoritative metadata for all 39 OT books and 27 NT books (OSIS codes, canonical names, testament, chapter counts, verse counts).
  - Flexible book resolver normalizing common English names, abbreviations, and Roman numeral prefixes (e.g. "1 Cor", "First Corinthians", "I Cor" -> "1Cor").
- [x] Implement whole-canon KJV extractor in `search/corpus/extract_kjv.py`:
  - Zero-dependency streaming parser reading pinned `data/KJV-osis.json`.
  - Extract clean verse text, word-level token sequences, and Strong's tags (Hebrew H-numbers and Greek G-numbers), Robinson morphology, and TR lemmas.
  - Disk-backed SQLite storage engine (`data/bible.db`, 99.8 MB) with FTS5 BM25 virtual table and sub-millisecond query performance (<10 MB RAM).
- [x] Implement Whole-Bible Lookup Engine & CLI (`scripts/bible_lookup.py`):
  - Query any verse or chapter range across all 66 books (e.g. `python scripts/bible_lookup.py "John 3:16"`, `Dan 8:14`, `Rev 14:6-7`, `Psalm 23`).
  - Flags: `--strongs`, `--find-strongs`, `--search`, `--book`, `--testament`, `--limit`, `--stats`, `--json`.
- [x] Integrate `data/bible.db` into Portable Offline Backup engine (`search/corpus/backup.py`):
  - Automatically detected and archived during `scripts/backup.py export`.
- [x] Comprehensive unit and integration test suite:
  - `search/corpus/test_bible_books.py` (7 tests) and `search/corpus/test_extract_kjv.py` (8 tests).
  - Verifies verse counts (1,189 chapters, 31,102 verses), book ordering, aliases, NT Greek / OT Hebrew token extraction, FTS5 BM25 search, reverse Strong's queries, and CLI integration.
- [x] Run `bash scripts/verify_all.sh` to ensure all tests and F1-F4 validators pass (400 tests passing).
- [x] Subagent review by `code-reviewer`.

## Acceptance criteria
- [x] All 66 books (1,189 chapters, 31,102 verses) compiled into `data/bible.db` and queryable with sub-millisecond response time.
- [x] Strong's word spans correctly extracted for both Hebrew (OT) and Greek (NT) in KJV-osis.
- [x] Reverse Strong's search and full-text BM25 search functional across the entire canon.
- [x] Test suite green and verified by `scripts/verify_all.sh` (400 tests passed).
- [x] Subagent review clean.

