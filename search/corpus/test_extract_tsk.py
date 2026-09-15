"""Unit and integration tests for Treasury of Scripture Knowledge (TSK) cross-references (WP-035, ADR-026)."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
import zipfile

from search.corpus.extract_kjv import DEFAULT_BIBLE_DB, BibleDB
from search.corpus.extract_tsk import (
    DEFAULT_TSK_ZIP,
    ingest_tsk_cross_references,
    norm_single_ref,
    norm_target_ref,
)
from search.ui.study_service import StudyService


class TestTskNormalization(unittest.TestCase):
    """Test OSIS reference normalization for cross-reference source data."""

    def test_norm_single_ref_standard_books(self):
        self.assertEqual(norm_single_ref("Gen.1.1"), "Gen.1.1")
        self.assertEqual(norm_single_ref("Exod.20.8"), "Exod.20.8")
        self.assertEqual(norm_single_ref("Ps.23.1"), "Ps.23.1")
        self.assertEqual(norm_single_ref("Isa.53.5"), "Isa.53.5")
        self.assertEqual(norm_single_ref("Matt.3.16"), "Matt.3.16")
        self.assertEqual(norm_single_ref("Rev.14.6"), "Rev.14.6")

    def test_norm_single_ref_numbered_books(self):
        self.assertEqual(norm_single_ref("1Sam.2.3"), "1Sam.2.3")
        self.assertEqual(norm_single_ref("2Kgs.4.1"), "2Kgs.4.1")
        self.assertEqual(norm_single_ref("1Chr.1.1"), "1Chr.1.1")
        self.assertEqual(norm_single_ref("1Cor.13.4"), "1Cor.13.4")
        self.assertEqual(norm_single_ref("2Cor.5.17"), "2Cor.5.17")
        self.assertEqual(norm_single_ref("1John.3.16"), "1John.3.16")
        self.assertEqual(norm_single_ref("2Pet.3.9"), "2Pet.3.9")

    def test_norm_single_ref_single_chapter_books(self):
        self.assertEqual(norm_single_ref("Jude.1.24"), "Jude.1.24")
        self.assertEqual(norm_single_ref("Obad.1.1"), "Obad.1.1")
        self.assertEqual(norm_single_ref("Phlm.1.6"), "Phlm.1.6")

    def test_norm_target_ref_single_and_ranges(self):
        self.assertEqual(norm_target_ref("John.1.1"), "John.1.1")
        self.assertEqual(norm_target_ref("Prov.8.22-Prov.8.30"), "Prov.8.22-Prov.8.30")
        self.assertEqual(
            norm_target_ref("1Thess.4.16-1Thess.4.17"),
            "1Thess.4.16-1Thess.4.17",
        )
        self.assertEqual(norm_target_ref("Heb.11.3"), "Heb.11.3")


class TestTskMockIngestion(unittest.TestCase):
    """Test ingestion, indexing, and querying using a controlled mock database."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

        # 1. Create mock cross-references.zip
        self.zip_path = self.dir_path / "mock-cross-references.zip"
        mock_tsv = (
            "from_verse\tto_verse\tvotes\n"
            "Gen.1.1\tJohn.1.1-John.1.3\t378\n"
            "Gen.1.1\tHeb.11.3\t275\n"
            "Gen.1.1\tIsa.45.18\t251\n"
            "Gen.1.1\tPs.33.6\t200\n"
            "John.1.1\tGen.1.1\t378\n"
            "Rev.14.6\tMatt.24.14\t150\n"
        )
        with zipfile.ZipFile(self.zip_path, "w") as zf:
            zf.writestr("cross_references.txt", mock_tsv.encode("utf-8"))

        # 2. Create mock bible.db with verses and books
        self.db_path = self.dir_path / "mock-bible.db"
        con = sqlite3.connect(str(self.db_path))
        con.executescript("""
            CREATE TABLE books (
                osis TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                testament TEXT NOT NULL
            );
            INSERT INTO books VALUES ('Gen', 'Genesis', 'OT');
            INSERT INTO books VALUES ('John', 'John', 'NT');
            INSERT INTO books VALUES ('Heb', 'Hebrews', 'NT');
            INSERT INTO books VALUES ('Isa', 'Isaiah', 'OT');
            INSERT INTO books VALUES ('Ps', 'Psalms', 'OT');
            INSERT INTO books VALUES ('Rev', 'Revelation', 'NT');
            INSERT INTO books VALUES ('Matt', 'Matthew', 'NT');

            CREATE TABLE verses (
                osis TEXT NOT NULL,
                chapter INTEGER NOT NULL,
                verse INTEGER NOT NULL,
                clean_text TEXT NOT NULL,
                PRIMARY KEY (osis, chapter, verse)
            );
            INSERT INTO verses VALUES ('Gen', 1, 1, 'In the beginning God created the heaven and the earth.');
            INSERT INTO verses VALUES ('John', 1, 1, 'In the beginning was the Word, and the Word was with God.');
            INSERT INTO verses VALUES ('Heb', 11, 3, 'Through faith we understand that the worlds were framed by the word of God.');
            INSERT INTO verses VALUES ('Isa', 45, 18, 'For thus saith the LORD that created the heavens;');
            INSERT INTO verses VALUES ('Ps', 33, 6, 'By the word of the LORD were the heavens made;');
            INSERT INTO verses VALUES ('Rev', 14, 6, 'And I saw another angel fly in the midst of heaven;');
            INSERT INTO verses VALUES ('Matt', 24, 14, 'And this gospel of the kingdom shall be preached in all the world;');
        """)
        con.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_mock_ingestion_and_ranking(self):
        count = ingest_tsk_cross_references(
            zip_path=self.zip_path,
            db_path=self.db_path,
            repo_root=self.dir_path,
            force=True,
        )
        self.assertEqual(count, 6)

        bible = BibleDB(self.db_path)
        try:
            # Query Gen 1:1
            xrefs = bible.get_cross_references("Gen.1.1", limit=10)
            self.assertEqual(len(xrefs), 4)

            # Check descending vote order
            self.assertEqual(xrefs[0]["to_verse"], "John.1.1-John.1.3")
            self.assertEqual(xrefs[0]["votes"], 378)
            self.assertIn("In the beginning was the Word", xrefs[0]["preview"])

            self.assertEqual(xrefs[1]["to_verse"], "Heb.11.3")
            self.assertEqual(xrefs[1]["votes"], 275)
            self.assertIn("Through faith we understand", xrefs[1]["preview"])

            self.assertEqual(xrefs[2]["to_verse"], "Isa.45.18")
            self.assertEqual(xrefs[2]["votes"], 251)

            self.assertEqual(xrefs[3]["to_verse"], "Ps.33.6")
            self.assertEqual(xrefs[3]["votes"], 200)

            # Limit bounding
            top2 = bible.get_cross_references("Gen.1.1", limit=2)
            self.assertEqual(len(top2), 2)
            self.assertEqual(top2[0]["to_verse"], "John.1.1-John.1.3")
            self.assertEqual(top2[1]["to_verse"], "Heb.11.3")

            # Min votes threshold
            high_votes = bible.get_cross_references("Gen.1.1", min_votes=260)
            self.assertEqual(len(high_votes), 2)

            # Reciprocal lookup (John 1:1 -> Gen 1:1)
            john_xrefs = bible.get_cross_references("John.1.1")
            self.assertEqual(len(john_xrefs), 1)
            self.assertEqual(john_xrefs[0]["to_verse"], "Gen.1.1")
            self.assertEqual(john_xrefs[0]["votes"], 378)
            self.assertIn("created the heaven", john_xrefs[0]["preview"])

            # Non-existent verse
            empty = bible.get_cross_references("Rev.22.21")
            self.assertEqual(empty, [])
        finally:
            bible.close()


