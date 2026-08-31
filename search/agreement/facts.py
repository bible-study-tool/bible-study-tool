"""Fact model + one adapter per pinned source (S1).

A fact is the atomic comparable unit::

    {"fact_type": ..., "source": ..., "key": ..., "value": ..., "meta": {...}}

Sources (ids are stable and appear in the ledger):
  kjv-osis         scrollmapper tagged KJV   (verse_text, word_strongs)
  oshb             Open Scriptures Hebrew Bible (word_strongs)
  strongs          Strong's lexicon artifact    (lexicon_gloss)
  tbesh / tbesg    STEPBible brief glosses      (lexicon_gloss)

Per-source meta schema (deliberately asymmetric — sources differ; documented
so S4 alignment consumes both knowingly):
  kjv-osis word_strongs meta.words[i] = {i, codes[], text}   (English span)
  oshb      word_strongs meta.words[i] = {i, codes[], text (WLC), morph, id,
                                           n (homonym attr), suffix, prefixes}

Design rules:
  * Adapters REUSE the existing generators' parsers (never re-implement):
    clean_verse_text/verse_codes from build_genesis1, parse_book_xml from
    build_morphology, strongs_definition for gloss extraction.
  * Every adapter is deterministic and fails fast on malformed input (the
    reused parsers already fail fast); adapters additionally enforce their own
    invariants (word-detail vs multiset agreement, skipped-code rejection).
  * Phase-1 scope: Genesis 1 for verse/word facts (documented; whole-OT is a
    later scaling step — the OSHB path is hardcoded to Gen.xml and the
    ADAPTERS callables take only (repo)). Lexicon facts cover the full
    canonical enumeration.
  * The word_strongs value is the verse-level SORTED MULTISET (duplicates
    kept) — segmentation-neutral across sources; per-word detail (ordinals,
    word text, morph) is preserved in meta for the S4 alignment phase.
  * lexicon_gloss values are VERBATIM; extraction status is marked in
    meta['gloss_status']: 'definition' (a real 'N. ...' core line) or
    'no_definition' (the source has no numbered definition — the value is the
    scraper header line, NOT a comparable reading; S2 must emit no_reading for
    these, never disagree). Known set: {H2492, H5774, H7114} ∪ {G2717} ∪
    {G3203..G3302} = 104 codes.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from search.corpus.build_genesis1 import clean_verse_text, verse_codes, strongs_definition
from search.corpus.build_morphology import parse_book_xml

# Stable source ids (appear verbatim in the Agreement Ledger).
KJV_OSIS = "kjv-osis"
OSHB = "oshb"
STRONGS = "strongs"
TBESH = "tbesh"
TBESG = "tbesg"

FACT_VERSE_TEXT = "verse_text"
FACT_WORD_STRONGS = "word_strongs"
FACT_LEXICON_GLOSS = "lexicon_gloss"

# KJV-osis <w> word elements (OSIS tagging of the scrollmapper file).
_W_RE = re.compile(r'<w lemma="([^"]*)"[^>]*>(.*?)</w>', re.DOTALL)


def _fact(fact_type: str, source: str, key: str, value, meta=None) -> dict:
    return {
        "fact_type": fact_type,
        "source": source,
        "key": key,
        "value": value,
        "meta": meta or {},
    }


# --------------------------------------------------------------------------
# kjv-osis adapter
# --------------------------------------------------------------------------

def kjv_osis_facts(repo: str = ".", chapter: int = 1) -> list[dict]:
    """Extract verse_text + word_strongs facts from the pinned tagged KJV.

    Word detail: one meta entry per <w> element (its Strong's tokens — which
    may be multiple per word, e.g. 'strong:H0853 strong:H07200' — and its
    English text span). The verse-level multiset is the fail-fast verse_codes
    expansion so the adapter cannot drift from the corpus generator.
    """
    kjv = json.loads(
        Path(repo, "data/KJV-osis.json").read_text(encoding="utf-8")
    )
    gen = next(b for b in kjv["books"] if b["name"] == "Genesis")
    ch = next(c for c in gen["chapters"] if c["chapter"] == chapter)
    facts: list[dict] = []
    for verse in ch["verses"]:
        v = verse["verse"]
        raw = verse["text"]
        key = f"Gen.{chapter}.{v}"

        text = clean_verse_text(raw)
        codes, occ, skipped = verse_codes(raw)  # fail-fast, attribute-checked
        if skipped:
            raise ValueError(
                f"{key}: non-canonical Strong's codes {skipped} — source changed; "
                "regenerate after review."
            )
        multiset = sorted(c for c, n in occ.items() for _ in range(n))

        words = []
        for i, m in enumerate(_W_RE.finditer(raw), start=1):
            word_codes = [
                f"{letter}{int(num)}"
                for letter, num in re.findall(r"strong:([HG])(\d{4,5})", m.group(1))
            ]
            words.append(
                {
                    "i": i,
                    "codes": word_codes,
                    # Unescaped to match clean_verse_text's entity handling.
                    "text": html.unescape(m.group(2)).strip(),
                }
            )

        # Two-path invariant: the <w> word-detail path and the verse_codes
        # regex path must agree exactly, or the multiset and meta would
        # silently diverge on a future re-pin (e.g. attribute reordering).
        flat = sorted(c for w in words for c in w["codes"])
        if flat != multiset:
            raise ValueError(
                f"{key}: word detail {flat} disagrees with verse multiset {multiset}"
            )

        facts.append(_fact(FACT_VERSE_TEXT, KJV_OSIS, key, text))
        facts.append(
            _fact(
                FACT_WORD_STRONGS,
                KJV_OSIS,
                key,
                multiset,
                {"word_count": len(words), "words": words},
            )
        )
    return facts


# --------------------------------------------------------------------------
# oshb adapter
# --------------------------------------------------------------------------

def oshb_facts(repo: str = ".", chapter: int = 1) -> list[dict]:
    """Extract word_strongs facts from the OSHB morphology layer.

    Reuses parse_book_xml (same parser as the committed morphology artifact —
    the adapter cannot disagree with it). The verse multiset contains every
    word's base Strong's number (prefix-only words contribute word detail but
    no code; prefix chains are ETCBC morphemes, not Strong's numbers).
    """
    records = parse_book_xml(str(Path(repo) / "data/oshb/Gen.xml"), chapter)
    by_verse: dict[str, list[dict]] = {}
    for rec in records:
        by_verse.setdefault(rec["osisID"], []).append(rec)

    facts: list[dict] = []
    for osis_id in sorted(by_verse, key=lambda k: int(k.rsplit(".", 1)[1])):
        words = by_verse[osis_id]
        multiset = sorted(r["base"] for r in words if r["base"])
        meta_words = [
            {
                "i": i,
                "codes": ([r["base"]] if r["base"] else []),
                "text": r["wlc"],
                "morph": r["morph"],
                "id": r["id"],
                "n": r["n"],
                "suffix": r["suffix"],
                "prefixes": r["prefixes"],
            }
            for i, r in enumerate(words, start=1)
        ]
        facts.append(
            _fact(
                FACT_WORD_STRONGS,
                OSHB,
                osis_id,
                multiset,
                {"word_count": len(words), "words": meta_words},
            )
        )
    return facts


# --------------------------------------------------------------------------
# lexicon adapters
# --------------------------------------------------------------------------

def _load_lexicon(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {**payload.get("hebrew", {}), **payload.get("greek", {})}


def strongs_gloss_facts(repo: str = ".") -> list[dict]:
    """lexicon_gloss facts from the Strong's lexicon artifact.

    Gloss = the core '1. ...' definition line (same extraction the corpus
    generator uses, so the ledger cannot drift from the entries). Entries
    whose desc has NO numbered definition (104 known codes — scraper headers
    without content) carry meta['gloss_status'] = 'no_definition' so S2 emits
    no_reading instead of manufacturing a nonsense disagreement.
    """
    lex = _load_lexicon(Path(repo) / "lexicons/strongs-lexicon.json")
    facts = []
    for code, entry in sorted(lex.items()):
        has_definition = any(
            re.match(r"^\d+\.", ln.strip())
            for ln in entry.get("desc", "").splitlines()
        )
        facts.append(
            _fact(
                FACT_LEXICON_GLOSS,
                STRONGS,
                code,
                strongs_definition(entry),
                {"gloss_status": "definition" if has_definition else "no_definition"},
            )
        )
    return facts


def _stepbible_gloss_facts(source_id: str, filename: str, repo: str) -> list[dict]:
    payload = json.loads(
        (Path(repo) / "lexicons" / filename).read_text(encoding="utf-8")
    )
    entries = payload.get("entries", {})
    facts = []
    for code in sorted(entries):
        variants = entries[code]
        # Primary-record convention (file order [0]), matching the corpus
        # generator so both layers read the same gloss for the same code.
        # Strict access: a missing gloss key is a data error, not an empty
        # reading (the codebase's fail-fast religion).
        gloss = variants[0]["gloss"]
        facts.append(_fact(FACT_LEXICON_GLOSS, source_id, code, gloss))
    return facts


def tbesh_gloss_facts(repo: str = ".") -> list[dict]:
    return _stepbible_gloss_facts(TBESH, "tbesh-glosses.json", repo)


def tbesg_gloss_facts(repo: str = ".") -> list[dict]:
    return _stepbible_gloss_facts(TBESG, "tbesg-glosses.json", repo)


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

ADAPTERS = {
    KJV_OSIS: kjv_osis_facts,
    OSHB: oshb_facts,
    STRONGS: strongs_gloss_facts,
    TBESH: tbesh_gloss_facts,
    TBESG: tbesg_gloss_facts,
}


def collect_all(repo: str = ".") -> dict[str, list[dict]]:
    """Run every adapter. Returns {source_id: [fact, ...]} in deterministic
    (adapter-defined) order."""
    return {source: adapter(repo) for source, adapter in ADAPTERS.items()}


def index_facts(all_facts: dict[str, list[dict]]) -> dict[str, dict[str, dict[str, dict]]]:
    """Index facts for comparison: {fact_type: {key: {source: fact}}}.

    Raises ValueError on duplicate (source, fact_type, key) — a duplicated
    fact would silently skew agreement counts.
    """
    index: dict[str, dict[str, dict[str, dict]]] = {}
    for source, facts in all_facts.items():
        for fact in facts:
            bucket = index.setdefault(fact["fact_type"], {}).setdefault(fact["key"], {})
            if fact["source"] in bucket:
                raise ValueError(
                    f"duplicate fact: {fact['source']} {fact['fact_type']} {fact['key']}"
                )
            bucket[fact["source"]] = fact
    return index