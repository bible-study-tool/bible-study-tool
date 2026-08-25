# Semantic Linking Implementation Guide

This is the living implementation guide for the semantic linking pipeline.
It complements `DETERMINISTIC_VS_AI.md` (the boundary) and `MACULA_INTEGRATION.md`
(the linguistic-data foundation) with the *code* that realises them.

## Goal

Make deep, cross-language biblical insight accessible to as many readers as
possible. Two Bible verses may look unrelated in English but share a deeper
bond when the original Hebrew / Greek is examined. The tool surfaces that
bond in a way that is trustworthy (deterministic core) and expandable
(multilingual AI layer) — without hallucinated or agenda-driven connections.

## Two cooperating layers

The pipeline intentionally mirrors the deterministic / AI boundary.

### Layer (b) — Deterministic Strong's root concordance

**Purpose:** authoritative, human-verified. Groups every entry that shares an
original-language lexeme (Strong's number) and connects attestations across
passages, translations, and languages.

**Where:** `search/linking/concordance.py`, output `index/concordance.json`

**Guarantees:**
* Fully deterministic — same materials in, same output out.
* Never invents a connection; every edge is grounded in an explicit
  `strongs-*` tag or a curated semantic link.
* `cross_language` flag marks roots attested in more than one language.

Each Strong's -> entry pair is read from a SQLite index (see below), so it
never rescans the Markdown tree at query time.

### The SQLite index (shared foundation)

`search/linking/dbindex.py` builds and queries `index/semantic.db` — a single,
offline, gitignored generated artifact. Markdown remains the source of truth;
the db is rebuilt when materials change.

* **FTS5** full-text search over passage + body (real BM25 scoring).
* **`entry_tags`** table with proper SQL queries — "entries with
  strongs-H7225 AND theme/creation" — instead of Python loops over every entry.
* Both layers (b) and (c) query the db rather than rescanning `materials/`.

```bash
# Build the index from Markdown (authoritative)
python -m search.linking.dbindex build --repo .

# Query the index (no rescan of materials/)
python -m search.linking.dbindex query --db index/semantic.db --count
python -m search.linking.dbindex query --db index/semantic.db --strongs H7225
python -m search.linking.dbindex query --db index/semantic.db --tag theme/creation
python -m search.linking.dbindex query --db index/semantic.db --free-text "creation light"
```

## Running the pipeline

The linking CLI builds the db once, then both layers query it:

```bash
# Layer (b): deterministic concordance -> index/concordance.json (queries the db)
python -m search.linking.cli --repo . --deterministic

# Layer (c): multilingual discovery -> correlations/ai-discovered-links.json
python -m search.linking.cli --repo . --discover --top-k 5

# Both layers, seeding accepted candidates to stdout
python -m search.linking.cli --repo . --all --seed

# Force a rebuild of the index, or tune the acceptance gate
python -m search.linking.cli --repo . --all --rebuild-db
python -m search.linking.cli --repo . --discover --min-sim 0.6
```

### Layer (c) — Multilingual semantic candidate discovery (AI layer)

**Purpose:** suggests cross-language connections *beyond* a shared Strong's
number. e.g. Hebrew `בָּרָא` (bara, divine create) with Greek `κτίζω` (ktizō,
divine create) belong to a common conceptual field despite being different
lexemes and different scripts.

**Where:** `search/linking/candidates.py`, output
`correlations/ai-discovered-links.json`

**Strict acceptance rules (enforced in code, see `RULE_ARCHIVE`):**
1. A candidate must be **cross-language** (Hebrew↔Greek, Hebrew↔English,
   Greek↔English). Same-language pairs are concordance territory (layer b).
2. It must exceed a **similarity threshold** (`min_similarity`).
3. The relationship type must come from the taxonomy's `relation/` vocabulary.
   `relation/contrast` is deliberately *not* auto-proposed — it needs a human.
4. Every candidate carries a `confidence` and `review_status` (`pending`).
5. Output is **always** written to `ai-discovered-links.json` — the
   deterministic `semantic-links.json` is never modified by the AI layer.
6. Candidates that duplicate an existing curated link are **deduplicated**.
7. `aligns_with_doctrine` is always `null` until a human reviewer sets it —
   theological alignment is an explicit human gate.
8. Only the strongest `top_k` candidates are kept.

## Embedder (the multilingual core)

`search/linking/embedder.py` provides a pluggable embedder:

* **Preferred:** `intfloat/multilingual-e5-small` (a real multilingual
  transformer) when `sentence-transformers` is installed. Hebrew / Greek /
  English land in one shared vector space — best fidelity.
* **Fallback:** a deterministic, offline, cross-script character n-gram
  hashing embedder (numpy only, 512-dim, L2-normalized). No model, no network,
  fully reproducible. Works on any script because it operates on characters.

The pipeline is model-agnostic: everything downstream just calls
`embedder.embed(text)`. Because the two embedders live in different vector
spaces, the effective similarity threshold differs (transformer ~0.82,
deterministic fallback ~0.70) — the CLI defaults adapt to the active embedder,
and both are overridable with `--min-sim`.

## Running the pipeline

```bash
# Layer (b): deterministic concordance -> index/concordance.json
python -m search.linking.cli --repo . --deterministic

# Layer (c): multilingual discovery -> correlations/ai-discovered-links.json
python -m search.linking.cli --repo . --discover --top-k 5

# Both, with the seed of accepted candidates printed
python -m search.linking.cli --repo . --all --seed

# Tune the acceptance gate for the active embedder space
python -m search.linking.cli --repo . --discover --min-sim 0.6
```

## Tests

```bash
python -m search.linking.test_pipeline
```

## Reading the outputs

### `index/concordance.json`
`by_strongs.<root>.entries` lists every entry (and its language / translation /
passage) that uses that root. `links` groups multi-attestation roots — these
are the "hidden in English, visible in Hebrew/Greek" connections.

### `correlations/ai-discovered-links.json`
Generated candidates. Each has `review_status: pending`, `confidence`, the two
lexemes with their languages, a similarity score, and a rationale. **Nothing
here is authoritative** until a human promotes it into `semantic-links.json`.

## Promotion workflow (human)

1. Reviewer opens `ai-discovered-links.json`.
2. Verifies the linguistic claim (lexicons, Macula, original text).
3. Checks theological alignment and sets `aligns_with_doctrine` truthfully.
4. If sound: copy the candidate into `semantic-links.json` (deterministic core),
   set its `source` to `manual` and `reviewed_by`.
5. Update the entry frontmatter `semantic_links` and the
   `semantic-links-index.json` lookup index.
6. If unsound: set `review_status: rejected` and leave it out of the core.

## Current dataset note

The MVP corpus is tiny (Genesis 1:1–3). The two strongest cross-language pairs
already exist as curated links (sl-001, sl-002), so the strict default
threshold correctly yields 0 *new* candidates. Lowering `--min-sim` reveals a
genuinely novel, un-curated connection (e.g. `κτίζω` ↔ `עָשָׂה`, create/make),
demonstrating the discovery mechanism end-to-end. As `materials/` grows the
discovery layer's value increases.
