# WP-043: Spirit of Prophecy (EGW) Hybrid Search & Isolated Library Vector Integration

status: complete
scope: Pillar C (C1, C2), Pillar A (A7, A12), Pillar D (D1, D3) — Integrate dense neural vector search and Dual-Signal Reciprocal Rank Fusion (RRF) for Spirit of Prophecy commentary from isolated user storage (`data/library_embeddings.db`), providing seamless semantic and hybrid search across EGW writings while guaranteeing 100% graceful fallback and zero impact on Scripture study when library embeddings are absent.
priority: high

## Objective

Deliver deep semantic and hybrid search for Spirit of Prophecy (EGW) writings by connecting the local 384-dimensional dense vectors in `data/library_embeddings.db` (364,022 paragraphs) with the existing FTS5 BM25 search engine:
1. **Dual-Signal Reciprocal Rank Fusion (RRF):** Blend deterministic BM25 keyword rankings with local dense vector cosine similarity to surface both exact phrase hits and thematic parallels (e.g. *sanctuary cleansing*, *Jacob wrestling at Peniel*, *investigative judgment*).
2. **Transparent Match Badging & Plain-English Explanations:** Surface match types (`✦ Hybrid`, `Aa Exact`, `☵ Thematic`), cosine similarity scores, and plain-English reasons in search results, matching the ergonomics of Scripture hybrid search.
3. **Decoupled & Resilient Degradation:** Preserve the fundamental principle that Scripture study never depends on external or user commentary. If `library_embeddings.db` is absent or unindexed, commentary search gracefully falls back to BM25 keyword matching; if `egw.db` is absent, commentary returns empty results without crashing or affecting Scripture search.
4. **Copyright & Privacy Isolation:** Strictly honor ADR-002, ADR-016, ADR-028, and ADR-029 by ensuring user library embeddings remain in isolated local storage (`data/library_embeddings.db`) and are never bundled into release artifacts.

## Inputs (read these first)
- `docs/decisions/ADR-029-zero-pytorch-local-neural-embeddings-and-hybrid-search.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `docs/decisions/ADR-002-licensing-and-content-sourcing.md`
- `docs/decisions/ADR-011-egw-integration.md`
- `docs/decisions/ADR-024-gui-first-architecture-tui-as-mode.md`
- `docs/wp/WP-040-neural-embeddings-and-hybrid-search.md`
- `docs/wp/WP-042-neural-model-sourcing-and-gui-embedding-management.md`
- `search/corpus/hybrid_search.py`
- `search/corpus/search_bridge.py`
- `search/linking/egw.py`
- `search/resource.py`

---

## Tasks

- [x] ### Task 1: `LibraryVectorStore` and `EgwDB.get_paragraphs_batch`
  - In `search/linking/egw.py`: Add `get_paragraphs_batch(paragraph_ids: Sequence[str]) -> dict[str, dict[str, Any]]` for fast single-query retrieval of paragraph metadata and text with token alias preservation.
  - In `search/corpus/hybrid_search.py`: Implement `LibraryVectorStore` with streaming chunked thread-safe loading, fast book code scoping, and dot-product vector query.

- [x] ### Task 2: `EgwHybridSearchEngine` Implementation
  - In `search/corpus/hybrid_search.py`: Implement `EgwHybridSearchEngine` blending BM25 from `EgwDB` and dense vector cosine similarity from `LibraryVectorStore`.
  - Support `hybrid`, `keyword`, and `thematic`/`semantic` search modes.
  - Compute calibrated scores in `[0.50, 0.99]`, match badges (`hybrid`, `exact`, `semantic`), and plain-English match explanations.

- [x] ### Task 3: `DeterministicSearchBridge` Integration & Graceful Fallback
  - In `search/corpus/search_bridge.py`: Wire `EgwHybridSearchEngine` into `_search_commentary`.
  - Pass search `mode` from `search(...)` to `_search_commentary`.
  - Ensure fail-safe fallback: if `library_vector_store.available()` is False, fallback to BM25; if `egw_db` is absent, return `[]`. Scripture search remains 100% independent.

- [x] ### Task 4: Unit Test Suite & Verification
  - Add comprehensive unit tests in `search/corpus/test_egw_hybrid_search.py` (14 unit tests).
  - Verify all modes, fallbacks with missing databases, book scoping, token aliases, and RRF calculations.
  - Run `bash scripts/verify_all.sh` to ensure all tests and validators pass.
  - Subagent review and documentation update.
