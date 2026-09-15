"""Treasury of Scripture Knowledge (TSK) Cross-Reference Ingestion Engine.

In accordance with ADR-013 and ADR-026:
  - Ingests ~344,800 canonical scripture cross-reference relationships from
    OpenBible.info / Treasury of Scripture Knowledge into data/bible.db.
  - Normalizes book abbreviations into standard OSIS reference identifiers.
  - Stores edges in SQLite table `cross_references` with bidirectional indices.
  - Provides sub-millisecond reciprocal lookup ordered by vote relevance.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys
import time
import zipfile

from search.corpus.bible_books import resolve_book_code

DEFAULT_TSK_ZIP = "data/cross-references.zip"
DEFAULT_BIBLE_DB = "data/bible.db"

_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS cross_references (
    from_verse TEXT NOT NULL,
    to_verse TEXT NOT NULL,
    votes INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (from_verse, to_verse)
);
"""

_INDICES_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_xrefs_from ON cross_references(from_verse, votes DESC);
CREATE INDEX IF NOT EXISTS idx_xrefs_to ON cross_references(to_verse);
"""


def norm_single_ref(ref: str) -> str:
    """Normalize a single verse reference (e.g. 'Gen.1.1' or '1John.3.16') into canonical OSIS format."""
    parts = ref.strip().split(".")
    if len(parts) == 3:
        book_part, ch_part, v_part = parts
        osis = resolve_book_code(book_part)
        return f"{osis}.{int(ch_part)}.{int(v_part)}"
    return ref.strip()


def norm_target_ref(target: str) -> str:
    """Normalize a target reference, which may be a single verse or a range (e.g. 'Prov.8.22-Prov.8.30')."""
    target = target.strip()
    if "-" in target:
        start_part, end_part = target.split("-", 1)
        return f"{norm_single_ref(start_part)}-{norm_single_ref(end_part)}"
    return norm_single_ref(target)


def ingest_tsk_cross_references(
    zip_path: str | Path = DEFAULT_TSK_ZIP,
    db_path: str | Path = DEFAULT_BIBLE_DB,
    repo_root: str | Path = ".",
    force: bool = False,
    batch_size: int = 10000,
) -> int:
    """Ingest Treasury of Scripture Knowledge cross references from zip into SQLite database."""
    root = Path(repo_root)
    target_db = root / db_path
    if not target_db.is_file():
        raise FileNotFoundError(
            f"Bible database missing at {target_db}. "
            "Compile KJV database first via python -m search.corpus.extract_kjv --compile."
        )

    # Check if table already populated before demanding source archive (offline-friendly)
    if not force:
        con_check = sqlite3.connect(str(target_db))
        try:
            cur = con_check.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='cross_references';"
            )
            if cur.fetchone()[0] > 0:
                count_cur = con_check.execute("SELECT count(*) FROM cross_references;")
                row_count = count_cur.fetchone()[0]
                if row_count > 300000:
                    print(f"cross_references table already populated ({row_count:,} rows). Use --force to re-ingest.")
                    return row_count
        finally:
            con_check.close()

    src_zip = root / zip_path
    if not src_zip.is_file():
        raise FileNotFoundError(
            f"TSK cross-references archive missing at {src_zip}. "
            "Run scripts/fetch_sources.sh to download pinned data."
        )

    start_time = time.time()
    con = sqlite3.connect(str(target_db))
    con.row_factory = sqlite3.Row

    try:
        with con:
            if force:
                con.execute("DROP TABLE IF EXISTS cross_references;")
                con.execute("DROP INDEX IF EXISTS idx_xrefs_from;")
                con.execute("DROP INDEX IF EXISTS idx_xrefs_to;")
            con.executescript(_TABLE_SCHEMA)

        # Performance optimizations for bulk insertion
        con.execute("PRAGMA synchronous = OFF;")
        con.execute("PRAGMA cache_size = 10000;")

        batch: list[tuple[str, str, int]] = []
        total_inserted = 0

        def flush():
            nonlocal total_inserted
            if batch:
                with con:
                    con.executemany(
                        "INSERT OR IGNORE INTO cross_references VALUES (?, ?, ?);",
                        batch,
                    )
                total_inserted += len(batch)
                batch.clear()

        with zipfile.ZipFile(src_zip) as zf:
            # Locate cross_references text file inside zip
            txt_name = next(
                (n for n in zf.namelist() if n.endswith("cross_references.txt")),
                None,
            )
            if not txt_name:
                raise ValueError(f"cross_references.txt not found inside archive: {src_zip}")

            with zf.open(txt_name) as f:
                header = f.readline()  # Skip TSV header
                for raw_line in f:
                    line = raw_line.decode("utf-8").strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        from_ref = norm_single_ref(parts[0])
                        to_ref = norm_target_ref(parts[1])
                        try:
                            votes = int(parts[2])
                        except ValueError:
                            votes = 0
                        batch.append((from_ref, to_ref, votes))
                        if len(batch) >= batch_size:
                            flush()

        flush()

        # Build indices post-insertion
        con.executescript(_INDICES_SCHEMA)
        con.execute("PRAGMA synchronous = NORMAL;")

        elapsed = time.time() - start_time
        print(f"Ingested {total_inserted:,} TSK cross-references into {target_db} in {elapsed:.2f}s.")
        return total_inserted
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest Treasury of Scripture Knowledge (TSK) cross references into BibleDB (ADR-026)."
    )
    parser.add_argument(
        "--zip",
        default=DEFAULT_TSK_ZIP,
        help=f"Path to cross-references.zip (default: {DEFAULT_TSK_ZIP})",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_BIBLE_DB,
        help=f"Path to SQLite bible.db (default: {DEFAULT_BIBLE_DB})",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-ingestion even if table exists",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Batch size for bulk insertion (default: 10000)",
    )
    args = parser.parse_args(argv)

    ingest_tsk_cross_references(
        zip_path=args.zip,
        db_path=args.db,
        repo_root=args.repo,
        force=args.force,
        batch_size=args.batch_size,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
