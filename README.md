# Adventist Bible Study Tool

An AI-assisted, deterministic knowledge base for in-depth Bible study and theological research, centered on Seventh-day Adventist beliefs and materials.

## Vision

A **NotebookLM-like** system built on Adventist theological texts — a structured, searchable library where the AI reads into everything related to your topic through referencing the knowledge base. The core is deterministic and works offline; AI is an optional, on-demand assistant for deeper study.

## What Makes This Different

1.  **Offline-first** — Core database works without AI or internet
    
2.  **Deterministic core** — Tags, cross-references, and correlations are rule-based and reliable
    
3.  **Cross-language semantic linking** — Hebrew → Greek → English concept mapping is the killer feature
    
4.  **AI transparency** — AI-generated content is explicitly marked and requires human review
    
5.  **Git-based collaboration** — Full version control with review workflow
    
6.  **Adventist-focused** — Built around Adventist theology and the Spirit of Prophecy
    

## Project Structure

```
bible-study-tool/
├── materials/           # Source documents
│   └── bible/           # Bible texts and commentaries (present: ot/ only)
│       └── ot/          # Old Testament
│           └── genesis/ # Whole-book Genesis corpus (all 1,533 verses, chapters 1–50; 1–3 curated, 4–50 draft skeletons)
│   # Planned: spirit-of-prophecy/, commentaries/, translations/, nt/
├── tags/                # Tag taxonomy and indexes
├── index/               # Generated indexes (tag → entry, passage → entry)
├── correlations/        # Cross-references, apparatus, and semantic links
│   ├── agreement-ledger.json      # Cross-source agreement ledger (generated)
│   ├── apparatus-genesis*.json    # Word-level alignment apparatus (chapters 1–50)
│   ├── semantic-links.json        # Curated cross-language relationships
│   ├── semantic-links-index.json  # Quick lookup index
│   ├── ai-discovered-links.json   # AI-suggested links awaiting review
│   ├── DETERMINISTIC_VS_AI.md     # Core vs AI layer boundary
│   ├── MACULA_INTEGRATION.md      # Macula dataset integration plan
│   └── SEMANTIC_LINKING_GUIDE.md  # Code-level implementation guide
├── lexicons/            # Generated lexical artifacts (Strong's, STEPBible glosses, morphology, WordGraph)
│   ├── strongs-list.json          # Canonical enumeration (8,674 H + 5,624 G)
│   ├── strongs-lexicon.json       # Definitions, transliterations, KJV usage
│   ├── tbesh-glosses.json         # STEPBible brief Hebrew glosses
│   ├── morphology-genesis*.json   # OSHB morphology layers (chapters 1–50)
│   └── wordgraph-genesis.json     # WordGraph lexical knowledge graph (1,783 lexemes)
├── data/                # Raw upstream sources (gitignored) + local JIT databases
│   ├── PROVENANCE.md              # Checksums, pins, and reproduction instructions
│   └── egw.db                     # Local SQLite FTS5 database for Spirit of Prophecy (gitignored)
├── scripts/             # bootstrap.sh, fetch_sources.sh, verify_all.sh, egw_lookup.py, status.py
├── ai-prompts/          # Templates for AI-assisted tasks
├── search/              # Search, linking, corpus + agreement layers (Python)
│   ├── linking/         # Semantic linking pipeline (layers b & c) + JIT EGW engine
│   ├── validation/      # F1-F4 data-integrity validators + lexicon builders
│   ├── corpus/          # Deterministic corpus/morphology generators + WordGraph draft engine
│   └── agreement/       # Source Agreement Layer (facts, comparison, ledger, apparatus)
├── .gitlab/             # Merge request template
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

# Automated environment setup (creates .venv, installs editable package and test dependencies):
./scripts/bootstrap.sh
```

### 2. Fetch Pinned Lexical Sources

