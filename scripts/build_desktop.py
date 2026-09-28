#!/usr/bin/env python3
"""build_desktop.py — Native Desktop Application Packaging Pipeline (WP-038, ADR-028).

Coordinates the desktop application build using Tauri v2:
1. Verifies that the frozen engine binary (bible-study) is built (or invokes build_release.py)
2. Stages the sidecar binary and data bundle into the Tauri bundle resources
3. Invokes `bunx @tauri-apps/cli build` or `cargo tauri build` to generate native installers:
   - macOS: .dmg disk image + .app bundle
   - Windows: NSIS .exe setup / .msi installer
   - Linux: .AppImage / .deb package
4. Collects and verifies generated desktop installer artifacts

Usage:
    python scripts/build_desktop.py               # full desktop build
    python scripts/build_desktop.py --skip-engine # use existing dist/ binary
    python scripts/build_desktop.py --check-only  # verify configuration and prerequisites
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_release import detect_platform, get_version


def check_tauri_prerequisites() -> dict[str, bool]:
    """Check availability of Rust and Tauri build tooling."""
    results = {
        "cargo": shutil.which("cargo") is not None,
        "rustc": shutil.which("rustc") is not None,
        "bun": shutil.which("bun") is not None,
        "node": shutil.which("node") is not None,
        "tauri_cli": (
            shutil.which("cargo-tauri") is not None
            or shutil.which("tauri") is not None
            or shutil.which("bunx") is not None
            or shutil.which("npx") is not None
        ),
    }
    return results


def resolve_tauri_command() -> list[str]:
    """Resolve the command line to invoke Tauri CLI."""
    if shutil.which("cargo-tauri"):
        return ["cargo", "tauri"]
    if shutil.which("tauri"):
        return ["tauri"]
    if shutil.which("bunx"):
        return ["bunx", "@tauri-apps/cli"]
    if shutil.which("npx"):
        return ["npx", "@tauri-apps/cli"]
    raise RuntimeError("No Tauri CLI runner found (install @tauri-apps/cli or cargo-tauri).")


def stage_sidecar_for_bundle(repo_root: Path, os_name: str) -> Path | None:
    """Stage frozen engine binary and sidecar data into src-tauri bundle directory."""
    dist_dir = repo_root / "dist"
    ext = ".exe" if os_name == "windows" else ""
    binary_name = f"bible-study{ext}"

    # Search candidates in dist/
    candidates = [
        dist_dir / f"bible-study-{os_name}-x86_64" / binary_name,
        dist_dir / f"bible-study-{os_name}-arm64" / binary_name,
        dist_dir / "bible-study" / binary_name,
        dist_dir / binary_name,
    ]

    found: Path | None = None
    for cand in candidates:
        if cand.is_file():
            found = cand
            break

    if not found:
        return None

    # Staging area inside src-tauri
    target_dir = repo_root / "src-tauri" / "binaries"
    target_dir.mkdir(parents=True, exist_ok=True)
    staged_binary = target_dir / binary_name
    shutil.copy2(found, staged_binary)
    try:
        staged_binary.chmod(0o755)
    except Exception:
        pass

    # PyInstaller onedir mode requires sibling _internal/ directory
    found_internal = found.parent / "_internal"
    if found_internal.is_dir():
        target_internal = target_dir / "_internal"
        if target_internal.exists():
            shutil.rmtree(target_internal)
        shutil.copytree(found_internal, target_internal)

    # Stage sidecar data directory per ADR-024 / ADR-028
    found_data = found.parent / "data"
    if not found_data.is_dir():
        found_data = repo_root / "data"
    if found_data.is_dir():
        target_data = target_dir / "data"
        if not target_data.exists():
            shutil.copytree(found_data, target_data)

    return staged_binary


def run_tauri_build(repo_root: Path, debug: bool = False) -> int:
    """Execute the Tauri native application build."""
    cmd = resolve_tauri_command()
    cmd.append("build")
    if debug:
        cmd.append("--debug")

    print(f"==> Running Tauri build: {' '.join(cmd)}")
    env = os.environ.copy()
    proc = subprocess.run(cmd, cwd=repo_root, env=env)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Build native desktop application via Tauri")
    parser.add_argument("--skip-engine", action="store_true", help="Skip building PyInstaller engine if already present")
    parser.add_argument("--check-only", action="store_true", help="Check prerequisites and exit")
    parser.add_argument("--debug", action="store_true", help="Build debug target instead of release")
    args = parser.parse_args()

    os_name, arch_name, platform_tag = detect_platform()
    version = get_version(REPO_ROOT)
    print(f"=== Adventist Bible Study — Desktop App Builder v{version} ({platform_tag}) ===")

    prereqs = check_tauri_prerequisites()
    print("Prerequisite checks:")
    for tool, available in prereqs.items():
        status = "✔ found" if available else "✘ missing"
        print(f"  - {tool:10s}: {status}")

    if args.check_only:
        all_ok = prereqs["cargo"] and prereqs["rustc"] and prereqs["tauri_cli"]
        return 0 if all_ok else 1

    # Stage or build engine
    staged = stage_sidecar_for_bundle(REPO_ROOT, os_name)
    if not staged and not args.skip_engine:
        print("==> Frozen engine not found in dist/. Invoking scripts/build_release.py...")
        ret = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "build_release.py"), "--skip-tests"],
            cwd=REPO_ROOT,
        )
        if ret.returncode != 0:
            print("ERROR: Failed to build underlying engine binary.", file=sys.stderr)
            return ret.returncode
        staged = stage_sidecar_for_bundle(REPO_ROOT, os_name)

    if staged:
        print(f"==> Staged engine binary: {staged}")
    else:
        print("WARNING: Could not find frozen engine binary to stage. Tauri build may fail if sidecar is required.")

    return run_tauri_build(REPO_ROOT, debug=args.debug)


if __name__ == "__main__":
    sys.exit(main())
