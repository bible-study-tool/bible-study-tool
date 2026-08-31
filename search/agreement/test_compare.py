"""Tests for the comparison engine + Agreement Ledger (S2)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from search.agreement.compare import (
    ALLOWED_STATUSES,
    build_ledger,
    normalize_gloss,
    write_ledger,
)
from search.agreement.facts import (
    collect_all,
    index_facts,
    FACT_LEXICON_GLOSS,
    FACT_WORD_STRONGS,
)

LEDGER_PATH = Path("correlations/agreement-ledger.json")


class NormalizeGlossTests(unittest.TestCase):
    def test_golden_samples(self):
        """Pinned from the review: these pairs must normalize to agreement."""
        self.assertEqual(normalize_gloss("1. (absolutely) to create"), "to create")
        self.assertEqual(normalize_gloss("to create"), "to create")
        # H7225: strongs first segment vs tbesh first segment.
        self.assertEqual(normalize_gloss("1. the first, in place, time, order or rank"),
                         "the first, in place, time, order or rank")
        self.assertEqual(normalize_gloss("first: beginning"), "first")

    def test_edge_cases(self):
        # '-Elohe' sits OUTSIDE the parenthetical, so it survives segment-split.
        self.assertEqual(normalize_gloss("God (LORD)-Elohe; also: x"), "god -elohe")
        self.assertEqual(normalize_gloss("  12.   A   B  "), "a b")
        self.assertEqual(normalize_gloss(""), "")


class EngineTests(unittest.TestCase):
    """Unit tests over synthetic indexes — every status path."""

    @staticmethod
    def _fact(source, value, meta=None):
        return {"fact_type": "", "source": source, "key": "k", "value": value,
                "meta": meta or {}}

    def test_word_strongs_agree_and_disagree(self):
        a = self._fact("kjv-osis", ["H1", "H2"])
        b = self._fact("oshb", ["H1", "H2"])
        c = self._fact("oshb", ["H1", "H2", "H853"])
        from search.agreement.compare import _compare_word_strongs
        self.assertEqual(_compare_word_strongs("k", {"a": a, "b": b})["status"], "agree")
        self.assertEqual(_compare_word_strongs("k", {"a": a, "c": c})["status"], "disagree")

    def test_gloss_never_disagree(self):
        """Policy (a): unequal glosses are 'info', never 'disagree'."""
        from search.agreement.compare import _compare_gloss
        a = self._fact("strongs", "1. (absolutely) to create",
                       {"gloss_status": "definition"})
        b = self._fact("tbesh", "to fatten", {"gloss_status": "definition"})
        row = _compare_gloss("H1254", {"strongs": a, "tbesh": b})
        self.assertEqual(row["status"], "info")
        self.assertIn(row["status"], ALLOWED_STATUSES[FACT_LEXICON_GLOSS])

    def test_gloss_no_definition_paths(self):
        from search.agreement.compare import _compare_gloss
        # strongs no_definition + tbesh real reading -> one-sided (H5774 case).
        a = self._fact("strongs", "Strong's Number H5774: עוף",
                       {"gloss_status": "no_definition"})
        b = self._fact("tbesh", "to fly", {"gloss_status": "definition"})
        self.assertEqual(_compare_gloss("H5774", {"strongs": a, "tbesh": b})["status"],
                         "one-sided")
        # Only a no_definition reading -> no_reading (G2717 case).
        self.assertEqual(_compare_gloss("G2717", {"strongs": a})["status"], "no_reading")

    def test_gloss_agree(self):
        from search.agreement.compare import _compare_gloss
        a = self._fact("strongs", "1. (absolutely) to create",
                       {"gloss_status": "definition"})
        b = self._fact("tbesh", "to create", {"gloss_status": "definition"})
        self.assertEqual(_compare_gloss("H1254", {"strongs": a, "tbesh": b})["status"],
                         "agree")


class LedgerArtifactTests(unittest.TestCase):
    """The committed ledger must match the facts and the policy."""

    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        cls.facts = collect_all(".")

    def test_schema_and_policy(self):
        self.assertEqual(self.ledger["$schema"], "agreement-ledger/v1")
        self.assertNotIn("disagree", self.ledger["policy"]["lexicon_gloss_statuses"])
        self.assertIn(FACT_WORD_STRONGS, self.ledger["policy"]["disagree_reserved_for"])

    def test_summary_counts_match_rows(self):
        for fact_type, rows in self.ledger["comparisons"].items():
            counts = {}
            for row in rows:
                counts[row["status"]] = counts.get(row["status"], 0) + 1
                self.assertIn(row["status"], ALLOWED_STATUSES[fact_type], row["key"])
            self.assertEqual(self.ledger["summary"][fact_type], counts)

    def test_no_disagree_in_gloss_section(self):
        for row in self.ledger["comparisons"][FACT_LEXICON_GLOSS]:
            self.assertNotEqual(row["status"], "disagree", row["key"])

    def test_known_word_strongs_rows(self):
        """v1 and v4 agree; Gen.1.3 is a real pinned disagreement: OSHB tags
        H1961 twice (yehi + vayehi), scrollmapper only once."""
        by_key = {r["key"]: r for r in self.ledger["comparisons"][FACT_WORD_STRONGS]}
        self.assertEqual(by_key["Gen.1.1"]["status"], "agree")
        self.assertEqual(by_key["Gen.1.4"]["status"], "agree")
        d = by_key["Gen.1.3"]
        self.assertEqual(d["status"], "disagree")
        readings = {r["source"]: r["value"] for r in d["readings"]}
        self.assertEqual(readings["kjv-osis"].count("H1961"), 1)
        self.assertEqual(readings["oshb"].count("H1961"), 2)

    def test_function_word_finding_is_systematic(self):
        """The dominant disagreement pattern: scrollmapper omits H853/H3605
        that OSHB fully tags. Pinned: v16 H853 4x vs 0x; v26 H3605 2x vs 0x."""
        by_key = {r["key"]: r for r in self.ledger["comparisons"][FACT_WORD_STRONGS]}
        v16 = {r["source"]: r["value"] for r in by_key["Gen.1.16"]["readings"]}
        self.assertEqual(v16["oshb"].count("H853"), 4)
        self.assertEqual(v16["kjv-osis"].count("H853"), 0)
        v26 = {r["source"]: r["value"] for r in by_key["Gen.1.26"]["readings"]}
        self.assertEqual(v26["oshb"].count("H3605"), 2)
        self.assertEqual(v26["kjv-osis"].count("H3605"), 0)

    def test_gloss_rows_match_fact_values_verbatim(self):
        by_key = {r["key"]: r for r in self.ledger["comparisons"][FACT_LEXICON_GLOSS]}
        fact_index = index_facts(self.facts)[FACT_LEXICON_GLOSS]
        for code in ("H1254", "H7225", "G746", "H2492", "G2717"):
            row = by_key[code]
            for reading in row["readings"]:
                self.assertEqual(
                    reading["value"], fact_index[code][reading["source"]]["value"],
                    f"{code}/{reading['source']}",
                )

    def test_known_gloss_rows(self):
        by_key = {r["key"]: r for r in self.ledger["comparisons"][FACT_LEXICON_GLOSS]}
        # H1254: strongs '1. (absolutely) to create' + tbesh 'to create' -> agree.
        self.assertEqual(by_key["H1254"]["status"], "agree")
        # H5774 (no_definition) + tbesh 'to fly' -> one-sided.
        h5774 = by_key["H5774"]
        self.assertEqual(h5774["status"], "one-sided")
        statuses = {r["source"]: r["gloss_status"] for r in h5774["readings"]}
        self.assertEqual(statuses["strongs"], "no_definition")
        # G2717: strongs no_definition only -> no_reading.
        self.assertEqual(by_key["G2717"]["status"], "no_reading")

    def test_sort_key_numeric_order(self):
        """Gen.1.2 must sort before Gen.1.10; H2 before H10 (protects the
        committed artifact's row order against refactors)."""
        from search.agreement.compare import _sort_key
        self.assertLess(_sort_key("Gen.1.2"), _sort_key("Gen.1.10"))
        self.assertLess(_sort_key("H2"), _sort_key("H10"))
        self.assertLess(_sort_key("Gen.1.1"), _sort_key("H1"))

    def test_known_info_row_normalized_values(self):
        """Pins the normalization behavior into an artifact row: H7676
        (Sabbath) — strongs multi-sense phrase vs tbesh single gloss."""
        by_key = {r["key"]: r for r in self.ledger["comparisons"][FACT_LEXICON_GLOSS]}
        row = by_key["H7676"]
        self.assertEqual(row["status"], "info")
        norm = {r["source"]: r.get("normalized") for r in row["readings"]}
        self.assertIsNotNone(norm["strongs"])
        self.assertEqual(norm["tbesh"], "sabbath")
        self.assertNotEqual(norm["strongs"], norm["tbesh"])

    def test_regeneration_byte_identical(self):
        """Byte-level drift tripwire (not just structural): the committed
        ledger must equal a fresh build byte for byte."""
        with tempfile.TemporaryDirectory() as td:
            write_ledger(".", out_path=Path(td) / "ledger.json")
            committed = LEDGER_PATH.read_text(encoding="utf-8")
            fresh = (Path(td) / "ledger.json").read_text(encoding="utf-8")
            self.assertEqual(fresh, committed)


if __name__ == "__main__":
    unittest.main(verbosity=2)