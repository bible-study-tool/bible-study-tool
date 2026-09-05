"""Ingestion engine and CLI for multi-translation parallel Bible texts (WP-024 Phase 3).

Ingests public-domain English translations into data/bible.db:
  - ASV: American Standard Version (1901) - formal literal equivalence, divine name Jehovah.
  - BSB: Berean Standard Bible (2020) - natural, accurate, accessible modern English.
  - YLT: Young's Literal Translation (1898) - ultra-literal Hebrew/Greek verbal aspect rendering.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

from search.corpus.extract_kjv import BibleDB, DEFAULT_BIBLE_DB

KNOWN_TRANSLATIONS = {
    "asv": {
        "name": "American Standard Version",
        "year": 1901,
        "license": "Public Domain",
        "file": "data/ASV.json",
    },
    "bsb": {
        "name": "Berean Standard Bible",
        "year": 2020,
        "license": "Public Domain (CC0)",
        "file": "data/BSB.json",
    },
    "ylt": {
        "name": "Young's Literal Translation",
        "year": 1898,
        "license": "Public Domain",
        "file": "data/YLT.json",
    },
}


def sync_kjv_translation(db: BibleDB) -> int:
    """Ensure KJV is registered in translation_verses for uniform querying."""
    db._ensure_translation_tables()
    with db.conn:
        db.conn.execute("""
        INSERT OR IGNORE INTO translations (id, name, year, license, is_default)
        VALUES ('kjv', 'King James Version', 1769, 'Public Domain', 1);
        """)
        cur = db.conn.execute("""
        INSERT OR IGNORE INTO translation_verses (translation_id, verse_id, osis, chapter, verse, text)
        SELECT 'kjv', id, osis, chapter, verse, clean_text FROM verses;
        """)
        return cur.rowcount


def ingest_translations(
    repo_root: str | Path = ".",
    db_path: str | Path = DEFAULT_BIBLE_DB,
    translation_ids: list[str] | None = None,
) -> dict[str, int]:
    """Ingest specified or available translations into the BibleDB database."""
    root = Path(repo_root)
    results: dict[str, int] = {}

    with BibleDB(db_path=db_path, repo_root=root) as db:
        if not db.exists():
            raise FileNotFoundError(f"Bible database not found at {db.db_path}. Build KJV database first.")

        # Sync KJV into translations table
        kjv_synced = sync_kjv_translation(db)
        results["kjv"] = kjv_synced

        targets = translation_ids or list(KNOWN_TRANSLATIONS.keys())
        for t_id in targets:
            key = t_id.lower()
            if key not in KNOWN_TRANSLATIONS:
                print(f"Warning: Unknown translation '{t_id}'. Skipping.", file=sys.stderr)
                continue
            meta = KNOWN_TRANSLATIONS[key]
            json_file = root / meta["file"]
            if not json_file.is_file():
                print(f"Notice: {meta['file']} not found. Run scripts/fetch_sources.sh first.", file=sys.stderr)
                continue

            t0 = time.time()
            count = db.ingest_translation(
                translation_id=key,
                name=meta["name"],
                year=meta["year"],
                license=meta["license"],
                json_path=json_file,
            )
            elapsed = time.time() - t0
            results[key] = count
            print(f"Ingested {meta['name']} ({key.upper()}): {count:,} verses in {elapsed:.2f}s")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest parallel Bible translations into BibleDB.")
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_BIBLE_DB,
        help="Path to SQLite bible.db",
    )
    parser.add_argument(
        "--translations",
        default="asv,bsb,ylt",
        help="Comma-separated list of translation IDs to ingest (default: asv,bsb,ylt)",
    )
    args = parser.parse_args()

    t_ids = [t.strip() for t in args.translations.split(",") if t.strip()]
    ingest_translations(repo_root=args.repo, db_path=args.db, translation_ids=t_ids)


if __name__ == "__main__":
    main()
