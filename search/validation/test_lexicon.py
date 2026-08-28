"""Tests for the Strong's lexicon generator (A4) and F2 canonical integration."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from search.validation.build_strongs_lexicon import parse_go_file, _clean_desc
from search.validation.strongs import StrongsCanonical, validate_strongs_tag


class CleanDescTests(unittest.TestCase):
    def test_unescapes_entities(self):
        d = _clean_desc("Strong&apos;s Number H1: ab (awb) n-m.\\n1. father")
        self.assertIn("'", d)
        self.assertIn("\n", d)

    def test_numeric_entities(self):
        d = _clean_desc("ab (aw-bad&#039;) v.")
        self.assertIn("'", d)


class ParseGoFileTests(unittest.TestCase):
    def _write(self, td, content):
        p = Path(td) / "strongs.go"
        p.write_text(content, encoding="utf-8")
        return p

    def test_parses_entries(self):
        with tempfile.TemporaryDirectory() as td:
            content = (
                'package strongs\nvar Hebrew = map[string]*Entry{\n'
                '\t"אב": &Entry{Num: 1, Word: "אָב", Length: 2, '
                'Desc: "Strong&apos;s Number H1: ab (awb) n-m.\\n1. father KJV: chief"},\n'
                '\t"אבד": &Entry{Num: 6, Word: "אָבַד", Length: 3, '
                'Desc: "Strong&apos;s Number H6: abad (aw-bad&#039;) v.\\n1. perish"},\n'
                '}\n'
            )
            p = self._write(td, content)
            entries = parse_go_file(str(p))
            self.assertIn(1, entries)
            self.assertIn(6, entries)
            self.assertEqual(entries[1]["translit"], "awb")
            self.assertEqual(entries[6]["translit"], "aw-bad'")

    def test_keeps_commented_duplicates_as_valid_numbers(self):
        """'DUP - SEE ABOVE' commented entries are distinct valid Strong's
        numbers (they share only a Hebrew/Greek spelling KEY with an earlier
        entry). They must be kept so the canonical 8674/5624 totals (which F2's
        bounds depend on) are preserved."""
        with tempfile.TemporaryDirectory() as td:
            content = (
                'package strongs\nvar Hebrew = map[string]*Entry{\n'
                '\t"אב": &Entry{Num: 1, Word: "אָב", Length: 2, '
                'Desc: "Strong&apos;s Number H1: ab (awb) n-m.\\n1. father"},\n'
                '\t// "אב": // DUP - SEE ABOVE // &Entry{Num: 2, Word: "אַב", '
                'Length: 2, Desc: "Strong&apos;s Number H2: ab (ab) n-m.\\n1. father"},\n'
                '\t// "אב": // DUP - SEE ABOVE // &Entry{Num: 3, Word: "אֵב", '
                'Length: 2, Desc: "Strong&apos;s Number H3: eb (abe) n-m.\\n1. a green plant"},\n'
                '}\n'
            )
            p = self._write(td, content)
            entries = parse_go_file(str(p))
            # H1, H2, H3 are all distinct valid Strong's numbers.
            self.assertIn(1, entries)
            self.assertIn(2, entries)
            self.assertIn(3, entries)
            self.assertEqual(len(entries), 3)

    def _write(self, td, content):
        p = Path(td) / "strongs.go"
        p.write_text(content, encoding="utf-8")
        return p


class CanonicalIntegrationTests(unittest.TestCase):
    def test_list_matches_lexicon_counts(self):
        """The committed list and lexicon must agree on counts."""
        lst = json.load(open("lexicons/strongs-list.json"))
        lex = json.load(open("lexicons/strongs-lexicon.json"))
        self.assertEqual(len(lst["hebrew"]), lst["hebrew_count"])
        self.assertEqual(len(lst["greek"]), lst["greek_count"])
        self.assertEqual(len(lst["hebrew"]), len(lex["hebrew"]))
        self.assertEqual(len(lst["greek"]), len(lex["greek"]))

    def test_canonical_totals(self):
        """The canonical enumeration must be the FULL Strong's set (8674 H /
        5624 G). F2's out-of-range bounds and the documented fingerprints in
        data/PROVENANCE.md depend on these exact totals; a bad re-pin that
        dropped entries would still be internally consistent, so pin the
        absolute numbers here."""
        lst = json.load(open("lexicons/strongs-list.json"))
        self.assertEqual(len(lst["hebrew"]), 8674)
        self.assertEqual(len(lst["greek"]), 5624)
        # Boundary numbers must be present.
        for code in ("H1", "H8674", "G1", "G5624", "H2", "H6791"):
            letter, num = code[0], int(code[1:])
            pool = lst["hebrew"] if letter == "H" else lst["greek"]
            self.assertIn(code, pool, f"{code} must be in the canonical list")

    def test_known_codes_in_canonical(self):
        lst = json.load(open("lexicons/strongs-list.json"))
        canon = StrongsCanonical(hebrew=set(lst["hebrew"]), greek=set(lst["greek"]))
        # These are codes used by the current corpus + curated links.
        for code in ("H7225", "H430", "H1254", "H8414", "H7307", "H7363",
                     "G746", "G2936", "G2532"):
            self.assertTrue(canon.has(code), f"{code} should be in canonical list")

    def test_real_corpus_passes_canonical(self):
        """F2 in canonical mode must accept the current corpus (0 errors)."""
        from search.linking.loader import Loader
        from search.validation.strongs import validate_all
        lst = json.load(open("lexicons/strongs-list.json"))
        canon = StrongsCanonical(hebrew=set(lst["hebrew"]), greek=set(lst["greek"]))
        loader = Loader(".")
        loader.load_entries()
        issues = validate_all(loader, canon)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [], f"canonical validation errors: {[str(e) for e in errors]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)