"""Tests for F3 — cross-reference integrity checker."""

from __future__ import annotations

import unittest

from search.validation.xrefs import (
    classify_target,
    _normalize_passage_to_id as normalize_passage_to_id,
    build_entry_index,
    validate_cross_references,
    validate_all,
)
from search.linking.loader import Loader, Entry


def _entry(eid, passage="", xrefs=None, tags=None):
    fm = {"id": eid, "passage": passage, "cross_references": xrefs or [], "tags": tags or []}
    return Entry(id=eid, path="materials/test.md", frontmatter=fm, body="", tags=fm["tags"])


class ClassifyTargetTests(unittest.TestCase):
    def test_entry_id(self):
        self.assertEqual(classify_target("john-1-1"), "entry")
        self.assertEqual(classify_target("gen-1-1-kjv"), "entry")
        self.assertEqual(classify_target("2peter-3-5-7"), "entry")
        self.assertEqual(classify_target("1cor-13-1"), "entry")

    def test_passage(self):
        self.assertEqual(classify_target("John 1:1"), "passage")
        self.assertEqual(classify_target("Genesis 1:1"), "passage")
        self.assertEqual(classify_target("2 Peter 3:5-7"), "passage")
        self.assertEqual(classify_target("1 Corinthians 13:1"), "passage")

    def test_malformed(self):
        for bad in ("", "garbage!!!", "John 1", "1:1", "John:1:1", "a b c", "1-1"):
            self.assertEqual(classify_target(bad), "malformed", f"{bad!r} should be malformed")


class NormalizeTests(unittest.TestCase):
    def test_passage_to_id(self):
        self.assertEqual(normalize_passage_to_id("John 1:1"), "john-1-1")
        self.assertEqual(normalize_passage_to_id("Genesis 1:1"), "genesis-1-1")
        self.assertEqual(normalize_passage_to_id("2 Peter 3:5-7"), "2-peter-3-5")


class XrefValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader = Loader(".")
        cls.loader.load_entries()

    def test_entry_index(self):
        idx = build_entry_index(self.loader)
        self.assertIn("gen-1-1-kjv", idx)
        self.assertIn("genesis-1-1", idx)  # normalized passage of the entry

    def test_resolved_target_no_issue(self):
        idx = {"gen-1-1-kjv": "gen-1-1-kjv"}
        entry = _entry("x", xrefs=[{"type": "xref/theme", "target": "gen-1-1-kjv"}])
        issues = validate_cross_references(entry, idx)
        self.assertEqual(issues, [])

    def test_forward_reference_is_warning_not_error(self):
        idx = {"gen-1-1-kjv": "gen-1-1-kjv"}
        entry = _entry("x", xrefs=[{"type": "xref/fulfillment", "target": "john-1-1"}])
        issues = validate_cross_references(entry, idx)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "unresolved-xref-target")
        self.assertEqual(issues[0].severity, "warning")

    def test_malformed_target_is_error(self):
        idx = {}
        entry = _entry("x", xrefs=[{"type": "xref/theme", "target": "!!!garbage!!!"}])
        issues = validate_cross_references(entry, idx)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "malformed-xref-target")
        self.assertEqual(issues[0].severity, "error")

    def test_validate_all_real_corpus(self):
        """Real corpus uses forward references (john-1-1 etc.) -> warnings, no errors."""
        issues = validate_all(self.loader)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [], f"no malformed targets expected: {[str(e) for e in errors]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)