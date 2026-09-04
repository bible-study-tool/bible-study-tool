"""Lowfat XML parser and linguistic extractor for Clear-Bible Macula Hebrew.

Extracts token-level linguistic attributes (Hebrew Strong's, Greek LXX Strong's,
SDBH semantic domains, glosses, morphology) and syntactic structure (sentence,
clause rules, phrases, and participant roles: Subject, Predicate, Object,
Prepositional Phrase, Adjunct) using Python standard library ElementTree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import xml.etree.ElementTree as ET

_HEBREW_RE = re.compile(r"^[Hh]?0*(\d+)[a-zA-Z]?$")
_GREEK_RE = re.compile(r"^[Gg]?0*(\d+)[a-zA-Z]?$")

ROLE_LABELS: dict[str, str] = {
    "s": "subject",
    "v": "predicate_verb",
    "o": "object",
    "o2": "indirect_object",
    "p": "predicate",
    "pp": "prepositional_phrase",
    "adv": "adverbial",
    "cjp": "conjunction_phrase",
    "voc": "vocative",
    "cl": "clause",
}

ROLE_ALIASES: dict[str, tuple[str, str]] = {
    "s": ("s", "subject"),
    "subj": ("s", "subject"),
    "subject": ("s", "subject"),
    "v": ("v", "predicate_verb"),
    "verb": ("v", "predicate_verb"),
    "predicate_verb": ("v", "predicate_verb"),
    "pred_verb": ("v", "predicate_verb"),
    "o": ("o", "object"),
    "obj": ("o", "object"),
    "object": ("o", "object"),
    "o2": ("o2", "indirect_object"),
    "iobj": ("o2", "indirect_object"),
    "indirect_object": ("o2", "indirect_object"),
    "p": ("p", "predicate"),
    "pred": ("p", "predicate"),
    "predicate": ("p", "predicate"),
    "pp": ("pp", "prepositional_phrase"),
    "prep": ("pp", "prepositional_phrase"),
    "prepositional_phrase": ("pp", "prepositional_phrase"),
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


def map_mt_to_canonical_verse(chapter: int, verse_num: int) -> tuple[str, str]:
    """Map Masoretic Text (MT) chapter:verse to canonical KJV corpus reference.

    Genesis 31-32 has traditional versification differences between MT and KJV:
      - MT Gen 32:1 -> KJV Gen 31:55
      - MT Gen 32:2..33 -> KJV Gen 32:1..32

    Returns (canonical_ref, mt_ref) e.g. ('Gen.31.55', 'GEN 32:1').
    """
    mt_ref = f"GEN {chapter}:{verse_num}"
    if chapter == 32 and verse_num == 1:
        return "Gen.31.55", mt_ref
    elif chapter == 32 and verse_num > 1:
        return f"Gen.32.{verse_num - 1}", mt_ref
    return f"Gen.{chapter}.{verse_num}", mt_ref


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
    s_el: ET.Element, chapter: int, canonical_versification: bool = True
) -> VerseRecord:
    """Parse a <sentence> element representing a single verse."""
    sid = s_el.attrib.get("id", "")  # e.g. "GEN 1:1"
    # Extract verse number from id
    parts = sid.replace("GEN ", "").split(":")
    if len(parts) != 2:
        raise ValueError(f"Malformed sentence ID: '{sid}' (expected 'GEN c:v')")
    c_num = int(parts[0])
    v_num = int(parts[1])
    if chapter is not None and c_num != chapter:
        raise ValueError(f"Sentence chapter mismatch: got {c_num}, expected {chapter} in '{sid}'")

    if canonical_versification:
        verse_id, mt_id = map_mt_to_canonical_verse(c_num, v_num)
    else:
        verse_id = f"Gen.{c_num}.{v_num}"
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


def parse_chapter_xml(
    source: str | Path | ET.Element, chapter: int, canonical_versification: bool = True
) -> list[VerseRecord]:
    """Parse one Lowfat XML chapter file (e.g. 01-Gen-001-lowfat.xml)."""
    if isinstance(source, ET.Element):
        root = source
    else:
        root = ET.parse(source).getroot()

    sentences = root.findall(".//sentence")
    if not sentences:
        raise ValueError(f"No <sentence> elements found in Lowfat XML for chapter {chapter}")

    verses: list[VerseRecord] = []
    for s in sentences:
        verses.append(parse_sentence(s, chapter, canonical_versification=canonical_versification))
    return verses


def parse_book_directory(
    macula_dir: str | Path,
    chapters: range | tuple[int, ...] = range(1, 51),
    canonical_versification: bool = True,
) -> list[VerseRecord]:
    """Parse all chapters in macula_dir in order, returning list of VerseRecords."""
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
        all_verses.extend(parse_chapter_xml(file_path, ch, canonical_versification=canonical_versification))
    return all_verses
