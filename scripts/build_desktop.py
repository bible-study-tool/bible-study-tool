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
from scripts.build_release_data import sha256_file


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

    # Search candidates in dist/ (prioritizing versioned staged release folders)
    candidates = [
        *sorted(dist_dir.glob(f"bible-study-*-{os_name}*/{binary_name}"), reverse=True),
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
        if target_data.exists():
            shutil.rmtree(target_data)
        shutil.copytree(found_data, target_data)

    return staged_binary


def run_tauri_build(repo_root: Path, debug: bool = False, bundles: str | None = None) -> int:
    """Execute the Tauri native application build."""
    cmd = resolve_tauri_command()
    cmd.append("build")
    if debug:
        cmd.append("--debug")
    if bundles is not None:
        cleaned_bundles = ",".join(b.strip() for b in bundles.split(",") if b.strip())
        if cleaned_bundles:
            cmd.extend(["--bundles", cleaned_bundles])
    elif sys.platform.startswith("linux"):
        # On Linux, default to deb and appimage, explicitly skipping rpm.
        # Tauri's rpm builder performs automated ELF dependency scanning
        # (`find-requires` inspecting hundreds of PyInstaller .so files)
        # and single-threaded xz compression, which takes 20-30+ minutes in CI.
        cmd.extend(["--bundles", "deb,appimage"])

    print(f"==> Running Tauri build: {' '.join(cmd)}")
    env = os.environ.copy()
    proc = subprocess.run(cmd, cwd=repo_root, env=env, shell=(sys.platform == "win32"))
    return proc.returncode


def collect_desktop_artifacts(repo_root: Path, dist_dir: Path) -> list[Path]:
    """Find generated Tauri desktop installers and copy them to dist/ with SHA256 checksums."""
    bundle_dir = repo_root / "src-tauri" / "target" / "release" / "bundle"
    if not bundle_dir.is_dir():
        return []

    dist_dir.mkdir(parents=True, exist_ok=True)
    collected: list[Path] = []
    extensions = ("*.dmg", "*.AppImage", "*.deb", "*.msi", "*.exe")
    for ext in extensions:
        for f in bundle_dir.rglob(ext):
            if "build" in f.parts or "deps" in f.parts or f.name.lower() in ("bible-study.exe", "uninstall.exe"):
                continue
            dest = dist_dir / f.name
            shutil.copy2(f, dest)
            collected.append(dest)

            digest = sha256_file(dest)
            sha_file = dest.with_name(f"{dest.name}.sha256")
            sha_file.write_text(f"{digest}  {dest.name}\n", encoding="utf-8")
            collected.append(sha_file)
            print(f"  ✔ Collected installer: {dest.name} (SHA-256: {digest[:16]}...)")

    return collected


def main() -> int:
    parser = argparse.ArgumentParser(description="Build native desktop application via Tauri")
    parser.add_argument("--skip-engine", action="store_true", help="Skip building PyInstaller engine if already present")
    parser.add_argument("--check-only", action="store_true", help="Check prerequisites and exit")
    parser.add_argument("--debug", action="store_true", help="Build debug target instead of release")
    parser.add_argument("--bundles", type=str, default=None, help="Comma-separated list of bundles to package (defaults to 'deb,appimage' on Linux)")
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
        print("ERROR: Could not find frozen engine binary to stage into Tauri bundle.", file=sys.stderr)
        return 1

    ret = run_tauri_build(REPO_ROOT, debug=args.debug, bundles=args.bundles)
    if ret == 0:
        print("==> Collecting desktop installers into dist/...")
        collected = collect_desktop_artifacts(REPO_ROOT, REPO_ROOT / "dist")
        print(f"==> Total installer artifacts collected: {len(collected)}")

    return ret


if __name__ == "__main__":
    sys.exit(main())
