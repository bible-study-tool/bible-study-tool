"""Query and lookup interface for Macula Hebrew linguistic and syntactic data.

Provides fast, in-memory lookups for:
  - Strong's Hebrew ↔ LXX Greek alignments and SDBH semantic domains
  - Verse syntactic clause structures and participant roles
  - Reverse lookups by Greek LXX Strong's number or SDBH core domain
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from search.macula.extract import (
    normalize_greek_strongs,
    normalize_hebrew_strongs,
    resolve_osis_book,
    resolve_role_query,
)
from search.macula.db import DEFAULT_MACULA_DB, MaculaSqliteDB

DEFAULT_ARTIFACT_PATH = "lexicons/macula-genesis.json"


def normalize_verse_ref(raw: str) -> str:
    """Normalize user input to canonical 'Book.c.v' format.

    Accepts:
      - 'Gen.1.1', 'Dan.8.14', 'Isa.53.5', 'Ps.23.1', 'Ps.51.0b'
      - 'GEN 1:1', 'DAN 8:14', 'ISA 53:5'
      - '1:1' or '1.1' (defaults to Gen for single-book compatibility)
      - 'gen-1-1' or 'gen-1-1-kjv'
      - 'Genesis 1:1', '1 Samuel 16:7', 'Song of Solomon 2:16'
    """
    cleaned = raw.strip()
    # Remove file extension or trailing qualifiers
    cleaned = re.sub(r"\.md$", "", cleaned)
    cleaned = re.sub(r"-kjv$", "", cleaned)

    # 1. Bare chapter:verse numbers (defaults to Gen)
    m_num = re.fullmatch(r"(\d+)[\s.:_-]+(\d+[a-zA-Z]?)", cleaned)
    if m_num:
        c = int(m_num.group(1))
        v_str = m_num.group(2)
        v = int(v_str) if v_str.isdigit() else v_str
        return f"Gen.{c}.{v}"

    # 2. Book chapter:verse or Book.chapter.verse
    m_full = re.fullmatch(
        r"([0-9A-Za-z\s]+?)[\s._-]+(\d+)[\s.:_-]+(\d+[a-zA-Z]?)",
        cleaned,
        re.IGNORECASE,
    )
    if m_full:
        book_str = m_full.group(1).strip()
        osis_b = resolve_osis_book(book_str)
        c = int(m_full.group(2))
        v_str = m_full.group(3)
        v = int(v_str) if v_str.isdigit() else v_str
        return f"{osis_b}.{c}.{v}"

    raise ValueError(f"Cannot parse verse reference from '{raw}'")


class MaculaDB:
    """Query engine backed by SQLite (data/macula.db) or JSON (lexicons/macula-genesis.json)."""

    def __init__(self, data_or_path: str | Path | dict | None = None):
        self._sqlite: MaculaSqliteDB | None = None
        self._data: dict | None = None

        if data_or_path is None:
            db_path = Path(DEFAULT_MACULA_DB)
            candidate = MaculaSqliteDB(db_path)
            if candidate.exists():
                self._sqlite = candidate
            else:
                candidate.close()
                data_or_path = DEFAULT_ARTIFACT_PATH

        if self._sqlite is None:
            if isinstance(data_or_path, (str, Path)) and str(data_or_path).endswith((".db", ".sqlite")):
                self._sqlite = MaculaSqliteDB(data_or_path)
            elif isinstance(data_or_path, dict):
                self._data = data_or_path
            else:
                p = Path(data_or_path)

                if not p.exists():
                    raise FileNotFoundError(
                        f"Macula artifact missing: {p}. "
                        "Run 'python -m search.macula.build_crosswalk' to generate it."
                    )
                with open(p, encoding="utf-8") as f:
                    self._data = json.load(f)

        if self._data is not None:
            self._crosswalk: dict[str, dict] = self._data.get("strongs_crosswalk", {})
            self._verses: dict[str, dict] = self._data.get("verses", {})

            # Build reverse index for Greek LXX Strong's
            self._greek_to_hebrew: dict[str, list[dict]] = {}
            # Build index for SDBH core domains
            self._domain_to_hebrew: dict[str, list[dict]] = {}

            for h_id, entry in self._crosswalk.items():
                for g_id, g_rec in entry.get("lxx", {}).items():
                    self._greek_to_hebrew.setdefault(g_id, []).append({
                        "hebrew_strongs": h_id,
                        "lemmas": entry.get("lemmas", []),
                        "glosses": entry.get("glosses", []),
                        "count": g_rec.get("count", 0),
                        "greek_forms": g_rec.get("greek", []),
                    })
                for cd in entry.get("core_domains", []):
                    self._domain_to_hebrew.setdefault(cd, []).append({
                        "hebrew_strongs": h_id,
                        "lemmas": entry.get("lemmas", []),
                        "glosses": entry.get("glosses", []),
                    })

            # Pre-sort each Greek index list once during initialization
            for entries in self._greek_to_hebrew.values():
                entries.sort(key=lambda x: x["count"], reverse=True)

    @property
    def is_sqlite(self) -> bool:
        return self._sqlite is not None

    @property
    def counts(self) -> dict[str, int]:
        if self._sqlite:
            return self._sqlite.counts
        return self._data.get("counts", {}) if self._data else {}

    def close(self) -> None:
        """Close backing SQLite connection if active."""
        if self._sqlite is not None:
            self._sqlite.close()

    def __enter__(self) -> MaculaDB:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def lookup_strongs(self, query: str) -> dict | None:
        """Look up Strong's entry (e.g. 'H7225', '7225', 'H430', 'G2316', 'G02316')."""
        q = query.strip().upper()
        if q.startswith("G"):
            norm = normalize_greek_strongs(q)
        else:
            norm = normalize_hebrew_strongs(q)
        if not norm:
            return None
        if self._sqlite:
            return self._sqlite.lookup_strongs(norm)
        return self._crosswalk.get(norm)

    def lookup_verse(self, query: str) -> dict | None:
        """Look up verse syntactic structure (e.g. 'Gen.1.1', 'GEN 1:1', '1:1')."""
        try:
            v_ref = normalize_verse_ref(query)
        except ValueError:
            return None
        if self._sqlite:
            return self._sqlite.lookup_verse(v_ref)
        return self._verses.get(v_ref)

    def lookup_lxx(self, query: str) -> list[dict]:
        """Reverse lookup: find Hebrew Strong's words translated by Greek LXX Strong's."""
        norm = normalize_greek_strongs(query)
        if not norm:
            return []
        if self._sqlite:
            return self._sqlite.lookup_lxx(norm)
        return self._greek_to_hebrew.get(norm, [])

    def search_by_domain(self, domain_code: str) -> list[dict]:
        """Find all Hebrew Strong's entries annotated with an SDBH core domain code."""
        code = domain_code.strip().zfill(3)
        if self._sqlite:
            return self._sqlite.search_by_domain(code)
        return self._domain_to_hebrew.get(code, [])

    def search_by_role(
        self,
        role: str,
        limit: int = 50,
        book_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search constituents by grammatical role (e.g. 'subj', 'pred', 'obj', 'adv')."""
        if self._sqlite:
            return self._sqlite.search_by_role(role, limit=limit, book_code=book_code)

        # In-memory JSON fallback
        target_roles = set(resolve_role_query(role))
        clean_book = book_code.strip().upper() if book_code else None
        results = []
        for v_id, v in self._verses.items():
            if clean_book and not v_id.upper().startswith(clean_book):
                continue
            for cl in v.get("clauses", []):
                for const in cl.get("constituents", []):
                    c_role = (const.get("role") or "").lower()
                    c_label = (const.get("role_label") or "").lower()
                    if c_role in target_roles or c_label in target_roles:
                        results.append({
                            "verse_id": v_id,
                            "role": const.get("role"),
                            "role_label": const.get("role_label"),
                            "class": const.get("class"),
                            "constituent_text": const.get("text"),
                            "clause_rule": cl.get("rule"),
                            "verse_text": v.get("text"),
                        })
                        if len(results) >= limit:
                            return results
        return results




_DEFAULT_DB: MaculaDB | None = None


def get_db(repo_root: str | Path = ".") -> MaculaDB:
    """Return singleton MaculaDB instance (prefers SQLite, falls back to JSON)."""
    global _DEFAULT_DB
    if _DEFAULT_DB is None:
        db_path = Path(repo_root) / DEFAULT_MACULA_DB
        if db_path.is_file():
            _DEFAULT_DB = MaculaDB(db_path)
        else:
            path = Path(repo_root) / DEFAULT_ARTIFACT_PATH
            _DEFAULT_DB = MaculaDB(path)
    return _DEFAULT_DB


def lookup_strongs(query: str, repo_root: str | Path = ".") -> dict | None:
    return get_db(repo_root).lookup_strongs(query)


def lookup_verse(query: str, repo_root: str | Path = ".") -> dict | None:
    return get_db(repo_root).lookup_verse(query)


def lookup_lxx(query: str, repo_root: str | Path = ".") -> list[dict]:
    return get_db(repo_root).lookup_lxx(query)


def search_by_domain(domain_code: str, repo_root: str | Path = ".") -> list[dict]:
    return get_db(repo_root).search_by_domain(domain_code)


def search_by_role(
    role: str,
    limit: int = 50,
    book_code: str | None = None,
    repo_root: str | Path = ".",
) -> list[dict]:
    return get_db(repo_root).search_by_role(role, limit=limit, book_code=book_code)
