"""Unified Bible study service.

Integrates whole-Bible Scripture (BibleDB), original language morphology & syntax
(MaculaSqliteDB), semantic participant frames, Strong's lexical definitions,
and Spirit of Prophecy commentary (EgwDB) into a cohesive study engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
import sqlite3
import threading
from typing import Any

from search.corpus.bible_books import BIBLE_BOOKS, parse_passage_ref, resolve_book_code
from search.corpus.extract_kjv import BibleDB, DEFAULT_BIBLE_DB
from search.macula.db import MaculaSqliteDB, DEFAULT_MACULA_DB
from search.macula.enrichment import (
    get_verse_semantic_frame,
    get_translation_equivalences,
    get_verse_semantic_frames_batch,
)
from search.linking.egw import EgwDB, DEFAULT_EGW_DB, is_egw_token, normalize_token

DEFAULT_STRONGS_LEXICON = Path("lexicons/strongs-lexicon.json")
DEFAULT_TBESH = Path("lexicons/tbesh-glosses.json")
DEFAULT_TBESG = Path("lexicons/tbesg-glosses.json")
EBOOK_METADATA_KEYWORDS = ("isbn", "ebook", "estate", "overview this")
PRIORITY_EGW_ORDER = ("PP", "PK", "DA", "MB", "COL", "AA", "GC", "SC", "ED", "MH", "SR")
PRIORITY_EGW_RANK = {code: i for i, code in enumerate(PRIORITY_EGW_ORDER)}



@dataclass
class VerseStudy:
    osis: str
    book_code: str
    chapter: int
    verse: int
    text: str
    tokens: list[dict[str, Any]] = field(default_factory=list)
    semantic_frames: list[dict[str, Any]] = field(default_factory=list)
    original_text: str = ""
    strongs_list: list[str] = field(default_factory=list)


@dataclass
class PassageStudy:
    ref: str
    book_code: str
    book_name: str
    start_chapter: int
    start_verse: int
    end_chapter: int
    end_verse: int
    verses: list[VerseStudy]
    egw_correlations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WordStudyResult:
    strongs_id: str
    language: str
    word: str
    translit: str
    definition: str
    gloss: str = ""
    lxx_equivalences: list[dict[str, Any]] = field(default_factory=list)
    occurrences_count: int = 0
    sample_verses: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class UnifiedSearchResult:
    query: str
    bible_hits: list[dict[str, Any]] = field(default_factory=list)
    egw_hits: list[dict[str, Any]] = field(default_factory=list)


class StudyService:
    """Consolidated study engine querying Scripture, Macula syntax, Lexicons, and EGW."""

    def __init__(
        self,
        bible_db_path: Path | str = DEFAULT_BIBLE_DB,
        macula_db_path: Path | str = DEFAULT_MACULA_DB,
        egw_db_path: Path | str = DEFAULT_EGW_DB,
        strongs_path: Path | str = DEFAULT_STRONGS_LEXICON,
        tbesh_path: Path | str | None = None,
        tbesg_path: Path | str | None = None,
    ) -> None:
        self.bible_db = BibleDB(bible_db_path) if Path(bible_db_path).exists() else None
        self.macula_db = MaculaSqliteDB(macula_db_path) if Path(macula_db_path).exists() else None
        self.egw_db = EgwDB(egw_db_path) if Path(egw_db_path).exists() else None
        self.strongs_path = Path(strongs_path)
        lex_dir = self.strongs_path.parent if self.strongs_path.parent.exists() else Path("lexicons")
        self.tbesh_path = Path(tbesh_path) if tbesh_path else (lex_dir / "tbesh-glosses.json")
        self.tbesg_path = Path(tbesg_path) if tbesg_path else (lex_dir / "tbesg-glosses.json")
        self._lexicon_cache: dict[str, Any] | None = None
        self._tbesh_cache: dict[str, str] | None = None
        self._tbesg_cache: dict[str, str] | None = None
        self._word_cache: dict[str, WordStudyResult] = {}
        self._verse_frame_cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def _load_lexicons(self) -> None:
        if self._lexicon_cache is None:
            if self.strongs_path.exists():
                with open(self.strongs_path, encoding="utf-8") as f:
                    self._lexicon_cache = json.load(f)
            else:
                self._lexicon_cache = {}

        def _load_gloss_file(path: Path) -> dict[str, str]:
            if not path.exists():
                return {}
            with open(path, encoding="utf-8") as f:
                raw_data = json.load(f)
                entries = raw_data.get("entries") or raw_data.get("glosses", {})
                return {
                    code: (items[0].get("gloss", "") if isinstance(items, list) and items else str(items))
                    for code, items in entries.items()
                }

        if self._tbesh_cache is None:
            self._tbesh_cache = _load_gloss_file(self.tbesh_path)

        if self._tbesg_cache is None:
            self._tbesg_cache = _load_gloss_file(self.tbesg_path)

    def get_passage_study(self, passage_ref: str, eager_frames: bool = True) -> PassageStudy:
        """Fetch complete multi-dimensional study for a passage reference."""
        with self._lock:
            book_code, ch, v1, v2 = parse_passage_ref(passage_ref)
            book_info = BIBLE_BOOKS.get(book_code)
            book_name = book_info.name if book_info else book_code

            # 1. Fetch Bible verses from BibleDB
            verses_raw = []
            if self.bible_db:
                verses_raw = self.bible_db.get_passage(passage_ref)

            s_ch = ch
            e_ch = ch
            s_v = v1 if v1 is not None else 1
            e_v = v2 if v2 is not None else (len(verses_raw) or 1)
            
            verse_studies: list[VerseStudy] = []
            all_strongs: set[str] = set()

            # Pre-fetch semantic frames for the whole chapter in a single batch query
            batch_frames: dict[str, dict[str, Any]] = {}
            if eager_frames and self.macula_db and verses_raw:
                v_refs = [f"{vr['osis']}.{vr['chapter']}.{vr['verse']}" for vr in verses_raw]
                try:
                    batch_frames = get_verse_semantic_frames_batch(v_refs, db=self.macula_db)
                    self._verse_frame_cache.update(batch_frames)
                except Exception:
                    batch_frames = {}

            for vr in verses_raw:
                verse_id = f"{vr['osis']}.{vr['chapter']}.{vr['verse']}"
                tokens = vr.get("tokens", [])
                strongs_in_v: list[str] = []
                for tok in tokens:
                    s_val = tok.get("strongs")
                    if isinstance(s_val, list):
                        strongs_in_v.extend(s_val)
                    elif isinstance(s_val, str) and s_val:
                        strongs_in_v.append(s_val)
                all_strongs.update(strongs_in_v)

                # 2. Extract Macula semantic frame & original language text
                frames: list[dict[str, Any]] = []
                orig_text = ""
                if verse_id in self._verse_frame_cache:
                    c_data = self._verse_frame_cache[verse_id]
                    frames = c_data.get("clauses", [])
                    orig_text = c_data.get("text", "")
                elif eager_frames and self.macula_db:
                    try:
                        frame_data = get_verse_semantic_frame(verse_id, db=self.macula_db)
                        if frame_data:
                            frames = frame_data.get("clauses", [])
                            orig_text = frame_data.get("text", "")
                            self._verse_frame_cache[verse_id] = frame_data
                    except Exception:
                        frames = []

                verse_studies.append(
                    VerseStudy(
                        osis=verse_id,
                        book_code=vr.get("osis", book_code),
                        chapter=vr["chapter"],
                        verse=vr["verse"],
                        text=vr.get("clean_text") or vr["text"],
                        tokens=tokens,
                        semantic_frames=frames,
                        original_text=orig_text,
                        strongs_list=strongs_in_v,
                    )
                )

            # 3. Correlated Spirit of Prophecy passages
            egw_correlations: list[dict[str, Any]] = []
            if self.egw_db:
                search_query = f'"{book_name} {s_ch}"'
                try:
                    hits = self.egw_db.search(search_query, limit=30)
                    candidate_hits: list[dict[str, Any]] = []
                    for h in hits:
                        b_code = h.get("book_code", "")
                        page_num = int(h.get("page") or 0)
                        hit_para = int(h.get("paragraph") or h.get("paragraph_num") or 0)
                        raw_text = (h.get("text", "") or h.get("snippet", "")).strip()

                        # Skip front matter eBook metadata (e.g. ISBN, Online Books overview)
                        if page_num <= 2 and any(meta in raw_text.lower() for meta in EBOOK_METADATA_KEYWORDS):
                            continue

                        candidate_hits.append(
                            {
                                "token": h.get("id") or h.get("canonical_token") or h.get("ref_code", ""),
                                "book_code": b_code,
                                "book_title": h.get("book_title", ""),
                                "chapter_title": h.get("chapter_title", ""),
                                "page": page_num,
                                "paragraph": hit_para,
                                "heading": h.get("chapter_title") or h.get("heading", ""),
                                "snippet": h.get("snippet", ""),
                                "text": raw_text,
                            }
                        )

                    # Prioritize canonical pages of primary Conflict of the Ages and commentary books
                    candidate_hits.sort(
                        key=lambda c: (
                            0 if (c["book_code"] in PRIORITY_EGW_RANK and c["page"] > 1) else (1 if c["book_code"] in PRIORITY_EGW_RANK else 2),
                            PRIORITY_EGW_RANK.get(c["book_code"], 999),
                            c["page"],
                            c["paragraph"],
                        )
                    )
                    top_hits = candidate_hits[:10]

                    # Expand introductory notes only for top hits to avoid N+1 DB queries
                    for item in top_hits:
                        raw_text = item["text"]
                        b_code = item["book_code"]
                        page_num = item["page"]
                        hit_para = item["paragraph"]

                        if (
                            page_num
                            and b_code
                            and (
                                hit_para <= 1
                                or len(raw_text) < 120
                                or any(k in raw_text.lower() for k in ("based on", "see egw", "vol."))
                            )
                        ):
                            page_paras = self.get_egw_page(b_code, page_num)
                            if page_paras:
                                subsequent = [
                                    p.get("text", "").strip()
                                    for p in page_paras
                                    if int(p.get("paragraph") or p.get("paragraph_num") or 0) > hit_para
                                    and p.get("text", "").strip()
                                    and not any(meta in p.get("text", "").lower() for meta in EBOOK_METADATA_KEYWORDS)
                                ][:4]
                                if subsequent:
                                    item["text"] = f"{raw_text}\n\n" + "\n\n".join(subsequent)

                    egw_correlations = top_hits
                except sqlite3.Error:
                    egw_correlations = []

            return PassageStudy(
                ref=passage_ref,
                book_code=book_code,
                book_name=book_name,
                start_chapter=s_ch,
                start_verse=s_v,
                end_chapter=e_ch,
                end_verse=e_v,
                verses=verse_studies,
                egw_correlations=egw_correlations,
            )

    def ensure_verse_frames(self, verse: VerseStudy) -> None:
        """Populate semantic frames and original language text on-demand if missing."""
        with self._lock:
            if verse.osis in self._verse_frame_cache:
                c_data = self._verse_frame_cache[verse.osis]
                verse.semantic_frames = c_data.get("clauses", [])
                verse.original_text = c_data.get("text", "")
                return
            if verse.semantic_frames and verse.original_text:
                return
            if not self.macula_db:
                return

            try:
                frame_data = get_verse_semantic_frame(verse.osis, db=self.macula_db) or {}
                verse.semantic_frames = frame_data.get("clauses", [])
                verse.original_text = frame_data.get("text", "")
                self._verse_frame_cache[verse.osis] = frame_data
            except Exception:
                self._verse_frame_cache[verse.osis] = {}

    def lookup_word(self, strongs_or_lemma: str, sample_limit: int = 5) -> WordStudyResult | None:
        """Fetch in-depth lexical study for a Strong's number with high-speed indexing."""
        with self._lock:
            self._load_lexicons()
            raw = strongs_or_lemma.strip().upper()
            
            # Normalize Strong's format
            if not (raw.startswith("H") or raw.startswith("G")):
                return None

            is_hebrew = raw.startswith("H")
            num_str = raw[1:].lstrip("0") or "0"
            canonical_id = f"{raw[0]}{num_str}"
            
            cache_key = f"{canonical_id}:{sample_limit}"
            if cache_key in self._word_cache:
                return self._word_cache[cache_key]

            lex_section = "hebrew" if is_hebrew else "greek"
            lex_dict = (self._lexicon_cache or {}).get(lex_section, {})
            entry = lex_dict.get(canonical_id)

            if not entry:
                return None

            word = entry.get("word", "")
            translit = entry.get("translit", "")
            definition = entry.get("desc", "")

            # Gloss
            gloss = ""
            if is_hebrew and self._tbesh_cache:
                gloss = self._tbesh_cache.get(canonical_id, "")
            elif not is_hebrew and self._tbesg_cache:
                gloss = self._tbesg_cache.get(canonical_id, "")

            # Septuagint translation equivalences (if Hebrew)
            lxx_equiv: list[dict[str, Any]] = []
            if is_hebrew and self.macula_db:
                try:
                    lxx_equiv = get_translation_equivalences(canonical_id, db=self.macula_db)
                except sqlite3.Error:
                    lxx_equiv = []

            # Bible occurrences count — prefer precomputed indexed count from macula.db
            occ_count = 0
            if self.macula_db:
                try:
                    cw = self.macula_db.lookup_strongs(canonical_id)
                    if cw and "occurrences" in cw:
                        occ_count = int(cw["occurrences"])
                except Exception:
                    occ_count = 0

            # Sample verses (only fetch if requested, avoiding table scans in TUI)
            sample_verses: list[dict[str, Any]] = []
            if sample_limit > 0 and self.bible_db:
                try:
                    sample_verses = self.bible_db.find_by_strongs(canonical_id, limit=sample_limit)
                    if occ_count == 0 and len(sample_verses) < sample_limit:
                        occ_count = len(sample_verses)
                except Exception:
                    sample_verses = []

            if occ_count == 0 and self.bible_db:
                try:
                    search_pat = f'%"{canonical_id}"%'
                    cur = self.bible_db.conn.execute(
                        "SELECT COUNT(*) FROM verses WHERE strongs_json LIKE ?;",
                        (search_pat,),
                    )
                    row = cur.fetchone()
                    occ_count = row[0] if row else len(sample_verses)
                except sqlite3.Error:
                    occ_count = len(sample_verses)

            res = WordStudyResult(
                strongs_id=canonical_id,
                language="Hebrew" if is_hebrew else "Greek",
                word=word,
                translit=translit,
                definition=definition,
                gloss=gloss,
                lxx_equivalences=lxx_equiv,
                occurrences_count=occ_count,
                sample_verses=sample_verses,
            )
            self._word_cache[cache_key] = res
            return res

    def search_unified(
        self,
        query: str,
        limit_bible: int = 10,
        limit_egw: int = 5,
        book_filter: str | None = None,
    ) -> UnifiedSearchResult:
        """Perform unified search across Scripture and Ellen G. White writings."""
        with self._lock:
            bible_hits = []
            if self.bible_db:
                try:
                    bible_hits = self.bible_db.search(query, limit=limit_bible, book=book_filter)
                except sqlite3.Error:
                    bible_hits = []

            egw_hits = []
            if self.egw_db:
                try:
                    raw_egw = self.egw_db.search(query, limit=limit_egw)
                    for h in raw_egw:
                        tok = h.get("id") or h.get("canonical_token") or h.get("ref_code", "")
                        egw_hits.append(
                            {
                                "token": tok,
                                "book_code": h.get("book_code", ""),
                                "book_title": h.get("book_title", ""),
                                "page": h.get("page", 0),
                                "paragraph": h.get("paragraph") or h.get("paragraph_num", 0),
                                "heading": h.get("chapter_title") or h.get("heading", ""),
                                "snippet": h.get("snippet", ""),
                            }
                        )
                except sqlite3.Error:
                    egw_hits = []

            return UnifiedSearchResult(query=query, bible_hits=bible_hits, egw_hits=egw_hits)

    def next_passage(self, passage: PassageStudy) -> str | None:
        """Compute the reference for the next chapter in the Bible."""
        from search.corpus.bible_books import BIBLE_BOOKS, CANONICAL_OSIS_ORDER
        book_info = BIBLE_BOOKS.get(passage.book_code)
        if not book_info:
            return None

        if passage.start_chapter < book_info.chapters:
            return f"{book_info.osis} {passage.start_chapter + 1}"

        # Advance to next book
        idx = next((i for i, osis in enumerate(CANONICAL_OSIS_ORDER) if osis == passage.book_code), None)
        if idx is not None and idx + 1 < len(CANONICAL_OSIS_ORDER):
            next_osis = CANONICAL_OSIS_ORDER[idx + 1]
            return f"{next_osis} 1"
        return None

    def prev_passage(self, passage: PassageStudy) -> str | None:
        """Compute the reference for the previous chapter in the Bible."""
        from search.corpus.bible_books import BIBLE_BOOKS, CANONICAL_OSIS_ORDER
        book_info = BIBLE_BOOKS.get(passage.book_code)
        if not book_info:
            return None

        if passage.start_chapter > 1:
            return f"{book_info.osis} {passage.start_chapter - 1}"

        # Go to previous book's last chapter
        idx = next((i for i, osis in enumerate(CANONICAL_OSIS_ORDER) if osis == passage.book_code), None)
        if idx is not None and idx > 0:
            prev_osis = CANONICAL_OSIS_ORDER[idx - 1]
            prev_info = BIBLE_BOOKS.get(prev_osis)
            if prev_info:
                return f"{prev_info.osis} {prev_info.chapters}"
        return None

    def lookup_egw_citation(self, token_or_query: str) -> dict[str, Any] | None:
        """Lookup an exact EGW paragraph citation (e.g. 'PP 44.1' or 'PP.44.1') or search query."""
        with self._lock:
            if not self.egw_db:
                return None
            from search.linking.egw import is_egw_token, normalize_token
            if is_egw_token(token_or_query):
                canonical_id, b_code, page, _ = normalize_token(token_or_query)
                p = self.egw_db.get_paragraph(canonical_id)
                page_paras = self.egw_db.get_page(b_code, page)
                if p:
                    p["page_paragraphs"] = page_paras
                    return p
                if page_paras:
                    first_p = page_paras[0]
                    first_p["page_paragraphs"] = page_paras
                    return first_p
                return None
            hits = self.egw_db.search(token_or_query, limit=1)
            if hits:
                h = hits[0]
                b_code = h.get("book_code", "")
                page = h.get("page", 0)
                if b_code and page:
                    h["page_paragraphs"] = self.egw_db.get_page(b_code, page)
                return h
            return None

    def get_egw_page(self, book_code: str, page: int) -> list[dict[str, Any]]:
        """Retrieve all paragraphs on a given EGW book page."""
        with self._lock:
            if not self.egw_db:
                return []
            return self.egw_db.get_page(book_code, page)

    def get_greek_gloss(self, greek_strongs: str) -> str:
        """Fetch concise English translation gloss for a Greek Strong's code (e.g. 'G4160' -> 'to do/make: do')."""
        with self._lock:
            self._load_lexicons()
            raw = greek_strongs.strip().upper()
            if not raw.startswith("G"):
                raw = f"G{raw}"
            num_str = raw[1:].lstrip("0") or "0"
            canonical_id = f"G{num_str}"
            if self._tbesg_cache and canonical_id in self._tbesg_cache:
                return self._tbesg_cache[canonical_id]
            ws = self.lookup_word(canonical_id, sample_limit=0)
            return ws.gloss if ws else ""


    def close(self) -> None:
        """Close database connections."""
        with self._lock:
            if self.bible_db is not None:
                self.bible_db.close()
            if self.macula_db is not None:
                self.macula_db.close()
            if self.egw_db is not None:
                self.egw_db.close()

    def __enter__(self) -> StudyService:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

