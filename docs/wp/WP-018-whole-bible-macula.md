# WP-018: Whole-Bible Macula Linguistic Integration (Pillar B, ADR-014, ADR-015)

status: complete
scope: Generalize Macula Hebrew parsing, versification mapping, and SQLite compilation across the entire Old Testament (all 39 books, 929 chapters, 23,206 verses, 102,124 clauses, 678,091 tokens).
priority: high

## Objective
Expand the Macula linguistic layer from Genesis (1,533 verses) to the full Old Testament canon (39 books, 23,206 verses).
Implement universal Masoretic Text (MT) to King James Version (KJV) versification mapping leveraging `data/oshb/VerseMap.xml`,
generalize token and syntactic clause extraction across all 39 book codes, stream-compile the whole-OT `data/macula.db` SQLite database
with low memory footprint (<50 MB RAM), and expand canonical reference lookups and syntactic queries across the entire Old Testament.

## Inputs (read these first)
- `ROADMAP.md` (Pillar B: Goals B1, B2, B3)
- `docs/decisions/ADR-012-macula-hebrew-linguistic-integration.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `docs/decisions/ADR-014-whole-bible-macula-sqlite-architecture.md`
- `docs/decisions/ADR-015-macula-semantic-enrichment.md`
- `data/oshb/VerseMap.xml` (pinned OSHB WLC-to-KJV versification mapping)
- `search/macula/extract.py`
- `search/macula/db.py`
- `search/macula/build_db.py`
- `search/macula/lookup.py`
- `scripts/macula_lookup.py`

## Tasks
- [x] Update `scripts/fetch_sources.sh`:
  - Fetch complete Macula Hebrew Lowfat XML corpus across all 39 OT books (929 chapters) via pinned git sparse-checkout.
  - Retain idempotent skips when XMLs are already present.
- [x] Generalize `search/macula/extract.py`:
  - Standardize 39-book OSIS mapping (`GEN` -> `Gen`, `EXO` -> `Exod`, `PSA` -> `Ps`, etc.).
  - Implement whole-OT MT-to-KJV versification mapping using `data/oshb/VerseMap.xml` with offline fallback.
  - Support parsing any chapter XML across all 39 OT books.
  - Implement `parse_all_chapters()` streaming generator with cross-chapter multi-sentence merging.
- [x] Update `search/macula/build_db.py` and `search/macula/db.py`:
  - Stream-compile all 929 chapters into `data/macula.db` in batches.
  - Compute global `strongs_crosswalk` (lemmas, glosses, sdbh, domains, LXX Greek alignments) across all 39 books.
  - PRAGMA optimizations during build (`synchronous=OFF`, `journal_mode=MEMORY`), building B-tree indices post-insert.
- [x] Generalize `search/macula/lookup.py` and `scripts/macula_lookup.py`:
  - Universal `normalize_verse_ref()` supporting all 39 books, abbreviations, and passage formats (including offset verses like `Ps.51.0b`).
  - Cross-book role, domain, and LXX queries.
- [x] Expand test suite:
  - Unit tests in `search/macula/test_extract.py`, `search/macula/test_db.py`, `search/macula/test_lookup.py`.
  - Multi-book test cases: Isaiah (e.g. Isa 53:5), Daniel (e.g. Dan 8:14), Psalms (e.g. Ps 23:1, Ps 51:0b), Malachi (Mal 4:6), Numbers (Num 26:1 split merge).
- [x] Verify test suite (`bash scripts/verify_all.sh`).
- [x] Subagent review by `code-reviewer`.

## Acceptance criteria
- [x] All 39 OT books (929 chapters, 23,206 verses) compiled into `data/macula.db`.
- [x] Sub-millisecond indexed queries across the entire Old Testament.
- [x] Versification differences (Psalms titles, Malachi 3/4, etc.) correctly map to KJV canonical IDs while preserving MT IDs.
- [x] Full test suite green with expanded test coverage.
- [x] Subagent review clean.
