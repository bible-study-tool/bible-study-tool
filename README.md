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
│   └── SEMANTIC_LINKING_GUIDE.md # Full implementation guide
├── notes/               # Study notes and word studies
├── ai-prompts/          # Templates for AI-assisted tasks
├── search/              # Semantic search engine (Python)
├── .gitlab/             # GitLab CI, merge request templates
├── CONTRIBUTION_STANDARDS.md
├── kb-schema.md
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
    

## Lexical / Keyword Search (MVP)

A lightweight offline search engine is included in  
`search/semantic_search.py`. It uses TF-IDF vectorization (scikit-learn)  
and YAML-frontmatter parsing (PyYAML). No API calls, fully offline.
Note: TF-IDF is a lexical/keyword search, not neural-semantic search. It  
matches literal terms and word n-grams; it does not understand synonyms,  
concepts, paraphrase, or cross-language meaning. True "semantic" matching  
(embeddings) is the planned upgrade - the engine interface is designed for a  
drop-in embeddings backend.
Usage:

```bash
# Build and persist the index once
python search/semantic_search.py --repo . --build-index

# Then query (loads the saved index)
python search/semantic_search.py --repo . --query "creation of light"
python search/semantic_search.py --repo . --strongs H7225
python search/semantic_search.py --repo . --tag theme/creation
python search/semantic_search.py --repo . --xref gen-1-1-kjv

# Force a rebuild
python search/semantic_search.py --repo . --rebuild-index
```

The built index is saved to index/semantic_index.pkl (a generated binary;  
add "index/*.pkl" to .gitignore).

### Install dependencies

```bash
pip install pyyaml scikit-learn
```

```

## Macula Dataset Integration

The project plans to integrate the [Macula](https://tools.bible/tools/macula-greek-and-hebrew-linguistic-datasets) datasets (open-licensed Hebrew and Greek linguistic annotation) to enrich original-language data. See Macula Integration Guide for details.

## Key Design Documents

*   Tag Taxonomy — Complete tag vocabulary and relationship types
    
*   [Knowledge Base Schema](kb-schema.md) — Entry format and metadata rules
    
*   Semantic Linking Implementation Guide — How cross-language relationships work
    
*   [Contribution Standards](CONTRIBUTION_STANDARDS.md) — Submission rules and review workflow
    
*   Deterministic vs AI Boundary — Core vs AI layer distinction
    
*   [AI Prompt Templates](ai-prompts/) — Templates for AI-assisted study tasks
    

## Technology Stack

*   **Core**: Markdown files with YAML frontmatter (human-readable, Git-friendly)
    
*   **Version Control**: Git (GitLab/GitHub)
    
*   **Search**: TF-IDF lexical/keyword vectorization via scikit-learn, plus 
PyYAML for frontmatter parsing (offline, no API). True semantic embeddings planned.
    
*   **AI Integration**: LLM API (optional, for on-demand assistance)
    
*   **Original Languages**: Strong's Concordance data, Macula datasets
    
*   **Translations**: Multiple Bible translations (KJV, NKJV, ESV, NIV, etc.)
    

## License

[To be determined]

## Contributing

See [Contribution Standards](CONTRIBUTION_STANDARDS.md) for guidelines.
