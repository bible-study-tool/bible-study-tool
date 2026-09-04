"""Spirit of Prophecy (EGW) JIT SQLite database & resolution engine.

In accordance with ADR-0011, this module manages the local, offline SQLite
database (data/egw.db) containing Spirit of Prophecy paragraph text, enabling
on-demand Just-In-Time (JIT) resolution of canonical citation tokens
(e.g., 'egw:PP.57.1' -> Patriarchs and Prophets, page 57, paragraph 1).

Key properties:
  * Canonical token syntax: `egw:BOOK.PAGE.PARAGRAPH` or `BOOK.PAGE.PARAGRAPH`
    (e.g. `egw:PP.57.1`, `DA.19.2`, `GC.582.1`).
  * Offline-first and license-safe (ADR-0002, NOTICE.md): The repository stores
    only tokens and fair-use study summaries; full paragraph text lives in the
    local gitignored SQLite database with FTS5 full-text indexing.
  * Fast FTS5 search with BM25 ranking and snippet generation.
"""

from __future__ import annotations

import json
import re
import sqlite3
import textwrap
from pathlib import Path
from typing import Any, Iterable

# Default database location inside gitignored data/ directory
DEFAULT_EGW_DB = "data/egw.db"

# Canonical abbreviation crosswalk for common Spirit of Prophecy works
KNOWN_EGW_BOOKS: dict[str, str] = {
    "PP": "Patriarchs and Prophets",
    "PK": "Prophets and Kings",
    "DA": "The Desire of Ages",
    "AA": "The Acts of the Apostles",
    "GC": "The Great Controversy",
    "SC": "Steps to Christ",
    "COL": "Christ's Object Lessons",
    "MB": "Thoughts from the Mount of Blessing",
    "Ed": "Education",
    "ED": "Education",
    "MH": "The Ministry of Healing",
    "1T": "Testimonies for the Church, Vol. 1",
    "2T": "Testimonies for the Church, Vol. 2",
    "3T": "Testimonies for the Church, Vol. 3",
    "4T": "Testimonies for the Church, Vol. 4",
    "5T": "Testimonies for the Church, Vol. 5",
    "6T": "Testimonies for the Church, Vol. 6",
    "7T": "Testimonies for the Church, Vol. 7",
    "8T": "Testimonies for the Church, Vol. 8",
    "9T": "Testimonies for the Church, Vol. 9",
    "1SM": "Selected Messages, Book 1",
    "2SM": "Selected Messages, Book 2",
    "3SM": "Selected Messages, Book 3",
    "EW": "Early Writings",
    "1SP": "The Spirit of Prophecy, Vol. 1",
    "2SP": "The Spirit of Prophecy, Vol. 2",
    "3SP": "The Spirit of Prophecy, Vol. 3",
    "4SP": "The Spirit of Prophecy, Vol. 4",
    "LS": "Life Sketches of Ellen G. White",
    "LP": "Sketches from the Life of Paul",
    "TM": "Testimonies to Ministers and Gospel Workers",
    "MYP": "Messages to Young People",
    "AH": "The Adventist Home",
    "CG": "Child Guidance",
    "GW": "Gospel Workers",
    "Ev": "Evangelism",
    "CS": "Counsels on Stewardship",
    "CD": "Counsels on Diet and Foods",
    "CH": "Counsels on Health",
    "MM": "Medical Ministry",
    "1MCP": "Mind, Character, and Personality, Vol. 1",
    "2MCP": "Mind, Character, and Personality, Vol. 2",
    "CTBH": "Christian Temperance and Bible Hygiene",
    "HS": "Historical Sketches of the Foreign Missions",
    "GCB": "General Conference Bulletin",
    "RH": "Review and Herald",
    "ST": "Signs of the Times",
    "YI": "The Youth's Instructor",
}

# Curated Classifications & Official White Estate Publication Codes (414 codes)
DEVOTIONALS: set[str] = {
    "AG", "BLJ", "CC", "CTr", "FH", "FLB", "HB", "HP", "LHU",
    "ML", "Mar", "OFC", "OHC", "RC", "RRe", "SD", "TDG", "TMK",
    "UL", "YRP",
}

