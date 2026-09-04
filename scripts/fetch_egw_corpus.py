#!/usr/bin/env python3
"""Automated Harvester for the Complete Official English EGW Corpus (Step 1b, WP-017).

Downloads and categorizes verified English publications from the official
White Estate / EGW Writings media CDN (https://media2.egwwritings.org) into
structured folders under data/egw-sources/.

Supported formats:
  - EPUB (default): lightweight (~160 MB for full corpus), cleanly parseable into
    structured paragraphs, chapters, and page anchors via EpubParser.
  - PDF: exact archival facsimile reproduction.
  - BOTH: download both EPUB and PDF.

Features:
  - Zero external dependencies: pure Python standard library (urllib.request, zipfile, time).
  - Resilient networking: exponential backoff retries on transient 429, 503, and socket timeouts.
  - Atomic staging: downloads to .tmp and replaces atomically; skips valid cached files.
  - Category routing: mirrors archival organization (Books, Devotionals, Biographies,
    Manuscript Releases, Periodicals, Special Collections, Pamphlets).
  - Ingestion flag (--ingest): directly parses and indexes downloaded EPUBs into data/egw.db.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST_DIR = _REPO_ROOT / "data" / "egw-sources"

EPUB_CDN = "https://media2.egwwritings.org/epub/"
PDF_CDN = "https://media2.egwwritings.org/pdf/"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/octet-stream, application/pdf, */*",
    "Referer": "https://egwwritings.org/",
}

# -----------------------------------------------------------------------------
# Curated Corpus Classifications & Publication Codes
# -----------------------------------------------------------------------------

from search.linking.egw import (
    BIOGRAPHIES,
    DEVOTIONALS,
    MR_CODES,
    PAMPHLET_CODES,
    PERIODICAL_CODES,
    SPECIAL_COLLECTIONS,
    STANDARD_BOOKS,
)


def resolve_category_path(code: str) -> Path:
    """Map a publication code to its archival category subfolder."""
    # 1. Manuscript Releases (1MR - 21MR)
    if re.fullmatch(r"\d+MR", code):
        return Path("02_Manuscript_Releases")

    # 2. Periodicals
    if code in PERIODICAL_CODES:
        return Path("03_Periodical_Articles")

    # 3. Special Collections & Sermons
    if code in SPECIAL_COLLECTIONS:
        return Path("04_Special_Collections_and_Sermons")

    # 4. Pamphlets & Special Testimonies
    if code.startswith("SpTA"):
        return Path("05_Pamphlets_and_Special_Testimonies/Special_Testimonies_Series_A")
    if code.startswith("SpTB"):
        return Path("05_Pamphlets_and_Special_Testimonies/Special_Testimonies_Series_B")
    if code == "SpTEd":
        return Path("05_Pamphlets_and_Special_Testimonies")
    if code.startswith("PH"):
        return Path("05_Pamphlets_and_Special_Testimonies/Numbered_Pamphlets")

    # 5. Core Books & Compilations (with sub-groupings)
    if code in DEVOTIONALS:
        return Path("01_Books_and_Compilations/Devotionals")
    if code in BIOGRAPHIES:
        return Path("01_Books_and_Compilations/Biographies")

    return Path("01_Books_and_Compilations")


def get_curated_corpus(category: str | None = None) -> dict[str, Path]:
    """Return publication codes mapped to their relative directory paths."""
    corpus: dict[str, Path] = {}

    mr_codes = MR_CODES
    pamphlet_codes = PAMPHLET_CODES

    cat_lower = (category or "all").lower().strip()

    if cat_lower in ("all", "books"):
        for code in STANDARD_BOOKS:
            corpus[code] = resolve_category_path(code)

    if cat_lower in ("all", "devotionals"):
        for code in sorted(DEVOTIONALS):
            corpus[code] = resolve_category_path(code)

    if cat_lower in ("all", "biographies"):
        for code in sorted(BIOGRAPHIES):
            corpus[code] = resolve_category_path(code)

    if cat_lower in ("all", "manuscripts", "mr"):
        for code in mr_codes:
            corpus[code] = resolve_category_path(code)

    if cat_lower in ("all", "periodicals"):
        for code in sorted(PERIODICAL_CODES):
            corpus[code] = resolve_category_path(code)

    if cat_lower in ("all", "special"):
        for code in sorted(SPECIAL_COLLECTIONS):
            corpus[code] = resolve_category_path(code)

    if cat_lower in ("all", "pamphlets"):
        for code in pamphlet_codes:
            corpus[code] = resolve_category_path(code)

    return corpus


# -----------------------------------------------------------------------------
# Resilient Downloader with Exponential Backoff
# -----------------------------------------------------------------------------

def download_file(
    url: str,
    dest_path: Path,
    timeout: int = 30,
    max_retries: int = 3,
    chunk_size: int = 65536,
) -> bool | None:
    """Download file with exponential backoff retries.

    Returns:
        True: Downloaded successfully.
        False: Skipped (already cached with valid size).
        None: Omitted (HTTP 404 Not Found, e.g. gap in pamphlet sequence).
    """
    if dest_path.is_file() and dest_path.stat().st_size > 100:
        if dest_path.suffix.lower() == ".epub" and not zipfile.is_zipfile(dest_path):
            pass  # Corrupt EPUB cache, re-download
        elif dest_path.suffix.lower() == ".pdf":
            try:
                with open(dest_path, "rb") as pf:
                    if pf.read(5) != b"%PDF-":
                        pass  # Corrupt PDF cache, re-download
                    else:
                        return False
            except Exception:
                pass
        else:
            return False

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_name(f"{dest_path.name}.tmp")

    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)

    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                if status == 404:
                    return None
                with open(temp_path, "wb") as f:
                    while chunk := resp.read(chunk_size):
                        f.write(chunk)

            # Validate EPUB if applicable
            if dest_path.suffix.lower() == ".epub":
                if not zipfile.is_zipfile(temp_path):
                    if temp_path.exists():
                        temp_path.unlink()
                    if attempt < max_retries:
                        sleep_sec = 2 ** attempt
                        sys.stderr.write(f"  [RETRY] Incomplete zip archive for {dest_path.name}; retrying in {sleep_sec}s (attempt {attempt}/{max_retries})...\n")
                        time.sleep(sleep_sec)
                        continue
                    sys.stderr.write(f"  [WARN] Corrupt zip archive for {dest_path.name}, skipping.\n")
                    return None

            # Validate PDF header if applicable
            if dest_path.suffix.lower() == ".pdf":
                try:
                    with open(temp_path, "rb") as pf:
                        header = pf.read(5)
                    if header != b"%PDF-":
                        if temp_path.exists():
                            temp_path.unlink()
                        if attempt < max_retries:
                            sleep_sec = 2 ** attempt
                            sys.stderr.write(f"  [RETRY] Incomplete PDF header for {dest_path.name}; retrying in {sleep_sec}s (attempt {attempt}/{max_retries})...\n")
                            time.sleep(sleep_sec)
                            continue
                        sys.stderr.write(f"  [WARN] Invalid PDF header for {dest_path.name}, skipping.\n")
                        return None
                except Exception:
                    if temp_path.exists():
                        temp_path.unlink()
                    return None

            temp_path.replace(dest_path)
            return True

        except urllib.error.HTTPError as ex:
            if ex.code == 404:
                if temp_path.exists():
                    temp_path.unlink()
                return None
            if ex.code in (429, 500, 502, 503, 504):
                retry_after = ex.headers.get("Retry-After") if hasattr(ex, "headers") and ex.headers else None
                if retry_after and retry_after.isdigit():
                    sleep_sec = max(int(retry_after), 2 ** attempt)
                else:
                    sleep_sec = 2 ** attempt
                sys.stderr.write(f"  [RETRY] HTTP {ex.code} for {dest_path.name}; retrying in {sleep_sec}s (attempt {attempt}/{max_retries})...\n")
                time.sleep(sleep_sec)
                continue
            if temp_path.exists():
                temp_path.unlink()
            sys.stderr.write(f"  [ERROR] HTTP {ex.code} for {dest_path.name}: {ex.reason}\n")
            return None

        except (urllib.error.URLError, TimeoutError) as ex:
            sleep_sec = 2 ** attempt
            sys.stderr.write(f"  [RETRY] Network error for {dest_path.name}: {ex}; retrying in {sleep_sec}s (attempt {attempt}/{max_retries})...\n")
            time.sleep(sleep_sec)
            continue

        except Exception as ex:
            if temp_path.exists():
                temp_path.unlink()
            sys.stderr.write(f"  [ERROR] Failed {dest_path.name}: {ex}\n")
            return None

    if temp_path.exists():
        temp_path.unlink()
    return None


# -----------------------------------------------------------------------------
# Main Execution CLI
# -----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download and catalog the complete official English Ellen G. White corpus from media2.egwwritings.org."
    )
    parser.add_argument(
        "--category",
        choices=["all", "books", "devotionals", "biographies", "manuscripts", "periodicals", "special", "pamphlets"],
        default="all",
        help="Filter downloads to a specific archival category (default: all)",
    )
    parser.add_argument(
        "--code",
        help="Download a specific publication code (e.g. 10MR, DA, PP, SpTA01)",
    )
    parser.add_argument(
        "--format",
        choices=["epub", "pdf", "both"],
        default="epub",
        help="Target format to download (default: epub — lightweight and parseable)",
    )
    parser.add_argument(
        "--dest-dir",
        default=str(DEFAULT_DEST_DIR),
        help=f"Target directory for downloaded corpus (default: {DEFAULT_DEST_DIR})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.6,
        help="Polite delay in seconds between downloads (default: 0.6s)",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Immediately ingest all downloaded EPUB files into data/egw.db",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DEST_DIR.parent / "egw.db"),
        help="Target SQLite database for ingested paragraphs (default: data/egw.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display target download list without downloading files",
    )

    args = parser.parse_args(argv)
    dest_base = Path(args.dest_dir)
    dest_base.mkdir(parents=True, exist_ok=True)

    # 1. Resolve publication list
    if args.code:
        code = args.code.strip()
        corpus_map = {code: resolve_category_path(code)}
    else:
        corpus_map = get_curated_corpus(args.category)

    total_works = len(corpus_map)
    formats = ["epub", "pdf"] if args.format == "both" else [args.format]

    print("=" * 70)
    print(f"Official EGW Corpus Harvester (Step 1b)")
    print(f"Target Directory: {dest_base}")
    print(f"Category Scope:   {args.category}")
    print(f"Selected Works:   {total_works} publication codes")
    print(f"Target Formats:   {', '.join(formats).upper()}")
    print("=" * 70 + "\n")

    if args.dry_run:
        print("DRY-RUN: Listing resolved files to download:")
        for idx, (code, rel_folder) in enumerate(sorted(corpus_map.items()), 1):
            for fmt in formats:
                fname = f"en_{code}.{fmt}"
                target_file = dest_base / rel_folder / fname
                print(f"  {idx:03d}. [{fmt.upper()}] {rel_folder / fname}")
        return 0

    downloaded_count = 0
    cached_count = 0
    missing_count = 0

    downloaded_epubs: list[Path] = []

    for idx, (code, rel_folder) in enumerate(sorted(corpus_map.items()), 1):
        for fmt in formats:
            base_url = EPUB_CDN if fmt == "epub" else PDF_CDN
            fname = f"en_{code}.{fmt}"
            file_url = urllib.parse.urljoin(base_url, fname)
            dest_file = dest_base / rel_folder / fname

            prefix = f"[{idx:03d}/{total_works}]"
            res = download_file(file_url, dest_file)

            if res is True:
                sz_kb = dest_file.stat().st_size / 1024
                print(f"{prefix} [OK] {fname:<14} -> {rel_folder} ({sz_kb:.1f} KB)")
                downloaded_count += 1
                if fmt == "epub":
                    downloaded_epubs.append(dest_file)
                time.sleep(args.delay)
            elif res is False:
                sz_kb = dest_file.stat().st_size / 1024
                print(f"{prefix} [CACHE] {fname:<14} ({sz_kb:.1f} KB)")
                cached_count += 1
                if fmt == "epub":
                    downloaded_epubs.append(dest_file)
            else:
                # 404 or missing
                missing_count += 1

    print("\n" + "=" * 70)
    print("Download Summary:")
    print(f"  ✔ Newly Downloaded: {downloaded_count}")
    print(f"  ✔ Already Cached:    {cached_count}")
    print(f"  - Omitted (404/gap): {missing_count}")
    print("=" * 70)

    # 2. Ingest into egw.db if requested
    if args.ingest and downloaded_epubs:
        print(f"\nIngesting {len(downloaded_epubs)} EPUB files into database...")
        from search.linking.egw import EgwDB
        from search.linking.egw_importer import BulkImporter

        target_db = Path(args.db_path)
        db = EgwDB(target_db, repo_root=_REPO_ROOT)
        db.init_db()

        importer = BulkImporter(db)
        results = importer.import_files(downloaded_epubs, fast=True)
        total_paras = sum(max(0, c) for c in results.values())
        succeeded = sum(1 for c in results.values() if c > 0)

        print(f"\n✔ Successfully ingested {total_paras} paragraphs across {succeeded} volumes into {db.db_path}!")
        print(f"✔ Current total database paragraph count: {db.count()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
