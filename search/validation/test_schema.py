"""Tests for F1 — the schema validator."""

from __future__ import annotations

import unittest

from search.validation.schema import Taxonomy, validate_entry, validate_tags, validate_all
from search.linking.loader import Loader, Entry


def make_entry(overrides=None):
    """Build a minimal schema-valid entry fixture; override fields via dict."""
    base = {
        "id": "gen-1-1-kjv",
        "type": "material/bible",
        "book": "book/genesis",
        "passage": "Genesis 1:1",
        "tags": ["material/bible", "book/genesis", "theme/creation"],
        "source": "source/bible",
        "language": "hebrew",
        "translation": "kjv",
        "level": "intro",
        "status": "review",
        "created": "2026-08-23",
        "updated": "2026-08-24",
    }
    if overrides:
        base.update(overrides)
    return Entry(
        id=base["id"],
        path="materials/test.md",
        frontmatter=base,
        body="",
        tags=base.get("tags", []),
    )


class TaxonomyTests(unittest.TestCase):
    def test_loads_from_repo(self):
        tax = Taxonomy("tags/taxonomy.json")
        self.assertTrue(tax.is_valid_value("material", "material/bible"))
        self.assertTrue(tax.is_valid_value("theme", "theme/creation"))
        self.assertFalse(tax.is_valid_value("theme", "theme/not-real"))
        self.assertIn("strongs-H", tax.strongs_prefixes)

    def test_category_for_tag(self):
        tax = Taxonomy("tags/taxonomy.json")
        self.assertEqual(tax.category_for_tag("material/bible"), "material")
        self.assertEqual(tax.category_for_tag("lang/hebrew"), "language")
        self.assertEqual(tax.category_for_tag("strongs-H7225"), "strongs")
        self.assertIsNone(tax.category_for_tag("totally/bogus"))


class SchemaValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tax = Taxonomy("tags/taxonomy.json")
        cls.loader = Loader(".")
        cls.loader.load_entries()

    def _codes(self, entry):
        return {i.code for i in validate_entry(self.tax, entry)}

    def test_real_entries_pass(self):
        """The current MVP entries should be schema-valid (no errors)."""
        issues = validate_all(self.loader, self.tax)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(
            errors, [],
            f"Expected zero errors on current corpus, got: {[str(e) for e in errors]}",
        )

    def test_missing_required_field(self):
        # Omit the required 'source' field and assert it is specifically caught.
        entry = make_entry()
        entry.frontmatter.pop("source", None)
        codes = self._codes(entry)
        missing = [i for i in validate_entry(self.tax, entry) if i.code == "missing-field"]
        self.assertIn("missing-field", codes)
        self.assertTrue(any("source" in m.message for m in missing), "should name the 'source' field")

    def test_unknown_tag_flagged(self):
        entry = make_entry({"tags": ["material/bible", "book/genesis", "theme/creation", "bogus/tag"]})
        self.assertIn("unknown-tag", self._codes(entry))

    def test_out_of_taxonomy_tag(self):
        entry = make_entry({"tags": ["material/bible", "book/genesis", "theme/not-real"]})
        self.assertIn("out-of-taxonomy-tag", self._codes(entry))

    def test_missing_material_tag(self):
        entry = make_entry({"tags": ["book/genesis", "theme/creation"]})
        self.assertIn("missing-material-tag", self._codes(entry))

    def test_missing_book_theme_tag(self):
        entry = make_entry({"tags": ["material/bible", "theme/creation"]})
        # has theme -> ok
        self.assertNotIn("missing-book-theme-tag", self._codes(entry))
        entry2 = make_entry({"tags": ["material/bible"]})
        self.assertIn("missing-book-theme-tag", self._codes(entry2))

    def test_bad_xref_structure(self):
        entry = make_entry({"cross_references": "not-a-list"})
        self.assertIn("bad-xref-structure", self._codes(entry))

    def test_xref_type_not_in_taxonomy(self):
        entry = make_entry({"cross_references": [{"type": "xref/bogus", "target": "john-1-1"}]})
        codes = self._codes(entry)
        self.assertIn("bad-xref-type", codes)

    def test_xref_valid_type_passes(self):
        entry = make_entry({"cross_references": [{"type": "xref/fulfillment", "target": "john-1-1"}]})
        self.assertNotIn("bad-xref-type", self._codes(entry))

    def test_xref_missing_target(self):
        entry = make_entry({"cross_references": [{"type": "xref/theme"}]})
        self.assertIn("bad-xref-item", self._codes(entry))

    def test_bad_level(self):
        entry = make_entry({"level": "bogus"})
        self.assertIn("bad-level", self._codes(entry))

    def test_valid_bare_level_passes(self):
        for lvl in ("intro", "intermediate", "advanced"):
            entry = make_entry({"level": lvl})
            self.assertNotIn("bad-level", self._codes(entry), f"level {lvl} should be valid")

    def test_bad_date(self):
        entry = make_entry({"created": "not-a-date"})
        self.assertIn("bad-date", self._codes(entry))

    def test_valid_date_passes(self):
        entry = make_entry({"created": "2026-08-23"})
        self.assertNotIn("bad-date", self._codes(entry))

    def test_bad_translation_flagged(self):
        entry = make_entry({"translation": "not-a-real-version"})
        self.assertIn("bad-translation", self._codes(entry))

    def test_valid_bare_translation_passes(self):
        entry = make_entry({"translation": "kjv"})
        self.assertNotIn("bad-translation", self._codes(entry))

    def test_bad_source_shape(self):
        entry = make_entry({"source": "the-bible"})
        self.assertIn("bad-source", self._codes(entry))

    def test_valid_source_passes(self):
        entry = make_entry({"source": "source/bible"})
        self.assertNotIn("bad-source", self._codes(entry))

    def test_original_language_requires_strongs_tag(self):
        entry = make_entry({"type": "material/original-language", "tags": ["material/original-language", "lang/hebrew"]})
        self.assertIn("missing-strongs-tag", self._codes(entry))

    def test_original_language_with_strongs_passes(self):
        entry = make_entry({"type": "material/original-language", "tags": ["material/original-language", "lang/hebrew", "strongs-H7225"]})
        self.assertNotIn("missing-strongs-tag", self._codes(entry))

    def test_bad_id_format(self):
        entry = make_entry({"id": "Gen 1:1 KJV"})
        self.assertIn("bad-id-format", self._codes(entry))

    def test_bad_status_prefixed_rejected(self):
        # kc-schema documents status as a bare value; the prefixed form is invalid.
        entry = make_entry({"status": "status/draft"})
        self.assertIn("bad-status", self._codes(entry))

    def _codes(self, entry):
        return {i.code for i in validate_entry(self.tax, entry)}


if __name__ == "__main__":
    unittest.main(verbosity=2)