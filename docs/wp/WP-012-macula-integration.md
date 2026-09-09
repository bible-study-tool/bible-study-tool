# WP-012: Macula Hebrew Linguistic Integration & Strong's-LXX Crosswalk (Pillar B)

status: completed
scope: Integration of Clear-Bible Macula Hebrew linguistic data (lowfat XML), Strong's-LXX crosswalk, SDBH semantic domains, and sentence/clause syntax extraction (ADR-012, Roadmap B1).
priority: high

## Objective
Integrate the Clear-Bible Macula Hebrew dataset to enrich our deterministic
linguistic layer. Build a zero-dependency XML parser (`search/macula/extract.py`)
using `xml.etree.ElementTree` that extracts token attributes (Strong's Hebrew,
LXX Greek equivalent and Strong's number, SDBH semantic domains) and clause syntax
trees (clause boundaries, phrase groupings, participant roles). Generate the
derived knowledge artifact `lexicons/macula-genesis.json`, provide a lookup engine
and CLI (`scripts/macula_lookup.py`), and pin upstream sources in `data/PROVENANCE.md`.

## Inputs (read these first)
- `ROADMAP.md` (Pillar B: B0, B1, B2, B3)
- `docs/decisions/ADR-012-macula-hebrew-linguistic-integration.md`
- `data/PROVENANCE.md` (integrity model and artifact inventory)
- Upstream: `https://github.com/Clear-Bible/macula-hebrew` (pinned commit `47db250bd55d0d8577f2a94fba114ef16c35b23c`)

## Tasks
- [x] Pin upstream `Clear-Bible/macula-hebrew` in `data/PROVENANCE.md` and draft ADR-012.
- [x] Update `scripts/fetch_sources.sh` to download and verify `data/macula-hebrew/01-Gen-*-lowfat.xml`.
- [x] Implement zero-dependency Lowfat XML parser in `search/macula/extract.py`.
- [x] Build crosswalk and syntax compiler in `search/macula/build_crosswalk.py`.
- [x] Generate derived artifact `lexicons/macula-genesis.json` and record checksum in `data/PROVENANCE.md`.
- [x] Implement query engine `search/macula/lookup.py` and CLI `scripts/macula_lookup.py`.
- [x] Create comprehensive unit test suite in `search/macula/test_extract.py` and `search/macula/test_lookup.py`.
- [x] Update `search/corpus/test_morphology.py` and provenance checks to gate `lexicons/macula-genesis.json`.
- [x] Verify whole test suite with `bash scripts/verify_all.sh`.
- [x] Code review by `code-reviewer` subagent and review recommendations applied.

## Conventions that apply
- Deterministic core: zero hand-editing of generated artifacts; regenerate via script.
- Fail fast: invalid XML, missing tags, or mismatched schema raises immediately.
- Zero heavyweight external dependencies: standard library `xml.etree.ElementTree`.
- Exact test counts in commit messages.

## Acceptance criteria
- [x] `search/macula/extract.py` correctly parses lowfat XML sentences, clauses, phrases, and tokens.
- [x] Strong's Hebrew to LXX Greek mapping and SDBH semantic domains extracted for Genesis.
- [x] `lexicons/macula-genesis.json` generated and checksum pinned in `data/PROVENANCE.md`.
- [x] `scripts/macula_lookup.py` returns syntax trees and Strong's crosswalks via CLI.
- [x] `bash scripts/verify_all.sh` passes with 0 errors.

## Notes / findings
- Extracted 1,533 sentences (verses), 7,007 clauses, and 43,063 tokens across Genesis 1-50.
- 1,753 Hebrew Strong's numbers mapped to SDBH semantic domains and Greek LXX Strong's numbers with 100% canonical alignment against `lexicons/strongs-list.json`.
- Versification divergence between Masoretic Text (MT) and English KJV for Genesis 31:55 / Genesis 32:1-32 handled cleanly in `map_mt_to_canonical_verse`.
- Zero external heavyweight dependencies; pure `xml.etree.ElementTree`.

