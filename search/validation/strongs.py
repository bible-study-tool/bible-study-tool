"""F2 — Strong's number verification.

Validates that every ``strongs-H####`` / ``strongs-G####`` tag (and the
corresponding ``id`` naming, where applicable) is well-formed and, when a
canonical list is available, that the number is real.

Two layers (option b — structural now, canonical later):
  * **Always:** structural/range check. A Strong's tag must match
    ``strongs-(H|G)`` followed by a number in the plausible range
    (Hebrew up to 8674, Greek up to 5624). This catches malformed tags and
    out-of-range numbers without any external data.
  * **When available:** canonical-list check. If ``lexicons/strongs-list.json``
    (or the path given with ``--list``) exists, each number is checked against
    the authoritative set of real Strong's numbers — the FULL canonical
    enumeration (8674 Hebrew + 5624 Greek), generated from the
    gmlewis/bible-codes concordance by ``build_strongs_lexicon.py`` and pinned
    with SHA-256 in ``data/PROVENANCE.md``.

This matters because a wrong Strong's number silently corrupts the
deterministic core — the exact class of error we already caught once
(G2532 vs G746).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .schema import Issue

# Plausible upper bounds for the Strong's enumeration (public facts).
_MAX_HEBREW = 8674
_MAX_GREEK = 5624

_STRONGS_TAG_RE = re.compile(r"^strongs-([HhGg])(\d{1,4})$")


@dataclass
class StrongsCanonical:
    """Loaded canonical set of valid Strong's numbers (H#### / G####)."""

    hebrew: set[str]
    greek: set[str]

    @classmethod
    def load(cls, path: str | Path = "lexicons/strongs-list.json") -> "StrongsCanonical | None":
        """Load the canonical list. Returns None if the file is absent.

        Expected shape: {"hebrew": ["H7225", ...], "greek": ["G2532", ...]}.
        """
        p = Path(path)
        if not p.exists():
            return None
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(
            hebrew=set(data.get("hebrew", [])),
            greek=set(data.get("greek", [])),
        )

    def has(self, code: str) -> bool:
        letter = code[0]
        if letter == "H":
            return code in self.hebrew
        if letter == "G":
            return code in self.greek
        return False


def parse_strongs(tag: str) -> tuple[str, int] | None:
    """Parse a strongs- tag into (letter, number) or None if malformed.

    Returns None when the tag is not a valid strongs-* shape at all; callers
    should then flag it as malformed.
    """
    m = _STRONGS_TAG_RE.match(tag)
    if not m:
        return None
    return m.group(1).upper(), int(m.group(2))


def validate_strongs_tag(tag: str, canonical: StrongsCanonical | None = None) -> list[Issue]:
    """Validate a single strongs- tag. Returns issues (possibly empty)."""
    parsed = parse_strongs(tag)
    if parsed is None:
        return [Issue("", "malformed-strongs", "error", f"'{tag}' is not a valid strongs- tag")]
    letter, number = parsed
    code = f"{letter}{number}"

    if letter == "H" and number > _MAX_HEBREW:
        return [Issue("", "out-of-range-strongs", "error", f"Hebrew Strong's {code} exceeds max {_MAX_HEBREW}")]
    if letter == "G" and number > _MAX_GREEK:
        return [Issue("", "out-of-range-strongs", "error", f"Greek Strong's {code} exceeds max {_MAX_GREEK}")]

    # Canonical-list check (only when a canonical list is supplied).
    if canonical is not None:
        if not canonical.has(code):
            return [Issue("", "unknown-strongs", "error", f"Strong's {code} is not in the canonical list")]
    return []


def validate_entry_strongs(entry, canonical: StrongsCanonical | None = None) -> list[Issue]:
    """Validate all strongs-* tags in an entry's tags list."""
    issues: list[Issue] = []
    tags = entry.tags or []
    for tag in tags:
        if not (isinstance(tag, str) and tag.startswith("strongs-")):
            continue
        for issue in validate_strongs_tag(tag, canonical):
            # Re-bind the entry id onto the issue.
            issues.append(Issue(entry.id, issue.code, issue.severity, issue.message))
    return issues


def validate_all(loader, canonical: StrongsCanonical | None = None) -> list[Issue]:
    """Validate Strong's tags across every entry in a Loader."""
    issues: list[Issue] = []
    for entry in loader.entries:
        issues.extend(validate_entry_strongs(entry, canonical))
    return issues


def main(argv=None) -> int:
    import argparse
    import sys

    from search.linking.loader import Loader

    parser = argparse.ArgumentParser(
        prog="validate-strongs", description="F2: validate Strong's number tags"
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--list-path", default="lexicons/strongs-list.json",
        help="Optional canonical Strong's list (skips full-number check if absent)",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    canonical = StrongsCanonical.load(args.list_path)
    loader = Loader(args.repo)
    loader.load_entries()
    issues = validate_all(loader, canonical)

    for issue in issues:
        print(issue)
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    mode = f"against canonical list ({args.list_path})" if canonical else "structural (no canonical list found)"
    if not args.quiet:
        print(f"\n{len(issues)} issues: {errors} error(s), {warnings} warning(s) across {len(loader.entries)} entries — checked {mode}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())