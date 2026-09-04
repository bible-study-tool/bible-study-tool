#!/usr/bin/env python3
"""curate_context.py — Generate a compact, deterministic curation briefing.

Compresses thousands of lines of apparatus JSON, agreement ledgers, and
lexicons into a focused, human-and-LLM-readable ~50-80 line briefing for a
specific work package or verse range.

Usage:
    python scripts/curate_context.py --wp WP-003
    python scripts/curate_context.py --verses 9..13
    python scripts/curate_context.py --verses 9,10,11,12,13 --chapter 1
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

_NUM_LINE_RE = re.compile(r"^\d+\.")


def find_repo_root() -> Path:
    current = Path.cwd()
    for p in [current, *current.parents]:
        if (p / "ROADMAP.md").exists() and (p / "materials").exists():
            return p
    if (_REPO_ROOT / "ROADMAP.md").exists() and (_REPO_ROOT / "materials").exists():
        return _REPO_ROOT
    return current


def parse_verse_range(range_str: str) -> list[int]:
    """Parse '9..13', '9-13', or '9,10,11' into a list of ints."""
    s = range_str.strip()
    if ".." in s:
        start, end = s.split("..", 1)
        return list(range(int(start), int(end) + 1))
    if "-" in s and not s.startswith("-"):
        start, end = s.split("-", 1)
        return list(range(int(start), int(end) + 1))
    if "," in s:
        return [int(x.strip()) for x in s.split(",") if x.strip()]
    return [int(s)]


class WpScope(tuple):
    """A 2-tuple (target_file, verses) with an extra `chapter` attribute."""

    target_file: Path | None
    verses: list[int]
    chapter: int

    def __new__(cls, target_file: Path | None, verses: list[int], chapter: int = 1):
        instance = super().__new__(cls, (target_file, verses))
        instance.target_file = target_file
        instance.verses = verses
        instance.chapter = chapter
        return instance


def find_wp_file(repo_root: Path, wp_query: str) -> WpScope:
    """Resolve a work package name like 'WP-003' or 'WP-003-gen1-day3.md'."""
    wp_dir = repo_root / "docs" / "wp"
    query = wp_query.strip().removesuffix(".md")

    target_file = None
    if (wp_dir / f"{query}.md").exists():
        target_file = wp_dir / f"{query}.md"
    else:
        for p in sorted(wp_dir.glob("*.md")):
            if p.stem.startswith(query) or query in p.stem:
                target_file = p
                break

    verses: list[int] = []
    chapter: int = 1
    if target_file and target_file.exists():
        text = target_file.read_text(encoding="utf-8")

        # 1. Check scope line for range or list (consistent with wp_check.py)
        scope_match = re.search(r"^scope:\s*(.+)$", text, re.MULTILINE)
        if scope_match:
            scope_str = scope_match.group(1)
            range_scope = re.search(
                r"gen-(\d+)-(\d+)-kjv(?:\.md)?\s*\.\.\s*gen-\d+-(\d+)-kjv(?:\.md)?",
                scope_str,
            )
            if range_scope:
                chapter = int(range_scope.group(1))
                start, end = int(range_scope.group(2)), int(range_scope.group(3))
                verses = list(range(start, end + 1))
            else:
                for v_match in re.finditer(r"gen-(\d+)-(\d+)-kjv", scope_str):
                    chapter = int(v_match.group(1))
                    verses.append(int(v_match.group(2)))

        # 2. Fallback: scan title line for "Genesis <ch>:<start>-<end>" or "v<start>-<end>"
        if not verses:
            title_line = next((l for l in text.splitlines() if l.startswith("#")), "")
            gen_range = re.search(r"Genesis\s+(\d+):(\d+)[-–\.]+(\d+)", title_line, re.IGNORECASE)
            if gen_range:
                chapter = int(gen_range.group(1))
                verses = list(range(int(gen_range.group(2)), int(gen_range.group(3)) + 1))
            else:
                title_match = re.search(r"v(\d+)(?:[-–]|\.{2})(\d+)", title_line)
                if title_match:
                    start, end = int(title_match.group(1)), int(title_match.group(2))
                    verses = list(range(start, end + 1))
                gen_match = re.search(r"Genesis\s+(\d+)", title_line, re.IGNORECASE)
                if gen_match:
                    chapter = int(gen_match.group(1))

    return WpScope(target_file, sorted(set(verses)), chapter)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_briefing(
    repo_root: Path,
    chapter: int,
    verses: list[int],
    wp_file: Path | None = None,
) -> str:
    if not verses:
        return f"# Curation Briefing — Genesis {chapter} (no verses specified)\n"

    # Load data artifacts
    apparatus_path = repo_root / f"correlations/apparatus-genesis{chapter}.json"
    apparatus_data = load_json(apparatus_path)
    apparatus_by_key = {
        v.get("key", ""): v for v in apparatus_data.get("verses", [])
    }

    lex_payload = load_json(repo_root / "lexicons/strongs-lexicon.json")
    strongs_lex = {**lex_payload.get("hebrew", {}), **lex_payload.get("greek", {})}

    tbesh_payload = load_json(repo_root / "lexicons/tbesh-glosses.json")
    tbesh_entries = tbesh_payload.get("entries", {})

    lines: list[str] = []
    lines.append(f"# Curation Briefing — Genesis {chapter}:{min(verses)}-{max(verses)}")
    if wp_file:
        lines.append(f"**Work Package:** `{wp_file.name}`")
    lines.append("")

    # If WP file exists, extract high-level tasks/xrefs
    if wp_file:
        wp_text = wp_file.read_text(encoding="utf-8")
        tasks_section = re.search(r"## Tasks\s*\n(.*?)(?=\n## |\Z)", wp_text, re.DOTALL)
        if tasks_section:
            lines.append("## Work Package Requirements")
            lines.append(tasks_section.group(1).strip())
            lines.append("")

    for v in verses:
        entry_path = repo_root / f"materials/bible/ot/genesis/gen-{chapter}-{v}-kjv.md"
        app_key = f"Gen.{chapter}.{v}"
        app_entry = apparatus_by_key.get(app_key, {})

        lines.append(f"---")
        lines.append(f"## Genesis {chapter}:{v} (`gen-{chapter}-{v}-kjv.md`)")

        # Read current draft verse text and status
        if entry_path.exists():
            entry_content = entry_path.read_text(encoding="utf-8")
            status_match = re.search(r"^status:\s*(\w+)", entry_content, re.MULTILINE)
            status = status_match.group(1) if status_match else "unknown"
            quote_match = re.search(r"^>\s*(.+)$", entry_content, re.MULTILINE)
            quote = quote_match.group(1) if quote_match else ""
            lines.append(f"* **Current Status:** `{status}`")
            lines.append(f"* **KJV Text:** > {quote}")
        else:
            lines.append(f"* **Entry file not found at:** `{entry_path}`")

        # Apparatus summary (Omissions & Alignments)
        if app_entry:
            counts = app_entry.get("counts", {})
            omissions = app_entry.get("omissions", [])
            lines.append(
                f"* **Apparatus Alignment:** {counts.get('matched', 0)} matched tokens, "
                f"{len(omissions)} untagged/omitted in KJV-osis."
            )
            if omissions:
                lines.append("  * **Untagged Hebrew Tokens in Source:**")
                for om in omissions:
                    code = om.get("code", "")
                    oshb = om.get("oshb", {})
                    wlc = oshb.get("wlc", "")
                    morph = oshb.get("morph", "")
                    lex_info = strongs_lex.get(code, {})
                    lemma = lex_info.get("word", "")
                    tbesh_list = tbesh_entries.get(code, [])
                    tbesh_gloss = tbesh_list[0].get("gloss", "") if tbesh_list else ""
                    lines.append(
                        f"    - `{code}` ({lemma} / \"{tbesh_gloss}\"): "
                        f"WLC Hebrew `{wlc}`, morph `{morph}`"
                    )

        # Lexicon items present in this verse
        matched_codes = (
            list(dict.fromkeys(
                m["code"] for m in app_entry.get("matched", []) if m.get("code")
            ))
            if app_entry
            else []
        )

        if matched_codes:
            lines.append("* **Key Lexemes in Verse:**")
            for code in matched_codes:
                st = strongs_lex.get(code, {})
                tb_list = tbesh_entries.get(code, [])
                gloss = tb_list[0].get("gloss", "") if tb_list else ""
                lemma = st.get("word", "")
                translit = st.get("translit", "")
                desc = st.get("desc", "")

                # Extract first definition line
                lines_desc = [l.strip() for l in desc.splitlines() if l.strip()]
                defn = ""
                for line in lines_desc:
                    if _NUM_LINE_RE.match(line):
                        defn = line
                        break
                if not defn and lines_desc:
                    defn = lines_desc[1] if len(lines_desc) > 1 else lines_desc[0]

                lines.append(
                    f"  - **{code}** (`{lemma}` / *{translit}*): modern: *\"{gloss}\"* | strongs: *{defn}*"
                )

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a compact curation briefing from apparatus and lexicons."
    )
    parser.add_argument("--wp", help="Work package name or path (e.g. WP-003)")
    parser.add_argument("--verses", help="Verse range (e.g. 9..13 or 9-13)")
    parser.add_argument(
        "--chapter",
        type=int,
        default=None,
        help="Genesis chapter (default: auto-detected from WP, or 1)",
    )
    args = parser.parse_args()

    repo_root = find_repo_root()
    if not (repo_root / "ROADMAP.md").exists():
        print("Error: Could not locate repository root. Please run from within the bible-study-tool repository.", file=sys.stderr)
        sys.exit(1)
    wp_file = None
    verses = []
    chapter = 1

    if args.wp:
        wp_scope = find_wp_file(repo_root, args.wp)
        wp_file, wp_verses = wp_scope
        chapter = wp_scope.chapter
        if wp_verses:
            verses = wp_verses

    if args.verses:
        verses = parse_verse_range(args.verses)

    if args.chapter is not None:
        chapter = args.chapter

    if not verses:
        if args.wp:
            print(f"Error: Could not resolve work package '{args.wp}' or extract scope.", file=sys.stderr)
        else:
            print("Error: Specify either --wp <WP-XXX> or --verses <range> (e.g. 9..13)", file=sys.stderr)
        sys.exit(1)

    briefing = build_briefing(repo_root, chapter, verses, wp_file)
    print(briefing)


if __name__ == "__main__":
    main()
