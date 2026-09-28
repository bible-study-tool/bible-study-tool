"""Deterministic Cross-Language & Unified Multi-Database Search Bridge (WP-039).

Unifies:
1. Scripture (KJV in data/bible.db `bible_fts`)
2. Parallel Translations (ASV, BSB, YLT in data/bible.db `translations_fts`)
3. Original Languages (Hebrew OT & Greek NT in data/macula.db and lexicons)
4. Spirit of Prophecy Commentary (data/egw.db `egw_fts`)
5. Curated Study Notes (materials/bible/**/*.md in-memory `entries_fts`)

Features:
- Zero ML / zero neural runtime downloads (ADR-013).
- Fine-grained search syntax parsing (`book:`, `testament:`, `translation:`, `strong:`, `domain:`, `egw:`, exact `"quotes"`, boolean operators).
- Passage reference detection for smart omnibox routing (L50).
- Deterministic query expansion across English <-> Strong's <-> Hebrew/Greek Lemmas <-> LXX crosswalk.
- BM25 score normalization across disparate databases to [0.0, 1.0].
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import html
import math
from pathlib import Path
import re
import sqlite3
from typing import Any, Optional, Sequence

from search.corpus.bible_books import (
    BIBLE_BOOKS,
    parse_passage_ref,
    resolve_book_code,
)
from search.corpus.extract_kjv import (
    BibleDB,
    clean_token_text,
    clean_verse_text,
    prepare_fts_query,
)
from search.corpus.query import _build_index as build_curated_index, _query_materials
from search.linking.egw import EgwDB
from search.macula.search import (
    MaculaLexicalHit,
    MaculaSearchEngine,
    normalize_strongs,
    strip_diacritics,
)

# Supported search source buckets
ALL_SOURCES = ("scripture", "translations", "original", "commentary", "curated")

# Regex operators for query parsing
_OP_BOOK_RE = re.compile(r"\b(?:book|b):(?:\s*\"([^\"]+)\"|(\S+))", re.IGNORECASE)
_OP_TESTAMENT_RE = re.compile(r"\b(?:testament|t):(?:\s*\"([^\"]+)\"|(\S+))", re.IGNORECASE)
_OP_TRANSLATION_RE = re.compile(r"\b(?:translation|tr):(?:\s*\"([^\"]+)\"|(\S+))", re.IGNORECASE)
_OP_STRONGS_RE = re.compile(r"\b(?:strong|strongs|s):(?:\s*\"([^\"]+)\"|(\S+))", re.IGNORECASE)
_OP_DOMAIN_RE = re.compile(r"\b(?:domain|d):(?:\s*\"([^\"]+)\"|(\S+))", re.IGNORECASE)
_OP_EGW_RE = re.compile(r"\b(?:egw|author):(?:\s*\"([^\"]+)\"|(\S+))", re.IGNORECASE)
_QUOTED_PHRASE_RE = re.compile(r'"([^"]+)"')


def normalize_bm25_score(rank: float) -> float:
    """Normalize SQLite FTS5 BM25 rank (negative float where lower is better) to [0.0, 1.0].

    Uses logistic sigmoid normalization: 1.0 / (1.0 + exp(rank / 4.0)).
    For rank = -12.0 -> 0.952
    For rank = -8.0  -> 0.880
    For rank = -4.0  -> 0.731
    For rank = 0.0   -> 0.500
    """
    try:
        # Clamp to avoid overflow
        clamped = max(-50.0, min(50.0, rank))
        return round(1.0 / (1.0 + math.exp(clamped / 4.0)), 4)
    except (OverflowError, ValueError):
        return 0.5


@dataclass
class ParsedQuery:
    """Structured representation of a parsed search query."""
    raw_query: str
    clean_text: str
    is_reference: bool = False
    reference_target: Optional[dict[str, Any]] = None
    book: Optional[str] = None
    testament: Optional[str] = None
    translation: Optional[str] = None
    strongs: Optional[str] = None
    domain: Optional[str] = None
    egw_book: Optional[str] = None
    exact_phrases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_search_query(raw_query: str) -> ParsedQuery:
    """Extract fine-grained search operators and detect scripture references."""
    raw = (raw_query or "").strip()
    if not raw:
        return ParsedQuery(raw_query="", clean_text="")

    extracted_book: Optional[str] = None
    extracted_testament: Optional[str] = None
    extracted_trans: Optional[str] = None
    extracted_strongs: Optional[str] = None
    extracted_domain: Optional[str] = None
    extracted_egw: Optional[str] = None

    working = raw

    # 1. Book operator
    m_book = _OP_BOOK_RE.search(working)
    if m_book:
        val = m_book.group(1) or m_book.group(2)
        try:
            extracted_book = resolve_book_code(val)
        except ValueError:
            extracted_book = val
        working = _OP_BOOK_RE.sub("", working)

    # 2. Testament operator
    m_test = _OP_TESTAMENT_RE.search(working)
    if m_test:
        val = (m_test.group(1) or m_test.group(2)).upper()
        if val in ("OT", "NT", "OLD", "NEW"):
            extracted_testament = "OT" if val in ("OT", "OLD") else "NT"
        working = _OP_TESTAMENT_RE.sub("", working)

    # 3. Translation operator
    m_trans = _OP_TRANSLATION_RE.search(working)
    if m_trans:
        extracted_trans = (m_trans.group(1) or m_trans.group(2)).lower()
        working = _OP_TRANSLATION_RE.sub("", working)

    # 4. Strong's operator
    m_str = _OP_STRONGS_RE.search(working)
    if m_str:
        val = m_str.group(1) or m_str.group(2)
        norm_s = normalize_strongs(val)
        extracted_strongs = norm_s or val.upper()
        working = _OP_STRONGS_RE.sub("", working)

    # 5. Semantic Domain operator
    m_dom = _OP_DOMAIN_RE.search(working)
    if m_dom:
        extracted_domain = m_dom.group(1) or m_dom.group(2)
        working = _OP_DOMAIN_RE.sub("", working)

    # 6. EGW book operator
    m_egw = _OP_EGW_RE.search(working)
    if m_egw:
        extracted_egw = (m_egw.group(1) or m_egw.group(2)).upper()
        working = _OP_EGW_RE.sub("", working)

    # Extract exact phrases
    exact_phrases = _QUOTED_PHRASE_RE.findall(working)

    # Clean text leftover
    clean_text = " ".join(working.split()).strip()

    # Check if the entire raw query or clean text is a passage reference (e.g. 'John 3:16', 'Gen 1:1-3')
    is_ref = False
    ref_target: Optional[dict[str, Any]] = None
    target_text = clean_text or raw
    if not (extracted_strongs or extracted_domain or extracted_egw):
        try:
            osis, ch, v1, v2 = parse_passage_ref(target_text)
            is_ref = True
            ref_target = {
                "osis": osis,
                "book_name": BIBLE_BOOKS[osis].name,
                "chapter": ch,
                "start_verse": v1,
                "end_verse": v2,
                "reference": f"{BIBLE_BOOKS[osis].name} {ch}:{v1}" + (f"-{v2}" if v2 and v2 != v1 else ""),
            }
        except Exception:
            is_ref = False
            ref_target = None

    # Check if clean text is an explicit Strong's code (e.g. 'H7225', 'G3056')
    if not extracted_strongs:
        direct_strongs = normalize_strongs(clean_text)
        if direct_strongs:
            extracted_strongs = direct_strongs

    return ParsedQuery(
        raw_query=raw,
        clean_text=clean_text,
        is_reference=is_ref,
        reference_target=ref_target,
        book=extracted_book,
        testament=extracted_testament,
        translation=extracted_trans,
        strongs=extracted_strongs,
        domain=extracted_domain,
        egw_book=extracted_egw,
        exact_phrases=exact_phrases,
    )


@dataclass
class SearchHit:
    """A unified result hit across any of the 5 library stores."""
    source: str          # 'scripture' | 'translations' | 'original' | 'commentary' | 'curated'
    id: str              # e.g. 'Gen.1.1', 'asv:Gen.1.1', 'H7225', 'DA.680.2'
    reference: str       # e.g. 'Genesis 1:1', 'H7225', 'The Desire of Ages p. 680.2'
    title: str           # Display heading
    snippet: str         # Formatted context snippet
    score: float         # 0.0 to 1.0 normalized ranking score
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DeterministicSearchBridge:
    """Unified deterministic multi-database search bridge and query expander."""

    def __init__(
        self,
        bible_db: Optional[BibleDB] = None,
        macula_engine: Optional[MaculaSearchEngine] = None,
        egw_db: Optional[EgwDB] = None,
    ):
        self._bible_db = bible_db
        self._macula_engine = macula_engine
        self._egw_db = egw_db
        self._curated_con: Optional[sqlite3.Connection] = None

    @property
    def bible_db(self) -> BibleDB:
        if self._bible_db is None:
            self._bible_db = BibleDB()
        return self._bible_db

    @property
    def macula_engine(self) -> MaculaSearchEngine:
        if self._macula_engine is None:
            self._macula_engine = MaculaSearchEngine()
        return self._macula_engine

    @property
    def egw_db(self) -> EgwDB:
        if self._egw_db is None:
            self._egw_db = EgwDB()
        return self._egw_db

    @property
    def curated_con(self) -> sqlite3.Connection:
        if self._curated_con is None:
            self._curated_con = build_curated_index()
        return self._curated_con

    def close(self) -> None:
        if self._bible_db is not None:
            self._bible_db.close()
            self._bible_db = None
        if self._macula_engine is not None:
            self._macula_engine.close()
            self._macula_engine = None
        if self._egw_db is not None:
            self._egw_db.close()
            self._egw_db = None
        self._curated_con = None

    def __enter__(self) -> DeterministicSearchBridge:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def expand_query(self, term: str) -> dict[str, Any]:
        """Perform bidirectional lexical expansion for an English keyword or Strong's code.

        Links:
        English Keyword <-> Strong's Number <-> Hebrew/Greek Lemma <-> Transliteration <-> LXX Crosswalk.
        """
        clean = (term or "").strip()
        if not clean:
            return {"term": "", "strongs": [], "lemmas": [], "lxx_aligned": []}

        expansion: dict[str, Any] = {
            "term": clean,
            "strongs": [],
            "lemmas": [],
            "lxx_aligned": [],
        }

        try:
            hits = self.macula_engine.search(clean, limit=6)
        except Exception:
            return expansion

        seen_strongs: set[str] = set()
        seen_lemmas: set[str] = set()

        for h in hits:
            if h.strongs and h.strongs not in seen_strongs:
                seen_strongs.add(h.strongs)
                expansion["strongs"].append(h.strongs)

            lemma_key = f"{h.lemma}:{h.translit}"
            if h.lemma and lemma_key not in seen_lemmas:
                seen_lemmas.add(lemma_key)
                expansion["lemmas"].append({
                    "strongs": h.strongs,
                    "language": h.language,
                    "lemma": h.lemma,
                    "translit": h.translit,
                    "gloss": h.glosses[0] if h.glosses else "",
                    "occurrences": h.occurrences,
                })

            if h.lxx_crosswalk:
                for lxx_code in sorted(
                    h.lxx_crosswalk.keys(),
                    key=lambda k: h.lxx_crosswalk[k].get("count", 0) if isinstance(h.lxx_crosswalk[k], dict) else (h.lxx_crosswalk[k] if isinstance(h.lxx_crosswalk[k], int) else 0),
                    reverse=True,
                )[:2]:
                    if lxx_code not in expansion["lxx_aligned"]:
                        expansion["lxx_aligned"].append(lxx_code)

        return expansion

    def _search_scripture(
        self,
        parsed: ParsedQuery,
        limit: int = 50,
    ) -> list[SearchHit]:
        """Search KJV Scripture in data/bible.db."""
        if not self.bible_db.exists():
            return []
        if parsed.translation and parsed.translation not in ("all", "*", "kjv"):
            return []

        try:
            if not parsed.clean_text and parsed.strongs:
                verses = self.bible_db.find_by_strongs(parsed.strongs, limit=limit)
                if parsed.book:
                    verses = [v for v in verses if v.get("osis") == parsed.book]
                elif parsed.testament:
                    verses = [v for v in verses if v.get("testament") == parsed.testament]
            elif parsed.clean_text:
                verses = self.bible_db.search(
                    query=parsed.clean_text,
                    limit=limit,
                    book=parsed.book,
                    testament=parsed.testament,
                    translation="kjv",
                )
            else:
                return []
        except Exception:
            return []

        hits: list[SearchHit] = []
        for v in verses:
            osis = v.get("osis", "")
            ch = v.get("chapter", 1)
            vs = v.get("verse", 1)
            book_name = v.get("book_name") or (BIBLE_BOOKS[osis].name if osis in BIBLE_BOOKS else osis)
            ref_str = f"{book_name} {ch}:{vs}"
            raw_text = v.get("text", "")
            clean_txt = clean_verse_text(raw_text)

            rank = float(v.get("rank", 0.0))
            score = normalize_bm25_score(rank)

            hits.append(SearchHit(
                source="scripture",
                id=v.get("id") or f"{osis}.{ch}.{vs}",
                reference=ref_str,
                title=f"{ref_str} (KJV)",
                snippet=clean_txt,
                score=score,
                metadata={
                    "osis": osis,
                    "book_name": book_name,
                    "chapter": ch,
                    "verse": vs,
                    "translation": "kjv",
                    "strongs": v.get("strongs", []),
                    "testament": v.get("testament", ""),
                },
            ))
        return hits

    def _search_translations(
        self,
        parsed: ParsedQuery,
        limit: int = 50,
    ) -> list[SearchHit]:
        """Search parallel translations (ASV, BSB, YLT) in data/bible.db."""
        if not self.bible_db.exists() or not parsed.clean_text:
            return []

        target_trans: Optional[str | list[str]] = parsed.translation
        if target_trans == "kjv":
            return []
        if not target_trans or target_trans in ("all", "*"):
            target_trans = ["asv", "bsb", "ylt"]

        try:
            verses = self.bible_db.search(
                query=parsed.clean_text,
                limit=limit,
                book=parsed.book,
                testament=parsed.testament,
                translation=target_trans,
            )
        except Exception:
            return []

        hits: list[SearchHit] = []
        for v in verses:
            t_id = (v.get("translation_id") or "asv").lower()
            if t_id == "kjv":
                continue
            t_name = v.get("translation_name") or t_id.upper()
            osis = v.get("osis", "")
            ch = v.get("chapter", 1)
            vs = v.get("verse", 1)
            book_name = v.get("book_name") or (BIBLE_BOOKS[osis].name if osis in BIBLE_BOOKS else osis)
            ref_str = f"{book_name} {ch}:{vs}"
            raw_text = v.get("text", "")
            clean_txt = clean_verse_text(raw_text)

            rank = float(v.get("rank", 0.0))
            score = normalize_bm25_score(rank)

            hits.append(SearchHit(
                source="translations",
                id=f"{t_id}:{osis}.{ch}.{vs}",
                reference=ref_str,
                title=f"{ref_str} ({t_name})",
                snippet=clean_txt,
                score=score,
                metadata={
                    "osis": osis,
                    "book_name": book_name,
                    "chapter": ch,
                    "verse": vs,
                    "translation_id": t_id,
                    "translation_name": t_name,
                    "testament": v.get("testament", ""),
                },
            ))
        return hits

    def _search_original(
        self,
        parsed: ParsedQuery,
        limit: int = 20,
    ) -> list[SearchHit]:
        """Search Hebrew/Greek lemmas, Strong's entries, and semantic domains in data/macula.db."""
        hits: list[SearchHit] = []

        try:
            # 1. Exact domain search if specified
            if parsed.domain:
                macula_hits = self.macula_engine.search_domain(parsed.domain, limit=limit)
            # 2. Exact Strong's search if specified
            elif parsed.strongs:
                hit_item = self.macula_engine.search_strongs(parsed.strongs)
                macula_hits = [hit_item] if hit_item else []
            # 3. Text query
            elif parsed.clean_text:
                macula_hits = self.macula_engine.search(parsed.clean_text, limit=limit)
            else:
                macula_hits = []
        except Exception:
            return []

        for mh in macula_hits:
            lang_label = "Hebrew" if mh.language == "hebrew" else "Greek"
            gloss_str = ", ".join(mh.glosses[:3]) if mh.glosses else mh.definition[:60]
            title = f"{mh.strongs} • {mh.lemma} ({mh.translit})" if mh.translit else f"{mh.strongs} • {mh.lemma}"
            snippet = f"{lang_label} • Glosses: {gloss_str} • {mh.occurrences} occurrences in scripture"
            if mh.definition:
                snippet += f" — {mh.definition[:140]}..."

            hits.append(SearchHit(
                source="original",
                id=mh.strongs,
                reference=mh.strongs,
                title=title,
                snippet=snippet,
                score=round(mh.score, 4),
                metadata={
                    "strongs": mh.strongs,
                    "language": mh.language,
                    "lemma": mh.lemma,
                    "translit": mh.translit,
                    "glosses": mh.glosses,
                    "occurrences": mh.occurrences,
                    "domains": mh.domains,
                    "lxx_crosswalk": mh.lxx_crosswalk,
                    "sample_verses": mh.sample_verses,
                },
            ))
        return hits

    def _search_commentary(
        self,
        parsed: ParsedQuery,
        limit: int = 50,
    ) -> list[SearchHit]:
        """Search Spirit of Prophecy (EGW) paragraphs in data/egw.db."""
        if not self.egw_db.exists() or not parsed.clean_text:
            return []

        try:
            paras = self.egw_db.search(
                query=parsed.clean_text,
                book_code=parsed.egw_book,
                limit=limit,
            )
        except Exception:
            return []

        hits: list[SearchHit] = []
        for p in paras:
            b_code = p.get("book_code", "")
            title = p.get("book_title") or b_code
            page = p.get("page", 1)
            para = p.get("paragraph", 1)
            ref_str = f"{title} p. {page}.{para}"
            snippet_text = p.get("snippet") or p.get("text", "")[:180]

            rank = float(p.get("rank", 0.0))
            score = normalize_bm25_score(rank)

            hits.append(SearchHit(
                source="commentary",
                id=p.get("id") or f"{b_code}.{page}.{para}",
                reference=f"{b_code} {page}.{para}",
                title=ref_str,
                snippet=snippet_text,
                score=score,
                metadata={
                    "book_code": b_code,
                    "book_title": title,
                    "chapter_num": p.get("chapter_num"),
                    "chapter_title": p.get("chapter_title"),
                    "page": page,
                    "paragraph": para,
                },
            ))
        return hits

    def _search_curated(
        self,
        parsed: ParsedQuery,
        limit: int = 20,
    ) -> list[SearchHit]:
        """Search curated study notes in materials/bible/ via in-memory FTS5."""
        if not parsed.clean_text:
            return []

        try:
            facets: dict[str, list[str]] = {}
            if parsed.book:
                book_tags = [f"book/{parsed.book.lower()}"]
                if parsed.book in BIBLE_BOOKS:
                    canonical_slug = BIBLE_BOOKS[parsed.book].name.lower().replace(" ", "-")
                    book_tags.append(f"book/{canonical_slug}")
                facets["book"] = book_tags
            entries = _query_materials(self.curated_con, facets, parsed.clean_text)
        except Exception:
            return []

        hits: list[SearchHit] = []
        for e in entries[:limit]:
            passage = e.get("passage") or "Curated Note"
            entry_id = e.get("id", "")
            body = e.get("body", "")
            # Extract first substantive paragraph for snippet
            paras = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith("#")]
            snippet = paras[0][:200] + "..." if paras else body[:200]

            rank = float(e.get("rank", 0.0))
            score = normalize_bm25_score(rank)

            hits.append(SearchHit(
                source="curated",
                id=entry_id,
                reference=passage,
                title=f"{passage} Study Note",
                snippet=snippet,
                score=score,
                metadata={
                    "entry_id": entry_id,
                    "passage": passage,
                    "tags": (e.get("tags") or "").split(","),
                    "status": e.get("status", ""),
                },
            ))
        return hits

    def search(
        self,
        query: str,
        sources: Sequence[str] | str = "all",
        limit: int = 50,
        book: Optional[str] = None,
        testament: Optional[str] = None,
        translation: Optional[str] = None,
        strongs: Optional[str] = None,
        domain: Optional[str] = None,
        egw_book: Optional[str] = None,
        expand: bool = True,
    ) -> dict[str, Any]:
        """Execute a unified deterministic multi-database search.

        Args:
            query: The user query string (may contain operators like `book:Gen` or `"quoted phrase"`).
            sources: List of sources to search ('scripture', 'translations', 'original', 'commentary', 'curated') or 'all'.
            limit: Maximum number of merged results to return.
            book: Optional explicit book filter (overridden if present in query string).
            testament: Optional explicit testament filter ('OT' or 'NT').
            translation: Optional translation filter ('kjv', 'asv', 'bsb', 'ylt', or 'all').
            strongs: Optional explicit Strong's filter.
            domain: Optional explicit semantic domain filter.
            egw_book: Optional explicit EGW book abbreviation.
            expand: Whether to compute bidirectional query expansion.

        Returns:
            Structured search results dictionary with categorized counts, expansion, and unified hits.
        """
        parsed = parse_search_query(query)

        # Apply explicit argument fallbacks if not parsed from query text
        if not parsed.book and book:
            try:
                parsed.book = resolve_book_code(book)
            except ValueError:
                parsed.book = book
        if not parsed.testament and testament:
            t_clean = testament.strip().upper()
            if t_clean in ("OT", "NT"):
                parsed.testament = t_clean
        if not parsed.translation and translation:
            parsed.translation = translation.strip().lower()
        if not parsed.strongs and strongs:
            parsed.strongs = normalize_strongs(strongs) or strongs.upper()
        if not parsed.domain and domain:
            parsed.domain = domain.strip()
        if not parsed.egw_book and egw_book:
            parsed.egw_book = egw_book.strip().upper()

        # Determine target sources
        active_sources: set[str] = set()
        if isinstance(sources, str):
            s_clean = sources.strip().lower()
            if s_clean in ("all", "*"):
                active_sources = set(ALL_SOURCES)
            elif s_clean in ALL_SOURCES:
                active_sources = {s_clean}
            else:
                active_sources = set(ALL_SOURCES)
        else:
            targets = {str(s).strip().lower() for s in sources}
            if "all" in targets:
                active_sources = set(ALL_SOURCES)
            else:
                active_sources = targets.intersection(ALL_SOURCES) or set(ALL_SOURCES)

        # Perform bidirectional lexical expansion if requested
        expansion_data: dict[str, Any] = {}
        if expand and (parsed.clean_text or parsed.strongs):
            term_to_expand = parsed.strongs or parsed.clean_text
            expansion_data = self.expand_query(term_to_expand)

        # Execute searches across active sources
        grouped_hits: dict[str, list[SearchHit]] = {src: [] for src in ALL_SOURCES}

        if "scripture" in active_sources:
            grouped_hits["scripture"] = self._search_scripture(parsed, limit=limit)

        if "translations" in active_sources:
            grouped_hits["translations"] = self._search_translations(parsed, limit=limit)

        if "original" in active_sources:
            grouped_hits["original"] = self._search_original(parsed, limit=limit)

        if "commentary" in active_sources:
            grouped_hits["commentary"] = self._search_commentary(parsed, limit=limit)

        if "curated" in active_sources:
            grouped_hits["curated"] = self._search_curated(parsed, limit=limit)

        # Merge and rank hits globally by normalized score
        all_merged: list[SearchHit] = []
        for src, hits in grouped_hits.items():
            all_merged.extend(hits)

        # Sort by score descending (higher relevance first)
        all_merged.sort(key=lambda h: h.score, reverse=True)

        counts = {
            "all": len(all_merged),
            "scripture": len(grouped_hits["scripture"]),
            "translations": len(grouped_hits["translations"]),
            "original": len(grouped_hits["original"]),
            "commentary": len(grouped_hits["commentary"]),
            "curated": len(grouped_hits["curated"]),
        }

        return {
            "query": query,
            "parsed": parsed.to_dict(),
            "is_reference": parsed.is_reference,
            "reference_target": parsed.reference_target,
            "expansion": expansion_data,
            "total_hits": len(all_merged),
            "counts": counts,
            "results": [h.to_dict() for h in all_merged[:limit]],
        }
