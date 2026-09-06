# Adventist Bible Study Tool

An AI-assisted, deterministic knowledge base and interactive terminal workstation for in-depth Bible study and theological research, centered on Seventh-day Adventist beliefs and materials.

> 📖 **New to the tool or preparing a sermon?** Read the [Pastor & Bible Student Guide](docs/PASTOR_GUIDE.md) for a friendly, step-by-step tutorial on navigating the workstation, studying original languages in plain English, and finding Spirit of Prophecy insights.

## Vision & Guiding North Star

A **NotebookLM-like** system built on Adventist theological texts — a structured, searchable library where the AI reads into everything related to your topic through referencing the knowledge base. The core is deterministic and works offline; AI is an optional, on-demand assistant for deeper study.

> *"Everything this tool is is in the search and benefit of understanding the word of God better, and at a deeper level. To be able to truly understand what the Holy Spirit is trying to tell us."* (1 Cor 2:10–13)

## What Makes This Different

1.  **Offline-first** — Core database and interactive workstation work 100% without AI or internet.
2.  **Deterministic core** — Tags, cross-references, original-language concordances, and correlations are rule-based and reliable.
3.  **Cross-language semantic linking** — Hebrew → Greek → English concept mapping backed by empirical Septuagint (LXX) translation equivalences.
4.  **The 5 Biblical Comprehension Tools**:
    *   **Plain-English Verbal Stems & Nuances**: Translates Hebrew stems (Qal, Niphal, Piel, Hiphil, Hitpael) and Greek verb aspects (Aorist, Middle Voice, Perfect Passive) into clear ministerial meaning.
    *   **Pauline Argument Flow & Discourse Markers**: Visualizes the Holy Spirit's inspired logic (`⟨Premise: γάρ⟩`, `⟨Therefore: οὖν⟩`, `⟨Purpose: ἵνα⟩`).
    *   **Scripture Interpreting Scripture (OT Citation Anchors)**: One-key jump (`o`) linking New Testament apostolic quotations to Old Testament Hebrew and Septuagint roots.
    *   **Multi-Translation Parallel View**: Instant, zero-latency comparison of KJV, ASV, BSB, and YLT (press `v`).
    *   **Spirit of Prophecy Integration & Continuous Page Reader**: Direct citation jumps (`g` ➔ `PP 44.1`, `DA 19.1`) and full chapter correlations.
5.  **Unabridged Scholarly Lexicons** — Integrated Brown-Driver-Briggs (BDB) for Hebrew and Abbott-Smith for Greek, with Strong's senses and KJV translation renderings.
6.  **AI transparency** — AI-generated content is explicitly marked `<!-- AI-GENERATED -->` and gated behind human review.
7.  **Git-based collaboration** — Full version control with automated CI verification gates (F1–F4 validators).
8.  **Adventist-focused** — Grounded in the sanctuary message, the Great Controversy theme, the seventh-day Sabbath, conditional immortality, and the Spirit of Prophecy.

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
├── data/                # Local SQLite databases (gitignored) & provenance
│   ├── bible.db                   # Whole-Bible 66 books (31,102 verses) in KJV, ASV, BSB, YLT
│   ├── macula.db                  # Macula Hebrew MT & Greek NT Lowfat syntax trees
│   ├── egw.db                     # Local SQLite FTS5 database for Spirit of Prophecy
│   └── PROVENANCE.md              # Checksums, pins, and reproduction instructions
├── scripts/             # study.py, bootstrap.sh, fetch_sources.sh, verify_all.sh, status.py
├── docs/                # Decisions (ADRs), work packages (WPs), PASTOR_GUIDE.md
│   ├── PASTOR_GUIDE.md            # Friendly tutorial & sermon prep walkthrough for pastors
│   ├── WORKFLOW.md                # Engineering workflow and session practices
│   ├── decisions/                 # Architecture Decision Records (ADR-0001..0021)
│   └── wp/                        # Work package specifications (WP-001..027)
├── search/              # Python search, linking, corpus, UI & agreement layers
│   ├── ui/              # Modern Textual study workstation, themes, and study shell
│   ├── corpus/          # Genesis & NT builders, grammar nuances, discourse flow, citations
│   ├── macula/          # Linguistic enrichment, syntax trees, LXX crosswalk
│   ├── linking/         # Semantic linking pipeline (layers b & c) + JIT EGW engine
│   ├── validation/      # F1-F4 data-integrity validators + lexicon builders
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

