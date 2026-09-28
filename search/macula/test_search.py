"""Unit tests for Macula lexical and semantic search engine (WP-039)."""

import sqlite3
import unittest
from pathlib import Path

from search.macula.search import (
    MaculaSearchEngine,
    normalize_strongs,
    strip_diacritics,
)


class TestMaculaSearchHelpers(unittest.TestCase):
    """Test string and Strong's code normalizers."""

    def test_strip_diacritics_hebrew(self):
        # Pointed vs unpointed reshit
        pointed = "רֵאשִׁית"
        unpointed = "ראשית"
        self.assertEqual(strip_diacritics(pointed), unpointed)

    def test_strip_diacritics_greek(self):
        # Accented vs unaccented arche
        accented = "ἀρχῇ"
        unaccented = "αρχη"
        self.assertEqual(strip_diacritics(accented), unaccented)

    def test_normalize_strongs(self):
        self.assertEqual(normalize_strongs("H7225"), "H7225")
        self.assertEqual(normalize_strongs("h07225"), "H7225")
        self.assertEqual(normalize_strongs("G746"), "G746")
        self.assertEqual(normalize_strongs("g00746"), "G746")
        self.assertIsNone(normalize_strongs("invalid"))
        self.assertIsNone(normalize_strongs("7225"))


class TestMaculaSearchEngine(unittest.TestCase):
    """Test MaculaSearchEngine queries across macula.db and lexicons."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.engine = MaculaSearchEngine()
            _ = cls.engine.conn
        except (FileNotFoundError, sqlite3.OperationalError):
            raise unittest.SkipTest("data/macula.db not present; skipping Macula search tests.")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "engine"):
            cls.engine.close()

    def test_search_strongs_hebrew_h7225(self):
        hit = self.engine.search_strongs("H7225")
        self.assertIsNotNone(hit)
        self.assertEqual(hit.strongs, "H7225")
        self.assertEqual(hit.language, "hebrew")
        self.assertEqual(hit.translit, "ray-sheeth'")
        self.assertGreater(hit.occurrences, 0)
        self.assertGreater(len(hit.sample_verses), 0)
        self.assertIn("beginning", [g.lower() for g in hit.glosses])

    def test_search_strongs_greek_g746(self):
        hit = self.engine.search_strongs("G746")
        self.assertIsNotNone(hit)
        self.assertEqual(hit.strongs, "G746")
        self.assertEqual(hit.language, "greek")
        self.assertEqual(hit.lemma, "ἀρχή")
        self.assertEqual(hit.translit, "ar-khay'")
        self.assertGreater(hit.occurrences, 0)
        self.assertGreater(len(hit.sample_verses), 0)

    def test_search_lemma_hebrew_pointed_and_unpointed(self):
        hits_pointed = self.engine.search_lemma("רֵאשִׁית", limit=5)
        self.assertGreater(len(hits_pointed), 0)
        self.assertEqual(hits_pointed[0].strongs, "H7225")

        hits_unpointed = self.engine.search_lemma("ראשית", limit=5)
        self.assertGreater(len(hits_unpointed), 0)
        self.assertEqual(hits_unpointed[0].strongs, "H7225")

    def test_search_lemma_greek_accented_and_unaccented(self):
        hits_accented = self.engine.search_lemma("ἀρχή", limit=5)
        self.assertGreater(len(hits_accented), 0)
        self.assertEqual(hits_accented[0].strongs, "G746")

        hits_unaccented = self.engine.search_lemma("αρχη", limit=5)
        self.assertGreater(len(hits_unaccented), 0)
        self.assertEqual(hits_unaccented[0].strongs, "G746")

    def test_search_transliteration(self):
        hits = self.engine.search("logos", limit=5)
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].strongs, "G3056")
        self.assertEqual(hits[0].lemma, "λόγος")

    def test_search_english_concept_covenant(self):
        hits = self.engine.search("covenant", limit=10)
        self.assertGreater(len(hits), 0)
        strongs_codes = [h.strongs for h in hits]
        # Must discover Hebrew berith (H1285) and Greek diatheke (G1242)
        self.assertIn("H1285", strongs_codes)
        self.assertIn("G1242", strongs_codes)

    def test_search_english_concept_sanctuary(self):
        hits = self.engine.search("sanctuary", limit=10)
        self.assertGreater(len(hits), 0)
        strongs_codes = [h.strongs for h in hits]
        # Must discover Hebrew miqdash (H4720) or qodesh (H6944)
        self.assertTrue("H4720" in strongs_codes or "H6944" in strongs_codes)

    def test_search_semantic_domain(self):
        # Louw-Nida Domain 67.65 (Time / Beginning)
        hits = self.engine.search_domain("67.65", limit=5)
        self.assertGreater(len(hits), 0)
        self.assertTrue(any(h.strongs == "G746" for h in hits))

    def test_empty_query_returns_empty_list(self):
        self.assertEqual(self.engine.search(""), [])
        self.assertEqual(self.engine.search("   "), [])


if __name__ == "__main__":
    unittest.main()
