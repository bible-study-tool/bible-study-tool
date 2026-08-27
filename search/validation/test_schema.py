"""Tests for F1 — the schema validator."""

from __future__ import annotations

import unittest

from search.validation.schema import Taxonomy, validate_entry, validate_tags, validate_all
from search.linking.loader import Loader


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

    def _fake_entry(self, frontmatter, body="", eid="test-entry"):
        from search.linking.loader import Entry
        return Entry(
            id=eid,
            path="materials/test.md",
            frontmatter=frontmatter,
            body=body,
            tags=frontmatter.get("tags", []),
        )

    def test_real_entries_pass(self):
        """The current MVP entries should be schema-valid (no errors)."""
        issues = validate_all(self.loader, self.tax)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(
            errors, [],
            f"Expected zero errors on current corpus, got: {[str(e) for e in errors]}",
        )

    def test_missing_required_field(self):
        # Omit the required 'source' field.
        fm = {"id": "x", "type": "material/bible", "book": "book/genesis",
              "status": "draft",
              "language": "hebrew", "tags": ["material/bible", "book/genesis", "theme/creation"]}
        entry = self._fake_entry(fm)
        issues = validate_entry(self.tax, entry, set())
        codes = {i.code for i in issues}
        self.assertIn("missing-field", codes)

    def test_unknown_tag_flagged(self):
        fm = {"id": "x", "type": "material/bible", "book": "book/genesis",
              "source": "source/bible", "status": "status/draft",
              "language": "hebrew",
              "tags": ["material/bible", "book/genesis", "theme/creation", "bogus/tag"]}
        entry = self._fake_entry(fm)
        issues = validate_entry(self.tax, entry, set())
        codes = {i.code for i in issues}
        self.assertIn("unknown-tag", codes)

    def test_out_of_taxonomy_tag(self):
        fm = {"id": "x", "type": "material/bible", "book": "book/genesis",
              "source": "source/bible", "status": "status/draft",
              "language": "hebrew",
              "tags": ["material/bible", "book/genesis", "theme/not-real"]}
        entry = self._fake_entry(fm)
        issues = validate_entry(self.tax, entry, set())
        codes = {i.code for i in issues}
        self.assertIn("out-of-taxonomy-tag", codes)

    def test_missing_material_tag(self):
        fm = {"id": "x", "type": "material/bible", "book": "book/genesis",
              "source": "source/bible", "status": "status/draft",
              "language": "hebrew",
              "tags": ["book/genesis", "theme/creation"]}
        entry = self._fake_entry(fm)
        issues = validate_entry(self.tax, entry, set())
        codes = {i.code for i in issues}
        self.assertIn("missing-material-tag", codes)

    def test_bad_xref_structure(self):
        fm = {"id": "x", "type": "material/bible", "book": "book/genesis",
              "source": "source/bible", "status": "status/draft",
              "language": "hebrew",
              "tags": ["material/bible", "book/genesis", "theme/creation"],
              "cross_references": "not-a-list"}
        entry = self._fake_entry(fm)
        issues = validate_entry(self.tax, entry, set())
        codes = {i.code for i in issues}
        self.assertIn("bad-xref-structure", codes)

    def test_bad_translation_flagged(self):
        fm = {"id": "x", "type": "material/bible", "book": "book/genesis",
              "source": "source/bible", "status": "draft",
              "language": "hebrew", "translation": "not-a-real-version",
              "tags": ["material/bible", "book/genesis", "theme/creation"]}
        entry = self._fake_entry(fm)
        issues = validate_entry(self.tax, entry, set())
        codes = {i.code for i in issues}
        self.assertIn("bad-translation", codes)

    def test_valid_bare_translation_passes(self):
        fm = {"id": "x", "type": "material/bible", "book": "book/genesis",
              "source": "source/bible", "status": "review",
              "language": "hebrew", "translation": "kjv",
              "tags": ["material/bible", "book/genesis", "theme/creation"]}
        entry = self._fake_entry(fm)
        issues = validate_entry(self.tax, entry, set())
        codes = {i.code for i in issues}
        self.assertNotIn("bad-translation", codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
