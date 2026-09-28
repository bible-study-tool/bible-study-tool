"""Unit tests for whole-Bible KJV extraction, tokenization, SQLite database, and CLI (WP-019)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from search.corpus.extract_kjv import (
    DEFAULT_BIBLE_DB,
    DEFAULT_KJV_JSON,
    BibleDB,
    clean_token_text,
    clean_verse_text,
    compile_bible_db,
    extract_tokens,
    main as extract_kjv_main,
)
import scripts.bible_lookup as bible_cli


class TestKjvExtraction(unittest.TestCase):
    """Test text cleaning and Strong's token extraction."""

    def test_clean_verse_text(self):
        raw = '<w lemma="strong:H07225">In the beginning</w> <w lemma="strong:H0430">God</w> <w lemma="strong:H0853 strong:H01254" morph="strongMorph:TH8804">created</w> <note type="margin">apparatus note</note> the heaven and the earth.'
        clean = clean_verse_text(raw)
        self.assertEqual(clean, "In the beginning God created the heaven and the earth.")

        divine_raw = '<w lemma="strong:H03068">Then the <divineName>Lord</divineName></w> said unto Moses'
        self.assertEqual(clean_verse_text(divine_raw), "Then the LORD said unto Moses")

    def test_clean_token_text(self):
        self.assertEqual(clean_token_text("Then the <divineName>Lord</divineName>"), "Then the LORD")
        self.assertEqual(clean_token_text("And <divineName>God</divineName>"), "And GOD")
        self.assertEqual(clean_token_text("the <divineName>Lord’s</divineName>"), "the LORD’S")
        self.assertEqual(clean_token_text("the <divineName>LORD</divineName>"), "the LORD")
        self.assertEqual(clean_token_text("dry <transChange type=\"added\">land</transChange>"), "dry land")
        self.assertEqual(clean_token_text("plain word"), "plain word")
        self.assertEqual(clean_token_text(""), "")
        self.assertIsNone(clean_token_text(None))

    def test_extract_tokens_ot(self):
        raw = '<w lemma="strong:H07225">In the beginning</w> <w lemma="strong:H0430">God</w> <w lemma="strong:H0853 strong:H01254" morph="strongMorph:TH8804">created</w>'
        tokens = extract_tokens(raw)
        self.assertEqual(len(tokens), 3)

        self.assertEqual(tokens[0].text, "In the beginning")
        self.assertEqual(tokens[0].strongs, ["H7225"])

        self.assertEqual(tokens[1].text, "God")
        self.assertEqual(tokens[1].strongs, ["H430"])

        self.assertEqual(tokens[2].text, "created")
        self.assertEqual(tokens[2].strongs, ["H853", "H1254"])
        self.assertEqual(tokens[2].morph, "strongMorph:TH8804")

    def test_extract_tokens_nt_greek(self):
        raw = '<w lemma="strong:G1063 lemma.TR:γαρ" morph="robinson:CONJ" src="2">For</w> <w lemma="strong:G3588 strong:G2316 lemma.TR:ο lemma.TR:θεος" morph="robinson:T-NSM robinson:N-NSM" src="4 5">God</w>'
        tokens = extract_tokens(raw)
        self.assertEqual(len(tokens), 2)

        self.assertEqual(tokens[0].text, "For")
        self.assertEqual(tokens[0].strongs, ["G1063"])
        self.assertEqual(tokens[0].lemma, "γαρ")
        self.assertEqual(tokens[0].morph, "robinson:CONJ")

        self.assertEqual(tokens[1].text, "God")
        self.assertEqual(tokens[1].strongs, ["G3588", "G2316"])
        self.assertEqual(tokens[1].lemma, "ο")


