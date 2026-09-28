# WP-041: Historical-Grammatical Context Layer & Architectural Ergonomics

status: open
scope: Pillar C / Pillar D / Pillar E / ADR-022 — Research, data pipelines, schema, and non-intrusive UI ergonomics for the biblical historical-grammatical context layer (1986 General Conference Annual Council "Methods of Bible Study" framework).
priority: high

## Objective
Fulfill the fourth essential dimension of the historical-grammatical method mandated by the 1986 General Conference Annual Council *Methods of Bible Study* (historical-cultural illumination) alongside the already completed grammatical (Macula Hebrew/Greek morphology), lexical (WordGraph, Strong's, BDB/Abbott-Smith), and intertextual (TSK, OT→NT citations, LXX crosswalk) layers.

Deliver historical era timelines, biblical geography (~4,000 places with coordinates), ancient Near Eastern / Greco-Roman cultural backgrounds, and person/entity registries to illuminate the biblical authors' original context without cluttering the serene Study Room Desk (strictly adhering to ADR-025 Anti-Slop Charter and ADR-001 deterministic core).

## Inputs (read these first)
- `docs/decisions/ADR-022-historical-grammatical-context-layer.md` (historical-grammatical framework and dataset analysis)
- `docs/decisions/ADR-025-visual-identity-and-anti-slop-design-charter.md` (Study Room Desk serenity, anti-slop rules)
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md` (zero-bloat stewardship, whole-Bible scalability)
- `docs/decisions/ADR-027-content-level-sqlite-integrity.md` (canonical SQLite verification standards)
- `docs/HOW_TO_STUDY_THE_BIBLE.md` (SDA hermeneutical principles and the historical-grammatical method)
- Candidate Open Datasets:
  - **OpenBible.info Geography**: Lat/lon coordinates, biblical place names, verse references, modern identifications (CC BY 4.0).
  - **STEPBible TIPNR** (Tyndale Proper Name Registry): Comprehensive registry of people, places, and nations across the canon (CC BY 4.0).
  - **STEPBible TOTHT** (Tyndale OT Historical Text): Per-pericope cultural eras, ruling empires, and chronological anchors for the Old Testament (CC BY-SA 4.0).
  - **NT Canonical Era Mapping**: Curated per-book and per-pericope chronological mapping for New Testament pericopes (Second Temple, Roman Imperial / Procuratorial Judea, Apostolic Age).

## Architectural & Ergonomic Principles
1. **Illumination, Never Subordination (1986 GC "Methods of Bible Study" & ADR-022):**
   Historical, geographical, and cultural data serve solely as *illumination* of what the inspired biblical authors conveyed to their original audiences. It rejects the historical-critical method and never places secular or archeological conjectures above the authority of Scripture.
2. **Serene Study Room Desk (ADR-025 Anti-Slop Charter):**
   The reading desk must remain quiet, contemplative, and uncluttered. Historical details must not produce noisy popups, flashing banners, or visual pollution. Information is surfaced progressively upon request or placed in dedicated, elegant inspector panels.
3. **Deterministic & Offline-First (ADR-001, ADR-013):**
   Zero cloud mapping services (no external Mapbox or Google Maps network dependencies). Map views utilize lightweight offline vector geometry or embedded SVG cartography. All data is pinned by commit hash and SHA-256 in `data/PROVENANCE.md` and compiled into verifiable SQLite storage (`data/history.db`).

## Tasks

- [ ] Task 1: Source Provenance & Data Ingestion Scaffolding (`scripts/fetch_sources.sh`, `data/PROVENANCE.md`)
  - Pin upstream releases, repositories, and exact commits for OpenBible.info Geography, STEPBible TIPNR, and STEPBible TOTHT.
  - Formulate the curated NT pericope chronological mapping to ensure complete 66-book coverage.
  - Record cryptographic SHA-256 checksums in `data/PROVENANCE.md`.
  - Add download logic into `scripts/fetch_sources.sh` with fail-fast checksum verification.

- [ ] Task 2: Database Schema & Ingestion Pipeline (`data/history.db`, `scripts/build_history_db.py`)
  - Design normalized SQLite schema in 1NF with strict foreign keys:
    - `places`: `place_id`, `canonical_name`, `ancient_names`, `modern_name`, `latitude`, `longitude`, `country`, `occurrences`, `confidence`
    - `entities`: `entity_id`, `name`, `entity_type` (person, nation, group), `strongs_codes`, `biographical_summary`
    - `eras`: `era_id`, `name`, `date_range`, `dominant_power`, `cultural_milieu`, `socio_political_summary`
    - `verse_history`: `verse_id`, `era_id`, `cultural_notes`
    - `verse_places`: `verse_id`, `place_id` (PRIMARY KEY (verse_id, place_id), FOREIGN KEYs to verses & places)
    - `verse_entities`: `verse_id`, `entity_id` (PRIMARY KEY (verse_id, entity_id), FOREIGN KEYs to verses & entities)
  - Implement deterministic builder `scripts/build_history_db.py` compiling raw datasets into `data/history.db`.
  - Register canonical schema and record `content_sha256` in `data/INTEGRITY.json` per ADR-027.

- [ ] Task 3: Front-Matter Curation Schema & Book Preambles (`kc-schema.md`, `materials/bible/`)
  - Extend `kc-schema.md` with optional, deterministic `historical_context:` block (Option A of ADR-022) for high-value curated chapters (e.g. Genesis 1–3, Daniel 2/7/8/9, John 1/17, Romans 1–8, Revelation 1/12/13/14).
  - Draft and review per-book historical preambles (`Option C` of ADR-022) establishing date, authorship, historical setting, and original audience for foundational books.

- [ ] Task 4: Study Room Desk Ergonomics & UI Integration (`web/app.js`, `web/styles.css`, `web/index.html`)
  - Surface historical context in the Study Room Desk through three progressive, non-intrusive layers:
    1. **Historical Inspector Tab ("History & Context"):** Add dedicated tab in the right-hand inspection drawer alongside Exegesis, Translations, and Cross-References showing active verse era, geographical location, and cultural notes.
    2. **Discreet Geospatial Cartography:** Provide an offline-first, tranquil vector map widget (SVG / Canvas) showing the biblical world (Canaan, Egypt, Mesopotamia, Asia Minor, Mediterranean) with coordinate pins for referenced locations.
    3. **Inline Pericope Context Header:** Understated, anchored contextual metadata line at narrative pericope boundaries (e.g. *"Exile in Babylon • Neo-Babylonian Empire (c. 605–539 BC)"*) that expands on click without floating pill decorations (ADR-025 §5).

- [ ] Task 5: Search & Retrieval Integration (`search/corpus/search_bridge.py`, `search/ui/study_service.py`)
  - Expose historical entities and places in unified search (e.g. `place:Jerusalem`, `person:Moses`, `era:Second-Temple`).
  - Provide REST endpoints `/api/places/<id>`, `/api/entities/<id>`, and `/api/verse/<ref>/history`.

- [ ] Task 6: Data Integrity Gate & Comprehensive Testing
  - Implement validator `scripts/validate_history_integrity.py` (Gate F7) verifying foreign key consistency, coordinate bounds, and verse alignment.
  - Add comprehensive unit and integration tests across data ingestion, API endpoints, and web rendering.
  - Verify full test suite passes cleanly via `bash scripts/verify_all.sh`.

## Acceptance Criteria
- [ ] Pinned datasets fetched, verified, and documented in `data/PROVENANCE.md`.
- [ ] `data/history.db` compiles deterministically with content-level checksum in `data/INTEGRITY.json`.
- [ ] No visual clutter, popups, or external network requests on the Study Room Desk (100% offline, tranquil design).
- [ ] All 31,102 verses map to their historical-cultural era and all biblical place references link to verifiable coordinates.
- [ ] Full test suite green with zero regressions.
