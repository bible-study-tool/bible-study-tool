"""Unit tests for Pauline Argument Flow & Discourse Markers Engine (WP-025)."""

from __future__ import annotations

import unittest

from search.corpus.discourse_flow import (
    DiscourseCategory,
    DiscourseMarker,
    analyze_passage_argument_flow,
    extract_passage_discourse_batch,
    extract_verse_discourse_markers,
    format_discourse_badge,
)
from search.corpus.extract_kjv import BibleDB


class DiscourseFlowTests(unittest.TestCase):
    """Test suite for Discourse Flow extraction and classification."""

    def test_greek_premise_marker(self):
        tokens = [
            {"text": "For", "strongs": ["G1063"], "lemma": "γαρ"},
            {"text": "I", "strongs": []},
        ]
        markers = extract_verse_discourse_markers(tokens)
        self.assertEqual(len(markers), 1)
        m = markers[0]
        self.assertEqual(m.category, DiscourseCategory.PREMISE)
        self.assertEqual(m.strongs, "G1063")
        self.assertEqual(m.original_word, "γάρ")
        self.assertEqual(m.transliteration, "gar")
        self.assertIn("Explains why", m.function_summary)

    def test_greek_conclusion_marker(self):
        tokens = [
            {"text": "therefore", "strongs": ["G3767"], "lemma": "ουν"},
        ]
        markers = extract_verse_discourse_markers(tokens)
        self.assertEqual(len(markers), 1)
        m = markers[0]
        self.assertEqual(m.category, DiscourseCategory.CONCLUSION)
        self.assertEqual(m.strongs, "G3767")
        self.assertEqual(m.original_word, "οὖν")
        self.assertTrue(m.is_major_pivot)
        self.assertIn("turning point", m.role_label.lower())

    def test_greek_purpose_marker(self):
        tokens = [
            {"text": "that", "strongs": ["G2443"], "lemma": "ινα"},
        ]
        markers = extract_verse_discourse_markers(tokens)
        self.assertEqual(len(markers), 1)
        m = markers[0]
        self.assertEqual(m.category, DiscourseCategory.PURPOSE)
        self.assertEqual(m.strongs, "G2443")
        self.assertEqual(m.original_word, "ἵνα")
        self.assertIn("divine purpose", m.function_summary.lower())

    def test_greek_contrast_marker(self):
        tokens = [
            {"text": "But", "strongs": ["G235"], "lemma": "αλλα"},
        ]
        markers = extract_verse_discourse_markers(tokens)
        self.assertEqual(len(markers), 1)
        m = markers[0]
        self.assertEqual(m.category, DiscourseCategory.CONTRAST)
        self.assertEqual(m.strongs, "G235")
        self.assertEqual(m.original_word, "ἀλλά")

    def test_greek_analogy_marker(self):
        tokens = [
            {"text": "According as", "strongs": ["G2531"], "lemma": "καθως"},
        ]
        markers = extract_verse_discourse_markers(tokens)
        self.assertEqual(len(markers), 1)
        m = markers[0]
        self.assertEqual(m.category, DiscourseCategory.ANALOGY)
        self.assertEqual(m.strongs, "G2531")
        self.assertEqual(m.original_word, "καθώς")
        self.assertIn("divine archetype", m.function_summary.lower())

    def test_hebrew_discourse_markers(self):
        tokens = [
            {"text": "Therefore", "strongs": ["H3651"]},
            {"text": "for", "strongs": ["H3588"]},
            {"text": "that", "strongs": ["H4616"]},
            {"text": "if", "strongs": ["H518"]},      # Unpadded from extract_tokens
            {"text": "truly", "strongs": ["H0061"]},  # 4-digit padded form
        ]
        markers = extract_verse_discourse_markers(tokens)
        categories = {m.category for m in markers}
        self.assertIn(DiscourseCategory.CONCLUSION, categories)
        self.assertIn(DiscourseCategory.PREMISE, categories)
        self.assertIn(DiscourseCategory.PURPOSE, categories)
        self.assertIn(DiscourseCategory.CONDITION, categories)
        self.assertIn(DiscourseCategory.CONTRAST, categories)

    def test_format_discourse_badge(self):
        tokens = [
            {"text": "For", "strongs": ["G1063"]},
            {"text": "that", "strongs": ["G2443"]},
        ]
        markers = extract_verse_discourse_markers(tokens)
        badge = format_discourse_badge(markers)
        self.assertIn("Premise", badge)
        self.assertIn("Purpose", badge)
        self.assertIn("γάρ", badge)
        self.assertIn("ἵνα", badge)

    def test_empty_tokens(self):
        markers = extract_verse_discourse_markers([])
        self.assertEqual(markers, [])
        badge = format_discourse_badge([])
        self.assertEqual(badge, "")

    def test_english_fallback_inference(self):
        tokens = [{"text": "Wherefore", "strongs": []}]
        markers = extract_verse_discourse_markers(tokens, text="Wherefore let him that thinketh he standeth...")
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0].category, DiscourseCategory.CONCLUSION)


