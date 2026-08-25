"""SQLite index + query layer for the semantic linking pipeline.

STRUCTURE RATIONALE
-------------------
Markdown in `materials/` remains the single source of truth. The SQLite
database is a *generated artifact* (like the `index/` pickle) that decouples
index-building from querying:

* build once  -> search/linking/dbindex.py build  ->  dbindex.semantic.db
* query many  -> search/linking/dbindex.py query   ->  reads only the .db

This gives:
- One file, fully offline, no server (offline-first vision).
- FTS5 full-text search over passages + bodies.
- Real metadata queries ("strongs-H7225 AND theme/creation") as proper SQL
  instead of Python loops over every entry.
- The same generated-artifact relationship the project already accepts for
  `index/*.pkl`; the .db is gitignored.

The query interface is shared by the concordance (layer b) and candidate
(layer c) modules so they stop rescanning materials/ every run.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

# Default location of the generated db (gitignored).
DEFAULT_DB = "index/semantic.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    path TEXT,
    passage TEXT,
    body TEXT,
    frontmatter TEXT
);
CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id TEXT,
    tag TEXT,
    PRIMARY KEY (entry_id, tag),
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_entry_tags_tag ON entry_tags(tag);
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    id,
    passage,
    body,
    content='entries',
    content_rowid='rowid',
    tokenize='porter unicode61'
);
"""

# Rowid trick so FTS stays in sync with the entries table.
_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
  INSERT INTO entries_fts(rowid, id, passage, body)
  VALUES (new.rowid, new.id, new.passage, new.body);
END;
CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, id, passage, body)
  VALUES ('delete', old.rowid, old.id, old.passage, old.body);
END;
CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE OF id, passage, body ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, id, passage, body)
  VALUES ('delete', old.rowid, old.id, old.passage, old.body);
  INSERT INTO entries_fts(rowid, id, passage, body)
  VALUES (new.rowid, new.id, new.passage, new.body);