class TestTskWholeBibleIntegration(unittest.TestCase):
    """Integration test against whole-Bible database and TSK dataset."""

    @classmethod
    def setUpClass(cls):
        cls.db_path = Path(DEFAULT_BIBLE_DB)
        if not cls.db_path.is_file():
            cls.has_db = False
            return
        cls.bible = BibleDB(cls.db_path)
        cls.has_db = cls.bible.count()["verses"] >= 31102

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "bible") and cls.bible:
            cls.bible.close()

    def test_whole_bible_cross_references_count(self):
        if not self.has_db:
            self.skipTest("Full 31,102-verse Bible database not present")

        con = sqlite3.connect(str(self.db_path))
        try:
            cur = con.execute("SELECT count(*) FROM cross_references;")
            row_count = cur.fetchone()[0]
            self.assertGreater(row_count, 340000, f"Expected >340,000 cross references, got {row_count}")
        finally:
            con.close()

    def test_genesis_1_1_cross_references(self):
        if not self.has_db:
            self.skipTest("Full 31,102-verse Bible database not present")

        t0 = time.perf_counter()
        xrefs = self.bible.get_cross_references("Gen.1.1", limit=25)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        self.assertGreaterEqual(len(xrefs), 20)
        self.assertLess(elapsed_ms, 10.0, f"Query took {elapsed_ms:.2f}ms, expected <10ms")

        to_refs = [x["to_verse"] for x in xrefs]
        self.assertTrue(any("John.1" in r for r in to_refs), "Expected John 1 in Gen 1:1 cross references")
        self.assertTrue(any("Heb.11" in r for r in to_refs), "Expected Hebrews 11 in Gen 1:1 cross references")

        # Verify preview text populated
        first = xrefs[0]
        self.assertTrue(first["preview"], "Expected preview text on top cross-reference")
        self.assertGreater(first["votes"], 200)

    def test_study_service_cross_references(self):
        if not self.has_db:
            self.skipTest("Full 31,102-verse Bible database not present")

        service = StudyService(bible_db_path=self.db_path)
        xrefs = service.get_verse_cross_references("Gen 1:1", limit=15)
        self.assertEqual(len(xrefs), 15)
        self.assertEqual(xrefs[0]["to_verse"], "John.1.1-John.1.3")

        # Verify get_passage_study attaches cross_references to VerseStudy
        passage = service.get_passage_study("Gen 1:1-2")
        self.assertEqual(len(passage.verses), 2)
        v1 = passage.verses[0]
        self.assertTrue(v1.cross_references, "Expected cross_references on VerseStudy")
        self.assertEqual(v1.cross_references[0]["to_verse"], "John.1.1-John.1.3")


if __name__ == "__main__":
    unittest.main()
