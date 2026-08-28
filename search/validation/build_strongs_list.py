"""Extract the set of Strong's numbers ATTESTED in a Bible-with-Strong's text.

NOTE — this is NOT the generator for ``lexicons/strongs-list.json``. The
canonical list used by F2 is the FULL Strong's enumeration (8674 Hebrew +
5624 Greek) and is produced by ``build_strongs_lexicon.py`` from the pinned
gmlewis/bible-codes concordance (see ``data/PROVENANCE.md``).

This script instead extracts the *attestation subset*: every distinct Strong's
number actually tagged in a source text. The tagged KJV attests 14,089 codes
(8,674 H + 5,415 G) — 209 valid Greek numbers are unattested and would be
missing, so its output must never overwrite the canonical list. Its uses are
usage-count analysis, attestation cross-checks, and cross-reference work.

Usage:
    python -m search.validation.build_strongs_list --input kjv.json --out attestations.json

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