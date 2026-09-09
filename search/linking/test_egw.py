"""Tests for Spirit of Prophecy (EGW) JIT SQLite architecture and CLI (ADR-011)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from search.linking.egw import (
    DEFAULT_EGW_DB,
    KNOWN_EGW_BOOKS,
    EgwDB,
    is_egw_token,
    normalize_token,
    seed_core_genesis_passages,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SCRIPT = REPO_ROOT / "scripts" / "egw_lookup.py"


class TokenParsingTests(unittest.TestCase):
    def test_normalize_token_standard(self):
        canonical_id, book, page, para = normalize_token("PP.57.1")
        self.assertEqual(canonical_id, "PP.57.1")
        self.assertEqual(book, "PP")
        self.assertEqual(page, 57)
        self.assertEqual(para, 1)

    def test_normalize_token_with_egw_prefix(self):
        canonical_id, book, page, para = normalize_token("egw:PP.57.1")
        self.assertEqual(canonical_id, "PP.57.1")
        self.assertEqual(book, "PP")
        self.assertEqual(page, 57)
        self.assertEqual(para, 1)

    def test_normalize_token_without_paragraph_defaults_to_one(self):
        canonical_id, book, page, para = normalize_token("DA.19")
        self.assertEqual(canonical_id, "DA.19.1")
        self.assertEqual(book, "DA")
        self.assertEqual(page, 19)
        self.assertEqual(para, 1)

    def test_normalize_token_case_insensitivity(self):
        canonical_id, book, page, para = normalize_token("egw:gc.582.2")
        self.assertEqual(canonical_id, "GC.582.2")
        self.assertEqual(book, "GC")
        self.assertEqual(page, 582)
        self.assertEqual(para, 2)

    def test_invalid_tokens_raise_value_error(self):
        for bad in ("", "   ", "PP", "57.1", "PP.", "PP.abc", "egw:", "invalid:token:123"):
            with self.assertRaises(ValueError):
                normalize_token(bad)

    def test_is_egw_token(self):
        self.assertTrue(is_egw_token("egw:PP.57.1"))
        self.assertTrue(is_egw_token("PP.57.1"))
        self.assertTrue(is_egw_token("DA.19"))
        self.assertFalse(is_egw_token("genesis-1-1"))
        self.assertFalse(is_egw_token("John 1:1"))
        self.assertFalse(is_egw_token(""))


class EgwDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_egw.db"
        self.db = EgwDB(db_path=self.db_path)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_init_and_exists(self):
        self.assertFalse(self.db.exists())
        self.db.init_db()
        self.assertTrue(self.db.exists())
        self.assertEqual(self.db.count(), 0)

    def test_insert_and_get_paragraph(self):
        self.db.insert_paragraph(
            book_code="PP",
            page=57,
            paragraph=1,
            text="They heard the voice of the Lord God walking in the garden.",
            chapter_num=3,
            chapter_title="The Temptation and Fall",
        )
        self.assertEqual(self.db.count(), 1)

        # Lookup with canonical ID
        p1 = self.db.get_paragraph("PP.57.1")
        self.assertIsNotNone(p1)
        self.assertEqual(p1["id"], "PP.57.1")
        self.assertEqual(p1["book_code"], "PP")
        self.assertEqual(p1["book_title"], "Patriarchs and Prophets")
        self.assertEqual(p1["chapter_num"], 3)
        self.assertIn("voice of the Lord God", p1["text"])

        # Lookup with egw: prefix
        p2 = self.db.get_paragraph("egw:PP.57.1")
        self.assertEqual(p1["id"], p2["id"])

        # Non-existent paragraph
        p3 = self.db.get_paragraph("PP.999.1")
        self.assertIsNone(p3)

    def test_get_page_ordered_by_paragraph(self):
        self.db.insert_paragraph("PP", 45, 2, "Second paragraph")
        self.db.insert_paragraph("PP", 45, 1, "First paragraph")
        self.db.insert_paragraph("PP", 46, 1, "Next page paragraph")

        paras = self.db.get_page("PP", 45)
        self.assertEqual(len(paras), 2)
        self.assertEqual(paras[0]["paragraph"], 1)
        self.assertEqual(paras[1]["paragraph"], 2)

    def test_fts5_search(self):
        seed_core_genesis_passages(self.db)
        self.assertEqual(self.db.count(), 8)

        # Search by keyword
        res = self.db.search("enmity")
        self.assertTrue(len(res) >= 1)
        self.assertEqual(res[0]["id"], "PP.66.1")
        self.assertIn("snippet", res[0])

        # Filter by book
        res_book = self.db.search("Sabbath", book_code="PP")
        self.assertTrue(len(res_book) >= 1)
        self.assertEqual(res_book[0]["id"], "PP.47.1")

        # Non-matching search
        res_empty = self.db.search("nonexistenttermXYZ")
        self.assertEqual(res_empty, [])

    def test_ingest_json(self):
        json_file = Path(self.temp_dir.name) / "import.json"
        data = [
            {
                "book_code": "DA",
                "page": 19,
                "paragraph": 1,
                "text": "His name shall be called Emmanuel... God with us.",
                "chapter_title": "God With Us",
            },
            {
                "book_code": "DA",
                "page": 19,
                "paragraph": 2,
                "text": "The light of the knowledge of the glory of God is seen in the face of Jesus Christ.",
            },
        ]
        json_file.write_text(json.dumps(data), encoding="utf-8")

        count = self.db.ingest_json(json_file)
        self.assertEqual(count, 2)
        self.assertEqual(self.db.count(), 2)
        p = self.db.get_paragraph("egw:DA.19.1")
        self.assertIsNotNone(p)
        self.assertIn("Emmanuel", p["text"])

    def test_format_paragraph(self):
        self.db.insert_paragraph(
            book_code="SC",
            page=15,
            paragraph=1,
            text="Nature and revelation alike testify of God's love.",
            book_title="Steps to Christ",
            chapter_num=1,
            chapter_title="God's Love for Man",
        )
        p = self.db.get_paragraph("SC.15.1")
        formatted = self.db.format_paragraph(p)
        self.assertIn("[SC 15.1] (egw:SC.15.1)", formatted)
        self.assertIn("Steps to Christ", formatted)
        self.assertIn("Chapter 1: God's Love for Man", formatted)
        self.assertIn("Nature and revelation alike testify", formatted)


class EgwCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "cli_egw.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(CLI_SCRIPT), "--db", str(self.db_path), *args]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_cli_seed_and_stats(self):
        res = self._run_cli("--seed-core")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Seeded 8 core Genesis study paragraphs", res.stdout)

        res_stats = self._run_cli("--stats")
        self.assertEqual(res_stats.returncode, 0)
        self.assertIn("Total paragraphs: 8", res_stats.stdout)
        self.assertIn("PP (Patriarchs and Prophets)", res_stats.stdout)

    def test_cli_token_lookup(self):
        self._run_cli("--seed-core")
        res = self._run_cli("PP.57.1")
        self.assertEqual(res.returncode, 0)
        self.assertIn("voice of the Lord God walking in the garden", res.stdout)

    def test_cli_search(self):
        self._run_cli("--seed-core")
        res = self._run_cli("--search", "sacrificial offerings")
        self.assertEqual(res.returncode, 0)
        self.assertIn("PP.68.1", res.stdout)
        self.assertIn("The Plan of Redemption", res.stdout)

    def test_cli_invalid_token(self):
        res = self._run_cli("invalid-token")
        self.assertEqual(res.returncode, 1)
        self.assertIn("Invalid EGW citation token", res.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
