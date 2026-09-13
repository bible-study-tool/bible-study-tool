"""Master Historicist Prophetic Lexicon Engine (WP-031 Phase 2, ADR-025).

Provides deterministic access to biblical apocalyptic symbols, their definitions,
canonical proof texts, original language Strong's concordance roots, and historical
Seventh-day Adventist prophetic consensus citations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import threading
from typing import Any, Optional

from search.corpus.bible_books import parse_passage_ref, resolve_book_code
from search.resource import data_path

VALID_CATEGORIES = frozenset({"Time", "Entities", "Elements"})
_STRONGS_RE = re.compile(r"^[HG]\d{1,5}$")


def _normalize_range(v_start: Optional[int], v_end: Optional[int]) -> tuple[int, int]:
    """Normalize verse range boundaries for overlap calculations."""
    if v_start is None:
        return (1, 999)
    return (v_start, v_start if v_end is None else v_end)


@dataclass(frozen=True)
class PropheticSymbol:
    """A canonical prophetic symbol in biblical apocalyptic prophecy."""
    id: str
    symbol: str
    meaning: str
    category: str
    books: list[str]
    proof_texts: list[str]
    canonical_anchors: list[str]
    strongs: list[str]
    sda_consensus: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnnotatedPropheticSymbol:
    """A prophetic symbol annotated with context flags for a specific passage."""
    id: str
    symbol: str
    meaning: str
    category: str
    books: list[str]
    proof_texts: list[str]
    canonical_anchors: list[str]
    strongs: list[str]
    sda_consensus: str
    is_anchor: bool = False
    is_proof: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_symbol(
        cls,
        symbol: PropheticSymbol,
        is_anchor: bool = False,
        is_proof: bool = False,
    ) -> "AnnotatedPropheticSymbol":
        return cls(
            id=symbol.id,
            symbol=symbol.symbol,
            meaning=symbol.meaning,
            category=symbol.category,
            books=list(symbol.books),
            proof_texts=list(symbol.proof_texts),
            canonical_anchors=list(symbol.canonical_anchors),
            strongs=list(symbol.strongs),
            sda_consensus=symbol.sda_consensus,
            is_anchor=is_anchor,
            is_proof=is_proof,
        )


class PropheticLexicon:
    """In-memory index and query engine for biblical prophetic symbols."""

    def __init__(self, data_file: Path | str | None = None) -> None:
        self.path = Path(data_file) if data_file else data_path("prophetic_lexicon.json")
        if not self.path.is_file():
            raise FileNotFoundError(f"Prophetic lexicon dataset not found: {self.path}")

        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.version: str = raw.get("version", "1.0.0")
        self.title: str = raw.get("title", "Master Historicist Prophetic Lexicon")
        self.description: str = raw.get("description", "")
        self.categories: list[str] = raw.get("categories", ["Time", "Entities", "Elements"])

        symbols_list = raw.get("symbols", [])
        self._symbols: list[PropheticSymbol] = []
        self._by_id: dict[str, PropheticSymbol] = {}
        # Pre-computed parsed verse ranges for zero-allocation hot-path overlap queries
        self._anchor_ranges: dict[str, list[tuple[str, int, int, int]]] = {}
        self._proof_ranges: dict[str, list[tuple[str, int, int, int]]] = {}

        for item in symbols_list:
            sym_id = item["id"]
            cat = item.get("category", "")
            if cat not in VALID_CATEGORIES:
                raise ValueError(f"Invalid category {cat!r} for prophetic symbol {sym_id!r}")

            strongs_codes = list(item.get("strongs", []))
            for sc in strongs_codes:
                if not _STRONGS_RE.match(sc):
                    raise ValueError(f"Invalid Strong's code {sc!r} in prophetic symbol {sym_id!r}")

            sym = PropheticSymbol(
                id=sym_id,
                symbol=item["symbol"],
                meaning=item["meaning"],
                category=cat,
                books=list(item.get("books", [])),
                proof_texts=list(item.get("proof_texts", [])),
                canonical_anchors=list(item.get("canonical_anchors", [])),
                strongs=strongs_codes,
                sda_consensus=item.get("sda_consensus", ""),
            )
            self._symbols.append(sym)
            self._by_id[sym.id] = sym

            # Pre-parse canonical anchors and proof texts
            anchors_parsed: list[tuple[str, int, int, int]] = []
            for ref_str in sym.canonical_anchors:
                p = parse_passage_ref(ref_str)
                if p:
                    osis, chap, s, e = p
                    ns, ne = _normalize_range(s, e)
                    anchors_parsed.append((osis, chap, ns, ne))
            self._anchor_ranges[sym.id] = anchors_parsed

            proofs_parsed: list[tuple[str, int, int, int]] = []
            for ref_str in sym.proof_texts:
                p = parse_passage_ref(ref_str)
                if p:
                    osis, chap, s, e = p
                    ns, ne = _normalize_range(s, e)
                    proofs_parsed.append((osis, chap, ns, ne))
            self._proof_ranges[sym.id] = proofs_parsed

    def __len__(self) -> int:
        return len(self._symbols)

    def get_symbol(self, symbol_id: str) -> Optional[PropheticSymbol]:
        """Lookup a symbol by its unique ID."""
        return self._by_id.get(symbol_id)

    def list_symbols(
        self,
        category: Optional[str] = None,
        book: Optional[str] = None,
        query: Optional[str] = None,
    ) -> list[PropheticSymbol]:
        """Filter symbols by category, associated book, or search query."""
        results = self._symbols

        if category:
            cat_norm = category.strip().capitalize()
            results = [s for s in results if s.category == cat_norm]

        if book:
            book_norm = book.strip().lower()
            try:
                book_osis = resolve_book_code(book_norm)
            except ValueError:
                book_osis = None

            if not book_osis:
                results = [s for s in results if any(b.lower() == book_norm for b in s.books)]
            else:
                results = [
                    s for s in results
                    if any(
                        b.lower() == book_norm or resolve_book_code(b) == book_osis
                        for b in s.books
                    )
                ]

        if query:
            q_terms = query.strip().lower().split()
            filtered = []
            for s in results:
                searchable = (
                    f"{s.symbol} {s.meaning} {s.category} {' '.join(s.books)} "
                    f"{s.sda_consensus} {' '.join(s.proof_texts)} {' '.join(s.canonical_anchors)} "
                    f"{' '.join(s.strongs)}"
                ).lower()
                if all(term in searchable for term in q_terms):
                    filtered.append(s)
            results = filtered

        return results

    def get_annotated_symbols_for_verse(
        self,
        osis: str,
        chap: int,
        verse: int,
        include_proofs: bool = True,
    ) -> list[AnnotatedPropheticSymbol]:
        """Direct lookup for symbols overlapping a specific verse without string parsing."""
        results: list[AnnotatedPropheticSymbol] = []
        for s in self._symbols:
            is_anchor = False
            for c_osis, c_chap, c_start, c_end in self._anchor_ranges.get(s.id, []):
                if c_osis == osis and c_chap == chap:
                    if c_start <= verse <= c_end:
                        is_anchor = True
                        break

            is_proof = False
            if include_proofs:
                for c_osis, c_chap, c_start, c_end in self._proof_ranges.get(s.id, []):
                    if c_osis == osis and c_chap == chap:
                        if c_start <= verse <= c_end:
                            is_proof = True
                            break

            if is_anchor or is_proof:
                results.append(
                    AnnotatedPropheticSymbol.from_symbol(
                        s,
                        is_anchor=is_anchor,
                        is_proof=is_proof,
                    )
                )

        return results

    def get_annotated_symbols_for_passage(
        self,
        ref: str,
        include_proofs: bool = True,
    ) -> list[AnnotatedPropheticSymbol]:
        """Find symbols overlapping ref, annotated with is_anchor and is_proof flags."""
        parsed = parse_passage_ref(ref)
        if not parsed:
            return []

        p_osis, p_chap, p_s, p_e = parsed
        p_start, p_end = _normalize_range(p_s, p_e)

        results: list[AnnotatedPropheticSymbol] = []
        for s in self._symbols:
            is_anchor = False
            for c_osis, c_chap, c_start, c_end in self._anchor_ranges.get(s.id, []):
                if c_osis == p_osis and c_chap == p_chap:
                    if max(p_start, c_start) <= min(p_end, c_end):
                        is_anchor = True
                        break

            is_proof = False
            if include_proofs:
                for c_osis, c_chap, c_start, c_end in self._proof_ranges.get(s.id, []):
                    if c_osis == p_osis and c_chap == p_chap:
                        if max(p_start, c_start) <= min(p_end, c_end):
                            is_proof = True
                            break

            if is_anchor or is_proof:
                results.append(
                    AnnotatedPropheticSymbol.from_symbol(
                        s,
                        is_anchor=is_anchor,
                        is_proof=is_proof,
                    )
                )

        return results

    def get_symbols_for_passage(self, ref: str, include_proofs: bool = True) -> list[PropheticSymbol]:
        """Find symbols whose canonical anchors (or proof texts) overlap the given passage."""
        annotated = self.get_annotated_symbols_for_passage(ref, include_proofs=include_proofs)
        return [self._by_id[a.id] for a in annotated]


_CACHED_LEXICON: Optional[PropheticLexicon] = None
_LEXICON_LOCK = threading.Lock()


def get_prophetic_lexicon(data_file: Path | str | None = None) -> PropheticLexicon:
    """Return the cached PropheticLexicon instance (thread-safe singleton)."""
    global _CACHED_LEXICON
    if data_file is not None:
        return PropheticLexicon(data_file)
    if _CACHED_LEXICON is None:
        with _LEXICON_LOCK:
            if _CACHED_LEXICON is None:
                _CACHED_LEXICON = PropheticLexicon()
    return _CACHED_LEXICON
