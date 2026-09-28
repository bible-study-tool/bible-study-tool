# Work Packages — Index

Curation of Genesis drafts per chapter (ADR-009). Each package is
self-contained: a session needs only `AGENTS.md` + the package file. Format:
see `TEMPLATE.md`.

The deterministic skeletons (verse text, Strong's tags, WordGraph-assembled
word studies) already exist and are byte-verified — curation ADDS interpretive
content (cross-references, study notes, theological connections) and moves
entries `draft` -> `review`.

| Package | Scope | Theme | Status |
| --- | --- | --- | --- |
| [WP-001](WP-001-gen1-day1-completion.md) | v4-5 | Day 1 completion (light; first naming) | complete |
| [WP-002](WP-002-gen1-day2.md) | v6-8 | Day 2 (firmament, waters) | complete |
| [WP-003](WP-003-gen1-day3.md) | v9-13 | Day 3 (dry land, seed-bearing plants) | complete |
| [WP-004](WP-004-gen1-day4.md) | v14-19 | Day 4 (luminaries, appointed times) | complete |
| [WP-005](WP-005-gen1-day5.md) | v20-23 | Day 5 (sea creatures, birds) | complete |
| [WP-006](WP-006-gen1-day6.md) | v24-31 | Day 6 (land animals, humanity, dominion) | complete |
| [WP-007](WP-007-gen2-pipeline.md) | Gen 2 (25 verses) | Book-level pipeline generalization + Genesis 2 skeletons (ADR-009) | complete |
| [WP-009](WP-009-wordgraph.md) | WordGraph | Build the WordGraph lexical knowledge graph for Genesis (ADR-010) | complete |
| [WP-010](WP-010-draft-engine.md) | Draft engine | Deterministic word-study draft engine consuming the WordGraph (ADR-010) | complete |
| [WP-008](WP-008-gen2-sabbath.md) | Gen 2:1-25 | Curate Genesis 2 — Eden, the man and woman, the seventh-day Sabbath (ADR-009) | complete |
| [WP-011](WP-011-gen3-fall.md) | Gen 3:1-24 | Curate Genesis 3 — the Fall (ADR-009) | complete |
| [WP-012](WP-012-macula-integration.md) | Pillar B (B1) | Macula Hebrew Linguistic Integration & Strong's-LXX Crosswalk (ADR-012) | complete |
| [WP-013](WP-013-egw-bulk-ingestion.md) | Pillar A (A7) | Spirit of Prophecy (EGW) Bulk Ingestion Engine & Importers (ADR-011, ADR-013) | complete |
| [WP-014](WP-014-whole-bible-macula-sqlite.md) | Pillar B (B2) | Whole-Bible Macula SQLite Architecture (ADR-013, ADR-014) | complete |
| [WP-015](WP-015-macula-semantic-enrichment.md) | Pillar B (B3) | Macula Semantic Role & Translation-Equivalence Enrichment (ADR-015) | complete |
| [WP-016](WP-016-egw-public-domain-corpus.md) | Pillar A (A7) | Spirit of Prophecy (EGW) Public Domain Corpus Expansion (Step 1a) | complete |
| [WP-017](WP-017-egw-full-corpus-harvester.md) | Pillar A (A7) | Full Official English EGW Corpus Harvester & Pagination Fidelity (Step 1b) | complete |
| [WP-018](WP-018-whole-bible-macula.md) | Pillar B (B1-B3) | Whole-Bible Macula Linguistic Integration (Step 2) | complete |
| [WP-019](WP-019-whole-bible-english-corpus.md) | Pillar A (A2, A3, A6) | Whole-Bible English Text Integration (All 66 Books) | complete |
| [WP-020](WP-020-macula-greek-nt-integration.md) | Pillar B (B1-B3, NT) | Macula Greek (NT) Linguistic Integration & Canon Unification | complete |
| [WP-021](WP-021-study-tui-and-cli.md) | Pillar D (D3, D4) | Interactive Terminal User Interface (TUI) & Unified Study CLI | complete |
| [WP-022](WP-022-textual-study-workstation.md) | Pillar D (D3, D4) | Modern Textual Study Workstation & Theme System | complete |
| [WP-023](WP-023-accessible-study-and-egw-reader.md) | Pillar D (D3, D4) | Human-Accessible Original Language Framing & Direct Commentary Navigation | complete |
| [WP-024](WP-024-workstation-performance-and-comprehension-tools.md) | Pillar D (D3, D4) | Textual Workstation Performance & Biblical Comprehension Tools | complete |
| [WP-025](WP-025-pauline-argument-flow-and-discourse-markers.md) | Pillar B (B4), Pillar D (D3) | Pauline Argument Flow & Discourse Markers (Comprehension Feature 3) | complete |
| [WP-026](WP-026-scripture-interpreting-scripture-ot-citation-anchors.md) | Pillar B (B5), Pillar D (D3) | Scripture Interpreting Scripture: OT Citation Anchors in NT (Feature 4) | complete |
| [WP-027](WP-027-nt-corpus-and-john-curation.md) | Pillar A (A3) | New Testament Corpus Generation & John 1 / 17 Curation | complete |
| [WP-028](WP-028-engineering-hardening-and-test-expansion.md) | Pillar G (G2, G3) | Engineering Hardening & Test Expansion — validator self-tests, passage normalization regressions, generator golden tests, Textual flakiness elimination, CI health dashboard | open |
| [WP-029](WP-029-zero-python-distribution.md) | Pillar P (new) | Zero-Python Distribution — frozen binary installer for Windows/macOS/Linux; "Open the Book" for non-technical users | complete |
| [WP-030](WP-030-divinity-hall-visual-identity-and-ergonomics.md) | Pillar D (GUI / UX) | Study Room Visual Identity & Workspace Ergonomics (split pane, focus modes, warm sepia, progressive disclosure) | complete |
| [WP-031](WP-031-master-prophetic-table-and-original-language-nuances.md) | Pillar B, C | Master Prophetic Key Table & Original-Language Theological Nuances (plain-English stems, aggregated prophetic lexicon) | complete |
| [WP-032](WP-032-sanctuary-typology-blueprint-and-plan-of-salvation.md) | Pillar A, D | Sanctuary Typology Blueprint & Chronological Plan of Salvation (FB #24 spatial/chronological roadmap) | complete |
| [WP-033](WP-033-progressive-spirit-of-prophecy-chapter-reader.md) | Pillar A, D | Progressive Spirit of Prophecy Narrative Navigation & Chapter Reader (compact chips → full contextual reader) | complete |
| [WP-034](WP-034-developer-ergonomics-and-bootstrap-hardening.md) | Pillar G (G5) | Developer Ergonomics & One-Command Bootstrapping (root ./bootstrap.sh, --data hydration, stale finder guard) | complete |
| [WP-035](WP-035-treasury-of-scripture-knowledge-tsk-integration.md) | Pillar A, C | Treasury of Scripture Knowledge (TSK) Ingestion Engine (~340k whole-Bible cross-references in SQLite) | complete |
| [WP-036](WP-036-interactive-whole-bible-cross-reference-workstation.md) | Pillar D (UX) | Interactive Whole-Bible Cross-Reference Workstation UI (Web & TUI ranked xref chips, preview tooltips) | complete |
| [WP-037](WP-037-curation-manifest-and-velocity-dashboard.md) | Pillar A, F, H | Curation Velocity Dashboard & Verifiable Terminal Manifest (status: approved, curation-manifest.json) | complete |
| [WP-038](WP-038-tauri-desktop-application.md) | Pillar P, D | Native Desktop Application (Tauri Packaging & GUI Window: .dmg / .exe / .AppImage) | complete |
| [WP-039](WP-039-deterministic-cross-language-unified-search.md) | Pillar C (C3, C4), D (D1, D3, D4) | Deterministic Cross-Language & Unified Multi-Database Search Workstation | complete |


Priority order: WP-001 first (it also completes the already-curated Day 1
verses 1-3), then ascending.
