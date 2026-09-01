#!/usr/bin/env python3
"""wp_check.py — Fast, deterministic pre-flight check for work packages.

Validates a work package's scoped entries before commit / subagent review:
  1. Frontmatter fields (status: review, valid updated ISO date).
  2. Balanced AI markers (<!-- AI-GENERATED --> ... <!-- END AI-GENERATED -->).
  3. Verbatim preservation of deterministic skeleton (verse text, word studies).
  4. F1-F4 schema & integrity validation for the scoped entries.

Usage:
    python scripts/wp_check.py --wp WP-002
    python scripts/wp_check.py --wp WP-003
    python scripts/wp_check.py --files materials/bible/ot/genesis/gen-1-6-kjv.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Ensure repo root is in sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from search.corpus.build_genesis1 import (
    clean_verse_text,
    load_pinned_sources,
    verse_codes,
    word_study_block,
)
from search.linking.loader import Loader
from search.validation import audit as f4
from search.validation import xrefs as f3
from search.validation.schema import Taxonomy, validate_all as schema_all
from search.validation.strongs import StrongsCanonical, validate_all as strongs_all


def find_repo_root() -> Path:
    current = Path.cwd()
    for p in [current, *current.parents]:
        if (p / "ROADMAP.md").exists() and (p / "materials").exists():
            return p
    return current


def resolve_wp_files(repo_root: Path, wp_name: str) -> tuple[Path | None, list[Path]]:
    """Resolve a WP name (e.g. WP-002) to its markdown file and scoped entry files."""
    wp_dir = repo_root / "docs" / "wp"
    query = wp_name.strip().removesuffix(".md")

    target_wp = None
    if (wp_dir / f"{query}.md").exists():
        target_wp = wp_dir / f"{query}.md"
    else:
        for p in sorted(wp_dir.glob("*.md")):
            if p.stem.startswith(query) or query in p.stem:
                target_wp = p
                break

    if not target_wp or not target_wp.exists():
        return None, []

    text = target_wp.read_text(encoding="utf-8")
    files: list[Path] = []

    # Extract ONLY from the scope: line
    scope_match = re.search(r"^scope:\s*(.+)$", text, re.MULTILINE)
    if scope_match:
        scope_str = scope_match.group(1)
        range_match = re.search(
            r"gen-(\d+)-(\d+)-kjv(?:\.md)?\s*\.\.\s*gen-\d+-(\d+)-kjv(?:\.md)?",
            scope_str,
        )
        if range_match:
            ch = int(range_match.group(1))
            start = int(range_match.group(2))
            end = int(range_match.group(3))
            for v in range(start, end + 1):
                files.append(repo_root / f"materials/bible/ot/genesis/gen-{ch}-{v}-kjv.md")
        else:
            for m in re.finditer(r"(gen-\d+-\d+-kjv(?:\.md)?)", scope_str):
                fname = m.group(1)
                if not fname.endswith(".md"):
                    fname += ".md"
                p = repo_root / "materials/bible/ot/genesis" / fname
                if p not in files:
                    files.append(p)

    return target_wp, files


def check_entry_ai_markers(path: Path, content: str) -> list[str]:
    """Verify AI comments are properly opened and closed."""
    errors = []
    # Strip inline code spans (e.g. `<!-- AI-GENERATED -->`) before checking real HTML comments
    code_stripped = re.sub(r"`[^`]*`", "", content)

    open_count = code_stripped.count("<!-- AI-GENERATED -->")
    close_count = code_stripped.count("<!-- END AI-GENERATED -->")

    if open_count != close_count:
        errors.append(
            f"Unbalanced AI markers: {open_count} '<!-- AI-GENERATED -->' vs {close_count} '<!-- END AI-GENERATED -->'"
        )

    # Check for unclosed HTML comment syntax
    comment_opens = len(re.findall(r"<!--", code_stripped))
    comment_closes = len(re.findall(r"-->", code_stripped))
    if comment_opens != comment_closes:
        errors.append(f"Malformed HTML comments: {comment_opens} opens vs {comment_closes} closes")

    return errors


def check_entry_skeleton(
    path: Path,
    content: str,
    kjv_verse: dict,
    lexicon: dict,
    tbesh: dict,
) -> list[str]:
    """Verify verse text quote and word study blocks match the pinned source."""
    errors = []

    # 1. Quoted verse text
    quote_match = re.search(r"^>\s*(.+)$", content, re.MULTILINE)
    if not quote_match:
        errors.append("Missing verse text blockquote ('> ...')")
    else:
        expected_quote = clean_verse_text(kjv_verse.get("text", ""))
        actual_quote = quote_match.group(1).strip()
        if actual_quote != expected_quote:
            errors.append(
                f"Verse quote drifted from pinned KJV source:\n  Actual:   {actual_quote}\n  Expected: {expected_quote}"
            )

    # 2. Word study facts
    block_header = re.compile(r"^### .+ - Strong's ([HG]\d+)$", re.MULTILINE)
    codes_in_verse, occ_map, _ = verse_codes(kjv_verse.get("text", ""))
    found_codes = set()
    for m in block_header.finditer(content):
        code = m.group(1)
        found_codes.add(code)
        if code in occ_map:
            expected_block = word_study_block(code, occ_map[code], lexicon, tbesh)
            if expected_block not in content:
                errors.append(f"Word study block for {code} drifted from canonical lexicons")

    # Verify no expected word study blocks were deleted
    for code in occ_map:
        if code not in found_codes:
            errors.append(f"Missing required word study block for {code}")

    return errors


def run_wp_check(repo_root: Path, target_wp: Path | None, files: list[Path]) -> int:
    print(f"Checking Work Package: {target_wp.name if target_wp else 'manual file list'}")
    print(f"Scoped files ({len(files)}): {[f.name for f in files]}")
    print("─" * 60)

    if not files:
        print("Error: No files resolved for checking.", file=sys.stderr)
        return 1

    kjv, lexicon, tbesh, canonical = load_pinned_sources(str(repo_root))
    gen = next(b for b in kjv["books"] if b["name"] == "Genesis")
    ch1 = next(c for c in gen["chapters"] if c["chapter"] == 1)
    verses_by_num = {v["verse"]: v for v in ch1["verses"]}

    all_errors: list[str] = []

    # Check each file individually
    for p in files:
        if not p.exists():
            all_errors.append(f"{p.name}: File does not exist")
            continue

        content = p.read_text(encoding="utf-8")
        v_match = re.search(r"gen-1-(\d+)-kjv", p.stem)
        v_num = int(v_match.group(1)) if v_match else None

        # Check frontmatter status and updated date
        if "status: review" not in content and "status: final" not in content:
            all_errors.append(f"{p.name}: status must be 'review' or 'final'")

        if not re.search(r"^updated:\s*\d{4}-\d{2}-\d{2}", content, re.MULTILINE):
            all_errors.append(f"{p.name}: missing or invalid 'updated: YYYY-MM-DD' date")

        # Check AI markers
        ai_errs = check_entry_ai_markers(p, content)
        for e in ai_errs:
            all_errors.append(f"{p.name}: {e}")

        # Check skeleton invariance
        if v_num and v_num in verses_by_num:
            skel_errs = check_entry_skeleton(
                p, content, verses_by_num[v_num], lexicon, tbesh
            )
            for e in skel_errs:
                all_errors.append(f"{p.name}: {e}")

    # Run F1-F4 validators across the repo loader
    loader = Loader(str(repo_root))
    loader.load_entries()
    tax = Taxonomy(str(repo_root / "tags/taxonomy.json"))

    schema_errs = [i for i in schema_all(loader, tax) if i.severity == "error"]
    for err in schema_errs:
        if any(f.stem in err.entry_id for f in files):
            all_errors.append(f"{err.entry_id} (F1 Schema): {err.message}")

    canon = StrongsCanonical(
        hebrew=set(canonical["hebrew"]), greek=set(canonical["greek"])
    )
    strongs_errs = [i for i in strongs_all(loader, canon) if i.severity == "error"]
    for err in strongs_errs:
        if any(f.stem in err.entry_id for f in files):
            all_errors.append(f"{err.entry_id} (F2 Strong's): {err.message}")

    xref_errs = [i for i in f3.validate_all(loader) if i.severity == "error"]
    for err in xref_errs:
        if any(f.stem in err.entry_id for f in files):
            all_errors.append(f"{err.entry_id} (F3 Xrefs): {err.message}")

    audit_errs = [i for i in f4.audit_all(loader, str(repo_root)) if i.severity == "error"]
    for err in audit_errs:
        if any(f.stem in err.entry_id for f in files):
            all_errors.append(f"{err.entry_id} (F4 Audit): {err.message}")

    print()
    if all_errors:
        print(f"❌ WP CHECK FAILED with {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  • {err}")
        return 1
    else:
        print(f"✔ WP CHECK PASSED — all {len(files)} entries are structurally sound, verified against lexicons, and pass F1-F4 gates.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Deterministic pre-flight checker for work packages.")
    parser.add_argument("--wp", help="Work package name or path (e.g. WP-002)")
    parser.add_argument("--files", nargs="+", help="Specific files to check")
    args = parser.parse_args()

    repo_root = find_repo_root()

    target_wp = None
    files: list[Path] = []

    if args.wp:
        target_wp, files = resolve_wp_files(repo_root, args.wp)
    elif args.files:
        files = [Path(f) for f in args.files]

    if not files:
        print("Error: Specify either --wp <WP-XXX> or --files <file1> <file2>...", file=sys.stderr)
        sys.exit(1)

    code = run_wp_check(repo_root, target_wp, files)
    sys.exit(code)


if __name__ == "__main__":
    main()
