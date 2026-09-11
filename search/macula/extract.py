"""Lowfat XML parser and linguistic extractor for Clear-Bible Macula Hebrew.

Extracts token-level linguistic attributes (Hebrew Strong's, Greek LXX Strong's,
SDBH semantic domains, glosses, morphology) and syntactic structure (sentence,
clause rules, phrases, and participant roles: Subject, Predicate, Object,
Prepositional Phrase, Adjunct) using Python standard library ElementTree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import gzip
import json
import logging
from pathlib import Path
import re
from typing import Any, Iterable, Iterator
import xml.etree.ElementTree as ET

from search.corpus.bible_books import resolve_book_code
from search.resource import resource_path

_HEBREW_RE = re.compile(r"^[Hh]?0*(\d+)[a-zA-Z]?$")
_GREEK_RE = re.compile(r"^[Gg]?0*(\d+)[a-zA-Z]?$")

ROLE_LABELS: dict[str, str] = {
    "s": "subject",
    "v": "predicate_verb",
    "vc": "copula",
    "o": "object",
    "o2": "indirect_object",
    "p": "predicate",
    "pp": "prepositional_phrase",
    "prep": "preposition",
    "adv": "adverbial",
    "cjp": "conjunction_phrase",
    "voc": "vocative",
    "cl": "clause",
}

ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "s": ("s", "subject"),
    "subj": ("s", "subject"),
    "subject": ("s", "subject"),
    "v": ("v", "predicate_verb"),
    "verb": ("v", "predicate_verb"),
    "predicate_verb": ("v", "predicate_verb"),
    "pred_verb": ("v", "predicate_verb"),
    "vc": ("vc", "copula"),
    "copula": ("vc", "copula"),
    "cop": ("vc", "copula"),
    "o": ("o", "object"),
    "obj": ("o", "object"),
    "object": ("o", "object"),
    "o2": ("o2", "indirect_object"),
    "iobj": ("o2", "indirect_object"),
    "indirect_object": ("o2", "indirect_object"),
    "p": ("p", "predicate"),
    "pred": ("p", "predicate"),
    "predicate": ("p", "predicate"),
    "pp": ("pp", "prepositional_phrase", "prep", "preposition"),
    "prep": ("pp", "prepositional_phrase", "prep", "preposition"),
    "preposition": ("pp", "prepositional_phrase", "prep", "preposition"),
    "prepositional_phrase": ("pp", "prepositional_phrase", "prep", "preposition"),
    "adv": ("adv", "adverbial"),
    "adverbial": ("adv", "adverbial"),
    "voc": ("voc", "vocative"),
    "vocative": ("voc", "vocative"),
    "cl": ("cl", "clause"),
    "clause": ("cl", "clause"),
    "cjp": ("cjp", "conjunction_phrase"),
    "conjunction_phrase": ("cjp", "conjunction_phrase"),
}


def resolve_role_query(role_query: str) -> tuple[str, ...]:
    """Resolve a user role string to matching role codes and labels."""
    clean = role_query.strip().lower()
    if clean in ROLE_ALIASES:
        return ROLE_ALIASES[clean]
    return (clean,)



def _normalize_strongs(raw: str | None, pattern: re.Pattern, prefix: str, max_num: int) -> str | None:
    if not raw:
        return None
    match = pattern.match(raw.strip())
    if not match:
        return None
    num = int(match.group(1))
    if num <= 0 or num > max_num:
        return None
    return f"{prefix}{num}"


def normalize_hebrew_strongs(raw: str | None) -> str | None:
    """Normalize a Hebrew Strong's identifier to canonical form 'H{num}'.

    Accepts '0871a', '7225', 'H0430', 'H430', '0001', returning 'H871', 'H7225',
    'H430', 'H1' matching lexicons/strongs-list.json. Returns None if invalid or empty.
    """
    return _normalize_strongs(raw, _HEBREW_RE, "H", 8674)


def normalize_greek_strongs(raw: str | None) -> str | None:
    """Normalize a Greek LXX Strong's identifier to canonical form 'G{num}'.

    Accepts '1722', '0746', 'G2316', returning 'G1722', 'G746', 'G2316'
    matching lexicons/strongs-list.json. Returns None if invalid or empty.
    """
    return _normalize_strongs(raw, _GREEK_RE, "G", 5624)


# Canonical 39 Old Testament books: Macula lowfat XML abbreviation -> OSIS code
MACULA_TO_OSIS: dict[str, str] = {
    "GEN": "Gen",
    "EXO": "Exod",
    "LEV": "Lev",
    "NUM": "Num",
    "DEU": "Deut",
    "JOS": "Josh",
    "JDG": "Judg",
    "RUT": "Ruth",
    "1SA": "1Sam",
    "2SA": "2Sam",
    "1KI": "1Kgs",
    "2KI": "2Kgs",
    "1CH": "1Chr",
    "2CH": "2Chr",
    "EZR": "Ezra",
    "NEH": "Neh",
    "EST": "Esth",
    "JOB": "Job",
    "PSA": "Ps",
    "PRO": "Prov",
    "ECC": "Eccl",
    "SNG": "Song",
    "ISA": "Isa",
    "JER": "Jer",
    "LAM": "Lam",
    "EZK": "Ezek",
    "DAN": "Dan",
    "HOS": "Hos",
    "JOL": "Joel",
    "AMO": "Amos",
    "OBA": "Obad",
    "JON": "Jonah",
    "MIC": "Mic",
    "NAM": "Nah",
    "HAB": "Hab",
    "ZEP": "Zeph",
    "HAG": "Hag",
    "ZEC": "Zech",
    "MAL": "Mal",

    # New Testament (27 books: Macula lowfat XML abbreviation -> OSIS code)
    "MAT": "Matt",
    "MRK": "Mark",
    "LUK": "Luke",
    "JHN": "John",
    "ACT": "Acts",
    "ROM": "Rom",
    "1CO": "1Cor",
    "2CO": "2Cor",
    "GAL": "Gal",
    "EPH": "Eph",
    "PHP": "Phil",
    "COL": "Col",
    "1TH": "1Thess",
    "2TH": "2Thess",
    "1TI": "1Tim",
    "2TI": "2Tim",
    "TIT": "Titus",
    "PHM": "Phlm",
    "HEB": "Heb",
    "JAS": "Jas",
    "1PE": "1Pet",
    "2PE": "2Pet",
    "1JN": "1John",
    "2JN": "2John",
    "3JN": "3John",
    "JUD": "Jude",
    "REV": "Rev",
}

OSIS_TO_MACULA: dict[str, str] = {v: k for k, v in MACULA_TO_OSIS.items()}

# Common aliases and names for Old Testament books -> canonical OSIS code
OSIS_BOOK_ALIASES: dict[str, str] = {
    "genesis": "Gen", "gen": "Gen",
    "exodus": "Exod", "exod": "Exod", "exo": "Exod",
    "leviticus": "Lev", "lev": "Lev",
    "numbers": "Num", "num": "Num",
    "deuteronomy": "Deut", "deut": "Deut", "deu": "Deut",
    "joshua": "Josh", "josh": "Josh", "jos": "Josh",
    "judges": "Judg", "judg": "Judg", "jdg": "Judg",
    "ruth": "Ruth", "rut": "Ruth",
    "1 samuel": "1Sam", "1samuel": "1Sam", "1sam": "1Sam", "1sa": "1Sam", "i samuel": "1Sam", "1-samuel": "1Sam",
    "2 samuel": "2Sam", "2samuel": "2Sam", "2sam": "2Sam", "2sa": "2Sam", "ii samuel": "2Sam", "2-samuel": "2Sam",
    "1 kings": "1Kgs", "1kings": "1Kgs", "1kgs": "1Kgs", "1ki": "1Kgs", "i kings": "1Kgs", "1-kings": "1Kgs",
    "2 kings": "2Kgs", "2kings": "2Kgs", "2kgs": "2Kgs", "2ki": "2Kgs", "ii kings": "2Kgs", "2-kings": "2Kgs",
    "1 chronicles": "1Chr", "1chronicles": "1Chr", "1chr": "1Chr", "1ch": "1Chr", "i chronicles": "1Chr", "1-chronicles": "1Chr",
    "2 chronicles": "2Chr", "2chronicles": "2Chr", "2chr": "2Chr", "2ch": "2Chr", "ii chronicles": "2Chr", "2-chronicles": "2Chr",
    "ezra": "Ezra", "ezr": "Ezra",
    "nehemiah": "Neh", "neh": "Neh",
    "esther": "Esth", "esth": "Esth", "est": "Esth",
    "job": "Job",
    "psalms": "Ps", "psalm": "Ps", "ps": "Ps", "psa": "Ps",
    "proverbs": "Prov", "prov": "Prov", "pro": "Prov",
    "ecclesiastes": "Eccl", "eccl": "Eccl", "ecc": "Eccl",
    "song of solomon": "Song", "song of songs": "Song", "song": "Song", "sng": "Song", "canticles": "Song",
    "isaiah": "Isa", "isa": "Isa",
    "jeremiah": "Jer", "jer": "Jer",
    "lamentations": "Lam", "lam": "Lam",
    "ezekiel": "Ezek", "ezek": "Ezek", "ezk": "Ezek",
    "daniel": "Dan", "dan": "Dan",
    "hosea": "Hos", "hos": "Hos",
    "joel": "Joel", "jol": "Joel",
    "amos": "Amos", "amo": "Amos",
    "obadiah": "Obad", "obad": "Obad", "oba": "Obad",
    "jonah": "Jonah", "jon": "Jonah",
    "micah": "Mic", "mic": "Mic",
    "nahum": "Nah", "nah": "Nah", "nam": "Nah",
    "habakkuk": "Hab", "hab": "Hab",
    "zephaniah": "Zeph", "zeph": "Zeph", "zep": "Zeph",
    "haggai": "Hag", "hag": "Hag",
    "zechariah": "Zech", "zech": "Zech", "zec": "Zech",
    "malachi": "Mal", "mal": "Mal",
}


def resolve_osis_book(book_str: str) -> str:
    """Resolve any book name, abbreviation, or alias to canonical OSIS code (e.g. 'Gen', 'Ps', 'Dan', 'John')."""
    clean_upper = book_str.strip().upper()
    if clean_upper in MACULA_TO_OSIS:
        return MACULA_TO_OSIS[clean_upper]
    clean = book_str.strip().lower()
    if clean in OSIS_BOOK_ALIASES:
        return OSIS_BOOK_ALIASES[clean]
    try:
        return resolve_book_code(book_str)
    except (ValueError, NameError):
        return book_str.strip().capitalize()


_PS_2TITLE_DEFAULT: frozenset[int] = frozenset({51, 52, 54, 60})
_PS_1TITLE_DEFAULT: frozenset[int] = frozenset({
    3, 4, 5, 6, 7, 8, 9, 12, 13, 18, 19, 20, 21, 22, 30, 31, 34, 36, 38, 39,
    40, 41, 42, 44, 45, 46, 47, 48, 49, 53, 55, 56, 57, 58, 59, 61, 62, 63,
    64, 65, 67, 68, 69, 70, 75, 76, 77, 80, 81, 83, 84, 85, 88, 89, 92, 102,
    108, 140, 142,
})

_VERSIFICATION_CACHE: tuple[dict[str, str], set[int], set[int]] | None = None


def get_versification_map(versemap_path: Path | str | None = None) -> tuple[dict[str, str], set[int], set[int]]:
    """Return cached (vmap, ps_1title_chapters, ps_2title_chapters) from OSHB VerseMap.xml or bundled fixture."""
    global _VERSIFICATION_CACHE
    if _VERSIFICATION_CACHE is not None and versemap_path is None:
        return _VERSIFICATION_CACHE

    vmap: dict[str, str] = {}
    # Genesis & Malachi baseline fallback (guaranteed offline determinism)
    vmap["Gen.32.1"] = "Gen.31.55"
    for v in range(2, 34):
        vmap[f"Gen.32.{v}"] = f"Gen.32.{v - 1}"
    for idx, v in enumerate(range(19, 25), 1):
        vmap[f"Mal.3.{v}"] = f"Mal.4.{idx}"

    ps_2title = set(_PS_2TITLE_DEFAULT)
    ps_1title = set(_PS_1TITLE_DEFAULT)

    p = Path(versemap_path or "data/oshb/VerseMap.xml")
    if p.is_file():
        try:
            tree = ET.parse(p)
            ns = {"ns": "http://www.APTBibleTools.com/namespace"}
            for v_el in tree.findall(".//ns:verse", ns):
                wlc_ref = v_el.attrib.get("wlc", "").split("!")[0].strip()
                kjv_ref = v_el.attrib.get("kjv", "").split("!")[0].strip()
                if wlc_ref and kjv_ref:
                    vmap[wlc_ref] = kjv_ref
                    if wlc_ref.startswith("Ps.") and wlc_ref.endswith(".2") and kjv_ref.endswith(".1"):
                        ch = int(wlc_ref.split(".")[1])
                        ps_1title.add(ch)
            ps_1title -= ps_2title
        except ET.ParseError as e:
            raise ValueError(f"Corrupt or invalid VerseMap.xml at {p}: {e}") from e
    else:
        # 3-tier precedence:
        # 1. Primary: explicitly passed versemap_path or data/oshb/VerseMap.xml
        # 2. Tier 2: search/fixtures/versemap.json.gz (headless CI / packaged release)
        # 3. Tier 3: _PS_1TITLE_DEFAULT + Malachi/Genesis baseline (zero-fixture fallback)
        bundled = resource_path("search/fixtures/versemap.json.gz")
        if not bundled.is_file():
            bundled = Path(__file__).resolve().parent.parent / "fixtures" / "versemap.json.gz"
        if bundled.is_file():
            try:
                with gzip.open(bundled, "rt", encoding="utf-8") as f:
                    raw = json.load(f)
                vmap.update(raw.get("vmap", {}))
                if "ps_1title" in raw:
                    ps_1title = set(raw["ps_1title"])
                if "ps_2title" in raw:
                    ps_2title = set(raw["ps_2title"])
                ps_1title -= ps_2title
            except (gzip.BadGzipFile, json.JSONDecodeError, OSError, KeyError) as e:
                logging.getLogger(__name__).warning("Failed to load bundled versemap fixture from %s: %s", bundled, e)

    res = (vmap, ps_1title, ps_2title)
    if versemap_path is None:
        _VERSIFICATION_CACHE = res
    return res


def map_mt_to_canonical_verse(
    chapter: int,
    verse_num: int,
    book_code: str = "GEN",
    versemap_data: tuple[dict[str, str], set[int], set[int]] | None = None,
) -> tuple[str, str]:
    """Map Masoretic Text (MT) chapter:verse to canonical KJV corpus reference.

    Uses OSHB VerseMap.xml to align MT numbering (including Psalms titles,
    Malachi 3/4, Genesis 31/32, etc.) to standard KJV versification.

    Returns (canonical_ref, mt_ref) e.g. ('Gen.31.55', 'GEN 32:1') or ('Mal.4.1', 'MAL 3:19').
    """
    clean_b = book_code.strip().upper()
    osis_b = MACULA_TO_OSIS.get(clean_b, resolve_osis_book(book_code))
    mt_ref = f"{clean_b} {chapter}:{verse_num}"

    vmap, ps_1title, ps_2title = versemap_data if versemap_data is not None else get_versification_map()
    wlc_key = f"{osis_b}.{chapter}.{verse_num}"

    if osis_b == "Ps" and verse_num == 1 and (chapter in ps_1title or chapter in ps_2title):
        canonical_ref = f"Ps.{chapter}.0"
    elif osis_b == "Ps" and verse_num == 2 and chapter in ps_2title:
        canonical_ref = f"Ps.{chapter}.0b"
    else:
        canonical_ref = vmap.get(wlc_key, wlc_key)

    return canonical_ref, mt_ref


def parse_verse_id(verse_id: str) -> tuple[str, int, int]:
    """Parse a canonical verse ID (e.g. 'Gen.1.1' or 'Ps.51.0b') into (book_code, chapter, verse_num)."""
    parts = verse_id.split(".")
    b_code = parts[0].upper() if len(parts) > 0 else "GEN"
    ch = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    vs = 1
    if len(parts) > 2:
        m_vs = re.match(r"^(\d+)", parts[2])
        if m_vs:
            vs = int(m_vs.group(1))
    return b_code, ch, vs


@dataclass
class TokenRecord:
    id: str
    text: str
    lemma: str
    strongs: str | None
    raw_strongs: str | None
    lxx_strongs: str | None
    lxx: str | None
    gloss: str
    pos: str
    morph: str
    role: str
    sdbh: str | None = None
    core_domains: list[str] = field(default_factory=list)
    lex_domains: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "id": self.id,
            "text": self.text,
            "lemma": self.lemma,
            "strongs": self.strongs,
            "lxx_strongs": self.lxx_strongs,
            "lxx": self.lxx,
            "gloss": self.gloss,
            "role": self.role,
        }
        if self.sdbh:
            d["sdbh"] = self.sdbh
        if self.core_domains:
            d["core_domains"] = self.core_domains
        return d


@dataclass
class ConstituentRecord:
    role: str
    role_label: str
    phrase_class: str
    rule: str
    text: str
    tokens: list[TokenRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "role_label": self.role_label,
            "class": self.phrase_class,
            "rule": self.rule,
            "text": self.text,
            "tokens": [t.to_dict() for t in self.tokens],
        }


@dataclass
class ClauseRecord:
    rule: str
    text: str
    constituents: list[ConstituentRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "text": self.text,
            "constituents": [c.to_dict() for c in self.constituents],
        }


@dataclass
class VerseRecord:
    verse_id: str
    mt_id: str
    chapter: int
    verse_num: int
    text: str
    clauses: list[ClauseRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "verse_id": self.verse_id,
            "mt_id": self.mt_id,
            "text": self.text,
            "clauses": [c.to_dict() for c in self.clauses],
        }


def parse_token(w_el: ET.Element, default_role: str = "") -> TokenRecord:
    """Parse a single <w> token element."""
    wid = w_el.attrib.get(
        "{http://www.w3.org/XML/1998/namespace}id",
        w_el.attrib.get("xml:id", w_el.attrib.get("id", "")),
    )
    raw_s = w_el.attrib.get("strongnumberx")
    raw_gs = w_el.attrib.get("greekstrong")
    role = w_el.attrib.get("role") or default_role or w_el.attrib.get("class", "")

    cd_str = w_el.attrib.get("coredomain")
    core_domains = cd_str.split() if cd_str else []

    ld_str = w_el.attrib.get("lexdomain")
    lex_domains = ld_str.split() if ld_str else []

    return TokenRecord(
        id=wid,
        text=w_el.text or "",
        lemma=w_el.attrib.get("stronglemma") or w_el.attrib.get("lemma", ""),
        strongs=normalize_hebrew_strongs(raw_s),
        raw_strongs=raw_s,
        lxx_strongs=normalize_greek_strongs(raw_gs),
        lxx=w_el.attrib.get("greek"),
        gloss=w_el.attrib.get("gloss") or w_el.attrib.get("english", ""),
        pos=w_el.attrib.get("pos", ""),
        morph=w_el.attrib.get("morph", ""),
        role=role,
        sdbh=w_el.attrib.get("sdbh"),
        core_domains=core_domains,
        lex_domains=lex_domains,
    )


def _extract_tokens_recursive(el: ET.Element, default_role: str = "") -> list[TokenRecord]:
    """Recursively collect all <w> tokens from an element."""
    tokens: list[TokenRecord] = []
    for w in el.findall(".//w"):
        tokens.append(parse_token(w, default_role=default_role))
    return tokens


def parse_constituent(child_el: ET.Element) -> ConstituentRecord:
    """Parse a direct constituent of a clause (either <wg> phrase or <w> token)."""
    tag = child_el.tag
    role = child_el.attrib.get("role") or child_el.attrib.get("class", "")
    phrase_cls = child_el.attrib.get("class", "")
    rule = child_el.attrib.get("rule", "")
    label = ROLE_LABELS.get(role.lower(), role)

    if tag == "w":
        w_text = child_el.text or ""
        token = parse_token(child_el, default_role=role)
        return ConstituentRecord(
            role=role,
            role_label=label,
            phrase_class=phrase_cls or "word",
            rule=rule,
            text=w_text,
            tokens=[token],
        )
    elif tag == "wg":
        # Multi-token phrase or embedded clause
        tokens = _extract_tokens_recursive(child_el, default_role=role)
        w_text = " ".join(t.text for t in tokens if t.text)
        return ConstituentRecord(
            role=role,
            role_label=label,
            phrase_class=phrase_cls,
            rule=rule,
            text=w_text,
            tokens=tokens,
        )
    else:
        raise ValueError(f"Unrecognized constituent element tag: {tag}")


def parse_clause(cl_el: ET.Element) -> ClauseRecord:
    """Parse a <wg class='cl'> element into a ClauseRecord."""
    rule = cl_el.attrib.get("rule", "")
    constituents: list[ConstituentRecord] = []
    for child in cl_el:
        if child.tag in ("wg", "w"):
            constituents.append(parse_constituent(child))

    clause_text = " ".join(c.text for c in constituents if c.text)
    return ClauseRecord(
        rule=rule,
        text=clause_text,
        constituents=constituents,
    )


def parse_sentence(
    s_el: ET.Element,
    chapter: int | None = None,
    canonical_versification: bool = True,
    book_code: str | None = None,
    versemap_data: tuple[dict[str, str], set[int], set[int]] | None = None,
) -> VerseRecord:
    """Parse a <sentence> element representing a single verse."""
    sid = s_el.attrib.get("id", "").strip()  # e.g. "GEN 1:1" or "ISA 53:5"
    m = re.match(r"^([0-9A-Za-z]+)\s+(\d+):(\d+)$", sid)
    if not m:
        raise ValueError(f"Malformed sentence ID: '{sid}' (expected 'BOOK c:v')")

    raw_b = m.group(1).upper()
    c_num = int(m.group(2))
    v_num = int(m.group(3))

    b_code = book_code.upper() if book_code else raw_b
    if chapter is not None and c_num != chapter:
        raise ValueError(f"Sentence chapter mismatch: got {c_num}, expected {chapter} in '{sid}'")

    osis_book = MACULA_TO_OSIS.get(b_code, resolve_osis_book(b_code))
    if canonical_versification:
        verse_id, mt_id = map_mt_to_canonical_verse(
            c_num, v_num, book_code=b_code, versemap_data=versemap_data
        )
    else:
        verse_id = f"{osis_book}.{c_num}.{v_num}"
        mt_id = sid

    # Extract verse surface text from <p> milestone
    p_el = s_el.find("p")
    if p_el is not None:
        raw_p = "".join(p_el.itertext())
        verse_text = raw_p.replace(sid, "").strip()
    else:
        # Fallback: combine all <w> tokens
        verse_text = " ".join(w.text or "" for w in s_el.findall(".//w") if w.text)

    clauses: list[ClauseRecord] = []
    for cl in s_el.findall(".//wg[@class='cl']"):
        clauses.append(parse_clause(cl))

    return VerseRecord(
        verse_id=verse_id,
        mt_id=mt_id,
        chapter=c_num,
        verse_num=v_num,
        text=verse_text,
        clauses=clauses,
    )


def merge_verse_records(records: Iterable[VerseRecord]) -> list[VerseRecord]:
    """Merge consecutive VerseRecords that share the same canonical verse_id.

    This preserves complete text, clauses, and token trees when an English KJV
    verse maps to multiple Hebrew sentences (e.g. Num 25:19 + Num 26:1 -> Num 26:1).
    """
    merged: list[VerseRecord] = []
    by_id: dict[str, VerseRecord] = {}

    for rec in records:
        vid = rec.verse_id
        if vid in by_id:
            existing = by_id[vid]
            existing.text = f"{existing.text} {rec.text}".strip()
            existing.mt_id = f"{existing.mt_id}, {rec.mt_id}"
            existing.clauses.extend(rec.clauses)
        else:
            by_id[vid] = rec
            merged.append(rec)
    return merged


def parse_chapter_xml(
    source: str | Path | ET.Element,
    chapter: int | None = None,
    canonical_versification: bool = True,
    book_code: str | None = None,
    versemap_data: tuple[dict[str, str], set[int], set[int]] | None = None,
    merge_multi_sentences: bool = True,
) -> list[VerseRecord]:
    """Parse one Lowfat XML chapter file (e.g. 01-Gen-001-lowfat.xml or 23-Isa-053-lowfat.xml)."""
    if isinstance(source, ET.Element):
        root = source
    else:
        root = ET.parse(source).getroot()

    sentences = root.findall(".//sentence")
    if not sentences:
        ch_label = f" for chapter {chapter}" if chapter is not None else ""
        raise ValueError(f"No <sentence> elements found in Lowfat XML{ch_label}")

    raw_verses: list[VerseRecord] = []
    for s in sentences:
        raw_verses.append(
            parse_sentence(
                s,
                chapter=chapter,
                canonical_versification=canonical_versification,
                book_code=book_code,
                versemap_data=versemap_data,
            )
        )

    if merge_multi_sentences:
        return merge_verse_records(raw_verses)
    return raw_verses


def parse_book_directory(
    macula_dir: str | Path,
    chapters: range | tuple[int, ...] = range(1, 51),
    canonical_versification: bool = True,
) -> list[VerseRecord]:
    """Parse all Genesis chapters in macula_dir in order, returning list of VerseRecords."""
    macula_path = Path(macula_dir)
    all_verses: list[VerseRecord] = []
    for ch in chapters:
        fname = f"01-Gen-{ch:03d}-lowfat.xml"
        file_path = macula_path / fname
        if not file_path.exists():
            raise FileNotFoundError(
                f"Macula Hebrew file missing: {file_path}. "
                "Run scripts/fetch_sources.sh to download pinned data."
            )
        all_verses.extend(
            parse_chapter_xml(
                file_path,
                ch,
                canonical_versification=canonical_versification,
                book_code="GEN",
            )
        )
    return all_verses


def iter_chapter_files(
    macula_dir: str | Path,
    books: Iterable[str] | None = None,
) -> list[Path]:
    """Find all Lowfat XML chapter files in macula_dir in canonical OT sequence."""
    p = Path(macula_dir)
    if not p.is_dir():
        return []

    allowed_osis = {resolve_osis_book(b) for b in books} if books else None

    files: list[tuple[int, int, Path]] = []
    for f in p.glob("*-lowfat.xml"):
        if f.name == "macula-hebrew-lowfat.xml":
            continue
        parts = f.stem.split("-")
        if len(parts) >= 3 and parts[0].isdigit() and parts[2].isdigit():
            book_num = int(parts[0])
            bcode = parts[1].upper()
            osis = MACULA_TO_OSIS.get(bcode, resolve_osis_book(bcode))
            ch_num = int(parts[2])
            if allowed_osis is None or osis in allowed_osis:
                files.append((book_num, ch_num, f))

    files.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in files]


def parse_all_chapters(
    macula_dir: str | Path,
    books: Iterable[str] | None = None,
    canonical_versification: bool = True,
) -> Iterator[VerseRecord]:
    """Stream all VerseRecords across the requested books or whole Old Testament,
    merging multi-sentence verses even across chapter boundaries (e.g. Num 25:19 + Num 26:1).
    """
    vmap_data = get_versification_map() if canonical_versification else None
    pending: VerseRecord | None = None

    for f in iter_chapter_files(macula_dir, books=books):
        verses = parse_chapter_xml(
            f,
            canonical_versification=canonical_versification,
            versemap_data=vmap_data,
            merge_multi_sentences=False,
        )
        for rec in verses:
            if pending is None:
                pending = rec
            elif pending.verse_id == rec.verse_id:
                # Merge into pending
                pending.text = f"{pending.text} {rec.text}".strip()
                pending.mt_id = f"{pending.mt_id}, {rec.mt_id}"
                pending.clauses.extend(rec.clauses)
            else:
                yield pending
                pending = rec

    if pending is not None:
        yield pending
