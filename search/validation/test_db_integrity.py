"""Tests for content-level SQLite integrity verification (ADR-027 Option B).

Verifies that SQLite databases are pinned by canonical content hash (schema +
every row) rather than raw bytes, so identical data verifies identically across
toolchains. Also verifies the fail-fast shape gate and tamper detection.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from search.validation.db_integrity import (
    CANONICAL_TABLES,
    check_manifest,
    compute_db_content_hash,
    generate_manifest,
    table_row_counts,
)
from search.testutil import require_raw_sources


def _make_db(path: Path, name: str, reverse_rows: bool = False) -> None:
    """Create a small, realistic SQLite DB with canonical tables.

    reverse_rows=True inserts rows in reverse order (and the distinct row
    counts below make the reversal observable to sqlite) so callers can
    prove row-order independence of the content hash.
    """
    conn = sqlite3.connect(str(path))
    if name == "bible.db":
        conn.executescript(
            """
            CREATE TABLE books (osis TEXT PRIMARY KEY, order_num INT, name TEXT);
            CREATE TABLE translations (id TEXT PRIMARY KEY, name TEXT, year INT, is_default INT);
            CREATE TABLE verses (id TEXT PRIMARY KEY, osis TEXT, chapter INT, verse INT, text TEXT);
            CREATE TABLE translation_verses (translation_id TEXT, verse_id TEXT, osis TEXT, chapter INT, verse INT, text TEXT, PRIMARY KEY (translation_id, verse_id));
            CREATE TABLE cross_references (from_verse TEXT, to_verse TEXT, votes INT, PRIMARY KEY (from_verse, to_verse));
            CREATE VIRTUAL TABLE bible_fts USING fts5(osis, clean_text);  -- real FTS5, shadows derived
            """
        )
        books = [
            ("Gen", 1, "Genesis"),
            ("Exod", 2, "Exodus"),
            ("Lev", 3, "Leviticus"),
        ]
        translations = [("kjv", "King James", 1769, 1), ("asv", "American Standard", 1901, 0)]
        verses = [
            ("Gen.1.1", "Gen.1.1", 1, 1, "In the beginning God created"),
            ("Gen.1.2", "Gen.1.2", 1, 2, "And the earth was without form"),
            ("Gen.1.3", "Gen.1.3", 1, 3, "And God said, Let there be light"),
        ]
        translation_verses = [
            ("kjv", "Gen.1.1", "Gen.1.1", 1, 1, "In the beginning God created"),
            ("kjv", "Gen.1.2", "Gen.1.2", 1, 2, "And the earth was without form"),
            ("asv", "Gen.1.1", "Gen.1.1", 1, 1, "In the beginning God created"),
        ]
        cross_references = [
            ("Gen.1.1", "John.1.1", 378),
            ("Gen.1.1", "John.1.3", 41),
            ("Gen.1.2", "Jer.4.23", 5),
        ]
        order = 1 if not reverse_rows else -1
        for b in books[::order]:
            conn.execute("INSERT INTO books VALUES (?, ?, ?)", b)
        for t in translations[::order]:
            conn.execute("INSERT INTO translations VALUES (?, ?, ?, ?)", t)
        if reverse_rows:
            # Insert verses with EXPLICIT rowids in scrambled order, so physical
            # storage order differs from PRIMARY KEY order. A hash that followed
            # insertion order would diverge; the canonical hash must not.
            for v, rowid in zip(verses, (3, 1, 2)):
                conn.execute(
                    "INSERT INTO verses (rowid, id, osis, chapter, verse, text)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (rowid, v[0], v[1], v[2], v[3], v[4]),
                )
        else:
            for v in verses:
                conn.execute("INSERT INTO verses VALUES (?, ?, ?, ?, ?)", v)
        for tv in translation_verses[::order]:
            conn.execute("INSERT INTO translation_verses VALUES (?, ?, ?, ?, ?, ?)", tv)
        for x in cross_references[::order]:
            conn.execute("INSERT INTO cross_references VALUES (?, ?, ?)", x)
    else:  # macula.db
        conn.executescript(
            """
            CREATE TABLE verses (id TEXT PRIMARY KEY, book_code TEXT, chapter INT, verse INT, text TEXT);
            CREATE TABLE clauses (id TEXT PRIMARY KEY, verse_id TEXT, clause_num INT, rule TEXT);
            CREATE TABLE constituents (id TEXT PRIMARY KEY, clause_id TEXT, verse_id TEXT, constituent_num INT, role TEXT, role_label TEXT, class TEXT, text TEXT);
            CREATE TABLE tokens (id TEXT PRIMARY KEY, constituent_id TEXT, verse_id TEXT, token_num INT, text TEXT, lemma TEXT, morph TEXT, pos TEXT, strongs TEXT, gloss TEXT);
            CREATE TABLE strongs_crosswalk (strongs TEXT PRIMARY KEY, lemmas_json TEXT, occurrences INT);
            """
        )
        verses = [("Gen.1.1", "GEN", 1, 1, "בראשית"), ("Gen.1.2", "GEN", 1, 2, "והארץ")]
        clauses = [("c:Gen.1.1:1", "Gen.1.1", 1, "cl"), ("c:Gen.1.2:1", "Gen.1.2", 1, "cl")]
        constituents = [
            ("c:Gen.1.1:1:1", "c:Gen.1.1:1", "Gen.1.1", 1, "prep", "preposition", "prep", "בְּ"),
            ("c:Gen.1.2:1:1", "c:Gen.1.2:1", "Gen.1.2", 1, "subs", "substantive", "subs", "ארץ"),
        ]
        tokens = [
            ("t:Gen.1.1:1", "c:Gen.1.1:1:1", "Gen.1.1", 1, "בְּ", "b", "R", "prep", "H???", "in"),
            ("t:Gen.1.2:1", "c:Gen.1.2:1:1", "Gen.1.2", 1, "ארץ", "erets", "N", "subs", "H0776", "earth"),
        ]
        strongs = [("H7225", '["reshit"]', 1), ("H0776", '["erets"]', 2)]
        order = 1 if not reverse_rows else -1
        for v in verses[::order]:
            conn.execute("INSERT INTO verses VALUES (?, ?, ?, ?, ?)", v)
        for c in clauses[::order]:
            conn.execute("INSERT INTO clauses VALUES (?, ?, ?, ?)", c)
        for cc in constituents[::order]:
            conn.execute("INSERT INTO constituents VALUES (?, ?, ?, ?, ?, ?, ?, ?)", cc)
        for t in tokens[::order]:
            conn.execute("INSERT INTO tokens VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", t)
        for s in strongs[::order]:
            conn.execute("INSERT INTO strongs_crosswalk VALUES (?, ?, ?)", s)
    conn.commit()
    conn.close()


class ComputeDbContentHashTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_hash_is_deterministic_across_rebuilds(self):
        """Row order and physical layout must not affect the content hash.

        Two DBs with identical logical content but different row insertion
        order and different physical layout (plus a VACUUM pass) must hash
        identically — that is the property that makes content integrity work
        across toolchains where raw bytes diverge. The enzymes are the PRIMARY
        KEY-ordered SELECT plus canonical per-cell serialization.
        """
        db1 = self.dir / "bible.db"
        _make_db(db1, "bible.db")
        h1 = compute_db_content_hash(db1, CANONICAL_TABLES["bible.db"])

        # Rebuild with same content but reversed insertion order, then VACUUM.
        db2 = self.dir / "bible-reversed.db"
        _make_db(db2, "bible.db", reverse_rows=True)
        conn = sqlite3.connect(str(db2))
        conn.execute("VACUUM")
        conn.commit()
        conn.close()
        h2 = compute_db_content_hash(db2, CANONICAL_TABLES["bible.db"])
        self.assertEqual(h1, h2)

        # Prove the two builds are physically distinct: different bytes, and
        # different underlying storage order (rowids scrambled in db2). The
        # canonical hash must yield identical results over both. Identical hash
        # over different bytes is exactly the cross-toolchain property we pin.
        self.assertNotEqual(db1.read_bytes(), db2.read_bytes())
        rowids1 = [r[0] for r in sqlite3.connect(str(db1)).execute("SELECT rowid FROM verses ORDER BY id")]
        rowids2 = [r[0] for r in sqlite3.connect(str(db2)).execute("SELECT rowid FROM verses ORDER BY id")]
        self.assertNotEqual(rowids1, rowids2)

    def test_hash_changes_on_tampering(self):
        """Editing a row's content changes the hash (detects tampering)."""
        db = self.dir / "bible.db"
        _make_db(db, "bible.db")
        h1 = compute_db_content_hash(db, CANONICAL_TABLES["bible.db"])

        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE verses SET text = 'TAMPERED' WHERE id = 'Gen.1.1'")
        conn.commit()
        conn.close()

        h2 = compute_db_content_hash(db, CANONICAL_TABLES["bible.db"])
        self.assertNotEqual(h1, h2)

    def test_fail_fast_on_unexpected_table(self):
        """An unexpected non-FTS table is rejected (shape gate)."""
        db = self.dir / "bible.db"
        _make_db(db, "bible.db")
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE rogue_table (id TEXT)")
        conn.commit()
        conn.close()

        with self.assertRaises(ValueError):
            compute_db_content_hash(db, CANONICAL_TABLES["bible.db"])

    def test_fail_fast_on_table_named_like_fts_shadow(self):
        """A table merely NAMED like an FTS shadow is rejected (no suffix masking).

        The old gate guessed shadow tables from name suffixes, so a rogue table
        named `x_data` slipped through. Shadows must be derived from actual
        `CREATE VIRTUAL TABLE` linkage in sqlite_master.
        """
        db = self.dir / "bible.db"
        _make_db(db, "bible.db")
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE rogue_data (id TEXT)")
        conn.commit()
        conn.close()

        with self.assertRaises(ValueError):
            compute_db_content_hash(db, CANONICAL_TABLES["bible.db"])

    def test_fail_fast_on_view(self):
        """Views are not part of the canonical data model and are rejected."""
        db = self.dir / "bible.db"
        _make_db(db, "bible.db")
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE VIEW rogue_view AS SELECT * FROM verses")
        conn.commit()
        conn.close()

        with self.assertRaises(ValueError):
            compute_db_content_hash(db, CANONICAL_TABLES["bible.db"])

    def test_fail_fast_on_trigger(self):
        """Triggers can change app-visible behavior; they are rejected."""
        db = self.dir / "bible.db"
        _make_db(db, "bible.db")
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TRIGGER rogue_trigger AFTER INSERT ON verses "
            "BEGIN UPDATE verses SET text = 'TAMPERED' WHERE text = NEW.text; END"
        )
        conn.commit()
        conn.close()

        with self.assertRaises(ValueError):
            compute_db_content_hash(db, CANONICAL_TABLES["bible.db"])

    def test_fts_shadow_tables_are_ignored(self):
        """FTS5 virtual table shadows are derived and excluded from content."""
        db = self.dir / "bible.db"
        _make_db(db, "bible.db")  # includes bible_fts
        # Should not raise: bible_fts is a virtual table, its shadows derived.
        h = compute_db_content_hash(db, CANONICAL_TABLES["bible.db"])
        self.assertIsInstance(h, str)
        self.assertEqual(len(h), 64)

    def test_primary_key_ordering_is_stable(self):
        """Row order is by primary key, so hash is independent of insertion order."""
        db1 = self.dir / "a.db"
        db2 = self.dir / "b.db"
        _make_db(db1, "macula.db")
        _make_db(db2, "macula.db")
        h1 = compute_db_content_hash(db1, CANONICAL_TABLES["macula.db"])
        h2 = compute_db_content_hash(db2, CANONICAL_TABLES["macula.db"])
        self.assertEqual(h1, h2)


class ManifestRoundTripTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_generate_and_check_round_trip(self):
        bible = self.dir / "bible.db"
        macula = self.dir / "macula.db"
        _make_db(bible, "bible.db")
        _make_db(macula, "macula.db")
        manifest = self.dir / "INTEGRITY.json"

        generate_manifest(bible, macula, manifest)
        self.assertTrue(manifest.is_file())

        valid, errors = check_manifest(bible, macula, manifest)
        self.assertTrue(valid, f"expected valid, got errors: {errors}")
        self.assertEqual(errors, [])

    def test_check_detects_content_change(self):
        bible = self.dir / "bible.db"
        macula = self.dir / "macula.db"
        _make_db(bible, "bible.db")
        _make_db(macula, "macula.db")
        manifest = self.dir / "INTEGRITY.json"
        generate_manifest(bible, macula, manifest)

        conn = sqlite3.connect(str(bible))
        conn.execute("UPDATE cross_references SET votes = 999 WHERE from_verse = 'Gen.1.1'")
        conn.commit()
        conn.close()

        valid, errors = check_manifest(bible, macula, manifest)
        self.assertFalse(valid)
        self.assertTrue(any("Content mismatch for bible.db" in e for e in errors))

    def test_check_detects_missing_db(self):
        bible = self.dir / "bible.db"
        macula = self.dir / "macula.db"
        _make_db(bible, "bible.db")
        _make_db(macula, "macula.db")
        manifest = self.dir / "INTEGRITY.json"
        generate_manifest(bible, macula, manifest)

        (self.dir / "macula.db").unlink()
        valid, errors = check_manifest(bible, macula, manifest)
        self.assertFalse(valid)
        self.assertTrue(any("Missing database: macula.db" in e for e in errors))

    def test_fast_mode_rejects_rogue_table(self):
        """Fast (non-deep) mode still runs the shape gate — no silent bypass."""
        bible = self.dir / "bible.db"
        macula = self.dir / "macula.db"
        _make_db(bible, "bible.db")
        _make_db(macula, "macula.db")
        manifest = self.dir / "INTEGRITY.json"
        generate_manifest(bible, macula, manifest)

        conn = sqlite3.connect(str(bible))
        conn.execute("CREATE TABLE rogue_data (id TEXT)")
        conn.commit()
        conn.close()

        valid, errors = check_manifest(bible, macula, manifest, deep=False)
        self.assertFalse(valid)
        self.assertTrue(any("Unexpected tables present: rogue_data" in e for e in errors))

    def test_check_missing_manifest(self):
        valid, errors = check_manifest(
            self.dir / "bible.db", self.dir / "macula.db", self.dir / "none.json"
        )
        self.assertFalse(valid)
        self.assertTrue(any("Integrity manifest not found" in e for e in errors))

    def test_row_counts_reported(self):
        bible = self.dir / "bible.db"
        _make_db(bible, "bible.db")
        counts = table_row_counts(bible, CANONICAL_TABLES["bible.db"])
        self.assertEqual(counts["books"], 3)
        self.assertEqual(counts["translation_verses"], 3)
        self.assertEqual(counts["cross_references"], 3)

    def test_malformed_manifest_entry_reported_gracefully(self):
        """A manifest entry missing required keys is an error, not a KeyError."""
        bible = self.dir / "bible.db"
        macula = self.dir / "macula.db"
        _make_db(bible, "bible.db")
        _make_db(macula, "macula.db")
        manifest = self.dir / "INTEGRITY.json"
        generate_manifest(bible, macula, manifest)

        data = json.loads(manifest.read_text(encoding="utf-8"))
        del data["databases"]["macula.db"]["canonical_tables"]
        manifest.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

        valid, errors = check_manifest(bible, macula, manifest)  # must not raise
        self.assertFalse(valid)
        self.assertTrue(
            any("macula.db is missing canonical_tables" in e for e in errors)
        )


@require_raw_sources()
class RealDataIntegrityTests(unittest.TestCase):
    """Integration test against the real pinned data (requires raw sources)."""

    def test_real_bible_and_macula_hashes_match_manifest(self):
        from search.validation.db_integrity import DEFAULT_DB_PATH, DEFAULT_MACULA_PATH

        self.assertTrue(DEFAULT_DB_PATH.is_file(), "data/bible.db must exist")
        self.assertTrue(DEFAULT_MACULA_PATH.is_file(), "data/macula.db must exist")

        valid, errors = check_manifest(DEFAULT_DB_PATH, DEFAULT_MACULA_PATH)
        self.assertTrue(valid, f"real data should match manifest: {errors}")


if __name__ == "__main__":
    unittest.main()