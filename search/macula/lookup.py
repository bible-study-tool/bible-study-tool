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

from search.macula.extract import normalize_hebrew_strongs, normalize_greek_strongs

DEFAULT_ARTIFACT_PATH = "lexicons/macula-genesis.json"


def normalize_verse_ref(raw: str) -> str:
    """Normalize user input to canonical 'Gen.c.v' format.

    Accepts:
      - 'Gen.1.1'
      - 'GEN 1:1' or 'gen 1:1'
      - '1:1' or '1.1'
      - 'gen-1-1' or 'gen-1-1-kjv'
      - 'Genesis 1:1'
    """
    cleaned = raw.strip()
    # Remove file extension or trailing qualifiers
    cleaned = re.sub(r"\.md$", "", cleaned)
    cleaned = re.sub(r"-kjv$", "", cleaned)

    # Match book, chapter, verse (anchored to entire string)
    m = re.fullmatch(r"(?:Gen(?:esis)?[\s._-]*)?(\d+)[\s.:_-]+(\d+)", cleaned, re.IGNORECASE)
    if m:
        c, v = int(m.group(1)), int(m.group(2))
        return f"Gen.{c}.{v}"
    raise ValueError(f"Cannot parse Genesis verse reference from '{raw}'")


class MaculaDB:
    """Query engine backed by lexicons/macula-genesis.json."""

    def __init__(self, data_or_path: str | Path | dict | None = None):
        if data_or_path is None:
            data_or_path = DEFAULT_ARTIFACT_PATH

        if isinstance(data_or_path, dict):
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
    def counts(self) -> dict[str, int]:
        return self._data.get("counts", {})

    def lookup_strongs(self, query: str) -> dict | None:
        """Look up Hebrew Strong's entry (e.g. 'H7225', '7225', '0722', 'H430')."""
        norm = normalize_hebrew_strongs(query)
        if not norm:
            return None
        return self._crosswalk.get(norm)

    def lookup_verse(self, query: str) -> dict | None:
        """Look up verse syntactic structure (e.g. 'Gen.1.1', 'GEN 1:1', '1:1')."""
        try:
            v_ref = normalize_verse_ref(query)
        except ValueError:
            return None
        return self._verses.get(v_ref)

    def lookup_lxx(self, query: str) -> list[dict]:
        """Reverse lookup: find Hebrew Strong's words translated by Greek LXX Strong's."""
        norm = normalize_greek_strongs(query)
        if not norm:
            return []
        return self._greek_to_hebrew.get(norm, [])

    def search_by_domain(self, domain_code: str) -> list[dict]:
        """Find all Hebrew Strong's entries annotated with an SDBH core domain code."""
        code = domain_code.strip().zfill(3)
        return self._domain_to_hebrew.get(code, [])


_DEFAULT_DB: MaculaDB | None = None


def get_db(repo_root: str | Path = ".") -> MaculaDB:
    """Return singleton MaculaDB instance."""
    global _DEFAULT_DB
    if _DEFAULT_DB is None:
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
