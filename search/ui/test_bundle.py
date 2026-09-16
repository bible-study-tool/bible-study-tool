"""Unit and integration tests for release data bundling and integrity verification (WP-029 Phase 2)."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from search.resource import verify_data_bundle
from search.testutil import require_raw_sources


class DataBundleVerificationTests(unittest.TestCase):
    """Test cryptographic verification of data bundles via verify_data_bundle."""

    def test_verify_bundle_missing_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            is_valid, errors = verify_data_bundle(Path(td))
            self.assertFalse(is_valid)
            self.assertTrue(any("SHA256SUMS not found" in err for err in errors))

    def test_verify_bundle_valid_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db1 = root / "bible.db"
            db1.write_text("sqlite database 1 content", encoding="utf-8")
            hash1 = hashlib.sha256(db1.read_bytes()).hexdigest()

            lex_dir = root / "lexicons"
            lex_dir.mkdir()
            lex1 = lex_dir / "strongs-lexicon.json"
            lex1.write_text('{"H1": "father"}', encoding="utf-8")
            hash2 = hashlib.sha256(lex1.read_bytes()).hexdigest()

            manifest = root / "SHA256SUMS"
            manifest.write_text(
                f"{hash1}  bible.db\n{hash2}  lexicons/strongs-lexicon.json\n",
                encoding="utf-8",
            )

            is_valid, errors = verify_data_bundle(root)
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])

    def test_verify_bundle_coreutils_binary_mode_and_backslashes(self):
        """Test parsing of sha256sum binary mode (*) and Windows backslashes."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db1 = root / "bible.db"
            db1.write_text("sqlite database binary content", encoding="utf-8")
            hash1 = hashlib.sha256(db1.read_bytes()).hexdigest()

            lex_dir = root / "lexicons"
            lex_dir.mkdir()
            lex1 = lex_dir / "strongs.json"
            lex1.write_text('{"H1": "father"}', encoding="utf-8")
            hash2 = hashlib.sha256(lex1.read_bytes()).hexdigest()

            manifest = root / "SHA256SUMS"
            manifest.write_text(
                f"{hash1} *bible.db\n{hash2}  lexicons\\strongs.json\n",
                encoding="utf-8",
            )

            is_valid, errors = verify_data_bundle(root)
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])

    def test_verify_bundle_rejects_path_traversal(self):
        """Test that directory traversal sequences in SHA256SUMS are rejected."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dummy_hash = "a" * 64
            manifest = root / "SHA256SUMS"
            manifest.write_text(
                f"{dummy_hash}  ../secret.txt\n{dummy_hash}  /etc/shadow\n",
                encoding="utf-8",
            )

            is_valid, errors = verify_data_bundle(root)
            self.assertFalse(is_valid)
            self.assertTrue(any("Invalid path traversal" in err for err in errors))

    def test_verify_bundle_malformed_hash(self):
        """Test rejection of malformed hash strings."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "file.txt").write_text("hello", encoding="utf-8")
            manifest = root / "SHA256SUMS"
            manifest.write_text(
                "not-a-valid-sha256-hash  file.txt\n",
                encoding="utf-8",
            )

            is_valid, errors = verify_data_bundle(root)
            self.assertFalse(is_valid)
            self.assertTrue(any("Malformed SHA-256 hash" in err for err in errors))

    def test_verify_bundle_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db1 = root / "bible.db"
            db1.write_text("corrupted content", encoding="utf-8")

            manifest = root / "SHA256SUMS"
            manifest.write_text(
                "0000000000000000000000000000000000000000000000000000000000000000  bible.db\n",
                encoding="utf-8",
            )

            is_valid, errors = verify_data_bundle(root)
            self.assertFalse(is_valid)
            self.assertTrue(any("Checksum mismatch" in err for err in errors))

    def test_verify_bundle_missing_referenced_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = root / "SHA256SUMS"
            manifest.write_text(
                "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789  missing.db\n",
                encoding="utf-8",
            )

            is_valid, errors = verify_data_bundle(root)
            self.assertFalse(is_valid)
            self.assertTrue(any("Missing bundle file" in err for err in errors))

    def test_verify_bundle_sibling_lexicons_fallback(self):
        """Test verification when lexicons are in sibling directory (developer repo layout)."""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            data_dir = base / "data"
            data_dir.mkdir()
            lex_dir = base / "lexicons"
            lex_dir.mkdir()

            db = data_dir / "bible.db"
            db.write_text("db content", encoding="utf-8")
            hash_db = hashlib.sha256(db.read_bytes()).hexdigest()

            lex = lex_dir / "strongs.json"
            lex.write_text("lex content", encoding="utf-8")
            hash_lex = hashlib.sha256(lex.read_bytes()).hexdigest()

            manifest = data_dir / "SHA256SUMS"
            manifest.write_text(
                f"{hash_db}  bible.db\n{hash_lex}  lexicons/strongs.json\n",
                encoding="utf-8",
            )

            is_valid, errors = verify_data_bundle(data_dir)
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])

    def test_verify_bundle_content_layer_with_integrity_manifest(self):
        """Layer 1 (content) path: DBs verified via INTEGRITY.json, not bytes.

        The DB file bytes here are arbitrary text; only the canonical content
        hash in INTEGRITY.json matters. Byte entries for the DBs in SHA256SUMS
        are ignored when INTEGRITY.json exists (ADR-027 two-layer model).
        """
        import json
        import sqlite3

        from search.validation.db_integrity import check_manifest, generate_manifest

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            # A real DB with the canonical bible.db shape (1 row per table).
            db = root / "bible.db"
            conn = sqlite3.connect(str(db))
            conn.executescript(
                """
                CREATE TABLE books (osis TEXT PRIMARY KEY, order_num INT, name TEXT);
                CREATE TABLE translations (id TEXT PRIMARY KEY, name TEXT, year INT, is_default INT);
                CREATE TABLE verses (id TEXT PRIMARY KEY, osis TEXT, chapter INT, verse INT, text TEXT);
                CREATE TABLE translation_verses (translation_id TEXT, verse_id TEXT, osis TEXT, chapter INT, verse INT, text TEXT, PRIMARY KEY (translation_id, verse_id));
                CREATE TABLE cross_references (from_verse TEXT, to_verse TEXT, votes INT, PRIMARY KEY (from_verse, to_verse));
                INSERT INTO books VALUES ('Gen', 1, 'Genesis');
                INSERT INTO translations VALUES ('kjv', 'King James', 1769, 1);
                INSERT INTO verses VALUES ('Gen.1.1', 'Gen.1.1', 1, 1, 'In the beginning God created');
                INSERT INTO translation_verses VALUES ('kjv', 'Gen.1.1', 'Gen.1.1', 1, 1, 'In the beginning God created');
                INSERT INTO cross_references VALUES ('Gen.1.1', 'John.1.1', 378);
                """
            )
            conn.commit()
            conn.close()

            # A real DB with the canonical macula.db shape (needed for both
            # entries in the content manifest).
            macula = root / "macula.db"
            conn = sqlite3.connect(str(macula))
            conn.executescript(
                """
                CREATE TABLE verses (id TEXT PRIMARY KEY, book_code TEXT, chapter INT, verse INT, text TEXT);
                CREATE TABLE clauses (id TEXT PRIMARY KEY, verse_id TEXT, clause_num INT, rule TEXT);
                CREATE TABLE constituents (id TEXT PRIMARY KEY, clause_id TEXT, verse_id TEXT, constituent_num INT, role TEXT, role_label TEXT, class TEXT, text TEXT);
                CREATE TABLE tokens (id TEXT PRIMARY KEY, constituent_id TEXT, verse_id TEXT, token_num INT, text TEXT, lemma TEXT, morph TEXT, pos TEXT, strongs TEXT, gloss TEXT);
                CREATE TABLE strongs_crosswalk (strongs TEXT PRIMARY KEY, lemmas_json TEXT, occurrences INT);
                INSERT INTO verses VALUES ('Gen.1.1', 'GEN', 1, 1, 'בראשית');
                INSERT INTO clauses VALUES ('c:Gen.1.1:1', 'Gen.1.1', 1, 'cl');
                INSERT INTO constituents VALUES ('c:Gen.1.1:1:1', 'c:Gen.1.1:1', 'Gen.1.1', 1, 'prep', 'preposition', 'prep', 'בְּ');
                INSERT INTO tokens VALUES ('t:Gen.1.1:1', 'c:Gen.1.1:1:1', 'Gen.1.1', 1, 'בְּ', 'b', 'R', 'prep', 'H???', 'in');
                INSERT INTO strongs_crosswalk VALUES ('H7225', '["reshit"]', 1);
                """
            )
            conn.commit()
            conn.close()

            from search.validation.db_integrity import CANONICAL_TABLES

            integrity = root / "INTEGRITY.json"
            generate_manifest(db, macula, integrity)
            # A deliberately WRONG byte hash for bible.db in SHA256SUMS: Layer 1
            # content check must win, so the bundle still verifies.
            sums = root / "SHA256SUMS"
            sums.write_text(
                "0000000000000000000000000000000000000000000000000000000000000000  bible.db\n",
                encoding="utf-8",
            )

            is_valid, errors = verify_data_bundle(root, deep=True)
            self.assertTrue(is_valid, f"content-verified bundle should pass: {errors}")

            # Same manifest, doctored DB content -> content check fails.
            conn = sqlite3.connect(str(db))
            conn.execute("UPDATE verses SET text = 'TAMPERED' WHERE id = 'Gen.1.1'")
            conn.commit()
            conn.close()

            is_valid, errors = verify_data_bundle(root, deep=True)
            self.assertFalse(is_valid)
            self.assertTrue(any("Content mismatch for bible.db" in e for e in errors))