class TestBibleDB(unittest.TestCase):
    """Test BibleDB SQLite database operations across the canon."""

    @classmethod
    def setUpClass(cls):
        # Ensure database is compiled or hydrated
        cls.db_path = Path(DEFAULT_BIBLE_DB)
        if not cls.db_path.is_file():
            if Path(DEFAULT_KJV_JSON).is_file():
                compile_bible_db(json_path=DEFAULT_KJV_JSON, db_path=cls.db_path)
            else:
                from search.testutil import ensure_test_databases
                ensure_test_databases()
        cls.db = BibleDB(db_path=cls.db_path)
        cls.verse_count = cls.db.count()["verses"]

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_whole_bible_counts(self):
        if self.verse_count < 31102:
            self.skipTest("Full 31,102-verse Bible database not present (run scripts/fetch_sources.sh)")
        counts = self.db.count()
        self.assertEqual(counts["books"], 66)
        self.assertEqual(counts["verses"], 31102)

    def test_verse_lookups_across_testaments(self):
        targets = [
            ("Gen.1.1", "In the beginning God created the heaven and the earth."),
            ("Deut.6.4", "Hear, O Israel: The Lord our God is one Lord:"),
            ("Dan.8.14", "And he said unto me, Unto two thousand and three hundred days; then shall the sanctuary be cleansed."),
            ("John 3:16", "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life."),
            ("Rom 8:28", "And we know that all things work together for good to them that love God, to them who are the called according to his purpose."),
            ("Rev 14:7", "Saying with a loud voice, Fear God, and give glory to him; for the hour of his judgment is come: and worship him that made heaven, and earth, and the sea, and the fountains of waters."),
        ]
        for vref, expected_text in targets:
            v = self.db.get_verse(vref)
            self.assertIsNotNone(v, f"Verse {vref} not found")
            self.assertEqual(v["clean_text"], expected_text)
            self.assertTrue(len(v["strongs"]) > 0)
            self.assertTrue(len(v["tokens"]) > 0)

    def test_passage_ranges(self):
        # Multi-verse range
        verses = self.db.get_passage("Rev 14:6-7")
        self.assertEqual(len(verses), 2)
        self.assertEqual(verses[0]["verse"], 6)
        self.assertEqual(verses[1]["verse"], 7)

        # Whole chapter
        ps23 = self.db.get_passage("Psalm 23")
        self.assertEqual(len(ps23), 6)

    def test_fts5_search(self):
        if self.verse_count < 31102:
            self.skipTest("Whole-Bible KJV database required for full FTS5 search suite")
        # Exact phrase search
        res = self.db.search("sanctuary cleansed")
        self.assertGreaterEqual(len(res), 1)
        dan814 = next((r for r in res if r["id"] == "Dan.8.14"), None)
        self.assertIsNotNone(dan814)

        # Scoped search
        nt_grace = self.db.search("grace", testament="NT", limit=10)
        self.assertEqual(len(nt_grace), 10)
        for r in nt_grace:
            self.assertEqual(r["testament"], "NT")

    def test_find_by_strongs(self):
        if self.verse_count < 31102:
            self.skipTest("Whole-Bible KJV database required for Strong's reverse index suite")
        # Greek Strong's G2316 (Theos)
        theos_verses = self.db.find_by_strongs("G2316", limit=5)
        self.assertEqual(len(theos_verses), 5)
        for v in theos_verses:
            self.assertEqual(v["testament"], "NT")
            self.assertIn("G2316", v["strongs"])

        # Hebrew Strong's H7225 (Reshit)
        reshit_verses = self.db.find_by_strongs("H7225", limit=5)
        self.assertEqual(len(reshit_verses), 5)
        for v in reshit_verses:
            self.assertEqual(v["testament"], "OT")
            self.assertIn("H7225", v["strongs"])

        # Padded Strong's codes (H0430, 0430, G02316)
        elohim_padded = self.db.find_by_strongs("H0430", limit=5)
        self.assertEqual(len(elohim_padded), 5)
        for v in elohim_padded:
            self.assertIn("H430", v["strongs"])

        elohim_unprefixed = self.db.find_by_strongs("0430", limit=5)
        self.assertEqual(len(elohim_unprefixed), 5)

        theos_padded = self.db.find_by_strongs("G02316", limit=5)
        self.assertEqual(len(theos_padded), 5)
        for v in theos_padded:
            self.assertIn("G2316", v["strongs"])

        # Invalid Strong's code raises ValueError
        with self.assertRaises(ValueError):
            self.db.find_by_strongs("INVALID_CODE")

    def test_search_testament_validation(self):
        # Valid testament
        ot_results = self.db.search("God", testament="OT", limit=3)
        self.assertTrue(len(ot_results) > 0)
        for r in ot_results:
            self.assertEqual(r["testament"], "OT")

        # Invalid testament raises ValueError
        with self.assertRaises(ValueError):
            self.db.search("God", testament="APOCRYPHA")

    def test_empty_db_count(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            empty_db = BibleDB(db_path=tmp.name)
            counts = empty_db.count()
            self.assertEqual(counts, {"books": 0, "verses": 0})
            empty_db.close()

    def test_cli_operations(self):
        rc = bible_cli.main(["John 3:16", "--db", str(self.db_path)])
        self.assertEqual(rc, 0)

        rc = bible_cli.main(["John 3:16", "--strongs", "--db", str(self.db_path)])
        self.assertEqual(rc, 0)

        rc = bible_cli.main(["--search", "sanctuary cleansed", "--db", str(self.db_path)])
        self.assertEqual(rc, 0)

        rc = bible_cli.main(["--find-strongs", "G2316", "--limit", "3", "--db", str(self.db_path)])
        self.assertEqual(rc, 0)

        rc = bible_cli.main(["--find-strongs", "H0430", "--limit", "3", "--db", str(self.db_path)])
        self.assertEqual(rc, 0)

        rc = bible_cli.main(["--stats", "--db", str(self.db_path)])
        self.assertEqual(rc, 0)

    def test_extract_kjv_cli_main(self):
        if not Path(DEFAULT_KJV_JSON).is_file():
            self.skipTest("KJV JSON source not present")
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test_bible.db"
            rc = extract_kjv_main(["--compile", "--db", str(db_path), "--json", DEFAULT_KJV_JSON])
            self.assertEqual(rc, 0)
            db = BibleDB(db_path=db_path)
            counts = db.count()
            self.assertEqual(counts["verses"], 31102)
            self.assertEqual(counts["books"], 66)
            db.close()


if __name__ == "__main__":
    unittest.main()