### 1. Clone & Bootstrap

```bash
git clone <repo-url>
cd bible-study-tool

# Automated environment setup (creates .venv, installs dependencies):
./scripts/bootstrap.sh
```

### 2. Launch the Interactive Study Workstation

The primary way to study Scripture with this tool is through the modern terminal workstation:

```bash
# Open the interactive visual study workstation (default: Genesis 1)
python scripts/study.py

# Or launch directly into any chapter:
python scripts/study.py "John 1"
python scripts/study.py "John 17"
python scripts/study.py "Romans 1"
```

Use `j` / `k` to move between verses, `1`–`5` to switch study inspector tabs, `v` to toggle parallel translations, `o` to jump between New Testament verses and their Old Testament quotation roots, `g` to jump to any passage or Spirit of Prophecy reference (e.g. `PP 44.1`), `t` to cycle themes, and `?` for interactive help.

### 3. Study via the Command-Line Interface (CLI)

If you prefer studying or searching directly in your terminal shell:

```bash
# Study a passage and print structured linguistic cards:
python scripts/study.py "John 1:1-5"

# Look up an original language word (Strong's Hebrew or Greek):
python scripts/study.py --word H7225
python scripts/study.py --word G3056

# Launch the interactive terminal study shell:
python scripts/study.py --cli
```

### 4. Fetch Pinned Lexical Sources (Optional, for Generators)

