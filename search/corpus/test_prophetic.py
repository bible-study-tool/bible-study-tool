"""Unit and validation tests for the Master Historicist Prophetic Lexicon (WP-031 Phase 2).

Verifies:
1. Deterministic JSON schema and integrity of data/prophetic_lexicon.json.
2. Canonical resolution in BibleDB for all proof texts and anchor passages.
3. Lexical validity of Strong's concordance codes against lexicons/strongs-lexicon.json.
4. Querying and filtering capabilities of PropheticLexicon and StudyService.
5. Passage overlap matching for apocalyptic texts (Daniel 7, Revelation 12, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from search.corpus.extract_kjv import BibleDB
from search.corpus.prophetic import (
    VALID_CATEGORIES,
    _STRONGS_RE,
    PropheticLexicon,
    PropheticSymbol,
    get_prophetic_lexicon,
)
from search.resource import data_path
from search.ui.study_service import StudyService


class PropheticLexiconDatasetValidationTests(unittest.TestCase):
    """Integrity and tripwire tests for data/prophetic_lexicon.json."""

    @classmethod
    def setUpClass(cls):
        cls.path = data_path("prophetic_lexicon.json")
        cls.assertTrue(cls.path.is_file(), f"Dataset not found at {cls.path}")
        with open(cls.path, "r", encoding="utf-8") as f:
            cls.raw = json.load(f)
        cls.bible = BibleDB()
        with open("lexicons/strongs-lexicon.json", "r", encoding="utf-8") as f:
            cls.strongs_lex = json.load(f)

    @classmethod
    def tearDownClass(cls):
        cls.bible.close()

    def test_schema_top_level(self):
        self.assertIn("version", self.raw)
        self.assertIn("title", self.raw)
        self.assertIn("description", self.raw)
        self.assertIn("categories", self.raw)
        self.assertIn("symbols", self.raw)
        self.assertEqual(set(self.raw["categories"]), {"Time", "Entities", "Elements"})

    def test_minimum_symbol_inventory_count(self):
        symbols = self.raw["symbols"]
        self.assertGreaterEqual(len(symbols), 25, "Must contain at least 25 canonical prophetic symbols")

    def test_symbol_fields_and_types(self):
        seen_ids = set()
        for s in self.raw["symbols"]:
            self.assertIn("id", s)
            self.assertIn("symbol", s)
            self.assertIn("meaning", s)
            self.assertIn("category", s)
            self.assertIn("books", s)
            self.assertIn("proof_texts", s)
            self.assertIn("canonical_anchors", s)
            self.assertIn("strongs", s)
            self.assertIn("sda_consensus", s)

            # Check uniqueness
            self.assertNotIn(s["id"], seen_ids, f"Duplicate symbol id: {s['id']}")
            seen_ids.add(s["id"])

            # Non-empty strings and lists
            self.assertTrue(s["id"].strip())
            self.assertTrue(s["symbol"].strip())
            self.assertTrue(s["meaning"].strip())
            self.assertIn(s["category"], VALID_CATEGORIES)
            self.assertGreaterEqual(len(s["books"]), 1)
            self.assertGreaterEqual(len(s["proof_texts"]), 1)
            self.assertGreaterEqual(len(s["canonical_anchors"]), 1)
            self.assertGreaterEqual(len(s["strongs"]), 1)
            self.assertTrue(s["sda_consensus"].strip())

    def test_strongs_codes_validity(self):
        """Verify every Strong's code conforms to format and exists in the lexicon."""
        for s in self.raw["symbols"]:
            for code in s["strongs"]:
                self.assertRegex(code, _STRONGS_RE, f"Invalid Strong's format {code} in {s['id']}")
                if code.startswith("H"):
                    self.assertIn(
                        code,
                        self.strongs_lex["hebrew"],
                        f"Hebrew Strong's code {code} in {s['id']} not found in strongs-lexicon",
                    )
                else:
                    self.assertIn(
                        code,
                        self.strongs_lex["greek"],
                        f"Greek Strong's code {code} in {s['id']} not found in strongs-lexicon",
                    )

    def test_all_proof_texts_resolve_in_bibledb(self):
        """Tripwire: Every proof text in data/prophetic_lexicon.json must resolve in BibleDB."""
        missing = []
        for s in self.raw["symbols"]:
            for ref in s["proof_texts"]:
                verses = self.bible.get_passage(ref)
                if not verses:
                    missing.append((s["id"], "proof_text", ref))
        self.assertEqual(missing, [], f"Unresolvable proof texts found: {missing}")

    def test_all_canonical_anchors_resolve_in_bibledb(self):
        """Tripwire: Every canonical anchor in data/prophetic_lexicon.json must resolve in BibleDB."""
        missing = []
        for s in self.raw["symbols"]:
            for ref in s["canonical_anchors"]:
                verses = self.bible.get_passage(ref)
                if not verses:
                    missing.append((s["id"], "canonical_anchor", ref))
        self.assertEqual(missing, [], f"Unresolvable canonical anchors found: {missing}")


