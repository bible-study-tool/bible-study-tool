"""Unit tests for Spirit of Prophecy (EGW) bulk importer & parsers (ADR-0011, ADR-0013)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from search.linking.egw import EgwDB
from search.linking.egw_importer import (
    BulkImporter,
    EpubParser,
    TextParagraphParser,
    detect_book_code,
    parse_roman,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SCRIPT = REPO_ROOT / "scripts" / "egw_lookup.py"


class RomanNumeralTests(unittest.TestCase):
    def test_valid_numerals(self):
        self.assertEqual(parse_roman("I"), 1)
        self.assertEqual(parse_roman("IV"), 4)
        self.assertEqual(parse_roman("VIII"), 8)
        self.assertEqual(parse_roman("IX"), 9)
        self.assertEqual(parse_roman("XIV"), 14)
        self.assertEqual(parse_roman("XX"), 20)
        self.assertEqual(parse_roman("XL"), 40)
        self.assertEqual(parse_roman("L"), 50)

    def test_invalid_numerals(self):
        self.assertIsNone(parse_roman("ABC"))
        self.assertIsNone(parse_roman(""))
        self.assertIsNone(parse_roman("123"))


class BookCodeDetectionTests(unittest.TestCase):
    def test_exact_codes(self):
        self.assertEqual(detect_book_code("PP"), "PP")
        self.assertEqual(detect_book_code("DA"), "DA")
        self.assertEqual(detect_book_code("gc"), "GC")

    def test_filename_patterns(self):
        self.assertEqual(detect_book_code("PP.txt"), "PP")
        self.assertEqual(detect_book_code("DA_1898.epub"), "DA")
        self.assertEqual(detect_book_code("GC-volume.json"), "GC")
        self.assertEqual(detect_book_code("steps to christ.txt"), "SC")

    def test_title_substrings(self):
        self.assertEqual(detect_book_code("Patriarchs and Prophets 1890 Edition"), "PP")
        self.assertEqual(detect_book_code("The Desire of Ages"), "DA")
        self.assertEqual(detect_book_code("Thoughts from the Mount of Blessing"), "MB")


class TextParagraphParserTests(unittest.TestCase):
    def test_parse_with_inline_tokens(self):
        sample = """
        {PP 57.1} They heard the voice of the Lord God walking in the garden.
        No longer did Adam greet the presence of God with joy.

        {PP 57.2} The love of God still pleaded for those who had fallen.
        """
        parser = TextParagraphParser(default_book_code="PP")
        paragraphs = parser.parse(sample)
        self.assertEqual(len(paragraphs), 2)
        self.assertEqual(paragraphs[0]["book_code"], "PP")
        self.assertEqual(paragraphs[0]["page"], 57)
        self.assertEqual(paragraphs[0]["paragraph"], 1)
        self.assertIn("They heard the voice", paragraphs[0]["text"])
        self.assertEqual(paragraphs[1]["page"], 57)
        self.assertEqual(paragraphs[1]["paragraph"], 2)

    def test_parse_with_page_markers_and_chapters(self):
        sample = """
        Chapter 2: The Creation

        [Page 44]
        The earth came forth from the hand of its Maker surpassing lovely.

        Its surface was gracefully diversified with hills and valleys.

        [Page 45]
        And God saw everything that He had made, and, behold, it was very good.
        """
        parser = TextParagraphParser(default_book_code="PP")
        paragraphs = parser.parse(sample)
        self.assertEqual(len(paragraphs), 3)

        self.assertEqual(paragraphs[0]["chapter_num"], 2)
        self.assertEqual(paragraphs[0]["chapter_title"], "The Creation")
        self.assertEqual(paragraphs[0]["page"], 44)
        self.assertEqual(paragraphs[0]["paragraph"], 1)
        self.assertIn("Maker surpassing lovely", paragraphs[0]["text"])

        self.assertEqual(paragraphs[1]["page"], 44)
        self.assertEqual(paragraphs[1]["paragraph"], 2)

        self.assertEqual(paragraphs[2]["page"], 45)
        self.assertEqual(paragraphs[2]["paragraph"], 1)
        self.assertIn("very good", paragraphs[2]["text"])


class EpubParserTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.epub_path = Path(self.temp_dir.name) / "test_book.epub"

        # Create a valid synthetic EPUB archive
        with zipfile.ZipFile(self.epub_path, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr(
                "META-INF/container.xml",
                """<?xml version="1.0"?>
                <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                  <rootfiles>
                    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
                  </rootfiles>
                </container>
                """,
            )
            zf.writestr(
                "OEBPS/content.opf",
                """<?xml version="1.0"?>
                <package version="2.0" xmlns="http://www.idpf.org/2007/opf">
                  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
                    <dc:title>Steps to Christ</dc:title>
                    <dc:creator>Ellen G. White</dc:creator>
                  </metadata>
                  <manifest>
                    <item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
                  </manifest>
                  <spine>
                    <itemref idref="c1"/>
                  </spine>
                </package>
                """,
            )
            zf.writestr(
                "OEBPS/chapter1.xhtml",
                """<?xml version="1.0" encoding="utf-8"?>
                <html xmlns="http://www.w3.org/1999/xhtml">
                  <body>
                    <h1>God's Love for Man</h1>
                    <span id="page_9"/>
                    <p>Nature and revelation alike testify of God's love.</p>
                    <p>Our Father in heaven is the source of life, of wisdom, and of joy.</p>
                    <span id="page_10"/>
                    <p>Look at the wonderful and beautiful things of nature.</p>
                  </body>
                </html>
                """,
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_epub(self):
        parser = EpubParser()
        paragraphs = parser.parse(self.epub_path)
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual(paragraphs[0]["book_code"], "SC")
        self.assertEqual(paragraphs[0]["chapter_title"], "God's Love for Man")
        self.assertEqual(paragraphs[0]["page"], 9)
        self.assertEqual(paragraphs[0]["paragraph"], 1)
        self.assertIn("Nature and revelation alike", paragraphs[0]["text"])

        self.assertEqual(paragraphs[1]["page"], 9)
        self.assertEqual(paragraphs[1]["paragraph"], 2)

        self.assertEqual(paragraphs[2]["page"], 10)
        self.assertEqual(paragraphs[2]["paragraph"], 1)
        self.assertIn("wonderful and beautiful things", paragraphs[2]["text"])


class FastBulkInsertTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_bulk.db"
        self.db = EgwDB(db_path=self.db_path)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_fast_bulk_insert_and_search(self):
        # Generate 200 paragraphs
        items = [
            {
                "book_code": "DA",
                "book_title": "The Desire of Ages",
                "page": 19 + (i // 5),
                "paragraph": (i % 5) + 1,
                "chapter_num": 1,
                "chapter_title": "God With Us",
                "text": f"His name shall be called Immanuel, God with us paragraph {i}.",
            }
            for i in range(200)
        ]
        n = self.db.fast_bulk_insert(items, batch_size=50)
        self.assertEqual(n, 200)
        self.assertEqual(self.db.count(), 200)

        # FTS5 search works immediately
        results = self.db.search("Immanuel paragraph 42")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "DA.27.3")

    def test_importer_with_directory(self):
        # Create a directory with multiple files
        doc_dir = Path(self.temp_dir.name) / "docs"
        doc_dir.mkdir()

        # Text file 1
        t1 = doc_dir / "PP.txt"
        t1.write_text("{PP 44.1} Creation week was lovely.\n\n{PP 44.2} Hills and valleys.")

        # Text file 2
        t2 = doc_dir / "SC.txt"
        t2.write_text("[Page 9]\nGod is love.\n\nNature testifies of it.")

        importer = BulkImporter(self.db)
        res = importer.import_directory(doc_dir)
        self.assertEqual(len(res), 2)
        self.assertEqual(res["PP.txt"], 2)
        self.assertEqual(res["SC.txt"], 2)
        self.assertEqual(self.db.count(), 4)


class CliImporterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "cli_test.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_ingest_file(self):
        txt_path = Path(self.temp_dir.name) / "test_sc.txt"
        txt_path.write_text("[Page 15]\nConscience is awakened by the Holy Spirit.")

        res = subprocess.run(
            [
                sys.executable,
                str(CLI_SCRIPT),
                "--db",
                str(self.db_path),
                "--ingest-file",
                str(txt_path),
                "--book",
                "SC",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Successfully ingested 1 paragraphs", res.stdout)

        # Query token via CLI
        res2 = subprocess.run(
            [
                sys.executable,
                str(CLI_SCRIPT),
                "--db",
                str(self.db_path),
                "SC.15.1",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res2.returncode, 0, res2.stderr)
        self.assertIn("Conscience is awakened", res2.stdout)

    def test_gutenberg_banner_stripping(self):
        sample = """
        *** START OF THE PROJECT GUTENBERG EBOOK EDUCATION ***
        [Page 13]
        True education means more than the pursual of a certain course of study.
        It has to do with the whole being.
        *** END OF THE PROJECT GUTENBERG EBOOK EDUCATION ***
        """
        parser = TextParagraphParser(default_book_code="ED")
        paragraphs = parser.parse(sample)
        self.assertEqual(len(paragraphs), 1)
        self.assertEqual(paragraphs[0]["book_code"], "ED")
        self.assertEqual(paragraphs[0]["page"], 13)
        self.assertIn("True education means more than", paragraphs[0]["text"])
        self.assertNotIn("START OF THE PROJECT", paragraphs[0]["text"])
        self.assertNotIn("END OF THE PROJECT", paragraphs[0]["text"])

    def test_epub_unpaginated_multi_chapter_accumulates(self):
        epub_path = Path(self.temp_dir.name) / "unpaginated.epub"
        with zipfile.ZipFile(epub_path, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr(
                "META-INF/container.xml",
                """<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                  <rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>
                </container>""",
            )
            zf.writestr(
                "content.opf",
                """<package version="2.0" xmlns="http://www.idpf.org/2007/opf">
                  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Education</dc:title></metadata>
                  <manifest>
                    <item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
                    <item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
                  </manifest>
                  <spine><itemref idref="c1"/><itemref idref="c2"/></spine>
                </package>""",
            )
            zf.writestr("ch1.xhtml", "<html><body><p>Chapter 1 Paragraph 1</p><p>Chapter 1 Paragraph 2</p></body></html>")
            zf.writestr("ch2.xhtml", "<html><body><p>Chapter 2 Paragraph 1</p></body></html>")

        parser = EpubParser(default_book_code="ED")
        paragraphs = parser.parse(epub_path)
        self.assertEqual(len(paragraphs), 3)
        # Verify paragraph numbers increment rather than resetting to 1 and overwriting
        self.assertEqual([p["paragraph"] for p in paragraphs], [1, 2, 3])


class AnchorVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_anchors.db"
        self.db = EgwDB(db_path=self.db_path)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_anchor_match(self):
        self.db.insert_paragraph(
            book_code="PP",
            page=57,
            paragraph=1,
            text="They heard the voice of the Lord God walking in the garden in the cool of the day.",
        )
        from search.linking.egw_importer import verify_book_anchors
        results = verify_book_anchors(self.db, book_code="PP")
        pp57 = next(r for r in results if r["token"] == "PP.57.1")
        self.assertEqual(pp57["status"], "match")

    def test_anchor_mismatch_warning(self):
        self.db.insert_paragraph(
            book_code="PP",
            page=57,
            paragraph=1,
            text="Some completely different edition text or preface material here.",
        )
        from search.linking.egw_importer import verify_book_anchors
        results = verify_book_anchors(self.db, book_code="PP")
        pp57 = next(r for r in results if r["token"] == "PP.57.1")
        self.assertEqual(pp57["status"], "mismatch")
        self.assertIn("Anchor mismatch on PP.57.1", pp57["message"])


class PublicDomainHarvesterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_harvest.db"
        self.db = EgwDB(db_path=self.db_path)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_catalog_inventory(self):
        from search.linking.egw_importer import PUBLIC_DOMAIN_SOURCES
        core_expected = {"PP", "PK", "DA", "AA", "GC", "SC", "COL", "MB", "MH", "ED"}
        for code in core_expected:
            self.assertIn(code, PUBLIC_DOMAIN_SOURCES)
            spec = PUBLIC_DOMAIN_SOURCES[code]
            self.assertTrue(spec["url"].startswith("https://"))
            self.assertEqual(spec["book_code"], code)

    def test_unknown_work_raises_value_error(self):
        from search.linking.egw_importer import harvest_public_domain
        with self.assertRaises(ValueError) as ctx:
            harvest_public_domain("UNKNOWN_BOOK_XYZ", self.db, dest_dir=self.temp_dir.name)
        self.assertIn("Unknown public-domain work", str(ctx.exception))

    def test_harvest_with_cached_local_file(self):
        from search.linking.egw_importer import harvest_public_domain
        # Create a mock cached text file for ED-TXT
        dest_dir = Path(self.temp_dir.name) / "sources"
        dest_dir.mkdir(parents=True, exist_ok=True)
        cached_file = dest_dir / "ED-TXT.txt"
        cached_file.write_text(
            "*** START OF THE PROJECT GUTENBERG EBOOK ***\n\n"
            "True education means more than the pursual of a certain course of study.\n\n"
            "It has to do with the whole being.\n\n"
            "*** END OF THE PROJECT GUTENBERG EBOOK ***\n",
            encoding="utf-8",
        )
        results = harvest_public_domain("ED-TXT", self.db, dest_dir=dest_dir)
        self.assertIn("ED-TXT", results)
        self.assertEqual(results["ED-TXT"], 2)
        self.assertEqual(self.db.count(), 2)

    def test_all_code_expansion(self):
        from search.linking.egw_importer import PUBLIC_DOMAIN_SOURCES
        epub_keys = [k for k, v in PUBLIC_DOMAIN_SOURCES.items() if v.get("format") == "epub"]
        self.assertEqual(len(epub_keys), 10)
        self.assertIn("PP", epub_keys)
        self.assertIn("DA", epub_keys)
        self.assertIn("GC", epub_keys)
        self.assertNotIn("ED-TXT", epub_keys)

    def test_multi_work_harvest_and_fts_search(self):
        from search.linking.egw_importer import harvest_public_domain
        dest_dir = Path(self.temp_dir.name) / "sources"
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "ED-TXT.txt").write_text(
            "*** START OF THE PROJECT GUTENBERG EBOOK ***\n\n"
            "True education means more than the pursual of study.\n\n"
            "*** END OF THE PROJECT GUTENBERG EBOOK ***",
            encoding="utf-8",
        )
        (dest_dir / "GC-1888.txt").write_text(
            "*** START OF THE PROJECT GUTENBERG EBOOK ***\n\n"
            "The great controversy between Christ and Satan began in heaven.\n\n"
            "*** END OF THE PROJECT GUTENBERG EBOOK ***",
            encoding="utf-8",
        )
        results = harvest_public_domain("ED-TXT,GC-1888", self.db, dest_dir=dest_dir, fast=True)
        self.assertEqual(results.get("ED-TXT"), 1)
        self.assertEqual(results.get("GC-1888"), 1)
        self.assertEqual(self.db.count(), 2)

        # Verify FTS5 rebuild succeeded and BM25 search works
        hits = self.db.search("education")
        self.assertGreaterEqual(len(hits), 1)
        self.assertIn("education", hits[0]["snippet"].lower())

    def test_deduplication_of_work_codes(self):
        from search.linking.egw_importer import harvest_public_domain
        dest_dir = Path(self.temp_dir.name) / "sources"
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "ED-TXT.txt").write_text(
            "*** START OF THE PROJECT GUTENBERG EBOOK ***\n\n"
            "Sample text for deduplication test.\n\n"
            "*** END OF THE PROJECT GUTENBERG EBOOK ***",
            encoding="utf-8",
        )
        results = harvest_public_domain(["ED-TXT", "ED-TXT"], self.db, dest_dir=dest_dir)
        self.assertEqual(list(results.keys()), ["ED-TXT"])
        self.assertEqual(self.db.count(), 1)

    def test_cli_list_sources(self):
        res = subprocess.run(
            [sys.executable, str(CLI_SCRIPT), "--list-sources"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Patriarchs and Prophets", res.stdout)
        self.assertIn("The Desire of Ages", res.stdout)
        self.assertIn("Steps to Christ", res.stdout)


if __name__ == "__main__":
    unittest.main()
