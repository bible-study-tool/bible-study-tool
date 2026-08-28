"""Tests for the STEPBible TBESH/TBESG gloss ingest (A4 extension)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from search.validation.build_stepbible_lexicon import parse_stepbible_txt, build

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

    def test_build_fail_fast_on_empty_source(self):
        """A truncated/empty/HTML-error-page source must raise, never emit an
        empty artifact (the generator must not fail open)."""
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "TBESH.txt"
            src.write_text("404: Not Found\n", encoding="utf-8")
            canon = Path(td) / "canon.json"
            canon.write_text(json.dumps({"hebrew": ["H1"], "greek": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                build(str(src), str(src), str(canon), str(td))

    def test_build_keeps_subentries_and_records_changes(self):
        """End-to-end build() on fixtures: lettered sub-entries keyed to the
        base number, counters recorded, license_note present. Guards the
        payload-assembly path (parser tests alone cannot catch a writer
        regression that drops sub-entries)."""
        with tempfile.TemporaryDirectory() as td:
            tbesh = Path(td) / "TBESH.txt"
            tbesh.write_text(
                HEADER + (
                    "H1254a\tH1254A =\tH1254A\tבָּרָא\tba.ra\tH:V\tto create\t1) create\n"
                    "H1254b\tH1254B =\tH1254B\tבָּרָא\tba.ra\tH:V\tto fatten\t1) fatten\n"
                ),
                encoding="utf-8",
            )
            tbesg = Path(td) / "TBESG.txt"
            tbesg.write_text(
                HEADER + (
                    "G0026\tG0026 =\tG0026\tἀγάπη\tagapē\tN:N-F\tlove\t1) love\n"
                ),
                encoding="utf-8",
            )
            canon = Path(td) / "canon.json"
            canon.write_text(
                json.dumps({"hebrew": ["H1254"], "greek": ["G26"]}), encoding="utf-8"
            )
            build(str(tbesh), str(tbesg), str(canon), str(td))
            art = json.loads((Path(td) / "tbesh-glosses.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [r["estrong"] for r in art["entries"]["H1254"]],
                ["H1254a", "H1254b"],
            )
            self.assertEqual(art["counts"]["codes"], 1)
            self.assertIn("Online Bible", art["license_note"])
            self.assertTrue(art["changes_recorded"])


class ArtifactTests(unittest.TestCase):
    """The committed artifacts must be present, subset-of-canonical, and known-correct."""

    @classmethod
    def setUpClass(cls):
        cls.tbesh = cls._load("lexicons/tbesh-glosses.json")
        cls.tbesg = cls._load("lexicons/tbesg-glosses.json")
        cls.canonical = cls._load("lexicons/strongs-list.json")

    @staticmethod
    def _load(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

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
        # Current upstream state pinned in test_counts_below: TBESH currently
        # achieves FULL Hebrew coverage (<= keeps the test honest if a future
        # re-pin improves Greek coverage too).
        self.assertEqual(len(self.tbesh["entries"]), len(canon_h))
        self.assertLessEqual(len(self.tbesg["entries"]), len(canon_g))

    def test_counts_below(self):
        """Pin today's upstream coverage so any re-pin that changes it is
        reviewed rather than silently accepted (or silently lost)."""
        self.assertEqual(self.tbesh["counts"]["codes"], 8674)
        self.assertEqual(self.tbesh["counts"]["records"], 11633)
        self.assertEqual(self.tbesg["counts"]["codes"], 5523)

    def test_known_entries(self):
        """Pins exact upstream gloss wording INTENTIONALLY: a future re-pin
        that changes wording should fail here and force a reviewed diff, not
        silently update the deterministic core's supplementary layer."""
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