BIOGRAPHIES: set[str] = {
    "1BIO", "2BIO", "3BIO", "4BIO", "5BIO", "6BIO",
    "LS", "LS80", "LS88", "LSMS", "CET",
}

PERIODICAL_CODES: set[str] = {
    "RH1", "RH2", "RH3", "RH4", "RH5", "RH6",
    "ST1", "ST2", "ST3", "ST4",
    "YI", "BE", "PT", "HR", "SW", "TMis",
}

SPECIAL_COLLECTIONS: set[str] = {
    "1888", "1SAT", "2SAT", "SpM", "PC", "KC", "ApM", "WLF", "ExV", "ExV54",
}

STANDARD_BOOKS: list[str] = [
    "1BC", "2BC", "3BC", "4BC", "5BC", "6BC", "7BC", "7ABC", "1MCP", "2MCP",
    "1SG", "2SG", "3SG", "4aSG", "4bSG", "1SM", "2SM", "3SM", "1SP", "2SP",
    "3SP", "4SP", "1T", "2T", "3T", "4T", "5T", "6T", "7T", "8T", "9T",
    "1TT", "2TT", "3TT", "AA", "AC", "AH", "AY", "BOE", "CCh", "CD", "CE",
    "CEv", "CG", "CH", "CIHS", "CL", "CM", "CME", "COL", "CS", "CSA", "CSW",
    "CT", "CTBH", "CW", "Con", "ChL", "ChS", "DA", "DD", "DG", "EGWE", "EP",
    "Ed", "Ev", "FE", "FW", "GC", "GC88", "GW", "GW92", "GrH_a", "GrH_c",
    "HDL", "HF", "HFM", "HH", "HL", "HLv", "HS", "Hvn", "LDE", "LF", "LP",
    "LYL", "MB", "MC", "MH", "MHH", "MM", "MTC", "MYP", "NL", "PaM", "PCP",
    "PK", "PM", "PP", "Pr", "RR", "RY", "SA", "SC", "SJ", "SL", "SR", "SS",
    "STJ", "SWk", "TA", "TE", "TM", "TR", "TSA", "TSB", "TSDF", "TSS", "TT",
    "Te", "TEd", "VSS", "WM", "WV",
]

MR_CODES: list[str] = [f"{i}MR" for i in range(1, 22)]

PAMPHLET_CODES: list[str] = (
    [f"SpTA{i:02d}" for i in range(1, 13)]
    + [f"SpTB{i:02d}" for i in range(1, 20)]
    + ["SpTEd"]
    + [f"PH{i:03d}" for i in range(1, 181)]
)

ALL_OFFICIAL_EGW_CODES: dict[str, str] = {
    code.upper(): code
    for code in (
        list(KNOWN_EGW_BOOKS.keys())
        + STANDARD_BOOKS
        + list(DEVOTIONALS)
        + list(BIOGRAPHIES)
        + list(PERIODICAL_CODES)
        + list(SPECIAL_COLLECTIONS)
        + MR_CODES
        + PAMPHLET_CODES
    )
}

