"""Generate modern-gloss lexicons from STEPBible TBESH/TBESG data.

Sources (CC BY 4.0, see data/PROVENANCE.md for pins):
  * TBESH — Translators Brief lexicon of Extended Strongs for Hebrew
    (abridged-BDB-based brief glosses; NOTE the Online-Bible caveat recorded
    in PROVENANCE.md and echoed into the artifact's license_note).
  * TBESG — Translators Brief lexicon of Extended Strongs for Greek
    (Abbott-Smith-based, public domain underlying text + CC BY 4.0).

Both are keyed to *Extended* Strong numbers that are backward-compatible with
original Strong's. This generator keeps only rows whose eStrong maps to an
ORIGINAL Strong's number in our canonical enumeration (H1-H8674, G1-G5624 —
loaded from lexicons/strongs-list.json), drops the extended-affix numbers
(>9000), and writes:

  lexicons/tbesh-glosses.json   # Hebrew modern brief glosses (BDB lineage)
  lexicons/tbesg-glosses.json   # Greek modern brief glosses (Abbott-Smith)

Output entry shape (verbatim data, reformatted only — per STEPBible's licence
"download the data and reformat it for your application, without changing the
data"; exact-duplicate rows are dropped and the drop count is recorded):
  {"H1": [{"dstrong": "H0001G =", "ustrong": "H0001G", "form": "אָב",
           "translit": "av", "morph": "H:N-M", "gloss": "father",
           "definition": "1) father of an individual..."}, ...]}

ATTRIBUTION (CC BY 4.0): data by www.STEPBible.org based on work at Tyndale
House Cambridge — credit "STEP Bible" with a link to www.STEPBible.org.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

# Data rows: eStrong tab dStrong tab uStrong tab form tab translit tab morph
# tab gloss tab definition (exactly 7 tabs; definition keeps any further tabs).
# eStrong forms seen in the data:
#   * H0001 / G0001        — original Strong's numbers (zero-padded 4 digits)
#   * H1254a (lowercase)   — BDB sub-entries of the SAME Strong's number (BDB
#     splits words Strong conflated, e.g. H1254a 'create' / H1254b 'fatten').
#     Some numbers have NO plain row — the lettered rows are their only
#     content — so they are KEPT, keyed to the base number.
#   * H9000+ / G20001+     — genuinely NEW extended words (affixes, NT/LXX
#     variants): outside the original enumeration, skipped.
_ROW_RE = re.compile(r"^([HG])(\d{4,6})([a-z]?)\t")

# Number of fields produced by splitting a row on the first 7 tabs.
_FIELDS = 8


def _canonical_code(letter: str, num: int) -> str | None:
    """Map a zero-padded eStrong to our canonical 'H####'/'G####' code, or
    None if it is outside the original Strong's enumeration (e.g. extended
    affix numbers above 9000)."""
    if letter == "H":
        return f"H{num}" if 1 <= num <= 8674 else None
    return f"G{num}" if 1 <= num <= 5624 else None


def parse_stepbible_txt(path: str) -> tuple["OrderedDict[str, list[dict]]", dict]:
    """Parse a TBESH/TBESG TSV into ({canonical_code: [variant, ...]}, stats).

    Skips the prose header (everything before the first data row). Drops
    exact-duplicate rows (counted in the returned stats). Raises ValueError if
    a data row does not have exactly 8 fields.
    """
    entries: "OrderedDict[str, list[dict]]" = OrderedDict()
    seen_rows: set[tuple] = set()
    dropped_duplicates = 0
    skipped_extended = 0
    started = False

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = _ROW_RE.match(line)
            if not m:
                if started:
                    # Prose/section lines between data rows are skipped; a
                    # line that looks like a row (superset of _ROW_RE: allows
                    # uppercase suffixes, 7+ digits, space-before-tab) but
                    # fails to parse is fatal — that is format drift.
                    if re.match(r"^[HG]\d+[a-zA-Z]?[ \t]*\t", line):
                        raise ValueError(
                            f"{path}: malformed data row: {line[:80]!r}"
                        )
                continue
            started = True
            letter, num_s, suffix = m.group(1), m.group(2), m.group(3)
            code = _canonical_code(letter, int(num_s))
            if code is None:
                skipped_extended += 1
                continue  # genuinely new extended word, outside the enumeration
            fields = line.split("\t", _FIELDS - 1)
            if len(fields) != _FIELDS:
                raise ValueError(f"{path}: expected {_FIELDS} fields, got {len(fields)}: {line[:80]!r}")
            estrong, dstrong, ustrong, form, translit, morph, gloss, definition = fields
            record = {
                "estrong": estrong.strip(),  # verbatim, incl. any suffix
                "dstrong": dstrong.strip(),
                "ustrong": ustrong.strip(),
                "form": form.strip(),
                "translit": translit.strip(),
                "morph": morph.strip(),
                "gloss": gloss.strip(),
                "definition": definition.strip(),
            }
            key = tuple(record.values())
            if key in seen_rows:
                dropped_duplicates += 1
                continue
            seen_rows.add(key)
            entries.setdefault(code, []).append(record)

    stats = {
        "dropped_duplicates": dropped_duplicates,
        "skipped_extended": skipped_extended,
        "started": started,
    }
    return entries, stats


def build(tbesh_path: str, tbesg_path: str, canonical_list_path: str, out_dir: str) -> None:
    with open(canonical_list_path, encoding="utf-8") as fh:
        canonical = json.load(fh)
    canon_h = set(canonical["hebrew"])
    canon_g = set(canonical["greek"])

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    attribution = "STEP Bible (www.STEPBible.org), based on work at Tyndale House Cambridge — CC BY 4.0"

    for src_path, canon_set, letter, stem, expect_full_coverage, extra in (
        (tbesh_path, canon_h, "H", "tbesh-glosses.json", True, {
            "license_note": (
                "STEPBible's own file header notes that the Brief lexicon is "
                "based on Abridged BDB by Online Bible and that 'Permission "
                "should be gained from Online Bible before these definitions "
                "are applied in any project.' Treat Hebrew brief glosses as "
                "supplementary, not authoritative; the Strong's definitions "
                "in strongs-lexicon.json remain the deterministic core."
            ),
        }),
        (tbesg_path, canon_g, "G", "tbesg-glosses.json", False, {}),
    ):
        entries, stats = parse_stepbible_txt(src_path)
        if not stats["started"] or not entries:
            raise ValueError(
                f"{src_path}: no data rows parsed (started={stats['started']}) — "
                "source file is empty, truncated, or not the expected format"
            )

        # Integrity (forward): every emitted code must exist in the canonical
        # list. (Bounds are the list itself, not hardcoded — _canonical_code
        # only pre-filters, this check is authoritative.)
        unknown = [c for c in entries if c not in canon_set]
        if unknown:
            raise ValueError(
                f"{src_path}: {len(unknown)} codes outside the canonical list, "
                f"e.g. {unknown[:5]}"
            )
        # Integrity (reverse, drift tripwire): TBESH is expected to cover the
        # full Hebrew enumeration (BDB sub-entries recover every code); a gap
        # means the source shrank or the parser regressed.
        missing = canon_set - set(entries)
        if expect_full_coverage and missing:
            raise ValueError(
                f"{src_path}: expected FULL canonical coverage, {len(missing)} "
                f"codes uncovered, e.g. {sorted(missing)[:5]}"
            )

        n_records = sum(len(v) for v in entries.values())
        if letter == "H":
            skip_note = (
                f"Skipped {stats['skipped_extended']} rows outside the "
                "enumeration (Hebrew affix numbers H8675-H9999)."
            )
        else:
            skip_note = (
                f"Skipped {stats['skipped_extended']} rows outside the "
                "enumeration (Greek variants G5625-G9999 and extended "
                "variant numbers G20000+)."
            )
        payload = {
            "$schema": "stepbible-glosses/v1",
            "source": {
                "dataset": Path(src_path).name,
                "upstream": "https://github.com/STEPBible/STEPBible-Data",
                "commit": "efe428a0047bf7b9c3ce2624f60c252c6e435945",
                "pin": "commit + blob SHAs + SHA-256 in data/PROVENANCE.md",
            },
            "license": "CC BY 4.0",
            "attribution": attribution,
            **extra,
            "changes_recorded": [
                "Reformatted TSV -> JSON (allowed by licence, data unchanged).",
                f"Dropped {stats['dropped_duplicates']} exact-duplicate rows.",
                skip_note,
                "BDB lettered sub-entries (e.g. H1254a) are keyed to their "
                "base Strong's number (H1254); the verbatim eStrong token is "
                "kept per record.",
            ],
            "counts": {
                "codes": len(entries),
                "records": n_records,
                "dropped_duplicates": stats["dropped_duplicates"],
                "skipped_extended": stats["skipped_extended"],
            },
            "entries": dict(entries),
        }
        out_path = out / stem
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            f"Wrote {len(entries)} {letter}-codes ({n_records} records) "
            f"to {out_path} (dropped {stats['dropped_duplicates']} duplicate rows)"
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate STEPBible modern-gloss lexicons")
    parser.add_argument("--tbesh", default="data/stepbible/TBESH.txt")
    parser.add_argument("--tbesg", default="data/stepbible/TBESG.txt")
    parser.add_argument("--canonical", default="lexicons/strongs-list.json")
    parser.add_argument("--out-dir", default="lexicons")
    args = parser.parse_args(argv)

    build(args.tbesh, args.tbesg, args.canonical, args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
