"""Tests for F4 — dead-reference / broken-link audit."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from search.validation.audit import (
    audit_related,
    audit_semantic_links,
    audit_links_file,
    audit_links_index,
    audit_all,
)
from search.linking.loader import Loader, Entry


def _entry(eid, related=None, semlinks=None, passage=""):
    fm = {"id": eid, "passage": passage, "related": related or [], "semantic_links": semlinks or []}
    return Entry(id=eid, path="materials/test.md", frontmatter=fm, body="", tags=[])


class RelatedAuditTests(unittest.TestCase):
    def test_unresolved_related_is_warning(self):
        loader = Loader(".")
        loader.entries = [_entry("a"), _entry("b", related=[{"id": "c"}])]
        issues = audit_related(loader)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "unresolved-related")
        self.assertEqual(issues[0].severity, "warning")

    def test_resolved_related_ok(self):
        loader = Loader(".")
        loader.entries = [_entry("a"), _entry("b", related=[{"id": "a"}])]
        self.assertEqual(audit_related(loader), [])


class SemanticLinksAuditTests(unittest.TestCase):
    def test_unknown_semantic_link(self):
        loader = Loader(".")
        loader.entries = [_entry("a", semlinks=["sl-999"])]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "links.json"
            p.write_text(json.dumps({"links": [{"id": "sl-001"}]}), encoding="utf-8")
            issues = audit_semantic_links(loader, p)
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].code, "unknown-semantic-link")

    def test_known_semantic_link_ok(self):
        loader = Loader(".")
        loader.entries = [_entry("a", semlinks=["sl-001"])]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "links.json"
            p.write_text(json.dumps({"links": [{"id": "sl-001"}]}), encoding="utf-8")
            self.assertEqual(audit_semantic_links(loader, p), [])


class LinksFileAuditTests(unittest.TestCase):
    def test_duplicate_id_and_missing_strongs(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "links.json"
            p.write_text(json.dumps({
                "links": [
                    {"id": "sl-001", "entries": [{"strongs": "H7225"}]},
                    {"id": "sl-001", "entries": [{"strongs": "G746"}]},
                    {"id": "sl-002", "entries": [{"word": "no strongs here"}]},
                ]
            }), encoding="utf-8")
            issues = audit_links_file(p)
            codes = {i.code for i in issues}
            self.assertIn("duplicate-link-id", codes)
            self.assertIn("link-entry-no-strongs", codes)

    def test_valid_links_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "links.json"
            p.write_text(json.dumps({
                "links": [{"id": "sl-001", "entries": [{"strongs": "H7225"}, {"strongs": "G746"}]}]
            }), encoding="utf-8")
            self.assertEqual(audit_links_file(p), [])


class LinksIndexAuditTests(unittest.TestCase):
    def test_index_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            links = Path(td) / "links.json"
            idx = Path(td) / "index.json"
            links.write_text(json.dumps({
                "links": [{"id": "sl-001", "entries": [{"strongs": "H7225"}, {"strongs": "G746"}]}]
            }), encoding="utf-8")
            # Index omits G746 -> mismatch flagged.
            idx.write_text(json.dumps({"by_strongs": {"H7225": ["sl-001"]}}), encoding="utf-8")
            issues = audit_links_index(links, idx)
            self.assertTrue(any(i.code == "index-missing-strongs" for i in issues))

    def test_index_matches(self):
        with tempfile.TemporaryDirectory() as td:
            links = Path(td) / "links.json"
            idx = Path(td) / "index.json"
            links.write_text(json.dumps({
                "links": [{"id": "sl-001", "entries": [{"strongs": "H7225"}, {"strongs": "G746"}]}]
            }), encoding="utf-8")
            idx.write_text(json.dumps({
                "by_strongs": {"H7225": ["sl-001"], "G746": ["sl-001"]}
            }), encoding="utf-8")
            self.assertEqual(audit_links_index(links, idx), [])


class AuditAllTests(unittest.TestCase):
    def test_audit_all_real_repo_no_errors(self):
        """The real corpus: unresolved forward refs/links are warnings, no errors."""
        loader = Loader(".")
        loader.load_entries()
        issues = audit_all(loader, ".")
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [], f"no errors expected: {[str(e) for e in errors]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)