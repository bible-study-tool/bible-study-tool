# ADR-021: New Testament Corpus Generation and Per-Chapter Curation Model

* Status: Accepted
* Date: 2026-09-06
* Deciders: Project Maintainers, Pair Programming Assistant
* Consulted: [ADR-001](ADR-001-deterministic-core-vs-ai.md), [ADR-003](ADR-003-standard-yaml-frontmatter.md), [ADR-005](ADR-005-data-integrity-precedes-scale.md), [ADR-009](ADR-009-corpus-expansion-model.md), [ADR-013](ADR-013-design-principles-stewardship-and-scalability.md)
* Informs: [WP-027](../wp/WP-027-nt-corpus-and-john-curation.md)

## Context

The Adventist Bible Study Tool was initially seeded with Genesis 1–50 (Old Testament Hebrew Masoretic Text). To achieve comprehensive biblical theology and fulfill Pillar A3 of the project roadmap, the offline-first knowledge base must support the Greek New Testament.

Prior to this decision:
1. Only Old Testament books (`book/genesis` through `book/malachi`) were registered in `tags/taxonomy.json`.
2. Markdown verse entries were generated solely via `search/corpus/build_genesis1.py` targeting Hebrew Strong's numbers (`strongs-H*`).
3. Forward cross-references from Genesis entries (e.g., Gen 1:1 pointing to John 1:1) remained unresolved advisory warnings in the F3 validator.
4. The user explicitly directed: "Add John 1 and 17 to the list of chapters to be curated in A3. This is a good proof of concept for the tool, no?" and mandated per-chapter folder structures across biblical books.

## Decision

1. **New Testament Taxonomy Expansion**:
   Add all 27 New Testament books (`book/matthew` through `book/revelation`) to `tags/taxonomy.json` under the `book` category.

2. **Deterministic New Testament Draft Generator (`search/corpus/build_nt.py`)**:
   Implement a deterministic, offline generator that parses the pinned `data/KJV-osis.json`, extracts Greek Strong's concordance numbers (`strongs-G1` through `strongs-G5624`), maps lemmas against `lexicons/strongs-lexicon.json` (Greek public domain) and `lexicons/tbesg-glosses.json` (STEPBible TBESG), and produces conformant markdown verse skeletons.

3. **Standardized Per-Chapter Directory Architecture**:
   Store all NT verse markdown entries in zero-padded, per-chapter subdirectories:
   `materials/bible/nt/{book}/{ch:02d}/{book}-{ch}-{v}-kjv.md`
   (e.g., `materials/bible/nt/john/01/john-1-1-kjv.md`, `materials/bible/nt/john/17/john-17-1-kjv.md`).

4. **Curated Pillar Proof of Concept (John 1 & John 17)**:
   Curate all 51 verses of John 1 (the Logos prologue, Lamb of God sanctuary typology, discipleship) and all 26 verses of John 17 (the High Priestly prayer, Trinitarian covenant oneness, and sanctification in truth) to `status: review`, strictly bounding theological and linguistic notes within `<!-- AI-GENERATED -->` ... `<!-- END AI-GENERATED -->` blocks.

## Consequences

* **Positive**:
  - The repository now possesses full-pipeline scaffolding for all 27 New Testament books.
  - Zero schema or validator regressions: F1 Schema, F2 Strong's, F3 Xrefs, and F4 Audit pass 100% across all 1,610 corpus entries.
  - Resolves foundational cross-testament linkages between Genesis creation typology and Johannine Christology.
* **Operational**:
  - `search/linking/test_pipeline.py` and semantic indices recognize `book/john` and multi-testament corpus entries without assumption of a Genesis-only dataset.
* **Trade-offs / Storage Stewardship**:
  - In accordance with ADR-013 and ADR-016, markdown entries are generated per chapter as needed rather than dumping all 7,957 NT verse markdown files into git at once, keeping the repository footprint minimal while whole-Bible text remains available via `data/bible.db`.
