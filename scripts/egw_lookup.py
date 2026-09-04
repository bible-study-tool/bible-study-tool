#!/usr/bin/env python3
"""egw_lookup.py — Spirit of Prophecy (EGW) citation resolution and search CLI.

Resolves canonical Spirit of Prophecy citation tokens (e.g. 'egw:PP.57.1')
Just-In-Time from the local SQLite database (data/egw.db) and provides FTS5 search.

Usage:
  python scripts/egw_lookup.py PP.57.1
  python scripts/egw_lookup.py egw:PP.66.1
  python scripts/egw_lookup.py --search "enmity between thee"
  python scripts/egw_lookup.py --search "Sabbath" --book PP
  python scripts/egw_lookup.py --seed-core
  python scripts/egw_lookup.py --stats
  python scripts/egw_lookup.py --ingest-json path/to/paragraphs.json
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure repo root is in sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from search.linking.egw import (
        DEFAULT_EGW_DB,
        KNOWN_EGW_BOOKS,
        EgwDB,
        is_egw_token,
        normalize_token,
        seed_core_genesis_passages,
    )
    from search.linking.egw_importer import (
        BulkImporter,
        harvest_public_domain,
        verify_book_anchors,
        PUBLIC_DOMAIN_SOURCES,
    )
except ModuleNotFoundError as err:
    sys.stderr.write(
        f"\n[ERROR] Missing required module: {err.name}\n"
        "Please run `./scripts/bootstrap.sh` or activate your virtual environment:\n"
        "    source .venv/bin/activate\n\n"
    )
    sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Spirit of Prophecy (EGW) citation lookup and search CLI (ADR-0011)."
    )
    parser.add_argument(
        "token",
        nargs="?",
        help="Canonical citation token (e.g. PP.57.1 or egw:PP.57.1)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help=f"Path to local SQLite database (default: {_REPO_ROOT / DEFAULT_EGW_DB})",
    )
    parser.add_argument(
        "--search",
        "-s",
        help="Full-text search query across Spirit of Prophecy writings",
    )
    parser.add_argument(
        "--book",
        "-b",
        help="Filter search to specific book code (e.g. PP, DA, GC)",
    )
    parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=5,
        help="Maximum search results to return (default: 5)",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize database schema and tables",
    )
    parser.add_argument(
        "--seed-core",
        action="store_true",
        help="Seed core Genesis study paragraphs from Patriarchs and Prophets",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics and paragraph counts",
    )
    parser.add_argument(
        "--ingest",
        "--ingest-file",
        dest="ingest_file",
        help="Path to an EPUB, TXT, MD, or JSON file to import into the local database",
    )
    parser.add_argument(
        "--ingest-dir",
        help="Path to a directory of EPUB, TXT, MD, or JSON files to batch import",
    )
    parser.add_argument(
        "--fetch-public-domain",
        type=str.upper,
        choices=list(PUBLIC_DOMAIN_SOURCES.keys()),
        help=f"Download and ingest verified pre-1929 public domain works ({', '.join(PUBLIC_DOMAIN_SOURCES.keys())})",
    )
    parser.add_argument(
        "--verify-anchors",
        action="store_true",
        help="Verify ingested edition paragraphs against canonical verification anchor checkpoints",
    )
    parser.add_argument(
        "--ingest-json",
        help="Path to JSON file containing paragraph entries to import (legacy alias)",
    )

    args = parser.parse_args(argv)

    with EgwDB(db_path=args.db, repo_root=_REPO_ROOT) as db:
        if args.init:
            db.init_db()
            print(f"Initialized database schema at {db.db_path}")
            return 0

        if args.seed_core:
            db.init_db()
            n = seed_core_genesis_passages(db)
            print(f"Seeded {n} core Genesis study paragraphs into {db.db_path}")
            return 0

        if args.verify_anchors:
            if not db.exists():
                print(f"Database does not exist at {db.db_path}.", file=sys.stderr)
                return 1
            results = verify_book_anchors(db, book_code=args.book)
            matches = [r for r in results if r["status"] == "match"]
            mismatches = [r for r in results if r["status"] == "mismatch"]
            missing = [r for r in results if r["status"] == "missing"]

            print(f"Canonical Anchor Verification Results ({db.db_path}):")
            print(f"  ✔ Matches:    {len(matches)}")
            print(f"  ⚠ Mismatches: {len(mismatches)}")
            print(f"  - Missing:    {len(missing)}")
            for r in matches:
                print(f"    [OK] {r['token']}: {r['message']}")
            for r in mismatches:
                print(f"    [WARNING] {r['token']}: {r['message']}", file=sys.stderr)
            return 0

        if args.fetch_public_domain:
            try:
                db.init_db()
                code = args.fetch_public_domain.upper()
                print(f"Fetching public-domain edition for {code} ({PUBLIC_DOMAIN_SOURCES[code]['title']})...")
                n = harvest_public_domain(code, db, dest_dir=_REPO_ROOT / "data" / "egw-sources")
                print(f"Successfully ingested {n} paragraphs into {db.db_path}")
                return 0
            except Exception as ex:
                print(f"Error fetching public domain work: {ex}", file=sys.stderr)
                return 1

        if args.ingest_file or args.ingest_json:
            target = args.ingest_file or args.ingest_json
            try:
                importer = BulkImporter(db)
                n = importer.import_file(target, book_code=args.book)
                print(f"Successfully ingested {n} paragraphs from {target} into {db.db_path}")
                return 0
            except Exception as ex:
                print(f"Error ingesting file: {ex}", file=sys.stderr)
                return 1

        if args.ingest_dir:
            try:
                importer = BulkImporter(db)
                print(f"Scanning and importing files in {args.ingest_dir}...")
                results = importer.import_directory(args.ingest_dir)
                total = sum(v for v in results.values() if v > 0)
                print(f"Imported {total} paragraphs across {len(results)} file(s):")
                for fname, cnt in results.items():
                    status = f"{cnt} paragraphs" if cnt >= 0 else "FAILED"
                    print(f"  - {fname}: {status}")
                return 0
            except Exception as ex:
                print(f"Error ingesting directory: {ex}", file=sys.stderr)
                return 1

        if args.stats:
            if not db.exists():
                print(f"Database does not exist at {db.db_path}. Run --init or --seed-core to create it.")
                return 0
            total = db.count()
            print(f"EGW Database: {db.db_path}")
            print(f"Total paragraphs: {total}")
            cur = db.conn.execute(
                "SELECT book_code, book_title, COUNT(*) as cnt FROM egw_paragraphs GROUP BY book_code ORDER BY cnt DESC;"
            )
            for row in cur.fetchall():
                print(f"  - {row['book_code']} ({row['book_title']}): {row['cnt']} paragraphs")
            return 0

        if args.search:
            if not db.exists():
                print(f"Database does not exist at {db.db_path}. Run --seed-core or --init to create it.")
                return 1
            results = db.search(args.search, book_code=args.book, limit=args.limit)
            if not results:
                print(f"No results found matching '{args.search}'.")
                return 0
            print(f"Found {len(results)} result(s) for '{args.search}':\n")
            use_color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
            for i, r in enumerate(results, 1):
                ref = r.get("ref_code") or f"{r['book_code']} {r['page']}.{r['paragraph']}"
                token_id = f"egw:{r['id']}"
                snippet = r.get("snippet", r["text"][:120] + "...")
                clean_snippet = (
                    snippet.replace("[b]", "\033[1m").replace("[/b]", "\033[0m")
                    if use_color
                    else snippet.replace("[b]", "").replace("[/b]", "")
                )
                chap_info = f" ({r['chapter_title']})" if r.get("chapter_title") else ""
                print(f"{i}. [{ref}] ({token_id}) — {r['book_title']}, p. {r['page']}, para {r['paragraph']}{chap_info}")
                print(f"   {clean_snippet}\n")
            return 0

        if args.token:
            if not is_egw_token(args.token):
                print(f"Invalid EGW citation token '{args.token}'. Shape: BOOK.PAGE.PARA (e.g. PP.57.1)", file=sys.stderr)
                return 1
            if not db.exists():
                print(
                    f"EGW database not found at {db.db_path}.\n"
                    f"Run `python scripts/egw_lookup.py --seed-core` to initialize core reference passages.",
                    file=sys.stderr,
                )
                return 1
            para = db.get_paragraph(args.token)
            if not para:
                canonical_id, b_code, page, p_num = normalize_token(args.token)
                b_title = KNOWN_EGW_BOOKS.get(b_code, b_code)
                print(
                    f"Paragraph not found in local database: {canonical_id} "
                    f"({b_title}, p. {page}, para {p_num}).",
                    file=sys.stderr,
                )
                return 1
            print(db.format_paragraph(para))
            return 0

        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
