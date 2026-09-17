# Adventist Bible Study Tool

A deterministic, offline-first theological research environment and interactive study workstation (Web GUI & Terminal TUI) for in-depth Bible study, centered on Seventh-day Adventist beliefs and materials.

> 📖 **Getting Started?**
> - **Non-technical users**: Download the zero-Python standalone application for Windows, macOS, or Linux in the [Installation Guide](docs/INSTALL.md).
> - **Screenshots & Gallery**: Take a look at the workstation in everyday use in the [Visual Tour](docs/VISUAL_TOUR.md).
> - **Study Walkthroughs**: Read the [User & Study Guide](docs/USER_GUIDE.md) for step-by-step tutorials on studying original languages in plain English, navigating the sanctuary blueprint, and tracing prophetic keys.

## Vision & Guiding North Star

A **NotebookLM-like** research desk built on Adventist theological texts — a structured, searchable library where every fact is pinned, verified, and reproducible. The core is deterministic and works 100% offline without cloud or AI dependencies; AI is an optional, on-demand assistant for research synthesis gated behind human review.

> *"Everything this tool is is in the search and benefit of understanding the word of God better, and at a deeper level. To be able to truly understand what the Holy Spirit is trying to tell us."* (1 Cor 2:10–13)

## What Makes This Different

