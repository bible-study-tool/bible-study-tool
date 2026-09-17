# WP-016: Spirit of Prophecy (EGW) Public Domain Corpus Harvester Expansion (Step 1a)

status: complete
scope: Expand public domain harvester in `search/linking/egw_importer.py` and CLI `scripts/egw_lookup.py` to fetch, parse, and ingest the complete Conflict of the Ages series and core public-domain works into `data/egw.db` (Pillar A, Goal A7, ADR-011, ADR-013).
priority: high

## Objective
Implement Step 1a of the full corpus download roadmap:
1. Expand `PUBLIC_DOMAIN_SOURCES` in `search/linking/egw_importer.py` to include verified official free editions (EPUB and plain text) for the complete *Conflict of the Ages* series (*Patriarchs and Prophets*, *Prophets and Kings*, *The Desire of Ages*, *The Acts of the Apostles*, *The Great Controversy*) plus core devotional and educational works (*Steps to Christ*, *Christ's Object Lessons*, *Thoughts from the Mount of Blessing*, *The Ministry of Healing*, *Education*).
2. Enhance `harvest_public_domain()` to support multi-work downloading and batching with `work="ALL"` or comma-separated lists, using high-performance trigger-deferred SQLite FTS5 insertion.
3. Update `scripts/egw_lookup.py` with `--fetch-public-domain ALL` and `--list-sources`.
4. Ensure verified unit tests in `search/linking/test_importer.py`.
5. Verify test suite and integrity gates via `bash scripts/verify_all.sh`.
6. Conduct subagent review and commit Step 1a before proceeding to Step 1b.

## Inputs
- `ROADMAP.md` (Pillar A, Goal A7)
- `NOTICE.md` (copyright and sourcing policy)
- `docs/decisions/ADR-011-whole-book-scaffolding-and-jit-egw.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `search/linking/egw.py`
- `search/linking/egw_importer.py`
- `scripts/egw_lookup.py`

## Tasks
- [x] Expand `PUBLIC_DOMAIN_SOURCES` in `search/linking/egw_importer.py` with verified official URLs:
  - `PP` (Patriarchs and Prophets)
  - `PK` (Prophets and Kings)
  - `DA` (The Desire of Ages)
  - `AA` (The Acts of the Apostles)
  - `GC` (The Great Controversy)
  - `SC` (Steps to Christ)
  - `COL` (Christ's Object Lessons)
  - `MB` (Thoughts from the Mount of Blessing)
  - `MH` (The Ministry of Healing)
  - `ED` (Education)
  - Plus Project Gutenberg verified historical editions.
- [x] Enhance `harvest_public_domain()` to support `ALL` / lists and trigger-deferred bulk insertion.
- [x] Update `scripts/egw_lookup.py` CLI:
  - Add `--list-sources` flag.
  - Allow `--fetch-public-domain ALL` or comma-separated codes.
- [x] Add unit tests in `search/linking/test_importer.py`.
- [x] Verify test suite with `bash scripts/verify_all.sh`.
- [x] Subagent review by `code-reviewer`.

## Acceptance criteria
- [x] `scripts/egw_lookup.py --list-sources` lists all available public-domain titles and formats.
- [x] `harvest_public_domain` supports both `.epub` and `.txt` seamlessly.
- [x] `egw_lookup.py --fetch-public-domain ALL` ingests the core series cleanly without corrupting the FTS5 index.
- [x] All unit tests pass (325 tests), `verify_all.sh` is green.
