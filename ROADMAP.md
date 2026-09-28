# Roadmap — Adventist Bible Study Tool

This is the living, tracked roadmap for the project. The MVP (Genesis 1:1-3
+ deterministic/AI semantic-linking pipeline) is **complete and proven**. This
document captures where the project is going: a complete, prioritized goal
inventory and the sequencing we intend to follow.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done

## Guiding Principles

1. **Deterministic core is the source of truth.** AI is an assistant, never an
   authority; everything AI produces is gated behind human review.
2. **Offline-first.** The tool works without AI or internet; generated
   artifacts are rebuilt from Markdown.
3. **Data integrity precedes scale.** Bad data compounds; validators and
   verification come *before* large-scale corpus growth.
4. **Link out, don't redistribute.** EGW/SDA and copyrighted translations are
   referenced or user-supplied, never bundled (see `NOTICE.md`).
5. **Doctrinal humility with progressive light.** Anchored to the Bible within
   the Adventist framework, open to correction grounded in Scripture.

## Current State (MVP, `[x]`)

- `[x]` Genesis 1:1-3 corpus (3 entries, 13 Strong's roots, 3 curated links)
- `[x]` Deterministic concordance (layer b) — `index/concordance.json`
- `[x]` Multilingual discovery (layer c) — `ai-discovered-links.json`
- `[x]` SQLite FTS5 index + query CLI (`dbindex`)
- `[x]` Pluggable embedder (offline n-gram fallback / transformer option)
- `[x]` Review-queue merge-preservation (human annotations survive regen)
- `[x]` Standard `---` YAML frontmatter + documented schema & taxonomy
- `[x]` Dual license (MIT code / CC BY 4.0 content) + NOTICE policy

---

## Goal Inventory

### A. Corpus & Content
- `[x]` **A1. Complete Genesis 1 creation narrative** — v1-31 (all 31 skeletons generated; v1-31 curated across WP-001..WP-006 with status: review) — **MVP scope closed**
- `[~]` **A2. Complete the book of Genesis, chapter by chapter** (per ADR-009 & ADR-011: whole-book pipeline, broad scaffolding + per-chapter curation) — Broad draft skeletons generated for all 50 chapters (1,533 verses); Genesis 1-3 curated (WP-001..WP-011); chapters 4-50 generated as draft skeletons awaiting per-chapter curation (Genesis 4 next); then expand to the wider OT (Exodus, Isaiah, Daniel, Psalms)
- `[x]` **A10. WordGraph lexical knowledge graph** (ADR-010) — lemma-centric spine (token id / lexeme + homograph index / Strong's legacy crosswalk); aggregate-first dictionary; deterministic word-study generation; per-book artifacts (`lexicons/wordgraph-*.json`); makes computation *more* deterministic as data grows. **Whole-book Genesis WordGraph done** (`lexicons/wordgraph-genesis.json`: 1,783 lexemes, 20,159 tokens across 50 chapters / 1,533 verses); draft engine operational (WP-010).
- `[x]` **A3. Add NT coverage & curated chapters** — Full New Testament draft generator (`search/corpus/build_nt.py`) and all 27 books in `tags/taxonomy.json`; per-chapter markdown entries in `materials/bible/nt/{book}/{ch:02d}/`; curated key theological chapters **John 1** (51 verses: Logos Christology, creation link to Gen 1:1, tabernacling, Lamb of God) and **John 17** (26 verses: High Priestly prayer, covenant unity, sanctification in truth) to `status: review` (WP-027, ADR-021). Whole-Bible KJV extraction operational in `data/bible.db`.
- `[x]` **A4. Full Strong's lexicon dataset** — `lexicons/strongs-list.json` (canonical 8674 H + 5624 G, F2-verified) + `lexicons/strongs-lexicon.json` (definitions/transliteration/KJV usage); sources pinned in `data/PROVENANCE.md`
- `[x]` **A5. Greek word-study expansion** — Ingested Clear-Bible macula-greek Lowfat XML (Nestle 1904) across all 27 New Testament books; unified Greek Strong's (G1-G5624), morphology, syntactic trees, and Louw-Nida semantic domains into `data/macula.db` (WP-020).
- `[x]` **A6. Multiple public-domain translations** — Ingested ASV (1901), BSB (2020), and YLT (1898) into normalized `data/bible.db` alongside KJV (1769). Surfaced in Textual workstation as Tab 4 comparison panel and stacked reader toggle (`v`) (WP-024 Phase 3).
- `[x]` **A7. Spirit of Prophecy integration** — link-out + user-supplied-text model (NOTICE.md, ADR-011); JIT SQLite architecture (`search/linking/egw.py`, `scripts/egw_lookup.py`, `search/validation/xrefs.py`) with FTS5 virtual table, BM25 ranking, and canonical citation resolution (`egw:BOOK.PAGE.PARA`).
- `[ ]` **A8. Commentaries & study guides** — SDABC-adjacent, Sabbath School
- `[ ]` **A9. Original-language text corpus** — Masoretic Hebrew, LXX Greek as structured data
- `[x]` **A11. Sanctuary Typology Blueprint & Chronological Plan of Salvation** — deterministic sanctuary typology schema (`data/sanctuary_schema.json`) mapping compartments (Courtyard, Holy Place, Most Holy Place), furniture, services (daily/yearly), and spiritual realities (Justification, Sanctification, Judgment/Vindication); interactive vector blueprint workstation with hotspot inspection, chronological "Plan of Salvation" slider (AD 31 Cross → Heavenly Inauguration → 1844 Judgment), in-text verse badges, and inspector banner — WP-032, ADR-025, FB #24
- `[x]` **A12. Progressive Spirit of Prophecy Narrative Navigation & Chapter Reader** — progressive disclosure commentary hierarchy from compact, single-line reference chips with teaser previews to full-chapter contextual reading drawers with automatic target paragraph centering, physical pagination fidelity breaks matching printed pages, sequential chapter traversal (‹ Prev / Next ›), and panel zoom (`z`) — WP-033, ADR-025
- `[x]` **A13. Treasury of Scripture Knowledge (TSK) Whole-Bible Cross-References** — ingest ~340,000 scripture-interpreting-scripture cross-reference pairs across all 66 books and 31,102 verses into `data/bible.db`, unlocking instant reciprocal navigation, vote-ranked relevance, and candidate reference generation for future chapter curation — ADR-026, WP-035 (engine), WP-036 (interactive workstation UI: Web GUI + Textual TUI Tab 6, Layer A curated + Layer B TSK, event-delegated navigation, EGW token routing, ARIA roles)

### B. Macula / Linguistic Data Integration
- `[x]` **B0. WordGraph foundation** (ADR-010) — lemma-centric lexical knowledge graph, complete for whole-book Genesis (`lexicons/wordgraph-genesis.json`); the substrate that Macula integration will enrich (WP-010 draft engine consumes it)
- `[x]` **B1. Phase 1: reference integration** — Pin upstream Clear-Bible Macula Hebrew (`47db250bd55d0d8577f2a94fba114ef16c35b23c`), download Lowfat XML datasets (Gen 1-50), extract Strong's Hebrew ↔ LXX Greek Strong's crosswalk and SDBH semantic domains into `lexicons/macula-genesis.json` (ADR-012)
- `[x]` **B2. Phase 2: automated lookup** — Zero-dependency query engine (`search/macula/lookup.py`), whole-Bible SQLite database (`data/macula.db`, ADR-014), and CLI (`scripts/macula_lookup.py`) for looking up Strong's LXX alignments, SDBH domains, and clause syntax trees/participant roles by verse/token without heavyweight external libraries
- `[x]` **B3. Phase 3: semantic enrichment** — use Macula syntactic frames/roles to explain relationships and empirical Septuagint (LXX) translation equivalences to ground cross-language links (ADR-015, WP-015)
- `[x]` **B4. Original-Language Theological Nuances** — plain-English theological glosses for Hebrew verbal stems (Qal, Niphal, Piel, Pual, Hiphil, Hophal, Hitpael) and Greek aspects/voices (Aorist, Present, Perfect across Active/Middle/Passive), accessible without formal seminary training via HTTP endpoint (`/api/nuance`) and interactive UI cards with progressive disclosure — WP-031, ADR-025

### C. Search & Semantic Engine
- `[ ]` **C1. True semantic embeddings** — enable multilingual-e5 by default when corpus is large enough
- `[ ]` **C2. Hybrid search** — FTS5 BM25 + embeddings, combined ranker
- `[ ]` **C3. Cross-language semantic search** — search in one language, find linked content in others
- `[x]` **C4. Faceted/filtered querying** — by book/theme/translation/language/status; clean query API
  (Phases 1–3 shipped: `search/corpus/query.py` + CLI flags + `/api/c4-query` endpoint + cross-source BM25 ranking across curated entries, Bible, and EGW; `search/test_query.py`, 10 tests)
- `[ ]` **C5. Validate & expand discovery layer** — more curated links → stronger candidate signal
- `[x]` **C6. Master Prophetic Key Table & Symbol Chaining** — deterministic historicist prophetic symbol dataset (`data/prophetic_lexicon.json`), real-time search/filter table UI, and in-context Scripture chaining linking apocalyptic symbols (Daniel 7, Revelation 12) directly to their defining Old Testament keys and historical consensus citations — WP-031, ADR-025

### D. Application / UX
- `[x]` **D1. NotebookLM-like web UI** — **primary face of the tool per ADR-024 (GUI-first)**: local web app (`search/ui/web.py`, `search/ui/web_server.py`, `web/`) serving static HTML/CSS/JS on localhost, opened automatically in default browser; browser tab now (Phase 1 delivered in WP-029), embedded Tauri window later; TUI retained as a mode/nightly channel (`bible-study --tui`). Visual identity and ergonomics established per ADR-025 and WP-030 (Study Room Desk warm sepia and dark walnut substrates, draggable 65/35 split pane, `f` Focus Mode, `z` Panel Zoom, WCAG AAA compliant contrast, progressive disclosure); interactive Master Prophetic Key Table and in-context symbol cards delivered in WP-031; interactive Sanctuary Typology Blueprint and in-text station breadcrumbs delivered in WP-032; progressive Spirit of Prophecy commentary chapter reader and pagination fidelity delivered in WP-033.
- `[ ]` **D2. Local on-device app** — user-supplied-text model (NOTICE.md)
- `[x]` **D3. Reading & study experience** — Modern Textual interactive workstation (`search/ui/app.py`, `search/ui/themes.py`, `scripts/study.py`) with persistent viewport architecture (<1ms navigation), plain-English verbal stems & theological nuances (`search/corpus/grammar_nuance.py`: Qal, Niphal, Piel, Hiphil, Hitpael, Aorist Middle, Perfect Passive), Pauline argument flow & discourse markers (`search/corpus/discourse_flow.py`), Scripture-interpreting-Scripture OT citation anchors (`search/corpus/ot_citations.py`), unabridged scholarly BDB/Abbott-Smith lexicons, dual-language syntax framing, KJV word-to-Strong's mapping, full-text EGW reader, direct citation navigation (`PP 44.1`, `[PP.44.1]`), 7 themes, and tabbed inspector — WP-021..WP-027, ADR-017..ADR-020
- `[x]` **D4. CLI polish** — Unified human-friendly CLI surface (`scripts/study.py`) and interactive readline shell (`search/ui/shell.py`) with colored typography, boxed panels, and JSON support — WP-021, ADR-017
- `[ ]` **D5. Historical-Grammatical Context Layer** — integrate historical, cultural, and geographical context per verse into the workstation inspector, grounded in the SDA *"Methods of Bible Study"* (1986) historical-grammatical method. Three-phase implementation: (A) curated `historical_context:` YAML front-matter for high-value passages (schema documented, Gen 1:1, John 1:1, John 17:1 seeded); (B) per-book historical preambles in corpus dirs (John and Genesis done); (C) `data/history.db` from STEPBible TIPNR + OpenBible.info Geography — new inspector tab, verse-level era/location/culture panels — ADR-022

### E. AI Integration & Review Workflow
- `[ ]` **E1. AI-assisted study assistant** — query KB → pull materials → structured AI response
- `[ ]` **E2. AI-suggestion review tooling** — workflow/UI to review & promote from ai-discovered-links.json
- `[ ]` **E3. Tag/cross-ref suggestion engine** — AI proposes, human approves
- `[ ]` **E4. AI provenance & confidence tracking** — stronger audit of AI vs human

### F. Data Integrity & Validation
- `[x]` **F1. Schema validator** — `search/validation/schema.py` — validate entry frontmatter against taxonomy + kc-schema
- `[x]` **F2. Strong's number verification** — `search/validation/strongs.py` — format/range now; canonical-list mode when `lexicons/strongs-list.json` exists
- `[x]` **F3. Cross-reference integrity checker** — `search/validation/xrefs.py` — xref targets resolve
- `[x]` **F4. Broken-link / dead-reference audit** — `search/validation/audit.py`

### G. Engineering Infrastructure
- `[x]` **G1. CI pipeline** — `.gitlab-ci.yml` — runs tests + F1-F4 validators on every MR; blocks merge on errors
- `[ ]` **G2. Test expansion** — validator self-tests (F1–F4 each ≥ 10 unit tests), passage-normalization regression suite (covers the `Ps.3.0` CI failure class), generator golden tests, Textual async flakiness elimination (`_wait_until_ready` pattern), CI health dashboard — WP-028
- `[ ]` **G3. Index caching / incremental rebuilds** — avoid full rebuilds as corpus grows
- `[ ]` **G4. Performance at scale** — benchmark FTS5 + embeddings on large corpus
- `[x]` **G5. Packaging / install** + session-portability infra (AGENTS.md charter, .opencode/ reviewer agent + /verify command, scripts/status.py briefing, docs/decisions/ ADRs, docs/wp/ work packages, docs/WORKFLOW.md) — `pyproject.toml` (deps pinned, namespace packages, pytest config); editable install verified; documented run-from-repo-root workflow
- `[x]` **G6. Developer Ergonomics & Single-Command Bootstrapping** — root `./bootstrap.sh` entrypoint, automated raw source fetching and database hydration (`--data`), stale editable install finder auto-refresh and detection, and isolated clean-clone validation — WP-034

### S. Source Agreement Layer *(new — cross-source comparison as first-class data)*
- `[x]` **S1. Fact model + source adapters** — typed facts (`verse_text`, `word_strongs`, `lexicon_gloss`) extracted from each pinned source (KJV-osis, OSHB, strongs-lexicon, TBESH/TBESG); adapter counts reconcile with sources
- `[x]` **S2. Comparison engine + Agreement Ledger** — `correlations/agreement-ledger.json`: per-key readings from every source, `agree|disagree|one-sided` status, summary stats; phase 1 = lexicon gloss comparison (Strong's <-> TBESH/TBESG, all codes) + per-verse Strong's multisets (KJV-osis <-> OSHB, Genesis 1)
- `[x]` **S3. CI golden-baseline gate + review workflow + verify_all.sh** — new disagreement on re-pin forces review; corpus-vs-source divergences are soft findings, never CI walls; single human-friendly verification command
- `[x]` **S4. Apparatus view + word-level alignment** — `correlations/apparatus-genesis1.json`: per-verse token alignment (order-free per-code pairing; matched correspondence table + 94 concrete omissions with WLC text/position/morph). Full positional sequence alignment remains future

### H. Governance & Community
- `[ ]` **H1. Contribution workflow hardening** — complete the Review Stage sections in CONTRIBUTION_STANDARDS.md
- `[ ]` **H2. Reviewer tooling** — make the human-review gate easy (semantic-link promotion UX)
- `[ ]` **H3. Contributor docs** — onboarding guide, entry-authoring quickstart
- `[ ]` **H4. Code of conduct** — community/curation emphasis
- `[ ]` **H5. Release & versioning** — tagged releases, changelog
- `[x]` **H6. Verifiable Curation Manifest & Velocity Dashboard** — terminal `status: approved` lifecycle state, cryptographic `data/curation-manifest.json` auditing human review, and real-time curation frontier breakdown in `scripts/status.py` — WP-037

### P. Public Distribution *(new — making the Word accessible to everyone)*
> *"What's the point of having the word and not sharing it?"*
- `[~]` **P1. GUI-first zero-Python distribution** — frozen engine binary + sidecar `data/` folder + browser launcher (Phase 1 delivered in WP-029, `v0.1.3-alpha`), native desktop installer & embedded window via Tauri (Phase 2 in progress: WP-038, ADR-024, ADR-028: macOS `.dmg` / Windows `.exe` / Linux `.AppImage`); zero Python or terminal required; pre-built databases included; first-run setup wizard; public-domain EGW one-click download
- `[ ]` **P2. Docker image** — container running workstation in web terminal (ttyd); accessible at `localhost:8080`; for servers, NAS, technically confident users
- `[x]` **P3. GitLab Releases CI** — automated binary builds on `v*` tags; release notes generated from ROADMAP + CHANGELOG
- `[ ]` **P4. First public release `v0.1.0`** — binary + illustrated INSTALL.md + USER_GUIDE.md as primary entry point

---

## Sequencing (ordered plan)

Rationale: **data integrity is the foundation** — nothing else is trustworthy
without it. Build validators first as guardrails, then use them to produce a
correct Strong's dataset, then expand the corpus safely. The discovery/
embedding value (C) only pays off once the corpus is large; the UI/app (D) and
AI assistant (E) depend on a solid data + integrity layer.

## CI/CD, in plain English

*"CI" (Continuous Integration)* means: every time someone proposes a change
(a Merge Request), a clean automated machine runs our checks and blocks the
change if any fail. It is the "robot gatekeeper" that enforces the
data-integrity foundation so bad data can't silently reach the deterministic
core. For this project, CI = *run the test suite + the F1-F4 validators on
every MR* (see `.gitlab-ci.yml`).

*"CD" (Continuous Delivery)* means: automatically building and shipping the
software. This project has nothing to deploy yet, so CD is not relevant for
now — CI is the half we use.

The key point: CI is just automating commands you already run locally. If a
contributor runs `python -m search.validation.schema --repo .` and it's clean,
the robot will be too. No extra knowledge needed — CI is a wrapper, not a
separate skill.

### Phase 1 — Data Integrity Foundation *(the load-bearing layer)* — ✅ DONE
1. **F1 — Schema validator** — entry frontmatter vs taxonomy + kc-schema
   `search/validation/schema.py` — ✅ (reviewed & hardened)
2. **F2 — Strong's number verification** — canonical H/G list
   `search/validation/strongs.py` + `build_strongs_lexicon.py` — ✅ (canonical
   list active: `lexicons/strongs-list.json` — full 8674 Hebrew + 5624 Greek
   enumeration, generated from gmlewis/bible-codes, pinned in
   `data/PROVENANCE.md`)
3. **F3 — Cross-reference integrity checker** — xref targets resolve
   `search/validation/xrefs.py` — ✅ (malformed=error, forward-ref=warning)
4. **F4 — Broken-link / dead-reference audit**
   `search/validation/audit.py` — ✅ (related/semantic_links/links-file/index)
5. **F6 — SQLite content-level integrity** (ADR-027): `data/INTEGRITY.json`
   content hash vs canonical projection (deep ~24s / fast shape+counts);
   `search/validation/db_integrity.py` and `scripts/integrity_drift_battery.py` — ✅.
6. **F6.x — Source-DB read hygiene** (ADR-027 §5): all runtime/verification
   reads sidecar-free (`search.dbaccess.connect_db_reader`; `mode=ro&immutable=1`
   when WAL is checkpointed, WAL-aware otherwise); writers checkpoint on close —
   completed in two commits after review found four runtime read paths still
   opening DBs read-write (21dab18 + 697542e) — ✅.

All four exit non-zero on errors and are wired to run as commands (ready for
CI, see G1). The Strong's source of truth is gmlewis/bible-codes
(Apache-2.0; underlying Strong's Concordance is public domain), pinned with
SHA-256 in `data/PROVENANCE.md` and fetchable via `scripts/fetch_sources.sh`.
scrollmapper/bible_databases (MIT) additionally serves A6 (translations).

### Phase 2 — Strong's Lexicon Dataset — ✅ DONE
5. **A4 — Full Strong's lexicon dataset** — all H####/G#### with definitions,
   transliteration, KJV usage. ✅ `lexicons/strongs-lexicon.json` (8674 H +
   5624 G, canonical totals pinned by test). F2 verifies corpus tags against
   it. Unlocks content + Macula.

### Phase 3 — Corpus Expansion (validated)
6. **A1 — Complete Genesis 1** (v1-31) — ✅ done (MVP scope; WP-001..WP-006)
7. **A2 — Complete Genesis book + OT expansion** — per ADR-009 (whole-book pipeline, per-chapter WPs): Genesis 2 next (WP-007..WP-008), then Genesis 3+ chapter by chapter, then Exodus, Isaiah, Daniel, Psalms
8. **A3 — Add NT coverage & curated chapters** — ✅ done (WP-027, ADR-021); full NT draft generator, 27 books in taxonomy, per-chapter entries in `materials/bible/nt/`, and curated **John 1** (51 verses) & **John 17** (26 verses) with status: review.
9. **A5 — Greek word-study expansion**
10. **A6 — Public-domain translations** (KJV/ASV/WEB); document user-supplied model

### Phase 4 — Macula / Linguistic Enrichment
11. **B1 — Macula reference integration**
12. **B2 — Macula automated lookup (Text-Fabric)**
13. **B3 — Macula semantic enrichment**

### Phase 5 — Semantic Search Upgrade
14. **C1 — True semantic embeddings**
15. **C2 — Hybrid search**
16. **C3 — Cross-language semantic search**
17. **C4 — Faceted/filtered querying** — ✅ Phase 1 done (`query(facets, text, limit)`, CLI `--theme/--translation/--language/--status/--text`, `/api/c4-query`)

### Phase 6 — Review Workflow & AI Assistant
18. **E2 — AI-suggestion review tooling** (promotion UX)
19. **E3 — Tag/cross-ref suggestion engine**
20. **E1 — AI-assisted study assistant**
21. **E4 — AI provenance & confidence tracking**

### Phase 7 — Application / UX
22. **D3 — Reading & study experience**
23. **D1 — NotebookLM-like web UI**
24. **D2 — Local on-device app**
25. **D4 — CLI polish**

### Phase 8 — Governance & Community
26. **H1 — Contribution workflow hardening**
27. **H3 — Contributor docs**
28. **H4 — Code of conduct**
29. **H2 — Reviewer tooling**
30. **H5 — Release & versioning**

### Cross-cutting (weave throughout, not a phase)
- **G1 — CI pipeline** — enforce F1-F4 + tests on every MR (start once Phase 1 exists)
- **G2 — Test expansion** — grow alongside corpus
- **G3 — Incremental rebuilds** — introduce when rebuild time becomes noticeable
- **G4 — Performance benchmarks** — when corpus is large
- **G5 — Packaging / reproducible env** — early, low effort, high value
- **A7/A8 — SoP + commentaries** — link-out model; enable as review capacity allows
- **C5 — Discovery validation** — continuous, as curated links grow

---

*This document is a living plan. Reorder and adjust as the project evolves;
the goal inventory above is the source of truth for what we're building.*