class DiscourseFlowIntegrationTests(unittest.TestCase):
    """Integration tests with real data from data/bible.db."""

    @classmethod
    def setUpClass(cls):
        from search.testutil import ensure_test_databases
        ensure_test_databases()
        cls.db = BibleDB()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_romans_1_16_discourse(self):
        verses = self.db.get_passage("Rom 1:16")
        self.assertTrue(len(verses) >= 1)
        markers = extract_verse_discourse_markers(verses[0]["tokens"], text=verses[0]["clean_text"])
        self.assertTrue(any(m.category == DiscourseCategory.PREMISE and m.strongs == "G1063" for m in markers))

    def test_romans_12_1_discourse(self):
        verses = self.db.get_passage("Rom 12:1")
        self.assertTrue(len(verses) >= 1)
        markers = extract_verse_discourse_markers(verses[0]["tokens"], text=verses[0]["clean_text"])
        self.assertTrue(any(m.category == DiscourseCategory.CONCLUSION and m.strongs == "G3767" for m in markers))

    def test_ephesians_1_4_discourse(self):
        verses = self.db.get_passage("Eph 1:4")
        self.assertTrue(len(verses) >= 1)
        markers = extract_verse_discourse_markers(verses[0]["tokens"], text=verses[0]["clean_text"])
        self.assertTrue(any(m.category == DiscourseCategory.ANALOGY and m.strongs == "G2531" for m in markers))

    def test_ephesians_2_4_discourse(self):
        verses = self.db.get_passage("Eph 2:4")
        self.assertTrue(len(verses) >= 1)
        markers = extract_verse_discourse_markers(verses[0]["tokens"], text=verses[0]["clean_text"])
        self.assertTrue(any(m.category == DiscourseCategory.CONTRAST for m in markers))

    def test_ephesians_2_10_discourse(self):
        verses = self.db.get_passage("Eph 2:10")
        self.assertTrue(len(verses) >= 1)
        markers = extract_verse_discourse_markers(verses[0]["tokens"], text=verses[0]["clean_text"])
        categories = {m.category for m in markers}
        self.assertIn(DiscourseCategory.PREMISE, categories)
        self.assertIn(DiscourseCategory.PURPOSE, categories)

    def test_genesis_2_24_discourse(self):
        verses = self.db.get_passage("Gen 2:24")
        self.assertTrue(len(verses) >= 1)
        markers = extract_verse_discourse_markers(verses[0]["tokens"], text=verses[0]["clean_text"])
        self.assertTrue(any(m.category == DiscourseCategory.CONCLUSION for m in markers))

    def test_passage_argument_flow_streak(self):
        verses = self.db.get_passage("Rom 1:15-18")
        steps = analyze_passage_argument_flow(verses)
        self.assertEqual(len(steps), 4)
        # Rom 1:16 is initial ground
        self.assertIn("Premise", steps[1].primary_role)
        # Rom 1:17 is Deepening Premise #2
        self.assertIn("Deepening Premise (Ground #2)", steps[2].primary_role)
        # Rom 1:18 is Deepening Premise #3
        self.assertIn("Deepening Premise (Ground #3)", steps[3].primary_role)

    def test_batch_extraction_passage(self):
        verses = self.db.get_passage("Eph 1:1-14")
        batch = extract_passage_discourse_batch(verses)
        self.assertEqual(len(batch), 14)
        # Eph 1:4 should have analogy
        self.assertTrue(len(batch["Eph.1.4"]) > 0)


if __name__ == "__main__":
    unittest.main()
