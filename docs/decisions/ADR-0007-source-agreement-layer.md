# ADR-0007: Source Agreement Layer (facts -> ledger -> apparatus)

**Status:** Accepted · **Date:** 2026-09-01

## Context

Every ingested source is independently produced; comparing them is itself
knowledge no single source has (agreement = corroboration; disagreement =
documented tagging philosophy or lexicon nuance). Prior art: text-critical
apparatus, inter-annotator agreement.

## Decision

Three-layer architecture (the approved 1+3 hybrid):

1. **Fact registry** (`search/agreement/facts.py`): typed facts
   (verse_text, word_strongs, lexicon_gloss) extracted per source by adapters
   that reuse the existing parsers.
2. **Agreement Ledger** (`correlations/agreement-ledger.json`): per-key
   readings from every source with status. **Integrity-first policy:**
   `disagree` is reserved for objective-equality facts (word_strongs
   multisets, verse_text strings); gloss phrasing differences are `info`
   side-by-side readings; no-definition entries are `no_reading`. Nothing is
   auto-resolved.
3. **Apparatus** (`correlations/apparatus-genesis1.json`): word-level
   order-free token alignment — correspondence pairs plus concrete omissions
   (94 function-word tags scrollmapper omits that OSHB fully tags).

The ledger is a **golden baseline**: a source re-pin that changes facts fails
CI and forces review before regeneration.

## Consequences

* First genuinely new knowledge layer (no single source documents the 94
  omissions or the gloss agreements).
* Hard CI gates protect machine artifacts and re-pins only; human-content
  differences are soft findings.
* Scaling to more sources costs one adapter each; positional sequence
  alignment remains future work.