The repository does not commit raw upstream archives to Git. Download the pinned raw sources (scrollmapper KJV OSIS, OSHB XML, gmlewis Strong's, STEPBible brief lexicons):

```bash
bash scripts/fetch_sources.sh
```

### 3. Initialize Spirit of Prophecy (EGW) JIT Database

Spirit of Prophecy writings are referenced via canonical pagination tokens (e.g. `egw:PP.57.1`) and stored in a local SQLite database (`data/egw.db`). Initialize the database and load seed passages:

```bash
python scripts/egw_lookup.py --init --seed-genesis
```

### 4. Run Full Local Verification

Run the exact test suite and data-integrity validators that CI executes:

```bash
bash scripts/verify_all.sh
```

### 5. Study & Query

Search the knowledge base deterministically and query Spirit of Prophecy citations:

```bash
# Query the lexical/passage SQLite index:
python -m search.linking.dbindex query --free-text "creation light"

# Lookup Spirit of Prophecy citation tokens:
python scripts/egw_lookup.py --token egw:PP.57.1

# Full-text search across local Spirit of Prophecy writings:
python scripts/egw_lookup.py --search "tree of life"
```

## Sourcing External Materials (What We Provide & What You Supply)

A foundational architectural principle of this project is: **"Link out, don't redistribute"** ([NOTICE.md](NOTICE.md), [ADR-0002](docs/decisions/ADR-0002-licensing-and-content-sourcing.md), [ADR-0011](docs/decisions/ADR-0011-whole-book-scaffolding-and-jit-egw.md)). This keeps the Git repository 100% license-clean under MIT and CC BY 4.0 while enabling powerful, offline, full-text research.

### What is bundled in the repository:
* **The Bible Text**: Pinned public-domain King James Version (KJV 1769 / OSIS) with Strong's numbering.
* **Corpus Entries**: All 1,533 verses of Genesis (`materials/bible/ot/genesis/`). Chapters 1–3 are human-curated (`status: review`); chapters 4–50 are generated as draft skeletons (`status: draft`) carrying deterministic WordGraph word-study blocks.
* **Lexical Artifacts**: Full Strong's Hebrew & Greek lexicons (`lexicons/strongs-*.json`), STEPBible brief glosses, whole-book Hebrew morphology (`lexicons/morphology-genesis{1..50}.json`), and the Genesis WordGraph (`lexicons/wordgraph-genesis.json`).
* **Source Agreement Layer**: The apparatus alignment (`correlations/apparatus-genesis{1..50}.json`) and agreement ledger.

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

## Corpus Scope: Whole-Book Genesis (Chapters 1–50)

The Genesis corpus encompasses **all 50 chapters (1,533 verses)**:
* **Genesis 1–3 (curated, `status: review`)**: Fully annotated with Hebrew word studies, Greek LXX cross-references, theological themes, and cross-language correlations.
* **Genesis 4–50 (draft skeletons, `status: draft`)**: Assembled by the deterministic draft engine (`search/corpus/draft_engine.py`) consuming the WordGraph (`lexicons/wordgraph-genesis.json`). Each entry contains verified KJV text, Strong's tags, and complete Hebrew word studies, ready for human/AI thematic curation in dedicated work packages (see `docs/wp/`).

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

## Macula Dataset Integration

The project plans to integrate the [Macula](https://tools.bible/tools/macula-greek-and-hebrew-linguistic-datasets) datasets (open-licensed Hebrew and Greek linguistic annotation) to enrich original-language data. See Macula Integration Guide for details.

## Key Design Documents

*   Tag Taxonomy — Complete tag vocabulary and relationship types
    
*   [Knowledge Base Schema](kc-schema.md) — Entry format and metadata rules
    
*   Semantic Linking Implementation Guide — How cross-language relationships work
    
*   [Contribution Standards](CONTRIBUTION_STANDARDS.md) — Submission rules and review workflow
    
*   Deterministic vs AI Boundary — Core vs AI layer distinction
    
*   [AI Prompt Templates](ai-prompts/) — Templates for AI-assisted study tasks

*   [Roadmap](ROADMAP.md) — Goal inventory and sequenced plan
    

## Technology Stack

*   **Core**: Markdown files with YAML frontmatter (human-readable, Git-friendly)
    
*   **Version Control**: Git (GitLab/GitHub)
    
*   **Search**: SQLite FTS5 (BM25) free-text + metadata queries, via the
`search/linking/` pipeline (offline, no API). Cross-language semantic
embeddings are the planned upgrade via a pluggable embedder.
    
*   **AI Integration**: LLM API (optional, for on-demand assistance)
    
*   **Original Languages**: Strong's Concordance data, Macula datasets
    
*   **Translations**: Multiple Bible translations (KJV, NKJV, ESV, NIV, etc.)
    

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
