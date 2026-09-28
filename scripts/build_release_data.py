#!/usr/bin/env python3
"""build_release_data.py — Cross-platform deterministic release data bundler (WP-029 Phase 2, ADR-024).

Packages the sidecar data bundle for zero-Python standalone distribution:
- Vacuumed SQLite databases (data/bible.db, data/macula.db)
- Canonical derived lexicons (lexicons/*.json)
- Cryptographic SHA256SUMS manifest for bundle verification
- Content-level SQLite integrity manifest (INTEGRITY.json, ADR-027)
- Compressed distribution archives (tar.gz and/or zip)

NOTE: data/egw.db is STRICTLY EXCLUDED from release bundles (ADR-002, ADR-023).

Usage:
    python scripts/build_release_data.py                 # full build + tar.gz
    python scripts/build_release_data.py --no-archive    # assemble dist/data/ only
    python scripts/build_release_data.py --zip           # also create dist/data.zip
    python scripts/build_release_data.py --check [dir]   # verify existing data bundle
    python scripts/build_release_data.py --out-dir <dir> # custom output directory
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import zipfile

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


def sha256_file(path: Path) -> str:
    """Compute hex SHA-256 digest of a file in streaming chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(base_dir: Path, manifest_path: Path) -> None:
    """Verify all entries in SHA256SUMS match files in base_dir."""
    if not manifest_path.is_file():
        sys.stderr.write(f"ERROR: {manifest_path} not found.\n")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            expected_hash, rel_path = parts
            file_path = base_dir / rel_path.replace("/", os.sep)
            if not file_path.is_file():
                sys.stderr.write(f"ERROR: missing file in manifest: {rel_path}\n")
                sys.exit(1)
            actual_hash = sha256_file(file_path)
            if actual_hash.lower() != expected_hash.lower():
                sys.stderr.write(f"ERROR: checksum mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}\n")
                sys.exit(1)


def verify_bundle(target_dir: Path, repo_root: Path) -> None:
    """Verify an existing data bundle directory against SHA256SUMS and INTEGRITY.json."""
    print(f"Verifying data bundle at: {target_dir}")
    manifest_path = target_dir / "SHA256SUMS"
    verify_manifest(target_dir, manifest_path)

    # Check content integrity manifest for SQLite DBs
    integrity_path = target_dir / "INTEGRITY.json"
    bible_db = target_dir / "bible.db"
    macula_db = target_dir / "macula.db"

    if integrity_path.is_file():
        res = subprocess.run(
            [
                sys.executable,
                "-m",
                "search.validation.db_integrity",
                "--check",
                "--bible-db",
                str(bible_db),
                "--macula-db",
                str(macula_db),
                "--manifest",
                str(integrity_path),
            ],
            cwd=repo_root,
        )
        if res.returncode != 0:
            sys.stderr.write("ERROR: SQLite content integrity check failed.\n")
            sys.exit(1)
    elif bible_db.is_file() or macula_db.is_file():
        sys.stderr.write(f"ERROR: {target_dir} contains SQLite DBs but no INTEGRITY.json content manifest.\n")
        sys.exit(1)

    print("✔ Data bundle integrity verified successfully.")


def ensure_pinned_sources(repo_root: Path) -> None:
    """Ensure raw pinned sources are fetched and verified before compiling databases."""
    data_src = repo_root / "data"
    required = [
        data_src / "KJV-osis.json",
        data_src / "ASV.json",
        data_src / "BSB.json",
        data_src / "YLT.json",
        data_src / "cross-references.zip",
        data_src / "macula-greek" / "27-revelation.xml",
        data_src / "macula-hebrew" / "39-Mal-003-lowfat.xml",
    ]
    missing = [p for p in required if not p.exists()]
    if not missing:
        return

    print(f"   Missing {len(missing)} pinned source file(s); fetching via scripts/fetch_sources.sh...")
    bash_exe = shutil.which("bash")
    if not bash_exe and sys.platform == "win32":
        candidates: list[Path] = []
        git_cmd = shutil.which("git")
        if git_cmd:
            git_root = Path(git_cmd).resolve().parent.parent
            candidates.extend([git_root / "bin" / "bash.exe", git_root / "usr" / "bin" / "bash.exe"])
        for env_var, default in [("PROGRAMFILES", "C:\\Program Files"), ("PROGRAMFILES(X86)", "C:\\Program Files (x86)")]:
            base = Path(os.environ.get(env_var, default))
            candidates.extend([base / "Git" / "bin" / "bash.exe", base / "Git" / "usr" / "bin" / "bash.exe"])
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            candidates.extend([
                Path(local_app) / "Programs" / "Git" / "bin" / "bash.exe",
                Path(local_app) / "Programs" / "Git" / "usr" / "bin" / "bash.exe",
            ])
        for c in candidates:
            if c.is_file():
                bash_exe = str(c)
                break

    if not bash_exe:
        raise RuntimeError(
            "Cannot fetch raw sources: 'bash' executable not found on PATH. "
            "Please ensure Git or bash is installed."
        )

    fetch_script = repo_root / "scripts" / "fetch_sources.sh"
    if not fetch_script.is_file():
        raise FileNotFoundError(f"Fetch script not found: {fetch_script}")
    subprocess.run([bash_exe, fetch_script.as_posix()], cwd=repo_root, check=True)
    print("   ✔ Raw sources fetched and cryptographically verified.")


