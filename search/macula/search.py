"""Deterministic Macula lexical, morphological, and semantic search engine (WP-039).

Provides zero-ML, sub-millisecond querying across:
1. Strong's Concordance codes (both Hebrew H-numbers and Greek G-numbers).
2. Hebrew and Greek lemmas, surface forms, and unaccented/unpointed stems.
3. Roman transliterations (e.g. 'bereshit', 'arche', 'logos', 'shalom').
4. Contextual English translation glosses and TBES/BDB definitions.
5. Semantic domains (Louw-Nida NT categories and SDBH OT domains).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from typing import Any, Optional

from search.dbaccess import connect_db_reader
from search.resource import data_path, lexicon_path

DEFAULT_MACULA_DB = "data/macula.db"
DEFAULT_STRONGS_LEXICON = "lexicons/strongs-lexicon.json"

_STRONGS_RE = re.compile(r"^([HGhg]?)0*(\d{1,5})$")

_LEXICON_STOPWORDS = {
    "strong", "strongs", "number", "kjv", "root", "roots",
    "compare", "see", "also", "from", "the", "and", "with",
    "for", "that", "this", "which",
}


def strip_diacritics(text: str) -> str:
    """Strip Hebrew vowel points (niqqud), cantillation, and Greek accents/breathing marks."""
    if not text:
        return ""
    # Normalize to NFD so combining characters are isolated, then drop Mn category (Mark, nonspacing)
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def normalize_strongs(code: str) -> Optional[str]:
    """Normalize a raw Strong's code (e.g. 'h07225', 'H7225', '7225') into canonical format."""
    clean = code.strip()
    m = _STRONGS_RE.match(clean)
    if not m:
        return None
    prefix = m.group(1).upper() if m.group(1) else ""
    num = int(m.group(2))
    if not prefix:
        # If no prefix specified, cannot distinguish without context, but default to None
        return None
    return f"{prefix}{num}"


