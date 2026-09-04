"""F3 — Cross-reference integrity checker.

Validates the ``cross_references`` in every entry: each target must be
well-formed and should resolve to a real entry in the knowledge base.

Two target forms are accepted (per kc-schema.md: ``target: "related-passage
or entry id"``):
  * entry id   -> lowercase, hyphenated (e.g. ``john-1-1``)
  * passage    -> "Book Chapter:Verse" style (e.g. ``John 1:1``)

Severity model:
  * ERROR   — malformed target (neither an entry-id nor a passage shape).
  * WARNING — well-formed but does not resolve to an existing entry. This is
              a *forward reference* to a planned entry, which is legitimate
              in this project (entries reference material not yet added), so
              it is advisory, not a hard failure.
  * (ok)    — target resolves to an existing entry.

Resolvability is judged against entry IDs in the current corpus. A passage
reference is considered resolved if it maps to an entry whose ``passage``
matches, or whose id matches the normalized book-chapter-verse.
"""

from __future__ import annotations

import re
from pathlib import Path

from .schema import Issue

# Entry-id shape: lowercase alphanumeric with at least one letter, hyphen-separated segments (e.g. john-1-1, 2peter-3-5-7).
_ENTRY_ID_RE = re.compile(r"^(?=.*[a-z])[a-z0-9]+(?:-[a-z0-9]+)+$")
# Passage shape: "Book Chapter:Verse" (optionally with ranges), e.g. John 1:1 or 2 Peter 3:5-7.
_PASSAGE_RE = re.compile(r"^[0-9A-Za-z][A-Za-z0-9 ]* \d+:\d+(?:[-–]\d+)?$")
# EGW canonical citation token shape: "egw:BOOK.PAGE.PARA" or "BOOK.PAGE.PARA" (e.g. egw:PP.57.1).
_EGW_TOKEN_RE = re.compile(r"^egw:[A-Za-z0-9]+(?:\.[0-9]+(?:\.[0-9]+)?)?$", re.IGNORECASE)


def classify_target(target: str) -> str:
    """Return 'entry' | 'passage' | 'egw' | 'malformed' for a target string."""
    t = (target or "").strip()
    if not t:
        return "malformed"
    if _EGW_TOKEN_RE.match(t):
        return "egw"
    if _ENTRY_ID_RE.match(t) and "-" in t:
        return "entry"
    if _PASSAGE_RE.match(t):
        return "passage"
    return "malformed"


def _normalize_passage_to_id(passage: str) -> str:
    """Normalize 'John 1:1' -> 'john-1-1' for id-style matching (best effort)."""
    parts = passage.split(":")
    if len(parts) != 2:
        return passage.lower().replace(" ", "-")
    book = parts[0].strip()
    chap_verse = parts[1].strip()
    if "-" in chap_verse or "–" in chap_verse:
        chap_verse = chap_verse.split("-")[0].split("–")[0]
    return f"{book.lower().replace(' ', '-')}-{chap_verse}"


def build_entry_index(loader) -> dict[str, str]:
    """Map every entry id and normalized passage to the entry id.

    Returns {candidate_target: entry_id}. A target resolves if it is in this
    map (either as an entry id or as a normalized passage).
    """
    index: dict[str, str] = {}
    for entry in loader.entries:
        index[entry.id] = entry.id
        if entry.passage:
            normalized = _normalize_passage_to_id(entry.passage)
            index[normalized] = entry.id
            # Also index the raw passage string.
            index[entry.passage.strip()] = entry.id
    return index


def validate_cross_references(entry, entry_index: dict[str, str], egw_db=None) -> list[Issue]:
    """Validate one entry's cross_references. Returns issues."""
    issues: list[Issue] = []
    fm = entry.frontmatter or {}
    xrefs = fm.get("cross_references")
    if xrefs is None:
        return issues
    if not isinstance(xrefs, list):
        return issues  # structural shape already reported by F1

    for i, xr in enumerate(xrefs):
        if not isinstance(xr, dict):
            continue
        target = xr.get("target")
        if not target:
            continue  # empty/missing target reported by F1
        kind = classify_target(target)
        if kind == "malformed":
            issues.append(
                Issue(entry.id, "malformed-xref-target", "error",
                      f"cross_references[{i}] target '{target}' is neither an entry id, passage reference, nor EGW citation token")
            )
            continue
        # EGW citation tokens.
        if kind == "egw":
            if egw_db is not None and egw_db.exists():
                if egw_db.get_paragraph(target) is not None:
                    continue
                issues.append(
                    Issue(entry.id, "unresolved-egw-target", "warning",
                          f"cross_references[{i}] target '{target}' is not found in local data/egw.db")
                )
            # If egw_db is not present, token shape is valid per ADR-0011 (no warning/error).
            continue
        # Resolvability for entry ids and passage references.
        if target.strip() in entry_index:
            continue
        issues.append(
            Issue(entry.id, "unresolved-xref-target", "warning",
                  f"cross_references[{i}] target '{target}' is well-formed but not found in the corpus (forward reference?)")
        )
    return issues


def validate_all(loader, egw_db=None) -> list[Issue]:
    """Validate cross_references across every entry."""
    index = build_entry_index(loader)
    if egw_db is None:
        try:
            from search.linking.egw import EgwDB
            repo_path = getattr(loader, "repo_root", ".")
            db = EgwDB(repo_root=repo_path)
            if db.exists():
                egw_db = db
        except Exception:
            egw_db = None

    issues: list[Issue] = []
    for entry in loader.entries:
        issues.extend(validate_cross_references(entry, index, egw_db=egw_db))
    return issues


def main(argv=None) -> int:
    import argparse

    from search.linking.loader import Loader

    parser = argparse.ArgumentParser(prog="validate-xrefs", description="F3: cross-reference integrity")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--fail-on-unresolved", action="store_true",
                        help="Promote unresolved (forward) targets to errors (default: warning)")
    args = parser.parse_args(argv)

    loader = Loader(args.repo)
    loader.load_entries()
    issues = validate_all(loader)

    if args.fail_on_unresolved:
        for i in issues:
            if i.code == "unresolved-xref-target":
                i.severity = "error"

    for issue in issues:
        print(issue)
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    if not args.quiet:
        print(f"\n{len(issues)} issues: {errors} error(s), {warnings} warning(s) across {len(loader.entries)} entries")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())