# WP-040: Local Neural Semantic Embeddings & Hybrid Search Engine

status: complete
scope: Pillar C (C1, C2) — Implement local dense vector embeddings and a hybrid search engine combining deterministic SQLite FTS5 BM25, dense semantic embeddings (`multilingual-e5-small`), and TSK reciprocal cross-references via Reciprocal Rank Fusion (RRF), powered by a zero-PyTorch ONNX Runtime engine and pre-computed whole-Bible vector database (`data/embeddings.db`).
priority: high

## Objective
Enable true conceptual and thematic search across the Old and New Testaments without cloud dependencies or binary bloat (ADR-013, ADR-029). Allow users searching for theological motifs or paraphrases (e.g. *"suffering servant mocked by crowds"*, *"rest from works"*, *"vindication in judgment"*) to discover relevant Scripture passages (such as Psalm 22, Isaiah 53, and Hebrews 4) even when exact lemma keywords differ, while preserving deterministic exact-match accuracy through a Tri-Brid Reciprocal Rank Fusion ranker.

## Inputs (read these first)
- `data/bible.db`: `verses` (31,102 verses, KJV text + Strong's tags + alignments)
- `data/macula.db`: original language morphology and Louw-Nida semantic domains
- `search/linking/embedder.py`: pluggable base embedder (`BaseEmbedder`, `CharNgramEmbedder`, `SentenceTransformerEmbedder`)
- `search/corpus/search_bridge.py`: deterministic search bridge with BM25 sigmoid normalization
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md` (Zero bloat / stewardship)
- `docs/decisions/ADR-027-content-level-sqlite-integrity.md` (SQLite canonical integrity)
- `docs/decisions/ADR-029-zero-pytorch-local-neural-embeddings-and-hybrid-search.md` (Zero-PyTorch ONNX & RRF)

## Tasks
- [x] Task 1: Offline Embedding Generation Pipeline (`scripts/build_embeddings.py`):
  - Ingest all 31,102 verses from `data/bible.db`.
  - Format verses with contextual book/chapter framing (`passage: Book Chapter:Verse text`).
  - Compute 384-dimensional dense vectors using `intfloat/multilingual-e5-small`.
  - Export into compact SQLite table (`data/embeddings.db`: `verses(verse_id TEXT PRIMARY KEY, vector BLOB, magnitude REAL)`).
  - Verify content-level SHA-256 in `data/INTEGRITY.json`.
- [x] Task 2: Lightweight ONNX Query Embedder (`search/linking/onnx_embedder.py`):
  - Implement single-query inference via `onnxruntime` (INT8 quantized model ~30 MB, ~10ms CPU latency).
  - Wrap inside `BaseEmbedder` interface with strict automatic fallback to `CharNgramEmbedder` if ONNX weights or runtime are absent.
  - Zero PyTorch or HuggingFace Transformers dependencies at runtime.
- [x] Task 3: Tri-Brid Reciprocal Rank Fusion Engine (`search/corpus/hybrid_search.py`):
  - Implement fast in-memory / SQLite vector cosine similarity scan over 31,102 verses (<5ms).
  - Implement Reciprocal Rank Fusion (RRF) blending:
    $$\text{RRF Score}(d) = \frac{w_{\text{text}}}{60 + \text{rank}_{\text{BM25}}(d)} + \frac{w_{\text{semantic}}}{60 + \text{rank}_{\text{vector}}(d)} + \frac{w_{\text{tsk}}}{60 + \text{rank}_{\text{TSK}}(d)}$$
  - Support search mode parameters: `mode=hybrid` (default), `mode=exact` (lexical BM25 only), `mode=semantic` (vector only).
- [x] Task 4: REST API & Search Workstation UI Integration:
  - Wire hybrid search into `search/ui/study_service.py` and `/api/search`.
  - Update `web/app.js` and `web/index.html` with a Search Mode toggle pill (`Hybrid`, `Keyword`, `Thematic`).
  - Render semantic similarity badges and thematic match explanations alongside verse cards.
- [x] Task 5: Testing, Benchmarking & Verification:
  - Unit tests in `search/corpus/test_hybrid_search.py` and `search/linking/test_onnx_embedder.py`.
  - Thematic validation tests (verifying that "suffering servant" / crucifixion queries retrieve Psalm 22 and Isaiah 53).
  - Sub-millisecond performance benchmarks verifying <20ms total end-to-end query time.
  - Full verification with `bash scripts/verify_all.sh`.

## Conventions that apply
- **Deterministic core (AGENTS.md Non-negotiable 1):** Pre-computed embeddings in `data/embeddings.db` are pinned and verified; raw neural outputs never overwrite canonical Scripture or curated entries.
- **Fail fast, never silently corrupt (Non-negotiable 3):** If ONNX runtime is absent, fallback to `CharNgramEmbedder` is logged and deterministic lexical search continues without crashing.
- **Zero-Waste Stewardship (ADR-013):** No 2 GB PyTorch installations. Single-query ONNX inference runs on CPU with <40 MB RAM.

## Acceptance criteria
- [x] `scripts/build_embeddings.py` compiles `data/embeddings.db` for all 31,102 verses.
- [x] Single query string embedding executes locally in <20ms on standard CPU.
- [x] Querying *"My God, my God, why hast thou forsaken me"* or *"mocked and pierced hands"* ranks Psalm 22 and Matthew 27 in top results.
- [x] Exact passage queries (e.g. `John 3:16`, `"In the beginning"`) maintain exact-match BM25 priority.
- [x] Packaging harnesses stage `data/embeddings.db` without exceeding release size budgets.
- [x] All automated tests pass in `scripts/verify_all.sh`.
