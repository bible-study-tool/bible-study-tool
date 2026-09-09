# WP-017: Full Official English EGW Corpus Harvester & Pagination Fidelity (Step 1b)

status: completed
scope: Automated harvester and high-fidelity pagination parser for the complete official English Ellen G. White corpus from media2.egwwritings.org across 414 publication codes (Pillar A, Goal A7, ADR-011, ADR-013).
priority: high

## Objective
Implement Step 1b of the complete corpus acquisition and offline-first knowledge base:
1. Provide zero-external-dependency automated harvester (`scripts/fetch_egw_corpus.py`) targeting the official White Estate CDN (`https://media2.egwwritings.org/epub/` and `/pdf/`).
2. Catalog and route all 414 official English publications into structured archival folders:
   - `01_Books_and_Compilations` (Books, Devotionals, Biographies)
   - `02_Manuscript_Releases` (1MR–21MR)
   - `03_Periodical_Articles` (RH1–RH6, ST1–ST4, YI, BE, PT, etc.)
   - `04_Special_Collections_and_Sermons` (1888, 1SAT, 2SAT, SpM, etc.)
   - `05_Pamphlets_and_Special_Testimonies` (SpTA, SpTB, SpTEd, PH001–PH180)
3. Implement resilient networking: exponential backoff retries on transient Cloudflare rate limits (429), socket timeouts, and atomic `.tmp` download staging.
4. Upgrade `EpubParser` in `search/linking/egw_importer.py` to extract true canonical pagination across multi-chapter spines from `<span class="pagebreak">[page]</span>`, `<span epub:type="pagebreak" id="pXX" title="XX">`, and chapter title continuity.
5. Provide comprehensive unit testing in `search/linking/test_fetch_corpus.py` and `search/linking/test_importer.py`.
6. Verify against project test suite and validators (`bash scripts/verify_all.sh`).
7. Conduct subagent review and commit Step 1b before proceeding to Step 2 (Macula whole-Bible linguistic data).

## Inputs
- `ROADMAP.md` (Pillar A, Goal A7)
- `NOTICE.md` (copyright and sourcing policy)
- `docs/decisions/ADR-011-whole-book-scaffolding-and-jit-egw.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `search/linking/egw.py`
- `search/linking/egw_importer.py`
- `scripts/egw_lookup.py`

## Tasks
- [x] Create `scripts/fetch_egw_corpus.py`:
  - Complete curated catalog of 414 publication codes.
  - Subfolder routing logic matching White Estate classifications.
  - Exponential backoff retry handler for Cloudflare 429/503 and timeouts.
  - Corrupt zip cache validation and atomic staging.
  - `--category`, `--code`, `--format`, `--dry-run`, and `--ingest` flags.
- [x] Upgrade `EpubParser` in `search/linking/egw_importer.py`:
  - Extract pagination from `<span class="pagebreak">[page]</span>` text bodies.
  - Extract pagination from `<span epub:type="pagebreak" id="pXX" title="XX">`.
  - Maintain page number and paragraph count continuity across EPUB spine chapters.
  - Preserve chapter titles across pagination breaks.
  - Detect publication codes from `en_<CODE>.epub` filenames without false positives on arbitrary files.
- [x] Create comprehensive test suite `search/linking/test_fetch_corpus.py` (21 unit tests).
- [x] Expand `search/linking/test_importer.py` to cover `en_` prefix detection and publication patterns (23 unit tests).
- [x] Verify live ingestion and canonical citation lookup on 21 Manuscript Releases (1MR–21MR, 38,313 paragraphs) and core works.
- [x] Run full project test suite (350 tests passing) and `bash scripts/verify_all.sh` (ALL CHECKS PASSED ✔).
- [x] Conduct subagent review by `code-reviewer`.
- [x] Update documentation and commit Step 1b.

## Acceptance Criteria
- [x] Harvester resolves and catalogs all 414 publication codes cleanly.
- [x] Resilient retry logic recovers gracefully from transient CDN timeouts / 429 rate limits.
- [x] EPUB parser extracts accurate multi-page pagination matching canonical citations (e.g. `10MR.15.1`, `PP.44.1`).
- [x] All unit tests passing in `search/linking/`.
- [x] All project tests pass (350 passed in 81.31s) and `bash scripts/verify_all.sh` is green.
