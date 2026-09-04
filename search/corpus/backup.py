"""Portable Offline Backup and Restore Engine (ADR-0016).

Provides deterministic, offline-first export and restore of on-device study state
(Tier 2 SQLite databases, user annotations, and local manifests) into a single,
portable, cryptographically-verified compressed archive (.tar.gz).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tarfile
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_MANIFEST_NAME = "backup_manifest.json"
CURRENT_BACKUP_VERSION = "1.0"


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 hexadecimal digest of a file in 64KB chunks."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_stream_sha256(stream: io.BufferedIOBase | io.RawIOBase) -> tuple[str, int]:
    """Calculate the SHA-256 digest and byte size of an open binary stream."""
    sha256 = hashlib.sha256()
    total_bytes = 0
    while chunk := stream.read(65536):
        sha256.update(chunk)
        total_bytes += len(chunk)
    return sha256.hexdigest(), total_bytes


def checkpoint_sqlite_db(db_path: Path) -> None:
    """Flush pending WAL journal transactions into the primary database file."""
    if not db_path.exists() or not db_path.is_file():
        return
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    except (sqlite3.Error, OSError):
        pass
    finally:
        if conn is not None:
            conn.close()


def inspect_sqlite_db(db_path: Path) -> dict[str, Any]:
    """Inspect tables and row counts for inclusion in backup manifest."""
    stats: dict[str, Any] = {"file_name": db_path.name, "tables": {}}
    if not db_path.exists() or not db_path.is_file():
        return stats
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            # Skip internal FTS shadow tables from full scan
            if table.endswith(("_content", "_segments", "_segdir", "_docsize", "_stat", "_idx", "_data", "_config")):
                continue
            try:
                escaped_table = table.replace('"', '""')
                cursor.execute(f'SELECT COUNT(*) FROM "{escaped_table}"')
                row = cursor.fetchone()
                stats["tables"][table] = row[0] if row else 0
            except sqlite3.Error:
                pass
    except (sqlite3.Error, OSError):
        pass
    finally:
        if conn is not None:
            conn.close()
    return stats


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Ensure target_path does not escape outside base_dir (Zip/Tar Slip prevention)."""
    try:
        resolved_target = target_path.resolve()
        resolved_base = base_dir.resolve()
        return resolved_base in resolved_target.parents or resolved_base == resolved_target
    except (ValueError, RuntimeError):
        return False


