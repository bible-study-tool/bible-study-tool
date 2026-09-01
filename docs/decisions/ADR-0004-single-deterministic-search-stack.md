# ADR-0004: Single deterministic search stack (SQLite FTS5)

**Status:** Accepted · **Date:** 2026-08-27; recorded 2026-09-01

## Context

Two engines had accumulated: a TF-IDF script (search/semantic_search.py,
required scikit-learn, did not even compile) and the linking pipeline
(SQLite FTS5 + BM25, metadata queries, cross-references, pluggable embedder).
Honesty note: FTS5 is lexical, not neural-semantic.

## Decision

Consolidate onto the linking pipeline. The TF-IDF engine was removed; all
deterministic lookups (free text, Strong's, tag, --xref) are native to
`search/linking/dbindex.py` over `index/semantic.db` (generated, gitignored).
Dependencies: numpy + PyYAML only.

## Consequences

* One engine, one CLI surface, no scikit-learn dependency.
* Later upgrades (embeddings, hybrid search) extend the pluggable embedder
  rather than adding a second stack.
