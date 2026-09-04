"""Lowfat XML parser and linguistic extractor for Clear-Bible Macula Greek (NT).

Extracts token-level linguistic attributes (Greek Strong's G1-G5624, Greek lemmas,
morphology, glosses, Louw-Nida semantic domains) and syntactic structure (clause
rules, phrase constituents, and participant roles: Subject, Predicate Verb, Object,
Indirect Object, Prepositional Phrase, Adjunct) across all 27 New Testament books.
"""

from __future__ import annotations

from itertools import groupby
from pathlib import Path
import re
from typing import Any, Iterable, Iterator
import xml.etree.ElementTree as ET

from search.macula.extract import (
    ROLE_LABELS,
    ClauseRecord,
    ConstituentRecord,
    TokenRecord,
    VerseRecord,
    merge_verse_records,
    normalize_greek_strongs,
)

# Canonical 27 New Testament books: Macula lowfat XML abbreviation -> OSIS code
GREEK_MACULA_TO_OSIS: dict[str, str] = {
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

OSIS_TO_GREEK_MACULA: dict[str, str] = {v: k for k, v in GREEK_MACULA_TO_OSIS.items()}

from search.corpus.bible_books import NT_BOOKS as NT_CANONICAL_ORDER


def parse_greek_token(w_el: ET.Element, default_role: str = "") -> TokenRecord:
    """Parse a single Greek <w> element into a TokenRecord."""
    wid = w_el.attrib.get(
        "{http://www.w3.org/XML/1998/namespace}id",
        w_el.attrib.get("xml:id", w_el.attrib.get("id", w_el.attrib.get("ref", ""))),
    )
    raw_s = w_el.attrib.get("strong")
    norm_s = None
    if raw_s:
        # Compound Strong's codes (e.g. '1501+5140') take the primary head code
        p0 = raw_s.split("+")[0].strip()
        norm_s = normalize_greek_strongs(p0)

    role = w_el.attrib.get("role") or default_role or ""
    domain = w_el.attrib.get("domain", "")
    core_domains = domain.split() if domain else []

    ln = w_el.attrib.get("ln", "")
    lex_domains = ln.split() if ln else []

    return TokenRecord(
        id=wid,
        text=w_el.text or "",
        lemma=w_el.attrib.get("lemma", ""),
        strongs=norm_s,
        raw_strongs=raw_s,
        lxx_strongs=None,
        lxx=None,
        gloss=w_el.attrib.get("gloss", ""),
        pos=w_el.attrib.get("class", ""),
        morph=w_el.attrib.get("morph", ""),
        role=role,
        sdbh=None,
        core_domains=core_domains,
        lex_domains=lex_domains,
    )


def parse_greek_sentence(s_el: ET.Element, book_osis: str) -> list[VerseRecord]:
    """Parse a single <sentence> element that may span one or more verses.

    Accurately maps Greek Lowfat XML syntax trees to canonical Protestant verses:
    - Multi-verse sentences (e.g. Matt 1:2-6, Rom 1:1-7) are partitioned by token reference.
    - Container clauses (e.g. Conj-CL, Conj3CL, CLaCL) and subordinate wrappers (sub-CL)
      are resolved into clean syntactic predications.
    - Conjunctions (class='conj') are preserved in reading order with role 'cjp'.
    - Participial/relative clauses embedded in noun phrases (DetCL) remain constituents
      of their governing phrase.
    """
    w_list = s_el.findall(".//w")
    if not w_list:
        return []

    parent_map = {c: p for p in s_el.iter() for c in p}

    tokens_by_v: dict[str, list[ET.Element]] = {}
    for w in w_list:
        ref = w.attrib.get("ref", "")
        if ref:
            v_key = ref.split("!")[0]
            tokens_by_v.setdefault(v_key, []).append(w)

    cl_node_cache: dict[ET.Element, bool] = {}

    def is_phrase(el: ET.Element) -> bool:
        return el.tag == "wg" and el.attrib.get("class") in ("np", "pp", "advp", "adjp")

    def is_cl_node(el: ET.Element) -> bool:
        if el in cl_node_cache:
            return cl_node_cache[el]
        if el.tag != "wg" or el.attrib.get("class") != "cl":
            cl_node_cache[el] = False
            return False
        curr = parent_map.get(el)
        while curr is not None:
            if is_phrase(curr):
                cl_node_cache[el] = False
                return False
            curr = parent_map.get(curr)
        cl_node_cache[el] = True
        return True

    container_cache: dict[ET.Element | None, bool] = {None: True}

    def is_container_cl(cl: ET.Element | None) -> bool:
        if cl in container_cache:
            return container_cache[cl]
        rule = cl.attrib.get("rule", "")
        res = False
        if rule.startswith("Conj") or rule in ("CLaCL", "sub-CL"):
            res = any(c != cl and is_cl_node(c) for c in cl.iter())
        container_cache[cl] = res
        return res

    def get_target_cl(w: ET.Element) -> ET.Element | None:
        curr = parent_map.get(w)
        while curr is not None:
            if is_cl_node(curr):
                return curr
            curr = parent_map.get(curr)
        return None

    verse_records: list[VerseRecord] = []
    for v_key, v_tokens in tokens_by_v.items():
        v_parts = v_key.split()
        ref_part = v_parts[1] if len(v_parts) > 1 else v_parts[0]
        c_v = ref_part.split(":")
        ch = int(c_v[0]) if len(c_v) > 0 and c_v[0].isdigit() else 1
        vs = int(c_v[1]) if len(c_v) > 1 and c_v[1].isdigit() else 1
        verse_id = f"{book_osis}.{ch}.{vs}"

        v_tokens_sorted = sorted(
            v_tokens,
            key=lambda w: int(w.attrib["ref"].split("!")[1]) if "!" in w.attrib.get("ref", "") else 0,
        )
        verse_text = "".join(
            (w.text or "") + (w.attrib.get("after") if "after" in w.attrib else " ")
            for w in v_tokens_sorted
        ).strip()

        raw_map = [get_target_cl(w) for w in v_tokens_sorted]

        final_cl_map: list[ET.Element | None] = []
        for i, (w, cl) in enumerate(zip(v_tokens_sorted, raw_map)):
            if is_container_cl(cl):
                target = None
                for next_cl in raw_map[i + 1 :]:
                    if not is_container_cl(next_cl):
                        target = next_cl
                        break
                if target is None:
                    for prev_cl in reversed(raw_map[:i]):
                        if not is_container_cl(prev_cl):
                            target = prev_cl
                            break
                final_cl_map.append(target if target is not None else cl)
            else:
                final_cl_map.append(cl)

        clauses: list[ClauseRecord] = []
        for cl, group in groupby(zip(v_tokens_sorted, final_cl_map), key=lambda x: x[1]):
            cl_toks = [x[0] for x in group]
            cl_rule = cl.attrib.get("rule", "") if cl is not None else ""

            const_groups: list[tuple[str, str, str, list[ET.Element]]] = []
            curr_const_key: Any = None
            curr_const_toks: list[ET.Element] = []
            curr_role = ""
            curr_cls = ""
            curr_rule = ""

            for w in cl_toks:
                w_class = w.attrib.get("class", "")
                if w_class == "conj":
                    target_role = "cjp"
                    target_cls = "conj"
                    target_rule = ""
                    target_el = w
                else:
                    target_role = w.attrib.get("role", "")
                    target_cls = w_class
                    target_rule = ""
                    target_el = w

                    curr = parent_map.get(w)
                    while curr is not None and curr != cl and curr != s_el:
                        if curr.attrib.get("role"):
                            target_role = curr.attrib["role"]
                            target_cls = curr.attrib.get("class", target_cls)
                            target_rule = curr.attrib.get("rule", "")
                            target_el = curr
                        elif curr.tag == "wg" and not target_role:
                            target_cls = curr.attrib.get("class", target_cls)
                            target_rule = curr.attrib.get("rule", target_rule)
                            target_el = curr
                        curr = parent_map.get(curr)

                    if not target_role:
                        if w_class == "prep":
                            target_role = "prep"
                        else:
                            target_role = "phrase"

                key = (target_el, target_role)
                if key != curr_const_key:
                    if curr_const_toks:
                        const_groups.append((curr_role, curr_cls, curr_rule, curr_const_toks))
                    curr_const_key = key
                    curr_const_toks = [w]
                    curr_role = target_role
                    curr_cls = target_cls
                    curr_rule = target_rule
                else:
                    curr_const_toks.append(w)

            if curr_const_toks:
                const_groups.append((curr_role, curr_cls, curr_rule, curr_const_toks))

            constituents: list[ConstituentRecord] = []
            for role, p_cls, rule, c_toks in const_groups:
                tok_records = [parse_greek_token(w, default_role=role) for w in c_toks]
                label = ROLE_LABELS.get(role.lower(), role)
                c_text = " ".join(t.text for t in tok_records if t.text)
                constituents.append(
                    ConstituentRecord(
                        role=role,
                        role_label=label,
                        phrase_class=p_cls or "phrase",
                        rule=rule,
                        text=c_text,
                        tokens=tok_records,
                    )
                )

            cl_text = " ".join(c.text for c in constituents if c.text)
            if not cl_rule:
                meaningful_roles = [
                    c.role.upper()
                    for c in constituents
                    if c.role not in ("cjp", "phrase", "prep")
                ]
                cl_rule = "-".join(meaningful_roles) if meaningful_roles else "CL"
            clauses.append(ClauseRecord(rule=cl_rule, text=cl_text, constituents=constituents))

        verse_records.append(
            VerseRecord(
                verse_id=verse_id,
                mt_id=v_key,
                chapter=ch,
                verse_num=vs,
                text=verse_text,
                clauses=clauses,
            )
        )

    return verse_records


def parse_greek_book(xml_path: str | Path, osis_book: str | None = None) -> list[VerseRecord]:
    """Parse an entire Greek NT Lowfat XML book file into canonical VerseRecords."""
    p = Path(xml_path)
    if not p.is_file():
        raise FileNotFoundError(f"Greek Lowfat XML book missing at {p}")

    tree = ET.parse(p)
    root = tree.getroot()
    raw_id = root.attrib.get("id", "").upper()
    book_osis = osis_book or GREEK_MACULA_TO_OSIS.get(raw_id, raw_id)

    raw_records: list[VerseRecord] = []
    for s_el in root.findall(".//sentence"):
        s_records = parse_greek_sentence(s_el, book_osis=book_osis)
        raw_records.extend(s_records)

    # Merge any sentences sharing the same verse ID (e.g. Matt.1.6)
    return merge_verse_records(raw_records)


def parse_all_greek_books(
    xml_dir: str | Path = "data/macula-greek",
    books: Iterable[str] | None = None,
) -> Iterator[VerseRecord]:
    """Stream-parse all 27 New Testament books in canonical Protestant order."""
    root = Path(xml_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Greek Lowfat XML directory missing at {root}")

    allowed_books: set[str] | None = None
    if books is not None:
        from search.macula.extract import resolve_osis_book
        allowed_books = {resolve_osis_book(b) for b in books}

    # Map available files by canonical OSIS
    files_by_osis: dict[str, Path] = {}
    for xml_file in root.glob("[0-9]*.xml"):
        m = re.match(r"^(\d+)-([a-z0-9]+)\.xml$", xml_file.name.lower())
        if m:
            num = int(m.group(1))
            if 1 <= num <= 27:
                osis = NT_CANONICAL_ORDER[num - 1]
                files_by_osis[osis] = xml_file

    for osis in NT_CANONICAL_ORDER:
        if allowed_books is not None and osis not in allowed_books:
            continue
        if osis not in files_by_osis:
            continue

        xml_path = files_by_osis[osis]
        records = parse_greek_book(xml_path, osis_book=osis)
        for rec in records:
            yield rec
