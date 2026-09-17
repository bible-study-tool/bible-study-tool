#!/usr/bin/env python3
"""build_release.py — Cross-platform unified release packaging pipeline (WP-029 Phase 3, ADR-024).

Builds the standalone zero-Python distribution for Windows, Linux, and macOS:
1. Runs pre-flight test verification (unless --skip-tests)
2. Freezes application binary with PyInstaller (via bible_study.spec)
3. Assembles release layout:
     <release_root>/
     ├── bible-study[.exe]        # Standalone executable
     ├── _internal/               # Bundled runtime and web assets
     ├── data/                    # Sidecar databases & lexicons (ADR-024)
     │   ├── bible.db
     │   ├── macula.db
     │   ├── INTEGRITY.json       # Content-level SQLite manifest (ADR-027)
     │   ├── SHA256SUMS           # Lexicon byte manifest
     │   └── lexicons/
     ├── SHA256SUMS               # Release-wide integrity manifest
     ├── README.md
     └── NOTICE.md
4. Packages sidecar data bundle (via build_release_data)
5. Generates and verifies cryptographic SHA256SUMS manifest
6. Runs smoke test against the assembled standalone binary
7. Packages compressed distribution archives (.tar.gz and/or .zip)
8. Verifies packaged archives against internal integrity manifests
9. Extracts release notes for publication

Usage:
    python scripts/build_release.py               # full release build + smoke test
    python scripts/build_release.py --skip-tests  # build without running test suite first
    python scripts/build_release.py --no-data     # build executable only (skip data)
    python scripts/build_release.py --zip         # create .zip archive alongside .tar.gz
    python scripts/build_release.py --clean       # remove previous build/ and dist/ first
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

# Add repo root to sys.path to allow importing internal helper modules
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_release_data import assemble_data_bundle, sha256_file, verify_bundle, verify_manifest


class ReleaseArgumentParser(argparse.ArgumentParser):
    """Argument parser matching build_release CLI interface and error format."""

    def error(self, message: str) -> None:
        sys.stderr.write(f"Unknown option: {message}\n")
        sys.exit(2)


def get_version(repo_root: Path) -> str:
    """Resolve release version from environment or pyproject.toml."""
    tag = os.environ.get("CI_COMMIT_TAG")
    if tag:
        return tag.lstrip("v")
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        import re
        content = pyproject.read_text(encoding="utf-8")
        m = re.search(r'version\s*=\s*"([^"]+)"', content)
        if m:
            return m.group(1)
    return "0.1.0"


def detect_platform() -> tuple[str, str, str]:
    """Detect normalized (os_name, arch_name, platform_tag)."""
    system = platform.system().lower()
    if any(k in system for k in ("win", "mingw", "msys", "cygwin")):
        os_name = "windows"
    elif "darwin" in system:
        os_name = "macos"
    else:
        os_name = "linux"

    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch_name = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch_name = "arm64"
    else:
        arch_name = machine

    return os_name, arch_name, f"{os_name}-{arch_name}"


def generate_manifest(stage_dir: Path) -> Path:
    """Generate release-wide SHA256SUMS manifest excluding SQLite DBs and manifests."""
    entries: list[tuple[str, str]] = []
    for root, dirs, files in os.walk(stage_dir):
        # Prune DBs and manifests per ADR-027
        for f in files:
            p = Path(root) / f
            if f.endswith(".db") or f in ("INTEGRITY.json", "SHA256SUMS"):
                continue
            rel = p.relative_to(stage_dir).as_posix()
            entries.append((rel, sha256_file(p)))

    entries.sort(key=lambda x: x[0])
    manifest_path = stage_dir / "SHA256SUMS"
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as out:
        for rel, h in entries:
            out.write(f"{h}  {rel}\n")
    return manifest_path


def smoke_test_binary(exe_path: Path, has_data: bool) -> None:
    """Run verification smoke tests against the frozen standalone binary."""
    print("--- Running smoke test on standalone binary ---")
    if not exe_path.is_file():
        sys.stderr.write(f"ERROR: Standalone executable not found at: {exe_path}\n")
        sys.exit(1)

    bundle_dir = exe_path.parent

    # Basic CLI checks (isolated cwd to verify bundled environment)
    subprocess.run([str(exe_path), "--version"], cwd=bundle_dir, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    subprocess.run([str(exe_path), "--help"], cwd=bundle_dir, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if has_data:
        # 1. CLI Scripture reading (isolated cwd to verify sidecar data path)
        res = subprocess.run(
            [str(exe_path), "read", "Gen 1:1", "--json"],
            cwd=bundle_dir,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if "In the beginning God created" not in res.stdout:
            sys.stderr.write("ERROR: Standalone binary failed smoke test on Gen 1:1\n")
            sys.exit(1)
        print("✔ CLI Scripture reading verified.")

        # 2. Lexical concordance
        res = subprocess.run(
            [str(exe_path), "word", "H1254", "--json"],
            cwd=bundle_dir,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if "H1254" not in res.stdout:
            sys.stderr.write("ERROR: Standalone binary failed smoke test on word H1254\n")
            sys.exit(1)
        print("✔ Lexical concordance verified.")

        # 3. TUI / shell mode smoke test
        res = subprocess.run(
            [str(exe_path), "--tui"],
            input="exit\n",
            cwd=bundle_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if "ADVENTIST BIBLE STUDY TOOL" not in res.stdout and "ADVENTIST BIBLE STUDY TOOL" not in res.stderr:
            sys.stderr.write("ERROR: Standalone binary failed TUI / shell smoke test\n")
            sys.exit(1)
        print("✔ TUI mode smoke test verified.")

    print("✔ Smoke tests passed successfully.")


def create_release_archives(
    stage_dir: Path,
    dist_dir: Path,
    stage_name: str,
    create_zip: bool,
    os_name: str,
) -> list[Path]:
    """Compress stage_dir into .tar.gz and/or .zip distribution archives."""
    created_archives: list[Path] = []

    # 1. Create .tar.gz
    tar_path = dist_dir / f"{stage_name}.tar.gz"
    print(f"Creating release archive: {tar_path}...")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(stage_dir, arcname=stage_name)
    tar_sha = sha256_file(tar_path)
    (dist_dir / f"{stage_name}.tar.gz.sha256").write_text(f"{tar_sha}\n", encoding="utf-8")
    print(f"✔ Release archive: {tar_path}")
    print(f"  SHA-256: {tar_sha}")
    created_archives.append(tar_path)

    # 2. Create .zip if requested or on Windows
    if create_zip or os_name == "windows":
        zip_path = dist_dir / f"{stage_name}.zip"
        print(f"Creating release zip archive: {zip_path}...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(stage_dir):
                for f in files:
                    full_p = Path(root) / f
                    arcname = Path(stage_name) / full_p.relative_to(stage_dir)
                    zf.write(full_p, arcname=arcname.as_posix())
        zip_sha = sha256_file(zip_path)
        (dist_dir / f"{stage_name}.zip.sha256").write_text(f"{zip_sha}\n", encoding="utf-8")
        print(f"✔ Release zip archive: {zip_path}")
        print(f"  SHA-256: {zip_sha}")
        created_archives.append(zip_path)

    return created_archives


def verify_archive_ground_truth(archive_path: Path, stage_name: str, repo_root: Path) -> None:
    """Extract packaged archive in a sandbox and verify internal manifests (ADR-024)."""
    print(f"--- Verifying packaged archive ground truth: {archive_path.name} ---")
    with tempfile.TemporaryDirectory() as scratch:
        scratch_dir = Path(scratch)
        if archive_path.name.endswith(".tar.gz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                if hasattr(tarfile, "data_filter"):
                    tar.extractall(scratch_dir, filter="data")
                else:
                    tar.extractall(scratch_dir)
        elif archive_path.name.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(scratch_dir)
        else:
            return

        extracted_stage = scratch_dir / stage_name
        manifest_file = extracted_stage / "SHA256SUMS"
        if manifest_file.is_file():
            print("   Checking release-wide SHA256SUMS inside packaged archive...")
            verify_manifest(extracted_stage, manifest_file)

        data_dir = extracted_stage / "data"
        if data_dir.is_dir():
            data_manifest = data_dir / "SHA256SUMS"
            if data_manifest.is_file():
                print("   Checking sidecar data/SHA256SUMS inside packaged archive...")
                verify_manifest(data_dir, data_manifest)

            integrity_manifest = data_dir / "INTEGRITY.json"
            bible_db = data_dir / "bible.db"
            macula_db = data_dir / "macula.db"
            if integrity_manifest.is_file():
                print("   Checking SQLite content integrity inside packaged archive...")
                subprocess.run(
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
                        str(integrity_manifest),
                    ],
                    cwd=repo_root,
                    check=True,
                )
            elif bible_db.is_file() or macula_db.is_file():
                sys.stderr.write("ERROR: package contains SQLite DBs but no INTEGRITY.json content manifest.\n")
                sys.exit(1)

    print("✔ Packaged archive verified against internal manifests.")


def main() -> int:
    parser = ReleaseArgumentParser(
        description="Adventist Bible Study Tool — Release Build Pipeline (WP-029, ADR-024)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip pre-flight test verification")
    parser.add_argument("--no-data", action="store_true", help="Skip sidecar data bundle compilation")
    parser.add_argument("--zip", action="store_true", help="Create .zip archive in addition to .tar.gz")
    parser.add_argument("--clean", action="store_true", help="Clean build/ and dist/ directories before building")
    parser.add_argument("--version", default=None, help="Explicit version tag to build")

    args = parser.parse_args()
    repo_root = REPO_ROOT
    version = args.version or get_version(repo_root)
    os_name, arch_name, platform_tag = detect_platform()

    dist_dir = repo_root / "dist"
    archive_tag = os.environ.get("CI_COMMIT_TAG") or version
    stage_name = f"bible-study-{archive_tag}-{platform_tag}"
    stage_dir = dist_dir / stage_name

    print("==============================================================")
    print(f"Adventist Bible Study Tool — Release Build Pipeline v{version}")
    print("==============================================================")
    print(f"Target Platform: {platform_tag}")
    print(f"Staging Dir:     {stage_dir}")
    print(f"Python:          {platform.python_version()} ({sys.executable})")

    # Ensure PyInstaller is installed
    try:
        pyinstaller_ver = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        print(f"PyInstaller:     {pyinstaller_ver}")
    except Exception:
        sys.stderr.write("ERROR: PyInstaller is not installed in the target Python environment.\n")
        sys.stderr.write("Run pip install pyinstaller\n")
        return 1

    # 0. Clean if requested
    if args.clean:
        print("Cleaning previous build artifacts...")
        shutil.rmtree(repo_root / "build", ignore_errors=True)
        shutil.rmtree(dist_dir, ignore_errors=True)

    # 1. Pre-flight verification
    if not args.skip_tests:
        print("\n--- 1. Running pre-flight verification ---")
        subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=repo_root, check=True)
        print("✔ Test suite passed.")

    # 2. Freeze binary with PyInstaller
    print("\n--- 2. Freezing standalone application binary ---")
    spec_file = repo_root / "bible_study.spec"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "-y", str(spec_file)],
        cwd=repo_root,
        check=True,
    )
    frozen_dir = dist_dir / "bible-study"
    exe_name = "bible-study.exe" if os_name == "windows" else "bible-study"
    print(f"✔ Standalone executable built: {frozen_dir / exe_name}")

    # 3. Prepare release staging directory
    print("\n--- 3. Assembling release bundle layout ---")
    shutil.rmtree(stage_dir, ignore_errors=True)
    stage_dir.mkdir(parents=True, exist_ok=True)

    # Copy binary and runtime files
    for item in frozen_dir.iterdir():
        dest = stage_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Ensure executable permissions on POSIX
    exe_path = stage_dir / exe_name
    if os_name != "windows" and exe_path.exists():
        os.chmod(exe_path, 0o755)

    # Copy release documentation & notices
    for doc in ["README.md", "NOTICE.md", "LICENSE", "CONTRIBUTION_STANDARDS.md"]:
        doc_path = repo_root / doc
        if doc_path.is_file():
            shutil.copy2(doc_path, stage_dir / doc)

    # 4. Assemble sidecar data bundle (ADR-024 §7)
    build_data = not args.no_data
    if build_data:
        print("\n--- 4. Building sidecar data bundle ---")
        assemble_data_bundle(stage_dir / "data", repo_root)
        print(f"✔ Sidecar data bundle assembled in {stage_dir / 'data'}")

    # 5. Generate release-wide SHA256SUMS manifest
    print("\n--- 5. Generating release integrity manifest ---")
    manifest_path = generate_manifest(stage_dir)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_line_count = sum(1 for line in f if line.strip())
    print(f"✔ Generated {manifest_path} ({manifest_line_count} entries; SQLite DBs handled by content manifest).")

    # 6. Verify release staging self-integrity
    print("\n--- 6. Verifying release staging integrity ---")
    verify_manifest(stage_dir, manifest_path)
    print("✔ Release staging integrity verified.")

    # 7. Smoke test the assembled standalone binary
    smoke_test_binary(exe_path, build_data)

    # Re-verify staging integrity post-smoke test
    print("--- 7b. Verifying staging integrity post-smoke test ---")
    verify_manifest(stage_dir, manifest_path)
    print("✔ Release staging integrity unchanged by smoke tests.")

    # 8. Create release archive
    print("\n--- 8. Creating release archive ---")
    created_archives = create_release_archives(stage_dir, dist_dir, stage_name, args.zip, os_name)

    # 8b. Verify packaged archives
    for archive in created_archives:
        verify_archive_ground_truth(archive, stage_name, repo_root)

    # 9. Extract release notes
    print("\n--- 9. Extracting release notes ---")
    notes_script = repo_root / "scripts" / "extract_release_notes.py"
    if notes_script.is_file():
        subprocess.run(
            [sys.executable, str(notes_script), archive_tag, "--out", str(dist_dir / "RELEASE_NOTES.md")],
            cwd=repo_root,
            check=True,
        )

    print("\n==============================================================")
    print(f"Release build complete for {stage_name}")
    print("==============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
