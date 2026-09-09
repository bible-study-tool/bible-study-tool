# ADR-011: Whole-Book Draft Scaffolding and JIT Spirit of Prophecy Resolution

**Status:** Accepted · **Date:** 2026-09-03

## Context

1. **Corpus Sizing:** ADR-009 established whole-book generation pipelines, but
   chapters 1–3 were curated sequentially as the pipeline tools were invented
   and hardened. Continuing to generate skeletons chapter-by-chapter creates an
   artificial bottleneck: search, lexical tools, and cross-references are blind
   to subsequent chapters, producing hundreds of "forward reference" warnings.
2. **Spirit of Prophecy Sourcing:** Cross-references to Ellen G. White writings
   currently use ad-hoc target IDs (`pat-3-1`) and manual excerpt pasting.
   Shipping entire books of external commentary in Git would bloat the
   repository and introduce licensing complexities (ADR-002).
3. **Developer Experience:** New agents, platforms, and human contributors
   encounter python environment and namespace-package friction when running
   standalone scripts without a unified bootstrap tool.

## Decision

1. **Pre-seed Whole-Book Draft Skeletons (Broad Scaffolding):**
   Batch-generate all remaining chapters of Genesis (chapters 4–50, all 1,533
   verses) as `status: draft` skeletons using `search/corpus/draft_engine.py`.
   This instantly populates the offline concordance, expands the WordGraph
   across the full book, resolves intra-book cross-references, and decouples
   database utility from the pace of human/AI curation.
2. **Just-In-Time (JIT) Spirit of Prophecy Token Resolution:**
   Standardize Spirit of Prophecy cross-references on canonical pagination tokens
   (`egw:PP.57.1` = Book `PP`, Page 57, Paragraph 1). The Git repository stores
   only citation tokens and short fair-use study summaries. Full paragraph text
   is stored in a local, pinned SQLite database (`data/egw.db`) with FTS5 search,
   resolved on-demand (JIT) at display/query time in the CLI and UI.
3. **Automated Bootstrapping:**
   Provide `scripts/bootstrap.sh` to automatically detect or create the virtual
   environment, install the package in editable mode (`pip install -e ".[test]"`),
   verify dependencies, and run diagnostic sanity checks.

## Consequences

* The offline database immediately contains the complete book of Genesis in
  canonical KJV + Hebrew Strong's/morphology, usable from day one.
* Curation proceeds asynchronously in thematic work packages (e.g., WP-012 for
  Gen 4, WP-013 for Gen 6–9 Flood) without blocking corpus completeness.
* The repository remains lean, fast, and cleanly separated from external texts
  while offering paragraph-accurate Spirit of Prophecy lookup and validation.
* Onboarding new agents and human contributors becomes a single `./scripts/bootstrap.sh` command.

Related: ADR-001 (deterministic core), ADR-002 (licensing & sourcing),
ADR-004 (SQLite FTS5), ADR-009 (corpus expansion), ADR-010 (WordGraph).
