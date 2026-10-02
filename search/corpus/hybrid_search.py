"""Tri-Brid Reciprocal Rank Fusion (RRF) Hybrid Search Engine (WP-040, ADR-029).

Blends three independent signals into a unified whole-Bible relevance ranking:
1. Deterministic SQLite FTS5 BM25 lexical search (exact keywords, phrases, Boolean).
2. Local dense vector cosine similarity (intfloat/multilingual-e5-small via ONNX).
3. Treasury of Scripture Knowledge (TSK) reciprocal apostolic cross-references.

Formula:
    RRF(d) = w_text / (k + rank_bm25(d)) + w_sem / (k + rank_sem(d)) + w_tsk / (k + rank_tsk(d))
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from typing import Any, Optional, Sequence

import numpy as np

from search.dbaccess import connect_db_reader
from search.corpus.extract_kjv import BibleDB
from search.linking.onnx_embedder import OnnxEmbedder
from search.resource import get_data_dir, get_embeddings_db_path, get_library_embeddings_db_path

logger = logging.getLogger(__name__)

_DEFAULT_K_RRF = 60
_DEFAULT_WEIGHTS = (1.0, 0.8, 0.5)  # (w_text, w_semantic, w_tsk)
_DEFAULT_EGW_WEIGHTS = (1.0, 0.8)  # (w_text, w_semantic)


@dataclass
class HybridHit:
    """A scored search hit combining lexical, semantic, and cross-reference signals."""

    verse_id: str
    book: str
    osis: str
    chapter: int
    verse: int
    text: str
    clean_text: str
    rrf_score: float
    text_rank: Optional[int] = None
    text_score: Optional[float] = None
    semantic_rank: Optional[int] = None
    semantic_score: Optional[float] = None
    tsk_rank: Optional[int] = None
    tsk_citations: list[str] = field(default_factory=list)
    match_type: str = "hybrid"  # "exact", "semantic", "cross_reference", "hybrid"
    match_reason: str = ""
    translation: str = "KJV"
    strongs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EgwHybridHit:
    """A scored EGW commentary hit combining BM25 keyword and dense neural semantic signals."""

    paragraph_id: str
    book_code: str
    book_title: str
    chapter_num: Optional[int]
    chapter_title: Optional[str]
    page: int
    paragraph: int
    ref_code: str
    text: str
    snippet: str
    rrf_score: float
    text_rank: Optional[int] = None
    text_score: Optional[float] = None
    semantic_rank: Optional[int] = None
    semantic_score: Optional[float] = None
    match_type: str = "hybrid"  # "hybrid" | "exact" | "semantic"
    match_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VectorStore:
    """In-memory contiguous float32 matrix for whole-Bible cosine similarity scans."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path).resolve() if db_path else get_embeddings_db_path()
        self._matrix: Optional[np.ndarray] = None
        self._verse_ids: list[str] = []
        self._id_to_idx: dict[str, int] = {}
        self._osis_indices: dict[str, list[int]] = {}
        self._lock = threading.Lock()
        self._is_loaded: bool = False
        self._load_error: Optional[str] = None

    def available(self) -> bool:
        """Return True if embeddings database exists and can be loaded."""
        if not self._is_loaded and self._load_error is None:
            self._load()
        return self._is_loaded

    def _load(self) -> None:
        with self._lock:
            if self._is_loaded:
                return
            if not self.db_path.is_file():
                self._load_error = f"Embeddings database not found at {self.db_path}"
                return

            try:
                conn = connect_db_reader(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT verse_id, vector FROM verses ORDER BY rowid")
                rows = cur.fetchall()
                conn.close()

                if not rows:
                    self._load_error = "Embeddings database contains no verses."
                    return

                self._verse_ids = [r[0] for r in rows]
                self._id_to_idx = {vid: idx for idx, vid in enumerate(self._verse_ids)}

                # Group indices by OSIS book for fast book scoping
                self._osis_indices = {}
                for idx, vid in enumerate(self._verse_ids):
                    osis = vid.split(".")[0]
                    self._osis_indices.setdefault(osis, []).append(idx)

                # Contiguous 2D matrix
                raw_bytes = b"".join(r[1] for r in rows)
                self._matrix = np.frombuffer(raw_bytes, dtype=np.float32).reshape(len(rows), 384)
                self._is_loaded = True
                logger.info(f"Loaded {len(self._verse_ids):,} vectors from {self.db_path}")
            except Exception as exc:
                self._load_error = str(exc)
                logger.warning(f"Failed to load VectorStore: {exc}")

    def query(
        self,
        q_vec: np.ndarray,
        top_k: int = 100,
        allowed_osis: Optional[set[str]] = None,
    ) -> list[tuple[str, float]]:
        """Compute cosine similarity against all verses and return top hits."""
        if not self.available() or self._matrix is None:
            return []

        # Single BLAS dot product across 31,102 vectors
        scores = self._matrix @ q_vec

        # Apply OSIS scoping filter if requested (slice matching indices to prevent leakage)
        if allowed_osis is not None:
            matching_indices: list[int] = []
            for osis in allowed_osis:
                matching_indices.extend(self._osis_indices.get(osis, []))
            if not matching_indices:
                return []
            idx_arr = np.array(matching_indices, dtype=np.intp)
            scoped_scores = scores[idx_arr]
            n_results = min(top_k, len(scoped_scores))
            if n_results <= 0:
                return []
            top_local = np.argpartition(scoped_scores, -n_results)[-n_results:]
            sorted_top_local = top_local[np.argsort(-scoped_scores[top_local])]
            return [(self._verse_ids[idx_arr[i]], float(scoped_scores[i])) for i in sorted_top_local]

        n_results = min(top_k, len(scores))
        if n_results <= 0:
            return []

        top_indices = np.argpartition(scores, -n_results)[-n_results:]
        sorted_top_indices = top_indices[np.argsort(-scores[top_indices])]

        return [(self._verse_ids[idx], float(scores[idx])) for idx in sorted_top_indices]


class LibraryVectorStore:
    """In-memory contiguous float32 matrix for user library / EGW commentary cosine similarity scans."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path).resolve() if db_path else get_library_embeddings_db_path()
        self._matrix: Optional[np.ndarray] = None
        self._paragraph_ids: list[str] = []
        self._book_indices: dict[str, list[int]] = {}
        self._lock = threading.Lock()
        self._is_loaded: bool = False
        self._load_error: Optional[str] = None

    def available(self) -> bool:
        """Return True if library embeddings database exists and can be loaded."""
        if not self._is_loaded:
            if self.db_path.is_file() and (self._load_error is None or "not found" in self._load_error):
                self._load()
        return self._is_loaded

    def reload(self) -> bool:
        """Force reload of the vector matrix from disk."""
        with self._lock:
            self._is_loaded = False
            self._load_error = None
            self._matrix = None
            self._paragraph_ids = []
            self._book_indices = {}
        return self.available()

    def _load(self) -> None:
        with self._lock:
            if self._is_loaded:
                return
            if not self.db_path.is_file():
                self._load_error = f"Library embeddings database not found at {self.db_path}"
                return

            try:
                conn = connect_db_reader(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM paragraphs")
                count_row = cur.fetchone()
                total_rows = count_row[0] if count_row else 0
                if total_rows == 0:
                    self._load_error = "Library embeddings database contains no paragraphs."
                    conn.close()
                    return

                matrix = np.empty((total_rows, 384), dtype=np.float32)
                paragraph_ids: list[str] = []
                book_indices: dict[str, list[int]] = {}

                cur.execute("SELECT paragraph_id, book_code, vector FROM paragraphs ORDER BY rowid")
                chunk_size = 10000
                row_offset = 0

                while True:
                    chunk = cur.fetchmany(chunk_size)
                    if not chunk:
                        break
                    chunk_len = len(chunk)
                    for idx_in_chunk, (pid, b_code, _) in enumerate(chunk):
                        global_idx = row_offset + idx_in_chunk
                        paragraph_ids.append(pid)
                        if b_code:
                            clean_b = b_code.strip().upper()
                            if clean_b:
                                book_indices.setdefault(clean_b, []).append(global_idx)

                    chunk_bytes = b"".join(r[2] for r in chunk)
                    matrix[row_offset : row_offset + chunk_len] = np.frombuffer(
                        chunk_bytes, dtype=np.float32
                    ).reshape(chunk_len, 384)
                    row_offset += chunk_len

                conn.close()
                self._matrix = matrix
                self._paragraph_ids = paragraph_ids
                self._book_indices = book_indices
                self._is_loaded = True
                logger.info(f"Loaded {len(self._paragraph_ids):,} library vectors from {self.db_path}")
            except Exception as exc:
                self._load_error = str(exc)
                logger.warning(f"Failed to load LibraryVectorStore: {exc}")

    def query(
        self,
        q_vec: np.ndarray,
        top_k: int = 100,
        allowed_book_codes: Optional[set[str]] = None,
    ) -> list[tuple[str, float]]:
        """Compute cosine similarity against all library paragraphs and return top hits."""
        if not self.available() or self._matrix is None:
            return []

        # Single BLAS dot product across all vectors
        scores = self._matrix @ q_vec

        # Apply book scoping filter if requested
        if allowed_book_codes is not None:
            clean_allowed = {b.strip().upper() for b in allowed_book_codes if b}
            if not clean_allowed:
                return []
            matching_indices: list[int] = []
            for b_code in clean_allowed:
                matching_indices.extend(self._book_indices.get(b_code, []))
            if not matching_indices:
                return []
            idx_arr = np.array(matching_indices, dtype=np.intp)
            scoped_scores = scores[idx_arr]
            n_results = min(top_k, len(scoped_scores))
            if n_results <= 0:
                return []
            top_local = np.argpartition(scoped_scores, -n_results)[-n_results:]
            sorted_top_local = top_local[np.argsort(-scoped_scores[top_local])]
            return [(self._paragraph_ids[idx_arr[i]], float(scoped_scores[i])) for i in sorted_top_local]

        n_results = min(top_k, len(scores))
        if n_results <= 0:
            return []

        top_indices = np.argpartition(scores, -n_results)[-n_results:]
        sorted_top_indices = top_indices[np.argsort(-scores[top_indices])]

        return [(self._paragraph_ids[idx], float(scores[idx])) for idx in sorted_top_indices]


class HybridSearchEngine:
    """Orchestrates Tri-Brid Reciprocal Rank Fusion search across Scripture."""

    def __init__(
        self,
        bible_db: Optional[BibleDB] = None,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[OnnxEmbedder] = None,
    ) -> None:
        self.bible_db = bible_db or BibleDB()
        self.vector_store = vector_store or VectorStore()
        self.embedder = embedder or OnnxEmbedder()

    def _resolve_book_osis(self, book_name_or_code: str) -> Optional[str]:
        """Normalize book name or code to canonical OSIS."""
        clean = book_name_or_code.strip()
        if not self.bible_db.exists():
            return None
        cur = self.bible_db.readonly_conn.cursor()
        cur.execute(
            "SELECT osis FROM books WHERE LOWER(osis) = LOWER(?) OR LOWER(name) = LOWER(?) LIMIT 1",
            (clean, clean),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def _get_testament_books(self, testament: str) -> set[str]:
        """Get set of OSIS codes for a testament (OT or NT)."""
        t = testament.strip().upper()
        if not self.bible_db.exists():
            return set()
        cur = self.bible_db.readonly_conn.cursor()
        cur.execute("SELECT osis FROM books WHERE testament = ?", (t,))
        return {r[0] for r in cur.fetchall()}

    def _get_reciprocal_cross_references(
        self,
        source_verse_ids: Sequence[str],
        limit: int = 50,
    ) -> list[tuple[str, int, list[str]]]:
        """Find candidate verses cross-referenced by the top search hits."""
        if not source_verse_ids or not self.bible_db.exists():
            return []

        placeholders = ",".join("?" for _ in source_verse_ids)
        cur = self.bible_db.readonly_conn.cursor()
        query = f"""
            SELECT to_verse, COUNT(DISTINCT from_verse) AS link_count,
                   GROUP_CONCAT(DISTINCT from_verse) AS sources
            FROM cross_references
            WHERE from_verse IN ({placeholders})
            GROUP BY to_verse
            ORDER BY link_count DESC, SUM(votes) DESC
            LIMIT ?
        """
        cur.execute(query, list(source_verse_ids) + [limit])
        rows = cur.fetchall()

        results = []
        for to_v, count, src_concat in rows:
            # Handle verse ranges (e.g. "Prov.8.22-Prov.8.30" -> primary verse "Prov.8.22")
            primary_v = to_v.split("-")[0].strip()
            sources = src_concat.split(",") if src_concat else []
            results.append((primary_v, count, sources))
        return results

    def _fetch_verse_details(self, verse_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        """Fetch verse text, book name, and metadata for a list of verse IDs."""
        if not verse_ids or not self.bible_db.exists():
            return {}

        placeholders = ",".join("?" for _ in verse_ids)
        cur = self.bible_db.readonly_conn.cursor()
        query = f"""
            SELECT v.id, b.name, v.osis, v.chapter, v.verse, v.text, v.clean_text, v.strongs_json
            FROM verses v
            JOIN books b ON v.osis = b.osis
            WHERE v.id IN ({placeholders})
        """
        cur.execute(query, list(verse_ids))
        details = {}
        for r in cur.fetchall():
            try:
                strongs = json.loads(r[7]) if r[7] else []
            except Exception:
                strongs = []

            details[r[0]] = {
                "verse_id": r[0],
                "book": r[1],
                "osis": r[2],
                "chapter": r[3],
                "verse": r[4],
                "text": r[5],
                "clean_text": r[6],
                "strongs": strongs,
            }
        return details

    def search(
        self,
        query: str,
        mode: str = "hybrid",
        limit: int = 20,
        book: Optional[str] = None,
        testament: Optional[str] = None,
        translation: str = "kjv",
        weights: tuple[float, float, float] = _DEFAULT_WEIGHTS,
        k_rrf: int = _DEFAULT_K_RRF,
    ) -> dict[str, Any]:
        """Perform Tri-Brid RRF search across whole-Bible Scripture."""
        t_start = time.perf_counter()
        t_embed = 0.0
        t_vector = 0.0
        t_fts = 0.0

        query_clean = query.strip()
        if not query_clean:
            return {
                "query": query,
                "mode": mode,
                "total_hits": 0,
                "hits": [],
                "timings_ms": {"total": 0.0},
            }

        # Resolve scoping constraints
        allowed_osis: Optional[set[str]] = None
        if book:
            resolved_osis = self._resolve_book_osis(book)
            if resolved_osis:
                allowed_osis = {resolved_osis}
        if testament and allowed_osis is None:
            allowed_osis = self._get_testament_books(testament)

        # -------------------------------------------------------------
        # Signal 1: Deterministic FTS5 BM25 Search
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        text_hits_raw = []
        if mode in ("hybrid", "keyword", "exact"):
            text_hits_raw = self.bible_db.search(
                query_clean,
                limit=max(limit * 2, 50),
                book=book,
                testament=testament,
                translation=translation,
            )
        t_fts = (time.perf_counter() - t0) * 1000

        text_ranks: dict[str, int] = {}
        text_scores: dict[str, float] = {}
        for rank, hit in enumerate(text_hits_raw, 1):
            vid = hit["id"]
            text_ranks[vid] = rank
            text_scores[vid] = hit.get("score", 0.0)

        # -------------------------------------------------------------
        # Signal 2: Dense Neural Vector Cosine Search
        # -------------------------------------------------------------
        vector_hits_raw: list[tuple[str, float]] = []
        if mode in ("hybrid", "thematic", "semantic") and self.vector_store.available():
            t0 = time.perf_counter()
            q_vec = self.embedder.embed(query_clean, is_query=True)
            t_embed = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            vector_hits_raw = self.vector_store.query(
                q_vec,
                top_k=max(limit * 2, 80),
                allowed_osis=allowed_osis,
            )
            t_vector = (time.perf_counter() - t0) * 1000

        semantic_ranks: dict[str, int] = {}
        semantic_scores: dict[str, float] = {}
        for rank, (vid, score) in enumerate(vector_hits_raw, 1):
            semantic_ranks[vid] = rank
            semantic_scores[vid] = score

        # -------------------------------------------------------------
        # Signal 3: TSK Reciprocal Cross-References
        # -------------------------------------------------------------
        tsk_ranks: dict[str, int] = {}
        tsk_citations: dict[str, list[str]] = {}

        if mode == "hybrid":
            # Extract unique top candidate verse IDs while preserving rank order
            candidates = list(text_ranks.keys())[:10] + list(semantic_ranks.keys())[:10]
            top_candidate_vids = list(dict.fromkeys(candidates))
            reciprocal_refs = self._get_reciprocal_cross_references(
                top_candidate_vids, limit=40
            )
            current_tsk_rank = 1
            for vid, count, sources in reciprocal_refs:
                # Filter by allowed OSIS if scoped
                if allowed_osis is not None and vid.split(".")[0] not in allowed_osis:
                    continue
                tsk_ranks[vid] = current_tsk_rank
                tsk_citations[vid] = sources
                current_tsk_rank += 1

        # -------------------------------------------------------------
        # Tri-Brid Reciprocal Rank Fusion (RRF) Blending
        # -------------------------------------------------------------
        w_text, w_sem, w_tsk = weights
        all_candidate_vids = set(text_ranks.keys()) | set(semantic_ranks.keys()) | set(tsk_ranks.keys())

        scored_candidates: list[tuple[str, float]] = []

        for vid in all_candidate_vids:
            score = 0.0
            if vid in text_ranks:
                score += w_text / (k_rrf + text_ranks[vid])
            if vid in semantic_ranks:
                score += w_sem / (k_rrf + semantic_ranks[vid])
            if vid in tsk_ranks:
                score += w_tsk / (k_rrf + tsk_ranks[vid])
            scored_candidates.append((vid, score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_candidates[:limit]
        top_vids = [vid for vid, _ in top_candidates]

        # Fetch verse metadata and format hits
        details = self._fetch_verse_details(top_vids)
        hits: list[dict[str, Any]] = []

        for vid, rrf_score in top_candidates:
            v_meta = details.get(vid)
            if not v_meta:
                continue

            t_rank = text_ranks.get(vid)
            s_rank = semantic_ranks.get(vid)
            s_score = semantic_scores.get(vid)
            tsk_r = tsk_ranks.get(vid)
            citations = tsk_citations.get(vid, [])

            # Categorize match type and generate plain-English explanation
            has_text = t_rank is not None
            has_sem = s_rank is not None
            is_high_sem = has_sem and (s_score or 0.0) >= 0.70
            has_tsk = tsk_r is not None and len(citations) >= 2

            if has_text and is_high_sem:
                m_type = "hybrid"
                m_reason = f"Keyword match (BM25 #{t_rank}) + High thematic alignment (cos: {s_score:.2f})"
            elif has_text and has_sem:
                m_type = "hybrid"
                m_reason = f"Keyword match (BM25 #{t_rank}) + Thematic parallel (cos: {s_score:.2f})"
            elif has_text:
                m_type = "exact"
                m_reason = f"Direct textual match (BM25 #{t_rank})"
            elif has_sem and has_tsk:
                m_type = "hybrid"
                sources_str = ", ".join(citations[:2])
                m_reason = f"Thematic parallel (cos: {s_score:.2f}) reinforced by TSK links from {sources_str}"
            elif has_sem:
                m_type = "semantic"
                m_reason = f"Thematic & conceptual parallel (cos: {s_score:.2f})"
            elif has_tsk:
                m_type = "cross_reference"
                sources_str = ", ".join(citations[:2])
                m_reason = f"Scriptural cross-reference connected to {sources_str}"
            else:
                m_type = "hybrid"
                m_reason = "Composite relevance match"

            hit = HybridHit(
                verse_id=vid,
                book=v_meta["book"],
                osis=v_meta["osis"],
                chapter=v_meta["chapter"],
                verse=v_meta["verse"],
                text=v_meta["text"],
                clean_text=v_meta["clean_text"],
                rrf_score=round(rrf_score, 6),
                text_rank=t_rank,
                text_score=round(text_scores.get(vid, 0.0), 4) if vid in text_scores else None,
                semantic_rank=s_rank,
                semantic_score=round(s_score, 4) if s_score is not None else None,
                tsk_rank=tsk_r,
                tsk_citations=citations,
                match_type=m_type,
                match_reason=m_reason,
                translation=translation.upper(),
                strongs=v_meta["strongs"],
            )
            hits.append(hit.to_dict())

        t_total = (time.perf_counter() - t_start) * 1000

        return {
            "query": query,
            "mode": mode,
            "total_hits": len(hits),
            "hits": hits,
            "timings_ms": {
                "embed": round(t_embed, 2),
                "vector_scan": round(t_vector, 2),
                "fts_search": round(t_fts, 2),
                "total": round(t_total, 2),
            },
        }


class EgwHybridSearchEngine:
    """Orchestrates Dual-Signal Reciprocal Rank Fusion search across Spirit of Prophecy (EGW) commentary."""

    def __init__(
        self,
        egw_db: Optional[Any] = None,
        library_vector_store: Optional[LibraryVectorStore] = None,
        embedder: Optional[OnnxEmbedder] = None,
    ) -> None:
        if egw_db is None:
            from search.linking.egw import EgwDB
            self.egw_db = EgwDB()
        else:
            self.egw_db = egw_db
        self.library_vector_store = library_vector_store or LibraryVectorStore()
        self.embedder = embedder or OnnxEmbedder()

    def search(
        self,
        query: str,
        mode: str = "hybrid",
        limit: int = 50,
        book_code: Optional[str] = None,
        weights: tuple[float, float] = _DEFAULT_EGW_WEIGHTS,
        k_rrf: int = _DEFAULT_K_RRF,
    ) -> dict[str, Any]:
        """Perform Dual-Signal RRF search across EGW commentary paragraphs."""
        t_start = time.perf_counter()
        t_embed = 0.0
        t_vector = 0.0
        t_fts = 0.0

        query_clean = query.strip()
        if not query_clean or not self.egw_db.exists():
            return {
                "query": query,
                "mode": mode,
                "total_hits": 0,
                "hits": [],
                "timings_ms": {"total": 0.0},
            }

        clean_book = book_code.strip().upper() if book_code else None

        # -------------------------------------------------------------
        # Signal 1: Deterministic FTS5 BM25 Search in egw.db
        # -------------------------------------------------------------
        text_hits_raw: list[dict[str, Any]] = []
        if mode in ("hybrid", "keyword", "exact"):
            t0 = time.perf_counter()
            text_hits_raw = self.egw_db.search(
                query=query_clean,
                book_code=clean_book,
                limit=max(limit * 2, 50),
            )
            t_fts = (time.perf_counter() - t0) * 1000

        text_ranks: dict[str, int] = {}
        text_scores: dict[str, float] = {}
        text_snippets: dict[str, str] = {}
        for rank, hit in enumerate(text_hits_raw, 1):
            pid = hit["id"]
            text_ranks[pid] = rank
            text_scores[pid] = float(hit.get("rank", 0.0))
            if hit.get("snippet"):
                text_snippets[pid] = hit["snippet"]

        # -------------------------------------------------------------
        # Signal 2: Dense Neural Vector Cosine Search in library_embeddings.db
        # -------------------------------------------------------------
        vector_hits_raw: list[tuple[str, float]] = []
        if mode in ("hybrid", "thematic", "semantic") and self.library_vector_store.available():
            t0 = time.perf_counter()
            q_vec = self.embedder.embed(query_clean, is_query=True)
            t_embed = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            allowed_books = {clean_book} if clean_book else None
            vector_hits_raw = self.library_vector_store.query(
                q_vec,
                top_k=max(limit * 2, 80),
                allowed_book_codes=allowed_books,
            )
            t_vector = (time.perf_counter() - t0) * 1000

        semantic_ranks: dict[str, int] = {}
        semantic_scores: dict[str, float] = {}
        for rank, (pid, score) in enumerate(vector_hits_raw, 1):
            semantic_ranks[pid] = rank
            semantic_scores[pid] = score

        # -------------------------------------------------------------
        # Dual-Signal Reciprocal Rank Fusion (RRF) Blending
        # -------------------------------------------------------------
        w_text, w_sem = weights
        if mode in ("thematic", "semantic"):
            w_text, w_sem = 0.2, 1.0
        elif mode in ("keyword", "exact"):
            w_text, w_sem = 1.0, 0.0

        all_candidate_pids = set(text_ranks.keys()) | set(semantic_ranks.keys())
        scored_candidates: list[tuple[str, float]] = []

        for pid in all_candidate_pids:
            score = 0.0
            if pid in text_ranks:
                score += w_text / (k_rrf + text_ranks[pid])
            if pid in semantic_ranks:
                score += w_sem / (k_rrf + semantic_ranks[pid])
            scored_candidates.append((pid, score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_candidates[:limit]
        top_pids = [pid for pid, _ in top_candidates]

        # Fetch paragraph details in batch from egw.db
        details = self.egw_db.get_paragraphs_batch(top_pids)
        hits: list[dict[str, Any]] = []

        for pid, rrf_score in top_candidates:
            p = details.get(pid)
            if not p:
                continue

            t_rank = text_ranks.get(pid)
            s_rank = semantic_ranks.get(pid)
            s_score = semantic_scores.get(pid)

            has_text = t_rank is not None
            has_sem = s_rank is not None
            is_high_sem = has_sem and (s_score or 0.0) >= 0.70

            if has_text and is_high_sem:
                m_type = "hybrid"
                m_reason = f"Keyword match (BM25 #{t_rank}) + High thematic alignment (cos: {s_score:.2f})"
            elif has_text and has_sem:
                m_type = "hybrid"
                m_reason = f"Keyword match (BM25 #{t_rank}) + Thematic parallel (cos: {s_score:.2f})"
            elif has_text:
                m_type = "exact"
                m_reason = f"Direct textual match (BM25 #{t_rank})"
            elif has_sem:
                m_type = "semantic"
                m_reason = f"Thematic & conceptual parallel (cos: {s_score:.2f})"
            else:
                m_type = "hybrid"
                m_reason = "Composite relevance match"

            # Snippet: use BM25 highlighted snippet if available, else first ~180 chars of text
            snippet = text_snippets.get(pid)
            if not snippet:
                full_text = p.get("text", "")
                snippet = full_text[:180] + ("…" if len(full_text) > 180 else "")

            hit = EgwHybridHit(
                paragraph_id=pid,
                book_code=p.get("book_code", ""),
                book_title=p.get("book_title") or p.get("book_code", ""),
                chapter_num=p.get("chapter_num"),
                chapter_title=p.get("chapter_title"),
                page=p.get("page", 1),
                paragraph=p.get("paragraph", 1),
                ref_code=p.get("ref_code") or f"{p.get('book_code', '')} {p.get('page', 1)}.{p.get('paragraph', 1)}",
                text=p.get("text", ""),
                snippet=snippet,
                rrf_score=round(rrf_score, 6),
                text_rank=t_rank,
                text_score=round(text_scores.get(pid, 0.0), 4) if pid in text_scores else None,
                semantic_rank=s_rank,
                semantic_score=round(s_score, 4) if s_score is not None else None,
                match_type=m_type,
                match_reason=m_reason,
            )
            hits.append(hit.to_dict())

        t_total = (time.perf_counter() - t_start) * 1000

        return {
            "query": query,
            "mode": mode,
            "total_hits": len(hits),
            "hits": hits,
            "timings_ms": {
                "embed": round(t_embed, 2),
                "vector_scan": round(t_vector, 2),
                "fts_search": round(t_fts, 2),
                "total": round(t_total, 2),
            },
        }
