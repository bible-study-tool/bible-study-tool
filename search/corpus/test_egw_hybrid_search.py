"""Unit tests for Spirit of Prophecy (EGW) Hybrid Search & LibraryVectorStore (WP-043)."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from search.corpus.hybrid_search import (
    EgwHybridHit,
    EgwHybridSearchEngine,
    LibraryVectorStore,
)
from search.corpus.search_bridge import DeterministicSearchBridge, SearchHit
from search.linking.egw import EgwDB
from search.resource import get_library_embeddings_db_path


class TestLibraryVectorStore(unittest.TestCase):
    """Test suite for LibraryVectorStore lifecycle, scoping, and vector operations."""

    def test_missing_database_graceful(self):
        """LibraryVectorStore handles non-existent database file gracefully."""
        lvs = LibraryVectorStore(db_path=Path("/nonexistent/library_embeddings.db"))
        self.assertFalse(lvs.available())
        results = lvs.query(np.zeros(384, dtype=np.float32))
        self.assertEqual(results, [])

    def test_empty_database_graceful(self):
        """LibraryVectorStore handles empty database gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            conn = sqlite3.connect(tmp.name)
            conn.execute(
                "CREATE TABLE paragraphs (paragraph_id TEXT PRIMARY KEY, book_code TEXT, vector BLOB, magnitude REAL);"
            )
            conn.commit()
            conn.close()

            lvs = LibraryVectorStore(db_path=Path(tmp.name))
            self.assertFalse(lvs.available())
            self.assertEqual(lvs.query(np.zeros(384, dtype=np.float32)), [])

    def test_mock_database_scoping_and_cosine(self):
        """LibraryVectorStore accurately indexes book codes and computes cosine similarity."""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            conn = sqlite3.connect(tmp.name)
            conn.execute(
                "CREATE TABLE paragraphs (paragraph_id TEXT PRIMARY KEY, book_code TEXT, vector BLOB, magnitude REAL);"
            )

            # Insert 3 unit vectors
            v1 = np.zeros(384, dtype=np.float32)
            v1[0] = 1.0  # Exact match for query on dim 0
            v2 = np.zeros(384, dtype=np.float32)
            v2[0] = 0.6
            v2[1] = 0.8  # Partial match
            v3 = np.zeros(384, dtype=np.float32)
            v3[2] = 1.0  # Orthogonal match

            conn.execute("INSERT INTO paragraphs VALUES ('DA.1.1', 'DA', ?, 1.0);", (v1.tobytes(),))
            conn.execute("INSERT INTO paragraphs VALUES ('PP.1.1', 'PP', ?, 1.0);", (v2.tobytes(),))
            conn.execute("INSERT INTO paragraphs VALUES ('DA.2.1', 'DA', ?, 1.0);", (v3.tobytes(),))
            conn.commit()
            conn.close()

            lvs = LibraryVectorStore(db_path=Path(tmp.name))
            self.assertTrue(lvs.available())

            # Query with unit vector on dim 0
            q_vec = np.zeros(384, dtype=np.float32)
            q_vec[0] = 1.0

            # Global query
            hits = lvs.query(q_vec, top_k=10)
            self.assertEqual(len(hits), 3)
            self.assertEqual(hits[0][0], "DA.1.1")
            self.assertAlmostEqual(hits[0][1], 1.0, places=4)
            self.assertEqual(hits[1][0], "PP.1.1")
            self.assertAlmostEqual(hits[1][1], 0.6, places=4)
            self.assertEqual(hits[2][0], "DA.2.1")
            self.assertAlmostEqual(hits[2][1], 0.0, places=4)

            # Scoped query: only PP
            pp_hits = lvs.query(q_vec, top_k=10, allowed_book_codes={"PP"})
            self.assertEqual(len(pp_hits), 1)
            self.assertEqual(pp_hits[0][0], "PP.1.1")

            # Scoped query: only DA
            da_hits = lvs.query(q_vec, top_k=10, allowed_book_codes={"DA"})
            self.assertEqual(len(da_hits), 2)
            self.assertEqual(da_hits[0][0], "DA.1.1")

            # Empty book scoping set must return 0 hits (no leakage)
            empty_hits = lvs.query(q_vec, top_k=10, allowed_book_codes=set())
            self.assertEqual(empty_hits, [])

            # Unknown book code must return 0 hits
            unknown_hits = lvs.query(q_vec, top_k=10, allowed_book_codes={"UNKNOWN"})
            self.assertEqual(unknown_hits, [])

            # Test reload()
            self.assertTrue(lvs.reload())

    def test_live_database_if_present(self):
        """LibraryVectorStore loads real library_embeddings.db when present in repo."""
        db_path = get_library_embeddings_db_path()
        if not db_path.is_file():
            self.skipTest("data/library_embeddings.db not present in this environment")

        lvs = LibraryVectorStore()
        self.assertTrue(lvs.available())
        q_vec = np.zeros(384, dtype=np.float32)
        q_vec[0] = 1.0
        hits = lvs.query(q_vec, top_k=5, allowed_book_codes={"GC"})
        self.assertGreater(len(hits), 0)
        self.assertTrue(hits[0][0].startswith("GC."))


