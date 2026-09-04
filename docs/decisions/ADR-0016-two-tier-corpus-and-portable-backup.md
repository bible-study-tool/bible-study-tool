# ADR-0016: Two-Tier Storage Architecture and Portable Offline Backup

**Status:** Accepted · **Date:** 2026-09-04

## Context

1. **Bring-Your-Own-Data (BYOD) Legal Boundaries:** Per `NOTICE.md` and ADR-0002,
   copyrighted materials and proprietary commentaries are never bundled in this
   git repository. Furthermore, automated scrapers with synthetic browser headers
   must not be shipped in the public repository to avoid DMCA/ToS exposure. The
   repository ships zero-dependency local multi-format ingestion engines (`egw_importer.py`,
   parsers) and query tools that operate on local, user-supplied files.
2. **Corpus Scope & User Collections:** Beyond the foundational Spirit of Prophecy
   writings (~100,000 pages across 414 official English publications), serious
   Adventist biblical research demands study across multiple corpus tiers:
   - Early Adventist Pioneers (e.g. Uriah Smith *Daniel and the Revelation*,
     J.N. Andrews, J.N. Loughborough, Alonzo T. Jones, E.J. Waggoner).
   - Biblical Commentaries (e.g. *SDA Bible Commentary*, Matthew Henry, Jamieson-Fausset-Brown).
   - User-supplied books, research papers, and personal study annotations.
   Hardcoding single-purpose schemas (e.g., `egw_paragraphs`) prevents modular
   expansion and risks schema fragmentation.
3. **Deterministic Core vs. Local Overlay Separation:** Under `AGENTS.md` Non-negotiable 1
   and ADR-0001, the deterministic biblical core (`materials/`, `correlations/semantic-links.json`,
   `lexicons/`) is cryptographically pinned, peer-reviewed, and gated by CI. User-uploaded
   or unvetted personal materials must never silently enter canonical cross-reference
   graphs without explicit human review and canonical vetting.
4. **Data Portability & Offline Migration:** Users who invest months indexing
   corpuses or creating personal annotations must not lose their work when migrating
   between machines, switching operating systems, or working in air-gapped environments.
   A single-command, offline, portable backup and restore engine with cryptographic
   integrity verification is essential.

## Decision

1. **Harvester Script Untracking:**
   Harvester scripts targeting proprietary third-party CDNs (e.g. `scripts/fetch_egw_corpus.py`)
   are kept on the local machine for personal use but untracked and excluded from
   git (`.gitignore`). The repository ships exclusively local parsers and import tools.
2. **Two-Tier Storage Architecture:**
   - **Tier 1 — Deterministic Core (Repository):** Git-tracked, peer-reviewed,
     content-hashed knowledge base (`materials/bible/`, `correlations/`, `lexicons/`).
     CI-gated by validators F1–F4 and cross-reference integrity checks.
   - **Tier 2 — Local Multi-Corpus Overlay (On-Device SQLite):** Gitignored SQLite
     database (`data/corpus.db` / `data/egw.db`). Hosts multi-corpus paragraphs,
     user annotations, and full-text search indexes.
3. **Extensible Namespaces & Schema Evolution:**
   - Token prefixes identify provenance:
     * `egw:` — Official Ellen G. White publications (e.g. `egw:PP.57.1`, `egw:10MR.15.1`).
     * `pioneer:` — Historical Adventist Pioneer corpus (e.g. `pioneer:DAR.102.3`).
     * `comm:` — Scriptural commentaries (e.g. `comm:SDABC.1.50.2`).
     * `user:` — Personal study notes and private collections (e.g. `user:NOTE.1.1`).
   - Schema unifies into `corpus_paragraphs`:
     `id`, `namespace`, `corpus_id`, `work_code`, `page`, `paragraph_num`,
     `canonical_token`, `heading`, `text`, `content_hash`, `fts_tokens`.
   - Backward compatibility: A SQL view `CREATE VIEW egw_paragraphs AS SELECT * FROM corpus_paragraphs WHERE namespace = 'egw';`
     guarantees zero breakage for existing queries and APIs.
4. **Dynamic Metadata Extraction & Deterministic Slugs:**
   - Arbitrary EPUB/PDF/TXT uploads parse OPF metadata (`dc:title`, `dc:creator`, `dc:identifier`).
   - If uncataloged, a deterministic slug generator generates standard work codes
     (e.g., `Uriah Smith - Daniel and the Revelation.epub` -> `pioneer:DAR`).
5. **CI Isolation Gate:**
   - `search/validation/xrefs.py` rejects unvetted `user:` or unregistered third-party
     tokens in Tier 1 entry frontmatter.
6. **Portable Offline Backup Engine (`scripts/backup.py`, `search/corpus/backup.py`):**
   - Standardizes a deterministic compressed archive (`.tar.gz`) for complete on-device
     study portability.
   - **Three Composable Backup Modes:**
     * **Mode 1: Lightweight / Index-Only (default):** Bundles on-device SQLite databases
       (`databases/egw.db`, `databases/corpus.db`, `databases/macula.db`) and user annotations
       (`user_data/`). Fast (~3-4s) and compact (~34 MB).
     * **Mode 2: Complete Backup (`--complete` / `--include-sources`):**
       $$\text{Complete Backup} = \text{System State (Databases + Annotations)} + \text{Raw BYOD Bookshelf (EPUBs, PDFs, TXTs)}$$
       Bundles both the compiled search indexes and the raw digital book collection (`sources/`),
       guaranteeing 100% offline self-containment when moving to air-gapped machines.
     * **Mode 3: Sources-Only (`--sources-only`):** Bundles only the raw BYOD source files
       without SQLite databases.
   - **Archive Structure:**
     * `backup_manifest.json`: archive format version, backup mode (`complete`, `index_only`,
       `sources_only`), generator, creation timestamp, database statistics, file list,
       byte counts, and SHA-256 checksums of each included file.
     * `databases/`: on-device SQLite databases.
     * `user_data/`: custom annotations, bookmarks, or user manifests.
     * `sources/`: raw BYOD bookshelf files and directories.
   - **Security & Integrity:**
     * Path-traversal / zip-slip prevention on both member names (`arcname`) and destination paths.
     * Rejection of non-regular files (symlinks, FIFO pipes).
     * Cryptographic SHA-256 verification of every extracted file against the manifest.
     * Zero-loss atomic restore with staging within destination directory (`dir=dest`)
       and atomic file replacement (`os.replace`).

## Consequences

* **Legal & Architectural Purity:** Fully adheres to `NOTICE.md` BYOD guidelines with
  zero risk of shipping scraping scripts or copyrighted content.
* **Unified Multi-Corpus Extensibility:** Pioneers, commentaries, and user books share
  a single indexed FTS5 query architecture without schema forks.
* **Total Study Portability:** Users can backup, transport, and restore their entire
  study state and raw digital bookshelf across air-gapped systems in a single deterministic step.
* **Tier 1 Integrity Preserved:** Deterministic Bible core remains clean, vetted,
  and protected from unvetted user data leakage.

Related: ADR-0001 (deterministic core vs AI), ADR-0002 (licensing & BYOD),
ADR-0004 (SQLite FTS5), ADR-0011 (JIT EGW architecture), ADR-0013 (scalability),
ADR-0014 (whole-Bible SQLite).
