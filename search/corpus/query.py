"""Faceted/filtered querying over the curated corpus (roadmap C4).

``query(facets, text, limit)`` combines exact facet filtering
(book, theme, translation, language, status — and any tag category
defined in ``tags/taxonomy.json``) with free-text search, unified
across the verse (``data/bible.db``), paragraph (``data/egw.db``)
and curated entry (``materials/bible/**/*.md``) stores.

Sidecar-free by construction: the curated index is built in-memory
from markdown (the source of truth) and any source databases opened
for free-text use ``mode=ro&immutable=1`` (ADR-027 §5). No content
is generated or modified. Zero new dependencies (stdlib + PyYAML,
an existing declared dependency).

Design notes:
* Facets are enforced strictly -- a result must carry the facet
  value to be returned, so a ``theme`` filter over mixed sources
  naturally returns the curated entries only (bible/egw stores
  carry no theme/status tags).
* Two paths, decided by what the caller asks for:
  - ``text`` only -> free-text across all content stores (bible +
    egw + curated entries), ranked by BM25.
  - ``facets`` (with or without ``text``) -> scoped to the curated
    corpus; free-text, when present, is applied within it via FTS5.
* Ranking across the three different BM25 scales is Phase 2 work;
  per-source ranking is used within each path.
"""
from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from search.linking.loader import _parse_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[2]
MATERIALS_DIR = REPO_ROOT / "materials" / "bible"

# Where a facet's values live. Tags are stored verbatim (e.g. "book/genesis");
# ``status`` is a frontmatter key, so its value is stored without a prefix.
_FACET_PREFIX = {"book": "book/", "theme": "theme/", "translation": "translation/", "language": "lang/"}
_FACET_SCALAR = {"status"}


@lru_cache(maxsize=1)
def _build_index() -> sqlite3.Connection:
    """Build the in-memory curated index from markdown frontmatter."""
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute(
        """CREATE TABLE entries (
            id TEXT PRIMARY KEY,
            passage TEXT, body TEXT,
            book TEXT, language TEXT, translation TEXT, status TEXT
        )"""
    )
    con.execute("""CREATE TABLE entry_tags (
        entry_id TEXT, tag TEXT, PRIMARY KEY (entry_id, tag)
    )""")
    con.execute("CREATE VIRTUAL TABLE entries_fts USING fts5(passage, body)")
    for md in sorted(MATERIALS_DIR.rglob("*.md")):
        try:
            content = md.read_text(encoding="utf-8", errors="replace")
            fm, body = _parse_frontmatter(content)
        except Exception:
            continue
        if not fm or not fm.get("id"):
            continue
        tags = fm.get("tags") or []
        if isinstance(tags, dict):
            tags = []
        if not isinstance(tags, list):
            tags = [str(tags)]
        tags = [str(t) for t in tags]
        book = language = translation = status = None
        for k in ("book", "language", "translation"):
            v = fm.get(k)
            if isinstance(v, str) and v:
                if k == "book":
                    book = v
                elif k == "language":
                    language = v
                else:
                    translation = v
        v = fm.get("status")
        if isinstance(v, str) and v:
            status = v
        passage = str(fm.get("passage") or "")
        body_text = (body or "").strip()
        cur = con.execute(
            "INSERT INTO entries (id, passage, body, book, language, translation, status) VALUES (?,?,?,?,?,?,?)",
            (str(fm["id"]), passage, body_text, book, language, translation, status),
        )
        rid = cur.lastrowid
        con.execute("INSERT INTO entries_fts (rowid, passage, body) VALUES (?,?,?)", (rid, passage, body_text))
        for tag in tags:
            con.execute("INSERT OR IGNORE INTO entry_tags (entry_id, tag) VALUES (?,?)", (str(fm["id"]), tag))
    return con


def _clean_text(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text).strip()


def _query_materials(con: sqlite3.Connection, facets: dict[str, list[str]], text: str | None) -> list[dict[str, Any]]:
    """Curated-corpus query: facets + optional FTS5 text, all scoped to materials."""
    select_cols = [
        "e.id", "e.passage", "e.body", "e.book", "e.language", "e.translation",
        "e.status",
        "(SELECT group_concat(tag, ',') FROM entry_tags WHERE entry_id = e.id) AS tags",
        "e.rowid AS rid",
    ]
    if text:
        select_cols.append("bm25(entries_fts) AS rank")
    select = "SELECT " + ", ".join(select_cols)
    from_clause = "FROM entries e"
    where: list[str] = []
    params: list[Any] = []
    if text:
        from_clause += ", entries_fts"
        ct = _clean_text(text)
        if not ct:
            return []
        where.append("entries_fts.rowid = e.rowid")
        where.append("entries_fts MATCH ?")
        params.append(" ".join(f'"{w}"' for w in ct.split()))
    for facet, values in facets.items():
        if facet in _FACET_SCALAR:
            where.append(f"e.status IN ({','.join('?' * len(values))})")
            params.extend(v.split("/", 1)[1] if "/" in v else v for v in values)
        else:
            where.append(f"e.id IN (SELECT entry_id FROM entry_tags WHERE tag IN ({','.join('?' * len(values))}))")
            params.extend(values)
    sql = select + " " + from_clause
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY e.id LIMIT ?"
    params.append(10_000)
    return [dict(r) for r in con.execute(sql, params).fetchall()]


