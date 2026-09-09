# ADR-001: Deterministic core vs AI layer boundary

**Status:** Accepted · **Date:** 2026-08-23 (origin); recorded 2026-09-01

## Context

The tool is AI-assisted by design, but AI output can be wrong, biased, or
subtly theological rather than textual. Trust in a Bible study tool depends
on knowing which claims are verified and which are generated.

## Decision

Two strict layers:

* **Deterministic core (source of truth):** tag taxonomy, YAML frontmatter,
  cross-references, curated semantic links (`correlations/semantic-links.json`),
  Strong's mappings, passage references, indexes. Human-verified only.
* **AI layer (provisional):** word-study insights, discovered links,
  summaries, tag suggestions. Always marked `<!-- AI-GENERATED -->`, never
  authoritative, promoted into the core only after human review. AI-discovered
  semantic links live in `correlations/ai-discovered-links.json` (a tracked
  review queue) and never touch the core directly.

## Consequences

* Every claim's trust level is inspectable (markers + review status).
* The pipeline enforces the boundary mechanically: layer (b) is deterministic,
  layer (c) only writes to the review queue; `aligns_with_doctrine` stays
  null until a human sets it.
* Curation is the bottleneck by design — correctness over throughput.
