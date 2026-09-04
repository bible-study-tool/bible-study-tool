"""Unit tests for the Portable Offline Backup and Restore engine (ADR-0016)."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest

from search.corpus.backup import (
    CURRENT_BACKUP_VERSION,
    SecurityError,
    calculate_sha256,
    checkpoint_sqlite_db,
    export_backup,
    inspect_backup,
    inspect_sqlite_db,
    is_safe_path,
    restore_backup,
    verify_backup,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SCRIPT = REPO_ROOT / "scripts" / "backup.py"


class BackupEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        self.data_dir = self.test_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create a sample SQLite DB
        self.sample_db = self.data_dir / "sample.db"
        conn = sqlite3.connect(str(self.sample_db))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, title TEXT, body TEXT);")
        conn.execute("INSERT INTO notes (title, body) VALUES ('Day 1', 'Creation study notes');")
        conn.execute("INSERT INTO notes (title, body) VALUES ('Day 2', 'Firmament and waters');")
        conn.commit()
        conn.close()

        # Create sample user data file
        self.sample_note = self.test_dir / "my_notes.txt"
        self.sample_note.write_text("Personal study journal.\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_calculate_sha256(self):
        digest = calculate_sha256(self.sample_note)
        self.assertIsInstance(digest, str)
        self.assertEqual(len(digest), 64)

    def test_checkpoint_sqlite_db(self):
        checkpoint_sqlite_db(self.sample_db)
        # Checkpoint should not fail and database remains queryable
        conn = sqlite3.connect(str(self.sample_db))
        count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        conn.close()
        self.assertEqual(count, 2)

    def test_inspect_sqlite_db(self):
        stats = inspect_sqlite_db(self.sample_db)
        self.assertEqual(stats["file_name"], "sample.db")
        self.assertIn("notes", stats["tables"])
        self.assertEqual(stats["tables"]["notes"], 2)

    def test_is_safe_path(self):
        base = self.test_dir
        safe = self.test_dir / "sub" / "file.txt"
        unsafe = self.test_dir / ".." / "outside.txt"
        self.assertTrue(is_safe_path(base, safe))
        self.assertFalse(is_safe_path(base, unsafe))

    def test_export_and_inspect_backup(self):
        archive_path = self.test_dir / "backup.tar.gz"
        manifest = export_backup(
            output_path=archive_path,
            db_paths=[self.sample_db],
            user_data_paths=[self.sample_note],
            note="Test Backup Archive",
            repo_root=self.test_dir,
        )

        self.assertTrue(archive_path.exists())
        self.assertEqual(manifest["version"], CURRENT_BACKUP_VERSION)
        self.assertEqual(manifest["note"], "Test Backup Archive")
        self.assertEqual(manifest["file_count"], 2)
        self.assertIn("sample.db", manifest["db_stats"])

        # Inspect without extraction
        inspected = inspect_backup(archive_path)
        self.assertEqual(inspected["version"], CURRENT_BACKUP_VERSION)
        self.assertEqual(inspected["file_count"], 2)
        self.assertEqual(len(inspected["files"]), 2)

    def test_verify_backup_clean(self):
        archive_path = self.test_dir / "backup.tar.gz"
        export_backup(
            output_path=archive_path,
            db_paths=[self.sample_db],
            user_data_paths=[self.sample_note],
            repo_root=self.test_dir,
        )

        is_valid, errors = verify_backup(archive_path)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_verify_backup_tampered(self):
        archive_path = self.test_dir / "backup.tar.gz"
        export_backup(
            output_path=archive_path,
            db_paths=[self.sample_db],
            user_data_paths=[self.sample_note],
            repo_root=self.test_dir,
        )

        # Tamper manifest inside archive by reconstructing with mismatched hash
        tampered_archive = self.test_dir / "tampered.tar.gz"
        manifest = inspect_backup(archive_path)
        manifest["files"][0]["sha256"] = "0" * 64  # Fake invalid hash

        with tarfile.open(archive_path, "r:gz") as src_tar, tarfile.open(tampered_archive, "w:gz") as dst_tar:
            for member in src_tar.getmembers():
                if member.name == "backup_manifest.json":
                    new_manifest_bytes = json.dumps(manifest).encode("utf-8")
                    ti = tarfile.TarInfo(name="backup_manifest.json")
                    ti.size = len(new_manifest_bytes)
                    dst_tar.addfile(ti, io.BytesIO(new_manifest_bytes))
                else:
                    dst_tar.addfile(member, src_tar.extractfile(member))

        is_valid, errors = verify_backup(tampered_archive)
        self.assertFalse(is_valid)
        self.assertTrue(any("Checksum mismatch" in e for e in errors))

    def test_restore_backup_success(self):
        archive_path = self.test_dir / "backup.tar.gz"
        export_backup(
            output_path=archive_path,
            db_paths=[self.sample_db],
            user_data_paths=[self.sample_note],
            repo_root=self.test_dir,
        )

        dest_dir = self.test_dir / "restored"
        res = restore_backup(archive_path, target_dir=dest_dir)

        self.assertEqual(res["status"], "restored")
        self.assertEqual(res["files_restored"], 2)

        restored_db = dest_dir / "data" / "sample.db"
        restored_note = dest_dir / "my_notes.txt"

        self.assertTrue(restored_db.exists())
        self.assertTrue(restored_note.exists())
        self.assertEqual(restored_note.read_text(encoding="utf-8"), "Personal study journal.\n")

        # Query restored database
        conn = sqlite3.connect(str(restored_db))
        count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        conn.close()
        self.assertEqual(count, 2)

    def test_restore_refuses_overwrite_without_flag(self):
        archive_path = self.test_dir / "backup.tar.gz"
        export_backup(
            output_path=archive_path,
            db_paths=[self.sample_db],
            repo_root=self.test_dir,
        )

        dest_dir = self.test_dir / "restored"
        restore_backup(archive_path, target_dir=dest_dir)

        # Attempt restore again without overwrite
        with self.assertRaises(FileExistsError):
            restore_backup(archive_path, target_dir=dest_dir, overwrite=False)

        # With overwrite=True, it succeeds
        res = restore_backup(archive_path, target_dir=dest_dir, overwrite=True)
        self.assertEqual(res["status"], "restored")

    def test_restore_dry_run(self):
        archive_path = self.test_dir / "backup.tar.gz"
        export_backup(
            output_path=archive_path,
            db_paths=[self.sample_db],
            repo_root=self.test_dir,
        )

        dest_dir = self.test_dir / "dry_run_target"
        res = restore_backup(archive_path, target_dir=dest_dir, dry_run=True)

        self.assertEqual(res["status"], "dry_run_success")
        self.assertEqual(res["files_to_restore"], 1)
        self.assertFalse((dest_dir / "data" / "sample.db").exists())

    def test_restore_path_traversal_prevention(self):
        malicious_archive = self.test_dir / "malicious.tar.gz"
        content = b"evil"
        manifest_data = {
            "version": CURRENT_BACKUP_VERSION,
            "generator": "test",
            "file_count": 1,
            "files": [
                {
                    "arcname": "payload.txt",
                    "target_relpath": "../../etc/shadow",
                    "size_bytes": len(content),
                    "sha256": "b5c1fb2efc6d6b4674c2fdcc48ce01b43a3b7c03763c0c3355de0099ee0f8c73",
                }
            ],
        }

        with tarfile.open(malicious_archive, "w:gz") as tar:
            m_bytes = json.dumps(manifest_data).encode("utf-8")
            ti = tarfile.TarInfo(name="backup_manifest.json")
            ti.size = len(m_bytes)
            tar.addfile(ti, io.BytesIO(m_bytes))

            ti2 = tarfile.TarInfo(name="payload.txt")
            ti2.size = len(content)
            tar.addfile(ti2, io.BytesIO(content))

        with self.assertRaises(SecurityError):
            restore_backup(malicious_archive, target_dir=self.test_dir)

    def test_restore_arcname_path_traversal_prevention(self):
        malicious_archive = self.test_dir / "malicious_arcname.tar.gz"
        content = b"evil_arcname"
        content_hash = hashlib.sha256(content).hexdigest()
        manifest_data = {
            "version": CURRENT_BACKUP_VERSION,
            "generator": "test",
            "file_count": 1,
            "files": [
                {
                    "arcname": "../../evil_escape.txt",
                    "target_relpath": "data/sample.txt",
                    "size_bytes": len(content),
                    "sha256": content_hash,
                }
            ],
        }

        with tarfile.open(malicious_archive, "w:gz") as tar:
            m_bytes = json.dumps(manifest_data).encode("utf-8")
            ti = tarfile.TarInfo(name="backup_manifest.json")
            ti.size = len(m_bytes)
            tar.addfile(ti, io.BytesIO(m_bytes))

            ti2 = tarfile.TarInfo(name="../../evil_escape.txt")
            ti2.size = len(content)
            tar.addfile(ti2, io.BytesIO(content))

        with self.assertRaises(SecurityError):
            restore_backup(malicious_archive, target_dir=self.test_dir)


class BackupCLITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create dummy database
        self.db_path = self.test_dir / "test.db"
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("CREATE TABLE items (id INTEGER, name TEXT);")
        conn.execute("INSERT INTO items VALUES (1, 'Gen1');")
        conn.commit()
        conn.close()

        self.archive_path = self.test_dir / "backup.tar.gz"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_export_inspect_verify_restore(self):
        # 1. Export via CLI
        res = subprocess.run(
            [
                sys.executable,
                str(CLI_SCRIPT),
                "export",
                "-o",
                str(self.archive_path),
                "--no-egw",
                "--no-corpus",
                "--no-macula",
                "--db",
                str(self.db_path),
                "--note",
                "CLI Integration Test",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Export failed: {res.stderr}")
        self.assertIn("Backup created successfully!", res.stdout)
        self.assertTrue(self.archive_path.exists())

        # 2. Inspect via CLI
        res_insp = subprocess.run(
            [sys.executable, str(CLI_SCRIPT), "inspect", str(self.archive_path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_insp.returncode, 0)
        self.assertIn("CLI Integration Test", res_insp.stdout)
        self.assertIn("test.db", res_insp.stdout)

        # 3. Verify via CLI
        res_ver = subprocess.run(
            [sys.executable, str(CLI_SCRIPT), "verify", str(self.archive_path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_ver.returncode, 0)
        self.assertIn("Archive integrity verified!", res_ver.stdout)

        # 4. Restore via CLI
        restore_dir = self.test_dir / "restored_cli"
        res_res = subprocess.run(
            [
                sys.executable,
                str(CLI_SCRIPT),
                "restore",
                str(self.archive_path),
                "--target-dir",
                str(restore_dir),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_res.returncode, 0, f"Restore failed: {res_res.stderr}")
        self.assertIn("Restore complete!", res_res.stdout)
        self.assertTrue((restore_dir / "data" / "test.db").exists())


if __name__ == "__main__":
    unittest.main()
