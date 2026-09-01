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
| [ADR-0009](ADR-0009-corpus-expansion-model.md) | Corpus expansion model — whole-book pipeline, per-chapter work packages | Proposed |
| [ADR-0010](ADR-0010-wordgraph.md) | The WordGraph — a lemma-centric lexical knowledge graph (evolution of Strong's) | Proposed |

## When to write one

Whenever a decision is (a) hard to reverse, (b) shapes future work, or
(c) was genuinely debated. If you're mid-conversation with an assistant when
the decision lands, ask it to draft the ADR before moving on. Format:
Context → Decision → Consequences. Keep each under ~40 lines; link related
ADRs.