class BuildReleaseDataScriptTests(unittest.TestCase):
    """Test CLI behavior of scripts/build_release_data.sh."""

    def test_script_help(self):
        res = subprocess.run(
            ["bash", "scripts/build_release_data.sh", "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Release Data Bundler", res.stdout)
        self.assertIn("--no-archive", res.stdout)
        self.assertIn("--check", res.stdout)
        self.assertIn("--out-dir", res.stdout)

    def test_script_check_mode_mock(self):
        """Test build_release_data.sh --check against a lightweight mock bundle."""
        with tempfile.TemporaryDirectory() as td:
            mock_dir = Path(td) / "mock_data"
            mock_dir.mkdir()
            sample = mock_dir / "sample.txt"
            sample.write_text("sample content", encoding="utf-8")
            h = hashlib.sha256(b"sample content").hexdigest()
            (mock_dir / "SHA256SUMS").write_text(f"{h}  sample.txt\n", encoding="utf-8")

            res = subprocess.run(
                ["bash", "scripts/build_release_data.sh", "--check", str(mock_dir)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Data bundle integrity verified successfully", res.stdout)

    @require_raw_sources()
    def test_script_build_release_data_e2e(self):
        """End-to-end release data bundle build test (requires raw sources)."""
        with tempfile.TemporaryDirectory() as td:
            tmp_data = Path(td) / "test_data"
            res_build = subprocess.run(
                [
                    "bash",
                    "scripts/build_release_data.sh",
                    "--no-archive",
                    "--out-dir",
                    str(tmp_data),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Release data bundle ready in:", res_build.stdout)
            self.assertTrue((tmp_data / "SHA256SUMS").exists())
            self.assertTrue((tmp_data / "bible.db").exists())
            self.assertTrue((tmp_data / "macula.db").exists())
            self.assertFalse((tmp_data / "egw.db").exists())


if __name__ == "__main__":
    unittest.main()
