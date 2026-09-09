# WP-020: Macula Greek (NT) Linguistic Integration & Canon Unification

status: completed
scope: Ingest Clear-Bible macula-greek Lowfat XML across all 27 New Testament books (260 chapters, 7,943 verses, ~138,000 tokens), extract token morphology, Greek Strong's (G1–G5624), syntactic trees, and participant roles, and unify with data/macula.db for whole-Bible original language coverage.
priority: high

## Objective
Complete the original-language linguistic and syntactic layer for the New Testament, mirroring the Old Testament Hebrew Macula integration.
Extract syntactic clause trees, phrase constituents, participant roles (Subject, Predicate Verb, Object, Adjunct), and Strong's alignments
for all 27 Greek NT books from Clear-Bible `macula-greek` (Nestle 1904 Lowfat XML). Unify the NT Greek dataset into `data/macula.db`, creating
a single, zero-dependency, whole-Bible linguistic knowledge engine across all 66 books.

## Inputs (read these first)
- `ROADMAP.md` (Pillar B: Goals B1, B2, B3; Phase 4)
- `docs/decisions/ADR-012-macula-hebrew-linguistic-integration.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `docs/decisions/ADR-014-whole-bible-macula-sqlite-architecture.md`
- `docs/decisions/ADR-015-macula-semantic-enrichment.md`
- `data/PROVENANCE.md` (upstream Clear-Bible pin)
- `search/macula/extract.py`
- `search/macula/extract_greek.py`
- `search/macula/db.py`
- `search/macula/build_db.py`
- `search/macula/lookup.py`
- `scripts/macula_lookup.py`

## Tasks
- [x] Upstream Sourcing & Pinning:
  - Pin upstream `Clear-Bible/macula-greek` repository commit in `data/PROVENANCE.md` (Section 6, commit `8423afe47b9e8f24b7772e808af45c7159a6fe7e`).
  - Update `scripts/fetch_sources.sh` to fetch `Nestle1904/lowfat` (all 27 NT books, 260 chapters) via git sparse-checkout and verify with `--check`.
- [x] Greek Lowfat XML Extractor:
  - Implement zero-dependency ElementTree parser for Greek Lowfat XML (`search/macula/extract_greek.py`).
  - Extract token attributes: Greek text, lemma, normalized Greek Strong's (G1–G5624), part of speech, morphology, Louw-Nida domains, and English gloss.
  - Parse hierarchical syntactic structures: multi-verse sentence splitting, clause rules, phrase constituents, and grammatical roles (Subject, Predicate Verb, Object, Indirect Object, Adjunct, Conjunction).
- [x] Database Schema & Canon Unification:
  - Extend `search/macula/db.py` and `search/macula/build_db.py` to stream-compile both Hebrew OT and Greek NT into `data/macula.db`.
  - Ensure unified relational tables:
    * `verses`: 31,149 verses across all 66 Protestant books.
    * `clauses`: 131,765 whole-Bible clause syntax trees.
    * `constituents`: 338,218 whole-Bible phrase roles.
    * `tokens`: 815,870 tokens across Hebrew, Aramaic, and Greek.
    * `strongs_crosswalk`: unified 13,538 entries (8,193 H-numbers + 5,345 G-numbers).
- [x] Query Engine & CLI Polish:
  - Extend `search/macula/lookup.py` and `scripts/macula_lookup.py` to query NT books (e.g. `John 1:1`, `Rom 8:28`, `Rev 14:6-7`).
  - Support NT participant frames (`--frame`) and Greek Strong's lookups (`--strongs G2316`).
  - Connect empirical cross-testament links: Hebrew OT $\leftrightarrow$ Septuagint (LXX) $\leftrightarrow$ New Testament Greek citations.
- [x] Test Suite Expansion:
  - Unit tests covering Greek token parsing, syntax extraction, multi-book NT lookups (`search/macula/test_extract_greek.py`, `test_db.py`, `test_lookup.py`).
  - Verify zero regression on existing OT Hebrew queries and Genesis JSON parity gate.
- [x] Run `bash scripts/verify_all.sh` to ensure all tests and validators pass.
- [x] Subagent review by `code-reviewer`.

## Acceptance criteria
- [x] All 27 NT books (260 chapters, 7,943 verses) compiled into `data/macula.db`.
- [x] Whole-Bible coverage: all 66 books queryable in `data/macula.db`.
- [x] Sub-millisecond indexed queries for NT Greek syntax, roles, and Strong's numbers.
- [x] Full test suite green and verified by `scripts/verify_all.sh` (411 tests passing).
- [x] Subagent review clean.

