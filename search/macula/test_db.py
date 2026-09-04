"""Unit and parity tests for Macula SQLite database engine (ADR-0014)."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from search.macula.build_db import compile_macula_db
from search.macula.db import DEFAULT_MACULA_DB, MaculaSqliteDB
from search.macula.extract import resolve_role_query
from search.macula.lookup import MaculaDB
import scripts.macula_lookup as macula_cli

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENESIS_JSON_PATH = REPO_ROOT / "lexicons" / "macula-genesis.json"
SQLITE_DB_PATH = REPO_ROOT / DEFAULT_MACULA_DB


class TestMaculaSqliteDBInit(unittest.TestCase):
    """Test MaculaSqliteDB lifecycle and schema initialization."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_macula.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_exists_and_init(self):
        db = MaculaSqliteDB(self.db_path)
        self.assertFalse(db.exists())

        db.init_db()
        self.assertTrue(db.exists())

        # Verify tables exist
        cur = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [r[0] for r in cur.fetchall()]
        self.assertIn("verses", tables)
        self.assertIn("clauses", tables)
        self.assertIn("constituents", tables)
        self.assertIn("tokens", tables)
        self.assertIn("strongs_crosswalk", tables)

        # Test force reinit drops and re-creates
        db.conn.execute("INSERT INTO verses (id, book_code, chapter, verse, text) VALUES ('test', 'GEN', 1, 1, 'text');")
        db.conn.commit()
        db.init_db(force=True)
        cur = db.conn.execute("SELECT COUNT(*) FROM verses;")
        self.assertEqual(cur.fetchone()[0], 0)
        db.close()



