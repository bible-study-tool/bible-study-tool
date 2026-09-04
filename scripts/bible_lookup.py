#!/usr/bin/env python3
"""CLI utility for querying whole-Bible English text, Strong's tags, and full-text search (WP-019).

Examples:
  # Verse lookup
  python scripts/bible_lookup.py "John 3:16"
  python scripts/bible_lookup.py "Dan 8:14"
  python scripts/bible_lookup.py "Rev 14:6-7"

  # Show Strong's numbers and word spans
  python scripts/bible_lookup.py "John 3:16" --strongs

  # Whole chapter
  python scripts/bible_lookup.py "Psalm 23"

  # Full-text BM25 search across 31,102 verses
  python scripts/bible_lookup.py --search "sanctuary cleansed"
  python scripts/bible_lookup.py --search "commandments of God" --testament NT

  # Reverse Strong's lookup across the biblical canon
  python scripts/bible_lookup.py --find-strongs G2316 --limit 10

  # Corpus statistics
  python scripts/bible_lookup.py --stats
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

# Ensure repo root in sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from search.corpus.extract_kjv import (
    DEFAULT_BIBLE_DB,
    DEFAULT_KJV_JSON,
    BibleDB,
    compile_bible_db,
)


def format_verse(v: dict[str, Any], show_strongs: bool = False) -> str:
    """Format a single verse for terminal display."""
    ref_label = f"{v['book_name']} {v['chapter']}:{v['verse']}"
    header = f"[{ref_label}] ({v['id']})"
    lines = [header, f"  {v['clean_text']}"]

    if show_strongs:
        tokens = v.get("tokens", [])
        if tokens:
            token_strs = []
            for t in tokens:
                s_codes = ",".join(t.get("strongs", []))
                s_tag = f"<{s_codes}>" if s_codes else ""
                token_strs.append(f"{t.get('text', '')}{s_tag}")
            lines.append(f"  Tokens: {' '.join(token_strs)}")

        strongs = v.get("strongs", [])
        if strongs:
            lines.append(f"  Strong's Codes: {', '.join(strongs)}")

    return "\n".join(lines)


def handle_stats(db: BibleDB) -> int:
    counts = db.count()
    print("=" * 60)
    print("Whole-Bible English Corpus Statistics (KJV with Strong's)")
    print("=" * 60)
    print(f"Database: {db.db_path}")
    print(f"Total Books:    {counts['books']}")
    print(f"Total Verses:   {counts['verses']}")
    print(f"Testament:      OT (39 books, 23,145 verses) | NT (27 books, 7,957 verses)")
    print("=" * 60)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Whole-Bible English Text & Strong's Query Engine (WP-019)."
    )
    parser.add_argument("ref", nargs="?", default=None, help="Passage or verse reference (e.g. 'John 3:16', 'Dan 8:14', 'Ps 23')")
    parser.add_argument("--strongs", action="store_true", help="Display Strong's numbers with token spans")
    parser.add_argument("--search", default=None, help="Full-text keyword/phrase search across the Bible")
    parser.add_argument("--find-strongs", default=None, help="Find verses containing a specific Strong's number (e.g. G2316 or H7225)")
    parser.add_argument("--book", default=None, help="Filter search to a specific book (e.g. Dan, John)")
    parser.add_argument("--testament", choices=["OT", "NT", "ot", "nt"], default=None, help="Filter search to OT or NT")
    parser.add_argument("--limit", type=int, default=20, help="Maximum search results to display (default: 20)")
    parser.add_argument("--stats", action="store_true", help="Display canon and database statistics")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")
    parser.add_argument("--build", action="store_true", help="Force recompilation of data/bible.db from KJV-osis.json")
    parser.add_argument("--db", default=None, help="Path to SQLite database (default: data/bible.db)")

    args = parser.parse_args(argv)

    db_path = Path(args.db) if args.db else _REPO_ROOT / DEFAULT_BIBLE_DB

    if args.build or not db_path.is_file():
        compile_bible_db(
            json_path=_REPO_ROOT / DEFAULT_KJV_JSON,
            db_path=db_path,
            repo_root=_REPO_ROOT,
            force=args.build,
        )
        if args.build and not args.ref and not args.search and not args.find_strongs and not args.stats:
            return 0

    db = BibleDB(db_path=db_path, repo_root=_REPO_ROOT)

    if args.stats:
        return handle_stats(db)

    # 1. Reverse Strong's lookup
    if args.find_strongs:
        results = db.find_by_strongs(args.find_strongs, limit=args.limit)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return 0
        print(f"Found {len(results)} verse(s) containing Strong's {args.find_strongs.upper()}:")
        for v in results:
            print(format_verse(v, show_strongs=args.strongs))
        return 0

    # 2. Full-text search
    if args.search:
        results = db.search(
            args.search,
            limit=args.limit,
            book=args.book,
            testament=args.testament,
        )
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return 0
        print(f"Found {len(results)} verse(s) matching '{args.search}':\n")
        for v in results:
            print(format_verse(v, show_strongs=args.strongs))
            print()
        return 0

    # 3. Passage or verse reference
    if args.ref:
        try:
            results = db.get_passage(args.ref)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if not results:
            print(f"No verses found for reference '{args.ref}'.", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(results if len(results) > 1 else results[0], indent=2, ensure_ascii=False))
            return 0

        for v in results:
            print(format_verse(v, show_strongs=args.strongs))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