class TestEgwDBBatchLookup(unittest.TestCase):
    """Test suite for EgwDB.get_paragraphs_batch."""

    def test_get_paragraphs_batch_empty(self):
        """Empty input returns empty dictionary."""
        db = EgwDB()
        self.assertEqual(db.get_paragraphs_batch([]), {})

    def test_get_paragraphs_batch_live(self):
        """Batch lookup retrieves paragraphs accessible by both canonical ID and input token key."""
        db = EgwDB()
        if not db.exists():
            self.skipTest("data/egw.db not installed")

        tokens = ["egw:PP.44.1", "GC.422.1", "nonexistent.999.1"]
        res = db.get_paragraphs_batch(tokens)
        self.assertIn("PP.44.1", res)
        self.assertIn("egw:PP.44.1", res)  # Preserves token alias
        self.assertIn("GC.422.1", res)
        self.assertNotIn("nonexistent.999.1", res)
        self.assertEqual(res["PP.44.1"]["book_code"], "PP")
        self.assertEqual(res["egw:PP.44.1"]["book_code"], "PP")
        self.assertEqual(res["GC.422.1"]["book_code"], "GC")


class TestEgwHybridSearchEngine(unittest.TestCase):
    """Test suite for Dual-Signal Reciprocal Rank Fusion search on EGW writings."""

    def test_empty_query(self):
        """Empty query returns empty hits cleanly."""
        engine = EgwHybridSearchEngine()
        res = engine.search("   ")
        self.assertEqual(res["total_hits"], 0)
        self.assertEqual(res["hits"], [])

    def test_search_mode_keyword(self):
        """Keyword mode only queries BM25 and does not query vector store."""
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_db.search.return_value = [{"id": "GC.1.1", "rank": -5.0}]
        mock_db.get_paragraphs_batch.return_value = {
            "GC.1.1": {"id": "GC.1.1", "book_code": "GC", "book_title": "Great Controversy", "page": 1, "paragraph": 1, "text": "text", "ref_code": "GC 1.1"}
        }
        mock_lvs = MagicMock()
        mock_lvs.available.return_value = True

        engine = EgwHybridSearchEngine(egw_db=mock_db, library_vector_store=mock_lvs)
        res = engine.search("sanctuary", mode="keyword")
        self.assertEqual(res["total_hits"], 1)
        mock_lvs.query.assert_not_called()

    def test_search_mode_thematic(self):
        """Thematic mode queries vector store and weights semantic ranking heavily."""
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_db.search.return_value = []
        mock_db.get_paragraphs_batch.return_value = {
            "DA.1.1": {"id": "DA.1.1", "book_code": "DA", "book_title": "Desire of Ages", "page": 1, "paragraph": 1, "text": "text", "ref_code": "DA 1.1"}
        }
        mock_lvs = MagicMock()
        mock_lvs.available.return_value = True
        mock_lvs.query.return_value = [("DA.1.1", 0.91)]
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = np.zeros(384, dtype=np.float32)

        engine = EgwHybridSearchEngine(egw_db=mock_db, library_vector_store=mock_lvs, embedder=mock_embedder)
        res = engine.search("weeping", mode="thematic")
        self.assertEqual(res["total_hits"], 1)
        self.assertEqual(res["hits"][0]["match_type"], "semantic")

    def test_nonexistent_egw_db(self):
        """Search degrades gracefully when egw.db is missing."""
        mock_db = MagicMock()
        mock_db.exists.return_value = False
        engine = EgwHybridSearchEngine(egw_db=mock_db)
        res = engine.search("sanctuary")
        self.assertEqual(res["total_hits"], 0)
        self.assertEqual(res["hits"], [])

    def test_dual_signal_rrf_blending(self):
        """Verifies RRF scoring, ranking, and match badging logic."""
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_db.search.return_value = [
            {"id": "GC.1.1", "rank": -10.5, "snippet": "Keyword hit [b]sanctuary[/b]"},
            {"id": "PP.1.1", "rank": -5.2, "snippet": "Second keyword hit"},
        ]
        mock_db.get_paragraphs_batch.return_value = {
            "GC.1.1": {
                "id": "GC.1.1",
                "book_code": "GC",
                "book_title": "The Great Controversy",
                "page": 1,
                "paragraph": 1,
                "text": "Full text of GC 1.1",
                "ref_code": "GC 1.1",
            },
            "PP.1.1": {
                "id": "PP.1.1",
                "book_code": "PP",
                "book_title": "Patriarchs and Prophets",
                "page": 1,
                "paragraph": 1,
                "text": "Full text of PP 1.1",
                "ref_code": "PP 1.1",
            },
            "DA.1.1": {
                "id": "DA.1.1",
                "book_code": "DA",
                "book_title": "The Desire of Ages",
                "page": 1,
                "paragraph": 1,
                "text": "Full text of DA 1.1 (thematic only)",
                "ref_code": "DA 1.1",
            },
        }

        mock_lvs = MagicMock()
        mock_lvs.available.return_value = True
        # Vector search yields DA.1.1 (pure semantic) and GC.1.1 (hybrid)
        mock_lvs.query.return_value = [
            ("GC.1.1", 0.88),
            ("DA.1.1", 0.82),
        ]

        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = np.zeros(384, dtype=np.float32)

        engine = EgwHybridSearchEngine(
            egw_db=mock_db,
            library_vector_store=mock_lvs,
            embedder=mock_embedder,
        )

        res = engine.search("sanctuary truth", mode="hybrid", limit=10)
        hits = res["hits"]
        self.assertEqual(len(hits), 3)

        # GC.1.1 appeared in both text (#1) and semantic (#1) -> highest RRF score
        self.assertEqual(hits[0]["paragraph_id"], "GC.1.1")
        self.assertEqual(hits[0]["match_type"], "hybrid")
        self.assertIn("Keyword match (BM25 #1) + High thematic alignment", hits[0]["match_reason"])
        self.assertEqual(hits[0]["snippet"], "Keyword hit [b]sanctuary[/b]")

        # DA.1.1 appeared only in semantic (#2)
        da_hit = next(h for h in hits if h["paragraph_id"] == "DA.1.1")
        self.assertEqual(da_hit["match_type"], "semantic")
        self.assertIn("Thematic & conceptual parallel", da_hit["match_reason"])

        # PP.1.1 appeared only in text (#2)
        pp_hit = next(h for h in hits if h["paragraph_id"] == "PP.1.1")
        self.assertEqual(pp_hit["match_type"], "exact")
        self.assertIn("Direct textual match", pp_hit["match_reason"])