def assemble_data_bundle(out_dir: Path, repo_root: Path) -> None:
    """Compile, vacuum, and assemble the data bundle into out_dir."""
    data_src = repo_root / "data"
    lexicons_src = repo_root / "lexicons"

    print("==============================================================")
    print("Adventist Bible Study Tool — Release Data Bundler (ADR-024)")
    print("==============================================================")

    # 1. Verify source databases exist or compile them
    bible_db_src = data_src / "bible.db"
    macula_db_src = data_src / "macula.db"

    if not bible_db_src.is_file() or not macula_db_src.is_file():
        ensure_pinned_sources(repo_root)

    if not bible_db_src.is_file():
        print("1. data/bible.db not found; compiling from pinned sources...")
        subprocess.run([sys.executable, "-m", "search.corpus.extract_kjv", "--compile"], cwd=repo_root, check=True)
        subprocess.run([sys.executable, "-m", "search.corpus.extract_translations"], cwd=repo_root, check=True)
        subprocess.run([sys.executable, "-m", "search.corpus.extract_tsk"], cwd=repo_root, check=True)
    else:
        print("1. Found data/bible.db; ensuring TSK cross references...")
        subprocess.run([sys.executable, "-m", "search.corpus.extract_tsk"], cwd=repo_root, check=True)

    if not macula_db_src.is_file():
        print("   data/macula.db not found; compiling linguistic database...")
        subprocess.run([sys.executable, "-m", "search.macula.build_db", "--repo", str(repo_root)], cwd=repo_root, check=True)
    else:
        print("   Found data/macula.db.")

    # 2. Clean and prepare output directory
    print(f"2. Preparing output directory: {out_dir}")
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lexicons").mkdir(parents=True, exist_ok=True)

    # 3. Compact and copy SQLite databases via VACUUM INTO
    print("3. Compacting and copying SQLite databases...")
    candidate_dbs = ["bible.db", "macula.db"]
    if (data_src / "embeddings.db").is_file():
        candidate_dbs.append("embeddings.db")

    for db_name in candidate_dbs:
        src = data_src / db_name
        dst = out_dir / db_name
        print(f"   Compacting {db_name} -> {dst}...")
        con = sqlite3.connect(str(src))
        dst_escaped = str(dst).replace("'", "''")
        con.execute(f"VACUUM INTO '{dst_escaped}'")
        con.close()

        # Verify compacted integrity and ensure WAL mode is set
        chk_con = sqlite3.connect(str(dst))
        chk_con.execute("PRAGMA journal_mode = WAL;")
        chk_con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        quick_check = chk_con.execute("PRAGMA quick_check;").fetchall()
        chk_con.close()
        if quick_check != [("ok",)]:
            sys.stderr.write(f"ERROR: Integrity check failed for {dst}: {quick_check}\n")
            sys.exit(1)

        # Clean any left-over sidecar files from checkpointing
        for ext in ("-wal", "-shm"):
            p = Path(str(dst) + ext)
            if p.exists():
                p.unlink()
    print("   ✔ SQLite databases vacuumed, WAL-initialized, and verified.")

    # 4. Copy canonical derived lexicons and optional neural models
    print("4. Copying canonical lexicons...")
    json_count = 0
    for p in sorted(lexicons_src.glob("*.json")):
        shutil.copy2(p, out_dir / "lexicons" / p.name)
        json_count += 1
    print(f"   ✔ Copied {json_count} lexicon JSON artifacts.")

    for extra in ["prophetic_lexicon.json", "sanctuary_schema.json"]:
        extra_src = data_src / extra
        if extra_src.is_file():
            shutil.copy2(extra_src, out_dir / extra)
            print(f"   ✔ Copied {extra}.")

    models_src = data_src / "models"
    if models_src.is_dir():
        shutil.copytree(models_src, out_dir / "models", dirs_exist_ok=True)
        print("   ✔ Copied local ONNX neural models and tokenizers.")

    # Enforce copyright boundary tripwire (ADR-002, ADR-023, ADR-024)
    if (out_dir / "egw.db").exists():
        sys.stderr.write("FATAL: egw.db found in release bundle directory! Violates copyright boundary.\n")
        sys.exit(1)

    # 5. Generate content-level integrity manifest (ADR-027)
    print("5. Generating integrity manifests...")
    integrity_dst = out_dir / "INTEGRITY.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "search.validation.db_integrity",
            "--generate",
            "--bible-db",
            str(out_dir / "bible.db"),
            "--macula-db",
            str(out_dir / "macula.db"),
            "--manifest",
            str(integrity_dst),
        ],
        cwd=repo_root,
        check=True,
    )
    if not integrity_dst.is_file():
        sys.stderr.write("ERROR: SQLite DBs present but content manifest INTEGRITY.json not generated.\n")
        sys.exit(1)

    # 6. Byte manifest for JSON artifacts only
    manifest_entries: list[tuple[str, str]] = []
    for p in sorted((out_dir / "lexicons").glob("*.json")):
        rel = f"lexicons/{p.name}"
        manifest_entries.append((rel, sha256_file(p)))

    for extra in ["prophetic_lexicon.json", "sanctuary_schema.json"]:
        extra_file = out_dir / extra
        if extra_file.is_file():
            manifest_entries.append((extra, sha256_file(extra_file)))

    manifest_entries.sort(key=lambda x: x[0])
    manifest_path = out_dir / "SHA256SUMS"
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        for rel, h in manifest_entries:
            f.write(f"{h}  {rel}\n")
    print(f"   ✔ Content manifest + byte manifest created ({len(manifest_entries)} entries).")

    # 7. Self-verifying data bundle
    print("6. Self-verifying data bundle against manifests...")
    verify_bundle(out_dir, repo_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Adventist Bible Study Tool — Release Data Bundler (ADR-024)")
    parser.add_argument("--no-archive", action="store_true", help="Assemble dist/data/ without creating tar.gz")
    parser.add_argument("--zip", action="store_true", help="Create .zip archive alongside .tar.gz")
    parser.add_argument("--check", nargs="?", const="", default=None, help="Verify data bundle directory against SHA256SUMS")
    parser.add_argument("--out-dir", default=None, help="Destination directory for sidecar data (default: dist/data)")

    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent

    if args.check is not None:
        target = Path(args.check) if args.check else (repo_root / "dist" / "data")
        verify_bundle(target.resolve(), repo_root)
        return 0

    out_dir = Path(args.out_dir).resolve() if args.out_dir else (repo_root / "dist" / "data")
    assemble_data_bundle(out_dir, repo_root)

    archive_parent = out_dir.parent
    archive_base = out_dir.name

    if not args.no_archive:
        tar_path = archive_parent / f"{archive_base}.tar.gz"
        print(f"Creating compressed release archive: {tar_path}...")
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(out_dir, arcname=archive_base)
        sha = sha256_file(tar_path)
        (archive_parent / f"{archive_base}.tar.gz.sha256").write_text(f"{sha}\n", encoding="utf-8")
        print(f"   ✔ Archive created: {tar_path}")
        print(f"   SHA-256: {sha}")

    if args.zip:
        zip_path = archive_parent / f"{archive_base}.zip"
        print(f"Creating zip archive: {zip_path}...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(out_dir):
                for f in files:
                    full_p = Path(root) / f
                    arcname = full_p.relative_to(archive_parent).as_posix()
                    zf.write(full_p, arcname=arcname)
        sha = sha256_file(zip_path)
        (archive_parent / f"{archive_base}.zip.sha256").write_text(f"{sha}\n", encoding="utf-8")
        print(f"   ✔ Zip archive created: {zip_path}")
        print(f"   SHA-256: {sha}")

    print("==============================================================")
    print(f"Release data bundle ready in: {out_dir}")
    print("==============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
