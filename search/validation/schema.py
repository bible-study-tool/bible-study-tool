"""F1 — Schema validator.

Validates every entry's YAML frontmatter against the documented schema
(``kc-schema.md``), the tag taxonomy (``tags/taxonomy.json``), and the
contribution standards (``CONTRIBUTION_STANDARDS.md``).

The whole point is to catch, *before* bad data accumulates, exactly the kind
of structural problem that previously corrupted the knowledge base (malformed
nested frontmatter, out-of-taxonomy tags, missing required fields, a wrong
Strong's number, unresolvable cross-references).

Design goals
------------
* Deterministic and offline (no AI, no network).
* Emits structured, human-readable issues: (entry_id, code, message).
* Distinguishes *errors* (must-fix, block CI) from *warnings* (advisory).
* Driven by the single source of truth for controlled vocabulary:
  ``tags/taxonomy.json``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Categories whose tag values are exactly ``<category>/<value>``.
# The taxonomy stores these as {category: {values: [...]}}.
_CATEGORY_VALUES = {
    "material",
    "book",
    "theme",
    "language",  # note: tag prefix is 'lang/', category key is 'language'
    "translation",
    "genre",
    "era",
    "xref",
    "relation",
    "level",
    "status",
    "ai",
}

# Maps the on-disk tag prefix to the taxonomy category key.
_PREFIX_TO_CATEGORY = {
    "material/": "material",
    "book/": "book",
    "theme/": "theme",
    "lang/": "language",
    "translation/": "translation",
    "genre/": "genre",
    "era/": "era",
    "xref/": "xref",
    "relation/": "relation",
    "level/": "level",
    "status/": "status",
    "ai/": "ai",
}

# Strong's tags are dynamic: 'strongs-H####' / 'strongs-G####'.
_STRONGS_RE = re.compile(r"^strongs-([HG])(\d{1,4})$")

# Fields required by CONTRIBUTION_STANDARDS.md (Required Fields).
REQUIRED_FIELDS = {
    "id": "unique identifier following naming convention",
    "type": "material type from taxonomy",
    "book": "biblical book or category",
    "source": "source attribution",
    "tags": "at least one theme tag and one category tag",
    "status": "draft, review, or final",
    "language": "language of the content",
}

# type: must be a material/ value. status: must be a status/ value.
_STATUS_TAGS = {"status/draft", "status/review", "status/final", "status/needs-update"}


@dataclass
class Issue:
    """A single validation finding."""

    entry_id: str
    code: str            # e.g. 'missing-field', 'unknown-tag', 'bad-strongs'
    severity: str        # 'error' | 'warning'
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.severity}] {self.entry_id}: {self.code} — {self.message}"


class Taxonomy:
    """Loads and indexes the controlled vocabulary from taxonomy.json."""

    def __init__(self, path: str | Path = "tags/taxonomy.json"):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as fh:
            self.data = json.load(fh)
        self.categories = self.data.get("categories", {})

        # category key -> set of valid full tag values
        self._valid_values: dict[str, set[str]] = {}
        for cat, meta in self.categories.items():
            vals = meta.get("values", [])
            self._valid_values[cat] = set(vals)

        # Dynamic strongs prefixes ('strongs-H', 'strongs-G')
        self.strongs_prefixes = tuple(
            self.categories.get("strongs", {}).get("prefixes", [])
        )

    def is_valid_value(self, category: str, value: str) -> bool:
        return value in self._valid_values.get(category, set())

    def category_for_tag(self, tag: str) -> str | None:
        """Return the taxonomy category a tag belongs to, or None if unknown.

        Handles both static 'cat/value' tags and dynamic 'strongs-H1234' tags.
        """
        for prefix, cat in _PREFIX_TO_CATEGORY.items():
            if tag.startswith(prefix):
                return cat
        if _STRONGS_RE.match(tag):
            return "strongs"
        return None


def _classify_tag(tax: Taxonomy, tag: str) -> str | None:
    return tax.category_for_tag(tag)


def validate_tags(tax: Taxonomy, entry_id: str, tags) -> list[Issue]:
    """Check that all tags conform to the taxonomy and entry-level rules."""
    issues: list[Issue] = []
    if tags is None:
        return [Issue(entry_id, "missing-field", "error", "'tags' is required")]
    if isinstance(tags, str):
        tags = [tags]

    for tag in tags:
        if not isinstance(tag, str) or not tag:
            issues.append(Issue(entry_id, "malformed-tag", "error", f"invalid tag {tag!r}"))
            continue
        cat = _classify_tag(tax, tag)
        if cat is None:
            issues.append(
                Issue(entry_id, "unknown-tag", "error", f"tag '{tag}' not in taxonomy")
            )
            continue
        if cat == "strongs":
            # Format checked by regex; validity of the number itself is F2.
            continue
        if not tax.is_valid_value(cat, tag):
            issues.append(
                Issue(
                    entry_id,
                    "out-of-taxonomy-tag",
                    "error",
                    f"tag '{tag}' is not a valid {cat}/ value",
                )
            )

    # Rule: at least one material/ tag.
    if not any(str(t).startswith("material/") for t in tags):
        issues.append(
            Issue(entry_id, "missing-material-tag", "error", "no 'material/' tag present")
        )
    # Rule: at least one book/ or theme/ tag.
    if not any(str(t).startswith(("book/", "theme/")) for t in tags):
        issues.append(
            Issue(
                entry_id,
                "missing-book-theme-tag",
                "error",
                "must have at least one 'book/' or 'theme/' tag",
            )
        )
    # Rule: cross-reference tags must be valid xref/ types (advisory if absent).
    xref_tags = [str(t) for t in tags if str(t).startswith("xref/")]
    for t in xref_tags:
        if not tax.is_valid_value("xref", t):
            issues.append(
                Issue(entry_id, "bad-xref-tag", "error", f"invalid cross-reference tag '{t}'")
            )
    return issues


def validate_entry(tax: Taxonomy, entry, all_ids: set[str]) -> list[Issue]:
    """Validate a single loaded Entry against the schema.

    ``entry`` is a ``search.linking.loader.Entry`` (has .id, .frontmatter,
    .tags, .passage, etc.).
    """
    issues: list[Issue] = []
    fm = entry.frontmatter or {}
    eid = entry.id or "(unnamed)"

    # --- required fields -------------------------------------------------
    for field_name, _hint in REQUIRED_FIELDS.items():
        if field_name not in fm or fm.get(field_name) in (None, ""):
            issues.append(
                Issue(eid, "missing-field", "error", f"missing required field '{field_name}'")
            )

    # --- id ---------------------------------------------------------------
    if not eid or eid == "(unnamed)":
        issues.append(Issue(eid, "missing-id", "error", "entry has no id"))
    # NOTE: id uniqueness across entries is checked by the caller (loader
    # dedupes by id, so this validator checks the id against the full set).

    # --- type -------------------------------------------------------------
    etype = fm.get("type")
    if etype:
        if not etype.startswith("material/"):
            issues.append(Issue(eid, "bad-type", "error", f"type '{etype}' must be a material/ value"))
        elif not tax.is_valid_value("material", etype):
            issues.append(Issue(eid, "out-of-taxonomy-type", "error", f"type '{etype}' not in taxonomy"))

    # --- status -----------------------------------------------------------
    # kc-schema.md documents the status *field* as a bare value
    # (draft|review|final|needs-update), distinct from the status/ tags.
    status = fm.get("status")
    if status:
        bare = str(status).split("/")[-1]
        if bare not in {"draft", "review", "final", "needs-update"}:
            issues.append(
                Issue(eid, "bad-status", "error", f"status '{status}' is not a valid status value")
            )

    # --- book -------------------------------------------------------------
    book = fm.get("book")
    if book and not str(book).startswith("book/"):
        issues.append(Issue(eid, "bad-book", "error", f"book '{book}' should be a book/ value"))
    elif book and not tax.is_valid_value("book", book):
        issues.append(Issue(eid, "out-of-taxonomy-book", "error", f"book '{book}' not in taxonomy"))

    # --- tags -------------------------------------------------------------
    issues.extend(validate_tags(tax, eid, fm.get("tags")))

    # --- translation -------------------------------------------------------
    # The 'translation' field is a bare key (e.g. 'kjv'); it corresponds to a
    # translation/{key} tag in the taxonomy.
    translation = fm.get("translation")
    if translation:
        tx_tag = f"translation/{str(translation).split('/')[-1]}"
        if not tax.is_valid_value("translation", tx_tag):
            issues.append(
                Issue(eid, "bad-translation", "error", f"translation '{translation}' not in taxonomy")
            )

    # --- language ----------------------------------------------------------
    lang = fm.get("language")
    if lang and str(lang) not in {"hebrew", "greek", "aramaic", "english"}:
        issues.append(Issue(eid, "bad-language", "warning", f"language '{lang}' unusual"))

    # --- cross_references structure ---------------------------------------
    xrefs = fm.get("cross_references")
    if xrefs is not None:
        if not isinstance(xrefs, list):
            issues.append(Issue(eid, "bad-xref-structure", "error", "'cross_references' must be a list"))
        else:
            for i, xr in enumerate(xrefs):
                if not isinstance(xr, dict):
                    issues.append(Issue(eid, "bad-xref-item", "error", f"cross_references[{i}] must be an object"))
                    continue
                if "target" not in xr:
                    issues.append(Issue(eid, "bad-xref-item", "error", f"cross_references[{i}] missing 'target'"))
                xr_type = xr.get("type")
                if xr_type and not xr_type.startswith("xref/"):
                    issues.append(Issue(eid, "bad-xref-type", "error", f"cross_references[{i}] type '{xr_type}' invalid"))

    # --- semantic_links structure ------------------------------------------
    semlinks = fm.get("semantic_links")
    if semlinks is not None and not isinstance(semlinks, list):
        issues.append(Issue(eid, "bad-semantic-links", "error", "'semantic_links' must be a list"))

    # --- related structure -------------------------------------------------
    related = fm.get("related")
    if related is not None and not isinstance(related, list):
        issues.append(Issue(eid, "bad-related", "error", "'related' must be a list"))

    return issues


def validate_all(loader, tax: Taxonomy) -> list[Issue]:
    """Validate every entry in a Loader. Returns all issues."""
    issues: list[Issue] = []
    all_ids = {e.id for e in loader.entries}

    for entry in loader.entries:
        issues.extend(validate_entry(tax, entry, all_ids))

    # Check id uniqueness.
    seen: dict[str, int] = {}
    for entry in loader.entries:
        seen[entry.id] = seen.get(entry.id, 0) + 1
    for eid, count in seen.items():
        if count > 1:
            issues.append(Issue(eid, "duplicate-id", "error", f"duplicate id appears {count} times"))

    return issues


def summarize(issues: list[Issue]) -> tuple[int, int]:
    """Return (errors, warnings) counts."""
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    return errors, warnings


def main(argv=None) -> int:
    """CLI entry point. Exits non-zero if any error is found (CI-friendly)."""
    import argparse
    import sys

    from search.linking.loader import Loader

    parser = argparse.ArgumentParser(prog="validate-schema", description="F1: validate entry schema + tags against taxonomy")
    parser.add_argument("--repo", default=".", help="Path to the knowledge base repo")
    parser.add_argument("--taxonomy", default="tags/taxonomy.json", help="Path to the taxonomy JSON")
    parser.add_argument("--quiet", action="store_true", help="Only print issues, not the summary")
    args = parser.parse_args(argv)

    tax = Taxonomy(args.taxonomy)
    loader = Loader(args.repo)
    loader.load_entries()
    issues = validate_all(loader, tax)

    for issue in issues:
        print(issue)
    errors, warnings = summarize(issues)
    if not args.quiet:
        print(f"\n{len(issues)} issues: {errors} error(s), {warnings} warning(s) across {len(loader.entries)} entries")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
