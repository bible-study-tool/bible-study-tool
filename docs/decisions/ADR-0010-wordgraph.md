# ADR-0010: The WordGraph — a lemma-centric lexical knowledge graph

**Status:** Accepted · **Date:** 2026-09-01

## Context

Strong's numbers (1890) are the project's legacy crosswalk: every KJV-osis
span is tagged with them, and the agreement ledger/apparatus align on them.
But they are older, not homograph-safe (a single code maps multiple lexemes
e.g. H7307 spirit/wind; H776 earth/land), and modern scholarship works from
lemmas and morphological databases (SDBH, BHSA/Macula, STEPBible), not Strong's
numbers. The project's north star: **the deterministic layer accumulates
truth** — computation should become *more* deterministic as data is added,
never less. Today, word-study prose is re-drafted per verse by LLM (O(verses)
cost, re-inferring the same lexemes every time). The corpus's future is the
whole Bible (~31k verses, ~10k Hebrew lexemes, ~5.6k Greek).

## Decision

Build a **lemma-centric lexical knowledge graph ("WordGraph")** as the
deterministic spine of word studies:

1. **Three-layer identifier stack.**
   - **Token layer**: every OSHB word token keeps its stable id (e.g.
     `01xeN`); English spans link via the apparatus.
   - **Lexeme layer**: OSHB base form + **homograph index** (ETCBC-style
     numbering) — the load-bearing identity, because Hebrew homographs are
     real. Curated, grown through review.
   - **Legacy crosswalk**: Strong's numbers retained as a *mapping* (KJV
     tags, ledger, apparatus), no longer primary identity.
2. **Aggregate-first dictionary.** The graph is built by *linking existing
   licensed data* — Strong's lexicon, BDB (public domain; to be fetched +
   pinned), TBESH/TBESG (CC BY 4.0), OSHB morphology, SDBH sense ids
   (license-permitting) — plus derived occurrence indexes and cross-links.
   Deterministic, complete-on-day-one for the in-scope books. Original
   authored glosses grow lexeme-by-lexeme through the existing review
   workflow (never bulk-AI-authored).
3. **Word-study generation.** Verse word-study blocks are *assembled
   deterministically* from the graph (verse text + per-lexeme blocks +
   occurrence context) instead of LLM-drafted per verse. The LLM's role
   shrinks to genuinely interpretive content (theological connections,
   summary prose) or disappears for routine verses.
4. **Book-scoped artifacts.** WordGraph ships per book
   (`lexicons/wordgraph-genesis.json` etc.); existing artifacts
   (strongs-*, tbesh-*, morphology-*, apparatus-*) remain byte-identical;
   the graph *consumes* them and adds the cross-links.
5. **Cross-translation equivalence** (the C-pillar deep end): starts with
   KJV-osis only (already Strong's-tagged → deterministic). ASV/WEB
   alignment is a future LLM-assisted research task, validated by the
   deterministic layer.

## Consequences

* Word studies drop from O(verses) LLM cost to O(lexemes) deterministic
  assembly — the largest content-class reduction (est. 5-8x).
* The tool becomes a biblical dictionary *and* a Bible: every word in any
  verse pulls its full accumulated metadata deterministically.
* The deterministic layer grows toward truth: each curated lexeme enriches
  every future verse that uses it, forever.
* Strong's remains honored but demoted: crosswalk, not identity — future
  scholarship layers (SDBH, Macula/BHSA) can be added without re-tagging.
* Homograph curation is a bounded, honest linguistic task — grown through
  review, deterministic once curated.
* WordGraph is the substrate levers B/C/D/E operate off (claims-checker,
  pre-verified fact-sheets, templates, two-tier review).

Related: ADR-0001 (deterministic core vs AI), ADR-0006 (generated-artifact
discipline), ADR-0007 (agreement layer), ADR-0009 (book-level pipeline).