"""Unit tests for multi-translation parallel engine and BibleDB translations support (WP-024 Phase 3)."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from search.corpus.extract_kjv import BibleDB
from search.corpus.extract_translations import (
    KNOWN_TRANSLATIONS,
    ingest_translations,
    sync_kjv_translation,
)


class BibleDBTranslationsTests(unittest.TestCase):
    """Test BibleDB multi-translation queries and schema."""

    @classmethod
    def setUpClass(cls):
        from search.testutil import ensure_test_databases
        ensure_test_databases()
        cls.db = BibleDB()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_list_translations_includes_core_set(self):
        translations = self.db.list_translations()
        self.assertGreaterEqual(len(translations), 4)
        t_ids = {t["id"] for t in translations}
        self.assertIn("kjv", t_ids)
        self.assertIn("asv", t_ids)
        self.assertIn("bsb", t_ids)
        self.assertIn("ylt", t_ids)

        kjv_meta = next(t for t in translations if t["id"] == "kjv")
        self.assertEqual(kjv_meta["is_default"], 1)
        self.assertEqual(kjv_meta["name"], "King James Version")

    def test_get_verse_translations_gen1_1(self):
        trans = self.db.get_verse_translations("Gen.1.1")
        self.assertIn("kjv", trans)
        self.assertIn("asv", trans)
        self.assertIn("bsb", trans)
        self.assertIn("ylt", trans)

        self.assertIn("created the heaven", trans["kjv"])
        self.assertIn("created the heavens", trans["asv"])
        self.assertIn("created the heavens", trans["bsb"])
        self.assertIn("God's preparing", trans["ylt"])

    def test_get_verse_translations_filter(self):
        trans = self.db.get_verse_translations("Gen.1.1", translation_ids=["asv", "bsb"])
        self.assertIn("asv", trans)
        self.assertIn("bsb", trans)
        self.assertNotIn("ylt", trans)

    def test_get_chapter_translations_batch(self):
        ch_trans = self.db.get_chapter_translations("Gen", 1)
        self.assertEqual(len(ch_trans), 31)
        for v_num in range(1, 32):
            self.assertIn(v_num, ch_trans)
            v_t = ch_trans[v_num]
            self.assertIn("kjv", v_t)
            self.assertIn("bsb", v_t)
            self.assertIn("asv", v_t)
            self.assertIn("ylt", v_t)

    def test_get_chapter_translations_ephesians(self):
        ch_trans = self.db.get_chapter_translations("Eph", 1)
        if len(ch_trans) < 23:
            self.assertIn(4, ch_trans)
        else:
            self.assertEqual(len(ch_trans), 23)
        v4 = ch_trans[4]
        # Verify distinct Paul translation characteristics
        self.assertIn("chosen us in him", v4["kjv"])
        self.assertIn("chose us in him", v4["asv"])
        self.assertIn("chose us in Him", v4["bsb"])
        self.assertIn("He did choose us", v4["ylt"])

    def test_invalid_verse_ref_returns_empty(self):
        res = self.db.get_verse_translations("InvalidRef 99:99")
        self.assertEqual(res, {})


class TranslationIngestionTests(unittest.TestCase):
    """Test standalone ingestion pipeline with isolated database."""

    def test_ingest_sample_translation(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "test_bible.db"
            sample_json = Path(td) / "sample.json"

            # Create sample JSON
            data = {
                "books": [
                    {
                        "name": "Genesis",
                        "chapters": [
                            {
                                "chapter": 1,
                                "verses": [
                                    {"verse": 1, "text": "In the beginning..."},
                                    {"verse": 2, "text": "The earth was formless..."},
                                ],
                            }
                        ],
                    }
                ]
            }
            sample_json.write_text(json.dumps(data), encoding="utf-8")

            with BibleDB(db_path=db_path) as db:
                count = db.ingest_translation(
                    translation_id="test_trans",
                    name="Test Translation",
                    year=2024,
                    license="Public Domain",
                    json_path=sample_json,
                )
                self.assertEqual(count, 2)

                t_list = db.list_translations()
                t_ids = {t["id"] for t in t_list}
                self.assertIn("test_trans", t_ids)

                v_trans = db.get_verse_translations("Gen.1.1")
                self.assertEqual(v_trans.get("test_trans"), "In the beginning...")

                ch_trans = db.get_chapter_translations("Gen", 1)
                self.assertEqual(ch_trans[2]["test_trans"], "The earth was formless...")


if __name__ == "__main__":
    unittest.main()
