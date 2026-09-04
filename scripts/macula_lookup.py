#!/usr/bin/env python3
"""CLI utility for querying Macula Hebrew linguistic and syntactic data.

Usage:
  python scripts/macula_lookup.py --strongs H7225
  python scripts/macula_lookup.py --verse Gen.1.1
  python scripts/macula_lookup.py --lxx G4160
  python scripts/macula_lookup.py --domain 168
  python scripts/macula_lookup.py --stats
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from search.macula.lookup import MaculaDB, normalize_verse_ref


def format_strongs(entry: dict) -> str:
    lines = [
        f"Strong's: {entry['strongs']}",
        f"Lemmas:   {', '.join(entry['lemmas'])}",
        f"Glosses:  {', '.join(entry['glosses'])}",
        f"Occurrences in Genesis: {entry['occurrences']}",
    ]
    if entry.get("sdbh"):
        lines.append(f"SDBH Senses:  {', '.join(entry['sdbh'])}")
    if entry.get("core_domains"):
        lines.append(f"Core Domains: {', '.join(entry['core_domains'])}")
    if entry.get("lex_domains"):
        lines.append(f"Lex Domains:  {', '.join(entry['lex_domains'])}")

    lxx = entry.get("lxx", {})
    if lxx:
        lines.append("Septuagint (LXX) Equivalents:")
        for g_id, g_rec in sorted(lxx.items(), key=lambda x: x[1]["count"], reverse=True):
            forms = ", ".join(g_rec.get("greek", []))
            lines.append(f"  - {g_id} ({forms}): {g_rec['count']}x")
    return "\n".join(lines)


def format_verse(entry: dict) -> str:
    lines = [
        f"Verse: {entry.get('verse_id')} [MT: {entry.get('mt_id')}]",
        f"Text:  {entry.get('text')}",
        "",
        "Clauses & Constituent Roles:",
    ]
    for idx, cl in enumerate(entry.get("clauses", []), 1):
        rule = cl.get("rule", "")
        lines.append(f"  Clause {idx} [rule: {rule}]:")
        for const in cl.get("constituents", []):
            label = const.get("role_label") or const.get("role") or const.get("class") or "phrase"
            c_text = const.get("text", "")
            tok_details = []
            for tok in const.get("tokens", []):
                s_num = tok.get("strongs") or ""
                lxx = tok.get("lxx_strongs") or ""
                gl = tok.get("gloss") or ""
                extra = []
                if s_num:
                    extra.append(s_num)
                if lxx:
                    extra.append(f"LXX:{lxx}")
                if gl:
                    extra.append(f"'{gl}'")
                tok_str = tok.get("text", "")
                if extra:
                    tok_str += f" ({', '.join(extra)})"
                tok_details.append(tok_str)
            lines.append(f"    - [{label.upper()}]: {c_text}")
            if len(const.get("tokens", [])) > 1:
                lines.append(f"        Tokens: {' | '.join(tok_details)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query Macula Hebrew linguistic and syntactic data.")
    query_group = parser.add_mutually_exclusive_group()
    query_group.add_argument("-s", "--strongs", help="Hebrew Strong's number (e.g. H7225, 7225)")
    query_group.add_argument("-v", "--verse", help="Verse reference (e.g. Gen.1.1, 1:1)")
    query_group.add_argument("-l", "--lxx", help="Greek LXX Strong's number (e.g. G4160, 4160)")
    query_group.add_argument("-d", "--domain", help="SDBH Core Domain code (e.g. 168, 028)")
    query_group.add_argument("--stats", action="store_true", help="Display summary statistics")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--artifact", default="lexicons/macula-genesis.json", help="Path to macula-genesis.json")

    args = parser.parse_args(argv)

    try:
        db = MaculaDB(REPO_ROOT / args.artifact)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.stats:
        counts = db.counts
        if args.json:
            print(json.dumps(counts, indent=2))
        else:
            print("Macula Hebrew Genesis Corpus Statistics:")
            for k, v in counts.items():
                print(f"  {k}: {v}")
        return 0

    if args.strongs:
        res = db.lookup_strongs(args.strongs)
        if not res:
            print(f"Strong's number '{args.strongs}' not found in Genesis.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(format_strongs(res))
        return 0

    if args.verse:
        res = db.lookup_verse(args.verse)
        if not res:
            print(f"Verse '{args.verse}' not found in Macula dataset.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(format_verse(res))
        return 0

    if args.lxx:
        res = db.lookup_lxx(args.lxx)
        if not res:
            print(f"Greek LXX Strong's '{args.lxx}' has no alignments in Genesis.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"Hebrew words aligned with {args.lxx.upper()} in Genesis:")
            for item in res:
                h_id = item["hebrew_strongs"]
                lemmas = ", ".join(item["lemmas"])
                glosses = ", ".join(item["glosses"])
                greek = ", ".join(item["greek_forms"])
                print(f"  - {h_id} ({lemmas} / '{glosses}'): {item['count']}x [forms: {greek}]")
        return 0

    if args.domain:
        res = db.search_by_domain(args.domain)
        if not res:
            print(f"No Hebrew words found for SDBH core domain '{args.domain}'.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"Hebrew words in SDBH Domain {args.domain}:")
            for item in res:
                h_id = item["hebrew_strongs"]
                lemmas = ", ".join(item["lemmas"])
                glosses = ", ".join(item["glosses"])
                print(f"  - {h_id} ({lemmas}): {glosses}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
