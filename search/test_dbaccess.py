"""Tests for sidecar-free source-database reads (ADR-027).

Pins two properties of ``search.dbaccess.connect_db_reader``:

* **Hygiene** -- reading a checkpointed WAL database must not create
  ``-wal``/``-shm`` sidecars next to it (the old ``mode=ro`` URI did).
* **Correctness** -- when a hot WAL exists (uncheckpointed committed frames,
  e.g. an ingest in another process), the reader must see those frames.
  ``immutable=1`` ignores them and would silently read stale content.
"""

from __future__ import annotations

import shutil
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from search.dbaccess import connect_db_reader
from search.validation.db_integrity import compute_db_content_hash


def _sidecars(db_path: Path) -> list[str]:
    return sorted(p.name for p in db_path.parent.glob(f"{db_path.name}-*"))


def _write_wal_db(db_path: Path, rows: list[tuple[int, str]], *, checkpoint: bool) -> sqlite3.Connection:
    """Create a WAL database; returns the still-open writer connection.

    The writer is left open deliberately: SQLite auto-checkpoints when the
    last connection closes, so a hot WAL cannot be observed otherwise.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT);")
    conn.executemany("INSERT INTO t VALUES (?, ?);", rows)
    conn.commit()
    if checkpoint:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    return conn


class ReaderHygieneTests(unittest.TestCase):
    def test_checkpointed_wal_read_creates_no_sidecars(self) -> None:
        with TemporaryDirectory() as td:
            db = Path(td) / "checkpointed.db"
            writer = _write_wal_db(db, [(1, "a"), (2, "b")], checkpoint=True)
            writer.close()
            for sc in _sidecars(db):  # start from the shipped-state invariant
                Path(td, sc).unlink()

            conn = connect_db_reader(db, row_factory=sqlite3.Row)
            try:
                rows = conn.execute("SELECT v FROM t ORDER BY id;").fetchall()
            finally:
                conn.close()
            self.assertEqual([r["v"] for r in rows], ["a", "b"])
            self.assertEqual(_sidecars(db), [], "reader created sidecars")


class ReaderCorrectnessTests(unittest.TestCase):
    def test_hot_wal_frames_are_visible(self) -> None:
        """immutable=1 would return zero rows here; the reader must not."""
        with TemporaryDirectory() as td:
            db = Path(td) / "hot.db"
            writer = _write_wal_db(db, [(1, "a"), (2, "b")], checkpoint=False)
            self.assertGreater(Path(f"{db}-wal").stat().st_size, 0, "test setup: expected hot WAL")
            try:
                conn = connect_db_reader(db)
                try:
                    n = conn.execute("SELECT count(*) FROM t;").fetchone()[0]
                finally:
                    conn.close()
            finally:
                writer.close()
            self.assertEqual(n, 2)

    def test_wal_aware_content_hash_matches_live_state(self) -> None:
        """The integrity gate must hash what readers see, WAL frames included."""
        with TemporaryDirectory() as td:
            db = Path(td) / "hot.db"
            writer = _write_wal_db(db, [(1, "a"), (2, "b")], checkpoint=False)
            try:
                hot = compute_db_content_hash(db, ["t"])
                writer.execute("UPDATE t SET v = 'tampered' WHERE id = 1;")
                writer.commit()
                tampered = compute_db_content_hash(db, ["t"])
            finally:
                writer.close()
            self.assertNotEqual(hot, tampered, "update in hot WAL was invisible to the hash")

    def test_checkpointed_hash_creates_no_sidecars(self) -> None:
        with TemporaryDirectory() as td:
            db = Path(td) / "checkpointed.db"
            writer = _write_wal_db(db, [(1, "a"), (2, "b")], checkpoint=True)
            writer.close()
            for sc in _sidecars(db):
                Path(td, sc).unlink()
            compute_db_content_hash(db, ["t"])
            self.assertEqual(_sidecars(db), [], "hash computation created sidecars")


class WriterCheckpointTests(unittest.TestCase):
    """A write session must not leave hot WAL frames behind (ADR-027 §5)."""

    def test_egw_close_checkpoints_and_fresh_reader_sees_rows(self) -> None:
        from search.linking.egw import EgwDB

        with TemporaryDirectory() as td:
            db_path = Path(td) / "egw.db"
            writer = EgwDB(db_path, repo_root=Path(td))
            writer.insert_paragraphs_batch(
                [
                    {"id": "PP.57.1", "book_code": "PP", "page": 57, "paragraph": 1, "text": "one"},
                    {"id": "PP.57.2", "book_code": "PP", "page": 57, "paragraph": 2, "text": "two"},
                ]
            )
            writer.close()

            wal = Path(f"{db_path}-wal")
            self.assertTrue(not wal.exists() or wal.stat().st_size == 0, "hot WAL left behind")

            # A new object (no in-process writer) must read via the immutable path.
            reader = EgwDB(db_path, repo_root=Path(td))
            try:
                self.assertEqual(reader.count(), 2)
                self.assertEqual(reader.get_paragraph("PP.57.1")["text"], "one")
            finally:
                reader.close()


class ConsumerSidecarTests(unittest.TestCase):
    """Runtime read methods of the DB classes must not litter sidecars (F5)."""

    def _assert_reads_leave_sidecars_untouched(self, tmp: Path, exercise) -> None:
        before = _sidecars_in(tmp)
        exercise()
        self.assertEqual(_sidecars_in(tmp), before, "read path created sidecars")

    def test_egw_read_methods_create_no_sidecars(self) -> None:
        from search.linking.egw import EgwDB

        with TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "egw.db"
            writer = EgwDB(db_path, repo_root=tmp)
            writer.insert_paragraphs_batch(
                [
                    {"id": "PP.56.9", "book_code": "PP", "page": 56, "paragraph": 9, "text": "prev"},
                    {"id": "PP.57.1", "book_code": "PP", "page": 57, "paragraph": 1, "text": "one"},
                    {"id": "PP.58.1", "book_code": "PP", "page": 58, "paragraph": 1, "text": "next"},
                ]
            )
            writer.close()
            for sc in _sidecars_in(tmp):  # normalise to the shipped-clean invariant
                (tmp / sc).unlink()

            reader = EgwDB(db_path, repo_root=tmp)
            try:
                self._assert_reads_leave_sidecars_untouched(
                    tmp,
                    lambda: (
                        reader.exists(),
                        reader.count(),
                        reader.get_paragraph("PP.57.1"),
                        reader.get_page("PP", 57),
                        reader.get_chapter("PP", 57),
                        reader.get_chapter_info("PP", 57),
                        reader.get_chapter_for_token("PP.57.1"),
                        reader.get_adjacent_chapters("PP", 57),
                        reader.search("one"),
                    ),
                )
            finally:
                reader.close()

    def test_macula_read_methods_create_no_sidecars(self) -> None:
        from search.macula.db import MaculaSqliteDB

        source = Path(__file__).resolve().parents[1] / "data" / "macula.db"
        if not source.is_file():
            self.skipTest("data/macula.db not present")
        with TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "macula.db"
            shutil.copyfile(source, db_path)

            reader = MaculaSqliteDB(db_path, repo_root=tmp)
            try:
                self._assert_reads_leave_sidecars_untouched(
                    tmp,
                    lambda: (
                        reader.exists(),
                        reader.counts,
                        reader.lookup_strongs("H7225"),
                        reader.lookup_verse("Gen.1.1"),
                        reader.search_by_domain("168"),
                        reader.search_by_role("subject", limit=10),
                    ),
                )
            finally:
                reader.close()

    def test_bible_read_methods_create_no_sidecars(self) -> None:
        from search.corpus.extract_kjv import BibleDB

        source = Path(__file__).resolve().parents[1] / "data" / "bible.db"
        if not source.is_file():
            self.skipTest("data/bible.db not present")
        with TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "bible.db"
            shutil.copyfile(source, db_path)

            reader = BibleDB(db_path, repo_root=tmp)
            try:
                self._assert_reads_leave_sidecars_untouched(
                    tmp,
                    lambda: (
                        reader.exists(),
                        reader.count(),
                        reader.get_verse("Gen.1.1"),
                        reader.get_passage("Gen.1"),
                        reader.search("beginning"),
                        reader.find_by_strongs("H7225"),
                        reader.list_translations(),
                    ),
                )
            finally:
                reader.close()


def _sidecars_in(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.glob("*.db-*"))


if __name__ == "__main__":
    unittest.main()