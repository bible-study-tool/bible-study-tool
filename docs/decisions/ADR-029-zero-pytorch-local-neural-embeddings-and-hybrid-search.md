# ADR-029: Zero-PyTorch Local Neural Embeddings & Hybrid RRF Search

## Context

Following the delivery of the Native Desktop Application (ADR-028, WP-038) and the Deterministic Cross-Language Unified Search Workstation (WP-039), the Adventist Bible Study Tool provides sub-millisecond lexical search across 31,102 Bible verses, parallel translations, Macula Hebrew and Greek morphology, 344k+ TSK cross-references, and historical commentary.

However, roadmap items **C1 (True semantic embeddings)** and **C2 (Hybrid search)** identify a remaining gap:
When users search for theological themes, thematic paraphrases, or conceptual motifs where exact keywords or lemma glosses differ (e.g. *"suffering servant mocked by crowds"* finding Psalm 22 and Isaiah 53, or *"vindication of the sanctuary"* finding Daniel 8:14 and Leviticus 16), deterministic BM25 keyword matching alone cannot infer the semantic overlap.

Traditional neural search solutions introduce severe drawbacks:
1. **Bloated Runtime Dependencies:** Shipping Python PyTorch or HuggingFace Transformers adds 800 MB to 2 GB of binary bloat, directly violating ADR-013 (*"Doing the best for God without waste"*), ADR-023, and ADR-024.
2. **Cloud/API Privacy Leaks:** Offloading vector embeddings to cloud APIs (e.g. OpenAI, Cohere) violates the core zero-cloud, 100% offline-first privacy guarantee.
3. **Hallucination and Vector Drift:** Unchecked vector similarity returns "fuzzy" associations that lack theological grounding, confusing typological distinctions.

## Decision

1. **Pre-Computed Whole-Bible Vector Database (`data/embeddings.db`):**
   - We will pre-compute 384-dimensional dense vectors for all 31,102 verses offline during release compilation using the multilingual transformer `intfloat/multilingual-e5-small`.
   - The resulting vector table will be stored in a compact SQLite database (`data/embeddings.db`, ~24–48 MB) and tracked by content-level SHA-256 in `data/INTEGRITY.json` (ADR-027).
   - The user's device **never** computes 31,102 verse embeddings at runtime.

2. **Zero-PyTorch Local Query Inference:**
   - At search time, the user's computer embeds only the single query string (typically 3–10 tokens).
   - Inference will be performed using a quantized ONNX Runtime engine (INT8 model size ~30 MB, memory footprint <40 MB, query latency ~10ms on CPU).
   - If ONNX weights or runtime are unavailable, the system strictly falls back to the deterministic character n-gram embedder (`CharNgramEmbedder`) and lexical FTS5 search with zero degradation of core functionality.

3. **Sub-Millisecond Vector Dot-Product Scoring:**
   - Query vectors will be compared against the 31,102 pre-computed vectors using native SIMD (AVX2/NEON) dot products, completing whole-Bible vector ranking in under 2 milliseconds on CPU.

4. **Tri-Brid Reciprocal Rank Fusion (RRF):**
   - Results will be ranked by blending three independent signals:
     $$\text{RRF}(d) = \frac{w_{\text{text}}}{60 + \text{rank}_{\text{BM25}}(d)} + \frac{w_{\text{semantic}}}{60 + \text{rank}_{\text{vector}}(d)} + \frac{w_{\text{tsk}}}{60 + \text{rank}_{\text{TSK}}(d)}$$
   - Exact textual matches remain pinned at #1.
   - Conceptual parallels surface naturally without keyword overlap.
   - Scripture-interpreting-Scripture apostolic cross-references receive reciprocal reinforcement.

## Status

Accepted.

## Consequences

* **Positive:**
  - True semantic search across Hebrew, Greek, and English with zero cloud calls.
  - Desktop installer sizes remain lean and portable (~25 MB compressed vector DB addition).
  - No 2 GB PyTorch installation or GPU required.
  - Exact textual search precision is preserved alongside thematic discovery.
* **Negative / Trade-offs:**
  - Requires maintaining the offline vector generation script (`scripts/build_embeddings.py`).
  - Packaging must stage `data/embeddings.db` and the quantized ONNX model file.

## References

- [ADR-001: Deterministic Core vs AI Layer Boundary](ADR-001-deterministic-core-vs-ai.md)
- [ADR-004: Single Deterministic Search Stack](ADR-004-single-deterministic-search-stack.md)
- [ADR-013: Design Principles — Stewardship & Scalability](ADR-013-design-principles-stewardship-and-scalability.md)
- [ADR-024: GUI-First Architecture & Standalone Desktop Packaging](ADR-024-gui-first-architecture-tui-as-mode.md)
- [ADR-027: Content-Level Integrity Verification for SQLite Data Bundles](ADR-027-content-level-sqlite-integrity.md)
- [ADR-028: Tauri Desktop Packaging and Native Window Architecture](ADR-028-tauri-desktop-packaging-and-native-window.md)
- [WP-039: Deterministic Cross-Language Unified Search Workstation](../wp/WP-039-deterministic-cross-language-unified-search.md)
- [WP-040: Local Neural Semantic Embeddings & Hybrid Search Engine](../wp/WP-040-neural-embeddings-and-hybrid-search.md)
