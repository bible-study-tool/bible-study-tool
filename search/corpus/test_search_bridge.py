"""Unit tests for DeterministicSearchBridge and advanced search syntax parser (WP-039)."""

import unittest

from search.corpus.search_bridge import (
    DeterministicSearchBridge,
    normalize_bm25_score,
    parse_search_query,
)


class TestSearchSyntaxParser(unittest.TestCase):
    """Test fine-grained query syntax parser and reference detection."""

    def test_empty_query(self):
        p = parse_search_query("")
        self.assertEqual(p.clean_text, "")
        self.assertFalse(p.is_reference)
        self.assertIsNone(p.book)

        p_spaces = parse_search_query("   ")
        self.assertEqual(p_spaces.clean_text, "")
        self.assertFalse(p_spaces.is_reference)

    def test_pure_text_query(self):
        p = parse_search_query("sanctuary")
        self.assertEqual(p.clean_text, "sanctuary")
        self.assertFalse(p.is_reference)
        self.assertIsNone(p.book)
        self.assertIsNone(p.testament)

    def test_scripture_reference_detection(self):
        # Verse reference
        p1 = parse_search_query("John 3:16")
        self.assertTrue(p1.is_reference)
        self.assertIsNotNone(p1.reference_target)
        self.assertEqual(p1.reference_target["osis"], "John")
        self.assertEqual(p1.reference_target["chapter"], 3)
        self.assertEqual(p1.reference_target["start_verse"], 16)

        # Verse range reference
        p2 = parse_search_query("Gen 1:1-3")
        self.assertTrue(p2.is_reference)
        self.assertEqual(p2.reference_target["osis"], "Gen")
        self.assertEqual(p2.reference_target["chapter"], 1)
        self.assertEqual(p2.reference_target["start_verse"], 1)
        self.assertEqual(p2.reference_target["end_verse"], 3)

        # Non-reference keyword query
        p3 = parse_search_query("righteousness by faith")
        self.assertFalse(p3.is_reference)
        self.assertIsNone(p3.reference_target)

    def test_strongs_detection(self):
        p = parse_search_query("H7225")
        self.assertEqual(p.strongs, "H7225")

        p_lower = parse_search_query("g3056")
        self.assertEqual(p_lower.strongs, "G3056")

    def test_operator_parsing(self):
        query = 'covenant book:Genesis testament:OT translation:asv strong:H1285 domain:67.65 egw:PP'
        p = parse_search_query(query)
        self.assertEqual(p.clean_text, "covenant")
        self.assertEqual(p.book, "Gen")
        self.assertEqual(p.testament, "OT")
        self.assertEqual(p.translation, "asv")
        self.assertEqual(p.strongs, "H1285")
        self.assertEqual(p.domain, "67.65")
        self.assertEqual(p.egw_book, "PP")

    def test_abbreviated_operators(self):
        query = 'sanctuary b:Heb t:NT tr:bsb s:G39 egw:GC'
        p = parse_search_query(query)
        self.assertEqual(p.clean_text, "sanctuary")
        self.assertEqual(p.book, "Heb")
        self.assertEqual(p.testament, "NT")
        self.assertEqual(p.translation, "bsb")
        self.assertEqual(p.strongs, "G39")
        self.assertEqual(p.egw_book, "GC")

    def test_quoted_exact_phrases(self):
        query = '"holy place" book:Exodus'
        p = parse_search_query(query)
        self.assertIn('"holy place"', p.clean_text)
        self.assertEqual(p.exact_phrases, ["holy place"])
        self.assertEqual(p.book, "Exod")


class TestScoreNormalization(unittest.TestCase):
    """Test BM25 rank to [0.0, 1.0] sigmoid normalization."""

    def test_bm25_monotonicity(self):
        # More negative is better in SQLite FTS5 bm25()
        score_high = normalize_bm25_score(-16.0)
        score_mid = normalize_bm25_score(-8.0)
        score_low = normalize_bm25_score(-2.0)
        score_zero = normalize_bm25_score(0.0)

        self.assertGreater(score_high, score_mid)
        self.assertGreater(score_mid, score_low)
        self.assertGreater(score_low, score_zero)
        self.assertEqual(score_zero, 0.5)
        self.assertGreater(score_high, 0.90)


class TestDeterministicSearchBridge(unittest.TestCase):
    """Test unified multi-database search and query expansion."""

    @classmethod
    def setUpClass(cls):
        cls.bridge = DeterministicSearchBridge()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "bridge"):
            cls.bridge.close()

    def test_expand_query_english_covenant(self):
        from search.macula.search import strip_diacritics
        exp = self.bridge.expand_query("covenant")
        self.assertEqual(exp["term"], "covenant")
        self.assertIn("H1285", exp["strongs"])
        self.assertIn("G1242", exp["strongs"])
        stripped_lemmas = [strip_diacritics(item["lemma"]) for item in exp["lemmas"]]
        self.assertTrue(any("ברית" in l for l in stripped_lemmas))
        self.assertTrue(any("διαθηκη" in l for l in stripped_lemmas))

    def test_expand_query_strongs_h7225(self):
        exp = self.bridge.expand_query("H7225")
        self.assertIn("H7225", exp["strongs"])
        # Should include LXX alignments (e.g. G746 arche)
        self.assertTrue(len(exp["lxx_aligned"]) > 0 or len(exp["lemmas"]) > 0)

    def test_search_all_sources(self):
        res = self.bridge.search("beginning", limit=20)
        self.assertGreater(res["total_hits"], 0)
        self.assertIn("counts", res)
        self.assertIn("all", res["counts"])
        self.assertIn("scripture", res["counts"])
        self.assertIn("translations", res["counts"])
        self.assertIn("original", res["counts"])
        self.assertIn("commentary", res["counts"])
        self.assertIn("curated", res["counts"])
        self.assertGreater(res["counts"]["scripture"], 0)
        self.assertGreater(res["counts"]["original"], 0)

        # Verify hits structure
        for hit in res["results"]:
            self.assertIn(hit["source"], ("scripture", "translations", "original", "commentary", "curated"))
            self.assertTrue(len(hit["id"]) > 0)
            self.assertTrue(len(hit["title"]) > 0)
            self.assertTrue(len(hit["snippet"]) > 0)
            self.assertGreaterEqual(hit["score"], 0.0)
            self.assertLessEqual(hit["score"], 1.0)

    def test_search_scoped_by_book_operator(self):
        res = self.bridge.search("beginning book:Genesis", limit=10)
        self.assertGreater(res["total_hits"], 0)
        for hit in res["results"]:
            if hit["source"] == "scripture":
                self.assertEqual(hit["metadata"]["osis"], "Gen")

    def test_search_scoped_by_source_filter(self):
        # Only original languages
        res_orig = self.bridge.search("logos", sources=["original"], limit=5)
        self.assertGreater(len(res_orig["results"]), 0)
        self.assertTrue(all(h["source"] == "original" for h in res_orig["results"]))

        # Only commentary
        res_comm = self.bridge.search("faith", sources=["commentary"], limit=5)
        if res_comm["results"]:
            self.assertTrue(all(h["source"] == "commentary" for h in res_comm["results"]))


if __name__ == "__main__":
    unittest.main()
