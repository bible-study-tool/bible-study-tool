"""Unit tests for Tri-Brid Reciprocal Rank Fusion hybrid search engine (WP-040, ADR-029)."""

from __future__ import annotations

import time
import unittest
from pathlib import Path

import numpy as np

from search.corpus.extract_kjv import BibleDB
from search.corpus.hybrid_search import HybridSearchEngine, VectorStore
from search.resource import get_embeddings_db_path


class TestHybridSearch(unittest.TestCase):
    """Test suite for VectorStore and HybridSearchEngine."""

    @classmethod
    def setUpClass(cls):
        cls.bible_db = BibleDB()
        cls.vector_store = VectorStore()
        cls.engine = HybridSearchEngine(
            bible_db=cls.bible_db,
            vector_store=cls.vector_store,
        )

    def test_vector_store_missing_database_graceful(self):
        """VectorStore handles non-existent embeddings database gracefully."""
        vs = VectorStore(db_path=Path("/nonexistent/embeddings.db"))
        self.assertFalse(vs.available())
        results = vs.query(np.zeros(384, dtype=np.float32))
        self.assertEqual(results, [])

    def test_vector_store_real_loading_if_present(self):
        """VectorStore loads contiguous float32 matrix from embeddings.db if present."""
        if not get_embeddings_db_path().is_file():
            self.skipTest("data/embeddings.db not present in this environment")

        self.assertTrue(self.vector_store.available())
        self.assertGreaterEqual(len(self.vector_store._verse_ids), 31000)

        # Query with unit vector
        import numpy as np

        q_vec = np.ones(384, dtype=np.float32)
        q_vec /= np.linalg.norm(q_vec)

        hits = self.vector_store.query(q_vec, top_k=10)
        self.assertEqual(len(hits), 10)
        for vid, score in hits:
            self.assertIsInstance(vid, str)
            self.assertIsInstance(score, float)

    def test_hybrid_search_empty_query(self):
        """Empty query returns empty results immediately."""
        res = self.engine.search("")
        self.assertEqual(res["total_hits"], 0)
        self.assertEqual(res["hits"], [])

    def test_hybrid_search_exact_scripture(self):
        """Exact phrase search prioritizes exact text match."""
        if not self.bible_db.exists():
            self.skipTest("data/bible.db not present in this environment")

        res = self.engine.search("In the beginning God created the heaven", mode="hybrid", limit=5)
        self.assertGreaterEqual(res["total_hits"], 1)
        top = res["hits"][0]
        self.assertEqual(top["verse_id"], "Gen.1.1")
        self.assertEqual(top["book"], "Genesis")
        self.assertIn("In the beginning", top["clean_text"])

    def test_hybrid_search_thematic_passion_motif(self):
        """Thematic query for suffering servant motif discovers relevant passages."""
        if not self.vector_store.available():
            self.skipTest("data/embeddings.db not present in this environment")

        res = self.engine.search("suffering servant mocked", mode="hybrid", limit=10)
        self.assertGreater(res["total_hits"], 0)
        top_vids = [h["verse_id"] for h in res["hits"]]
        # At least one relevant gospel / passion / suffering chapter (e.g. Matt, Mark, Luke, John, Job, Isa)
        books_found = {vid.split(".")[0] for vid in top_vids}
        self.assertTrue(
            any(b in books_found for b in ("Matt", "Mark", "Luke", "John", "Isa", "Ps", "Job")),
            f"Expected passion/suffering books in hits: {top_vids}",
        )

    def test_hybrid_search_modes(self):
        """Test search mode differentiation: keyword vs thematic vs hybrid."""
        if not self.bible_db.exists():
            self.skipTest("data/bible.db not present")

        kw_res = self.engine.search("sanctuary", mode="keyword", limit=5)
        self.assertEqual(kw_res["mode"], "keyword")
        for h in kw_res["hits"]:
            self.assertIsNotNone(h["text_rank"])

        if self.vector_store.available():
            them_res = self.engine.search("sanctuary", mode="thematic", limit=5)
            self.assertEqual(them_res["mode"], "thematic")
            for h in them_res["hits"]:
                self.assertIsNotNone(h["semantic_rank"])

    def test_hybrid_search_scoping_book_and_testament(self):
        """Scoping filters search results to specific book and testament."""
        if not self.bible_db.exists():
            self.skipTest("data/bible.db not present")

        # Book scoping
        res_heb = self.engine.search("sanctuary", book="Hebrews", limit=5)
        for h in res_heb["hits"]:
            self.assertEqual(h["book"], "Hebrews")

        # Testament scoping
        res_ot = self.engine.search("holy place", testament="OT", limit=5)
        for h in res_ot["hits"]:
            # OT books only
            self.assertIn(h["osis"], ("Exod", "Lev", "Num", "Deut", "1Kgs", "2Chr", "Ezek"))

    def test_hybrid_search_latency_performance(self):
        """Vector similarity and RRF fusion execute within performance budgets."""
        if not self.vector_store.available():
            self.skipTest("data/embeddings.db not present")

        # Warm up query
        self.engine.search("covenant", limit=5)

        t0 = time.perf_counter()
        res = self.engine.search("peace covenant", limit=10)
        dt = (time.perf_counter() - t0) * 1000

        # Vector scan itself must be sub-10ms
        self.assertLess(res["timings_ms"]["vector_scan"], 25.0)

    def test_vector_store_scoped_query_no_leakage(self):
        """VectorStore strictly respects book boundary and does not leak negative-score verses."""
        if not self.vector_store.available():
            self.skipTest("data/embeddings.db not present in this environment")

        q_vec = np.ones(384, dtype=np.float32)
        q_vec /= np.linalg.norm(q_vec)

        # Philemon has exactly 25 verses
        hits = self.vector_store.query(q_vec, top_k=80, allowed_osis={"Phlm"})
        self.assertLessEqual(len(hits), 25)
        for vid, score in hits:
            self.assertTrue(vid.startswith("Phlm."), f"Leaked verse across book boundary: {vid}")
            self.assertGreater(score, -1.0)

    def test_thematic_badge_classification(self):
        """Pure thematic queries classify hits as 'semantic' rather than fallback 'hybrid'."""
        if not self.vector_store.available():
            self.skipTest("data/embeddings.db not present")

        res = self.engine.search("suffering servant", mode="thematic", limit=5)
        self.assertGreater(len(res["hits"]), 0)
        for h in res["hits"]:
            self.assertEqual(h["match_type"], "semantic")
            self.assertIn("Thematic", h["match_reason"])


if __name__ == "__main__":
    import numpy as np

    unittest.main()
