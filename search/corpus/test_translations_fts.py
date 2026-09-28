"""Unit tests for multi-translation FTS search and query formatting (WP-039)."""

import sqlite3
import unittest
from pathlib import Path

from search.corpus.extract_kjv import BibleDB, prepare_fts_query


class TestPrepareFtsQuery(unittest.TestCase):
    """Test FTS5 query formatting and sanitization."""

    def test_plain_words(self):
        self.assertEqual(prepare_fts_query("covenant sanctuary"), '"covenant" "sanctuary"')

    def test_quoted_phrase(self):
        self.assertEqual(prepare_fts_query('"in the beginning"'), '"in the beginning"')

    def test_mixed_phrase_and_terms(self):
        res = prepare_fts_query('"holy place" sanctuary')
        self.assertEqual(res, '"holy place" "sanctuary"')

    def test_boolean_operators(self):
        self.assertEqual(prepare_fts_query("light AND darkness"), '"light" AND "darkness"')
        self.assertEqual(prepare_fts_query("sanctuary OR tabernacle"), '"sanctuary" OR "tabernacle"')
        self.assertEqual(prepare_fts_query("grace NOT law"), '"grace" NOT "law"')

    def test_strip_stray_operators(self):
        self.assertEqual(prepare_fts_query("AND sanctuary AND"), '"sanctuary"')
        self.assertEqual(prepare_fts_query("OR"), "")

    def test_special_characters_sanitized(self):
        self.assertEqual(prepare_fts_query("God! (Father)"), '"God" "Father"')
        self.assertEqual(prepare_fts_query("   "), "")

    def test_lowercase_natural_language_not(self):
        self.assertEqual(prepare_fts_query("fear not"), '"fear" "not"')
        self.assertEqual(prepare_fts_query("thou shalt not kill"), '"thou" "shalt" "not" "kill"')

    def test_hyphenated_and_possessive_terms(self):
        self.assertEqual(prepare_fts_query("ark-covenant"), '"ark" "covenant"')
        self.assertEqual(prepare_fts_query("Aaron's rod"), '"Aaron" "s" "rod"')


class TestMultiTranslationSearch(unittest.TestCase):
    """Test searching across KJV, ASV, BSB, and YLT via BibleDB."""

    @classmethod
    def setUpClass(cls):
        cls.db = BibleDB()
        if not cls.db.exists():
            raise unittest.SkipTest("data/bible.db not present; skipping multi-translation tests.")
        cls.db.ensure_translations_fts()

    def test_translations_fts_table_exists(self):
        self.assertTrue(self.db._has_translations_fts())

    def test_search_kjv_default(self):
        hits = self.db.search("sanctuary", limit=5)
        self.assertGreater(len(hits), 0)
        for h in hits:
            self.assertEqual(h["translation_id"], "kjv")
            self.assertEqual(h["translation_name"], "King James Version")
            self.assertIn("strongs", h)
            self.assertIn("tokens", h)

    def test_search_specific_translation_bsb(self):
        hits = self.db.search("light", translation="bsb", limit=5)
        self.assertGreater(len(hits), 0)
        for h in hits:
            self.assertEqual(h["translation_id"], "bsb")
            self.assertEqual(h["translation_name"], "Berean Standard Bible")

    def test_search_specific_translation_asv(self):
        hits = self.db.search("covenant", translation="asv", limit=5)
        self.assertGreater(len(hits), 0)
        for h in hits:
            self.assertEqual(h["translation_id"], "asv")
            self.assertEqual(h["translation_name"], "American Standard Version")

    def test_search_all_translations(self):
        hits = self.db.search("light", translation="all", limit=20)
        self.assertGreater(len(hits), 0)
        found_translations = {h["translation_id"] for h in hits}
        # Multi-translation search returns diverse translations
        self.assertGreater(len(found_translations), 1)

    def test_search_quoted_phrase(self):
        hits = self.db.search('"in the beginning"', translation="all", limit=5)
        self.assertGreater(len(hits), 0)
        for h in hits:
            self.assertIn("in the beginning", h["clean_text"].lower())

    def test_search_scoped_by_book(self):
        hits = self.db.search("God", book="Gen", translation="all", limit=10)
        self.assertGreater(len(hits), 0)
        for h in hits:
            self.assertEqual(h["osis"], "Gen")

    def test_search_scoped_by_testament(self):
        hits = self.db.search("grace", testament="NT", translation="all", limit=10)
        self.assertGreater(len(hits), 0)
        for h in hits:
            self.assertEqual(h["testament"], "NT")

    def test_search_list_of_translations(self):
        hits = self.db.search("covenant", translation=["asv", "bsb"], limit=10)
        self.assertGreater(len(hits), 0)
        for h in hits:
            self.assertIn(h["translation_id"], ["asv", "bsb"])

    def test_search_thou_shalt_not_kill_returns_exodus(self):
        hits = self.db.search("thou shalt not kill", limit=10)
        self.assertGreater(len(hits), 0)
        hit_ids = [h["id"] for h in hits]
        self.assertIn("Exod.20.13", hit_ids)


if __name__ == "__main__":
    unittest.main()
