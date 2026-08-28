"""Generate the canonical Strong's lexicon from the Go concordance data.

The data/strongs/*.go files (from gmlewis/bible-codes/strongs, see
data/strongs/strongs.go) are the authoritative Strong's concordance: 8674
Hebrew + 5624 Greek entries, each with Num, Word, transliteration, and a Desc
with definition + KJV usage. This matches the canonical maxima exactly.

Outputs two files:
  lexicons/strongs-list.json        -- the set of valid Strong's codes (H####/G####)
                                       used by F2 for canonical verification.
  lexicons/strongs-lexicon.json     -- the full dictionary (number -> word,
                                       transliteration, definition) for study
                                       use (ROADMAP A4).

Strong's *numbers* and *definitions* are public-domain facts (the original
Strong's concordance is in the public domain). No Bible verse text is copied.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Matches an entry line:
#   "אב": &Entry{Num: 1, Word: "אָב", Length: 2, Desc: "..."},
#   OR a commented-out duplicate:
#   // "אב": // DUP - SEE ABOVE // &Entry{Num: 2, Word: "אַב", ...},
_ENTRY_RE = re.compile(
    r'&Entry\{Num:\s*(\d+),\s*Word:\s*"([^"]*)",\s*Length:\s*\d+,\s*Desc:\s*"((?:[^"\\]|\\.)*)"\s*\}',
)

# NOTE on "commented-out duplicates": the Go source comments out entries whose
# Hebrew/Greek spelling KEY collides with an earlier entry (the Go map can only
# hold one entry per key). These are NOT invalid — each is a distinct, valid
# Strong's number with its own definition (e.g. H2 'ab is the Aramaic "father",
# distinct from H1 'ab). Stripping them would drop ~1900 valid Hebrew and ~100
# valid Greek numbers and break the canonical 8674/5624 totals that F2's bounds
# (max H8674 / G5624) depend on. Therefore we keep ALL entries and rely on the
# numbers themselves being unique. There are no true duplicate NUMBERS in the
# data (verified: real ∩ commented = empty).

# Transliteration is the FIRST parenthetical on the headword line, i.e. the one
# immediately after the headword that follows the colon. Anchored to the colon
# so we do not accidentally match a KJV-usage or root parenthetical later in
# the desc (which the previous unanchored `[A-Za-z]+\(...\)` regex did — e.g.
# it grabbed 'me' from "KJV: I (me) beseech" for H577). Handles headwords that
# start with apostrophe ('eb), are multi-word (ei me ti), are empty, or contain
# HTML-escaped Greek.
_TRANSLIT_RE = re.compile(r":\s*([^:\n]*?)\(([^)]*)\)")


def _clean_desc(desc: str) -> str:
    # Desc is Go-escaped; unescape common entities and escapes.
    desc = desc.replace("&apos;", "'").replace("&quot;", '"').replace("&amp;", "&")
    desc = re.sub(r"&#0*(\d+);", lambda m: chr(int(m.group(1))), desc)  # numeric entities
    desc = desc.replace('\\"', '"').replace("\\n", "\n").replace("\\'", "'")
    return desc.strip()


def parse_go_file(path: str) -> dict[int, dict]:
    """Parse a strongs/*.go file into {num: {word, translit, definition}}.

    Every `&Entry{...}` line is captured, including the ones the Go source
    comments out as "DUP - SEE ABOVE" (they are distinct valid Strong's numbers
    that merely share a spelling key). Keeps the full canonical 8674 Hebrew /
    5624 Greek enumeration that F2's bounds depend on.
    """
    content = Path(path).read_text(encoding="utf-8")
    entries: dict[int, dict] = {}
    for m in _ENTRY_RE.finditer(content):
        num = int(m.group(1))
        word = m.group(2)
        desc = _clean_desc(m.group(3))
        # Extract transliteration: the first parenthetical on the headword line
        # (anchored to the colon so KJV/root parentheticals later in the desc
        # are not matched). A few headwords carry variant notation in nested
        # parens (e.g. "(el-o'-ah; rarely (shortened) ...)"); the primary
        # transliteration is the text before the first ';'. No legitimate
        # transliteration in the source contains ';' (verified: the only 5
        # occurrences were all bleed artifacts), so trimming there is safe.
        translit = ""
        tmatch = _TRANSLIT_RE.search(desc)
        if tmatch:
            translit = tmatch.group(2).strip()
            if ";" in translit:
                translit = translit.split(";", 1)[0].strip()
        entries[num] = {"num": num, "word": word, "translit": translit, "desc": desc}
    return entries


def build(hebrew_file: str, greek_file: str, out_dir: str) -> None:
    hebrew = parse_go_file(hebrew_file)
    greek = parse_go_file(greek_file)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Canonical list (for F2): just the set of valid codes.
    list_payload = {
        "$schema": "strongs-list/v1",
        "source": "generated from data/strongs (gmlewis/bible-codes/strongs)",
        "hebrew_count": len(hebrew),
        "greek_count": len(greek),
        "hebrew": [f"H{n}" for n in sorted(hebrew)],
        "greek": [f"G{n}" for n in sorted(greek)],
    }
    list_path = out / "strongs-list.json"
    list_path.write_text(json.dumps(list_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Full lexicon (for A4 study use).
    lexicon_payload = {
        "$schema": "strongs-lexicon/v1",
        "source": "generated from data/strongs (gmlewis/bible-codes/strongs)",
        "hebrew": {f"H{n}": v for n, v in sorted(hebrew.items())},
        "greek": {f"G{n}": v for n, v in sorted(greek.items())},
    }
    lexicon_path = out / "strongs-lexicon.json"
    lexicon_path.write_text(json.dumps(lexicon_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(hebrew)} Hebrew + {len(greek)} Greek Strong's codes to:")
    print(f"  {list_path}")
    print(f"  {lexicon_path}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate canonical Strong's lexicon")
    parser.add_argument("--hebrew", default="data/strongs/hebrew.go")
    parser.add_argument("--greek", default="data/strongs/greek.go")
    parser.add_argument("--out-dir", default="lexicons")
    args = parser.parse_args(argv)

    build(args.hebrew, args.greek, args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())