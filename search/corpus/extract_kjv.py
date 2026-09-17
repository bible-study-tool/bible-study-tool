"""Whole-Bible KJV extraction, tokenization, and SQLite storage engine (WP-019).

In accordance with ADR-013 and ADR-014, this module provides:
  - Zero-dependency streaming extraction from pinned KJV-osis JSON (all 66 books, 1,189 chapters, 31,102 verses).
  - High-fidelity clean text extraction (un-escaping entities, stripping OSIS tags, preserving punctuation).
  - Word-level tokenization with Strong's numbers (both Hebrew H-codes and Greek G-codes),
    morphology, Textus Receptus lemmas, and source alignments.
  - Disk-backed SQLite database (data/bible.db) with FTS5 BM25 search and sub-millisecond query performance (<10 MB RAM).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import html
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any, Iterable, Optional

from search.corpus.bible_books import (
    BIBLE_BOOKS,
    CANONICAL_OSIS_ORDER,
    BookInfo,
    get_book_info,
    parse_passage_ref,
    resolve_book_code,
)
from search.dbaccess import connect_db_reader
from search.resource import data_path, get_repo_root

DEFAULT_KJV_JSON = "data/KJV-osis.json"
DEFAULT_BIBLE_DB = "data/bible.db"

_NOTE_RE = re.compile(r"<note\b[^>]*>.*?</note>", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_W_RE = re.compile(r'<w\b([^>]*?)(?:/>|>(.*?)</w>)', re.DOTALL)
_LEMMA_ATTR_RE = re.compile(r'lemma="([^"]*)"')
_MORPH_ATTR_RE = re.compile(r'morph="([^"]*)"')
_SRC_ATTR_RE = re.compile(r'src="([^"]*)"')
_STRONG_CODE_RE = re.compile(r"strong:([HG])(\d{1,5})")
_TR_LEMMA_RE = re.compile(r"lemma\.TR:([^\s\"]+)")


@dataclass
class WordToken:
    """A word or token span with linguistic attributes."""
    index: int
    text: str
    strongs: list[str]
    lemma: Optional[str] = None
    morph: Optional[str] = None
    src: Optional[str] = None


def clean_verse_text(raw: str) -> str:
    """Strip OSIS markup, unescape XML entities, and condense whitespace.

    Preserves translated text and translation-supplied italics (<transChange>).
    Removes margin apparatus notes (<note>...</note>) and XML tags.
    """
    if not raw:
        return ""
    text = _NOTE_RE.sub("", raw)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def extract_tokens(raw: str) -> list[WordToken]:
    """Extract word tokens and Strong's markup from a raw KJV-osis verse."""
    tokens: list[WordToken] = []
    for i, m in enumerate(_W_RE.finditer(raw), start=1):
        attrs = m.group(1)
        inner_text = m.group(2) or ""

        # Extract Strong's codes
        lem_m = _LEMMA_ATTR_RE.search(attrs)
        lem_str = lem_m.group(1) if lem_m else ""
        strongs = [
            f"{letter}{int(num)}"
            for letter, num in _STRONG_CODE_RE.findall(lem_str)
        ]

        # Extract Textus Receptus lemma if present
        tr_m = _TR_LEMMA_RE.search(lem_str)
        tr_lemma = tr_m.group(1) if tr_m else None

        # Extract morphology
        morph_m = _MORPH_ATTR_RE.search(attrs)
        morph = morph_m.group(1) if morph_m else None

        # Extract source alignment
        src_m = _SRC_ATTR_RE.search(attrs)
        src = src_m.group(1) if src_m else None

        # Clean text span
        span_text = html.unescape(inner_text).strip()

        tokens.append(
            WordToken(
                index=i,
                text=span_text,
                strongs=strongs,
                lemma=tr_lemma,
                morph=morph,
                src=src,
            )
        )
    return tokens


_TABLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    osis TEXT PRIMARY KEY,
    order_num INTEGER NOT NULL,
    name TEXT NOT NULL,
    testament TEXT NOT NULL,
    chapters INTEGER NOT NULL,
    verses INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS verses (
    id TEXT PRIMARY KEY,
    osis TEXT NOT NULL REFERENCES books(osis),
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    clean_text TEXT NOT NULL,
    strongs_json TEXT NOT NULL,
    tokens_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS translations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    year INTEGER,
    license TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS translation_verses (
    translation_id TEXT NOT NULL REFERENCES translations(id),
    verse_id TEXT NOT NULL,
    osis TEXT NOT NULL REFERENCES books(osis),
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (translation_id, verse_id)
);

CREATE TABLE IF NOT EXISTS cross_references (
    from_verse TEXT NOT NULL,
    to_verse TEXT NOT NULL,
    votes INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (from_verse, to_verse)
);
"""

_INDICES_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_verses_osis_ch ON verses(osis, chapter, verse);
CREATE INDEX IF NOT EXISTS idx_verses_osis ON verses(osis);
CREATE INDEX IF NOT EXISTS idx_trans_verses_verse ON translation_verses(verse_id);
CREATE INDEX IF NOT EXISTS idx_trans_verses_ch ON translation_verses(translation_id, osis, chapter);
CREATE INDEX IF NOT EXISTS idx_xrefs_from ON cross_references(from_verse, votes DESC);
CREATE INDEX IF NOT EXISTS idx_xrefs_to ON cross_references(to_verse);
"""

_FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS bible_fts USING fts5(
    id UNINDEXED,
    osis UNINDEXED,
    clean_text,
    content='verses',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS verses_ai AFTER INSERT ON verses BEGIN
    INSERT INTO bible_fts(rowid, id, osis, clean_text)
    VALUES (new.rowid, new.id, new.osis, new.clean_text);
END;

CREATE TRIGGER IF NOT EXISTS verses_ad AFTER DELETE ON verses BEGIN
    INSERT INTO bible_fts(bible_fts, rowid, id, osis, clean_text)
    VALUES ('delete', old.rowid, old.id, old.osis, old.clean_text);
END;

CREATE TRIGGER IF NOT EXISTS verses_au AFTER UPDATE ON verses BEGIN
    INSERT INTO bible_fts(bible_fts, rowid, id, osis, clean_text)
    VALUES ('delete', old.rowid, old.id, old.osis, old.clean_text);
    INSERT INTO bible_fts(rowid, id, osis, clean_text)
    VALUES (new.rowid, new.id, new.osis, new.clean_text);
END;
"""


class BibleDB:
    """Disk-backed SQLite database engine for whole-Bible English text and Strong's tags."""

    def __init__(self, db_path: str | Path | None = None, repo_root: str | Path | None = None):
        self.repo_root = get_repo_root() if repo_root is None else Path(repo_root)
        p = Path(db_path) if db_path is not None else Path(DEFAULT_BIBLE_DB)
        if p.is_absolute():
            self.db_path = p
        elif (self.repo_root / p).exists():
            self.db_path = self.repo_root / p
        else:
            self.db_path = data_path(p)

        self._conn: Optional[sqlite3.Connection] = None
        self._readonly_conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._ensure_translation_tables()
        return self._conn

    @property
    def readonly_conn(self) -> sqlite3.Connection:
        """Sidecar-free read-only connection for runtime queries (ADR-027 §5).

        ``conn`` is builder/ingest-only: opening it runs
        ``_ensure_translation_tables()`` (a write) and enables WAL on a
        read-write handle, so runtime reads through it both mutate source
        data and litter ``-wal``/``-shm`` sidecars. Reads go through
        :func:`search.dbaccess.connect_db_reader` instead.

        If this process has already written through ``conn``, reads go
        through it: immutable reads ignore uncheckpointed WAL frames and
        would return stale data.
        """
        if self._conn is not None:
            return self._conn
        if self._readonly_conn is None:
            self._readonly_conn = connect_db_reader(
                self.db_path,
                row_factory=sqlite3.Row,
                check_same_thread=False,
            )
        return self._readonly_conn

    def exists(self) -> bool:
        return self.db_path.is_file() and self.db_path.stat().st_size > 0

    def init_db(self, force: bool = False, create_indices: bool = True) -> None:
        """Initialize database tables and triggers."""
        if force:
            self.close()
            if self.db_path.exists():
                self.db_path.unlink()
        with self.conn:
            self.conn.executescript(_TABLES_SCHEMA)
            if create_indices:
                self.create_indices()

    def create_indices(self) -> None:
        """Build B-Tree indices and FTS virtual table."""
        with self.conn:
            self.conn.executescript(_INDICES_SCHEMA)
            self.conn.executescript(_FTS_SCHEMA)

    def close(self) -> None:
        if self._conn is not None:
            self._checkpoint()
            self._conn.close()
            self._conn = None
        if self._readonly_conn is not None:
            self._readonly_conn.close()
            self._readonly_conn = None

    def _checkpoint(self) -> None:
        """Fold WAL frames into the main file on close (ADR-027 §5).

        A busy checkpoint is benign (the WAL-aware reader fallback keeps
        readers correct); other SQLite errors are real failures and raise.
        """
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except sqlite3.OperationalError as exc:
            if "busy" in str(exc).lower() or "locked" in str(exc).lower():
                return
            raise

    def __enter__(self) -> BibleDB:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def count(self) -> dict[str, int]:
        """Return total book and verse counts."""
        if not self.exists():
            return {"books": 0, "verses": 0}
        try:
            with self.readonly_conn:
                b_cnt = self.readonly_conn.execute("SELECT COUNT(*) FROM books;").fetchone()[0]
                v_cnt = self.readonly_conn.execute("SELECT COUNT(*) FROM verses;").fetchone()[0]
                return {"books": b_cnt, "verses": v_cnt}
        except sqlite3.OperationalError:
            return {"books": 0, "verses": 0}

    def get_verse(self, verse_ref: str) -> Optional[dict[str, Any]]:
        """Fetch verse record by canonical reference (e.g. 'Gen.1.1' or 'John 3:16')."""
        if not self.exists():
            return None
        try:
            osis, ch, v1, _ = parse_passage_ref(verse_ref)
        except ValueError:
            return None

        v_num = v1 if v1 is not None else 1
        cur = self.readonly_conn.execute(
            """
            SELECT v.*, b.name as book_name, b.testament
            FROM verses v
            JOIN books b ON v.osis = b.osis
            WHERE v.osis = ? AND v.chapter = ? AND v.verse = ?;
            """,
            (osis, ch, v_num),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._format_verse_row(row)

    def get_passage(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """Fetch one or more verses for a passage (e.g. 'John 3:16-18' or 'Psalm 23')."""
        if not self.exists():
            return []
        osis, ch, v1, v2 = parse_passage_ref(query)

        if v1 is None and v2 is None:
            # Whole chapter
            cur = self.readonly_conn.execute(
                """
                SELECT v.*, b.name as book_name, b.testament
                FROM verses v
                JOIN books b ON v.osis = b.osis
                WHERE v.osis = ? AND v.chapter = ?
                ORDER BY v.verse ASC;
                """,
                (osis, ch),
            )
        else:
            cur = self.readonly_conn.execute(
                """
                SELECT v.*, b.name as book_name, b.testament
                FROM verses v
                JOIN books b ON v.osis = b.osis
                WHERE v.osis = ? AND v.chapter = ? AND v.verse >= ? AND v.verse <= ?
                ORDER BY v.verse ASC;
                """,
                (osis, ch, v1, v2),
            )

        return [self._format_verse_row(r) for r in cur.fetchall()]

    def search(
        self,
        query: str,
        limit: int = 50,
        book: Optional[str] = None,
        testament: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Full-text search across whole-Bible verses using BM25 ranking."""
        if not self.exists() or not query.strip():
            return []

        # Sanitize FTS query
        clean_q = re.sub(r'[^\w\s]', ' ', query).strip()
        if not clean_q:
            return []
        fts_term = " ".join(f'"{word}"' for word in clean_q.split())

        sql = """
        SELECT v.*, b.name as book_name, b.testament, bm25(bible_fts) as rank
        FROM bible_fts f
        JOIN verses v ON f.rowid = v.rowid
        JOIN books b ON v.osis = b.osis
        WHERE bible_fts MATCH ?
        """
        params: list[Any] = [fts_term]

        if book:
            osis = resolve_book_code(book)
            sql += " AND v.osis = ?"
            params.append(osis)
        elif testament:
            t_clean = testament.strip().upper()
            if t_clean not in ("OT", "NT"):
                raise ValueError(f"Invalid testament '{testament}'. Expected 'OT' or 'NT'.")
            sql += " AND b.testament = ?"
            params.append(t_clean)

        sql += " ORDER BY rank ASC LIMIT ?;"
        params.append(limit)

        cur = self.readonly_conn.execute(sql, params)
        return [self._format_verse_row(r) for r in cur.fetchall()]

    def find_by_strongs(self, strongs_code: str, limit: int = 50) -> list[dict[str, Any]]:
        """Find verses containing a specific Hebrew or Greek Strong's code."""
        if not self.exists():
            return []
        m = re.match(r"^([HGhg]?)0*(\d+)$", strongs_code.strip())
        if not m:
            raise ValueError(f"Invalid Strong's code format: '{strongs_code}'")
        prefix = (m.group(1) or "H").upper()
        clean_s = f"{prefix}{int(m.group(2))}"
        search_pattern = f'%"{clean_s}"%'
        cur = self.readonly_conn.execute(
            """
            SELECT v.*, b.name as book_name, b.testament
            FROM verses v
            JOIN books b ON v.osis = b.osis
            WHERE v.strongs_json LIKE ?
            ORDER BY b.order_num, v.chapter, v.verse
            LIMIT ?;
            """,
            (search_pattern, limit),
        )
        return [self._format_verse_row(r) for r in cur.fetchall()]

    def _ensure_translation_tables(self) -> None:
        """Ensure multi-translation tables and indices exist."""
        if not self.db_path.exists() or self.db_path.stat().st_size == 0:
            return
        if self._conn is None:
            _ = self.conn
            return
        try:
            with self._conn:
                self._conn.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    year INTEGER,
                    license TEXT NOT NULL,
                    is_default INTEGER NOT NULL DEFAULT 0
                );
                """)
                self._conn.execute("""
                CREATE TABLE IF NOT EXISTS translation_verses (
                    translation_id TEXT NOT NULL,
                    verse_id TEXT NOT NULL,
                    osis TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    verse INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    PRIMARY KEY (translation_id, verse_id)
                );
                """)
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_trans_verses_verse ON translation_verses(verse_id);")
                self._conn.execute("CREATE INDEX IF NOT EXISTS idx_trans_verses_ch ON translation_verses(translation_id, osis, chapter);")
                self._conn.execute("""
                INSERT OR IGNORE INTO translations (id, name, year, license, is_default)
                VALUES ('kjv', 'King James Version', 1769, 'Public Domain', 1);
                """)
        except sqlite3.OperationalError:
            pass

    def list_translations(self) -> list[dict[str, Any]]:
        """List all available translations in the database."""
        if not self.exists():
            return []
        try:
            with self.readonly_conn:
                cur = self.readonly_conn.execute(
                    "SELECT id, name, year, license, is_default FROM translations ORDER BY is_default DESC, year ASC, id ASC;"
                )
                return [dict(r) for r in cur.fetchall()]
        except sqlite3.OperationalError:
            return []

    def get_verse_translations(
        self,
        verse_ref: str,
        translation_ids: list[str] | None = None,
    ) -> dict[str, str]:
        """Fetch all translation renderings for a specific verse (e.g. 'Gen.1.1' or 'John 3:16').

        Returns mapping of translation_id -> verse text (including 'kjv' from verses table).
        """
        if not self.exists():
            return {}
        try:
            osis, ch, v1, _ = parse_passage_ref(verse_ref)
        except ValueError:
            return {}
        v_num = v1 if v1 is not None else 1
        v_id = f"{osis}.{ch}.{v_num}"

        result: dict[str, str] = {}
        wanted_kjv = translation_ids is None or "kjv" in {t.lower() for t in translation_ids}

        # 1. Fetch KJV clean_text from primary verses table if requested and present
        if wanted_kjv:
            try:
                cur_kjv = self.readonly_conn.execute(
                    "SELECT clean_text FROM verses WHERE osis = ? AND chapter = ? AND verse = ?;",
                    (osis, ch, v_num),
                )
                row_kjv = cur_kjv.fetchone()
                if row_kjv:
                    result["kjv"] = row_kjv["clean_text"]
            except sqlite3.OperationalError:
                pass

        # 2. Fetch parallel translations
        try:
            if translation_ids is not None:
                wanted = [t.lower() for t in translation_ids if t.lower() != "kjv"]
                if wanted:
                    placeholders = ",".join("?" for _ in wanted)
                    sql = (
                        f"SELECT translation_id, text FROM translation_verses "
                        f"WHERE verse_id = ? AND translation_id IN ({placeholders});"
                    )
                    cur = self.readonly_conn.execute(sql, [v_id] + wanted)
                    for r in cur.fetchall():
                        result[r["translation_id"]] = r["text"]
            else:
                cur = self.readonly_conn.execute(
                    "SELECT translation_id, text FROM translation_verses WHERE verse_id = ?;",
                    (v_id,),
                )
                for r in cur.fetchall():
                    result[r["translation_id"]] = r["text"]
        except sqlite3.OperationalError:
            pass

        return result

    def get_chapter_translations(
        self,
        osis: str,
        chapter: int,
        translation_ids: list[str] | None = None,
    ) -> dict[int, dict[str, str]]:
        """Fetch all translation renderings for an entire chapter in a single batch query.

        Returns mapping: verse_number -> {translation_id: text}.
        """
        if not self.exists():
            return {}
        try:
            norm_osis = resolve_book_code(osis)
        except ValueError:
            return {}

        result: dict[int, dict[str, str]] = {}
        wanted_kjv = translation_ids is None or "kjv" in {t.lower() for t in translation_ids}

        # 1. Fetch KJV verses if requested and present
        if wanted_kjv:
            try:
                cur_kjv = self.readonly_conn.execute(
                    "SELECT verse, clean_text FROM verses WHERE osis = ? AND chapter = ? ORDER BY verse ASC;",
                    (norm_osis, chapter),
                )
                for r in cur_kjv.fetchall():
                    v_num = r["verse"]
                    if v_num not in result:
                        result[v_num] = {}
                    result[v_num]["kjv"] = r["clean_text"]
            except sqlite3.OperationalError:
                pass

        # 2. Fetch parallel translation verses
        try:
            if translation_ids is not None:
                wanted = [t.lower() for t in translation_ids if t.lower() != "kjv"]
                if wanted:
                    placeholders = ",".join("?" for _ in wanted)
                    sql = (
                        f"SELECT verse, translation_id, text FROM translation_verses "
                        f"WHERE osis = ? AND chapter = ? AND translation_id IN ({placeholders}) "
                        f"ORDER BY verse ASC, translation_id ASC;"
                    )
                    cur = self.readonly_conn.execute(sql, [norm_osis, chapter] + wanted)
                    for r in cur.fetchall():
                        v_num = r["verse"]
                        if v_num not in result:
                            result[v_num] = {}
                        result[v_num][r["translation_id"]] = r["text"]
            else:
                sql = (
                    "SELECT verse, translation_id, text FROM translation_verses "
                    "WHERE osis = ? AND chapter = ? "
                    "ORDER BY verse ASC, translation_id ASC;"
                )
                cur = self.readonly_conn.execute(sql, (norm_osis, chapter))
                for r in cur.fetchall():
                    v_num = r["verse"]
                    if v_num not in result:
                        result[v_num] = {}
                    result[v_num][r["translation_id"]] = r["text"]
        except sqlite3.OperationalError:
            pass

        return result

    def get_cross_references(
        self,
        verse_ref: str,
        limit: int = 25,
        min_votes: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch ranked Treasury of Scripture Knowledge (TSK) cross references for a verse.

        Returns list of dicts: {"to_verse": str, "votes": int, "preview": str}.
        """
        if not self.exists():
            return []
        try:
            osis, ch, v1, _ = parse_passage_ref(verse_ref)
        except ValueError:
            return []
        v_num = v1 if v1 is not None else 1
        v_id = f"{osis}.{ch}.{v_num}"

        try:
            cur = self.readonly_conn.execute(
                """
                SELECT to_verse, votes
                FROM cross_references
                WHERE from_verse = ? AND votes >= ?
                ORDER BY votes DESC
                LIMIT ?;
                """,
                (v_id, min_votes, limit),
            )
            rows = cur.fetchall()
            if not rows:
                return []

            # Batch fetch preview texts for all candidates in a single roundtrip
            preview_coords: list[tuple[str, int, int]] = []
            for r in rows:
                parts = r["to_verse"].split("-")[0].split(".")
                if len(parts) == 3:
                    try:
                        preview_coords.append((parts[0], int(parts[1]), int(parts[2])))
                    except ValueError:
                        pass

            preview_map: dict[str, str] = {}
            if preview_coords:
                placeholders = ", ".join("(?, ?, ?)" for _ in preview_coords)
                params: list[Any] = [val for coord in preview_coords for val in coord]
                try:
                    p_cur = self.readonly_conn.execute(
                        f"SELECT osis, chapter, verse, clean_text FROM verses WHERE (osis, chapter, verse) IN (VALUES {placeholders});",
                        params,
                    )
                    for prow in p_cur.fetchall():
                        preview_map[f"{prow['osis']}.{prow['chapter']}.{prow['verse']}"] = prow["clean_text"]
                except sqlite3.OperationalError:
                    pass

            results: list[dict[str, Any]] = []
            for r in rows:
                to_ref = r["to_verse"]
                preview_ref = to_ref.split("-")[0]
                prev_text = preview_map.get(preview_ref, "")
                results.append({
                    "to_verse": to_ref,
                    "to_ref": to_ref,
                    "votes": r["votes"],
                    "preview": prev_text,
                    "preview_text": prev_text,
                })
            return results
        except sqlite3.OperationalError:
            return []

    def ingest_translation(
        self,
        translation_id: str,
        name: str,
        year: int,
        license: str,
        json_path: str | Path,
        is_default: bool = False,
        batch_size: int = 2000,
    ) -> int:
        """Ingest a translation JSON into the database.

        Returns total number of verses inserted.
        """
        src_path = Path(json_path)
        if not src_path.is_file():
            raise FileNotFoundError(f"Translation JSON not found at {src_path}")

        t_id = translation_id.strip().lower()
        self._ensure_translation_tables()

        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO translations (id, name, year, license, is_default) VALUES (?, ?, ?, ?, ?);",
                (t_id, name, year, license, 1 if is_default else 0),
            )

        payload = json.loads(src_path.read_text(encoding="utf-8"))
        rows: list[tuple[str, str, str, int, int, str]] = []
        count = 0

        def flush():
            nonlocal count
            if rows:
                with self.conn:
                    self.conn.executemany(
                        "INSERT OR REPLACE INTO translation_verses (translation_id, verse_id, osis, chapter, verse, text) "
                        "VALUES (?, ?, ?, ?, ?, ?);",
                        rows,
                    )
                count += len(rows)
                rows.clear()

        for book in payload.get("books", []):
            raw_name = book.get("name", "")
            try:
                osis = resolve_book_code(raw_name)
            except ValueError:
                continue
            for ch in book.get("chapters", []):
                ch_num = int(ch.get("chapter", 1))
                for v in ch.get("verses", []):
                    v_num = int(v.get("verse", 1))
                    raw_text = v.get("text", "")
                    clean_text = html.unescape(raw_text).strip()
                    clean_text = _WS_RE.sub(" ", clean_text)
                    v_id = f"{osis}.{ch_num}.{v_num}"
                    rows.append((t_id, v_id, osis, ch_num, v_num, clean_text))
                    if len(rows) >= batch_size:
                        flush()

        flush()
        return count

    @staticmethod
    def _format_verse_row(row: sqlite3.Row) -> dict[str, Any]:
        result = {
            "id": row["id"],
            "osis": row["osis"],
            "book_name": row["book_name"],
            "testament": row["testament"],
            "chapter": row["chapter"],
            "verse": row["verse"],
            "text": row["text"],
            "clean_text": row["clean_text"],
            "strongs": json.loads(row["strongs_json"]),
            "tokens": json.loads(row["tokens_json"]),
        }
        if "rank" in row.keys():
            result["rank"] = row["rank"]
        return result


def compile_bible_db(
    json_path: str | Path = DEFAULT_KJV_JSON,
    db_path: str | Path = DEFAULT_BIBLE_DB,
    repo_root: str | Path = ".",
    force: bool = False,
    batch_size: int = 1000,
) -> Path:
    """Compile whole-Bible KJV JSON into normalized SQLite database."""
    root = Path(repo_root)
    src_json = root / json_path
    if not src_json.is_file():
        raise FileNotFoundError(
            f"KJV OSIS source missing at {src_json}. "
            "Run scripts/fetch_sources.sh to download pinned data."
        )

    target_db = root / db_path
    with BibleDB(db_path=target_db, repo_root=root) as db:
        db.init_db(force=force, create_indices=False)

        # PRAGMA optimizations for bulk compile
        db.conn.execute("PRAGMA synchronous = OFF;")
        db.conn.execute("PRAGMA journal_mode = MEMORY;")
        db.conn.execute("PRAGMA foreign_keys = OFF;")

        start_time = time.time()
        payload = json.loads(src_json.read_text(encoding="utf-8"))

        # Populate books table first
        book_rows = [
            (
                b.osis,
                b.order,
                b.name,
                b.testament,
                b.chapters,
                b.verses,
            )
            for b in BIBLE_BOOKS.values()
        ]
        with db.conn:
            db.conn.executemany(
                "INSERT OR REPLACE INTO books VALUES (?, ?, ?, ?, ?, ?);",
                book_rows,
            )

        verse_rows = []

        def flush_verses():
            if verse_rows:
                with db.conn:
                    db.conn.executemany(
                        "INSERT OR REPLACE INTO verses VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                        verse_rows,
                    )
                verse_rows.clear()

        for raw_book in payload.get("books", []):
            raw_name = raw_book.get("name", "")
            osis = resolve_book_code(raw_name)

            for raw_ch in raw_book.get("chapters", []):
                ch_num = int(raw_ch.get("chapter", 1))
                for raw_v in raw_ch.get("verses", []):
                    v_num = int(raw_v.get("verse", 1))
                    v_id = f"{osis}.{ch_num}.{v_num}"
                    raw_text = raw_v.get("text", "")
                    c_text = clean_verse_text(raw_text)

                    tokens = extract_tokens(raw_text)
                    all_strongs = sorted(list({s for t in tokens for s in t.strongs}))

                    tokens_data = [asdict(t) for t in tokens]

                    verse_rows.append((
                        v_id,
                        osis,
                        ch_num,
                        v_num,
                        raw_text,
                        c_text,
                        json.dumps(all_strongs),
                        json.dumps(tokens_data),
                    ))

                    if len(verse_rows) >= batch_size:
                        flush_verses()

        flush_verses()

        # Rebuild indices and FTS5 table
        db.create_indices()
        with db.conn:
            db.conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild');")
        db.conn.execute("PRAGMA journal_mode = WAL;")
        db.conn.execute("PRAGMA synchronous = NORMAL;")
        db.conn.execute("PRAGMA foreign_keys = ON;")

        elapsed = time.time() - start_time
        counts = db.count()
        print(f"Compiled {target_db} in {elapsed:.2f}s:")
        print(f"  - Books:  {counts['books']}")
        print(f"  - Verses: {counts['verses']}")

    return target_db


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compile whole-Bible KJV into normalized SQLite database."
    )
    parser.add_argument(
        "--compile",
        "-c",
        action="store_true",
        help="Compile KJV database from KJV-osis.json",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--json",
        default=DEFAULT_KJV_JSON,
        help=f"Path to KJV OSIS JSON source (default: {DEFAULT_KJV_JSON})",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_BIBLE_DB,
        help=f"Path to output SQLite database (default: {DEFAULT_BIBLE_DB})",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force recompilation even if database exists",
    )
    args = parser.parse_args(argv)

    compile_bible_db(
        json_path=args.json,
        db_path=args.db,
        repo_root=args.repo,
        force=args.force or args.compile,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
