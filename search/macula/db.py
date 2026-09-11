"""Macula SQLite database engine & schema for whole-Bible linguistic and syntactic data.

In accordance with ADR-013 and ADR-014, this module implements a disk-backed,
zero-dependency SQLite database (data/macula.db) storing normalized verses,
clauses, phrase constituents, tokens, Strong's-LXX alignments, and SDBH semantic
domains.

Key capabilities:
  - Sub-millisecond indexed queries (<15 MB RAM) across the full biblical canon.
  - Relational querying across grammatical roles (Subject, Predicate, Object, Adjunct).
  - Clean API parity with in-memory JSON lookup.
  - Zero external dependencies: Python standard library sqlite3.
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable

from search.resource import data_path, get_repo_root

DEFAULT_MACULA_DB = "data/macula.db"

_TABLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS verses (
    id TEXT PRIMARY KEY,
    book_code TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    mt_id TEXT,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clauses (
    id TEXT PRIMARY KEY,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    clause_num INTEGER NOT NULL,
    rule TEXT
);

CREATE TABLE IF NOT EXISTS constituents (
    id TEXT PRIMARY KEY,
    clause_id TEXT NOT NULL REFERENCES clauses(id),
    verse_id TEXT NOT NULL REFERENCES verses(id),
    constituent_num INTEGER NOT NULL,
    role TEXT,
    role_label TEXT,
    class TEXT,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    id TEXT PRIMARY KEY,
    constituent_id TEXT NOT NULL REFERENCES constituents(id),
    verse_id TEXT NOT NULL REFERENCES verses(id),
    token_num INTEGER NOT NULL,
    text TEXT NOT NULL,
    lemma TEXT,
    morph TEXT,
    pos TEXT,
    strongs TEXT,
    lxx TEXT,
    lxx_strongs TEXT,
    sdbh TEXT,
    core_domains TEXT,
    lex_domains TEXT,
    gloss TEXT
);

CREATE TABLE IF NOT EXISTS strongs_crosswalk (
    strongs TEXT PRIMARY KEY,
    lemmas_json TEXT NOT NULL,
    glosses_json TEXT NOT NULL,
    sdbh_json TEXT NOT NULL,
    core_domains_json TEXT NOT NULL,
    lex_domains_json TEXT NOT NULL,
    lxx_json TEXT NOT NULL,
    occurrences INTEGER NOT NULL
);
"""