@dataclass
class MaculaLexicalHit:
    """A search result from the Macula Hebrew/Greek linguistic database."""
    strongs: str
    language: str  # 'hebrew' | 'greek'
    lemma: str
    translit: str
    glosses: list[str]
    occurrences: int
    domains: list[str]
    lxx_crosswalk: dict[str, Any]
    sample_verses: list[str]
    definition: str
    match_type: str  # 'strongs' | 'lemma' | 'translit' | 'gloss' | 'domain'
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MaculaSearchEngine:
    """Sub-millisecond lexical and semantic search over data/macula.db and lexicons."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        lexicon_file: str | Path | None = None,
    ):
        if db_path is not None:
            self.db_path = Path(db_path)
        else:
            self.db_path = data_path("macula.db")

        if lexicon_file is not None:
            self.lexicon_file = Path(lexicon_file)
        else:
            self.lexicon_file = lexicon_path("strongs-lexicon.json")

        self._conn: Optional[sqlite3.Connection] = None
        self._lexicon_data: Optional[dict[str, Any]] = None
        self._lemma_index: Optional[dict[str, list[str]]] = None  # lemma -> [strongs]
        self._translit_index: Optional[dict[str, list[str]]] = None  # translit_norm -> [strongs]
        self._def_index: Optional[dict[str, list[str]]] = None  # word -> [strongs]

    @property
    def conn(self) -> sqlite3.Connection:
        """Sidecar-free read-only connection (ADR-027 §5)."""
        if self._conn is None:
            if not self.db_path.is_file():
                raise FileNotFoundError(f"Macula SQLite DB not found at {self.db_path}")
            self._conn = connect_db_reader(
                self.db_path,
                row_factory=sqlite3.Row,
                check_same_thread=False,
            )
        return self._conn

    def _ensure_lexicon_loaded(self) -> None:
        """Lazily load strongs-lexicon.json into memory (approx 4 MB, ~30ms)."""
        if self._lexicon_data is not None:
            return

        if not self.lexicon_file.is_file():
            self._lexicon_data = {"hebrew": {}, "greek": {}}
            self._lemma_index = {}
            self._translit_index = {}
            self._def_index = {}
            return

        with open(self.lexicon_file, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self._lexicon_data = {
            "hebrew": raw.get("hebrew", {}),
            "greek": raw.get("greek", {}),
        }

        # Build in-memory inverted indices for transliteration, definition words, and lemmas
        self._translit_index = {}
        self._def_index = {}
        self._lemma_index = {}

        for lang, entries in self._lexicon_data.items():
            for s_code, entry in entries.items():
                # Lemma index
                w = entry.get("word", "")
                if w:
                    self._lemma_index.setdefault(w, []).append(s_code)
                    clean_w = strip_diacritics(w)
                    if clean_w and clean_w != w:
                        self._lemma_index.setdefault(clean_w, []).append(s_code)

                # Translit index
                tr = entry.get("translit", "")
                if tr:
                    clean_tr = re.sub(r"[^a-zA-Z]", "", tr).lower()
                    if clean_tr:
                        self._translit_index.setdefault(clean_tr, []).append(s_code)

                # Definition words index
                desc = entry.get("desc", "")
                if desc:
                    words = set(re.findall(r"\b[a-zA-Z]{3,}\b", desc.lower())) - _LEXICON_STOPWORDS
                    for def_word in words:
                        self._def_index.setdefault(def_word, []).append(s_code)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> MaculaSearchEngine:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def get_sample_verses(self, strongs_code: str, limit: int = 5) -> list[str]:
        """Fetch distinct verse references where this Strong's code occurs."""
        try:
            cur = self.conn.execute(
                "SELECT DISTINCT verse_id FROM tokens WHERE strongs = ? ORDER BY verse_id LIMIT ?;",
                (strongs_code, limit),
            )
            return [r[0] for r in cur.fetchall()]
        except sqlite3.OperationalError:
            return []

    def get_strongs_entry(self, strongs_code: str) -> Optional[dict[str, Any]]:
        """Fetch Strong's lexicon definition dictionary (pointed word, translit, desc)."""
        self._ensure_lexicon_loaded()
        s_norm = strongs_code.upper()
        if s_norm.startswith("H"):
            return self._lexicon_data["hebrew"].get(s_norm)
        if s_norm.startswith("G"):
            return self._lexicon_data["greek"].get(s_norm)
        return None

    def search_strongs(self, strongs_code: str) -> Optional[MaculaLexicalHit]:
        """Look up a Strong's code directly from strongs_crosswalk and strongs-lexicon."""
        s_clean = strongs_code.strip().upper()
        m = _STRONGS_RE.match(s_clean)
        if not m:
            return None
        prefix = m.group(1).upper()
        num = int(m.group(2))
        canonical_code = f"{prefix}{num}" if prefix else None

        if not canonical_code:
            # Try both H and G
            hit = self.search_strongs(f"H{num}")
            if hit:
                return hit
            return self.search_strongs(f"G{num}")

        cur = self.conn.execute(
            "SELECT * FROM strongs_crosswalk WHERE strongs = ?;",
            (canonical_code,),
        )
        row = cur.fetchone()
        if not row:
            # Fall back to lexicon entry only
            entry = self.get_strongs_entry(canonical_code)
            if not entry:
                return None
            lang = "hebrew" if canonical_code.startswith("H") else "greek"
            return MaculaLexicalHit(
                strongs=canonical_code,
                language=lang,
                lemma=entry.get("word", ""),
                translit=entry.get("translit", ""),
                glosses=[],
                occurrences=0,
                domains=[],
                lxx_crosswalk={},
                sample_verses=self.get_sample_verses(canonical_code),
                definition=entry.get("desc", ""),
                match_type="strongs",
                score=1.0,
            )

        return self._build_hit_from_row(row, match_type="strongs", score=1.0, include_samples=True)

    def search_lemma(self, lemma_query: str, limit: int = 20) -> list[MaculaLexicalHit]:
        """Search by Hebrew or Greek lemma/surface form (exact or stripped diacritics)."""
        clean_q = lemma_query.strip()
        if not clean_q:
            return []

        self._ensure_lexicon_loaded()
        stripped_q = strip_diacritics(clean_q)
        results: list[MaculaLexicalHit] = []
        seen_strongs: set[str] = set()

        # 1. Exact or stripped lemma match via in-memory lexicon index
        if self._lemma_index:
            for s_code in self._lemma_index.get(clean_q, []):
                if s_code not in seen_strongs:
                    seen_strongs.add(s_code)
                    hit = self.search_strongs(s_code)
                    if hit:
                        hit.match_type = "lemma"
                        hit.score = 0.98
                        results.append(hit)

            if len(results) < limit and stripped_q in self._lemma_index:
                for s_code in self._lemma_index[stripped_q]:
                    if s_code not in seen_strongs:
                        seen_strongs.add(s_code)
                        hit = self.search_strongs(s_code)
                        if hit:
                            hit.match_type = "lemma"
                            hit.score = 0.95
                            results.append(hit)

        # 2. Query tokens table only as a last resort when in-memory lexicon index misses
        if not results:
            cur = self.conn.execute(
                """
                SELECT DISTINCT strongs FROM tokens
                WHERE (lemma = ? OR text = ?)
                  AND strongs IS NOT NULL
                LIMIT ?;
                """,
                (clean_q, clean_q, limit),
            )
            for r in cur.fetchall():
                s_code = r[0]
                if s_code and s_code not in seen_strongs:
                    seen_strongs.add(s_code)
                    hit = self.search_strongs(s_code)
                    if hit:
                        hit.match_type = "lemma"
                        hit.score = 0.92
                        results.append(hit)

        return results[:limit]

    def search_gloss(self, english_term: str, limit: int = 20) -> list[MaculaLexicalHit]:
        """Search Hebrew/Greek entries by English translation gloss or Strong's definition."""
        term = english_term.strip().lower()
        if not term:
            return []

        self._ensure_lexicon_loaded()
        results: list[MaculaLexicalHit] = []
        seen_strongs: set[str] = set()

        # 1. Exact gloss match in strongs_crosswalk.glosses_json
        # JSON array contains e.g. "covenant", "beginning", "sanctuary"
        exact_pattern = f'%"{term}"%'
        cur_exact = self.conn.execute(
            "SELECT * FROM strongs_crosswalk WHERE LOWER(glosses_json) LIKE ? ORDER BY occurrences DESC LIMIT ?;",
            (exact_pattern, limit),
        )
        for r in cur_exact.fetchall():
            s_code = r["strongs"]
            seen_strongs.add(s_code)
            results.append(self._build_hit_from_row(r, match_type="gloss", score=0.85))

        # 2. Transliteration matches (e.g. 'logos' -> G3056, 'arche' -> G746, 'bereshit' -> H7225)
        clean_term_tr = re.sub(r"[^a-zA-Z]", "", term)
        if clean_term_tr and self._translit_index and clean_term_tr in self._translit_index:
            for s_code in self._translit_index[clean_term_tr]:
                if s_code not in seen_strongs and len(results) < limit:
                    seen_strongs.add(s_code)
                    hit = self.search_strongs(s_code)
                    if hit:
                        hit.match_type = "translit"
                        hit.score = 0.88
                        results.append(hit)

        # 3. Definition inverted index matches
        if len(results) < limit and self._def_index and term in self._def_index:
            for s_code in self._def_index[term]:
                if s_code not in seen_strongs and len(results) < limit:
                    seen_strongs.add(s_code)
                    hit = self.search_strongs(s_code)
                    if hit:
                        hit.match_type = "definition"
                        hit.score = 0.75
                        results.append(hit)

        # Sort results: exact score first, then occurrences
        results.sort(key=lambda h: (h.score, h.occurrences), reverse=True)
        return results[:limit]

    def search_domain(self, domain_code: str, limit: int = 20) -> list[MaculaLexicalHit]:
        """Search entries mapped to a specific Louw-Nida or SDBH semantic domain."""
        clean_d = domain_code.strip()
        if not clean_d:
            return []

        pattern = f'%"{clean_d}"%'
        cur = self.conn.execute(
            """
            SELECT * FROM strongs_crosswalk
            WHERE lex_domains_json LIKE ? OR core_domains_json LIKE ? OR sdbh_json LIKE ?
            ORDER BY occurrences DESC LIMIT ?;
            """,
            (pattern, pattern, pattern, limit),
        )
        results = [
            self._build_hit_from_row(r, match_type="domain", score=0.70)
            for r in cur.fetchall()
        ]
        return results

    def search(self, query: str, limit: int = 20) -> list[MaculaLexicalHit]:
        """Unified entry point for Macula lexical and semantic search.

        Automatically recognizes:
        - Strong's codes ('H7225', 'G746', 'H1285') -> instant exact lookup.
        - Greek / Hebrew characters -> lemma search.
        - English / Roman keywords -> bidirectional gloss, transliteration, and definition search.
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        # Check for Strong's code
        if _STRONGS_RE.match(clean_q):
            hit = self.search_strongs(clean_q)
            if hit:
                hits = [hit]
                # If hit has LXX alignments, add top aligned codes
                if hit.lxx_crosswalk:
                    for lxx_code, info in sorted(
                        hit.lxx_crosswalk.items(),
                        key=lambda x: x[1].get("count", 0) if isinstance(x[1], dict) else 0,
                        reverse=True,
                    )[:3]:
                        lxx_hit = self.search_strongs(lxx_code)
                        if lxx_hit:
                            lxx_hit.match_type = "lxx_aligned"
                            lxx_hit.score = 0.85
                            hits.append(lxx_hit)
                return hits[:limit]

        # Check if query contains Hebrew or Greek characters
        has_hebrew_or_greek = any(
            "\u0590" <= c <= "\u05FF" or "\u0370" <= c <= "\u03FF" or "\u1F00" <= c <= "\u1FFF"
            for c in clean_q
        )
        if has_hebrew_or_greek:
            hits = self.search_lemma(clean_q, limit=limit)
        else:
            # Search English glosses, transliterations, and definitions
            hits = self.search_gloss(clean_q, limit=limit)

        if hits and not hits[0].sample_verses:
            hits[0].sample_verses = self.get_sample_verses(hits[0].strongs)
        return hits

    def _build_hit_from_row(
        self,
        row: sqlite3.Row,
        match_type: str = "gloss",
        score: float = 0.80,
        include_samples: bool = False,
    ) -> MaculaLexicalHit:
        """Helper to construct MaculaLexicalHit from a strongs_crosswalk row."""
        s_code = row["strongs"]
        lang = "hebrew" if s_code.startswith("H") else "greek"
        lemmas = json.loads(row["lemmas_json"])
        glosses = json.loads(row["glosses_json"])
        domains = json.loads(row["lex_domains_json"]) or json.loads(row["core_domains_json"])
        lxx = json.loads(row["lxx_json"]) if "lxx_json" in row.keys() and row["lxx_json"] else {}
        occurrences = row["occurrences"]

        entry = self.get_strongs_entry(s_code) or {}
        lemma = lemmas[0] if lemmas else entry.get("word", "")
        translit = entry.get("translit", "")
        definition = entry.get("desc", "")

        return MaculaLexicalHit(
            strongs=s_code,
            language=lang,
            lemma=lemma,
            translit=translit,
            glosses=glosses,
            occurrences=occurrences,
            domains=domains,
            lxx_crosswalk=lxx,
            sample_verses=self.get_sample_verses(s_code) if include_samples else [],
            definition=definition,
            match_type=match_type,
            score=score,
        )
