# WP-035: Treasury of Scripture Knowledge (TSK) Whole-Bible Ingestion Engine

status: complete
scope: Pillar A (Corpus & Content), Pillar C (Search & Cross-Referencing), ADR-013, ADR-026
priority: high
decisions: [ADR-001](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-001-deterministic-core-vs-ai.md), [ADR-002](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-002-licensing-and-content-sourcing.md), [ADR-006](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-006-provenance-and-generated-artifacts.md), [ADR-013](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md), [ADR-026](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-026-treasury-of-scripture-knowledge-cross-references.md)

---

## 1. Objective

Integrate the complete *Treasury of Scripture Knowledge* (TSK) cross-reference dataset into `data/bible.db`, establishing immediate, reciprocal, relevance-ranked cross-referencing across all 66 books and 31,102 verses of the biblical canon.

---

## 2. Background

Currently, cross-references exist only for passages with hand-curated Markdown files (`materials/bible/`: Genesis 1–3, John 1, John 17; ~157 verses). When studying the remaining 30,945 verses, the cross-reference panel remains blank or sparse.

Rather than re-creating ~340,000 cross references manually over many years, [ADR-026](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-026-treasury-of-scripture-knowledge-cross-references.md) specifies ingesting the public-domain *Treasury of Scripture Knowledge* as compiled and normalized by OpenBible.info (~1.98 MB compressed, ~340,000 reciprocal pairs). This dataset adds ~12–15 MB to SQLite while instantly providing comprehensive scriptural cross references for every single verse in the Bible.

---

## 3. Implementation Plan

### Phase 1 — Provenance Pinning & Fetch Pipeline
* [x] Pin upstream archive `https://a.openbible.info/data/cross-references.zip` with SHA-256 checksum in `data/PROVENANCE.md`.
* [x] Update `NOTICE.md` with attribution to OpenBible.info (CC BY 4.0) and the public-domain Treasury of Scripture Knowledge.
* [x] Add download and integrity verification steps to `scripts/fetch_sources.sh`.
* [x] Add `!data/cross-references.zip` and uncompressed files to `.gitignore` exclusions/tracking as appropriate.

### Phase 2 — Ingestion Engine (`search/corpus/extract_tsk.py`)
* [x] Create `search/corpus/extract_tsk.py` with CLI entrypoint:
  - Supports `--zip`, `--db`, `--force`, `--batch-size`.
  - Parses cross-reference table (`from_verse`, `to_verse`, `votes`).
  - Normalizes book abbreviations to canonical OSIS identifiers (e.g. `Gen.1.1`, `Matt.3.16`).
  - Creates SQLite schema:
    ```sql
    CREATE TABLE IF NOT EXISTS cross_references (
        from_verse TEXT NOT NULL,
        to_verse TEXT NOT NULL,
        votes INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (from_verse, to_verse)
    );
    CREATE INDEX IF NOT EXISTS idx_xrefs_from ON cross_references(from_verse, votes DESC);
    CREATE INDEX IF NOT EXISTS idx_xrefs_to ON cross_references(to_verse);
    ```
  - Bulk inserts with transactions (`PRAGMA synchronous = OFF; PRAGMA cache_size = 10000;`).

### Phase 3 — Query Layer & Release Data Bundling
* [x] Add `get_cross_references(verse_ref: str, limit: int = 25) -> list[dict[str, Any]]` to `BibleDB` in `search/corpus/extract_kjv.py`.
* [x] Expose `get_verse_cross_references(verse_ref: str, limit: int = 25)` on `StudyService` in `search/ui/study_service.py`.
* [x] Update `scripts/build_release_data.sh` and `scripts/bootstrap.sh` to run `search.corpus.extract_tsk` when building the release bundle.

### Phase 4 — Unit Tests & Validation Gates
* [x] Create `search/corpus/test_extract_tsk.py`:
  - Test archive extraction and parsing logic.
  - Test OSIS reference normalization across Old and New Testaments.
  - Test SQLite insertion and verify expected row count (~344,800).
  - Test query retrieval, limit bounding, and descending vote sort order.
  - Test reciprocal resolution (e.g. querying from verse B finds verse A).

---

## 4. Acceptance Criteria

1. `scripts/fetch_sources.sh` downloads and verifies the TSK cross-reference archive against its pinned SHA-256 in `data/PROVENANCE.md`.
2. `search/corpus/extract_tsk.py` compiles ~340,000 cross references into `data/bible.db` in <10 seconds (1.70s verified).
3. `BibleDB.get_cross_references("Gen.1.1")` returns ranked cross-references (including John 1:1–3, Hebrews 11:3, Psalm 33:6, etc.) in <2ms (0.24ms warm verified).
4. Full test suite and `bash scripts/verify_all.sh` pass cleanly (756 passed).
