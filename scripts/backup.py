#!/usr/bin/env python3
"""CLI utility for Portable Offline Backup and Restore (ADR-0016).

Usage:
  # Export default study state (egw.db, corpus.db, macula.db):
  python scripts/backup.py export -o my_study_backup.tar.gz --note "Full study library"

  # Inspect an existing backup archive:
  python scripts/backup.py inspect my_study_backup.tar.gz

  # Cryptographically verify archive integrity:
  python scripts/backup.py verify my_study_backup.tar.gz

  # Restore backup archive to another machine or folder:
  python scripts/backup.py restore my_study_backup.tar.gz --overwrite
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from search.corpus.backup import (
    CURRENT_BACKUP_VERSION,
    export_backup,
    inspect_backup,
    restore_backup,
    verify_backup,
)


def format_bytes(bytes_count: int) -> str:
    """Format bytes into human-readable size string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}" if unit != "B" else f"{bytes_count} B"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} TB"


def handle_export(args: argparse.Namespace) -> int:
    """Handle export subcommand."""
    repo_root = Path(args.repo_root).resolve() if getattr(args, "repo_root", None) else REPO_ROOT
    out_path = args.output
    if not out_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = f"data/study_backup_{ts}.tar.gz"

    db_paths: list[Path] = []
    root_data = repo_root / "data"

    if not args.sources_only:
        if args.include_egw and (root_data / "egw.db").exists():
            db_paths.append(root_data / "egw.db")
        if args.include_corpus and (root_data / "corpus.db").exists():
            db_paths.append(root_data / "corpus.db")
        if args.include_macula and (root_data / "macula.db").exists():
            db_paths.append(root_data / "macula.db")

        resolved_dbs = {p.resolve() for p in db_paths}
        if args.db:
            for db in args.db:
                p = Path(db).resolve()
                if p.exists() and p.is_file():
                    if p not in resolved_dbs:
                        db_paths.append(p)
                        resolved_dbs.add(p)
                else:
                    print(f"[!] Warning: Specified database not found: {db}", file=sys.stderr)

    user_paths: list[Path] = []
    resolved_users: set[Path] = set()
    if args.user_data:
        for up in args.user_data:
            p = Path(up).resolve()
            if p.exists():
                if p not in resolved_users:
                    user_paths.append(p)
                    resolved_users.add(p)
            else:
                print(f"[!] Warning: Specified user data path not found: {up}", file=sys.stderr)

    source_paths: list[Path] | None = None
    if args.sources:
        source_paths = []
        for sp in args.sources:
            p = Path(sp).resolve()
            if p.exists():
                source_paths.append(p)
            else:
                print(f"[!] Warning: Specified source path not found: {sp}", file=sys.stderr)

    include_sources = args.include_sources or args.sources_only or (source_paths is not None)

    if not db_paths and not user_paths and not include_sources:
        print("[!] No databases, user data files, or sources found to back up.", file=sys.stderr)
        return 1

    mode_label = "Complete" if (db_paths and include_sources) else ("Sources-Only" if args.sources_only else "Index-Only")
    print(f"[*] Packaging {mode_label} backup archive: {out_path}")
    if db_paths:
        print(f"    Databases: {', '.join(p.name for p in db_paths)}")
    if user_paths:
        print(f"    User Data: {', '.join(p.name for p in user_paths)}")
    if include_sources:
        print(f"    Sources:   Raw BYOD bookshelf included")

    manifest = export_backup(
        output_path=out_path,
        db_paths=db_paths,
        user_data_paths=user_paths,
        source_paths=source_paths,
        include_sources=include_sources,
        note=args.note or "",
        repo_root=repo_root,
    )

    total_bytes = sum(f["size_bytes"] for f in manifest["files"])
    arch_size = Path(out_path).stat().st_size
    actual_mode = manifest.get("mode", "index_only").replace("_", "-").title()
    print(f"\n[✓] {actual_mode} backup created successfully!")
    print(f"    Archive Path: {Path(out_path).resolve()}")
    print(f"    Archive Size: {format_bytes(arch_size)} (uncompressed: {format_bytes(total_bytes)})")
    print(f"    Files Bundled: {len(manifest['files'])}")

    if manifest.get("db_stats"):
        print("\n--- Database Overview ---")
        for db_name, stats in manifest["db_stats"].items():
            tables_summary = ", ".join(f"{t}: {count:,}" for t, count in stats.get("tables", {}).items())
            print(f"  • {db_name}: {tables_summary or 'no tables'}")

    return 0