class PropheticLexiconEngineTests(unittest.TestCase):
    """Unit tests for PropheticLexicon class and search filtering."""

    def setUp(self):
        self.lexicon = PropheticLexicon()

    def test_get_symbol_by_id(self):
        sym = self.lexicon.get_symbol("day-year-principle")
        self.assertIsNotNone(sym)
        self.assertEqual(sym.symbol, "Day")
        self.assertEqual(sym.category, "Time")
        self.assertIn("Numbers 14:34", sym.proof_texts)
        self.assertIn("Ezekiel 4:6", sym.proof_texts)
        self.assertIn("H3117", sym.strongs)
        self.assertIn("G2250", sym.strongs)

    def test_get_nonexistent_symbol_returns_none(self):
        self.assertIsNone(self.lexicon.get_symbol("quantum-prophecy"))

    def test_filter_by_category_time(self):
        time_symbols = self.lexicon.list_symbols(category="Time")
        ids = {s.id for s in time_symbols}
        self.assertIn("day-year-principle", ids)
        self.assertIn("time-times-half", ids)
        self.assertIn("seventy-weeks", ids)
        self.assertIn("twenty-three-hundred-days", ids)
        for s in time_symbols:
            self.assertEqual(s.category, "Time")

    def test_filter_by_category_entities(self):
        entities = self.lexicon.list_symbols(category="Entities")
        ids = {s.id for s in entities}
        self.assertIn("beast", ids)
        self.assertIn("horns", ids)
        self.assertIn("pure-woman", ids)
        self.assertIn("harlot-woman", ids)
        self.assertIn("dragon", ids)
        self.assertIn("seven-heads", ids)
        self.assertIn("two-witnesses", ids)
        self.assertIn("locusts-and-scorpions", ids)

    def test_filter_by_category_elements(self):
        elements = self.lexicon.list_symbols(category="Elements")
        ids = {s.id for s in elements}
        self.assertIn("waters-sea", ids)
        self.assertIn("earth-wilderness", ids)
        self.assertIn("winds", ids)
        self.assertIn("wings", ids)
        self.assertIn("sun-and-moon", ids)
        self.assertIn("crowns", ids)
        self.assertIn("mark-and-seal", ids)
        self.assertIn("wine-of-babylon", ids)
        self.assertIn("candlestick-lampstand", ids)
        self.assertIn("incense", ids)
        self.assertIn("seven-trumpets", ids)

    def test_filter_by_book_daniel(self):
        dan_symbols = self.lexicon.list_symbols(book="Daniel")
        ids = {s.id for s in dan_symbols}
        self.assertIn("beast", ids)
        self.assertIn("horns", ids)
        self.assertIn("rock-stone", ids)
        self.assertIn("seventy-weeks", ids)
        self.assertIn("twenty-three-hundred-days", ids)

    def test_filter_by_book_revelation(self):
        rev_symbols = self.lexicon.list_symbols(book="Revelation")
        ids = {s.id for s in rev_symbols}
        self.assertIn("pure-woman", ids)
        self.assertIn("dragon", ids)
        self.assertIn("seven-heads", ids)
        self.assertIn("mark-and-seal", ids)
        self.assertIn("seven-trumpets", ids)

    def test_text_search_query(self):
        results = self.lexicon.list_symbols(query="papal supremacy")
        self.assertTrue(any(s.id == "time-times-half" for s in results))

    def test_text_search_query_expanded_scope(self):
        # Matches by category
        results = self.lexicon.list_symbols(query="Elements")
        self.assertGreater(len(results), 0)
        # Matches by associated book name
        dan_results = self.lexicon.list_symbols(query="Zechariah")
        self.assertTrue(any(s.id == "two-witnesses" for s in dan_results))

    def test_filter_by_invalid_book_does_not_raise(self):
        """Verify invalid book name gracefully returns empty list rather than raising ValueError."""
        results = self.lexicon.list_symbols(book="NonexistentBook123")
        self.assertEqual(results, [])

    def test_passage_overlap_daniel_7_25(self):
        """Acceptance Criterion: In-context symbols in Daniel 7 link to defining scriptures."""
        symbols = self.lexicon.get_symbols_for_passage("Daniel 7:25")
        ids = {s.id for s in symbols}
        self.assertIn("day-year-principle", ids)
        self.assertIn("time-times-half", ids)

    def test_passage_overlap_revelation_12(self):
        """Acceptance Criterion: In-context symbols in Revelation 12 link to defining scriptures."""
        symbols = self.lexicon.get_symbols_for_passage("Revelation 12:1-3")
        ids = {s.id for s in symbols}
        self.assertIn("pure-woman", ids)
        self.assertIn("sun-and-moon", ids)
        self.assertIn("crowns", ids)
        self.assertIn("dragon", ids)
        self.assertIn("seven-heads", ids)
        self.assertIn("horns", ids)

    def test_passage_overlap_anchor_only_when_include_proofs_false(self):
        # Numbers 14:34 is a proof_text for day-year-principle, but not a canonical_anchor
        with_proofs = self.lexicon.get_symbols_for_passage("Numbers 14:34", include_proofs=True)
        self.assertTrue(any(s.id == "day-year-principle" for s in with_proofs))

        anchors_only = self.lexicon.get_symbols_for_passage("Numbers 14:34", include_proofs=False)
        self.assertFalse(any(s.id == "day-year-principle" for s in anchors_only))

    def test_fail_fast_validation_invalid_category(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as tf:
            bad_data = {
                "symbols": [{
                    "id": "bad-cat",
                    "symbol": "Bad",
                    "meaning": "Invalid",
                    "category": "InvalidCategory",
                    "books": ["Dan"],
                    "proof_texts": ["Dan 1:1"],
                    "canonical_anchors": ["Dan 1:1"],
                    "strongs": ["H1234"],
                    "sda_consensus": "none",
                }]
            }
            json.dump(bad_data, tf)
            tf.flush()
            with self.assertRaises(ValueError) as ctx:
                PropheticLexicon(data_file=tf.name)
            self.assertIn("Invalid category", str(ctx.exception))

    def test_fail_fast_validation_invalid_strongs(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as tf:
            bad_data = {
                "symbols": [{
                    "id": "bad-strongs",
                    "symbol": "Bad",
                    "meaning": "Invalid",
                    "category": "Time",
                    "books": ["Dan"],
                    "proof_texts": ["Dan 1:1"],
                    "canonical_anchors": ["Dan 1:1"],
                    "strongs": ["Z9999"],
                    "sda_consensus": "none",
                }]
            }
            json.dump(bad_data, tf)
            tf.flush()
            with self.assertRaises(ValueError) as ctx:
                PropheticLexicon(data_file=tf.name)
            self.assertIn("Invalid Strong's code", str(ctx.exception))

    def test_cached_singleton_function(self):
        l1 = get_prophetic_lexicon()
        l2 = get_prophetic_lexicon()
        self.assertIs(l1, l2)


class PropheticStudyServiceIntegrationTests(unittest.TestCase):
    """Test StudyService integration with prophetic lexicon."""

    def test_study_service_prophetic_methods(self):
        with StudyService() as study:
            lex = study.get_prophetic_lexicon()
            self.assertIsInstance(lex, PropheticLexicon)

            all_syms = study.get_prophetic_symbols()
            self.assertGreaterEqual(len(all_syms), 25)

            time_syms = study.get_prophetic_symbols(category="Time")
            self.assertTrue(all(s["category"] == "Time" for s in time_syms))

            one_sym = study.get_prophetic_symbol("day-year-principle")
            self.assertIsNotNone(one_sym)
            self.assertEqual(one_sym["id"], "day-year-principle")

            dan_syms = study.get_prophetic_symbols_for_passage("Dan 7:25")
            dan_ids = [s["id"] for s in dan_syms]
            self.assertIn("day-year-principle", dan_ids)

            # Annotated symbols with is_anchor and is_proof flags
            annotated_dan = study.get_annotated_prophetic_symbols_for_passage("Dan 7:25")
            day_sym = next(s for s in annotated_dan if s["id"] == "day-year-principle")
            self.assertTrue(day_sym["is_anchor"])
            self.assertFalse(day_sym["is_proof"])

            # In-context VerseStudy prophetic symbols
            ps = study.get_passage_study("Dan 7:25")
            self.assertEqual(len(ps.verses), 1)
            v_sym_ids = [s.id for s in ps.verses[0].prophetic_symbols]
            self.assertIn("day-year-principle", v_sym_ids)
            self.assertIn("time-times-half", v_sym_ids)

            # Proof text recognition in Ezekiel 4:6
            ps_eze = study.get_passage_study("Ezekiel 4:6")
            self.assertEqual(len(ps_eze.verses), 1)
            eze_day = next((s for s in ps_eze.verses[0].prophetic_symbols if s.id == "day-year-principle"), None)
            self.assertIsNotNone(eze_day)
            self.assertFalse(eze_day.is_anchor)
            self.assertTrue(eze_day.is_proof)

            # Revelation 12:1 symbols
            ps_rev = study.get_passage_study("Revelation 12:1")
            rev_ids = {s.id for s in ps_rev.verses[0].prophetic_symbols}
            self.assertIn("pure-woman", rev_ids)
            self.assertIn("sun-and-moon", rev_ids)
            self.assertIn("stars", rev_ids)
            self.assertIn("crowns", rev_ids)


if __name__ == "__main__":
    unittest.main()
