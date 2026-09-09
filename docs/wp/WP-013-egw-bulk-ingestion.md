# WP-013: Spirit of Prophecy (EGW) Bulk Ingestion Engine & Importers (Pillar A, Goal A7)

status: completed
scope: Multi-format bulk ingestion (EPUB, TXT/Markdown, JSON, directory batching), high-performance SQLite FTS5 rebuild indexing, and public-domain edition harvester (ADR-011, ADR-013).
priority: high

## Objective
Build a robust, zero-waste, scalable bulk ingestion engine (`search/linking/egw_importer.py`)
capable of parsing and importing complete Ellen G. White writings and commentary volumes
into the local `data/egw.db` SQLite FTS5 database.
Support EPUB archives (standard package spine + XHTML paragraph/page tags), plain text /
markdown with pagination markers (`{PP 57.1}`, `[Page 57]`), JSON arrays, and folder batching.
Provide high-speed batch transactions with deferred FTS5 rebuilding (`rebuild`) for 10x–50x
speedup across large books. Provide an automated harvester for verified public-domain editions
(pre-1929, e.g. Steps to Christ, Patriarchs and Prophets, Desire of Ages, Great Controversy).

## Inputs (read these first)
- `ROADMAP.md` (Pillar A: A7)
- `docs/decisions/ADR-011-whole-book-scaffolding-and-jit-egw.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `NOTICE.md` & `README.md` (sourcing & copyright compliance)
- `search/linking/egw.py` (core `EgwDB` and SQLite schema)
- `scripts/egw_lookup.py` (CLI interface)

## Tasks
- [x] Create `search/linking/egw_importer.py` with modular parsers:
  - `TextParagraphParser`: Parses `{BOOK.PAGE.PARA}`, `[p. 57]`, and page header patterns. Strips Project Gutenberg header/footer banners.
  - `EpubParser`: Parses EPUB container, OPF manifest/spine, and extracts paragraphs with page-break anchors using Python standard library (`zipfile`, `html.parser`). Handles forward-slash POSIX normalization for Windows compatibility.
  - `BulkImporter`: High-speed file and directory batch scanning with trigger-deferred FTS rebuilds across whole directory imports.
- [x] Optimize `EgwDB` for high-volume bulk insertion:
  - Add `fast_bulk_insert()` supporting trigger-disabled batching and one-shot `egw_fts` index rebuild.
  - Eliminate DRY SQL duplication via `_UPSERT_PARAGRAPH_SQL`.
- [x] Implement public-domain fetcher/importer for freely available pre-1929 editions (Project Gutenberg / ADL) with verified EGW work IDs (GC #25833, ED #62102).
- [x] Update `scripts/egw_lookup.py` to support `--ingest-file`, `--ingest-dir`, and case-insensitive `--fetch-public-domain`.
- [x] Expand test suite in `search/linking/test_egw.py` and `search/linking/test_importer.py` (13 new tests).
- [x] Verify test suite with `bash scripts/verify_all.sh` (278 tests passing).
- [x] Subagent review by `code-reviewer` and actionable feedback addressed.

## Acceptance criteria
- [x] Text parser accurately extracts canonical book codes, pages, paragraphs, and titles.
- [x] EPUB parser extracts XHTML paragraphs and page breaks without external dependencies.
- [x] High-volume bulk insertion runs fast with zero memory blowup (3,224 paragraphs ingested in ~2s).
- [x] All tests passing, verify_all.sh green.
