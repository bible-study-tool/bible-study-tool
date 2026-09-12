# Decision Records (ADRs)

Architecture Decision Records: one short file per decision that is hard to
reverse or that shapes how all future work happens. Written **at decision
time** (or retroactively seeded, as here) — see `AGENTS.md` Non-negotiable 8.

| ADR | Decision | Status |
| --- | --- | --- |
| [ADR-001](ADR-001-deterministic-core-vs-ai.md) | Deterministic core vs AI layer boundary | Accepted |
| [ADR-002](ADR-002-licensing-and-content-sourcing.md) | Dual licensing + link-out content sourcing | Accepted |
| [ADR-003](ADR-003-standard-yaml-frontmatter.md) | Standard `---` YAML frontmatter as the entry format | Accepted |
| [ADR-004](ADR-004-single-deterministic-search-stack.md) | Single deterministic search stack (SQLite FTS5) | Accepted |
| [ADR-005](ADR-005-data-integrity-precedes-scale.md) | Data integrity precedes scale (validators + CI) | Accepted |
| [ADR-006](ADR-006-provenance-and-generated-artifacts.md) | Source pinning + generated-artifact discipline | Accepted |
| [ADR-007](ADR-007-source-agreement-layer.md) | Source Agreement Layer (facts → ledger → apparatus) | Accepted |
| [ADR-008](ADR-008-future-architecture-and-packaging.md) | Future architecture & packaging direction (3-tier engine, tiered distribution) | Proposed |
| [ADR-009](ADR-009-corpus-expansion-model.md) | Corpus expansion model — whole-book pipeline, per-chapter work packages | Accepted |
| [ADR-010](ADR-010-wordgraph.md) | The WordGraph — a lemma-centric lexical knowledge graph (evolution of Strong's) | Accepted |
| [ADR-011](ADR-011-whole-book-scaffolding-and-jit-egw.md) | Whole-Book Draft Scaffolding and JIT Spirit of Prophecy Resolution | Accepted |
| [ADR-012](ADR-012-macula-hebrew-linguistic-integration.md) | Macula Hebrew Linguistic Integration & Strong's-LXX Crosswalk | Accepted |
| [ADR-013](ADR-013-design-principles-stewardship-and-scalability.md) | Design principles — stewardship, excellence, scalable simplicity ("Doing the best for God without waste") | Accepted |
| [ADR-014](ADR-014-whole-bible-macula-sqlite-architecture.md) | Whole-Bible Macula SQLite Architecture (`data/macula.db`) | Accepted |
| [ADR-015](ADR-015-macula-semantic-enrichment.md) | Macula Semantic Role & Translation-Equivalence Enrichment | Accepted |
| [ADR-016](ADR-016-two-tier-corpus-and-portable-backup.md) | Two-Tier Storage Architecture and Portable Offline Backup | Accepted |
| [ADR-017](ADR-017-terminal-user-interface-and-unified-study-cli.md) | Interactive Terminal User Interface (TUI) and Unified Study CLI | Accepted |
| [ADR-018](ADR-018-textual-study-workstation-and-themes.md) | Textual Study Workstation and Theme System | Accepted |
| [ADR-019](ADR-019-accessible-original-languages-and-commentary-integration.md) | Human-Accessible Original Language Framing and Direct Commentary Navigation | Accepted |
| [ADR-020](ADR-020-persistent-viewport-workstation-and-comprehension-engine.md) | Persistent Viewport Workstation Architecture & Biblical Comprehension Engine | Accepted |
| [ADR-021](ADR-021-new-testament-corpus-and-curation.md) | New Testament Corpus Generation and Per-Chapter Curation Model | Accepted |
| [ADR-022](ADR-022-historical-grammatical-context-layer.md) | Historical-Grammatical Context Layer — historical/cultural/geographical data in the workstation | Proposed |
| [ADR-023](ADR-023-zero-python-distribution-and-packaging.md) | Zero-Python Distribution & Standalone Desktop Packaging (Pillar P) | Accepted (Partially superseded by ADR-024) |
| [ADR-024](ADR-024-gui-first-architecture-tui-as-mode.md) | GUI-First Architecture — Local Web UI as Primary Face, TUI as a Mode (Pillar D/P) | Accepted |
| [ADR-025](ADR-025-visual-identity-and-anti-slop-design-charter.md) | Visual Identity, "Divinity Hall Desk" Mental Anchor, and Anti-Slop Design Charter | Accepted |


## When to write one

Whenever a decision is (a) hard to reverse, (b) shapes future work, or
(c) was genuinely debated. If you're mid-conversation with an assistant when
the decision lands, ask it to draft the ADR before moving on. Format:
Context → Decision → Consequences. Keep each under ~40 lines; link related
ADRs.
