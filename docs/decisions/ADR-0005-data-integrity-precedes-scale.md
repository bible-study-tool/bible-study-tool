# ADR-0005: Data integrity precedes scale

**Status:** Accepted · **Date:** 2026-08-27; recorded 2026-09-01

## Context

Corpus expansion multiplies every latent data defect. Two real bugs had
already slipped into the "human-verified" core (wrong Strong's G2532 vs G746;
missing material/ tags). Scaling before validation would compound them.

## Decision

Validators were built BEFORE large-scale corpus growth, as a tested module
(`search/validation/`) with a CI-friendly CLI:

* F1 schema (frontmatter vs kc-schema + taxonomy), F2 Strong's verification
  (format/range + canonical-list mode), F3 cross-reference integrity
  (malformed = error; forward references = warning), F4 dead-reference audit.
* GitLab CI runs the test suite + all four validators on every MR; errors
  block merge, warnings do not.

## Consequences

* The validators immediately caught real corpus issues on day one.
* Corpus growth (Genesis 1:4-31, future OT/NT) is gated: bad data cannot
  silently enter.
* This ADR is the reason the order of the roadmap puts pillar F before pillar A.
