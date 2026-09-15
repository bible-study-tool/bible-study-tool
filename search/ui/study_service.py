"""Unified Bible study service.

Integrates whole-Bible Scripture (BibleDB), original language morphology & syntax
(MaculaSqliteDB), semantic participant frames, Strong's lexical definitions,
and Spirit of Prophecy commentary (EgwDB) into a cohesive study engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil
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
from search.corpus.grammar_nuance import (
    GrammarNuance,
    explain_verb,
    get_verse_grammar_nuances,
    get_verses_grammar_nuances_batch,
)
from search.corpus.discourse_flow import (
    DiscourseMarker,
    ArgumentFlowStep,
    extract_passage_discourse_batch,
    extract_verse_discourse_markers,
    analyze_passage_argument_flow,
)
from search.corpus.ot_citations import (
    OTCitation,
    lookup_citations_for_verse,
    get_passage_ot_citations_batch,
)
from search.corpus.prophetic import (
    AnnotatedPropheticSymbol,
    PropheticLexicon,
    PropheticSymbol,
    get_prophetic_lexicon,
)
from search.corpus.sanctuary import (
    AnnotatedSanctuaryStation,
    SanctuaryEngine,
    get_sanctuary_engine,
)
from search.linking.egw import EgwDB, DEFAULT_EGW_DB, is_egw_token, normalize_token
from search.resource import data_path, get_lexicons_dir, lexicon_path

from rich.markup import escape

DEFAULT_STRONGS_LEXICON = Path("lexicons/strongs-lexicon.json")
DEFAULT_TBESH = Path("lexicons/tbesh-glosses.json")
DEFAULT_TBESG = Path("lexicons/tbesg-glosses.json")
EBOOK_METADATA_KEYWORDS = ("isbn", "ebook", "estate", "overview this")
PRIORITY_EGW_ORDER = ("PP", "PK", "DA", "MB", "COL", "AA", "GC", "SC", "ED", "MH", "SR")
PRIORITY_EGW_RANK = {code: i for i, code in enumerate(PRIORITY_EGW_ORDER)}


import html


def clean_lexicon_definition(raw_html: str) -> str:
    """Format and beautify raw lexicon HTML (TBESH/TBESG) into readable terminal text with Rich markup."""
    if not raw_html:
        return ""
    # Decode HTML entities (e.g. &gt; -> >)
    t = html.unescape(raw_html)
    # Normalize HTML line breaks
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.IGNORECASE)
    # Strip <re> and </re>
    t = re.sub(r"</?re>", "", t, flags=re.IGNORECASE)

    # Stash structured elements into unique placeholders, defensively stripping inner HTML tags
    refs: list[str] = []
    def _save_ref(m: re.Match) -> str:
        clean_inner = re.sub(r"<[^>]+>", "", m.group(1))
        refs.append(clean_inner)
        return f"__LEX_REF_{len(refs)-1}__"
    t = re.sub(r"<ref=[\x27\"][^\x27\"]*[\x27\"]>(.*?)</ref>", _save_ref, t, flags=re.IGNORECASE)

    bolds: list[str] = []
    def _save_bold(m: re.Match) -> str:
        clean_inner = re.sub(r"<[^>]+>", "", m.group(1))
        bolds.append(clean_inner)
        return f"__LEX_BOLD_{len(bolds)-1}__"
    t = re.sub(r"<b>(.*?)</b>", _save_bold, t, flags=re.IGNORECASE)

    italics: list[str] = []
    def _save_italic(m: re.Match) -> str:
        clean_inner = re.sub(r"<[^>]+>", "", m.group(1))
        italics.append(clean_inner)
        return f"__LEX_ITALIC_{len(italics)-1}__"
    t = re.sub(r"<i>(.*?)</i>", _save_italic, t, flags=re.IGNORECASE)

    # Strip remaining arbitrary HTML tags
    t = re.sub(r"<[^>]+>", "", t)

    # Safely escape all literal markup characters (brackets, backslashes) in the outer text
    t = escape(t)

    # Re-inject sanitized markup tags
    for idx, b in enumerate(bolds):
        t = t.replace(f"__LEX_BOLD_{idx}__", f"[bold]{escape(b)}[/bold]")
    for idx, it in enumerate(italics):
        t = t.replace(f"__LEX_ITALIC_{idx}__", f"[italic]{escape(it)}[/italic]")
    for idx, r in enumerate(refs):
        t = t.replace(f"__LEX_REF_{idx}__", f"[dim]{escape(r)}[/dim]")

    cleaned_lines = []
    for raw_line in t.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Abbott-Smith Roman/Arabic outline markers (__I., __1., __(a))
        m_as = re.match(r"^__([IVXLCDM]+\.|[0-9]+\.|\([a-z0-9]+\))\s*(.*)", line)
        if m_as:
            tag, rest = m_as.groups()
            indent = "    " if len(tag) > 3 else "  "
            cleaned_lines.append(f"{indent}[bold yellow]{tag}[/bold yellow] {rest}")
            continue
        # BDB outline sub-senses (1a), 1a1))
        m_sub = re.match(r"^([0-9]+[a-z][0-9]*\))\s*(.*)", line)
        if m_sub:
            tag, rest = m_sub.groups()
            indent = "    " if len(tag) > 3 else "  "
            cleaned_lines.append(f"{indent}[bold yellow]{tag}[/bold yellow] {rest}")
            continue
        # BDB outline main senses (1), 2))
        m_main = re.match(r"^([0-9]+\))\s*(.*)", line)
        if m_main:
            tag, rest = m_main.groups()
            cleaned_lines.append(f"[bold cyan]{tag}[/bold cyan] {rest}")
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def format_scholarly_entries(items: list[dict[str, Any]], source_name: str = "") -> str:
    """Format single or multi-sense lexicon entries into a cohesive readable card."""
    if not items:
        return ""
    if len(items) == 1:
        return clean_lexicon_definition(items[0].get("definition", ""))

    sections = []
    for idx, it in enumerate(items, 1):
        estrong = it.get("estrong", "")
        gloss = it.get("gloss", "")
        raw_def = it.get("definition", "")
        if not raw_def:
            continue
        defn = clean_lexicon_definition(raw_def)
        sub_hdr = f"[bold cyan]Sense {idx}[/bold cyan]"
        if estrong or gloss:
            sub_hdr += f" [dim]({escape(estrong)} — \"{escape(gloss)}\")[/dim]"
        sections.append(f"{sub_hdr}:\n{defn}")
    return "\n\n".join(sections)


def parse_strongs_desc(desc: str) -> dict[str, Any]:
    """Parse raw Strong's lexicon desc field into numbered senses, KJV renderings, etymology, and roots."""
    lines = [l.strip() for l in desc.splitlines() if l.strip()]
    senses: list[str] = []
    kjv_renderings = ""
    etymology = ""
    roots = ""

    for l in lines:
        if l.startswith("Strong's Number"):
            continue
        m_sense = re.match(r"^([0-9]+\.\s+.*)", l)
        if m_sense:
            senses.append(m_sense.group(1))
            continue
        m_kjv = re.match(r"^KJV:\s*(.*)", l, re.IGNORECASE)
        if m_kjv:
            kjv_renderings = m_kjv.group(1)
            continue
        m_root = re.match(r"^Root\(s\):\s*(.*)", l, re.IGNORECASE)
        if m_root:
            roots = m_root.group(1)
            continue
        m_etym = re.match(r"^\[(.*)\]", l)
        if m_etym:
            etymology = m_etym.group(1)
            continue
        if not (l.startswith("Compare:") or l.startswith("See also:")):
            senses.append(l)

    return {
        "senses": senses,
        "kjv": kjv_renderings,
        "etymology": etymology,
        "roots": roots,
    }


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
    verbal_nuances: list[GrammarNuance] = field(default_factory=list)
    translations: dict[str, str] = field(default_factory=dict)
    discourse_markers: list[DiscourseMarker] = field(default_factory=list)
    ot_citations: list[OTCitation] = field(default_factory=list)
    prophetic_symbols: list[AnnotatedPropheticSymbol] = field(default_factory=list)
    sanctuary_stations: list[AnnotatedSanctuaryStation] = field(default_factory=list)



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
    argument_flow: list[ArgumentFlowStep] = field(default_factory=list)
    prev_ref: str | None = None
    next_ref: str | None = None


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
    scholarly_definition: str = ""
    source_lexicon: str = ""
    strongs_senses: list[str] = field(default_factory=list)
    kjv_renderings: str = ""
    etymology: str = ""


