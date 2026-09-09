# ADR-014: Whole-Bible Macula SQLite Architecture

**Status:** Accepted · **Date:** 2026-09-04

## Context

1. **Proof-of-Concept vs. Full Canon:** WP-012 and ADR-012 established our first
   Macula Hebrew integration for Genesis 1–50, generating `lexicons/macula-genesis.json`
   (~2.86 MB). While fast for 50 chapters, scaling this in-memory JSON model across
   all 66 books of the Bible (39 OT Hebrew/Aramaic books + 27 NT Greek books,
   ~31,102 verses, ~550,000 words, ~180,000 syntactic clauses) would produce
   an 80–120 MB monolithic JSON file, consuming significant RAM and causing
   multi-second startup latencies.
2. **Scalability Mandate (ADR-013):** "We are doing this for God. So we must do
   the best we can without being wasteful." We reject shortsighted toy solutions
   that break under the weight of the full biblical canon.
3. **Relational Syntactic Queries:** Biblical study within the Adventist framework
   often investigates participant roles across the canon (e.g., finding all
   prophetic clauses where God or the Angel of the Lord is the explicit grammatical
   Subject, or tracing Greek LXX translation equivalents of covenant terms).
   Relational querying over nested clauses and constituents requires indexed
   tables, not flat dictionary scans.

## Decision

1. **Unified Disk-Backed Database (`data/macula.db`):**
   Implement a local, high-performance SQLite database storing the complete
   syntactic and linguistic data across the canon. The database is gitignored
   and generated locally from pinned upstream source data.
2. **Normalized Relational Schema:**
   - `verses`: canonical reference (`Gen.1.1`), MT reference, book code, chapter, verse, surface text.
   - `clauses`: clause ID, parent verse, clause order, grammar production rule.
   - `constituents`: constituent phrase ID, parent clause, verse ID, grammatical role (`subj`, `pred`, `obj`), role label, phrase class.
   - `tokens`: token ID, parent constituent, verse ID, position, surface text, lemma, morphology, Strong's Hebrew ID, LXX Greek lemma, Greek Strong's ID, SDBH senses and domains.
   - `strongs_crosswalk`: Strong's ID, lemma list, glosses, SDBH domains, LXX equivalents, occurrence count.
3. **B-Tree Indexing:**
   Index `tokens(strongs)`, `tokens(lxx_strongs)`, `tokens(verse_id)`,
   `constituents(role)`, `constituents(clause_id)`, and `clauses(verse_id)`
   for sub-millisecond query response.
4. **Dual-Mode Query Engine:**
   `search/macula/lookup.py` and `scripts/macula_lookup.py` automatically detect
   and query `data/macula.db` when present. If the database file is absent
   (such as in minimal CI test runs), it falls back seamlessly to the committed
   `lexicons/macula-genesis.json` artifact, maintaining 100% offline testability.

## Consequences

* Enables instant, memory-efficient (<15 MB RAM) lookups across millions of tokens.
* Unlocks deep syntactic queries (e.g. searching by grammatical role or clause rule).
* Preserves byte-for-byte provenance gates for Genesis while paving the highway
  for whole-Bible OT and NT linguistic expansion.

Related: ADR-001 (deterministic core), ADR-004 (SQLite search), ADR-012 (Macula Hebrew),
ADR-013 (stewardship and whole-Bible scalability).
