"""Unified CLI and TUI subcommand dispatcher for Adventist Bible Study Tool.

Shared by scripts/study.py and the main bible-study launcher (search.ui.web).
Provides an integrated interface for Scripture reading, original language
syntactic exploration (Macula), Strong's concordances, and commentary lookups.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

# Force UTF-8 encoding for stdout/stderr across platforms (avoids cp1252 UnicodeEncodeError on Windows)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from search.linking.egw import is_egw_token
from search.ui.shell import StudyShell
from search.ui.study_service import StudyService

try:
    from search.ui.app import run_textual_app
    from search.ui.themes import THEMES, DEFAULT_THEME
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    THEMES = {}
    DEFAULT_THEME = "transparent"

_DB_REQUIRED = {"read", "study", "word", "search", "frame"}


def launch_interactive_tui(
    service: StudyService,
    passage: str = "Gen 1:1",
    theme: str = "transparent",
    force_curses: bool = False,
) -> None:
    """Launch Textual TUI if available and interactive, otherwise fallback to curses."""
    if not force_curses and TEXTUAL_AVAILABLE:
        try:
            run_textual_app(service, initial_ref=passage, initial_theme=theme)
            return
        except Exception as e:
            sys.stderr.write(f"Notice: Textual UI encountered an issue ({e}). Falling back to curses...\n")
    try:
        from search.ui.tui import run_tui
        run_tui(service, initial_ref=passage)
    except (RuntimeError, ImportError, Exception) as err:
        sys.stderr.write(f"Error launching TUI: {err}\n")
        sys.exit(1)


def add_cli_subparsers(subparsers: argparse._SubParsersAction) -> None:
    """Register all standard study CLI subcommands on an existing subparsers action."""
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
    p_search.add_argument("--theme", help="Filter by theme tag (e.g. theme/grace)")
    p_search.add_argument("--translation", help="Filter by translation (e.g. kjv)")
    p_search.add_argument("--language", help="Filter by language (e.g. lang/hebrew)")
    p_search.add_argument("--status", help="Filter by curation status (e.g. status/review)")
    p_search.add_argument("--text", help="Free-text across all content stores")
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
    subparsers.add_parser("shell", help="Launch interactive readline study shell")

    # Subcommand: tui
    p_tui = subparsers.add_parser("tui", help="Launch full-screen interactive TUI workstation")
    p_tui.add_argument("passage", nargs="?", default="Gen 1:1", help="Initial passage to display")
    p_tui.add_argument("--theme", choices=list(THEMES.keys()) if THEMES else None, default=DEFAULT_THEME, help="Color theme for Textual TUI")
    p_tui.add_argument("--curses", action="store_true", help="Force classic curses interface instead of Textual")


def execute_subcommand(service: StudyService, args: argparse.Namespace) -> int:
    """Execute a CLI subcommand. Returns exit code (0 for success, non-zero for error)."""
    subcommand = getattr(args, "subcommand", None)

    # Facet/text flags route search to the C4 query API, which works on the
    # curated markdown corpus (no bible.db required). TUI and shell handle
    # the missing DB gracefully on their own.
    use_query = subcommand == "search" and any([
        getattr(args, "theme", None),
        getattr(args, "translation", None),
        getattr(args, "language", None),
        getattr(args, "status", None),
        getattr(args, "text", None),
    ])
    if subcommand in _DB_REQUIRED and service.bible_db is None and not use_query:
        sys.stderr.write(
            "ERROR: data/bible.db not found.\n"
            "Build it first by running:\n\n"
            "    python bible_lookup.py\n\n"
            "This takes ~6 seconds and creates the whole-Bible database (31,102 verses).\n"
        )
        return 1

    shell = StudyShell(service)

    if subcommand == "tui":
        theme = getattr(args, "theme", DEFAULT_THEME) or DEFAULT_THEME
        force_curses = getattr(args, "curses", False)
        passage = getattr(args, "passage", "Gen 1:1") or "Gen 1:1"
        launch_interactive_tui(service, passage=passage, theme=theme, force_curses=force_curses)
        return 0

    if subcommand == "shell":
        shell.run()
        return 0

    if subcommand == "read":
        if getattr(args, "json", False):
            ps = service.get_passage_study(args.passage, eager_frames=False)
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
            return 0
        shell.show_strongs = getattr(args, "strongs", False)
        shell.cmd_read(args.passage)
        return 0

    if subcommand == "study":
        if getattr(args, "json", False):
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
                        "ot_citations": [
                            {
                                "nt_osis": c.nt_osis,
                                "ot_osis": c.ot_osis,
                                "ot_book": c.ot_book,
                                "ot_ref_display": c.ot_ref_display,
                                "nt_ref_display": c.nt_ref_display,
                                "citation_type": c.citation_type.value,
                                "introductory_formula": c.introductory_formula,
                                "covenant_theme": c.covenant_theme,
                                "theological_significance": c.theological_significance,
                            }
                            for c in v.ot_citations
                        ],
                        "discourse_markers": [
                            {
                                "category": m.category.value,
                                "original_word": m.original_word,
                                "role_label": m.role_label,
                                "function_summary": m.function_summary,
                            }
                            for m in v.discourse_markers
                        ],
                    }
                    for v in ps.verses
                ],
                "egw_correlations": ps.egw_correlations,
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return 0
        shell.cmd_study(args.passage)
        return 0

    if subcommand == "word":
        if getattr(args, "json", False):
            ws = service.lookup_word(args.strongs)
            if not ws:
                print(json.dumps({"error": f"Strong's entry not found: {args.strongs}"}))
                return 1
            out = {
                "strongs_id": ws.strongs_id,
                "language": ws.language,
                "word": ws.word,
                "translit": ws.translit,
                "gloss": ws.gloss,
                "definition": ws.definition,
                "scholarly_definition": ws.scholarly_definition,
                "source_lexicon": ws.source_lexicon,
                "strongs_senses": ws.strongs_senses,
                "kjv_renderings": ws.kjv_renderings,
                "etymology": ws.etymology,
                "occurrences_count": ws.occurrences_count,
                "lxx_equivalences": ws.lxx_equivalences,
                "sample_verses": ws.sample_verses,
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return 0
        shell.cmd_word(args.strongs)
        return 0

    if subcommand == "search":
        if use_query:
            facets = {}
            for facet, value in (
                ("theme", getattr(args, "theme", None)),
                ("translation", getattr(args, "translation", None)),
                ("language", getattr(args, "language", None)),
                ("status", getattr(args, "status", None)),
            ):
                if value:
                    facets.setdefault(facet, []).append(value)
            text = getattr(args, "text", None) or args.query or None
            from search.corpus.query import query as _c4_query

            res = _c4_query(facets, text, limit=args.limit)
            if getattr(args, "json", False):
                out = {
                    "query": args.query,
                    "facets": facets,
                    "text": text,
                    "results": res,
                    "count": len(res),
                }
                print(json.dumps(out, indent=2, ensure_ascii=False))
                return 0
            for r in res:
                print(f"{r.get('source', 'entry')}: {r.get('passage', '')}")
            return 0
        limit_b = args.limit if args.scope in ("all", "bible") else 0
        limit_e = args.limit if args.scope in ("all", "egw") else 0
        res = service.search_unified(args.query, limit_bible=limit_b, limit_egw=limit_e, book_filter=args.book)
        if getattr(args, "json", False):
            bridge_res = service.search(args.query, limit=args.limit, book=args.book)
            out = {
                "query": res.query,
                "bible_hits": res.bible_hits,
                "egw_hits": res.egw_hits,
                "total_hits": bridge_res.get("total_hits", 0),
                "counts": bridge_res.get("counts", {}),
                "expansion": bridge_res.get("expansion", {}),
                "results": bridge_res.get("results", []),
            }
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return 0
        shell.cmd_search(args.query, results=res)
        return 0

    if subcommand == "egw":
        if getattr(args, "json", False):
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
                    return 0
            hits = service.egw_db.search(args.query, limit=10) if service.egw_db else []
            print(json.dumps({"hits": hits}, indent=2, ensure_ascii=False))
            return 0
        shell.cmd_egw(args.query)
        return 0

    if subcommand == "frame":
        if getattr(args, "json", False):
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
            return 0
        shell.cmd_frame(args.passage)
        return 0

    return 0


def build_cli_parser(prog: str = "study") -> argparse.ArgumentParser:
    """Build parser for study.py CLI."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Adventist Bible Study Tool — Interactive TUI & Unified Study CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Study commands")
    add_cli_subparsers(subparsers)

    # Optional top-level flags for default invocation
    parser.add_argument("--passage", help="Passage to read or study")
    parser.add_argument("--theme", choices=list(THEMES.keys()) if THEMES else None, default=DEFAULT_THEME, help="Color theme for Textual TUI")
    parser.add_argument("--curses", action="store_true", help="Force classic curses interface instead of Textual")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for study.py (default launches TUI)."""
    parser = build_cli_parser(prog="study")
    args = parser.parse_args(argv)

    service = StudyService()
    try:
        if not args.subcommand:
            start_ref = args.passage or "Gen 1:1"
            theme = getattr(args, "theme", DEFAULT_THEME) or DEFAULT_THEME
            force_curses = getattr(args, "curses", False)
            if sys.stdin.isatty() and sys.stdout.isatty():
                launch_interactive_tui(service, passage=start_ref, theme=theme, force_curses=force_curses)
            else:
                shell = StudyShell(service)
                if args.passage:
                    shell.cmd_read(args.passage)
                shell.run()
            return 0

        return execute_subcommand(service, args)
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())
