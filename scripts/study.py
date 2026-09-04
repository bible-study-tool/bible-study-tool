#!/usr/bin/env python3
"""Unified human-friendly CLI and TUI for Adventist Bible Study Tool (WP-021, ADR-0017).

Provides an integrated, beautiful terminal interface for Scripture reading,
original language syntactic exploration (Macula), Strong's concordances,
and Spirit of Prophecy commentary.

Usage:
  python scripts/study.py                       Launch full-screen interactive TUI (default)
  python scripts/study.py read "John 3:16"      Read scripture passage with verse formatting
  python scripts/study.py study "Rev 14:6-7"    Deep study view (Scripture + Syntax + Lexicon + EGW)
  python scripts/study.py word H1254            Word study (Hebrew/Greek lemma, definition, LXX)
  python scripts/study.py search "covenant"     Unified search across Bible and commentary
  python scripts/study.py egw "PP.57.1"         Look up EGW citation or search topics
  python scripts/study.py shell                 Launch interactive readline REPL
  python scripts/study.py tui                   Explicitly launch curses TUI
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from search.ui.formatting import supports_color
from search.ui.shell import StudyShell
from search.ui.study_service import StudyService
from search.ui.tui import run_tui


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="study",
        description="Adventist Bible Study Tool — Interactive TUI & Unified Study CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Study commands")

    # Subcommand: read
    p_read = subparsers.add_parser("read", help="Read scripture passage")
    p_read.add_argument("passage", help="Passage reference (e.g. 'John 1', 'Gen 1:1-5', 'Ps 23')")
    p_read.add_argument("-s", "--strongs", action="store_true", help="Display inline Strong's tags")
    p_read.add_argument("--json", action="store_true", help="Output raw JSON data")

    # Subcommand: study
    p_study = subparsers.add_parser("study", help="Deep study view combining Scripture, Macula syntax, Lexicon, and EGW")
    p_study.add_argument("passage", help="Passage reference (e.g. 'Rev 14:6-12', 'Gen 1:1-3')")
    p_study.add_argument("--json", action="store_true", help="Output raw JSON data")

    # Subcommand: word
    p_word = subparsers.add_parser("word", help="Deep lexical word study for a Strong's number")
    p_word.add_argument("strongs", help="Strong's number (e.g. 'H1254', 'G2316')")
    p_word.add_argument("--json", action="store_true", help="Output raw JSON data")

    # Subcommand: search
    p_search = subparsers.add_parser("search", help="Search across Scripture and EGW writings")
    p_search.add_argument("query", help="Keywords or search phrase")
    p_search.add_argument("--in", dest="scope", choices=["all", "bible", "egw"], default="all", help="Corpus to search")
    p_search.add_argument("--book", help="Filter search to specific biblical book")
    p_search.add_argument("--limit", type=int, default=10, help="Max results to return")
    p_search.add_argument("--json", action="store_true", help="Output raw JSON data")

    # Subcommand: egw
    p_egw = subparsers.add_parser("egw", help="Look up EGW citation or search writings")
    p_egw.add_argument("query", help="Citation (e.g. 'PP.57.1') or search query (e.g. 'sanctuary')")
    p_egw.add_argument("--json", action="store_true", help="Output raw JSON data")

    # Subcommand: frame
    p_frame = subparsers.add_parser("frame", help="Inspect Macula syntactic participant frames")
    p_frame.add_argument("passage", help="Passage or verse reference (e.g. 'Gen 1:1', 'John 1:1')")
    p_frame.add_argument("--json", action="store_true", help="Output raw JSON data")

    # Subcommand: shell
    p_shell = subparsers.add_parser("shell", help="Launch interactive readline study shell")

    # Subcommand: tui
    p_tui = subparsers.add_parser("tui", help="Launch full-screen curses TUI")
    p_tui.add_argument("passage", nargs="?", default="Gen 1:1", help="Initial passage to display")

    # Optional top-level flag
    parser.add_argument("--passage", help="Passage to read or study")

    args = parser.parse_args()

    service = StudyService()
    shell = StudyShell(service)

    if not args.subcommand:
        # Default behavior: Launch TUI if TTY, otherwise interactive shell
        start_ref = args.passage or "Gen 1:1"
        if sys.stdin.isatty() and sys.stdout.isatty():
            run_tui(service, initial_ref=start_ref)
        else:
            if args.passage:
                shell.cmd_read(args.passage)
            shell.run()
        return

    if args.subcommand == "tui":
        run_tui(service, initial_ref=args.passage)
        return

    if args.subcommand == "shell":
        shell.run()
        return

    if args.subcommand == "read":
        if args.json:
            ps = service.get_passage_study(args.passage)
            out = {
                "ref": ps.ref,
                "book": ps.book_name,
                "verses": [
                    {
                        "osis": v.osis,
                        "chapter": v.chapter,
                        "verse": v.verse,
                        "text": v.text,
                        "strongs": v.strongs_list,
                    }
                    for v in ps.verses
                ],
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return
        shell.show_strongs = args.strongs
        shell.cmd_read(args.passage)
        return

    if args.subcommand == "study":
        if args.json:
            ps = service.get_passage_study(args.passage)
            out = {
                "ref": ps.ref,
                "book": ps.book_name,
                "verses": [
                    {
                        "osis": v.osis,
                        "chapter": v.chapter,
                        "verse": v.verse,
                        "text": v.text,
                        "original_text": v.original_text,
                        "semantic_frames": v.semantic_frames,
                        "strongs": v.strongs_list,
                    }
                    for v in ps.verses
                ],
                "egw_correlations": ps.egw_correlations,
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return
        shell.cmd_study(args.passage)
        return

    if args.subcommand == "word":
        if args.json:
            ws = service.lookup_word(args.strongs)
            if not ws:
                print(json.dumps({"error": f"Strong's entry not found: {args.strongs}"}))
                sys.exit(1)
            out = {
                "strongs_id": ws.strongs_id,
                "language": ws.language,
                "word": ws.word,
                "translit": ws.translit,
                "gloss": ws.gloss,
                "definition": ws.definition,
                "occurrences_count": ws.occurrences_count,
                "lxx_equivalences": ws.lxx_equivalences,
                "sample_verses": ws.sample_verses,
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return
        shell.cmd_word(args.strongs)
        return

    if args.subcommand == "search":
        limit_b = args.limit if args.scope in ("all", "bible") else 0
        limit_e = args.limit if args.scope in ("all", "egw") else 0
        res = service.search_unified(args.query, limit_bible=limit_b, limit_egw=limit_e, book_filter=args.book)
        if args.json:
            out = {
                "query": res.query,
                "bible_hits": res.bible_hits,
                "egw_hits": res.egw_hits,
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return
        shell.cmd_search(args.query, results=res)
        return

    if args.subcommand == "egw":
        if args.json:
            from search.linking.egw import is_egw_token, normalize_token
            if is_egw_token(args.query) and service.egw_db:
                p = service.egw_db.get_paragraph(args.query)
                if p:
                    print(json.dumps({
                        "token": p.get("ref_code") or p.get("id"),
                        "book_name": p.get("book_title"),
                        "page": p.get("page"),
                        "paragraph": p.get("paragraph"),
                        "heading": p.get("chapter_title"),
                        "text": p.get("text"),
                    }, indent=2, ensure_ascii=False))
                    return
            # Search
            hits = service.egw_db.search(args.query, limit=10) if service.egw_db else []
            print(json.dumps({"hits": hits}, indent=2, ensure_ascii=False))
            return
        shell.cmd_egw(args.query)
        return

    if args.subcommand == "frame":
        if args.json:
            ps = service.get_passage_study(args.passage)
            out = {
                "ref": ps.ref,
                "verses": [
                    {
                        "osis": v.osis,
                        "original_text": v.original_text,
                        "semantic_frames": v.semantic_frames,
                    }
                    for v in ps.verses
                ],
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return
        shell.cmd_frame(args.passage)
        return


if __name__ == "__main__":
    main()
