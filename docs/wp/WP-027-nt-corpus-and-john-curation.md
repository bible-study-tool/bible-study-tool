# WP-027: New Testament Corpus Generation & John 1 / 17 Theological Curation

status: complete
scope: Implementation of Pillar A3: New Testament taxonomy expansion, deterministic Greek draft generator, per-chapter folder organization, and comprehensive theological curation of John 1 and John 17.
priority: high

## Objective

To expand the deterministic offline knowledge base from Old Testament Hebrew Masoretic texts (Genesis 1–50) into the Greek New Testament, establishing full-pipeline scaffolding for all 27 New Testament books and delivering deep theological curations of John 1 (the Logos prologue, Lamb of God, and discipleship) and John 17 (the High Priestly prayer and Trinitarian covenant unity) per Pillar A3 of the repository roadmap.

## Inputs
- `data/KJV-osis.json`: Pinned full-Bible KJV text.
- `lexicons/strongs-lexicon.json`: Canonical Strong's Greek definitions (G1–G5624).
- `lexicons/tbesg-glosses.json`: STEPBible TBESG contextual Greek glosses.
- `tags/taxonomy.json`: Project category taxonomy.
- `ROADMAP.md`: Pillar A3 milestone definition.
- `docs/decisions/ADR-021-new-testament-corpus-and-curation.md`: Architecture record.

## Conventions that Apply
- ADR-001 (Deterministic core vs AI layer boundary).
- ADR-003 (Standard YAML frontmatter).
- ADR-005 (Data integrity precedes scale).
- ADR-009 & ADR-021 (Per-chapter folder structure and whole-book generation).

## Implementation Tasks

### 1. New Testament Taxonomy & Generator (`tags/taxonomy.json`, `search/corpus/build_nt.py`)
- [x] Register all 27 New Testament books (`book/matthew` through `book/revelation`) in `tags/taxonomy.json`.
- [x] Implement deterministic NT draft generator `search/corpus/build_nt.py` utilizing pinned `data/KJV-osis.json`, public domain Strong's Greek definitions (`lexicons/strongs-lexicon.json`), and STEPBible TBESG glosses (`lexicons/tbesg-glosses.json`).
- [x] Structure output directories into zero-padded per-chapter folders: `materials/bible/nt/{book}/{ch:02d}/{book}-{ch}-{v}-kjv.md`.
- [x] Add comprehensive test suite in `search/corpus/test_build_nt.py` (9 unit and integration tests).

### 2. Draft Skeletons Generation
- [x] Generate all 51 verse skeletons for John 1 in `materials/bible/nt/john/01/`.
- [x] Generate all 26 verse skeletons for John 17 in `materials/bible/nt/john/17/`.
- [x] Corpus size expanded from 1,533 to 1,610 entries with zero validator regressions.

### 3. Theological Curation of John 1 (`materials/bible/nt/john/01/`)
- [x] Transition all 51 verses from `status: draft` to `status: review`.
- [x] Preserve KJV text, Strong's tags, and Greek morphology blocks verbatim.
- [x] Add valid taxonomy tags, verified cross-references, and OT backgrounds.
- [x] Add deep theological study notes on the Logos prologue, *skēnoō* tabernacling, Lamb of God sanctuary typology, and Jacob's ladder discipleship, encased in `<!-- AI-GENERATED -->` ... `<!-- END AI-GENERATED -->` comments.
- [x] Automated via `scripts/curate_john1.py`.

### 4. Theological Curation of John 17 (`materials/bible/nt/john/17/`)
- [x] Transition all 26 verses from `status: draft` to `status: review`.
- [x] Preserve deterministic core text verbatim.
- [x] Add cross-references to the Upper Room discourse, High Priestly intercession, and *Desire of Ages* Chapter 73.
- [x] Add deep study notes on mutual glorification, knowing God as eternal life, pastoral preservation (*ephylaxa*), the son of perdition (*ho huios tēs apōleias*), sanctification in objective truth, and Trinitarian covenant oneness.
- [x] Automated via `scripts/curate_john17.py`.

### 5. Semantic Linking & Verification
- [x] Update `search/linking/test_pipeline.py` to index both Old and New Testament entries (`book/genesis == 1533`, `book/john == 77`).
- [x] Verify complete test suite and data integrity gates via `bash scripts/verify_all.sh` (565 tests passing, F1–F4 validators 100% clean).

## Acceptance Criteria
- [x] All 27 New Testament books registered in `tags/taxonomy.json` and validated by F1 Schema.
- [x] Deterministic NT draft generator `search/corpus/build_nt.py` fully tested (`search/corpus/test_build_nt.py`).
- [x] All 51 verses of John 1 and 26 verses of John 17 generated into `materials/bible/nt/john/01/` and `materials/bible/nt/john/17/`.
- [x] All 77 verses curated to `status: review` with interpretive notes strictly encased in `<!-- AI-GENERATED -->` ... `<!-- END AI-GENERATED -->` blocks.
- [x] Full test and verification suite passes cleanly via `bash scripts/verify_all.sh` (565 tests, F1–F4 clean).

## Key Findings & Architecture Notes
1. **Validator Agility**: The F1 schema validator already supported `language: greek` and `strongs-G*` prefixes; adding the 27 NT books to `tags/taxonomy.json` was sufficient to validate the entire NT corpus without altering validator code.
2. **Forward Cross-Reference Resolution**: Generating `john-1-1-kjv.md` resolved the long-standing forward reference in `gen-1-1-kjv.md` (`target: "john-1-1"`).
3. **Per-Chapter Organization**: Zero-padded two-digit chapter folders (`01/`, `17/`) ensure clean filesystem navigation and consistency with the Genesis refactor.