Download the pinned raw upstream sources (scrollmapper KJV OSIS, OSHB XML, gmlewis Strong's, STEPBible brief lexicons) for building lexical artifacts:

```bash
bash scripts/fetch_sources.sh
```

### 5. Initialize Spirit of Prophecy (EGW) Local Database

Spirit of Prophecy writings are referenced via canonical pagination tokens (e.g. `egw:PP.57.1`) and stored in a local SQLite database (`data/egw.db`). Initialize the database and load seed passages:

```bash
python scripts/egw_lookup.py --init --seed-genesis
```

### 6. Run Full Local Verification

Run the exact test suite and data-integrity validators that CI executes:

```bash
bash scripts/verify_all.sh
```

## Sourcing External Materials (What We Provide & What You Supply)

A foundational architectural principle of this project is: **"Link out, don't redistribute"** ([NOTICE.md](NOTICE.md), [ADR-0002](docs/decisions/ADR-0002-licensing-and-content-sourcing.md), [ADR-0011](docs/decisions/ADR-0011-whole-book-scaffolding-and-jit-egw.md)). This keeps the Git repository 100% license-clean under MIT and CC BY 4.0 while enabling powerful, offline, full-text research.

### What is bundled in the repository:
* **The Bible Text**: Whole-Bible 66 books (31,102 verses) stored in normalized local SQLite (`data/bible.db`) containing the King James Version (KJV 1769 with Strong's tags), Berean Standard Bible (BSB 2020), American Standard Version (ASV 1901), and Young's Literal Translation (YLT 1898).
* **Curated Corpus Entries**:
  * **Old Testament**: All 1,533 verses of Genesis (`materials/bible/ot/genesis/{01..50}/`). Chapters 1–3 are fully human-curated (`status: review`); chapters 4–50 are generated as draft skeletons (`status: draft`) carrying deterministic WordGraph word-study blocks.
  * **New Testament**: Curated Gospel of John chapters 1 & 17 (77 verses, `status: review`) in `materials/bible/nt/john/{01,17}/` detailing Logos Christology, the incarnation tabernacle (*skēnoō*), the Lamb of God, Trinitarian oneness, and Christ's High Priestly prayer. All 27 New Testament books are supported by the deterministic NT generator (`search/corpus/build_nt.py`).
* **Lexical Artifacts**: Full Strong's Hebrew & Greek lexicons (`lexicons/strongs-*.json`), unabridged Brown-Driver-Briggs (BDB) and Abbott-Smith definitions, STEPBible brief glosses (TBESH / TBESG), whole-book Hebrew morphology (`lexicons/morphology-genesis{1..50}.json`), and the Genesis WordGraph (`lexicons/wordgraph-genesis.json`).
* **Linguistic Datasets (Macula)**: Integrated Clear-Bible Macula Hebrew (WLC) and Greek (Nestle 1904) Lowfat syntax trees, clause roles, and Louw-Nida semantic domains (`data/macula.db`).
* **Source Agreement Layer**: The apparatus alignment (`correlations/apparatus-genesis{1..50}.json`) and agreement ledger (`correlations/agreement-ledger.json`).

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
     python scripts/egw_lookup.py --seed-genesis   # Seeds foundational Genesis 1-3 passages
     ```
  4. If you have exported EGW study text in JSON format (array of objects with `{"book_code": "PP", "page": 57, "paragraph": 1, "text": "...", "book_title": "Patriarchs and Prophets"}`), import it locally:
     ```bash
     python scripts/egw_lookup.py --import-json /path/to/passages.json
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
3. **The Clean Reference Architecture**: By standardizing on canonical citation tokens (`egw:BOOK.PAGE.PARA`) and providing local import tooling (`--import-json`) for user-supplied data, the project remains an objective study engine and indexer, strictly honoring copyright while delivering instant, offline research capabilities.

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

## Lexical / Keyword Search

All search — free-text, metadata, and cross-references — runs through the
`search/linking/` pipeline backed by a single SQLite index (`index/semantic.db`).
No API calls; fully offline.

> **Honesty note:** The free-text search is lexical/keyword (SQLite FTS5 BM25),
> not neural-semantic. It matches literal terms and n-grams; it does not
> understand synonyms, concepts, paraphrase, or cross-language meaning. True
> semantic matching (embeddings) is the planned upgrade, provided by the
> pluggable embedder in the linking layer (c). The older standalone
> `search/semantic_search.py` (TF-IDF) has been **removed** — its deterministic
> lookups and cross-reference support are now native to the linking pipeline,
> which is a single, more capable engine.

### Semantic linking pipeline (layers b & c)

A dedicated package (`search/linking/`) implements the semantic correlating
feature in two cooperating layers, matching the deterministic/AI boundary in
[DETERMINISTIC_VS_AI.md](correlations/DETERMINISTIC_VS_AI.md). See
[SEMANTIC_LINKING_GUIDE.md](correlations/SEMANTIC_LINKING_GUIDE.md) for full
detail.

* **Layer (b) — deterministic concordance**: groups entries that share an
  original-language lexeme (Strong's number) into cross-passage /
  cross-language root links. Always authoritative. Writes `index/concordance.json`.
* **Layer (c) — multilingual discovery (AI)**: proposes cross-language links
  *beyond* a shared Strong's number (different lexemes, different scripts,
  same conceptual field) using a pluggable multilingual embedder. Gated by
  strict rules and written only to `correlations/ai-discovered-links.json`
  for human review — it never touches the deterministic core.

Both layers query a shared **SQLite index** (`index/semantic.db`) so they read
only the generated index instead of rescanning the Markdown tree. Markdown in
`materials/` stays the single source of truth; the `.db` is a rebuilt artifact.

```bash
# Build the SQLite index (once, from authoritative Markdown)
python -m search.linking.dbindex build --repo .

# Query the index (FTS5 free-text + metadata, no rescan of materials/)
python -m search.linking.dbindex query --db index/semantic.db --count
python -m search.linking.dbindex query --db index/semantic.db --strongs H7225
python -m search.linking.dbindex query --db index/semantic.db --tag theme/creation
python -m search.linking.dbindex query --db index/semantic.db --free-text "creation light"
python -m search.linking.dbindex query --db index/semantic.db --xref gen-1-1-kjv

# Layer (b): deterministic concordance (queries the index)
python -m search.linking.cli --repo . --deterministic

# Layer (c): multilingual candidate discovery (pending human review)
python -m search.linking.cli --repo . --discover --top-k 5

# Both layers, rebuilding the index and seeding accepted candidates
python -m search.linking.cli --repo . --all --rebuild-db --seed

# Run tests
python -m search.linking.test_pipeline
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

Macula Hebrew and Greek linguistic annotations are integrated directly into `data/macula.db` (ADR-0012, ADR-0014, ADR-0015, ADR-0020). This provides sub-millisecond offline access to syntax clause trees, participant semantic roles (Agent, Action, Patient, Context), empirical Septuagint (LXX) translation equivalences, and Louw-Nida semantic domains across both Testaments.

## Key Design & Study Documents

*   [Pastor & Bible Student Guide](docs/PASTOR_GUIDE.md) — Non-technical tutorial, sermon prep walkthroughs, and keyboard cheat sheet
*   [Architecture Decision Records (ADRs)](docs/decisions/INDEX.md) — 21 formal architectural decisions documenting all design milestones
*   [Work Packages (WPs)](docs/wp/INDEX.md) — Completed and open engineering packages (WP-001 through WP-027)
*   [Workflow Guide](docs/WORKFLOW.md) — Explicit guide to the project's working method and verification cycle
*   [Tag Taxonomy](tags/taxonomy.json) — Complete tag vocabulary and relationship types (66 books, themes, xrefs)
*   [Knowledge Base Schema](kc-schema.md) — Entry format, YAML frontmatter, and metadata validation rules
*   [Contribution Standards](CONTRIBUTION_STANDARDS.md) — Submission rules and review workflow
*   [Deterministic vs AI Boundary](correlations/DETERMINISTIC_VS_AI.md) — Core vs AI layer distinction
*   [AI Prompt Templates](ai-prompts/) — Templates for AI-assisted study tasks
*   [Roadmap](ROADMAP.md) — Goal inventory, progress tracking, and sequenced plan

## Technology Stack

*   **Interactive Workstation**: [Textual](https://textual.textualize.io/) (modern terminal application framework), Rich typography, persistent viewport engine, and 7 built-in themes (`search/ui/`)
*   **Core Knowledge Base**: Markdown files with standard YAML frontmatter (human-readable, Git-friendly)
*   **Local Databases**: SQLite FTS5 (BM25) on-device engines (`data/bible.db`, `data/macula.db`, `data/egw.db`, `index/semantic.db`)
*   **Linguistic & Lexical Data**: Clear-Bible Macula Hebrew MT & Greek NT (Nestle 1904), Open Scriptures Hebrew Bible (OSHB), Strong's Exhaustive Concordance, STEPBible TBESH/TBESG glosses, Brown-Driver-Briggs (BDB), Abbott-Smith Greek Lexicon
*   **Translations**: Pinned KJV (1769), BSB (2020), ASV (1901), and YLT (1898)
*   **Verification & CI**: Python `pytest`, 4 automated data-integrity gates (F1 Schema, F2 Strong's, F3 Cross-refs, F4 Audit), and GitLab CI / GitHub Actions
    

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

`bash scripts/verify_all.sh` runs the test suite, the F1-F4 data-integrity validators, and the source
checksums — the exact checks CI runs — and prints a remedy for each failure.
Hand-authored content (`materials/`) is validated by the F1-F4 validators;
generated artifacts (`lexicons/`, the agreement ledger, generated corpus
entries) are never hand-edited — regenerate them with the commands printed in
their failure messages (see Contribution Standards for the full workflow).