_TOKEN_RE = re.compile(
    r"^(?:egw:)?(?=[0-9A-Za-z]*[A-Za-z])([A-Za-z0-9]+)\.([0-9]+)(?:\.([0-9]+))?$",
    re.IGNORECASE,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS egw_paragraphs (
    id TEXT PRIMARY KEY,
    book_code TEXT NOT NULL,
    book_title TEXT NOT NULL,
    chapter_num INTEGER,
    chapter_title TEXT,
    page INTEGER NOT NULL,
    paragraph INTEGER NOT NULL,
    ref_code TEXT,
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_egw_book_page ON egw_paragraphs(book_code, page);

CREATE VIRTUAL TABLE IF NOT EXISTS egw_fts USING fts5(
    id UNINDEXED,
    book_code UNINDEXED,
    book_title UNINDEXED,
    chapter_title,
    text,
    content='egw_paragraphs',
    content_rowid='rowid',
    tokenize='porter unicode61'
);
"""

_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS egw_ai AFTER INSERT ON egw_paragraphs BEGIN
  INSERT INTO egw_fts(rowid, id, book_code, book_title, chapter_title, text)
  VALUES (new.rowid, new.id, new.book_code, new.book_title, new.chapter_title, new.text);
END;

CREATE TRIGGER IF NOT EXISTS egw_ad AFTER DELETE ON egw_paragraphs BEGIN
  INSERT INTO egw_fts(egw_fts, rowid, id, book_code, book_title, chapter_title, text)
  VALUES ('delete', old.rowid, old.id, old.book_code, old.book_title, old.chapter_title, old.text);
END;

CREATE TRIGGER IF NOT EXISTS egw_au AFTER UPDATE OF id, book_code, book_title, chapter_title, text ON egw_paragraphs BEGIN
  INSERT INTO egw_fts(egw_fts, rowid, id, book_code, book_title, chapter_title, text)
  VALUES ('delete', old.rowid, old.id, old.book_code, old.book_title, old.chapter_title, old.text);
  INSERT INTO egw_fts(rowid, id, book_code, book_title, chapter_title, text)
  VALUES (new.rowid, new.id, new.book_code, new.book_title, new.chapter_title, new.text);
END;
"""

_UPSERT_PARAGRAPH_SQL = """
INSERT INTO egw_paragraphs (
    id, book_code, book_title, chapter_num, chapter_title, page, paragraph, ref_code, text
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    book_code = excluded.book_code,
    book_title = excluded.book_title,
    chapter_num = excluded.chapter_num,
    chapter_title = excluded.chapter_title,
    page = excluded.page,
    paragraph = excluded.paragraph,
    ref_code = excluded.ref_code,
    text = excluded.text;
"""


def normalize_token(token: str) -> tuple[str, str, int, int]:
    """Parse and normalize an EGW citation token.

    Args:
        token: e.g. "egw:PP.57.1", "pp.57.1", or "PP.57".

    Returns:
        (canonical_id, book_code, page, paragraph)
        e.g. ("PP.57.1", "PP", 57, 1)

    Raises:
        ValueError: if the token cannot be parsed.
    """
    s = (token or "").strip()
    m = _TOKEN_RE.match(s)
    if not m:
        raise ValueError(
            f"Invalid EGW citation token '{token}'. "
            f"Expected shape: BOOK.PAGE.PARAGRAPH or egw:BOOK.PAGE.PARAGRAPH (e.g., PP.57.1)"
        )
    book_code = m.group(1).upper()
    page = int(m.group(2))
    para = int(m.group(3)) if m.group(3) is not None else 1
    canonical_id = f"{book_code}.{page}.{para}"
    return canonical_id, book_code, page, para


def is_egw_token(token: str) -> bool:
    """Return True if string conforms to an EGW token shape."""
    try:
        normalize_token(token)
        return True
    except ValueError:
        return False


class EgwDB:
    """Local SQLite-backed database with FTS5 search for Spirit of Prophecy texts."""

    def __init__(self, db_path: str | Path | None = None, repo_root: str | Path = "."):
        self.repo_root = Path(repo_root)
        if db_path is None:
            self.db_path = self.repo_root / DEFAULT_EGW_DB
        else:
            p = Path(db_path)
            self.db_path = p if p.is_absolute() else self.repo_root / p

        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            # Enforce SQLite foreign keys and pragmas
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.execute("PRAGMA synchronous = NORMAL;")
            self._conn.execute("PRAGMA busy_timeout = 5000;")
            self._conn.execute("PRAGMA recursive_triggers = ON;")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> EgwDB:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def init_db(self, force: bool = False) -> None:
        """Initialize tables, indices, and FTS5 triggers."""
        if getattr(self, "_initialized", False) and not force:
            return
        cur = self.conn.cursor()
        cur.executescript(_SCHEMA)
        cur.executescript(_TRIGGERS)
        self.conn.commit()
        self._initialized = True
        self._has_tables = True

    def exists(self) -> bool:
        """True if the database file exists on disk and has tables."""
        if not self.db_path.exists():
            return False
        if getattr(self, "_has_tables", None) is None:
            try:
                cur = self.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='egw_paragraphs';"
                )
                self._has_tables = cur.fetchone() is not None
            except sqlite3.Error:
                return False
        return self._has_tables

    def insert_paragraph(
        self,
        book_code: str,
        page: int,
        paragraph: int,
        text: str,
        *,
        book_title: str | None = None,
        chapter_num: int | None = None,
        chapter_title: str | None = None,
        ref_code: str | None = None,
    ) -> str:
        """Insert or replace a paragraph.

        Returns:
            canonical_id: e.g. "PP.57.1"
        """
        self.init_db()
        book_code = book_code.strip().upper()
        canonical_id = f"{book_code}.{page}.{paragraph}"
        title = book_title or KNOWN_EGW_BOOKS.get(book_code, book_code)
        ref = ref_code or f"{book_code} {page}.{paragraph}"

        with self.conn:
            self.conn.execute(
                _UPSERT_PARAGRAPH_SQL,
                (canonical_id, book_code, title, chapter_num, chapter_title, page, paragraph, ref, text.strip()),
            )
        return canonical_id

    def insert_paragraphs_batch(self, items: Iterable[dict[str, Any]]) -> int:
        """Insert a batch of paragraphs in a single transaction."""
        self.init_db()
        rows = []
        for item in items:
            b_code = str(item["book_code"]).strip().upper()
            page = int(item["page"])
            para = int(item.get("paragraph", 1))
            canonical_id = item.get("id") or f"{b_code}.{page}.{para}"
            title = item.get("book_title") or KNOWN_EGW_BOOKS.get(b_code, b_code)
            ref = item.get("ref_code") or f"{b_code} {page}.{para}"
            txt = str(item["text"]).strip()
            chap_num = item.get("chapter_num")
            chap_title = item.get("chapter_title")
            rows.append((canonical_id, b_code, title, chap_num, chap_title, page, para, ref, txt))

        with self.conn:
            self.conn.executemany(_UPSERT_PARAGRAPH_SQL, rows)
        return len(rows)

    def fast_bulk_insert(
        self,
        items: Iterable[dict[str, Any]],
        batch_size: int = 5000,
    ) -> int:
        """Rapidly insert large batches of paragraphs by deferring FTS5 index updates.

        Temporarily drops insert/update triggers during insertion, inserts rows
        in high-speed batched transactions, and runs FTS5 'rebuild' in a single
        pass upon completion. 10x-50x faster for whole books or multi-volume corpuses.
        """
        self.init_db()

        # Temporarily drop triggers to avoid row-by-row FTS index maintenance
        with self.conn:
            self.conn.execute("DROP TRIGGER IF EXISTS egw_ai;")
            self.conn.execute("DROP TRIGGER IF EXISTS egw_ad;")
            self.conn.execute("DROP TRIGGER IF EXISTS egw_au;")

        total_inserted = 0
        batch: list[tuple] = []
        try:
            for item in items:
                b_code = str(item["book_code"]).strip().upper()
                page = int(item["page"])
                para = int(item.get("paragraph", 1))
                canonical_id = item.get("id") or f"{b_code}.{page}.{para}"
                title = item.get("book_title") or KNOWN_EGW_BOOKS.get(b_code, b_code)
                ref = item.get("ref_code") or f"{b_code} {page}.{para}"
                txt = str(item["text"]).strip()
                chap_num = item.get("chapter_num")
                chap_title = item.get("chapter_title")
                batch.append((canonical_id, b_code, title, chap_num, chap_title, page, para, ref, txt))

                if len(batch) >= batch_size:
                    with self.conn:
                        self.conn.executemany(_UPSERT_PARAGRAPH_SQL, batch)
                    total_inserted += len(batch)
                    batch.clear()

            if batch:
                with self.conn:
                    self.conn.executemany(_UPSERT_PARAGRAPH_SQL, batch)
                total_inserted += len(batch)
                batch.clear()
        finally:
            # Recreate triggers and rebuild FTS5 index in one pass
            with self.conn:
                self.conn.executescript(_TRIGGERS)
                if total_inserted > 0:
                    self.conn.execute("INSERT INTO egw_fts(egw_fts) VALUES('rebuild');")

        return total_inserted

    def has_paragraph(self, token: str) -> bool:
        """Check if a paragraph exists without fetching full text into memory."""
        if not self.exists():
            return False
        try:
            canonical_id, _, _, _ = normalize_token(token)
        except ValueError:
            return False
        cur = self.conn.execute("SELECT 1 FROM egw_paragraphs WHERE id = ? LIMIT 1;", (canonical_id,))
        return cur.fetchone() is not None

    def get_paragraph(self, token: str) -> dict[str, Any] | None:
        """Lookup a paragraph by token (e.g. 'egw:PP.57.1' or 'PP.57.1')."""
        if not self.exists():
            return None
        try:
            canonical_id, _, _, _ = normalize_token(token)
        except ValueError:
            return None

        cur = self.conn.execute(
            "SELECT * FROM egw_paragraphs WHERE id = ?;", (canonical_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_page(self, book_code: str, page: int) -> list[dict[str, Any]]:
        """Retrieve all paragraphs on a given page."""
        if not self.exists():
            return []
        b_code = book_code.strip().upper()
        cur = self.conn.execute(
            "SELECT * FROM egw_paragraphs WHERE book_code = ? AND page = ? ORDER BY paragraph ASC;",
            (b_code, page),
        )
        return [dict(r) for r in cur.fetchall()]

    def search(
        self,
        query: str,
        book_code: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search paragraphs via SQLite FTS5."""
        if not self.exists():
            return []

        # Sanitize query for FTS5 syntax
        clean_q = query.strip()
        if not clean_q:
            return []

        def _execute_search(fts_query: str):
            where_clauses = ["egw_fts MATCH ?"]
            params: list[Any] = [fts_query]
            if book_code:
                where_clauses.append("p.book_code = ?")
                params.append(book_code.strip().upper())
            params.append(limit)

            sql = f"""
            SELECT p.*,
                   snippet(egw_fts, 4, '[b]', '[/b]', '...', 28) as snippet,
                   bm25(egw_fts) as rank
            FROM egw_fts
            JOIN egw_paragraphs p ON egw_fts.rowid = p.rowid
            WHERE {' AND '.join(where_clauses)}
            ORDER BY rank
            LIMIT ?;
            """
            return self.conn.execute(sql, params)

        try:
            cur = _execute_search(clean_q)
        except sqlite3.OperationalError:
            # Fall back to searching as a literal phrase if raw query has unbalanced syntax
            try:
                escaped = clean_q.replace('"', '""')
                cur = _execute_search(f'"{escaped}"')
            except sqlite3.OperationalError:
                return []

        return [dict(r) for r in cur.fetchall()]

    def count(self) -> int:
        """Return total paragraph count."""
        if not self.exists():
            return 0
        cur = self.conn.execute("SELECT COUNT(*) FROM egw_paragraphs;")
        row = cur.fetchone()
        return row[0] if row else 0

    def ingest_json(self, json_path: str | Path) -> int:
        """Ingest paragraphs from a JSON file.

        Supported JSON formats:
          1. A list of objects with fields:
             book_code, page, paragraph, text, (optional: book_title, chapter_num, chapter_title)
          2. A dict with a 'paragraphs' array.
        """
        p = Path(json_path)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {json_path}")

        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "paragraphs" in data:
            data = data["paragraphs"]
        if not isinstance(data, list):
            raise ValueError("Expected JSON file containing an array of paragraph objects.")

        return self.insert_paragraphs_batch(data)

    def format_paragraph(self, p: dict[str, Any], width: int = 80) -> str:
        """Format paragraph for clean terminal/CLI reading."""
        token = f"egw:{p['id']}"
        ref = p.get("ref_code") or f"{p['book_code']} {p['page']}.{p['paragraph']}"
        book = p.get("book_title") or p["book_code"]
        chap_info = ""
        if p.get("chapter_num") or p.get("chapter_title"):
            c_num = f"Chapter {p['chapter_num']}: " if p.get("chapter_num") else ""
            c_title = p.get("chapter_title") or ""
            chap_info = f"\n{c_num}{c_title}"

        header = f"[{ref}] ({token}) — {book}, p. {p['page']}, para {p['paragraph']}{chap_info}"
        separator = "─" * min(len(header), width)
        body = textwrap.fill(p["text"], width=width)
        return f"{header}\n{separator}\n{body}\n"


def seed_core_genesis_passages(db: EgwDB) -> int:
    """Seed foundational Patriarchs and Prophets paragraphs for Genesis 1–3 study.

    Provides a clean, verified, minimal fair-use testing fixture dataset for
    offline development, cross-referencing, and automated verification without
    distributing copyrighted full volumes (NOTICE.md, ADR-0011). Full study
    materials are user-supplied via `--ingest-json`.
    """
    passages = [
        {
            "book_code": "PP",
            "book_title": "Patriarchs and Prophets",
            "chapter_num": 2,
            "chapter_title": "The Creation",
            "page": 44,
            "paragraph": 1,
            "text": (
                "The earth came forth from the hand of its Maker surpassing lovely. "
                "Its surface was gracefully diversified with hills and valleys, presenting "
                "a pleasing variety. There were no high, rugged mountains; no deep, "
                "hideous chasms; no barren precipices; but rounded knolls and gentle slopes, "
                "clothed with a carpet of living green."
            ),
        },
        {
            "book_code": "PP",
            "book_title": "Patriarchs and Prophets",
            "chapter_num": 2,
            "chapter_title": "The Creation",
            "page": 45,
            "paragraph": 1,
            "text": (
                "And God saw everything that He had made, and, behold, it was very good. "
                "A holy harmony pervaded the whole creation. Every creature was happy in "
                "its existence. There was no discord, no decay, no death."
            ),
        },
        {
            "book_code": "PP",
            "book_title": "Patriarchs and Prophets",
            "chapter_num": 2,
            "chapter_title": "The Creation",
            "page": 47,
            "paragraph": 1,
            "text": (
                "God sanctified and blessed the seventh day, because that in it He had "
                "rested from all His work which God created and made. The Sabbath was "
                "instituted at the close of creation week, and given to humanity as a "
                "perpetual memorial of the Creator's power and love."
            ),
        },
        {
            "book_code": "PP",
            "book_title": "Patriarchs and Prophets",
            "chapter_num": 3,
            "chapter_title": "The Temptation and Fall",
            "page": 53,
            "paragraph": 1,
            "text": (
                "In order to accomplish his work unperceived, Satan chose to employ as his "
                "medium the serpent—a disguise well adapted for his purpose of deception. "
                "The serpent was then one of the wisest and most beautiful creatures upon "
                "the earth. It had wings, and while flying through the air presented an "
                "appearance of dazzling brightness."
            ),
        },
        {
            "book_code": "PP",
            "book_title": "Patriarchs and Prophets",
            "chapter_num": 3,
            "chapter_title": "The Temptation and Fall",
            "page": 57,
            "paragraph": 1,
            "text": (
                "They heard the voice of the Lord God walking in the garden in the cool of "
                "the day. No longer did Adam and his companion greet the presence of God "
                "with joy, but with terror and shame they fled from His presence, seeking "
                "to hide in the deepest recesses of the forest."
            ),
        },
        {
            "book_code": "PP",
            "book_title": "Patriarchs and Prophets",
            "chapter_num": 4,
            "chapter_title": "The Plan of Redemption",
            "page": 65,
            "paragraph": 1,
            "text": (
                "The fall of man filled all heaven with sorrow. The world that God had "
                "made was blighted with the curse of sin, and inhabited by beings doomed "
                "to misery and death. There appeared no possible way of escape for those "
                "who had transgressed the law."
            ),
        },
        {
            "book_code": "PP",
            "book_title": "Patriarchs and Prophets",
            "chapter_num": 4,
            "chapter_title": "The Plan of Redemption",
            "page": 66,
            "paragraph": 1,
            "text": (
                "To man the first intimation of redemption was communicated in the sentence "
                "pronounced upon Satan in the garden. The Lord declared, 'I will put enmity "
                "between thee and the woman, and between thy seed and her seed; it shall bruise "
                "thy head, and thou shalt bruise his heel.' This sentence, uttered in the hearing "
                "of our first parents, was to them a promise."
            ),
        },
        {
            "book_code": "PP",
            "book_title": "Patriarchs and Prophets",
            "chapter_num": 4,
            "chapter_title": "The Plan of Redemption",
            "page": 68,
            "paragraph": 1,
            "text": (
                "The sacrificial offerings were ordained by God to be to man a perpetual "
                "reminder and a penitential acknowledgment of his sin, and a confession of his "
                "faith in the promised Redeemer. They were intended to impress upon the fallen "
                "race the solemn truth that it was sin that caused death."
            ),
        },
    ]
    return db.insert_paragraphs_batch(passages)