def _search_all_sources(
    con: sqlite3.Connection, facets: dict[str, list[str]], text: str | None, limit: int
) -> list[dict[str, Any]]:
    """Search all content stores (curated + bible + egw), merged by id.

    Facets scope to the curated corpus; free-text is searched across all
    stores. Bible results are additionally scoped by ``book``/``testament``
    facets where present (per plan: facets apply where structured data
    exists, absent never faked). EGW is searched by text only (no EGW book
    facet in the taxonomy). Cross-source ranking (Phase 3) converts
    SQLite FTS5 ``bm25`` (negative; more negative = more relevant) to
    positive relevance, normalizes per source to [0, 1], sorts globally;
    ``_norm`` is the internal relevance field (0-1; -1 unranked).
    """
    curated = _query_materials(con, facets, text or None)
    for r in curated:
        r["source"] = "entry"
    results: list[dict[str, Any]] = list(curated)

    ct = text.strip() if text else ""
    if not _clean_text(ct):
        return results[:limit]

    # Map facets to per-source params (book/testament -> BibleDB; rest curated).
    book = testament = None
    for facet, values in facets.items():
        if not values:
            continue
        value = values[0].split("/", 1)[1] if "/" in values[0] else values[0]
        if facet == "book":
            book = value
        elif facet == "testament":
            testament = value.upper()

    seen = {r["id"] for r in results}

    try:
        from search.corpus.extract_kjv import BibleDB

        for hit in BibleDB().search(ct, book=book, testament=testament):
            rid = hit.get("osis")
            if rid and rid not in seen:
                seen.add(rid)
                results.append(
                    {
                        "id": rid,
                        "passage": hit.get("osis"),
                        "body": hit.get("text") or hit.get("clean_text"),
                        "book": hit.get("book_name"),
                        "language": None,
                        "translation": None,
                        "status": None,
                        "tags": [],
                        "source": "bible",
                        "rank": hit.get("rank") or 0.0,
                    }
                )
    except sqlite3.Error:
        pass

    try:
        from search.linking.egw import EgwDB

        for hit in EgwDB().search(ct):
            rid = hit.get("id") or hit.get("canonical_id") or hit.get("token")
            if rid and rid not in seen:
                seen.add(rid)
                results.append(
                    {
                        "id": rid,
                        "passage": rid,
                        "body": hit.get("snippet") or hit.get("body"),
                        "book": hit.get("book_title"),
                        "language": "english",
                        "translation": None,
                        "status": None,
                        "tags": [],
                "source": "egw",
                "rank": hit.get("rank") or 0.0,
                    }
                )
    except sqlite3.Error:
        pass

    # Cross-source ranking (Phase 3): SQLite FTS5 bm25 returns
    # negative values where MORE NEGATIVE = MORE RELEVANT.
    # Convert to positive relevance (``-rank``), normalize per
    # source to [0, 1], then sort globally. Unranked results
    # (facet-only, or curated with no FTS5 content) sort last.
    # `_norm` is an internal relevance field (0-1; -1 unranked).
    source_max: dict[str, float] = {}
    for r in results:
        rank = r.get("rank")
        if isinstance(rank, (int, float)):
            s = r.get("source", "entry")
            rel = -rank
            source_max[s] = max(source_max.get(s, 0.0), rel)
    for r in results:
        rank = r.get("rank")
        mx = source_max.get(r.get("source", "entry"))
        if mx is None or not isinstance(rank, (int, float)):
            r["_norm"] = -1.0
        else:
            rel = -rank
            r["_norm"] = (rel / mx) if mx > 0 else 0.0
    results.sort(key=lambda r: r["_norm"], reverse=True)
    return results[:limit]


def query(
    facets: dict[str, list[str]] | None = None,
    text: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return entries matching ``facets`` and/or ``text``.

    Facets: dict of facet -> list of values; within a facet values
    are OR, across facets they AND/intersect. Pass ``text`` for
    free-text search (all content stores, cross-source ranked by
    normalized BM25) or ``None`` for facet-only. Facets always
    scope to the curated corpus; free-text is searched across
    curated + bible + EGW (Phase 2).
    """
    facets = facets or {}
    con = _build_index()
    return _search_all_sources(con, facets, text, limit)
