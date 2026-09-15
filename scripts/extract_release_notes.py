#!/usr/bin/env python3
"""extract_release_notes.py — Extract release notes from CHANGELOG.md for a git tag/version.

Used by the release build pipeline and GitLab CI/CD to populate release descriptions.

Usage:
    python scripts/extract_release_notes.py [TAG_OR_VERSION] [--out FILE]
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys


def get_current_version(repo_root: Path) -> str:
    """Read version from pyproject.toml."""
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        content = pyproject.read_text(encoding="utf-8")
        m = re.search(r'version\s*=\s*"([^"]+)"', content)
        if m:
            return m.group(1)
    return "0.1.0"


def extract_notes_from_changelog(changelog_text: str, version: str) -> str | None:
    """Extract the markdown section corresponding to a specific version."""
    clean_ver = version.lstrip("v").strip()
    pattern = rf"##\s+\[{re.escape(clean_ver)}(?![0-9])[^\]]*\][^\n]*\n(.*?)(?=\n##\s+\[|\Z)"
    match = re.search(pattern, changelog_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract release notes for a version from CHANGELOG.md.")
    parser.add_argument("version", nargs="?", default=None, help="Version or tag (e.g. v0.1.1-alpha or 0.1.1)")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="Path to CHANGELOG.md")
    parser.add_argument("--out", default=None, help="Output file path (default: stdout)")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    changelog_path = (repo_root / args.changelog).resolve()

    version = args.version or os.environ.get("CI_COMMIT_TAG")
    if not version:
        version = get_current_version(repo_root)

    notes = None
    if changelog_path.is_file():
        changelog_text = changelog_path.read_text(encoding="utf-8")
        notes = extract_notes_from_changelog(changelog_text, version)

    if not notes:
        notes = f"Release {version}\n\nAutomated release build for {version}. See CHANGELOG.md for complete commit history."

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(notes + "\n", encoding="utf-8")
        print(f"✔ Extracted release notes for {version} to {args.out} ({len(notes)} chars).")
    else:
        print(notes)

    return 0


if __name__ == "__main__":
    sys.exit(main())
