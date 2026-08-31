"""Generate the deterministic Hebrew morphology layer from OSHB XML.

Source: Open Scriptures Hebrew Bible v2.2 (CC BY 4.0, pinned in
data/PROVENANCE.md; extracted per-book XML in data/oshb/). This generator
parses the OSIS <w> word elements for Genesis 1 and emits
``lexicons/morphology-genesis1.json`` — the word-level Morphology+Lemma layer
that sits directly above the base text and Strong's numbers:

  * WLC Hebrew word text (verbatim, including maqqef joins)
  * OSHB lemma VERBATIM, plus a decomposition:
      - prefix chain  (e.g. 'c/l/3117' -> ['c', 'l']  = conjunction + prep)
      - base Strong's number (normalized to canonical 'H####')
      - suffix marker (e.g. '1254 a' -> 'a')
      - prefix-only words (e.g. lemma 'b') carry no base number
  * ETCBC morphology code (e.g. 'HVqp3ms' = Hebrew verb qal perfect 3ms)
  * OSHB stable word id (persistent identifier, unique within the file)
  * OSHB 'n' attribute (homonym/gloss number), verbatim when present

Determinism: output is a pure function of the pinned XML + the committed
canonical Strong's list; no timestamps. Integrity: every decomposed base
number must exist in lexicons/strongs-list.json — an unknown number fails the
build (a silent miss would corrupt the deterministic base).

ATTRIBUTION (CC BY 4.0): Open Scriptures Hebrew Bible Project
(https://hb.openscriptures.org). Changes made here are recorded in the
artifact's `changes_recorded` (reformatting only; data unchanged).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

OSIS_NS = {"osis": "http://www.bibletechnologies.net/2003/OSIS/namespace"}

# Optional space-letter suffix at the very end (e.g. '1254 a').
_LEMMA_SUFFIX_RE = re.compile(r"^(?P<head>.*?)(?:\s+(?P<suffix>[a-z]))?$")

# ETCBC/OSHB morphology code shape: 'H' + letters/digits/slashes.
# (Hebrew entries only; if scope ever widens, Aramaic words use 'A'-prefixed
# codes — e.g. the two Aramaic words at Gen 31:47, morph 'ANp' — and would
# need their own branch.)
_MORPH_RE = re.compile(r"^H[A-Za-z0-9/]+$")

# A single prefix/segment: 1-2 lowercase letters (ETCBC preformat morphemes).
_SEGMENT_RE = re.compile(r"^[a-z]{1,2}$")


def decompose_lemma(lemma: str) -> dict:
    """Decompose an OSHB lemma into prefixes / base / suffix (verbatim kept).

    Forms handled (all observed in the pinned Genesis data):
      '7225'      -> base H7225
      'b/7225'    -> prefixes [b], base H7225
      'c/l/3117'  -> prefixes [c, l], base H3117
      '1254 a'    -> base H1254, suffix 'a'
      'c/l/4723 c'-> prefixes [c, l], base H4723, suffix 'c'
      'b', 'c'    -> prefix-only word (no base number)
    Returns {"lemma": ..., "prefixes": [...], "base": "H####"|None, "suffix": str|None}.
    Raises ValueError on unrecognized forms (fail-fast, no silent drops).
    """
    m = _LEMMA_SUFFIX_RE.match(lemma)
    suffix = m.group("suffix")
    head = m.group("head")
    if " " in head:
        # e.g. '1254 a b' — multiple trailing tokens would decompose
        # ambiguously; fail fast rather than guess.
        raise ValueError(f"unrecognized OSHB lemma (multi-token head): {lemma!r}")
    parts = head.split("/")
    prefixes: list[str] = []
    base: str | None = None
    for part in parts:
        if part.isdigit():
            if base is not None:
                raise ValueError(f"unrecognized OSHB lemma (two numeric parts): {lemma!r}")
            base = f"H{int(part)}"
        elif _SEGMENT_RE.match(part):
            prefixes.append(part)
        else:
            raise ValueError(f"unrecognized OSHB lemma form: {lemma!r}")
    return {
        "lemma": lemma,
        "prefixes": prefixes,
        "base": base,
        "suffix": suffix,
    }


def parse_book_xml(path: str, chapter: int) -> list[dict]:
    """Parse one OSHB book XML and return word records for one chapter, in order.

    Selects exactly ``Book.CHAPTER.N`` verses (e.g. Gen.1.1..Gen.1.31) and
    iterates their <w> children in document order. Raises ValueError if any
    word has a malformed morphology code, an unrecognized lemma form, or empty
    text (all would silently corrupt the layer).
    """
    root = ET.parse(path).getroot()
    records: list[dict] = []
    prefix = f"Gen.{chapter}"
    for verse in root.iter(f"{{{OSIS_NS['osis']}}}verse"):
        osis_id = verse.get("osisID", "")
        if osis_id != prefix and not osis_id.startswith(prefix + "."):
            continue
        for w in verse.iter(f"{{{OSIS_NS['osis']}}}w"):
            lemma = w.get("lemma", "")
            morph = w.get("morph", "")
            wid = w.get("id", "")
            n_attr = w.get("n")
            if not _MORPH_RE.match(morph):
                raise ValueError(f"{path}: word id {wid}: malformed morph {morph!r}")
            decomp = decompose_lemma(lemma)
            text = (w.text or "").strip()
            if not text:
                raise ValueError(f"{path}: word id {wid}: empty WLC text")
            records.append(
                {
                    "id": wid,
                    "osisID": osis_id,
                    "wlc": text,
                    "morph": morph,
                    "n": n_attr,
                    **decomp,
                }
            )
    return records


def build(repo: str = ".", oshb_dir: str | None = None, out_dir: str = "lexicons") -> dict:
    oshb_path = Path(oshb_dir) if oshb_dir else Path(repo) / "data/oshb"
    gen_xml = oshb_path / "Gen.xml"
    if not gen_xml.exists():
        raise FileNotFoundError(
            f"{gen_xml} missing — run scripts/fetch_sources.sh to extract OSHB"
        )

    with open(Path(repo) / "lexicons/strongs-list.json", encoding="utf-8") as fh:
        canonical = json.load(fh)
    canon_h = set(canonical["hebrew"])

    verses: dict[str, list[dict]] = {}
    for chapter in (1,):
        for rec in parse_book_xml(str(gen_xml), chapter):
            vnum = rec["osisID"].split(".")[-1]
            verses.setdefault(vnum, []).append(rec)

    # Integrity: every base Strong's number must be in the canonical list.
    unknown = sorted(
        {r["base"] for words in verses.values() for r in words if r["base"]}
        - canon_h
    )
    if unknown:
        raise ValueError(
            f"base Strong's numbers outside the canonical list: {unknown[:10]}"
        )

    n_words = sum(len(w) for w in verses.values())
    prefix_only = sum(1 for words in verses.values() for r in words if not r["base"])
    ids = [r["id"] for words in verses.values() for r in words]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate OSHB word ids in Genesis 1 — layer would be ambiguous")

    payload = {
        "$schema": "morphology-genesis1/v1",
        "source": {
            "dataset": "Open Scriptures Hebrew Bible v2.2 (per-book OSIS XML)",
            "upstream": "https://github.com/openscriptures/morphhb",
            "pin": "SHA-256 in data/PROVENANCE.md",
        },
        "license": "WLC text: public domain; morphology+lemma: CC BY 4.0",
        "attribution": "Open Scriptures Hebrew Bible Project (https://hb.openscriptures.org)",
        "changes_recorded": [
            "Reformatted OSIS XML -> JSON, one record per <w> word (data unchanged).",
            "Lemma decomposition into prefix chain / base Strong's / suffix marker",
            "is derived structure; the verbatim lemma is kept on every record.",
        ],
        "counts": {
            "verses": len(verses),
            "words": n_words,
            "prefix_only_words": prefix_only,
        },
        "verses": verses,
    }
    out_path = Path(out_dir) / "morphology-genesis1.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(verses)} verses / {n_words} words "
        f"({prefix_only} prefix-only) to {out_path}"
    )
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate OSHB morphology layer")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--oshb-dir", default=None)
    parser.add_argument("--out-dir", default="lexicons")
    args = parser.parse_args(argv)
    build(args.repo, args.oshb_dir, args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())