def handle_inspect(args: argparse.Namespace) -> int:
    """Handle inspect subcommand."""
    archive_path = Path(args.archive)
    if not archive_path.exists():
        print(f"[!] Archive not found: {archive_path}", file=sys.stderr)
        return 1

    try:
        manifest = inspect_backup(archive_path)
    except Exception as e:
        print(f"[!] Failed to inspect archive: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(manifest, indent=2))
        return 0

    print(f"=== Backup Archive Inspection ===")
    print(f"Archive:       {archive_path.resolve()}")
    print(f"Version:       {manifest.get('version', 'unknown')}")
    print(f"Mode:          {manifest.get('mode', 'index_only').upper()}")
    print(f"Generator:     {manifest.get('generator', 'unknown')}")
    print(f"Created At:    {manifest.get('created_at', 'unknown')}")
    if manifest.get("note"):
        print(f"Note:          {manifest.get('note')}")

    files = manifest.get("files", [])
    types_count: dict[str, int] = {}
    for f in files:
        t = f.get("type", "file")
        types_count[t] = types_count.get(t, 0) + 1
    label_map = {"database": "databases", "source": "sources", "user_data": "user data files"}
    types_str = ", ".join(f"{cnt} {label_map.get(t, t + 's') if cnt != 1 else t}" for t, cnt in types_count.items())
    print(f"File Count:    {manifest.get('file_count', len(files))} ({types_str or 'empty'})")

    if files:
        print("\n--- Bundled Files ---")
        for f in files:
            print(f"  • {f['arcname']} -> {f['target_relpath']}")
            print(f"    Size: {format_bytes(f['size_bytes'])} | SHA-256: {f['sha256'][:16]}...")

    db_stats = manifest.get("db_stats", {})
    if db_stats:
        print("\n--- Database Statistics ---")
        for db_name, stats in db_stats.items():
            print(f"  Database: {db_name}")
            for tbl, cnt in stats.get("tables", {}).items():
                print(f"    - {tbl}: {cnt:,} rows")

    return 0


def handle_verify(args: argparse.Namespace) -> int:
    """Handle verify subcommand."""
    archive_path = Path(args.archive)
    print(f"[*] Verifying archive integrity: {archive_path}")

    is_valid, errors = verify_backup(archive_path)
    if is_valid:
        print(f"[✓] Archive integrity verified! All cryptographic checksums match.")
        return 0
    else:
        print(f"[!] Archive integrity verification FAILED:", file=sys.stderr)
        for err in errors:
            print(f"    - {err}", file=sys.stderr)
        return 1


def handle_restore(args: argparse.Namespace) -> int:
    """Handle restore subcommand."""
    archive_path = Path(args.archive)
    target_dir = Path(args.target_dir) if args.target_dir else REPO_ROOT

    print(f"[*] Restoring backup from: {archive_path}")
    print(f"    Target Directory:     {target_dir.resolve()}")
    if args.dry_run:
        print(f"    Mode:                 DRY RUN (simulation)")

    try:
        res = restore_backup(
            archive_path=archive_path,
            target_dir=target_dir,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    except FileExistsError as e:
        print(f"[!] Restore halted: {e}", file=sys.stderr)
        print("    Pass --overwrite to replace existing files.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[!] Restore failed: {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"\n[✓] Dry run succeeded! {res['files_to_restore']} files would be restored.")
        for item in res.get("details", []):
            status = "[exists, will overwrite]" if item["already_exists"] else "[new]"
            print(f"    - {item['target_path']} {status}")
    else:
        print(f"\n[✓] Restore complete! {res['files_restored']} files successfully extracted and verified.")
        for p in res.get("restored_paths", []):
            print(f"    - {p}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Portable Offline Backup and Restore utility for Adventist Bible Study Tool (ADR-0016)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # export
    exp_parser = subparsers.add_parser("export", help="Export on-device databases and study state to .tar.gz")
    exp_parser.add_argument("-o", "--output", help="Output archive path (default: data/study_backup_<timestamp>.tar.gz)")
    exp_parser.add_argument("--note", help="Optional descriptive note for the backup")
    exp_parser.add_argument("--include-egw", action="store_true", default=True, help="Include data/egw.db (default)")
    exp_parser.add_argument("--no-egw", action="store_false", dest="include_egw", help="Exclude data/egw.db")
    exp_parser.add_argument("--include-corpus", action="store_true", default=True, help="Include data/corpus.db (default)")
    exp_parser.add_argument("--no-corpus", action="store_false", dest="include_corpus", help="Exclude data/corpus.db")
    exp_parser.add_argument("--include-macula", action="store_true", default=True, help="Include data/macula.db (default)")
    exp_parser.add_argument("--no-macula", action="store_false", dest="include_macula", help="Exclude data/macula.db")

    mode_group = exp_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--include-sources", "--complete",
        action="store_true",
        dest="include_sources",
        help="Complete Backup: bundle raw BYOD bookshelf (data/egw-sources, etc.) alongside databases",
    )
    mode_group.add_argument(
        "--sources-only",
        action="store_true",
        help="Sources-Only mode: bundle only raw BYOD source files without SQLite databases",
    )

    exp_parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Specific raw source directory or file to include (can specify multiple times)",
    )
    exp_parser.add_argument("--db", action="append", help="Additional SQLite database path to include")
    exp_parser.add_argument("--user-data", action="append", help="Additional user annotation file/dir to include")
    exp_parser.add_argument("--repo-root", help="Custom repository root directory (default: project root)")

    # inspect
    insp_parser = subparsers.add_parser("inspect", help="Inspect backup archive manifest and statistics")
    insp_parser.add_argument("archive", help="Path to .tar.gz backup archive")
    insp_parser.add_argument("--json", action="store_true", help="Output raw JSON manifest")

    # verify
    ver_parser = subparsers.add_parser("verify", help="Verify cryptographic SHA-256 integrity of backup archive")
    ver_parser.add_argument("archive", help="Path to .tar.gz backup archive")

    # restore
    res_parser = subparsers.add_parser("restore", help="Restore backup archive to target directory")
    res_parser.add_argument("archive", help="Path to .tar.gz backup archive")
    res_parser.add_argument("--target-dir", help="Target extraction directory (default: repository root)")
    res_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files at destination")
    res_parser.add_argument("--dry-run", action="store_true", help="Simulate restore and verify without writing files")

    args = parser.parse_args()

    if args.command == "export":
        return handle_export(args)
    elif args.command == "inspect":
        return handle_inspect(args)
    elif args.command == "verify":
        return handle_verify(args)
    elif args.command == "restore":
        return handle_restore(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