END;
"""


def _escape_table(value: str) -> str:
    # SQLite identifiers are wrapped in double quotes; double-quote any quotes.
    return value.replace('"', '""')


class SemanticDB:
    """SQLite-backed semantic index. Markdown is authoritative; this is read-only."""

    def __init__(self, db_path: str | Path = DEFAULT_DB, repo_root="."):
        self.db_path = str(db_path)
        self.repo_root = Path(repo_root)

    # ---- index building ---------------------------------------------------

    def build(self, loader) -> None:
        """Load entries from the loader (Markdown) and (re)build the db."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # WAL so queries can run while writes happen elsewhere; still single-file.
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA foreign_keys=ON;")
        con.executescript(_SCHEMA)
        con.executescript(_TRIGGERS)
        con.execute("DELETE FROM entries;")  # clear old data, triggers cascade FTS

        with con:
            for entry in loader.entries:
                con.execute(
                    "INSERT INTO entries(id, path, passage, body, frontmatter) VALUES (?,?,?,?,?)",
                    (
                        entry.id,
                        entry.path,
                        entry.passage,
                        entry.body,
                        json.dumps(entry.frontmatter, ensure_ascii=False, default=_json_default),
                    ),
                )
                for tag in entry.tags:
                    con.execute(
                        "INSERT OR IGNORE INTO entry_tags(entry_id, tag) VALUES (?,?)",
                        (entry.id, tag),
                    )
        con.commit()
        con.close()

    # ---- connection --------------------------------------------------------

    def _connect(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def count(self) -> int:
        con = self._connect()
        try:
            return con.execute("SELECT COUNT(*) AS c FROM entries").fetchone()["c"]
        finally:
            con.close()

    # ---- metadata queries --------------------------------------------------

    def entries_by_strongs(self, strongs: str) -> list[dict]:
        """Return dicts of every entry tagged with a given Strong's number."""
        return self._entries_by_tags([f"strongs-{strongs}"])

    def entries_by_tag(self, tag: str) -> list[dict]:
        return self._entries_by_tags([tag])

    def by_tag_and_strongs(self, strongs: str, tag: str) -> list[dict]:
        """All entries that have BOTH a strongs-* and a given tag."""
        return self._entries_by_tags([f"strongs-{strongs}", tag])

    def _entries_by_tags(self, tags: list[str]) -> list[dict]:
        """Return entries that have ALL of the given tags (proper SQL)."""
        con = self._connect()
        try:
            placeholders = ",".join("?" for _ in tags)
            rows = con.execute(
                f"""
                SELECT e.*
                FROM entries e
                WHERE (SELECT COUNT(*) FROM entry_tags t
                       WHERE t.entry_id = e.id AND t.tag IN ({placeholders})) = ?
                """,
                (*tags, len(tags)),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()

    # ---- Strong's concordance (DB-backed, no full rescan) -----------------

    def concordance(self) -> list[dict]:
        """Return all (strongs, entry-ref) pairs grouped by Strong's.

        Each item: {strongs, entry_id, path, passage, language, translation, word}
        Read directly from the DB (parses the stored frontmatter JSON), so the
        caller does not need to rescan the Markdown tree.
        """
        con = self._connect()
        try:
            rows = con.execute(
                """
                SELECT substr(t.tag, 9) AS strongs, e.id AS entry_id, e.path,
                       e.passage, e.frontmatter
                FROM entry_tags t
                JOIN entries e ON e.id = t.entry_id
                WHERE t.tag LIKE 'strongs-%'
                ORDER BY t.tag, e.id
                """
            ).fetchall()
            out = []
            for r in rows:
                fm = {}
                try:
                    fm = json.loads(r["frontmatter"])
                except Exception:
                    pass
                out.append(
                    {
                        "strongs": r["strongs"],
                        "entry_id": r["entry_id"],
                        "path": r["path"],
                        "passage": r["passage"],
                        "language": (fm.get("language") or ""),
                        "translation": (fm.get("translation") or ""),
                        "word": (fm.get("word") or ""),
                    }
                )
            return out
        finally:
            con.close()

    def entries(self) -> list[dict]:
        """Return all stored entries as dicts (DB-backed; no Markdown rescan)."""
        con = self._connect()
        try:
            rows = con.execute("SELECT * FROM entries ORDER BY id").fetchall()
            return [dict(r) for r in rows]
        finally:
            con.close()

    # ---- FTS5 free-text query ---------------------------------------------

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Full-text search across passage + body (FTS5)."""
        con = self._connect()
        try:
            # FTS5 BM25 scoring; match only supported syntax.
            try:
                rows = con.execute(
                    """
                    SELECT e.id, e.path, e.passage,
                           bm25(entries_fts) AS bm25
                    FROM entries_fts
                    JOIN entries e ON e.rowid = entries_fts.rowid
                    WHERE entries_fts MATCH ?
                    ORDER BY bm25
                    LIMIT ?
                    """,
                    (query, top_k),
                ).fetchall()
            except sqlite3.OperationalError:
                return []  # invalid FTS query syntax
            return [dict(r) for r in rows]
        finally:
            con.close()


def _json_default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    return str(o)


def build_index(repo=".", db_path=DEFAULT_DB) -> str:
    """Build the db from the repo's materials. Returns the db path."""
    from .loader import Loader

    loader = Loader(repo)
    loader.load_entries()
    db = SemanticDB(repo_root=repo, db_path=db_path)
    db.build(loader)
    return db_path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="dbindex", description="SQLite semantic index for bible-study-tool")
    sub = parser.add_subparsers(dest="cmd")

    b = sub.add_parser("build", help="Build the index from materials/ (Markdown stays authoritative)")
    b.add_argument("--repo", default=".")
    b.add_argument("--db", default=DEFAULT_DB)

    q = sub.add_parser("query", help="Query the built index")
    q.add_argument("--db", default=DEFAULT_DB)
    q.add_argument("--free-text", help="FTS5 free-text query")
    q.add_argument("--strongs", help="tag lookup, e.g. H7225")
    q.add_argument("--tag", help="tag lookup, e.g. theme/creation")
    q.add_argument("--count", action="store_true", help="print entry count")
    q.add_argument("--top-k", type=int, default=10)

    args = parser.parse_args(argv)

    if args.cmd == "build":
        path = build_index(args.repo, args.db)
        n = SemanticDB(path).count()
        print(f"[db] built {path} with {n} entries")
        return 0

    if args.cmd == "query":
        db = SemanticDB(args.db)
        if args.count:
            print(f"{db.count()} entries")
            return 0
        if args.strongs:
            for r in db.entries_by_strongs(args.strongs):
                print(f"{r['id']} — {r['passage']}")
        elif args.tag:
            for r in db.entries_by_tag(args.tag):
                print(f"{r['id']} — {r['passage']}")
        elif getattr(args, "free_text", None):
            for r in db.search(args.free_text, top_k=args.top_k):
                print(f"{r['id']} — {r['passage']} (bm25 {r['bm25']:.3f})")
        else:
            parser.print_help()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())