def export_backup(
    output_path: Path | str,
    db_paths: list[Path | str] | None = None,
    user_data_paths: list[Path | str] | None = None,
    note: str = "",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Export on-device databases and user study data into a portable .tar.gz archive.

    Args:
        output_path: Destination path for the backup archive (.tar.gz).
        db_paths: Optional list of SQLite databases to include. Defaults to
                  data/egw.db, data/corpus.db, and data/macula.db if present.
        user_data_paths: Optional list of user annotation files/directories to bundle.
        note: Optional study or backup annotation.
        repo_root: Base repository root directory. Defaults to REPO_ROOT.

    Returns:
        The generated manifest dictionary.
    """
    root = (repo_root or REPO_ROOT).resolve()
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    # Determine default databases to bundle
    if db_paths is None:
        candidate_dbs = [
            root / "data" / "egw.db",
            root / "data" / "corpus.db",
            root / "data" / "macula.db",
        ]
        active_dbs = [p for p in candidate_dbs if p.exists() and p.is_file()]
    else:
        active_dbs = [Path(p).resolve() for p in db_paths if Path(p).exists() and Path(p).is_file()]

    active_user_paths: list[Path] = []
    if user_data_paths:
        for p in user_data_paths:
            resolved = Path(p).resolve()
            if resolved.exists():
                active_user_paths.append(resolved)

    # Checkpoint all active SQLite databases before archiving
    for db in active_dbs:
        checkpoint_sqlite_db(db)

    db_stats: dict[str, Any] = {}
    files_manifest: list[dict[str, Any]] = []

    # Temporary staging for archive construction
    tmp_out = out.parent / f"{out.name}.tmp.{os.getpid()}"

    try:
        with tarfile.open(tmp_out, "w:gz") as tar:
            # 1. Bundle SQLite databases
            for db in active_dbs:
                rel_to_root = db.relative_to(root) if root in db.parents else Path("data") / db.name
                arcname = f"databases/{db.name}"
                sha256 = calculate_sha256(db)
                size_bytes = db.stat().st_size
                stats = inspect_sqlite_db(db)
                db_stats[db.name] = stats

                files_manifest.append({
                    "arcname": arcname,
                    "target_relpath": str(rel_to_root),
                    "size_bytes": size_bytes,
                    "sha256": sha256,
                    "type": "database",
                })
                tar.add(str(db), arcname=arcname)

            # 2. Bundle user annotations / extra files
            for up in active_user_paths:
                if up.is_file():
                    if root in up.parents:
                        rel_to_root = up.relative_to(root)
                        arcname = f"user_data/{rel_to_root}"
                    else:
                        rel_to_root = Path("user_data") / up.name
                        arcname = f"user_data/{up.name}"
                    sha256 = calculate_sha256(up)
                    size_bytes = up.stat().st_size
                    files_manifest.append({
                        "arcname": arcname,
                        "target_relpath": str(rel_to_root),
                        "size_bytes": size_bytes,
                        "sha256": sha256,
                        "type": "user_data",
                    })
                    tar.add(str(up), arcname=arcname)
                elif up.is_dir():
                    for child in sorted(up.rglob("*")):
                        if child.is_file():
                            rel_to_dir = child.relative_to(up)
                            rel_to_root = child.relative_to(root) if root in child.parents else Path("user_data") / up.name / rel_to_dir
                            arcname = f"user_data/{up.name}/{rel_to_dir}"
                            sha256 = calculate_sha256(child)
                            size_bytes = child.stat().st_size
                            files_manifest.append({
                                "arcname": arcname,
                                "target_relpath": str(rel_to_root),
                                "size_bytes": size_bytes,
                                "sha256": sha256,
                                "type": "user_data",
                            })
                            tar.add(str(child), arcname=arcname)

            # 3. Create manifest and add to root of tar archive
            manifest_data: dict[str, Any] = {
                "version": CURRENT_BACKUP_VERSION,
                "generator": "adventist-bible-study-tool/backup-engine (ADR-0016)",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "note": note,
                "file_count": len(files_manifest),
                "db_stats": db_stats,
                "files": files_manifest,
            }

            manifest_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")
            tarinfo = tarfile.TarInfo(name=BACKUP_MANIFEST_NAME)
            tarinfo.size = len(manifest_bytes)
            tarinfo.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(tarinfo, io.BytesIO(manifest_bytes))

        # Atomic replace
        tmp_out.replace(out)

    finally:
        if tmp_out.exists():
            try:
                tmp_out.unlink()
            except OSError:
                pass

    return manifest_data


def inspect_backup(archive_path: Path | str) -> dict[str, Any]:
    """Inspect and return the manifest dictionary from a backup archive without extracting files."""
    arch = Path(archive_path).resolve()
    if not arch.exists() or not arch.is_file():
        raise FileNotFoundError(f"Backup archive not found: {arch}")

    with tarfile.open(arch, "r:gz") as tar:
        try:
            member = tar.getmember(BACKUP_MANIFEST_NAME)
        except KeyError:
            raise ValueError(f"Invalid backup archive: missing {BACKUP_MANIFEST_NAME}")

        fileobj = tar.extractfile(member)
        if fileobj is None:
            raise ValueError(f"Failed to read {BACKUP_MANIFEST_NAME} from archive")

        manifest_data = json.loads(fileobj.read().decode("utf-8"))
        return manifest_data


def verify_backup(archive_path: Path | str) -> tuple[bool, list[str]]:
    """Verify cryptographic checksums and completeness of all files in the archive.

    Returns:
        Tuple of (is_valid, list_of_error_strings).
    """
    arch = Path(archive_path).resolve()
    if not arch.exists() or not arch.is_file():
        return False, [f"Archive does not exist: {arch}"]

    errors: list[str] = []
    try:
        manifest = inspect_backup(arch)
    except Exception as e:
        return False, [f"Manifest inspection error: {e}"]

    manifest_files = {f["arcname"]: f for f in manifest.get("files", [])}

    with tarfile.open(arch, "r:gz") as tar:
        for arcname, file_info in manifest_files.items():
            try:
                member = tar.getmember(arcname)
            except KeyError:
                errors.append(f"Missing file in archive: {arcname}")
                continue

            fileobj = tar.extractfile(member)
            if fileobj is None:
                errors.append(f"Cannot extract file stream: {arcname}")
                continue

            actual_hash, actual_bytes = calculate_stream_sha256(fileobj)
            expected_hash = file_info.get("sha256")
            expected_bytes = file_info.get("size_bytes")

            if actual_bytes != expected_bytes:
                errors.append(
                    f"Size mismatch for {arcname}: expected {expected_bytes} bytes, got {actual_bytes}"
                )
            if actual_hash != expected_hash:
                errors.append(
                    f"Checksum mismatch for {arcname}: expected {expected_hash}, got {actual_hash}"
                )

    return (len(errors) == 0, errors)


def restore_backup(
    archive_path: Path | str,
    target_dir: Path | str | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Restore a backup archive to target directory with cryptographic verification.

    Args:
        archive_path: Path to the backup archive (.tar.gz).
        target_dir: Destination base directory. Defaults to REPO_ROOT.
        overwrite: If True, existing files will be replaced. If False, raises FileExistsError.
        dry_run: If True, performs verification and returns planned actions without writing.

    Returns:
        Dictionary summarizing the restoration results.
    """
    arch = Path(archive_path).resolve()
    dest = (target_dir or REPO_ROOT).resolve()

    # Step 1: Pre-flight cryptographic integrity check
    is_valid, errors = verify_backup(arch)
    if not is_valid:
        raise ValueError(f"Backup verification failed prior to restore:\n" + "\n".join(errors))

    manifest = inspect_backup(arch)
    files = manifest.get("files", [])

    planned_restorations: list[dict[str, Any]] = []

    # Step 2: Validate target paths and check for overwrites
    for file_info in files:
        arcname = file_info["arcname"]
        target_rel = file_info["target_relpath"]
        target_file = (dest / target_rel).resolve()

        # Zip Slip security defense
        if not is_safe_path(dest, target_file):
            raise SecurityError(
                f"Path traversal security violation in archive: {target_rel} resolves outside {dest}"
            )

        exists = target_file.exists()
        if exists and not overwrite and not dry_run:
            raise FileExistsError(
                f"Destination file already exists: {target_file}. Pass overwrite=True or --overwrite to replace."
            )

        planned_restorations.append({
            "arcname": arcname,
            "target_path": str(target_file),
            "size_bytes": file_info["size_bytes"],
            "sha256": file_info["sha256"],
            "already_exists": exists,
        })

    if dry_run:
        return {
            "status": "dry_run_success",
            "archive": str(arch),
            "target_dir": str(dest),
            "files_to_restore": len(planned_restorations),
            "details": planned_restorations,
        }

    # Step 3: Atomic extraction via temporary staging directory inside dest
    dest.mkdir(parents=True, exist_ok=True)
    staging_dir = tempfile.mkdtemp(prefix=".bst_restore_stage_", dir=dest)
    stage_path = Path(staging_dir)

    restored_files: list[str] = []
    try:
        with tarfile.open(arch, "r:gz") as tar:
            for item in planned_restorations:
                arcname = item["arcname"]
                staged_file = (stage_path / arcname).resolve()

                # Guard staging extraction against zip-slip, absolute paths, and non-regular members
                if not is_safe_path(stage_path, staged_file) or Path(arcname).is_absolute():
                    raise SecurityError(f"Path traversal detected in archive member name: {arcname}")

                member = tar.getmember(arcname)
                if not member.isreg():
                    raise SecurityError(f"Archive member is not a regular file: {arcname}")

                staged_file.parent.mkdir(parents=True, exist_ok=True)
                src = tar.extractfile(member)
                if src is None:
                    raise ValueError(f"Cannot extract stream for: {arcname}")
                with src, open(staged_file, "wb") as dst:
                    shutil.copyfileobj(src, dst)

                # Post-extraction disk verification
                actual_hash = calculate_sha256(staged_file)
                if actual_hash != item["sha256"]:
                    raise ValueError(
                        f"Post-extraction checksum mismatch for {arcname}: expected {item['sha256']}, got {actual_hash}"
                    )

        # Step 4: Move from staging to final destinations atomically
        for item in planned_restorations:
            arcname = item["arcname"]
            staged_file = (stage_path / arcname).resolve()
            target_path = Path(item["target_path"])
            target_path.parent.mkdir(parents=True, exist_ok=True)

            os.replace(staged_file, target_path)
            restored_files.append(str(target_path))

    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    return {
        "status": "restored",
        "archive": str(arch),
        "target_dir": str(dest),
        "files_restored": len(restored_files),
        "restored_paths": restored_files,
        "manifest": manifest,
    }


class SecurityError(Exception):
    """Raised when an archive member attempts a path traversal / zip slip attack."""
    pass
