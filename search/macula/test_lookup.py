"""Unit tests for search/macula/lookup.py and scripts/macula_lookup.py."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

from search.macula.lookup import (
    MaculaDB,
    normalize_verse_ref,
    lookup_strongs,
    lookup_verse,
    lookup_lxx,
)

SAMPLE_DATA = {
    "$schema": "../schemas/macula-schema.json",
    "source": {
        "upstream": "https://github.com/Clear-Bible/macula-hebrew",
        "commit": "47db250bd55d0d8577f2a94fba114ef16c35b23c",
        "license": "CC BY 4.0",
        "attribution": "Macula Hebrew project",
    },
    "counts": {
        "chapters": 1,
        "verses": 1,
        "clauses": 1,
        "tokens": 4,
        "strongs_crosswalk_entries": 3,
    },
    "strongs_crosswalk": {
        "H430": {
            "strongs": "H430",
            "lemmas": ["אֱלֹהִים"],
            "glosses": ["God"],
            "sdbh": ["000397001003000"],
            "core_domains": ["055"],
            "lex_domains": ["001001001"],
            "lxx": {
                "G2316": {
                    "strongs": "G2316",
                    "greek": ["θεὸς"],
                    "count": 1,
                }
            },
            "occurrences": 1,
        },
        "H1254": {
            "strongs": "H1254",
            "lemmas": ["בָּרָא"],
            "glosses": ["created"],
            "sdbh": ["001156001002000"],
            "core_domains": ["028", "055"],
            "lex_domains": ["002002002005"],
            "lxx": {
                "G4160": {
                    "strongs": "G4160",
                    "greek": ["ἐποίησεν"],
                    "count": 1,
                }
            },
            "occurrences": 1,
        },
        "H7225": {
            "strongs": "H7225",
            "lemmas": ["רֵאשִׁית"],
            "glosses": ["beginning"],
            "sdbh": ["006653001001000"],
            "core_domains": ["168"],
            "lex_domains": ["002001001042"],
            "lxx": {
                "G746": {
                    "strongs": "G746",
                    "greek": ["ἀρξῇ"],
                    "count": 1,
                }
            },
            "occurrences": 1,
        },
    },
    "verses": {
        "Gen.1.1": {
            "verse_id": "Gen.1.1",
            "mt_id": "GEN 1:1",
            "text": "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים",
            "clauses": [
                {
                    "rule": "PP-V-S",
                    "text": "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים",
                    "constituents": [
                        {
                            "role": "pp",
                            "role_label": "prepositional_phrase",
                            "class": "pp",
                            "rule": "PrepNp",
                            "text": "בְּרֵאשִׁ֖ית",
                            "tokens": [
                                {
                                    "id": "o010010010012",
                                    "text": "רֵאשִׁ֖ית",
                                    "lemma": "רֵאשִׁית",
                                    "strongs": "H7225",
                                    "lxx_strongs": "G746",
                                    "lxx": "ἀρξῇ",
                                    "gloss": "beginning",
                                    "role": "pp",
                                }
                            ],
                        },
                        {
                            "role": "v",
                            "role_label": "predicate_verb",
                            "class": "verb",
                            "rule": "",
                            "text": "בָּרָ֣א",
                            "tokens": [
                                {
                                    "id": "o010010010021",
                                    "text": "בָּרָ֣א",
                                    "lemma": "בָּרָא",
                                    "strongs": "H1254",
                                    "lxx_strongs": "G4160",
                                    "lxx": "ἐποίησεν",
                                    "gloss": "created",
                                    "role": "v",
                                }
                            ],
                        },
                        {
                            "role": "s",
                            "role_label": "subject",
                            "class": "noun",
                            "rule": "",
                            "text": "אֱלֹהִ֑ים",
                            "tokens": [
                                {
                                    "id": "o010010010031",
                                    "text": "אֱלֹהִ֑ים",
                                    "lemma": "אֱלֹהִים",
                                    "strongs": "H430",
                                    "lxx_strongs": "G2316",
                                    "lxx": "θεὸς",
                                    "gloss": "God",
                                    "role": "s",
                                }
                            ],
                        },
                    ],
                }
            ],
        }
    },
}


class NormalizeVerseRefTests(unittest.TestCase):
    def test_various_formats(self):
        self.assertEqual(normalize_verse_ref("Gen.1.1"), "Gen.1.1")
        self.assertEqual(normalize_verse_ref("GEN 1:1"), "Gen.1.1")
        self.assertEqual(normalize_verse_ref("gen 1:1"), "Gen.1.1")
        self.assertEqual(normalize_verse_ref("1:1"), "Gen.1.1")
        self.assertEqual(normalize_verse_ref("1.1"), "Gen.1.1")
        self.assertEqual(normalize_verse_ref("gen-1-1"), "Gen.1.1")
        self.assertEqual(normalize_verse_ref("gen-1-1-kjv.md"), "Gen.1.1")
        self.assertEqual(normalize_verse_ref("Genesis 1:1"), "Gen.1.1")
        self.assertEqual(normalize_verse_ref("Gen.50.26"), "Gen.50.26")

    def test_invalid_ref(self):
        with self.assertRaises(ValueError):
            normalize_verse_ref("invalid-ref")


class MaculaDbTests(unittest.TestCase):
    def setUp(self):
        self.db = MaculaDB(SAMPLE_DATA)

    def test_counts(self):
        self.assertEqual(self.db.counts["verses"], 1)
        self.assertEqual(self.db.counts["strongs_crosswalk_entries"], 3)

    def test_lookup_strongs(self):
        res = self.db.lookup_strongs("H7225")
        self.assertIsNotNone(res)
        self.assertEqual(res["strongs"], "H7225")
        self.assertIn("רֵאשִׁית", res["lemmas"])
        self.assertIn("G746", res["lxx"])

        # Number-only input
        res2 = self.db.lookup_strongs("7225")
        self.assertEqual(res2, res)

        # Zero-padded input
        res3 = self.db.lookup_strongs("H0430")
        self.assertIsNotNone(res3)
        self.assertEqual(res3["strongs"], "H430")

        # Unknown
        self.assertIsNone(self.db.lookup_strongs("H9999"))

    def test_lookup_verse(self):
        v = self.db.lookup_verse("Gen.1.1")
        self.assertIsNotNone(v)
        self.assertEqual(v["verse_id"], "Gen.1.1")
        self.assertEqual(len(v["clauses"]), 1)
        self.assertEqual(v["clauses"][0]["rule"], "PP-V-S")
        self.assertEqual(len(v["clauses"][0]["constituents"]), 3)

        # Alternative formats
        self.assertEqual(self.db.lookup_verse("GEN 1:1"), v)
        self.assertEqual(self.db.lookup_verse("1:1"), v)
        self.assertIsNone(self.db.lookup_verse("Gen.99.99"))

    def test_lookup_lxx(self):
        # Reverse lookup for G4160
        matches = self.db.lookup_lxx("G4160")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["hebrew_strongs"], "H1254")
        self.assertEqual(matches[0]["count"], 1)

        # Numeric input
        matches2 = self.db.lookup_lxx("4160")
        self.assertEqual(matches2, matches)

        # Unknown Greek
        self.assertEqual(self.db.lookup_lxx("G9999"), [])

    def test_search_by_domain(self):
        matches = self.db.search_by_domain("168")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["hebrew_strongs"], "H7225")

        matches_055 = self.db.search_by_domain("055")
        self.assertEqual(len(matches_055), 2)
        h_ids = {m["hebrew_strongs"] for m in matches_055}
        self.assertEqual(h_ids, {"H430", "H1254"})


class MaculaCliTests(unittest.TestCase):
    def test_cli_strongs(self):
        cmd = [sys.executable, "scripts/macula_lookup.py", "--strongs", "H7225"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Strong's: H7225", res.stdout)
        self.assertIn("רֵאשִׁית", res.stdout)
        self.assertIn("G746", res.stdout)

    def test_cli_verse(self):
        cmd = [sys.executable, "scripts/macula_lookup.py", "--verse", "Gen.1.1"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Verse: Gen.1.1", res.stdout)
        self.assertIn("PP-V-S-O", res.stdout)
        self.assertIn("SUBJECT", res.stdout)

    def test_cli_lxx(self):
        cmd = [sys.executable, "scripts/macula_lookup.py", "--lxx", "G4160"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("H6213", res.stdout)

    def test_cli_domain(self):
        cmd = [sys.executable, "scripts/macula_lookup.py", "--domain", "168"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("H7225", res.stdout)

    def test_cli_stats_json(self):
        cmd = [sys.executable, "scripts/macula_lookup.py", "--stats", "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertGreaterEqual(data["chapters"], 50)
        self.assertGreaterEqual(data["verses"], 1533)
        self.assertGreaterEqual(data["clauses"], 7007)

        # Explicit artifact test
        cmd_art = [
            sys.executable, "scripts/macula_lookup.py",
            "--artifact", "lexicons/macula-genesis.json",
            "--stats", "--json"
        ]
        res_art = subprocess.run(cmd_art, capture_output=True, text=True)
        self.assertEqual(res_art.returncode, 0, res_art.stderr)
        data_art = json.loads(res_art.stdout)
        self.assertEqual(data_art["chapters"], 50)
        self.assertEqual(data_art["verses"], 1533)
        self.assertEqual(data_art["clauses"], 7007)


if __name__ == "__main__":
    unittest.main(verbosity=2)
