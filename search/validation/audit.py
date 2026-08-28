"""F4 — Dead-reference / broken-link audit.

A broader consistency audit across the knowledge base's reference graph. F1
(schema) checks structure, F3 (xrefs) checks ``cross_references``; this audit
checks the *remaining* reference surfaces and the curated semantic-links data
itself:

  * ``related[].id``   -> must be a well-formed id; unresolved ones are forward
                          references (warning).
  * ``semantic_links`` -> each referenced link id must exist in
                          ``correlations/semantic-links.json`` (warning if not).
  * ``semantic-links.json`` internal consistency:
        - no duplicate link ids
        - every entry in a link carries a Strong's number
        - every ``semantic_links`` id in any entry resolves to a real link
  * ``semantic-links-index.json`` consistency: its ``by_strongs`` must match
    the strongs actually declared in ``semantic-links.json``.

This is the "audit" counterpart to F3's focused check — it aggregates
dead references so a curator can see the whole unhealthy-reference surface at
once.
"""

from __future__ import annotations

import json
from pathlib import Path

from .schema import Issue


def _load_json(path: str | Path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def audit_related(loader) -> list[Issue]:
    issues: list[Issue] = []
    entry_ids = {e.id for e in loader.entries}
    for entry in loader.entries:
        related = (entry.frontmatter or {}).get("related") or []
        if not isinstance(related, list):
            continue  # structure handled by F1
        for r in related:
            if isinstance(r, dict):
                rid = r.get("id")
            else:
                continue
            if not rid:
                continue
            if rid not in entry_ids:
                issues.append(
                    Issue(entry.id, "unresolved-related", "warning",
                          f"related id '{rid}' not found in corpus (forward reference?)")
                )
    return issues


def audit_semantic_links(loader, links_path="correlations/semantic-links.json") -> list[Issue]:
    """Check entry semantic_links against the curated links file."""
    issues: list[Issue] = []
    links_data = _load_json(links_path)
    link_ids = {l.get("id") for l in (links_data or {}).get("links", [])} if links_data else set()

    for entry in loader.entries:
        sl = (entry.frontmatter or {}).get("semantic_links") or []
        if not isinstance(sl, list):
            continue
        for lid in sl:
            if lid not in link_ids:
                issues.append(
                    Issue(entry.id, "unknown-semantic-link", "warning",
                          f"semantic_links references '{lid}' which is not in {links_path}")
                )
    return issues


def audit_links_file(links_path="correlations/semantic-links.json") -> list[Issue]:
    """Check internal consistency of semantic-links.json itself."""
    issues: list[Issue] = []
    data = _load_json(links_path)
    if data is None:
        return [Issue("(semantic-links.json)", "missing-links-file", "warning", f"{links_path} not found or unreadable")]
    links = data.get("links", [])
    seen: set[str] = set()
    for link in links:
        lid = link.get("id")
        if lid in seen:
            issues.append(Issue(lid, "duplicate-link-id", "error", f"duplicate semantic link id '{lid}'"))
        seen.add(lid)
        for ent in link.get("entries", []):
            # A lexical entry (has a word/transliteration) MUST carry a
            # Strong's number. Concept annotations (english_concept/notes) are
            # metadata, not lexical entries, so they legitimately have none.
            is_lexical = bool(ent.get("word") or ent.get("transliteration"))
            if is_lexical and not ent.get("strongs"):
                issues.append(Issue(lid, "link-entry-no-strongs", "error", f"link '{lid}' has a lexical entry without a Strong's number"))
    return issues


def audit_links_index(
    links_path="correlations/semantic-links.json",
    index_path="correlations/semantic-links-index.json",
) -> list[Issue]:
    """Check semantic-links-index.json by_strongs matches the links file."""
    issues: list[Issue] = []
    links_data = _load_json(links_path)
    idx_data = _load_json(index_path)
    if links_data is None or idx_data is None:
        return issues  # absence handled elsewhere

    # Canonical: strongs -> link ids, from the source of truth (links file).
    by_strongs = {}
    for link in links_data.get("links", []):
        lid = link.get("id")
        for ent in link.get("entries", []):
            s = ent.get("strongs")
            if s:
                by_strongs.setdefault(s, []).append(lid)

    indexed = (idx_data.get("by_strongs") or {})
    for s, lids in by_strongs.items():
        if s not in indexed:
            issues.append(Issue("(index)", "index-missing-strongs", "warning", f"semantic-links-index.json missing strongs {s}"))
        elif set(indexed.get(s, [])) != set(lids):
            issues.append(Issue("(index)", "index-mismatch", "warning", f"semantic-links-index.json strongs {s} mismatch"))
    return issues


def audit_all(loader, repo=".") -> list[Issue]:
    issues: list[Issue] = []
    issues.extend(audit_related(loader))
    issues.extend(audit_semantic_links(loader, Path(repo) / "correlations/semantic-links.json"))
    issues.extend(audit_links_file(Path(repo) / "correlations/semantic-links.json"))
    issues.extend(audit_links_index(
        Path(repo) / "correlations/semantic-links.json",
        Path(repo) / "correlations/semantic-links-index.json",
    ))
    return issues


def main(argv=None) -> int:
    import argparse

    from search.linking.loader import Loader

    parser = argparse.ArgumentParser(prog="audit-links", description="F4: dead-reference / broken-link audit")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    loader = Loader(args.repo)
    loader.load_entries()
    issues = audit_all(loader, args.repo)

    for issue in issues:
        print(issue)
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    if not args.quiet:
        print(f"\n{len(issues)} issues: {errors} error(s), {warnings} warning(s) across {len(loader.entries)} entries")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())