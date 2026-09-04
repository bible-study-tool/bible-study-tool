"""Unit tests for the official English EGW corpus harvester (scripts/fetch_egw_corpus.py)."""

from __future__ import annotations

import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import zipfile

from scripts.fetch_egw_corpus import (
    BIOGRAPHIES,
    DEVOTIONALS,
    PERIODICAL_CODES,
    SPECIAL_COLLECTIONS,
    STANDARD_BOOKS,
    download_file,
    get_curated_corpus,
    main,
    resolve_category_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SCRIPT = REPO_ROOT / "scripts" / "fetch_egw_corpus.py"


def _create_minimal_epub(zip_path: Path, title: str = "Test Book", paragraphs: list[str] | None = None) -> None:
    paras = paragraphs or ["First paragraph of content.", "Second paragraph of content."]
    p_tags = "\n".join(f"<p>{p}</p>" for p in paras)

    container_xml = """<?xml version="1.0"?>
    <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
      <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
      </rootfiles>
    </container>"""

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
    <package xmlns="http://www.idpf.org/2007/opf" version="3.0">
      <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>{title}</dc:title>
      </metadata>
      <manifest>
        <item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>
      </manifest>
      <spine>
        <itemref idref="chap1"/>
      </spine>
    </package>"""

    chap1_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head><title>{title}</title></head>
      <body>
        <h1>Chapter 1</h1>
        {p_tags}
      </body>
    </html>"""

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        zf.writestr("OEBPS/chap1.xhtml", chap1_xhtml)


class CategoryResolutionTests(unittest.TestCase):
    def test_manuscript_releases_resolution(self):
        self.assertEqual(resolve_category_path("1MR"), Path("02_Manuscript_Releases"))
        self.assertEqual(resolve_category_path("10MR"), Path("02_Manuscript_Releases"))
        self.assertEqual(resolve_category_path("21MR"), Path("02_Manuscript_Releases"))

    def test_periodicals_resolution(self):
        self.assertEqual(resolve_category_path("RH1"), Path("03_Periodical_Articles"))
        self.assertEqual(resolve_category_path("ST4"), Path("03_Periodical_Articles"))
        self.assertEqual(resolve_category_path("YI"), Path("03_Periodical_Articles"))

    def test_special_collections_resolution(self):
        self.assertEqual(resolve_category_path("1888"), Path("04_Special_Collections_and_Sermons"))
        self.assertEqual(resolve_category_path("1SAT"), Path("04_Special_Collections_and_Sermons"))
        self.assertEqual(resolve_category_path("SpM"), Path("04_Special_Collections_and_Sermons"))

    def test_pamphlets_resolution(self):
        self.assertEqual(
            resolve_category_path("SpTA01"),
            Path("05_Pamphlets_and_Special_Testimonies/Special_Testimonies_Series_A"),
        )
        self.assertEqual(
            resolve_category_path("SpTB08"),
            Path("05_Pamphlets_and_Special_Testimonies/Special_Testimonies_Series_B"),
        )
        self.assertEqual(
            resolve_category_path("SpTEd"),
            Path("05_Pamphlets_and_Special_Testimonies"),
        )
        self.assertEqual(
            resolve_category_path("PH001"),
            Path("05_Pamphlets_and_Special_Testimonies/Numbered_Pamphlets"),
        )

    def test_devotionals_and_biographies_resolution(self):
        self.assertEqual(resolve_category_path("AG"), Path("01_Books_and_Compilations/Devotionals"))
        self.assertEqual(resolve_category_path("Mar"), Path("01_Books_and_Compilations/Devotionals"))
        self.assertEqual(resolve_category_path("1BIO"), Path("01_Books_and_Compilations/Biographies"))
        self.assertEqual(resolve_category_path("LS"), Path("01_Books_and_Compilations/Biographies"))

    def test_standard_books_resolution(self):
        self.assertEqual(resolve_category_path("PP"), Path("01_Books_and_Compilations"))
        self.assertEqual(resolve_category_path("DA"), Path("01_Books_and_Compilations"))
        self.assertEqual(resolve_category_path("GC"), Path("01_Books_and_Compilations"))


class CuratedCorpusInventoryTests(unittest.TestCase):
    def test_manuscript_releases_count(self):
        corpus = get_curated_corpus("manuscripts")
        self.assertEqual(len(corpus), 21)
        self.assertIn("1MR", corpus)
        self.assertIn("10MR", corpus)
        self.assertIn("21MR", corpus)

    def test_devotionals_count(self):
        corpus = get_curated_corpus("devotionals")
        self.assertEqual(len(corpus), len(DEVOTIONALS))
        self.assertIn("AG", corpus)
        self.assertIn("YRP", corpus)

    def test_biographies_count(self):
        corpus = get_curated_corpus("biographies")
        self.assertEqual(len(corpus), len(BIOGRAPHIES))
        self.assertIn("1BIO", corpus)
        self.assertIn("LS", corpus)

    def test_periodicals_count(self):
        corpus = get_curated_corpus("periodicals")
        self.assertEqual(len(corpus), len(PERIODICAL_CODES))
        self.assertIn("RH1", corpus)
        self.assertIn("ST1", corpus)

    def test_special_collections_count(self):
        corpus = get_curated_corpus("special")
        self.assertEqual(len(corpus), len(SPECIAL_COLLECTIONS))
        self.assertIn("1888", corpus)
        self.assertIn("2SAT", corpus)

    def test_pamphlets_count(self):
        corpus = get_curated_corpus("pamphlets")
        self.assertEqual(len(corpus), 212)
        self.assertIn("SpTA01", corpus)
        self.assertIn("SpTB19", corpus)
        self.assertIn("SpTEd", corpus)
        self.assertIn("PH001", corpus)
        self.assertIn("PH180", corpus)

    def test_all_count(self):
        corpus = get_curated_corpus("all")
        self.assertEqual(len(corpus), 414)


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dest_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_skip_valid_cached_file(self):
        epub_file = self.dest_dir / "en_10MR.epub"
        _create_minimal_epub(epub_file)
        res = download_file("http://example.com/en_10MR.epub", epub_file)
        self.assertFalse(res)

    def test_redownload_corrupt_cached_epub(self):
        epub_file = self.dest_dir / "en_10MR.epub"
        epub_file.write_text("not a valid zip file " * 20)

        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr("META-INF/container.xml", "<container/>")
        zip_bytes = mem_zip.getvalue()

        mock_resp = MagicMock()
        mock_resp.read.side_effect = [zip_bytes, b""]
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = download_file("http://example.com/en_10MR.epub", epub_file)
            self.assertTrue(res)
            self.assertTrue(zipfile.is_zipfile(epub_file))

    def test_handle_404_not_found(self):
        target_file = self.dest_dir / "en_PH999.epub"
        http_err = urllib.error.HTTPError("http://example.com", 404, "Not Found", None, None)

        with patch("urllib.request.urlopen", side_effect=http_err):
            res = download_file("http://example.com/en_PH999.epub", target_file)
            self.assertIsNone(res)
            self.assertFalse(target_file.exists())

    def test_retry_on_429_backoff(self):
        target_file = self.dest_dir / "en_10MR.epub"
        err_429 = urllib.error.HTTPError("http://example.com", 429, "Too Many Requests", None, None)

        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
        zip_bytes = mem_zip.getvalue()

        mock_resp = MagicMock()
        mock_resp.read.side_effect = [zip_bytes, b""]
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", side_effect=[err_429, mock_resp]):
            with patch("time.sleep") as mock_sleep:
                res = download_file("http://example.com/en_10MR.epub", target_file, max_retries=2)
                self.assertTrue(res)
                self.assertTrue(mock_sleep.called)

    def test_retry_after_header_handling(self):
        target_file = self.dest_dir / "en_10MR.epub"
        headers_mock = MagicMock()
        headers_mock.get.side_effect = lambda k: "15" if k == "Retry-After" else None
        err_429 = urllib.error.HTTPError("http://example.com", 429, "Too Many Requests", headers_mock, None)

        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
        zip_bytes = mem_zip.getvalue()

        mock_resp = MagicMock()
        mock_resp.read.side_effect = [zip_bytes, b""]
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", side_effect=[err_429, mock_resp]):
            with patch("time.sleep") as mock_sleep:
                res = download_file("http://example.com/en_10MR.epub", target_file, max_retries=2)
                self.assertTrue(res)
                # Sleep should respect the 15s Retry-After header
                mock_sleep.assert_called_with(15)

    def test_retry_on_truncated_zip_incomplete(self):
        target_file = self.dest_dir / "en_10MR.epub"

        # First attempt returns corrupted/truncated stream
        bad_resp = MagicMock()
        bad_resp.read.side_effect = [b"incomplete zip content", b""]
        bad_resp.status = 200
        bad_resp.__enter__.return_value = bad_resp

        # Second attempt returns valid zip
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
        zip_bytes = mem_zip.getvalue()

        good_resp = MagicMock()
        good_resp.read.side_effect = [zip_bytes, b""]
        good_resp.status = 200
        good_resp.__enter__.return_value = good_resp

        with patch("urllib.request.urlopen", side_effect=[bad_resp, good_resp]):
            with patch("time.sleep") as mock_sleep:
                res = download_file("http://example.com/en_10MR.epub", target_file, max_retries=2)
                self.assertTrue(res)
                self.assertTrue(mock_sleep.called)
                self.assertTrue(zipfile.is_zipfile(target_file))

    def test_pdf_magic_header_validation(self):
        pdf_file = self.dest_dir / "en_PP.pdf"

        # Mock urlopen returning HTML error page instead of PDF
        html_resp = MagicMock()
        html_resp.read.side_effect = [b"<!DOCTYPE html><html><body>Error</body></html>", b""]
        html_resp.status = 200
        html_resp.__enter__.return_value = html_resp

        # Valid PDF response
        pdf_resp = MagicMock()
        pdf_resp.read.side_effect = [b"%PDF-1.4\n%real pdf content here", b""]
        pdf_resp.status = 200
        pdf_resp.__enter__.return_value = pdf_resp

        with patch("urllib.request.urlopen", side_effect=[html_resp, pdf_resp]):
            with patch("time.sleep") as mock_sleep:
                res = download_file("http://example.com/en_PP.pdf", pdf_file, max_retries=2)
                self.assertTrue(res)
                self.assertTrue(mock_sleep.called)
                with open(pdf_file, "rb") as pf:
                    self.assertEqual(pf.read(5), b"%PDF-")


class HarvesterCLITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dest_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_dry_run_all(self):
        res = subprocess.run(
            [sys.executable, str(CLI_SCRIPT), "--dry-run", "--dest-dir", str(self.dest_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Official EGW Corpus Harvester (Step 1b)", res.stdout)
        self.assertIn("Selected Works:   414 publication codes", res.stdout)
        self.assertIn("02_Manuscript_Releases/en_10MR.epub", res.stdout)
        self.assertIn("01_Books_and_Compilations/en_PP.epub", res.stdout)

    def test_cli_dry_run_category_manuscripts(self):
        res = subprocess.run(
            [
                sys.executable,
                str(CLI_SCRIPT),
                "--category",
                "manuscripts",
                "--dry-run",
                "--dest-dir",
                str(self.dest_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Selected Works:   21 publication codes", res.stdout)
        self.assertIn("en_1MR.epub", res.stdout)
        self.assertIn("en_21MR.epub", res.stdout)
        self.assertNotIn("en_PP.epub", res.stdout)

    def test_cli_dry_run_single_code(self):
        res = subprocess.run(
            [
                sys.executable,
                str(CLI_SCRIPT),
                "--code",
                "10MR",
                "--dry-run",
                "--dest-dir",
                str(self.dest_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Selected Works:   1 publication codes", res.stdout)
        self.assertIn("02_Manuscript_Releases/en_10MR.epub", res.stdout)

    def test_cli_ingest_into_test_db(self):
        from search.linking.egw import EgwDB

        epub_file = self.dest_dir / "02_Manuscript_Releases" / "en_10MR.epub"
        _create_minimal_epub(
            epub_file,
            title="Manuscript Releases, Vol. 10",
            paragraphs=[
                "{10MR 15.1} Christ is our advocate in the heavenly sanctuary.",
                "{10MR 15.2} Faith looks beyond the visible to the eternal realities.",
            ],
        )

        test_db_path = self.dest_dir / "custom_egw.db"
        test_db = EgwDB(test_db_path, repo_root=REPO_ROOT)
        test_db.init_db()

        # Test CLI ingestion using explicit --db-path
        ret = main([
            "--code", "10MR",
            "--dest-dir", str(self.dest_dir),
            "--db-path", str(test_db_path),
            "--ingest",
        ])
        self.assertEqual(ret, 0)

        db_after = EgwDB(test_db_path, repo_root=self.dest_dir)
        self.assertEqual(db_after.count(), 2)
        row = db_after.get_paragraph("10MR.15.1")
        self.assertIsNotNone(row)
        self.assertIn("heavenly sanctuary", row["text"])

        hits = db_after.search("sanctuary")
        self.assertGreaterEqual(len(hits), 1)
        self.assertEqual(hits[0]["id"], "10MR.15.1")


if __name__ == "__main__":
    unittest.main()