class TestDeterministicSearchBridgeCommentary(unittest.TestCase):
    """Test suite for DeterministicSearchBridge commentary routing and resilience."""

    def test_commentary_search_when_library_embeddings_missing(self):
        """SearchBridge falls back to BM25 when library embeddings are absent."""
        with patch("search.corpus.hybrid_search.get_library_embeddings_db_path", return_value=Path("/nonexistent/lib.db")):
            bridge = DeterministicSearchBridge()
            if not bridge.egw_db.exists():
                self.skipTest("data/egw.db not installed")

            res = bridge.search("covenant", sources=["commentary"], mode="hybrid", limit=5)
            self.assertGreater(res["counts"]["commentary"], 0)
            hit = res["results"][0]
            self.assertEqual(hit["source"], "commentary")
            self.assertEqual(hit["metadata"]["match_type"], "exact")

    def test_commentary_search_when_egw_missing_scripture_unaffected(self):
        """Scripture search works 100% normally when egw.db is missing."""
        mock_egw = MagicMock()
        mock_egw.exists.return_value = False
        mock_egw.close.return_value = None

        bridge = DeterministicSearchBridge(egw_db=mock_egw)
        res = bridge.search("grace", sources="all", mode="hybrid", limit=5)
        self.assertGreater(res["counts"]["scripture"], 0)
        self.assertEqual(res["counts"]["commentary"], 0)

    def test_commentary_search_live_hybrid_when_present(self):
        """SearchBridge surfaces hybrid match badges when library_embeddings.db is present."""
        if not get_library_embeddings_db_path().is_file():
            self.skipTest("data/library_embeddings.db not present")
        bridge = DeterministicSearchBridge()
        if not bridge.egw_db.exists():
            self.skipTest("data/egw.db not installed")

        res = bridge.search("sanctuary cleansed", sources=["commentary"], mode="hybrid", limit=3)
        self.assertGreater(res["counts"]["commentary"], 0)
        top = res["results"][0]
        self.assertEqual(top["source"], "commentary")
        self.assertIn(top["metadata"]["match_type"], ("hybrid", "exact", "semantic"))
        self.assertIn("match_reason", top["metadata"])