class TestMaculaSqliteOperations(unittest.TestCase):
    """Test data insertion, indexing, and retrieval in SQLite."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_macula.db"
        self.db = MaculaSqliteDB(self.db_path)
        self.db.init_db()

        # Seed sample data
        sample_verses = [
            {
                "verse_id": "Gen.1.1",
                "mt_id": "Gen.1.1",
                "text": "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ׃",
                "clauses": [
                    {
                        "rule": "PP-V-S-O",
                        "constituents": [
                            {
                                "role": "pp",
                                "role_label": "prepositional_phrase",
                                "class": "pp",
                                "text": "בְּרֵאשִׁ֖ית",
                                "tokens": [
                                    {
                                        "text": "בְּרֵאשִׁ֖ית",
                                        "lemma": "רֵאשִׁית",
                                        "morph": "HR/Ncfsa",
                                        "pos": "noun",
                                        "strongs": "H7225",
                                        "lxx": "ἀρχή",
                                        "lxx_strongs": "G746",
                                        "sdbh": "006644001001000",
                                        "core_domains": ["002", "168"],
                                        "lex_domains": ["002001001002"],
                                        "gloss": "beginning",
                                    }
                                ],
                            },
                            {
                                "role": "s",
                                "role_label": "subject",
                                "class": "noun",
                                "text": "אֱלֹהִ֑ים",
                                "tokens": [
                                    {
                                        "text": "אֱלֹהִ֑ים",
                                        "lemma": "אֱלֹהִים",
                                        "morph": "HNcmpa",
                                        "pos": "noun",
                                        "strongs": "H430",
                                        "lxx": "θεός",
                                        "lxx_strongs": "G2316",
                                        "sdbh": "000397001001000",
                                        "core_domains": ["001"],
                                        "lex_domains": ["001001001"],
                                        "gloss": "God",
                                    }
                                ],
                            },
                        ],
                    }
                ],
            }
        ]
        sample_crosswalk = {
            "H7225": {
                "lemmas": ["רֵאשִׁית"],
                "glosses": ["beginning"],
                "sdbh": ["006644001001000"],
                "core_domains": ["002", "168"],
                "lex_domains": ["002001001002"],
                "lxx": {
                    "G746": {"greek": ["ἀρχή"], "count": 1}
                },
                "occurrences": 1,
            },
            "H430": {
                "lemmas": ["אֱלֹהִים"],
                "glosses": ["God"],
                "sdbh": ["000397001001000"],
                "core_domains": ["001"],
                "lex_domains": ["001001001"],
                "lxx": {
                    "G2316": {"greek": ["θεός"], "count": 1}
                },
                "occurrences": 1,
            },
        }
        self.db.insert_verse_batch(sample_verses, strongs_crosswalk=sample_crosswalk)

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_counts(self):
        counts = self.db.counts
        self.assertEqual(counts["verses"], 1)
        self.assertEqual(counts["clauses"], 1)
        self.assertEqual(counts["constituents"], 2)
        self.assertEqual(counts["tokens"], 2)
        self.assertEqual(counts["strongs_crosswalk_entries"], 2)

    def test_lookup_strongs(self):
        res = self.db.lookup_strongs("H7225")
        self.assertIsNotNone(res)
        self.assertEqual(res["strongs"], "H7225")
        self.assertIn("beginning", res["glosses"])
        self.assertIn("168", res["core_domains"])

        # Test normalization
        res_num = self.db.lookup_strongs("7225")
        self.assertEqual(res_num, res)

        # Non-existent
        self.assertIsNone(self.db.lookup_strongs("H99999"))

    def test_lookup_verse(self):
        res = self.db.lookup_verse("Gen.1.1")
        self.assertIsNotNone(res)
        self.assertEqual(res["verse_id"], "Gen.1.1")
        self.assertEqual(len(res["clauses"]), 1)
        self.assertEqual(res["clauses"][0]["rule"], "PP-V-S-O")
        self.assertEqual(len(res["clauses"][0]["constituents"]), 2)

        # Flexible normalization
        self.assertIsNotNone(self.db.lookup_verse("1:1"))
        self.assertIsNotNone(self.db.lookup_verse("Genesis 1:1"))
        self.assertIsNone(self.db.lookup_verse("Gen.99.99"))

    def test_lookup_lxx(self):
        res = self.db.lookup_lxx("G746")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["hebrew_strongs"], "H7225")
        self.assertEqual(res[0]["count"], 1)
        self.assertIn("ἀρχή", res[0]["greek_forms"])

        # Digits only normalization
        res_digit = self.db.lookup_lxx("746")
        self.assertEqual(res_digit, res)

        # Non-existent
        self.assertEqual(self.db.lookup_lxx("G9999"), [])

    def test_search_by_domain(self):
        res = self.db.search_by_domain("168")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["hebrew_strongs"], "H7225")

        # Zero padding
        res_pad = self.db.search_by_domain("1")
        self.assertEqual(len(res_pad), 1)
        self.assertEqual(res_pad[0]["hebrew_strongs"], "H430")

        # Non-existent
        self.assertEqual(self.db.search_by_domain("999"), [])

    def test_macula_db_context_manager(self):
        with MaculaDB(self.db_path) as mdb:
            self.assertTrue(mdb.is_sqlite)
            res = mdb.lookup_strongs("H7225")
            self.assertIsNotNone(res)
            self.assertEqual(res["strongs"], "H7225")
        # After exit, backing sqlite connection closed
        self.assertIsNone(mdb._sqlite._conn)

    def test_search_by_role_aliases(self):
        # Test subject lookup with various aliases
        for q in ["s", "subj", "subject"]:
            res = self.db.search_by_role(q, limit=10)
            self.assertEqual(len(res), 1, f"Failed for alias {q}")
            self.assertEqual(res[0]["verse_id"], "Gen.1.1")
            self.assertEqual(res[0]["role"], "s")
            self.assertEqual(res[0]["constituent_text"], "אֱלֹהִ֑ים")

        # Test prepositional phrase
        for q in ["pp", "prep", "prepositional_phrase"]:
            res_pp = self.db.search_by_role(q, limit=10)
            self.assertEqual(len(res_pp), 1, f"Failed for alias {q}")
            self.assertEqual(res_pp[0]["role"], "pp")

        # Book code filtering
        res_gen = self.db.search_by_role("subj", book_code="GEN")
        self.assertEqual(len(res_gen), 1)
        res_exo = self.db.search_by_role("subj", book_code="EXO")
        self.assertEqual(len(res_exo), 0)



class TestRoleAliasResolution(unittest.TestCase):
    """Test role query resolver helper."""

    def test_role_aliases(self):
        self.assertEqual(resolve_role_query("subj"), ("s", "subject"))
        self.assertEqual(resolve_role_query("s"), ("s", "subject"))
        self.assertEqual(resolve_role_query("pred"), ("p", "predicate"))
        self.assertEqual(resolve_role_query("obj"), ("o", "object"))
        self.assertEqual(resolve_role_query("unknown_role"), ("unknown_role",))


class TestMaculaParityWithJson(unittest.TestCase):
    """Test query parity between MaculaSqliteDB and in-memory MaculaDB JSON fallback."""

    @classmethod
    def setUpClass(cls):
        if not GENESIS_JSON_PATH.is_file():
            raise unittest.SkipTest("lexicons/macula-genesis.json not found")

        with open(GENESIS_JSON_PATH, encoding="utf-8") as f:
            cls.json_data = json.load(f)

        cls.json_engine = MaculaDB(cls.json_data)

        # If data/macula.db exists on disk, use it; otherwise build a temporary one
        if SQLITE_DB_PATH.is_file():
            cls.sqlite_engine = MaculaSqliteDB(SQLITE_DB_PATH)
            cls.cleanup_sqlite = False
        else:
            cls.temp_dir = tempfile.TemporaryDirectory()
            temp_db = Path(cls.temp_dir.name) / "macula_parity.db"
            compile_macula_db(from_json=GENESIS_JSON_PATH, out_db=temp_db)
            cls.sqlite_engine = MaculaSqliteDB(temp_db)
            cls.cleanup_sqlite = True

    @classmethod
    def tearDownClass(cls):
        cls.sqlite_engine.close()
        if getattr(cls, "cleanup_sqlite", False):
            cls.temp_dir.cleanup()

    def test_parity_strongs_lookup(self):
        for s_id in ["H7225", "H430", "H1254", "H8064", "H776"]:
            sqlite_res = self.sqlite_engine.lookup_strongs(s_id)
            json_res = self.json_engine.lookup_strongs(s_id)
            self.assertIsNotNone(sqlite_res)
            self.assertIsNotNone(json_res)
            self.assertEqual(sqlite_res["strongs"], json_res["strongs"])
            self.assertEqual(sqlite_res["lemmas"], json_res["lemmas"])
            self.assertEqual(sqlite_res["glosses"], json_res["glosses"])
            self.assertEqual(sqlite_res["sdbh"], json_res["sdbh"])
            self.assertEqual(sqlite_res["core_domains"], json_res["core_domains"])
            self.assertEqual(sqlite_res["occurrences"], json_res["occurrences"])

    def test_parity_verse_lookup(self):
        for v_ref in ["Gen.1.1", "Gen.1.2", "Gen.1.3", "Gen.31.55", "Gen.32.1"]:
            sqlite_res = self.sqlite_engine.lookup_verse(v_ref)
            json_res = self.json_engine.lookup_verse(v_ref)
            self.assertIsNotNone(sqlite_res, f"SQLite returned None for {v_ref}")
            self.assertIsNotNone(json_res, f"JSON returned None for {v_ref}")
            self.assertEqual(sqlite_res["verse_id"], json_res["verse_id"])
            self.assertEqual(sqlite_res["mt_id"], json_res["mt_id"])
            self.assertEqual(sqlite_res["text"], json_res["text"])
            self.assertEqual(len(sqlite_res["clauses"]), len(json_res["clauses"]))

            # Compare constituent roles
            for sq_cl, js_cl in zip(sqlite_res["clauses"], json_res["clauses"]):
                self.assertEqual(sq_cl["rule"], js_cl["rule"])
                self.assertEqual(len(sq_cl["constituents"]), len(js_cl["constituents"]))
                for sq_c, js_c in zip(sq_cl["constituents"], js_cl["constituents"]):
                    self.assertEqual(sq_c["role"], js_c["role"])
                    self.assertEqual(sq_c["text"], js_c["text"])
                    self.assertEqual(len(sq_c["tokens"]), len(js_c["tokens"]))

    def test_parity_lxx_lookup(self):
        for g_id in ["G746", "G4160", "G2316"]:
            sqlite_res = self.sqlite_engine.lookup_lxx(g_id)
            json_res = self.json_engine.lookup_lxx(g_id)
            self.assertEqual(len(sqlite_res), len(json_res))
            if sqlite_res:
                self.assertEqual(sqlite_res[0]["hebrew_strongs"], json_res[0]["hebrew_strongs"])
                self.assertEqual(sqlite_res[0]["count"], json_res[0]["count"])

    def test_parity_domain_search(self):
        for d_code in ["168", "028", "001"]:
            sqlite_res = self.sqlite_engine.search_by_domain(d_code)
            json_res = self.json_engine.search_by_domain(d_code)
            self.assertEqual(len(sqlite_res), len(json_res))
            sqlite_ids = [r["hebrew_strongs"] for r in sqlite_res]
            json_ids = [r["hebrew_strongs"] for r in json_res]
            self.assertEqual(sqlite_ids, json_ids)

    def test_parity_role_search(self):
        for role in ["s", "subj", "subject", "pred", "obj"]:
            sqlite_res = self.sqlite_engine.search_by_role(role, limit=20)
            json_res = self.json_engine.search_by_role(role, limit=20)
            self.assertEqual(len(sqlite_res), len(json_res), f"Mismatched count for role {role}")
            for sq_r, js_r in zip(sqlite_res, json_res):
                self.assertEqual(sq_r["verse_id"], js_r["verse_id"])
                self.assertEqual(sq_r["role"], js_r["role"])
                self.assertEqual(sq_r["constituent_text"], js_r["constituent_text"])


class TestMaculaBuildScript(unittest.TestCase):
    """Test database compiler script."""

    def test_compile_from_json_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_json = Path(tmp) / "non_existent.json"
            out_db = Path(tmp) / "out.db"
            with self.assertRaises(FileNotFoundError):
                compile_macula_db(from_json=missing_json, out_db=out_db)


class TestMaculaCLI(unittest.TestCase):
    """Test CLI commands and options."""

    def test_cli_stats(self):
        rc = macula_cli.main(["--stats"])
        self.assertEqual(rc, 0)

    def test_cli_strongs(self):
        rc = macula_cli.main(["--strongs", "H7225"])
        self.assertEqual(rc, 0)

    def test_cli_verse(self):
        rc = macula_cli.main(["--verse", "Gen.1.1"])
        self.assertEqual(rc, 0)

    def test_cli_role(self):
        rc = macula_cli.main(["--role", "subj", "--limit", "5"])
        self.assertEqual(rc, 0)

    def test_cli_role_json(self):
        rc = macula_cli.main(["--role", "subj", "--limit", "3", "--json"])
        self.assertEqual(rc, 0)

    def test_cli_not_found(self):
        rc = macula_cli.main(["--strongs", "H99999"])
        self.assertEqual(rc, 1)



if __name__ == "__main__":
    unittest.main()
