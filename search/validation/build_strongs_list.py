"""Generate the canonical Strong's list from a Bible-with-Strong's source.

F2's canonical-list check needs an authoritative set of real Strong's
numbers. A clean, MIT-licensed source is scrollmapper/bible_databases
(https://github.com/scrollmapper/bible_databases) — its KJV translation ships
with Strong's numbers and morphology.

This script extracts every distinct Strong's number actually attested in a
source file and writes ``lexicons/strongs-list.json`` with shape:
    {"hebrew": ["H7225", ...], "greek": ["G2532", ...]}

Usage:
    python -m search.validation.build_strongs_list --input kjv.json --out lexicons/strongs-list.json

Input formats supported (auto-detected by extension):
  * JSON: a list of verse objects, each with a ``text`` field containing
    Strong's markup. Two conventions are recognised:
      - ``<H7225>word</H7225>`` / ``<G2532>word</G2532>`` (scrollmapper OSIS-like)
      - ``strong:H7225`` inline tokens
  * TXT: plain text containing ``<H7225>`` or ``<G2532>`` tags.

The list of Strong's *numbers* is a set of public-domain facts; extraction here
carries no text and so is clean from a licensing standpoint (NOTICE.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Scrollmapper KJV uses OSIS-style tags: <H7225>...</H7225>, <G2532>...</G2532>
_OSIS_RE = re.compile(r"<(H|G)\d{1,4}>")
# Generic token form: <H7225> / <G2532> anywhere in text
_TOKEN_RE = re.compile(r"<([HG]\d{1,4})>")


def extract_from_json(path: Path, text_field: str = "text") -> set[str]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        # Some dumps are {"verses": [...]}
        data = data.get("verses", [])
    codes: set[str] = set()
    for verse in data:
        text = verse.get(text_field, "") if isinstance(verse, dict) else str(verse)
        for m in _TOKEN_RE.finditer(text):
            codes.add(m.group(1))
    return codes


def extract_from_text(path: str) -> set[str]:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    codes: set[str] = set()
    for m in _TOKEN_RE.finditer(text):
        codes.add(m.group(1))
    return codes


def extract_from_file(path: str) -> set[str]:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return extract_from_json(path)
    return extract_from_text(path)


def split_hebrew_greek(codes: set[str]) -> tuple[list[str], list[str]]:
    hebrew = sorted(c for c in codes if c.startswith("H"))
    greek = sorted(c for c in codes if c.startswith("G"))
    return hebrew, greek


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate canonical Strong's number list")
    parser.add_argument("--file", required=True, help="Source Bible-with-Strong's file (JSON or TXT)")
    parser.add_argument("--out", default="lexicons/strongs-list.json", help="Output JSON path")
    args = parser.parse_args(argv)

    codes = extract_from_file(args.file)
    hebrew, greek = split_hebrew_greek(codes)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "$schema": "strongs-list/v1",
        "source": "extracted from {file}".format(file=args.file),
        "hebrew_count": len(hebrew),
        "greek_count": len(greek),
        "hebrew": hebrew,
        "greek": greek,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(hebrew)} Hebrew + {len(greek)} Greek Strong's numbers to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())