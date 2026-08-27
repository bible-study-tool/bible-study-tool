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
│   ├── bible/           # Bible texts and commentaries
│   │   ├── ot/          # Old Testament
│   │   └── nt/          # New Testament
│   ├── spirit-of-prophecy/  # Ellen G. White writings
│   ├── commentaries/    # Third-party commentaries
│   ├── original-languages/  # Hebrew, Greek, Aramaic
│   ├── lexicons/        # Strong's, Thayer's, BDB
│   ├── study-guides/    # Sabbath School, devotionals
│   └── translations/    # Multiple translation versions
├── tags/                # Tag taxonomy and indexes
├── index/               # Generated indexes (tag → entry, passage → entry)
├── correlations/        # Cross-references and semantic links
│   ├── semantic-links.json       # Curated cross-language relationships
│   ├── semantic-links-index.json # Quick lookup index
│   ├── ai-discovered-links.json  # AI-suggested links awaiting review
│   ├── DETERMINISTIC_VS_AI.md    # Core vs AI layer boundary
│   ├── MACULA_INTEGRATION.md     # Macula dataset integration plan
│   └── SEMANTIC_LINKING_GUIDE.md # Code-level implementation guide
├── notes/               # Study notes and word studies
├── ai-prompts/          # Templates for AI-assisted tasks
├── search/              # Semantic search engine (Python)
│   └── linking/         # Semantic linking pipeline (layers b & c)
├── .gitlab/             # GitLab CI, merge request templates
├── CONTRIBUTION_STANDARDS.md
├── kc-schema.md
└── README.md
```

## Quick Start

### 1. Clone the Repository

```bash
git clone <repo-url>
cd bible-study-tool
```

### 2. Add Materials

Place your materials in the appropriate `materials/` subdirectory following the naming convention:

*   Bible passages: `{book}-{chapter}-{verse}-{source}.md`
    
*   Word studies: `{lang}-{strongs}-{source}.md`
    
*   Spirit of Prophecy: `{abbrev}-{chapter}-{source}.md`
    

### 3. Tag and Index

Each entry uses YAML frontmatter with tags from the Tag Taxonomy.

### 4. Use AI Assistance (Optional)

When you need deeper study:

1.  Query the knowledge base deterministically
    
2.  Pull relevant materials into context
    
3.  Use the [AI Prompt Templates](ai-prompts/) for structured AI assistance
    
4.  Review and save AI-generated content back to the knowledge base
    

## MVP: Genesis 1:1-3

The initial MVP covers **Genesis 1:1–3** with:

*   Full Hebrew word studies (Strong's H7225, H430, H1254, H8415, H7307, H7741, H559, H215, H216)
    
*   Greek LXX cross-references
    
*   Semantic linking between Hebrew and Greek concepts (3 curated links)
    
*   AI-assisted word study and cross-reference discovery
    

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

### Install dependencies

```bash
pip install numpy pyyaml
```

> Note: the linking pipeline (`search/linking/`) requires only `numpy` and
> PyYAML for its deterministic mode; SQLite (`sqlite3`) is part of Python's
> standard library. scikit-learn is **not** required. For the higher-fidelity
> multilingual embedder, optionally install `sentence-transformers` (see the
> Semantic Linking Guide).

## Macula Dataset Integration

The project plans to integrate the [Macula](https://tools.bible/tools/macula-greek-and-hebrew-linguistic-datasets) datasets (open-licensed Hebrew and Greek linguistic annotation) to enrich original-language data. See Macula Integration Guide for details.

## Key Design Documents

*   Tag Taxonomy — Complete tag vocabulary and relationship types
    
*   [Knowledge Base Schema](kc-schema.md) — Entry format and metadata rules
    
*   Semantic Linking Implementation Guide — How cross-language relationships work
    
*   [Contribution Standards](CONTRIBUTION_STANDARDS.md) — Submission rules and review workflow
    
*   Deterministic vs AI Boundary — Core vs AI layer distinction
    
*   [AI Prompt Templates](ai-prompts/) — Templates for AI-assisted study tasks
    

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

[To be determined]

## Contributing

See [Contribution Standards](CONTRIBUTION_STANDARDS.md) for guidelines.