_INDICES_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_tokens_strongs ON tokens(strongs);
CREATE INDEX IF NOT EXISTS idx_tokens_lxx ON tokens(lxx_strongs);
CREATE INDEX IF NOT EXISTS idx_tokens_verse ON tokens(verse_id);
CREATE INDEX IF NOT EXISTS idx_constituents_clause ON constituents(clause_id);
CREATE INDEX IF NOT EXISTS idx_constituents_verse ON constituents(verse_id);
CREATE INDEX IF NOT EXISTS idx_constituents_role ON constituents(role COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_constituents_role_label ON constituents(role_label COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_clauses_verse ON clauses(verse_id);
CREATE INDEX IF NOT EXISTS idx_verses_book_ch ON verses(book_code, chapter, verse);
"""

_SCHEMA = _TABLES_SCHEMA + "\n" + _INDICES_SCHEMA



class MaculaSqliteDB:
    """Disk-backed SQLite database engine for Macula linguistic and syntactic data."""

    def __init__(self, db_path: str | Path | None = None, repo_root: str | Path | None = None):
        self.repo_root = get_repo_root() if repo_root is None else Path(repo_root)
        p = Path(db_path) if db_path is not None else Path(DEFAULT_MACULA_DB)
        if p.is_absolute():
            self.db_path = p
        elif (self.repo_root / p).exists():
            self.db_path = self.repo_root / p
        else:
            self.db_path = data_path(p)

        self._conn: sqlite3.Connection | None = None
        self._has_tables: bool | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.execute("PRAGMA synchronous = NORMAL;")
            self._conn.execute("PRAGMA busy_timeout = 5000;")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> MaculaSqliteDB:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def init_db(self, force: bool = False, create_indices: bool = True) -> None:
        """Initialize database schema and optionally indices."""
        if force:
            drop_script = """
            DROP TABLE IF EXISTS tokens;
            DROP TABLE IF EXISTS constituents;
            DROP TABLE IF EXISTS clauses;
            DROP TABLE IF EXISTS verses;
            DROP TABLE IF EXISTS strongs_crosswalk;
            """
            self.conn.cursor().executescript(drop_script)
            self.conn.commit()
            self._has_tables = False
        if not self._has_tables:
            schema_to_run = _SCHEMA if create_indices else _TABLES_SCHEMA
            self.conn.cursor().executescript(schema_to_run)
            self.conn.commit()
            self._has_tables = True

    def create_indices(self) -> None:
        """Create B-Tree indices on tables."""
        self.conn.cursor().executescript(_INDICES_SCHEMA)
        self.conn.commit()

    def exists(self) -> bool:
        """True if the database file exists on disk and has tables."""
        if not self.db_path.exists():
            return False
        if self._has_tables is None:
            try:
                cur = self.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='verses';"
                )
                self._has_tables = cur.fetchone() is not None
            except sqlite3.Error:
                return False
        return self._has_tables

    def insert_verse_batch(
        self,
        verses: list[dict[str, Any]],
        strongs_crosswalk: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Insert verse syntax trees and crosswalk data in high-speed transactions."""
        self.init_db()

        verse_rows = []
        clause_rows = []
        const_rows = []
        token_rows = []

        from search.macula.extract import parse_verse_id

        for v in verses:
            v_id = v["verse_id"]
            b_code, ch, vs = parse_verse_id(v_id)
            verse_rows.append((v_id, b_code, ch, vs, v.get("mt_id"), v.get("text", "")))

            for cl_idx, cl in enumerate(v.get("clauses", []), 1):
                cl_id = f"c:{v_id}:{cl_idx}"
                clause_rows.append((cl_id, v_id, cl_idx, cl.get("rule", "")))

                for c_idx, const in enumerate(cl.get("constituents", []), 1):
                    const_id = f"{cl_id}:{c_idx}"
                    const_rows.append((
                        const_id,
                        cl_id,
                        v_id,
                        c_idx,
                        const.get("role"),
                        const.get("role_label"),
                        const.get("class"),
                        const.get("text", ""),
                    ))

                    for t_idx, tok in enumerate(const.get("tokens", []), 1):
                        tok_id = f"{const_id}:{t_idx}"
                        token_rows.append((
                            tok_id,
                            const_id,
                            v_id,
                            t_idx,
                            tok.get("text", ""),
                            tok.get("lemma"),
                            tok.get("morph"),
                            tok.get("pos"),
                            tok.get("strongs"),
                            tok.get("lxx"),
                            tok.get("lxx_strongs"),
                            tok.get("sdbh"),
                            json.dumps(tok.get("core_domains", [])),
                            json.dumps(tok.get("lex_domains", [])),
                            tok.get("gloss"),
                        ))

        with self.conn:
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO verses (id, book_code, chapter, verse, mt_id, text)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                verse_rows,
            )
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO clauses (id, verse_id, clause_num, rule)
                VALUES (?, ?, ?, ?);
                """,
                clause_rows,
            )
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO constituents (id, clause_id, verse_id, constituent_num, role, role_label, class, text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                const_rows,
            )
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO tokens (
                    id, constituent_id, verse_id, token_num, text, lemma, morph, pos,
                    strongs, lxx, lxx_strongs, sdbh, core_domains, lex_domains, gloss
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                token_rows,
            )

        if strongs_crosswalk:
            self.insert_strongs_crosswalk(strongs_crosswalk)

    def insert_strongs_crosswalk(self, crosswalk: dict[str, dict[str, Any]]) -> None:
        """Insert or replace Strong's crosswalk index."""
        self.init_db()
        rows = []
        for s_id, data in crosswalk.items():
            rows.append((
                s_id,
                json.dumps(data.get("lemmas", [])),
                json.dumps(data.get("glosses", [])),
                json.dumps(data.get("sdbh", [])),
                json.dumps(data.get("core_domains", [])),
                json.dumps(data.get("lex_domains", [])),
                json.dumps(data.get("lxx", {})),
                int(data.get("occurrences", 0)),
            ))

        with self.conn:
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO strongs_crosswalk (
                    strongs, lemmas_json, glosses_json, sdbh_json,
                    core_domains_json, lex_domains_json, lxx_json, occurrences
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                rows,
            )

    def lookup_strongs(self, strongs_num: str) -> dict[str, Any] | None:
        """Lookup Strong's entry (Hebrew H... or Greek G...) from database."""
        if not self.exists():
            return None
        from search.macula.extract import normalize_greek_strongs, normalize_hebrew_strongs

        raw = strongs_num.strip().upper()
        norm_s = normalize_greek_strongs(raw) if raw.startswith("G") else normalize_hebrew_strongs(raw)
        if not norm_s:
            norm_s = raw

        cur = self.conn.execute(
            "SELECT * FROM strongs_crosswalk WHERE strongs = ?;", (norm_s,)
        )
        row = cur.fetchone()
        if not row:
            return None

        return {
            "strongs": row["strongs"],
            "lemmas": json.loads(row["lemmas_json"]),
            "glosses": json.loads(row["glosses_json"]),
            "sdbh": json.loads(row["sdbh_json"]),
            "core_domains": json.loads(row["core_domains_json"]),
            "lex_domains": json.loads(row["lex_domains_json"]),
            "lxx": json.loads(row["lxx_json"]),
            "occurrences": row["occurrences"],
        }

    def lookup_verse(self, verse_ref: str) -> dict[str, Any] | None:
        """Lookup full verse syntax tree from database."""
        if not self.exists():
            return None

        from search.macula.lookup import normalize_verse_ref
        norm_ref = normalize_verse_ref(verse_ref)
        if not norm_ref:
            return None

        v_cur = self.conn.execute("SELECT * FROM verses WHERE id = ?;", (norm_ref,))
        v_row = v_cur.fetchone()
        if not v_row:
            return None

        # Fetch clauses
        c_cur = self.conn.execute(
            "SELECT * FROM clauses WHERE verse_id = ? ORDER BY clause_num ASC;", (norm_ref,)
        )
        clause_rows = c_cur.fetchall()

        # Fetch constituents
        const_cur = self.conn.execute(
            "SELECT * FROM constituents WHERE verse_id = ? ORDER BY clause_id, constituent_num ASC;",
            (norm_ref,),
        )
        constituents_by_clause: dict[str, list[dict[str, Any]]] = defaultdict(list)
        const_map: dict[str, dict[str, Any]] = {}
        for r in const_cur.fetchall():
            c_dict = {
                "role": r["role"],
                "role_label": r["role_label"],
                "class": r["class"],
                "text": r["text"],
                "tokens": [],
            }
            constituents_by_clause[r["clause_id"]].append(c_dict)
            const_map[r["id"]] = c_dict

        # Fetch tokens
        t_cur = self.conn.execute(
            "SELECT * FROM tokens WHERE verse_id = ? ORDER BY constituent_id, token_num ASC;",
            (norm_ref,),
        )
        for tr in t_cur.fetchall():
            tok_dict = {
                "text": tr["text"],
                "lemma": tr["lemma"],
                "morph": tr["morph"],
                "pos": tr["pos"],
                "strongs": tr["strongs"],
                "lxx": tr["lxx"],
                "lxx_strongs": tr["lxx_strongs"],
                "sdbh": tr["sdbh"],
                "core_domains": json.loads(tr["core_domains"]),
                "lex_domains": json.loads(tr["lex_domains"]),
                "gloss": tr["gloss"],
            }
            c_target = const_map.get(tr["constituent_id"])
            if c_target is not None:
                c_target["tokens"].append(tok_dict)

        clauses = []
        for cl in clause_rows:
            cl_consts = constituents_by_clause.get(cl["id"], [])
            cl_text = " ".join(c["text"] for c in cl_consts if c.get("text"))
            clauses.append({
                "rule": cl["rule"],
                "text": cl_text,
                "constituents": cl_consts,
            })

        return {
            "verse_id": v_row["id"],
            "mt_id": v_row["mt_id"],
            "text": v_row["text"],
            "clauses": clauses,
        }

    def lookup_verses_batch(self, verse_refs: list[str]) -> dict[str, dict[str, Any]]:
        """Lookup multiple verse syntax trees from database in batched queries."""
        if not self.exists() or not verse_refs:
            return {}

        from search.macula.lookup import normalize_verse_ref
        norm_map: dict[str, str] = {}
        for r in verse_refs:
            try:
                n = normalize_verse_ref(r)
                if n:
                    norm_map[r] = n
            except ValueError:
                pass

        if not norm_map:
            return {}

        unique_norm_refs = list(set(norm_map.values()))
        placeholders = ",".join("?" * len(unique_norm_refs))

        # 1. Fetch verses
        v_cur = self.conn.execute(
            f"SELECT * FROM verses WHERE id IN ({placeholders});",
            unique_norm_refs,
        )
        verse_rows = {r["id"]: r for r in v_cur.fetchall()}
        if not verse_rows:
            return {}

        found_verse_ids = list(verse_rows.keys())
        v_placeholders = ",".join("?" * len(found_verse_ids))

        # 2. Fetch clauses
        c_cur = self.conn.execute(
            f"SELECT * FROM clauses WHERE verse_id IN ({v_placeholders}) ORDER BY verse_id, clause_num ASC;",
            found_verse_ids,
        )
        clause_rows = c_cur.fetchall()

        # 3. Fetch constituents
        const_cur = self.conn.execute(
            f"SELECT * FROM constituents WHERE verse_id IN ({v_placeholders}) ORDER BY clause_id, constituent_num ASC;",
            found_verse_ids,
        )
        constituents_by_clause: dict[str, list[dict[str, Any]]] = defaultdict(list)
        const_map: dict[str, dict[str, Any]] = {}
        for r in const_cur.fetchall():
            c_dict = {
                "role": r["role"],
                "role_label": r["role_label"],
                "class": r["class"],
                "text": r["text"],
                "tokens": [],
            }
            constituents_by_clause[r["clause_id"]].append(c_dict)
            const_map[r["id"]] = c_dict

        # 4. Fetch tokens
        t_cur = self.conn.execute(
            f"SELECT * FROM tokens WHERE verse_id IN ({v_placeholders}) ORDER BY constituent_id, token_num ASC;",
            found_verse_ids,
        )
        for tr in t_cur.fetchall():
            tok_dict = {
                "text": tr["text"],
                "lemma": tr["lemma"],
                "morph": tr["morph"],
                "pos": tr["pos"],
                "strongs": tr["strongs"],
                "lxx": tr["lxx"],
                "lxx_strongs": tr["lxx_strongs"],
                "sdbh": tr["sdbh"],
                "core_domains": json.loads(tr["core_domains"]),
                "lex_domains": json.loads(tr["lex_domains"]),
                "gloss": tr["gloss"],
            }
            c_target = const_map.get(tr["constituent_id"])
            if c_target is not None:
                c_target["tokens"].append(tok_dict)

        clauses_by_verse: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for cl in clause_rows:
            cl_consts = constituents_by_clause.get(cl["id"], [])
            cl_text = " ".join(c["text"] for c in cl_consts if c.get("text"))
            clauses_by_verse[cl["verse_id"]].append({
                "rule": cl["rule"],
                "text": cl_text,
                "constituents": cl_consts,
            })

        out_by_norm: dict[str, dict[str, Any]] = {}
        for v_id, v_row in verse_rows.items():
            out_by_norm[v_id] = {
                "verse_id": v_row["id"],
                "mt_id": v_row["mt_id"],
                "text": v_row["text"],
                "clauses": clauses_by_verse.get(v_id, []),
            }

        res: dict[str, dict[str, Any]] = {}
        for orig_ref, norm_ref in norm_map.items():
            if norm_ref in out_by_norm:
                res[orig_ref] = out_by_norm[norm_ref]
                res[norm_ref] = out_by_norm[norm_ref]

        return res

    def lookup_lxx(self, greek_strongs: str) -> list[dict[str, Any]]:
        """Find Hebrew words aligned with given Greek LXX Strong's number."""
        if not self.exists():
            return []
        norm_g = greek_strongs.strip().upper()
        if not norm_g.startswith("G") and norm_g.isdigit():
            norm_g = f"G{int(norm_g)}"

        cur = self.conn.execute(
            """
            SELECT strongs, lemmas_json, glosses_json, json_extract(lxx_json, '$.' || ?) AS match_json
            FROM strongs_crosswalk
            WHERE match_json IS NOT NULL;
            """,
            (norm_g,),
        )
        matches = []
        for row in cur.fetchall():
            g_rec = json.loads(row["match_json"])
            matches.append({
                "hebrew_strongs": row["strongs"],
                "lemmas": json.loads(row["lemmas_json"]),
                "glosses": json.loads(row["glosses_json"]),
                "greek_forms": g_rec.get("greek") or g_rec.get("forms", []),
                "count": g_rec.get("count", 0),
            })

        matches.sort(key=lambda x: x["count"], reverse=True)
        return matches

    def search_by_domain(self, domain_code: str) -> list[dict[str, Any]]:
        """Find Hebrew words mapped to an SDBH semantic domain."""
        if not self.exists():
            return []
        clean_d = domain_code.strip().zfill(3)
        cur = self.conn.execute(
            """
            SELECT sc.strongs, sc.lemmas_json, sc.glosses_json
            FROM strongs_crosswalk sc, json_each(sc.core_domains_json) je
            WHERE je.value = ?;
            """,
            (clean_d,),
        )
        results = [
            {
                "hebrew_strongs": row["strongs"],
                "lemmas": json.loads(row["lemmas_json"]),
                "glosses": json.loads(row["glosses_json"]),
            }
            for row in cur.fetchall()
        ]

        def _sort_key(item: dict) -> int:
            s = item["hebrew_strongs"]
            return int(s[1:]) if len(s) > 1 and s[1:].isdigit() else 999999

        results.sort(key=_sort_key)
        return results

    def search_by_role(
        self,
        role: str,
        book: str | None = None,
        book_code: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Find syntactic constituents matching a grammatical role."""
        if not self.exists() or not role:
            return []
        from search.macula.extract import resolve_role_query, resolve_osis_book
        target_roles = resolve_role_query(role)
        placeholders = ", ".join("?" for _ in target_roles)
        query = f"""
        SELECT c.*, cl.rule as clause_rule, v.text as verse_text
        FROM constituents c
        JOIN clauses cl ON c.clause_id = cl.id
        JOIN verses v ON c.verse_id = v.id
        WHERE (c.role IN ({placeholders}) OR c.role_label IN ({placeholders}))
        """
        params: list[Any] = list(target_roles) + list(target_roles)
        target_book = book or book_code
        if target_book:
            query += " AND v.book_code = ?"
            params.append(resolve_osis_book(target_book).upper())

        query += " ORDER BY v.book_code, v.chapter, v.verse, cl.clause_num, c.constituent_num LIMIT ?;"
        params.append(limit)

        cur = self.conn.execute(query, params)
        results = []
        for r in cur.fetchall():
            results.append({
                "verse_id": r["verse_id"],
                "role": r["role"],
                "role_label": r["role_label"],
                "class": r["class"],
                "text": r["text"],
                "constituent_text": r["text"],
                "clause_rule": r["clause_rule"],
                "verse_text": r["verse_text"],
            })
        return results

    @property
    def counts(self) -> dict[str, int]:
        """Return counts of all entities in database."""
        if not self.exists():
            return {}
        v_cnt = self.conn.execute("SELECT COUNT(*) FROM verses;").fetchone()[0]
        cl_cnt = self.conn.execute("SELECT COUNT(*) FROM clauses;").fetchone()[0]
        c_cnt = self.conn.execute("SELECT COUNT(*) FROM constituents;").fetchone()[0]
        t_cnt = self.conn.execute("SELECT COUNT(*) FROM tokens;").fetchone()[0]
        s_cnt = self.conn.execute("SELECT COUNT(*) FROM strongs_crosswalk;").fetchone()[0]
        ch_cnt = self.conn.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT book_code, chapter FROM verses);"
        ).fetchone()[0]
        return {
            "chapters": ch_cnt,
            "verses": v_cnt,
            "clauses": cl_cnt,
            "constituents": c_cnt,
            "tokens": t_cnt,
            "strongs_crosswalk_entries": s_cnt,
        }

