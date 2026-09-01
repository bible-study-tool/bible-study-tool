# ADR-0009: Corpus expansion model — whole-book pipeline, per-chapter work packages

**Status:** Accepted · **Date:** 2026-09-01

## Context

The MVP scope was Genesis 1 (all 31 verses curated across WP-001..006; A1
marked done). Genesis 2:1-3 — the seventh-day Sabbath — is thematically the
culmination of the creation week and was initially drafted as a standalone
follow-up package. But the corpus's long-term structure is the whole Bible,
book by book. Isolating a three-verse fragment as its own package would
(a) fragment the chapter structure we want for every future book — the same
logic would then apply to any theologically interesting passage,
(b) force the pipeline to special-case chapter 1 instead of generalizing,
and (c) multiply package overhead as the corpus scales to 1,189 chapters.

## Decision

1. **Whole-book generation.** The deterministic pipeline generalizes from
   `search/corpus/build_genesis1.py` to a book-level generator (parameterized
   by book), producing per-book artifacts: skeletons for every verse of the
   book, `correlations/apparatus-{book}.json`,
   `lexicons/morphology-{book}.json`, and book-scoped ledger rows. Genesis is
   the pilot book.
2. **Per-chapter work packages.** Curated content ships as one WP per chapter
   (a coherent group of chapters for very long chapters/books), never per
   passage-fragment. Genesis 2:1-3 therefore ships inside the **Complete
   Genesis 2** WP — theologically the Sabbath culmination of the creation
   week, structurally a chapter of the book.
3. **Package sequencing.** WP-007 = book-level pipeline generalization +
   Genesis 2 skeleton generation (25 verses). WP-008 = curate Genesis 2
   (whole chapter, including 2:1-3). Subsequent WPs continue per chapter
   through Genesis, then the pattern applies to the rest of the OT/NT.

## Consequences

* The `genesis1` artifacts (`apparatus-genesis1.json`,
  `morphology-genesis1.json`) remain as the seeded pilot; the book-level
  generator must keep them byte-identical (backward-compatible naming
  decision, recorded here).
* A1 (Genesis 1) stays closed as the MVP. The roadmap's immediate next goal
  becomes **Complete the book of Genesis, chapter by chapter** — ahead of the
  wider OT expansion (Exodus, Isaiah, Daniel, Psalms).
* The Sabbath study (Gen 2:1-3) still ships — as part of the Genesis-2 WP,
  with its Exodus 20:8-11 / Hebrews 4 / Isaiah 66:23 cross-references intact.
* WP overhead is bounded (~1 WP per chapter, not one per passage); Genesis 2
  (25 verses) is the first large-chapter test of package sizing.

Related: ADR-0001 (deterministic core), ADR-0006 (generated-artifact
discipline), ADR-0007 (agreement layer).