@dataclass
class UnifiedSearchResult:
    query: str
    bible_hits: list[dict[str, Any]] = field(default_factory=list)
    egw_hits: list[dict[str, Any]] = field(default_factory=list)


def _canonical_strongs(code: str) -> str:
    """Normalize a Strong's number to its canonical uppercase prefix-trimmed form."""
    if not code:
        return ""
    norm = code.strip().upper()
    return norm[0] + norm[1:].lstrip("0") if len(norm) > 1 else norm


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
        b_path = Path(bible_db_path)
        if not b_path.exists():
            b_path = data_path(bible_db_path)
        self.bible_db = BibleDB(b_path) if b_path.exists() else None

        m_path = Path(macula_db_path)
        if not m_path.exists():
            m_path = data_path(macula_db_path)
        self.macula_db = MaculaSqliteDB(m_path) if m_path.exists() else None

        e_path = Path(egw_db_path)
        if not e_path.exists():
            e_path = data_path(egw_db_path)
        self.egw_db_path = e_path
        self.egw_db = EgwDB(e_path) if e_path.exists() else None

        s_path = Path(strongs_path)
        if not s_path.exists():
            s_path = lexicon_path(strongs_path)
        self.strongs_path = s_path

        lex_dir = self.strongs_path.parent if self.strongs_path.parent.exists() else get_lexicons_dir()

        if tbesh_path:
            p = Path(tbesh_path)
            self.tbesh_path = p if p.exists() else lexicon_path(p)
        elif (lex_dir / "tbesh-glosses.json").exists():
            self.tbesh_path = lex_dir / "tbesh-glosses.json"
        else:
            self.tbesh_path = lexicon_path("tbesh-glosses.json")

        if tbesg_path:
            p = Path(tbesg_path)
            self.tbesg_path = p if p.exists() else lexicon_path(p)
        elif (lex_dir / "tbesg-glosses.json").exists():
            self.tbesg_path = lex_dir / "tbesg-glosses.json"
        else:
            self.tbesg_path = lexicon_path("tbesg-glosses.json")
        self._lexicon_cache: dict[str, Any] | None = None
        self._tbesh_cache: dict[str, str] | None = None
        self._tbesg_cache: dict[str, str] | None = None
        self._tbesh_entries_cache: dict[str, list[dict[str, Any]]] | None = None
        self._tbesg_entries_cache: dict[str, list[dict[str, Any]]] | None = None
        self._word_cache: dict[str, WordStudyResult] = {}
        self._verse_frame_cache: dict[str, dict[str, Any]] = {}
        self._verse_nuance_cache: dict[str, list[GrammarNuance]] = {}
        self._lock = threading.RLock()

    def _load_tbes_file(self, path: Path) -> tuple[dict[str, str], dict[str, list[dict[str, Any]]]]:
        if not path.exists():
            return {}, {}
        with open(path, encoding="utf-8") as f:
            raw_data = json.load(f)
            entries = raw_data.get("entries") or raw_data.get("glosses", {})
            gloss_map: dict[str, str] = {}
            entries_map: dict[str, list[dict[str, Any]]] = {}
            for code, items in entries.items():
                if isinstance(items, list):
                    gloss_map[code] = items[0].get("gloss", "") if items else ""
                    entries_map[code] = items
                else:
                    gloss_map[code] = str(items)
                    entries_map[code] = [{"gloss": str(items), "definition": ""}]
            return gloss_map, entries_map

    def _load_lexicons(self) -> None:
        with self._lock:
            if self._lexicon_cache is None:
                if self.strongs_path.exists():
                    with open(self.strongs_path, encoding="utf-8") as f:
                        self._lexicon_cache = json.load(f)
                else:
                    self._lexicon_cache = {}

            if self._tbesh_cache is None or self._tbesh_entries_cache is None:
                self._tbesh_cache, self._tbesh_entries_cache = self._load_tbes_file(self.tbesh_path)

            if self._tbesg_cache is None or self._tbesg_entries_cache is None:
                self._tbesg_cache, self._tbesg_entries_cache = self._load_tbes_file(self.tbesg_path)

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

            # Pre-fetch semantic frames and verbal grammar nuances in batch queries
            batch_frames: dict[str, dict[str, Any]] = {}
            batch_nuances: dict[str, list[GrammarNuance]] = {}
            if self.macula_db and verses_raw:
                v_refs = [f"{vr['osis']}.{vr['chapter']}.{vr['verse']}" for vr in verses_raw]
                if eager_frames:
                    try:
                        batch_frames = get_verse_semantic_frames_batch(v_refs, db=self.macula_db)
                        self._verse_frame_cache.update(batch_frames)
                    except Exception:
                        batch_frames = {}
                try:
                    batch_nuances = get_verses_grammar_nuances_batch(v_refs, db=self.macula_db)
                    self._verse_nuance_cache.update(batch_nuances)
                except Exception:
                    batch_nuances = {}

            # Pre-fetch parallel translations in a single fast query
            batch_translations: dict[int, dict[str, str]] = {}
            if self.bible_db and verses_raw:
                try:
                    batch_translations = self.bible_db.get_chapter_translations(book_code, ch)
                except Exception:
                    batch_translations = {}

            # Pre-fetch discourse markers and passage argument flow (<0.2ms)
            batch_discourse = extract_passage_discourse_batch(verses_raw)
            argument_flow = analyze_passage_argument_flow(verses_raw, markers_by_verse=batch_discourse)

            # Pre-fetch OT citations and NT covenant anchors (<0.1ms)
            batch_citations = get_passage_ot_citations_batch(book_code, ch)

            # Pre-fetch prophetic symbols and sanctuary stations for verses (<0.05ms)
            prophetic_lex = self.get_prophetic_lexicon()
            sanct_engine = self.get_sanctuary_engine()

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

                v_nuances = batch_nuances.get(verse_id, [])
                v_trans = batch_translations.get(vr["verse"], {})
                if not v_trans.get("kjv"):
                    v_trans["kjv"] = vr.get("clean_text") or vr["text"]
                v_discourse = batch_discourse.get(verse_id, [])
                v_citations = batch_citations.get(verse_id, []) or lookup_citations_for_verse(verse_id)
                v_prophetic = prophetic_lex.get_annotated_symbols_for_verse(
                    vr.get("osis", book_code), vr["chapter"], vr["verse"]
                )
                v_sanctuary = sanct_engine.get_annotated_stations_for_verse(
                    vr.get("osis", book_code), vr["chapter"], vr["verse"]
                )

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
                        verbal_nuances=v_nuances,
                        translations=v_trans,
                        discourse_markers=v_discourse,
                        ot_citations=v_citations,
                        prophetic_symbols=v_prophetic,
                        sanctuary_stations=v_sanctuary,
                    )
                )

            # 3. Correlated Spirit of Prophecy passages
            egw_correlations = self._find_egw_correlations(book_name, s_ch, limit=10)

            canonical_ref = passage_ref
            if v1 is None and v2 is None:
                canonical_ref = f"{book_name} {s_ch}"

            study = PassageStudy(
                ref=canonical_ref,
                book_code=book_code,
                book_name=book_name,
                start_chapter=s_ch,
                start_verse=s_v,
                end_chapter=e_ch,
                end_verse=e_v,
                verses=verse_studies,
                egw_correlations=egw_correlations,
                argument_flow=argument_flow,
            )
            study.prev_ref = self.prev_passage(study)
            study.next_ref = self.next_passage(study)
            return study

    def ensure_verse_frames(self, verse: VerseStudy) -> None:
        """Populate semantic frames, verbal nuances, and original language text on-demand if missing."""
        with self._lock:
            # 1. Frames & original text
            if verse.osis in self._verse_frame_cache:
                c_data = self._verse_frame_cache[verse.osis]
                verse.semantic_frames = c_data.get("clauses", [])
                verse.original_text = c_data.get("text", "")
            elif not (verse.semantic_frames and verse.original_text) and self.macula_db:
                try:
                    frame_data = get_verse_semantic_frame(verse.osis, db=self.macula_db) or {}
                    verse.semantic_frames = frame_data.get("clauses", [])
                    verse.original_text = frame_data.get("text", "")
                    self._verse_frame_cache[verse.osis] = frame_data
                except Exception:
                    self._verse_frame_cache[verse.osis] = {}

            # 2. Verbal grammar nuances
            if not verse.verbal_nuances and self.macula_db:
                if verse.osis in self._verse_nuance_cache:
                    verse.verbal_nuances = self._verse_nuance_cache[verse.osis]
                else:
                    try:
                        v_nuances = get_verse_grammar_nuances(verse.osis, db=self.macula_db)
                        verse.verbal_nuances = v_nuances
                        self._verse_nuance_cache[verse.osis] = v_nuances
                    except Exception:
                        verse.verbal_nuances = []

            # 3. Discourse markers (if not already extracted)
            if not verse.discourse_markers and verse.tokens:
                verse.discourse_markers = extract_verse_discourse_markers(
                    verse.tokens, text=verse.text, verse_osis=verse.osis
                )

            # 4. OT Citations (if not already extracted)
            if not verse.ot_citations:
                verse.ot_citations = lookup_citations_for_verse(verse.osis)

    def get_verse_nuance_for_strongs(self, verse: VerseStudy, strongs_code: str) -> list[GrammarNuance]:
        """Return verbal nuances for a specific Strong's number in a verse."""
        if not verse or not verse.verbal_nuances or not strongs_code:
            return []
        target_canon = _canonical_strongs(strongs_code)
        return [
            n for n in verse.verbal_nuances
            if n.strongs and _canonical_strongs(n.strongs) == target_canon
        ]

    def explain_verb(
        self,
        morph: str,
        language: str = "",
        lemma: str = "",
        text: str = "",
        gloss: str = "",
        strongs: str = "",
    ) -> Optional[GrammarNuance]:
        """Explain a verbal morphology code in plain English (ADR-025, WP-031)."""
        return explain_verb(
            morph,
            language=language,
            lemma=lemma,
            text=text,
            gloss=gloss,
            strongs=strongs,
        )

    def get_verse_nuances(self, ref: str, strongs: str = "") -> list[GrammarNuance]:
        """Retrieve all verbal grammar nuances for a verse (optionally filtered by Strong's)."""
        if not self.macula_db:
            return []
        with self._lock:
            nuances = self._verse_nuance_cache.get(ref)
            if nuances is None:
                nuances = get_verse_grammar_nuances(ref, db=self.macula_db)
                self._verse_nuance_cache[ref] = nuances
            if strongs:
                target_canon = _canonical_strongs(strongs)
                return [
                    n for n in nuances
                    if n.strongs and _canonical_strongs(n.strongs) == target_canon
                ]
            return list(nuances)

    def get_available_translations(self) -> list[dict[str, Any]]:
        """Return metadata for all available Bible translations."""
        if not self.bible_db:
            return []
        with self._lock:
            try:
                return self.bible_db.list_translations()
            except Exception:
                return []


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

            # Scholarly Unabridged Lexicon & Strong's Senses
            parsed_strongs = parse_strongs_desc(definition)
            strongs_senses = parsed_strongs["senses"]
            kjv_renderings = parsed_strongs["kjv"]
            etymology = parsed_strongs["etymology"]
            roots = parsed_strongs.get("roots", "")
            if roots:
                etymology = f"{etymology} (Root: {roots})" if etymology else f"Root: {roots}"

            scholarly_def = ""
            source_lexicon = ""
            if is_hebrew and self._tbesh_entries_cache:
                h_entries = self._tbesh_entries_cache.get(canonical_id, [])
                if h_entries:
                    scholarly_def = format_scholarly_entries(h_entries, "Brown-Driver-Briggs")
                    source_lexicon = "Brown-Driver-Briggs (BDB) Hebrew Lexicon"
            elif not is_hebrew and self._tbesg_entries_cache:
                g_entries = self._tbesg_entries_cache.get(canonical_id, [])
                if g_entries:
                    scholarly_def = format_scholarly_entries(g_entries, "Abbott-Smith")
                    source_lexicon = "Abbott-Smith Manual Greek Lexicon"

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
                scholarly_definition=scholarly_def,
                source_lexicon=source_lexicon,
                strongs_senses=strongs_senses,
                kjv_renderings=kjv_renderings,
                etymology=etymology,
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

    @staticmethod
    def _create_egw_teaser(text: str, max_len: int = 140) -> str:
        """Create a clean, single-line excerpt for compact reference chips."""
        s = " ".join((text or "").split()).strip()
        if len(s) <= max_len:
            return s
        cutoff = s[:max_len].rfind(" ")
        if cutoff > max_len // 2:
            return s[:cutoff] + "…"
        return s[:max_len] + "…"

    def _find_egw_correlations(self, book_name: str, s_ch: int, limit: int = 10) -> list[dict[str, Any]]:
        """Internal helper to discover and rank EGW correlations for a book and chapter."""
        if not self.egw_db or not self.egw_db.exists():
            return []
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
                        "chapter_num": h.get("chapter_num"),
                        "chapter_title": h.get("chapter_title", ""),
                        "page": page_num,
                        "paragraph": hit_para,
                        "heading": h.get("chapter_title") or h.get("heading", ""),
                        "snippet": h.get("snippet", ""),
                        "teaser": self._create_egw_teaser(raw_text),
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
            top_hits = candidate_hits[:limit]

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
                            item["teaser"] = self._create_egw_teaser(item["text"])

            return top_hits
        except sqlite3.Error:
            return []

    def get_egw_chapter(self, book_code: str, chapter_num: int | str) -> list[dict[str, Any]]:
        """Retrieve all paragraphs in an EGW book chapter."""
        with self._lock:
            if not self.egw_db:
                return []
            return self.egw_db.get_chapter(book_code, chapter_num)

    def get_egw_chapter_info(self, book_code: str, chapter_num: int | str) -> dict[str, Any] | None:
        """Retrieve metadata for an EGW book chapter."""
        with self._lock:
            if not self.egw_db:
                return None
            return self.egw_db.get_chapter_info(book_code, chapter_num)

    def get_egw_chapter_for_token(self, token: str) -> dict[str, Any] | None:
        """Retrieve the entire chapter containing a given paragraph token, marking the target paragraph."""
        with self._lock:
            if not self.egw_db:
                return None
            return self.egw_db.get_chapter_for_token(token)

    def get_egw_adjacent_chapters(
        self, book_code: str, chapter_num: int | str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Find the immediate previous and next chapters within the same book."""
        with self._lock:
            if not self.egw_db:
                return None, None
            return self.egw_db.get_adjacent_chapters(book_code, chapter_num)

    def get_egw_correlations_for_passage(self, passage_ref: str, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve correlated Spirit of Prophecy commentary for a passage reference."""
        with self._lock:
            if not self.egw_db:
                return []
            try:
                book_code, ch, _, _ = parse_passage_ref(passage_ref)
            except Exception:
                return []
            book_info = BIBLE_BOOKS.get(book_code)
            book_name = book_info.name if book_info else book_code
            return self._find_egw_correlations(book_name, ch, limit=limit)

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

    def get_citation_ot_verse_text(self, citation: OTCitation) -> str:
        """Fetch the text of an Old Testament citation's source verse."""
        if not citation:
            return ""
        if citation.ot_text_kjv:
            return citation.ot_text_kjv
        with self._lock:
            if self.bible_db:
                try:
                    parts = citation.ot_osis.split(".")
                    if len(parts) >= 3:
                        b_code, ch_str, v_str = parts[0], parts[1], parts[2]
                        verses = self.bible_db.get_passage(f"{b_code} {ch_str}:{v_str}")
                        if verses:
                            return verses[0].get("clean_text") or verses[0]["text"]
                except Exception:
                    pass
        return citation.ot_text_kjv

    def get_prophetic_lexicon(self) -> PropheticLexicon:
        """Retrieve the canonical PropheticLexicon index."""
        return get_prophetic_lexicon()

    def get_prophetic_symbols(
        self,
        category: Optional[str] = None,
        book: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve filtered prophetic symbols as dictionaries."""
        lex = self.get_prophetic_lexicon()
        symbols = lex.list_symbols(category=category, book=book, query=query)
        return [s.to_dict() for s in symbols]

    def get_prophetic_symbol(self, symbol_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a prophetic symbol by its unique ID."""
        lex = self.get_prophetic_lexicon()
        s = lex.get_symbol(symbol_id)
        return s.to_dict() if s else None

    def get_prophetic_symbols_for_passage(
        self,
        ref: str,
        include_proofs: bool = True,
    ) -> list[dict[str, Any]]:
        """Retrieve prophetic symbols anchored in or referencing the given passage."""
        lex = self.get_prophetic_lexicon()
        symbols = lex.get_symbols_for_passage(ref, include_proofs=include_proofs)
        return [s.to_dict() for s in symbols]

    def get_annotated_prophetic_symbols_for_passage(
        self,
        ref: str,
        include_proofs: bool = True,
    ) -> list[dict[str, Any]]:
        """Retrieve annotated prophetic symbols with anchor/proof flags for the passage."""
        lex = self.get_prophetic_lexicon()
        symbols = lex.get_annotated_symbols_for_passage(ref, include_proofs=include_proofs)
        return [s.to_dict() for s in symbols]

    def get_sanctuary_engine(self) -> SanctuaryEngine:
        """Get the singleton SanctuaryEngine instance."""
        return get_sanctuary_engine()

    def get_sanctuary_data(self) -> dict[str, Any]:
        """Retrieve the complete structured Sanctuary knowledge graph."""
        return self.get_sanctuary_engine().get_all_data()

    def get_sanctuary_stations(
        self,
        compartment: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve sanctuary stations filtered by compartment or query."""
        engine = self.get_sanctuary_engine()
        stations = engine.list_stations(compartment=compartment, query=query)
        return [s.to_dict() for s in stations]

    def get_sanctuary_station(self, station_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a single sanctuary station by ID."""
        engine = self.get_sanctuary_engine()
        s = engine.get_station(station_id)
        return s.to_dict() if s else None

    def get_annotated_sanctuary_stations_for_passage(
        self,
        ref: str,
    ) -> list[dict[str, Any]]:
        """Retrieve annotated sanctuary stations with OT/NT flags for the passage."""
        engine = self.get_sanctuary_engine()
        stations = engine.get_annotated_stations_for_passage(ref)
        return [s.to_dict() for s in stations]

    def ensure_egw_db(self) -> EgwDB:
        """Ensure an active EgwDB instance is connected, initializing the database if needed."""
        with self._lock:
            if self.egw_db is None or not self.egw_db.exists():
                if self.egw_db is not None:
                    try:
                        self.egw_db.close()
                    except Exception:
                        pass
                self.egw_db = EgwDB(self.egw_db_path)
                self.egw_db.init_db()
            return self.egw_db

    def reload_egw_db(self) -> EgwDB | None:
        """Close and reconnect to egw_db to refresh tables/indices after external updates."""
        with self._lock:
            if self.egw_db is not None:
                try:
                    self.egw_db.close()
                except Exception:
                    pass
                self.egw_db = None
            if self.egw_db_path.exists():
                self.egw_db = EgwDB(self.egw_db_path)
                if not self.egw_db.exists():
                    self.egw_db.init_db()
            return self.egw_db

    def replace_egw_db(self, src_path: Path | str) -> EgwDB:
        """Atomically replace egw.db from a verified file, clearing WAL artifacts."""
        with self._lock:
            if self.egw_db is not None:
                try:
                    self.egw_db.close()
                except Exception:
                    pass
                self.egw_db = None
            self.egw_db_path.parent.mkdir(parents=True, exist_ok=True)
            for suffix in ("-wal", "-shm"):
                wal_file = self.egw_db_path.with_name(self.egw_db_path.name + suffix)
                if wal_file.exists():
                    try:
                        wal_file.unlink(missing_ok=True)
                    except OSError:
                        pass
            shutil.copy2(src_path, self.egw_db_path)
            self.egw_db = EgwDB(self.egw_db_path)
            if not self.egw_db.exists():
                self.egw_db.init_db()
            return self.egw_db

    def get_egw_stats(self) -> dict[str, Any]:
        """Return summary statistics for the local EGW database."""
        with self._lock:
            available = bool(self.egw_db and self.egw_db.exists())
            if not available:
                return {
                    "available": False,
                    "path": str(self.egw_db_path),
                    "books_count": 0,
                    "paragraphs_count": 0,
                }
            try:
                total_paragraphs = self.egw_db.count()
                cur = self.egw_db.conn.execute("SELECT COUNT(DISTINCT book_code) FROM egw_paragraphs;")
                row = cur.fetchone()
                books_count = row[0] if row else 0
                return {
                    "available": True,
                    "path": str(self.egw_db_path),
                    "books_count": books_count,
                    "paragraphs_count": total_paragraphs,
                }
            except Exception:
                return {
                    "available": available,
                    "path": str(self.egw_db_path),
                    "books_count": 0,
                    "paragraphs_count": 0,
                }

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

