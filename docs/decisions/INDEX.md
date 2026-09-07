# Decision Records (ADRs)

Architecture Decision Records: one short file per decision that is hard to
reverse or that shapes how all future work happens. Written **at decision
time** (or retroactively seeded, as here) — see `AGENTS.md` Non-negotiable 8.

| ADR | Decision | Status |
| --- | --- | --- |
| [ADR-0001](ADR-0001-deterministic-core-vs-ai.md) | Deterministic core vs AI layer boundary | Accepted |
| [ADR-0002](ADR-0002-licensing-and-content-sourcing.md) | Dual licensing + link-out content sourcing | Accepted |
| [ADR-0003](ADR-0003-standard-yaml-frontmatter.md) | Standard `---` YAML frontmatter as the entry format | Accepted |
| [ADR-0004](ADR-0004-single-deterministic-search-stack.md) | Single deterministic search stack (SQLite FTS5) | Accepted |
| [ADR-0005](ADR-0005-data-integrity-precedes-scale.md) | Data integrity precedes scale (validators + CI) | Accepted |
| [ADR-0006](ADR-0006-provenance-and-generated-artifacts.md) | Source pinning + generated-artifact discipline | Accepted |
| [ADR-0007](ADR-0007-source-agreement-layer.md) | Source Agreement Layer (facts → ledger → apparatus) | Accepted |
| [ADR-0008](ADR-0008-future-architecture-and-packaging.md) | Future architecture & packaging direction (3-tier engine, tiered distribution) | Proposed |
| [ADR-0009](ADR-0009-corpus-expansion-model.md) | Corpus expansion model — whole-book pipeline, per-chapter work packages | Accepted |
| [ADR-0010](ADR-0010-wordgraph.md) | The WordGraph — a lemma-centric lexical knowledge graph (evolution of Strong's) | Accepted |
| [ADR-0011](ADR-0011-whole-book-scaffolding-and-jit-egw.md) | Whole-Book Draft Scaffolding and JIT Spirit of Prophecy Resolution | Accepted |
| [ADR-0012](ADR-0012-macula-hebrew-linguistic-integration.md) | Macula Hebrew Linguistic Integration & Strong's-LXX Crosswalk | Accepted |
| [ADR-0013](ADR-0013-design-principles-stewardship-and-scalability.md) | Design principles — stewardship, excellence, scalable simplicity ("Doing the best for God without waste") | Accepted |
| [ADR-0014](ADR-0014-whole-bible-macula-sqlite-architecture.md) | Whole-Bible Macula SQLite Architecture (`data/macula.db`) | Accepted |
| [ADR-0015](ADR-0015-macula-semantic-enrichment.md) | Macula Semantic Role & Translation-Equivalence Enrichment | Accepted |
| [ADR-0016](ADR-0016-two-tier-corpus-and-portable-backup.md) | Two-Tier Storage Architecture and Portable Offline Backup | Accepted |
| [ADR-0017](ADR-0017-terminal-user-interface-and-unified-study-cli.md) | Interactive Terminal User Interface (TUI) and Unified Study CLI | Accepted |
| [ADR-0018](ADR-0018-textual-study-workstation-and-themes.md) | Textual Study Workstation and Theme System | Accepted |
| [ADR-0019](ADR-0019-accessible-original-languages-and-commentary-integration.md) | Human-Accessible Original Language Framing and Direct Commentary Navigation | Accepted |
| [ADR-0020](ADR-0020-persistent-viewport-workstation-and-comprehension-engine.md) | Persistent Viewport Workstation Architecture & Biblical Comprehension Engine | Accepted |
| [ADR-0021](ADR-0021-new-testament-corpus-and-curation.md) | New Testament Corpus Generation and Per-Chapter Curation Model | Accepted |
| [ADR-0022](ADR-0022-historical-grammatical-context-layer.md) | Historical-Grammatical Context Layer — historical/cultural/geographical data in the workstation | Proposed |
| [ADR-0023](ADR-0023-zero-python-distribution-and-packaging.md) | Zero-Python Distribution & Standalone Desktop Packaging (Pillar P) | Proposed |


## When to write one

Whenever a decision is (a) hard to reverse, (b) shapes future work, or
(c) was genuinely debated. If you're mid-conversation with an assistant when
the decision lands, ask it to draft the ADR before moving on. Format:
Context → Decision → Consequences. Keep each under ~40 lines; link related
ADRs.
