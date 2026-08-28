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
- `[ ]` **A1. Complete Genesis 1 creation narrative** — v1-31 (full creation week)
- `[ ]` **A2. Expand OT coverage** — Exodus, Isaiah, Daniel, Psalms (Adventist-prioritized); more word studies
- `[ ]` **A3. Add NT coverage** — John 1, Hebrews, Revelation, Romans
- `[ ]` **A4. Full Strong's lexicon dataset** — all H####/G#### (definitions, transliteration, usage counts). *Prerequisite for much else.*
- `[ ]` **A5. Greek word-study expansion** — corpus is currently Hebrew-dominant
- `[ ]` **A6. Multiple public-domain translations** (KJV/ASV/WEB) bundled; user-supplied model for copyrighted
- `[ ]` **A7. Spirit of Prophecy integration** — link-out + user-supplied-text model (NOTICE.md)
- `[ ]` **A8. Commentaries & study guides** — SDABC-adjacent, Sabbath School
- `[ ]` **A9. Original-language text corpus** — Masoretic Hebrew, LXX Greek as structured data

### B. Macula / Linguistic Data Integration
- `[ ]` **B1. Phase 1: reference integration** — download datasets, Strong's↔Macula mapping
- `[ ]` **B2. Phase 2: automated lookup** — Text-Fabric script (Strong's → Macula annotations)
- `[ ]` **B3. Phase 3: semantic enrichment** — use Macula roles/syntax to enrich semantic-links + translation-equivalence

### C. Search & Semantic Engine
- `[ ]` **C1. True semantic embeddings** — enable multilingual-e5 by default when corpus is large enough
- `[ ]` **C2. Hybrid search** — FTS5 BM25 + embeddings, combined ranker
- `[ ]` **C3. Cross-language semantic search** — search in one language, find linked content in others
- `[ ]` **C4. Faceted/filtered querying** — by book/theme/translation/language/status; clean query API
- `[ ]` **C5. Validate & expand discovery layer** — more curated links → stronger candidate signal

### D. Application / UX
- `[ ]` **D1. NotebookLM-like web UI** — long-term vision
- `[ ]` **D2. Local on-device app** — user-supplied-text model (NOTICE.md)
- `[ ]` **D3. Reading & study experience** — passage view w/ inline word studies, cross-refs, semantic links, SoP tabs
- `[ ]` **D4. CLI polish** — stable, documented CLI surface

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
- `[ ]` **G2. Test expansion** — property/consistency tests; golden tests over corpus
- `[ ]` **G3. Index caching / incremental rebuilds** — avoid full rebuilds as corpus grows
- `[ ]` **G4. Performance at scale** — benchmark FTS5 + embeddings on large corpus
- `[ ]` **G5. Packaging / install** — pyproject.toml, dependency pinning, reproducible env

### H. Governance & Community
- `[ ]` **H1. Contribution workflow hardening** — complete the Review Stage sections in CONTRIBUTION_STANDARDS.md
- `[ ]` **H2. Reviewer tooling** — make the human-review gate easy (semantic-link promotion UX)
- `[ ]` **H3. Contributor docs** — onboarding guide, entry-authoring quickstart
- `[ ]` **H4. Code of conduct** — community/curation emphasis
- `[ ]` **H5. Release & versioning** — tagged releases, changelog

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
   `search/validation/strongs.py` + `build_strongs_list.py` — ✅ (structural
   mode now; canonical-list mode activates when `lexicons/strongs-list.json`
   exists — generated from scrollmapper/bible_databases, see A4)
3. **F3 — Cross-reference integrity checker** — xref targets resolve
   `search/validation/xrefs.py` — ✅ (malformed=error, forward-ref=warning)
4. **F4 — Broken-link / dead-reference audit**
   `search/validation/audit.py` — ✅ (related/semantic_links/links-file/index)

All four exit non-zero on errors and are wired to run as commands (ready for
CI, see G1). Note: the source of truth for strongs-list.json is
scrollmapper/bible_databases (MIT), which also serves A6 (translations) and
the F3 cross-reference source of truth.

### Phase 2 — Strong's Lexicon Dataset
5. **A4 — Full Strong's lexicon dataset** — all H####/G#### with definitions,
   transliteration, usage counts. Verified by F2. *Unlocks content + Macula.*

### Phase 3 — Corpus Expansion (validated)
6. **A1 — Complete Genesis 1** (v1-31)
7. **A2 — Expand OT** (Exodus, Isaiah, Daniel, Psalms)
8. **A3 — Add NT** (John 1, Hebrews, Revelation, Romans)
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
17. **C4 — Faceted/filtered querying**

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
