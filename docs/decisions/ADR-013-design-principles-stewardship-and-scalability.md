# ADR-013: Design Principles — Stewardship, Excellence, and Scalable Simplicity

**Status:** Accepted · **Date:** 2026-09-04

## Context

1. **Foundational Motivation:** This project is built to aid the honest, deep,
   and faithful study of God's Word. Because our service is rendered unto God,
   the engineering standards and care we bring to Scripture must reflect our
   highest commitment to excellence, integrity, and diligence.
2. **The Danger of Extremes:**
   - **Shortsighted "Toy" Engineering:** Building narrow, single-chapter or
     in-memory hacks that work only for proof-of-concept scopes (like Genesis 1–3)
     but crumble, slow down, or exhaust memory when scaled to the entire Bible
     (66 books, 31,102 verses) or large commentary corpuses (100k+ pages).
   - **Wasteful Enterprise Overkill:** Importing dozens of heavy external
     dependencies, complex microservices, or terabyte-scale distributed engines
     that introduce brittle build steps, security attack surfaces, and
     unnecessary operational overhead for tasks readily solved by lean,
     battle-tested local tools.
3. **Open-Source Synergy:** Generous open-source projects have spent years
   refining parsers, lexicons, and biblical data structures. Reinventing these
   wheels from scratch is both prideful and inefficient; ignoring them wastes
   God-given time and resources.

## Decision

We adopt as a core architectural design principle:
**"We are doing this for God. So we must do the best we can without being wasteful."**

In engineering practice, this dictates:

1. **Whole-Bible Scalability by Design:** Every tool, data model, and query
   engine must be designed with the full scope of the canon (OT + NT, 66 books,
   ~31,102 verses) and full external study corpuses (tens of millions of words)
   in view. We favor disk-backed, zero-dependency indexed engines (such as
   SQLite FTS5, B-trees, and memory-mapped indexes) that sustain sub-millisecond
   lookups under full-scale production data without blowing RAM.
2. **Lean & Zero-Waste Stewardship:** Avoid unnecessary dependencies and
   overkill abstractions. Keep runtime requirements minimal (Python standard
   library + SQLite where possible), ensuring anyone can run the tool offline on
   modest hardware anywhere in the world.
3. **Stand on the Shoulders of Giants:** When battle-tested open-source
   solutions exist, we study, adapt, integrate, or reference their patterns
   rather than building from scratch. We give clear, prominent attribution
   and credit in our documentation and provenance records.

## Consequences

* The Macula linguistic engine will expand beyond in-memory JSON to a scalable,
  unified, disk-backed SQLite indexing architecture (`data/macula.db`) as it
  scales to the whole Old and New Testaments.
* The Spirit of Prophecy (EGW) bulk ingestion engine will leverage proven
  open-source patterns (e.g., Gospel Sounders / FTS5 schemas) and standard
  EPUB/text parser structures to ingest millions of words efficiently.
* The codebase remains robust, fast, portable, and cleanly attributed.

Related: ADR-001 (deterministic core), ADR-002 (licensing & sourcing),
ADR-004 (SQLite FTS5), ADR-010 (WordGraph), ADR-011 (JIT EGW), ADR-012 (Macula).
