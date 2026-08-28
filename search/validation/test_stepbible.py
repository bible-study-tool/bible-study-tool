"""Tests for the STEPBible TBESH/TBESG gloss ingest (A4 extension)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from search.validation.build_stepbible_lexicon import parse_stepbible_txt

HEADER = (
    "TBESH - some title - STEPBible.org CC BY\n"
    "prose header line\n"
    "more prose\n"
)
DATA = (
    "H0001\tH0001G =\tH0001G\tאָב\tav\tH:N-M\tfather\t1) father of an individual\n"
    "H0001\tH0001H = a Part of\tH2438H\tאָב\tav\tH:N-M\t(Huram)-abi\tA man living at the time of...\n"
    "H0430\tH0430G =\tH0430G\tאֱלֹהִים\te.lo.him\tH:N-M\tGod\t1) God\n"
    "H0122a\tH0122A =\tH0122A\tאָדֹם\ta.dom\tH:A\tred\tred, ruddy (BDB sub-entry)\n"
    "G20001\tG20001 =\tG20001\tἀβάτοομαι\tabatoomai\t\tbe made desert\tvariant word\n"
    "H9999\tH9999X =\tH9999X\tx\tx\tH:X\tx\taffix row (out of range)\n"
    "H0001\tH0001G =\tH0001G\tאָב\tav\tH:N-M\tfather\t1) father of an individual\n"
)


class ParseTests(unittest.TestCase):
    def _parse(self, tmp, content, name="TBESH.txt"):
        p = Path(tmp) / name
        p.write_text(HEADER + content, encoding="utf-8")
        return parse_stepbible_txt(str(p))

    def test_parses_canonical_rows(self):
        with tempfile.TemporaryDirectory() as td:
            entries, _ = self._parse(td, DATA)
            # H0001, H0430 plain rows; H0122a is a BDB sub-entry of H122.
            # G20001 (variant) and H9999 (out of range) are skipped.
            self.assertEqual(set(entries), {"H1", "H430", "H122"})
            self.assertEqual(len(entries["H1"]), 2)
            self.assertEqual(entries["H1"][0]["gloss"], "father")
            self.assertEqual(entries["H1"][0]["translit"], "av")
            self.assertEqual(entries["H430"][0]["gloss"], "God")

    def test_subentry_keyed_to_base_with_verbatim_estrong(self):
        with tempfile.TemporaryDirectory() as td:
            entries, _ = self._parse(td, DATA)
            rec = entries["H122"][0]
            self.assertEqual(rec["estrong"], "H0122a")  # verbatim token kept
            self.assertEqual(rec["gloss"], "red")

    def test_out_of_range_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            _, stats = self._parse(td, DATA)
            # G20001 (variant) + H9999 (out of range) — NOT H0122a (kept).
            self.assertEqual(stats["skipped_extended"], 2)

    def test_duplicates_dropped_and_counted(self):
        with tempfile.TemporaryDirectory() as td:
            entries, stats = self._parse(td, DATA)
            # The exact duplicate H0001G row was dropped once.
            self.assertEqual(stats["dropped_duplicates"], 1)
            self.assertEqual(len(entries["H1"]), 2)

    def test_definition_keeps_later_tabs(self):
        with tempfile.TemporaryDirectory() as td:
            content = (
                "H0001\tH0001G =\tH0001G\tאָב\tav\tH:N-M\tfather\thas\tinner\ttabs\n"
            )
            entries, _ = self._parse(td, content)
            self.assertEqual(entries["H1"][0]["definition"], "has\tinner\ttabs")

    def test_malformed_row_raises(self):
        with tempfile.TemporaryDirectory() as td:
            content = "H0001\tbroken\trow\n"
            p = Path(td) / "TBESH.txt"
            p.write_text(HEADER + content, encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_stepbible_txt(str(p))


class ArtifactTests(unittest.TestCase):
    """The committed artifacts must be present, subset-of-canonical, and known-correct."""

    @classmethod
    def setUpClass(cls):
        cls.tbesh = json.load(open("lexicons/tbesh-glosses.json", encoding="utf-8"))
        cls.tbesg = json.load(open("lexicons/tbesg-glosses.json", encoding="utf-8"))
        cls.canonical = json.load(open("lexicons/strongs-list.json", encoding="utf-8"))

    def test_license_and_attribution(self):
        for art in (self.tbesh, self.tbesg):
            self.assertEqual(art["license"], "CC BY 4.0")
            self.assertIn("STEP Bible", art["attribution"])
        # The Online-Bible caveat must be recorded on the Hebrew artifact.
        self.assertIn("Online Bible", self.tbesh["license_note"])

    def test_keys_within_canonical(self):
        canon_h = set(self.canonical["hebrew"])
        canon_g = set(self.canonical["greek"])
        self.assertLessEqual(set(self.tbesh["entries"]), canon_h)
        self.assertLessEqual(set(self.tbesg["entries"]), canon_g)
        # TBESH covers every Hebrew canonical code (BDB sub-entries recover
        # full coverage); TBESG remains a genuine subset (some Greek numbers
        # lack Abbott-Smith lineage in the brief lexicon).
        self.assertEqual(len(self.tbesh["entries"]), len(canon_h))
        self.assertLess(len(self.tbesg["entries"]), len(canon_g))

    def test_known_entries(self):
        self.assertEqual(self.tbesh["entries"]["H1"][0]["gloss"], "father")
        self.assertEqual(self.tbesh["entries"]["H430"][0]["gloss"], "God")
        # H1254 has NO plain row — bara exists only as BDB sub-entries a/b.
        # Both must be present, keyed to the base number, in source order.
        h1254 = self.tbesh["entries"]["H1254"]
        self.assertEqual([r["estrong"] for r in h1254], ["H1254a", "H1254b"])
        self.assertEqual(h1254[0]["gloss"], "to create")
        self.assertEqual(h1254[1]["gloss"], "to fatten")
        self.assertEqual(self.tbesg["entries"]["G746"][0]["gloss"], "beginning")
        self.assertEqual(self.tbesg["entries"]["G2936"][0]["gloss"], "to create")
        self.assertEqual(self.tbesg["entries"]["G26"][0]["gloss"], "love")

    def test_counts_consistent(self):
        for art in (self.tbesh, self.tbesg):
            self.assertEqual(art["counts"]["codes"], len(art["entries"]))
            self.assertEqual(
                art["counts"]["records"],
                sum(len(v) for v in art["entries"].values()),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
