# ADR-026: Treasury of Scripture Knowledge (TSK) Cross-Reference Integration & Whole-Bible Hyperlinking

* **Status:** Accepted
* **Date:** 2026-09-15
* **Scope:** Pillar A (Corpus & Content), Pillar C (Search & Semantic Engine), Pillar D (Application/UX), Pillar P (Distribution)
* **Deciders:** Project Maintainer & Strategic Orchestrator
* **Consulted:** [ADR-001](ADR-001-deterministic-core-vs-ai.md) (Deterministic Core), [ADR-002](ADR-002-licensing-and-content-sourcing.md) (Licensing & Sourcing), [ADR-006](ADR-006-provenance-and-generated-artifacts.md) (Provenance & Pins), [ADR-013](ADR-013-design-principles-stewardship-and-scalability.md) (Stewardship & Scale), [ADR-024](ADR-024-gui-first-architecture-tui-as-mode.md) (GUI-First Architecture)
* **Informs:** WP-035, WP-036, WP-037

---

## Context

The Adventist Bible Study Tool relies on the Protestant principle of *Scriptura Sacra sui ipsius interpres* ("Holy Scripture is its own interpreter"). Currently, rich cross-references are hand-curated into per-verse Markdown files (`materials/bible/`). While this provides unmatched theological depth for curated chapters (Genesis 1–3, John 1, John 17; ~157 verses), it leaves the remaining 30,945 verses across 1,189 chapters without cross-references in the UI.

At a rate of one chapter per work package, manually compiling cross-references across all 66 books from scratch would take years. Re-inventing what has already been faithfully assembled by generations of biblical scholars violates [ADR-013](ADR-013-design-principles-stewardship-and-scalability.md) (*"Do the best for God without waste — stand on the shoulders of open-source giants; study, incorporate, adapt, and attribute generously"*).

The *Treasury of Scripture Knowledge* (TSK; Bagster 1836, Torrey 1900) contains ~340,000 to ~500,000 scripture-interpreting-scripture cross references covering every verse in the biblical canon. The OpenBible.info project compiled and normalized this public-domain dataset into a machine-readable cross-reference table (~340,000 reciprocal connections, ~1.98 MB compressed, CC BY 4.0).

## Decision

We incorporate the *Treasury of Scripture Knowledge* (TSK) cross-reference dataset directly into the deterministic SQLite data layer (`data/bible.db`), unlocking immediate, reciprocal, whole-Bible cross-referencing across all 31,102 verses.

### 1. Ingestion & Storage Model
* **Database Integration:** A dedicated `cross_references` table is created in `data/bible.db`:
  ```sql
  CREATE TABLE IF NOT EXISTS cross_references (
      from_verse TEXT NOT NULL,
      to_verse TEXT NOT NULL,
      votes INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (from_verse, to_verse)
  );
  CREATE INDEX IF NOT EXISTS idx_xrefs_from ON cross_references(from_verse);
  CREATE INDEX IF NOT EXISTS idx_xrefs_to ON cross_references(to_verse);
  ```
* **Footprint:** The entire 340,000-edge graph occupies ~12–15 MB when vacuumed with B-Tree indices. Compared to `bible.db` (127 MB) and `macula.db` (14 MB), this payload increase is negligible (<10%).
* **Query Performance:** Sub-millisecond indexed lookup by source verse (`from_verse`) ordered by relevance (`votes DESC`).

### 2. Lineage, Pinning & Attribution
* **Provenance:** The raw dataset (`cross-references.zip`) is pinned with its upstream download URL and SHA-256 hash in `data/PROVENANCE.md` and fetched via `scripts/fetch_sources.sh`.
* **Legal Attribution:** Attribution to OpenBible.info and the public-domain Treasury of Scripture Knowledge is registered in `NOTICE.md` under CC BY 4.0 terms.
* **Distribution Split:**
  * **Standalone Binary:** Ships with `cross_references` pre-compiled and vacuumed inside the sidecar `data/bible.db`. Zero network activity at runtime; 100% offline-first.
  * **Source Build:** Pinned, fetched, and compiled deterministically through `scripts/fetch_sources.sh` and `scripts/build_release_data.sh`.

### 3. Layering with Curated Markdown Entries
* TSK cross-references serve as **Layer B (Canonical Structural Foundation)**.
* Curated markdown entries in `materials/bible/` remain **Layer A (High-Touch Curated Insight)** with specific Adventist theological framing, Spirit of Prophecy anchors, and linguistic nuances.
* When viewing a verse:
  1. High-touch curated cross-references are highlighted prominently with theological annotations.
  2. Broad TSK cross-references provide exhaustive canonical connections with vote-ranked relevance chips.
  3. Curation workflows and suggestion engines (E2/H2) can consume TSK to propose candidate cross-references for human approval.

## Consequences

* **Positive:** Instantaneous whole-Bible cross referencing for all 66 books and 31,102 verses. Eliminates the cold-start problem when navigating uncurated chapters.
* **Positive:** Drastically accelerates future curation by providing candidate references directly to human reviewers.
* **Neutral:** Adds ~12–15 MB to `data/bible.db`.
* **Negative:** Requires updating `scripts/fetch_sources.sh`, `scripts/build_release_data.sh`, and `data/PROVENANCE.md`.
