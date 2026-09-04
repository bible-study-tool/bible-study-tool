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
from search.macula.enrichment import get_translation_equivalences, get_verse_semantic_frame


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


def format_equivalences(eqs: list[dict], strongs: str) -> str:
    lines = [f"LXX Translation Equivalences for {strongs.upper()} ({len(eqs)} found):"]
    for idx, eq in enumerate(eqs, 1):
        g_id = eq.get("greek_strongs")
        h_id = eq.get("hebrew_strongs")
        count = eq.get("count", 0)
        forms = ", ".join(eq.get("greek_forms", []))
        lemmas = ", ".join(eq.get("hebrew_lemmas", []))
        glosses = ", ".join(eq.get("hebrew_glosses", []))
        lines.append(f"  {idx}. {h_id} ({lemmas} / '{glosses}') ↔ {g_id} ({forms}): {count}x")
        if eq.get("core_domains"):
            lines.append(f"     SDBH Core Domains: {', '.join(eq['core_domains'])}")
    return "\n".join(lines)


def format_semantic_frame(frame: dict) -> str:
    lines = [
        f"Verse: {frame.get('verse_id')} [MT: {frame.get('mt_id')}]",
        f"Text:  {frame.get('text')}",
        "",
        "Semantic Participant Roles & Clauses:",
    ]
    for cl in frame.get("clauses", []):
        num = cl.get("clause_num")
        rule = cl.get("rule", "")
        lines.append(f"  Clause {num} [rule: {rule}]:")
        if cl.get("agents"):
            ag = ", ".join(a["text"] for a in cl["agents"])
            lines.append(f"    - Agent (Subject):          {ag}")
        if cl.get("actions"):
            ac = ", ".join(a["text"] for a in cl["actions"])
            lines.append(f"    - Action (Predicate Verb):   {ac}")
        if cl.get("patients"):
            pt = ", ".join(p["text"] for p in cl["patients"])
            lines.append(f"    - Patient (Object/Theme):   {pt}")
        if cl.get("context"):
            cx = ", ".join(c["text"] for c in cl["context"])
            lines.append(f"    - Context (Preposition/Adv): {cx}")
        if cl.get("summary"):
            lines.append(f"    Summary: {cl['summary']}")
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


def format_roles(results: list[dict], role: str) -> str:
    lines = [f"Syntactic Role '{role.upper()}' Matches ({len(results)} found):"]
    for idx, r in enumerate(results, 1):
        v_id = r.get("verse_id", "")
        c_text = r.get("constituent_text", "")
        r_label = r.get("role_label") or r.get("role") or ""
        cl_rule = r.get("clause_rule", "")
        lines.append(f"  {idx}. [{v_id}] [{r_label.upper()}]: {c_text}")
        if cl_rule:
            lines.append(f"     Clause Rule: {cl_rule}")
        if r.get("verse_text"):
            lines.append(f"     Verse Text:  {r['verse_text']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query Macula Hebrew linguistic and syntactic data.")
    query_group = parser.add_mutually_exclusive_group()
    query_group.add_argument("-s", "--strongs", help="Hebrew Strong's number (e.g. H7225, 7225)")
    query_group.add_argument("-v", "--verse", help="Verse reference (e.g. Gen.1.1, 1:1)")
    query_group.add_argument("-l", "--lxx", help="Greek LXX Strong's number (e.g. G4160, 4160)")
    query_group.add_argument("-d", "--domain", help="SDBH Core Domain code (e.g. 168, 028)")
    query_group.add_argument("-r", "--role", help="Constituent syntactic role (e.g. subj, pred, obj, adv)")
    query_group.add_argument("--stats", action="store_true", help="Display summary statistics")
    parser.add_argument("--frame", action="store_true", help="Display semantic participant frame for verse")
    parser.add_argument("--equiv", action="store_true", help="Display Septuagint (LXX) translation equivalences for Strong's")
    parser.add_argument("--limit", type=int, default=50, help="Maximum results for role queries (default: 50)")
    parser.add_argument("--book", help="Filter role query to book code (e.g. GEN)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--db", help="Explicit path to SQLite database (e.g. data/macula.db)")
    parser.add_argument("--artifact", default=None, help="Explicit path to JSON artifact (e.g. lexicons/macula-genesis.json)")

    args = parser.parse_args(argv)

    raw_path = args.db or args.artifact
    target_path = (REPO_ROOT / raw_path) if raw_path else None
    try:
        db = MaculaDB(target_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.frame and not args.verse:
        print("Error: --frame requires --verse (e.g. --verse Gen.1.1 --frame)", file=sys.stderr)
        return 1
    if args.equiv and not (args.strongs or args.lxx):
        print("Error: --equiv requires --strongs or --lxx (e.g. --strongs H1254 --equiv)", file=sys.stderr)
        return 1

    if args.stats:
        counts = db.counts
        backend = "SQLite" if db.is_sqlite else "In-Memory JSON"
        if args.json:
            out = dict(counts)
            out["backend"] = backend
            print(json.dumps(out, indent=2))
        else:
            print(f"Macula Hebrew Corpus Statistics [Backend: {backend}]:")
            for k, v in counts.items():
                print(f"  {k}: {v}")
        return 0

    if args.strongs:
        if args.equiv:
            eqs = get_translation_equivalences(args.strongs, db=db, repo_root=REPO_ROOT)
            if not eqs:
                print(f"No LXX translation equivalences found for '{args.strongs}'.", file=sys.stderr)
                return 1
            if args.json:
                print(json.dumps(eqs, ensure_ascii=False, indent=2))
            else:
                print(format_equivalences(eqs, args.strongs))
            return 0

        res = db.lookup_strongs(args.strongs)
        if not res:
            print(f"Strong's number '{args.strongs}' not found in Macula corpus.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(format_strongs(res))
        return 0

    if args.verse:
        if args.frame:
            frame = get_verse_semantic_frame(args.verse, db=db, repo_root=REPO_ROOT)
            if not frame:
                print(f"Verse '{args.verse}' not found in Macula dataset.", file=sys.stderr)
                return 1
            if args.json:
                print(json.dumps(frame, ensure_ascii=False, indent=2))
            else:
                print(format_semantic_frame(frame))
            return 0

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
        if args.equiv:
            eqs = get_translation_equivalences(args.lxx, db=db, repo_root=REPO_ROOT)
            if not eqs:
                print(f"No LXX translation equivalences found for '{args.lxx}'.", file=sys.stderr)
                return 1
            if args.json:
                print(json.dumps(eqs, ensure_ascii=False, indent=2))
            else:
                print(format_equivalences(eqs, args.lxx))
            return 0

        res = db.lookup_lxx(args.lxx)
        if not res:
            print(f"Greek LXX Strong's '{args.lxx}' has no alignments in Macula corpus.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"Hebrew words aligned with {args.lxx.upper()} in Macula corpus:")
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

    if args.role:
        res = db.search_by_role(args.role, limit=args.limit, book_code=args.book)
        if not res:
            print(f"No constituents found with role '{args.role}'.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(format_roles(res, args.role))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

