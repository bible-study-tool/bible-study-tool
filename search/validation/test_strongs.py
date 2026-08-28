"""Tests for F2 — Strong's number verification."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from search.validation.strongs import (
    StrongsCanonical,
    parse_strongs,
    validate_strongs_tag,
    validate_entry_strongs,
    validate_all,
)
from search.validation.build_strongs_list import extract_from_json, extract_from_text
from search.linking.loader import Loader, Entry


def _entry(tags, eid="x"):
    return Entry(id=eid, path="materials/test.md", frontmatter={"tags": tags}, body="", tags=tags)


class ParseStrongsTests(unittest.TestCase):
    def test_valid_hebrew_and_greek(self):
        self.assertEqual(parse_strongs("strongs-H7225"), ("H", 7225))
        self.assertEqual(parse_strongs("strongs-G2532"), ("G", 2532))

    def test_malformed(self):
        for bad in ("strongs-X7225", "strongs-7225", "strongs-H", "H7225", "strongs-Habc"):
            self.assertIsNone(parse_strongs(bad), f"should reject {bad!r}")

    def test_case_insensitive_prefix(self):
        self.assertEqual(parse_strongs("strongs-h7225"), ("H", 7225))


class ValidateStrongsTests(unittest.TestCase):
    def test_valid_passes(self):
        self.assertEqual(validate_strongs_tag("strongs-H7225"), [])

    def test_malformed_flagged(self):
        issues = validate_strongs_tag("strongs-X7225")
        self.assertEqual(issues[0].code, "malformed-strongs")
        self.assertEqual(issues[0].severity, "error")

    def test_out_of_range(self):
        # 4-digit numbers exceeding the real maxima (H<=8674, G<=5624).
        issues = validate_strongs_tag("strongs-H9999")
        self.assertEqual(issues[0].code, "out-of-range-strongs")
        issues2 = validate_strongs_tag("strongs-G9999")
        self.assertEqual(issues2[0].code, "out-of-range-strongs")

    def test_unknown_vs_canonical(self):
        canon = StrongsCanonical(hebrew={"H7225"}, greek={"G2532"})
        self.assertEqual(validate_strongs_tag("strongs-H7225", canon), [])
        issues = validate_strongs_tag("strongs-H0001", canon)
        self.assertEqual(issues[0].code, "unknown-strongs")

    def test_entry_validation_binds_id(self):
        entry = _entry(["strongs-X9999"])
        issues = validate_entry_strongs(entry)
        self.assertEqual(issues[0].entry_id, "test-entry" if False else "x")


class CanonicalTests(unittest.TestCase):
    def test_load_missing_returns_none(self):
        self.assertIsNone(StrongsCanonical.load("does-not-exist.json"))

    def test_load_and_check(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "list.json"
            p.write_text(json.dumps({"hebrew": ["H7225"], "greek": ["G2532"]}), encoding="utf-8")
            canon = StrongsCanonical.load(p)
            self.assertIsNotNone(canon)
            self.assertTrue(canon.has("H7225"))
            self.assertTrue(canon.has("G2532"))
            self.assertFalse(canon.has("H0001"))

    def test_validate_all_uses_canonical(self):
        # H0001 is a 4-digit, in-range but NOT in the canonical set -> unknown.
        canon = StrongsCanonical(hebrew={"H7225"}, greek=set())
        entry = _entry(["strongs-H0001", "strongs-H7225"])
        loader = Loader(".")
        loader.entries = [entry]
        issues = validate_all(loader, canon)
        codes = {i.code for i in issues}
        self.assertIn("unknown-strongs", codes)


class BuildListTests(unittest.TestCase):
    def test_extract_from_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "kjv.json"
            p.write_text(json.dumps([
                {"text": "In the beginning <H7225>God</H7225> <H1254>created</H1254>"},
                {"text": "And <G2532>God</G2532> said"},
            ]), encoding="utf-8")
            codes = extract_from_json(p)
            self.assertIn("H7225", codes)
            self.assertIn("H1254", codes)
            self.assertIn("G2532", codes)

    def test_extract_from_text(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "kjv.txt"
            p.write_text("In the beginning <H7225>God</H7225> <G2532>kai</G2532>.", encoding="utf-8")
            codes = extract_from_text(str(p))
            self.assertIn("H7225", codes)
            self.assertIn("G2532", codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)