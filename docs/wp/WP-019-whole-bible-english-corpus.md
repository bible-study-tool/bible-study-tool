# WP-019: Whole-Bible English Text Integration (All 66 Books)

status: open
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
- [ ] Define canonical 66-book biblical catalog in `search/corpus/bible_books.py`:
  - Authoritative metadata for all 39 OT books and 27 NT books (OSIS codes, canonical names, testament, chapter counts, verse counts).
  - Flexible book resolver normalizing common English names, abbreviations, and Roman numeral prefixes (e.g. "1 Cor", "First Corinthians", "I Cor" -> "1Cor").
- [ ] Implement whole-canon KJV extractor in `search/corpus/extract_kjv.py`:
  - Zero-dependency streaming XML parser reading `data/scrollmapper/kjv-osis.xml`.
  - Extract clean verse text, word-level token sequences, and Strong's tags (Hebrew H-numbers and Greek G-numbers).
  - Robust handling of self-closing XML tags and italicized translation-supplied words.
- [ ] Incorporate public-domain translation witnesses (ASV and WEB):
  - Stream-parse or ingest American Standard Version (1901) and World English Bible texts for comparative reading.
  - Enable multi-translation side-by-side verse comparisons in CLI and API.
- [ ] Implement Whole-Bible Lookup Engine & CLI (`scripts/bible_lookup.py`):
  - Query any verse or chapter range across all 66 books (e.g. `python scripts/bible_lookup.py "John 3:16"`, `Dan 8:14`, `Rev 14:6-12`).
  - Flags: `--strongs`, `--compare` (KJV vs ASV vs WEB), `--tokens`, `--json`.
- [ ] Standardize human-friendly skeleton directory structure:
  - Address Genesis single-folder scaling by structuring passage markdown skeletons cleanly (`materials/bible/{testament}/{book}/` with chapter subdirectories or partitioned indexing).
  - Implement deterministic skeleton generator for whole-book passage files across OT and NT.
- [ ] Comprehensive unit and integration test suite:
  - `search/corpus/test_bible_books.py` and `search/corpus/test_extract_kjv.py`.
  - Verify verse count totals, Strong's tag fidelity across Pentateuch, Histories, Wisdom, Prophets, Gospels, Epistles, and Apocalypse.
- [ ] Run `bash scripts/verify_all.sh` to ensure all tests and F1-F4 validators pass.
- [ ] Subagent review by `code-reviewer`.

## Acceptance criteria
- [ ] All 66 books (1,189 chapters, ~31,102 verses) queryable with sub-millisecond response time.
- [ ] Strong's word spans correctly extracted for both Hebrew (OT) and Greek (NT) in KJV-osis.
- [ ] Comparative translation lookups (KJV, ASV, WEB) functional.
- [ ] Test suite green and verified by `scripts/verify_all.sh`.
- [ ] Subagent review clean.