1.  **GUI-First & Zero-Python Standalone App (ADR-024, WP-029)** — Launches directly into a dedicated Study Room Desk web workstation (`http://localhost:8000`) with zero installation hurdles. A full-featured terminal TUI (`bible-study --tui`) is built-in for power users.
2.  **100% Offline & Private** — All Scripture databases, lexicons, syntax trees, and commentary indexes run locally on-device. Zero telemetry, zero analytics, zero external network traffic during study.
3.  **Deterministic Core & Two-Layer Integrity (ADR-027)** — Content-level canonical SHA-256 verification (`data/INTEGRITY.json`) ensures SQLite databases (`bible.db`, `macula.db`) are cryptographically verified across all platforms and toolchains.
4.  **The 8 Biblical Comprehension & Research Tools**:
    *   **Plain-English Verbal Stems & Nuances**: Automatically translates Hebrew verbal stems (Qal, Niphal, Piel, Hiphil, Hitpael) and Greek aspects/voices (Aorist, Middle Voice, Perfect Passive) into clear theological meaning.
    *   **Pauline Argument Flow & Discourse Markers**: Visualizes apostolic logical argumentation (`⟨Premise: γάρ⟩`, `⟨Therefore: οὖν⟩`, `⟨Purpose: ἵνα⟩`, `⟨Contrast: ἀλλά⟩`).
    *   **Scripture Interpreting Scripture (OT Citation Anchors)**: One-key jump (`o`) linking New Testament apostolic citations directly to Old Testament Hebrew and Septuagint source passages.
    *   **Multi-Translation Parallel View**: Instant side-by-side or stacked comparison of KJV (1769 with Strong's tags), ASV (1901), BSB (2020), and YLT (1898).
    *   **Treasury of Scripture Knowledge (TSK) Cross-References**: Over 344,000 vote-ranked, reciprocal scripture-interpreting-scripture cross-reference pairs across all 31,102 verses in `data/bible.db`.
    *   **Interactive Sanctuary Typology Blueprint & Chronological Plan of Salvation**: Interactive vector floorplan (Courtyard, Holy Place, Most Holy Place) with a chronological timeline slider (AD 31 Cross → Heavenly Inauguration → 1844 Judgment → New Earth) and in-text station breadcrumbs.
    *   **Master Prophetic Key Table & Apocalyptic Symbol Chaining**: Historicist apocalyptic symbol decoder (Daniel 7–12, Revelation) linking symbols directly to defining Old Testament keys and historical consensus citations.
    *   **Spirit of Prophecy Progressive Chapter Reader**: In-browser reading drawer with physical printed pagination fidelity breaks, sequential chapter traversal (`‹ Prev / Next ›`), and direct citation navigation (`PP 44.1`, `DA 19.1`).
5.  **Unabridged Scholarly Lexicons** — Integrated Brown-Driver-Briggs (BDB) for Hebrew and Abbott-Smith for Greek, with Strong's senses, STEPBible brief glosses (TBESH / TBESG), and King James translation renderings.
6.  **Cross-Language Semantic Linking** — Hebrew → Greek → English concept mapping backed by empirical Septuagint (LXX) translation equivalences.
7.  **AI Transparency** — AI-generated content is provisional, explicitly marked `<!-- AI-GENERATED -->`, and strictly gated behind human review before entering the knowledge base.
8.  **Adventist Theological Grounding** — Rooted in the sanctuary doctrine, the Great Controversy thematic framework, the seventh-day Sabbath, conditional immortality, and the Spirit of Prophecy.

## Project Structure

```
bible-study-tool/
├── materials/           # Curated markdown entries & draft skeletons
│   └── bible/
│       ├── ot/          # Old Testament
│       │   └── genesis/ # Whole-book Genesis (chapters 01–50, 1,533 verses)
│       └── nt/          # New Testament
│           └── john/    # Curated John 1 (51 verses) & John 17 (26 verses)
├── tags/                # Tag taxonomy (66 Bible books, themes, cross-reference types)
├── index/               # Generated indexes (tag → entry, passage → entry)
├── correlations/        # Cross-references, apparatus, and semantic links
│   ├── agreement-ledger.json      # Cross-source agreement ledger (generated)
│   ├── apparatus-genesis*.json    # Word-level alignment apparatus (chapters 1–50)
│   ├── semantic-links.json        # Curated cross-language relationships
│   ├── semantic-links-index.json  # Quick lookup index
│   ├── ai-discovered-links.json   # AI-suggested links awaiting review
│   ├── DETERMINISTIC_VS_AI.md     # Core vs AI layer boundary
│   ├── MACULA_INTEGRATION.md      # Macula dataset integration overview
│   └── SEMANTIC_LINKING_GUIDE.md  # Code-level implementation guide
├── lexicons/            # Generated lexical artifacts (Strong's, STEPBible, WordGraph)
│   ├── strongs-list.json          # Canonical enumeration (8,674 H + 5,624 G)
│   ├── strongs-lexicon.json       # Definitions, transliterations, KJV usage
│   ├── tbesh-glosses.json         # STEPBible brief Hebrew glosses
│   ├── tbesg-glosses.json         # STEPBible brief Greek glosses
│   ├── morphology-genesis*.json   # OSHB morphology layers (chapters 1–50)
│   └── wordgraph-genesis.json     # WordGraph lexical knowledge graph (1,783 lexemes)
├── data/                # Local SQLite databases (gitignored) & integrity manifests
│   ├── bible.db                   # Whole-Bible 66 books (31,102 verses) + ~345k TSK cross-references
│   ├── macula.db                  # Macula Hebrew MT & Greek NT Lowfat syntax trees & crosswalks
│   ├── egw.db                     # Local SQLite FTS5 database for Spirit of Prophecy
│   ├── INTEGRITY.json             # Canonical SQLite content-level SHA-256 hashes (ADR-027)
│   └── PROVENANCE.md              # Upstream git pins, checksums, and reproduction instructions
├── web/                 # Local Web Workstation (HTML5 / Vanilla JS / CSS3 Study Room Desk)
├── scripts/             # study.py, bootstrap.sh, fetch_sources.sh, verify_all.sh, status.py
├── docs/                # Decisions (ADRs), work packages (WPs), visual tour & guides
│   ├── INSTALL.md                 # 3-step zero-Python standalone setup for Win/Mac/Linux
│   ├── VISUAL_TOUR.md             # Workstation screenshots (Focus mode, syntax, sanctuary)
│   ├── USER_GUIDE.md              # In-depth tutorial & study walkthroughs
│   ├── WORKFLOW.md                # Engineering workflow, subagent review, and verification
│   ├── decisions/                 # Architecture Decision Records (ADR-001..027)
│   └── wp/                        # Work package specifications (WP-001..037)
├── search/              # Core search, linguistic engine, corpus, UI & agreement layers
│   ├── ui/              # Web GUI HTTP server, Textual TUI workstation, themes & shell
│   ├── corpus/          # Faceted query engine (query.py), grammar nuances, discourse, citations
│   ├── macula/          # Linguistic enrichment, syntax trees, LXX crosswalk
│   ├── linking/         # Semantic linking pipeline (layers b & c) + JIT EGW engine
│   ├── validation/      # F1-F4 schema & integrity validators, F6 SQLite content gate
│   └── agreement/       # Source Agreement Layer (facts, comparison, ledger, apparatus)
├── .gitlab/             # Merge request template & CI configuration
├── CONTRIBUTION_STANDARDS.md
├── kc-schema.md
├── LICENSE              # Code license (MIT)
├── LICENSE.content      # Content license (CC BY 4.0)
├── NOTICE.md            # Purpose, doctrinal basis, content-sourcing policy
├── ROADMAP.md           # Goal inventory + sequenced plan
└── README.md
```

## Quick Start

### For Non-Technical Users (Standalone App — Zero Python Required)

For personal devotions, sermon preparation, and group Bible study, a standalone, zero-Python distribution is available:

1. **Download**: Grab the standalone release package (`bible-study-linux-x86_64.tar.gz`) from the [Releases Page](https://gitlab.com/adventist-bible-study/bible-study-tool/-/releases). *(Note: Windows and macOS standalone packages are currently in active packaging; Windows and macOS users can run immediately in 2 minutes via the standard setup below.)*
2. **Launch**: Run `./bible-study` (or double-click the binary).
3. **Study**: Your default web browser immediately opens to your local study desk at `http://localhost:8000`.

The built-in First-Run Setup Wizard automatically verifies cryptographic database integrity, configures offline privacy settings, and greets you with the text of Scripture. For detailed platform instructions, see the [Installation Guide](docs/INSTALL.md).

---

### For Developers & Power Users (Source & Terminal Setup)

If you are developing features, curating the corpus, or studying directly in the terminal:

#### 1. Clone & Bootstrap

```bash
git clone https://gitlab.com/adventist-bible-study/bible-study-tool.git
cd bible-study-tool

# One-command automated setup (creates .venv, installs dependencies, hydrates SQLite databases, and verifies):
./bootstrap.sh --data --verify
```

#### 2. Launch the Workstation

```bash
# Launch the primary Web Workstation (starts local server & opens http://localhost:8000):
python -m search.ui.web
# (or with the installed CLI binary: bible-study)

# Or launch the interactive Terminal User Interface (TUI companion):
python scripts/study.py tui
python scripts/study.py tui "John 1"
python scripts/study.py tui "Romans 1"
```

In the TUI, use `j` / `k` to move between verses, `h` / `l` for chapters, `1`–`5` for inspector tabs, `v` to toggle parallel translations, `o` for Old Testament quotation roots, `g` for passage or EGW token jumps (`PP 44.1`), `t` to cycle color themes, and `?` for interactive help.

#### 3. Faceted Search & CLI Research

```bash
# Unified cross-source faceted search (curated entries + Bible verses + Spirit of Prophecy):
python scripts/study.py search "grace" --book genesis --theme theme/grace
python scripts/study.py search "sanctuary" --in bible --limit 10

# Passagewise linguistic inspection cards:
python scripts/study.py study "John 1:1-5"

# Original-language lexicon lookups:
python scripts/study.py word H7225
python scripts/study.py word G3056

# Interactive study shell:
python scripts/study.py shell
```

#### 4. Run Full Local Verification

Run the exact test suite, schema validators, and SQLite content integrity gates that CI executes:

```bash
bash scripts/verify_all.sh
```

## Sourcing External Materials (What We Provide & What You Supply)

A foundational architectural principle of this project is: **"Link out, don't redistribute"** ([NOTICE.md](NOTICE.md), [ADR-002](docs/decisions/ADR-002-licensing-and-content-sourcing.md), [ADR-011](docs/decisions/ADR-011-whole-book-scaffolding-and-jit-egw.md)). This keeps the Git repository 100% license-clean under MIT and CC BY 4.0 while enabling powerful, offline, full-text research.

### What is bundled in the repository:
* **The Bible Text & TSK Cross-References**: Whole-Bible 66 books (31,102 verses) stored in normalized local SQLite (`data/bible.db`) containing KJV (1769 with Strong's tags), BSB (2020), ASV (1901), YLT (1898), and over 344,000 vote-ranked Treasury of Scripture Knowledge (TSK) cross-reference pairs.
* **Curated Corpus Entries**:
  * **Old Testament**: All 1,533 verses of Genesis (`materials/bible/ot/genesis/{01..50}/`). Chapters 1–3 are fully human-curated (`status: review`); chapters 4–50 are generated as draft skeletons (`status: draft`) carrying deterministic WordGraph word-study blocks.
  * **New Testament**: Curated Gospel of John chapters 1 & 17 (77 verses, `status: review`) in `materials/bible/nt/john/{01,17}/` detailing Logos Christology, the incarnation tabernacle (*skēnoō*), the Lamb of God, Trinitarian oneness, and Christ's High Priestly prayer. All 27 New Testament books are supported by the deterministic NT generator (`search/corpus/build_nt.py`).
* **Theological Schemas & Prophetic Keys**: Pinned historicist prophetic symbol database (`data/prophetic_lexicon.json`) and sanctuary typology blueprint (`data/sanctuary_schema.json`).
* **Lexical Artifacts**: Full Strong's Hebrew & Greek lexicons (`lexicons/strongs-*.json`), unabridged Brown-Driver-Briggs (BDB) and Abbott-Smith definitions, STEPBible brief glosses (TBESH / TBESG), whole-book Hebrew morphology (`lexicons/morphology-genesis{1..50}.json`), and the Genesis WordGraph (`lexicons/wordgraph-genesis.json`).
* **Linguistic Datasets (Macula)**: Integrated Clear-Bible Macula Hebrew (WLC) and Greek (Nestle 1904) Lowfat syntax trees, clause roles, and Louw-Nida semantic domains (`data/macula.db`).
* **Integrity Manifest & Source Agreement**: Canonical SQLite content hashes in `data/INTEGRITY.json` (ADR-027), apparatus alignment (`correlations/apparatus-genesis{1..50}.json`), and agreement ledger (`correlations/agreement-ledger.json`).

### What is NOT bundled (and how to supply it):

#### 1. Ellen G. White / Spirit of Prophecy Texts
* **Why not bundled**: Ellen G. White writings and General Conference-published works are protected under active copyright held by the Ellen G. White Estate. Reproducing entire books in a public Git repository is prohibited without express license.
* **Official Resources & Links**:
  - Official online research database: [egwwritings.org](https://m.egwwritings.org/) (Ellen G. White Estate).
  - Public-domain historical editions (works published prior to 1929, such as original 1888/1911 *The Great Controversy*, 1890 *Patriarchs and Prophets*, 1898 *The Desire of Ages*): available at the [Adventist Digital Library](https://adventistdigitallibrary.org/) and the [Internet Archive](https://archive.org/).
* **How to install on your machine**:
  1. Entries in the repository store **only canonical citation tokens** (`egw:BOOK.PAGE.PARA`, e.g., `egw:PP.57.1`).
  2. Full paragraph texts reside in your local SQLite database at `data/egw.db` (gitignored).
  3. Initialize your local database:
     ```bash
     python scripts/egw_lookup.py --init
     python scripts/egw_lookup.py --seed-core   # Seeds core reference passages
     ```
  4. Look up a passage (citation is a positional argument, not a flag):
     ```bash
     python scripts/egw_lookup.py PP.57.1
     python scripts/study.py egw "PP.57.1"
     ```
  5. If you have exported EGW study text in JSON format (array of objects with `{"book_code": "PP", "page": 57, "paragraph": 1, "text": "...", "book_title": "Patriarchs and Prophets"}`), import it locally:
     ```bash
     python scripts/egw_lookup.py --ingest-json /path/to/passages.json
     ```

#### 2. Modern Bible Translations & Commentaries
* **Why not bundled**: Modern copyrighted translations (e.g. NIV, ESV, NASB, NKJV) and proprietary commentaries (e.g. the Seventh-day Adventist Bible Commentary — SDABC) belong to their respective publishers (Crossway, Zondervan, Lockman Foundation, Review and Herald / Pacific Press).
* **How to use**: This project employs a **user-supplied-text / on-device model**. Users load personal translation files onto their local machine. All search, correlation, and comparison computations run strictly on-device without broadcasting or redistributing the text.

#### 3. Raw Upstream Lexical Datasets
* **Why not bundled**: Raw multi-megabyte XML and JSON files from third parties are gitignored in `data/` to keep the repository lightweight and decoupled from upstream repository structures.
* **How to fetch**: Run `bash scripts/fetch_sources.sh`. The script fetches the exact commit pins recorded in `data/PROVENANCE.md` (OSHB from `openscriptures/morphhb`, KJV-osis from `scrollmapper/bible_databases`, Strong's from `gmlewis/bible-codes`, and TBESH/TBESG from Tyndale House / STEPBible).

### Legal Notice Regarding Automated Scraping Scripts

**Question: Why does this project not provide an automated script to download the entire egwwritings.org database or scrape modern translation websites?**

**Answer: Because doing so would violate our license aims, website Terms of Service, and copyright laws.**
1. **Terms of Service Compliance**: Online repositories such as `egwwritings.org` and commercial Bible portals explicitly restrict automated web scraping, bulk crawling, and unauthorized data harvesting in their Terms of Service. Shipping an automated scraper script in an open-source tool would encourage bulk extraction in violation of those terms.
2. **License Purity**: The Adventist Bible Study Tool core is licensed under MIT and CC BY 4.0. Providing scripts that bypass access controls or ingest copyrighted content into derivative databases would compromise the legal purity and longevity of the project.
3. **The Clean Reference Architecture**: By standardizing on canonical citation tokens (`egw:BOOK.PAGE.PARA`) and providing local import tooling (`--ingest-json`) for user-supplied data, the project remains an objective study engine and indexer, strictly honoring copyright while delivering instant, offline research capabilities.

---

## Corpus Scope: Old & New Testaments

The knowledge base combines broad whole-Bible textual integration with deeply curated theological entries:

* **Curated Theological Chapters (`status: review`)**:
  * **Genesis 1–3 (80 verses)**: Creation ex nihilo, the seventh-day Sabbath holy crown, Edenic covenant, the Fall, Protevangelium (Gen 3:15), substitutionary atonement, and sanctuary gates.
  * **John 1 (51 verses)**: Pre-existent deity of the Word (`En archē ēn ho Logos`), creation agency, incarnation tabernacle (`skēnoō`, echoing Ex 34:6), and the Lamb of God.
  * **John 17 (26 verses)**: Christ's High Priestly prayer, Day of Atonement sanctuary typology, covenant Trinitarian oneness (`hina ōsin hen`), and sanctification in the truth.
* **Old Testament Genesis Draft Skeletons (Chapters 4–50, 1,453 verses, `status: draft`)**:
  * Assembled by the deterministic draft engine (`search/corpus/draft_engine.py`) consuming the WordGraph (`lexicons/wordgraph-genesis.json`). Each entry contains verified KJV text, Strong's tags, and complete Hebrew word studies, organized per-chapter (`materials/bible/ot/genesis/{01..50}/`).
* **New Testament Infrastructure (All 27 Books)**:
  * Deterministic generator (`search/corpus/build_nt.py`) capable of generating draft skeletons across all 27 New Testament books with Greek Strong's crosswalks and word-study blocks into `materials/bible/nt/{book}/{ch:02d}/`.
* **Whole-Bible Scripture Database (`data/bible.db`)**:
  * All 66 books (31,102 verses) fully indexed in KJV, ASV, BSB, and YLT with sub-millisecond retrieval.

## Search & Semantic Discovery

### 1. Unified Faceted Search Engine (C4 Query API)

Search across the entire knowledge base is powered by a high-performance, sidecar-free query engine (`search/corpus/query.py`) that unifies **all three content stores**:

1. **Curated Study Entries** (`materials/bible/**/*.md`): 1,610+ deeply analyzed verses indexed in-memory with FTS5 and frontmatter facet tables.
2. **Whole-Bible Scripture** (`data/bible.db`): 31,102 verses across 66 books in 4 translations (KJV, ASV, BSB, YLT) via `BibleDB.search`.
3. **Spirit of Prophecy Commentary** (`data/egw.db`): Ellen G. White paragraph corpus via `EgwDB.search`.

#### Features:
* **Faceted Filtering**: Filter by any structured metadata (`--book`, `--theme`, `--translation`, `--language`, `--status`). Facets combine by intersection (AND); values within a facet combine by union (OR).
* **Cross-Source BM25 Ranking**: Converts disparate SQLite BM25 scales into positive relevance, normalizes scores per source to `[0, 1]`, and globally sorts merged results so the most relevant passages rise to the top.
* **Sidecar-Free Hygiene (ADR-027)**: Uses immutable read connections (`mode=ro&immutable=1`), ensuring zero lock contention and preventing rogue `-wal`/`-shm` sidecar creation.

```bash
# Multi-facet search across the curated corpus and Bible:
python scripts/study.py search "grace" --book genesis --theme theme/grace

# Search verses matching a theme or term in a specific book:
python scripts/study.py search "covenant" --book genesis --limit 10

# Filter curated entries by review status:
python scripts/study.py search --status review --limit 20

# Output results as structured JSON:
python scripts/study.py search "tabernacle" --json
```

### 2. Semantic Linking Pipeline (Layers b & c)

A dedicated engine (`search/linking/`) links passages and concepts across Scripture and languages, maintaining the strict boundary defined in [DETERMINISTIC_VS_AI.md](correlations/DETERMINISTIC_VS_AI.md):

* **Layer (b) — Deterministic Concordance**: Groups entries sharing an original-language lexeme (Strong's number) into cross-passage and cross-language root links. Always authoritative. Generates `index/concordance.json`.
* **Layer (c) — Multilingual Discovery (AI)**: Proposes conceptual links *beyond* shared Strong's numbers (different lexemes, different scripts, same semantic field) using a pluggable embedder (`intfloat/multilingual-e5-small` or offline n-gram fallback). Gated by strict rules and written only to `correlations/ai-discovered-links.json` for human review — AI never touches the deterministic core.

```bash
# Run deterministic concordance linking:
python -m search.linking.cli --repo . --deterministic

# Run multilingual candidate discovery (proposals for human review):
python -m search.linking.cli --repo . --discover --top-k 5

# Rebuild indexes and seed accepted candidates:
python -m search.linking.cli --repo . --all --rebuild-db --seed
```

The embedder is pluggable: it uses `intfloat/multilingual-e5-small` when
`sentence-transformers` is installed and otherwise falls back to a
deterministic, offline, cross-script character n-gram embedder (numpy only).

### Environment Setup & Dependencies

The easiest way to configure your development environment is with the automated bootstrap script:

```bash
./scripts/bootstrap.sh              # Standard environment with test dependencies
./scripts/bootstrap.sh --ml         # Include optional ML dependencies (sentence-transformers)
```

Alternatively, to set up manually:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

The linking pipeline (`search/linking/`) requires only `numpy` and `PyYAML` for its deterministic mode; `sqlite3` is part of Python's standard library. For higher-fidelity multilingual embeddings, optionally install `sentence-transformers` (via `--ml`).

**Running from a checkout.** The tool loads its data (the Markdown corpus in `materials/`, the tag taxonomy, `lexicons/`, `correlations/`, and generated `index/`) from **relative paths at the repo root**. Always run commands from the repo root:

```bash
python -m search.linking.cli --repo . --deterministic   # or any validator/dbindex
```

Packaging metadata lives in `pyproject.toml`.

## Macula Linguistic Dataset Integration

Macula Hebrew and Greek linguistic annotations are integrated directly into `data/macula.db` (ADR-012, ADR-014, ADR-015, ADR-020). This provides sub-millisecond offline access to syntax clause trees, participant semantic roles (Agent, Action, Patient, Context), empirical Septuagint (LXX) translation equivalences, and Louw-Nida semantic domains across both Testaments.

## Key Design & Study Documents

*   [Installation Guide](docs/INSTALL.md) — 3-step zero-Python standalone setup for Windows, macOS, and Linux
*   [Visual Tour](docs/VISUAL_TOUR.md) — High-resolution screenshots of the workstation in everyday use
*   [User & Study Guide](docs/USER_GUIDE.md) — Tutorial, practical study walkthroughs, and keyboard cheat sheet
*   [How to Study the Bible Deeply](docs/HOW_TO_STUDY_THE_BIBLE.md) — Inductive study methods, word studies, and sanctuary blueprint
*   [Architecture Decision Records (ADRs)](docs/decisions/INDEX.md) — 27 formal architectural decisions documenting all design milestones (ADR-001..027)
*   [Work Packages (WPs)](docs/wp/INDEX.md) — Completed and open engineering packages (WP-001 through WP-037)
*   [Workflow Guide](docs/WORKFLOW.md) — Explicit guide to the project's working method, subagent review, and verification cycle
*   [Tag Taxonomy](tags/taxonomy.json) — Complete tag vocabulary and relationship types (66 books, themes, xrefs)
*   [Knowledge Base Schema](kc-schema.md) — Entry format, YAML frontmatter, and metadata validation rules
*   [Contribution Standards](CONTRIBUTION_STANDARDS.md) — Submission rules and review workflow
*   [Deterministic vs AI Boundary](correlations/DETERMINISTIC_VS_AI.md) — Core vs AI layer distinction
*   [AI Prompt Templates](ai-prompts/) — Templates for AI-assisted study tasks
*   [Roadmap](ROADMAP.md) — Goal inventory, progress tracking, and sequenced plan

## Technology Stack

*   **Primary Web Workstation**: Responsive HTML5, Vanilla JavaScript, and CSS3 single-page app (`web/`) with draggable 65/35 split-pane, Study Room visual ergonomics (ADR-024, ADR-025, WP-030), and zero external web dependencies.
*   **Companion Terminal Workstation**: [Textual](https://textual.textualize.io/) TUI, Rich typography, persistent sub-millisecond viewport engine, and 7 built-in themes (`search/ui/app.py`).
*   **Core Knowledge Base**: Markdown files with standard YAML frontmatter (human-readable, Git-friendly).
*   **Local Databases**: SQLite FTS5 (BM25) sidecar-free on-device engines (`data/bible.db`, `data/macula.db`, `data/egw.db`).
*   **Linguistic & Lexical Data**: Clear-Bible Macula Hebrew MT & Greek NT (Nestle 1904), Open Scriptures Hebrew Bible (OSHB), Strong's Exhaustive Concordance, STEPBible TBESH/TBESG glosses, Brown-Driver-Briggs (BDB), Abbott-Smith Greek Lexicon.
*   **Translations & Cross-References**: Pinned KJV (1769), BSB (2020), ASV (1901), YLT (1898), and ~345k Treasury of Scripture Knowledge (TSK) cross-reference pairs.
*   **Data Integrity & Verification**: Python `pytest`, 5 automated data-integrity gates (F1 Schema, F2 Strong's, F3 Cross-refs, F4 Audit, F6 SQLite Content Integrity via `data/INTEGRITY.json`), and CI automation.
*   **Packaging & Distribution**: Zero-Python standalone binary builds via PyInstaller (`scripts/build_release.sh`).
    

## License

This repository is dual-licensed by component:

*   **Code** (the `search/` pipeline and tooling): [MIT](LICENSE)
*   **Original content** (concordance data, semantic links, cross-references,
    taxonomies, word studies): [CC BY 4.0](LICENSE.content)

See [NOTICE.md](NOTICE.md) for the project's doctrinal basis and its
content-sourcing policy, including why Ellen G. White and copyrighted
translation texts are linked to rather than bundled.

## Contributing

See [Contribution Standards](CONTRIBUTION_STANDARDS.md) for guidelines and
[docs/WORKFLOW.md](docs/WORKFLOW.md) for the explicit working method (session
start, step-by-step execution with subagent review, ADRs, work packages).
`AGENTS.md` is the thin charter every session loads.

For work package curation, use the deterministic tooling:
```bash
# 1. Extract concise curation context
python scripts/curate_context.py --wp WP-003

# 2. Pre-flight check scoped entries
python scripts/wp_check.py --wp WP-003

# 3. Run full local verification
bash scripts/verify_all.sh
```

`bash scripts/verify_all.sh` runs the test suite, the F1–F4 data-integrity validators, the F6 SQLite content integrity gate, and the raw source
checksums — the exact checks CI runs — and prints a remedy for each failure.
Hand-authored content (`materials/`) is validated by the F1–F4 validators;
generated artifacts (`lexicons/`, the agreement ledger, generated corpus
entries, `data/INTEGRITY.json`) are never hand-edited — regenerate them with the commands printed in
their failure messages (see Contribution Standards for the full workflow).
