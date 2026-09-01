"""Tests for the word-level apparatus (S4)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from search.agreement.apparatus import build_apparatus, write_apparatus

APPARATUS_PATH = Path("correlations/apparatus-genesis1.json")

# The pinned function-word omission set (all 94 omissions are these codes).
FUNCTION_WORDS = {
    "H1961", "H853", "H3605", "H5921", "H996",
    "H3651", "H3588", "H834", "H2009", "H8478",
}


class ApparatusArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = json.loads(APPARATUS_PATH.read_text(encoding="utf-8"))
        cls.by_key = {v["key"]: v for v in cls.app["verses"]}

    def test_summary_pins(self):
        """The 94/0 finding, pinned exactly (independently re-verified twice:
        auditor + local recomputation)."""
        s = self.app["summary"]
        self.assertEqual(s["verses"], 31)
        self.assertEqual(s["matched_tokens"], 333)
        self.assertEqual(s["omissions"], 94)
        self.assertEqual(s["additions"], 0)
        self.assertEqual(
            s["omissions_by_code"],
            {
                "H1961": 24, "H853": 23, "H3605": 14, "H5921": 9, "H996": 7,
                "H3588": 5, "H3651": 5, "H834": 5, "H2009": 1, "H8478": 1,
            },
        )

    def test_token_reconciliation_per_verse(self):
        """matched + omissions == oshb tokens; matched + additions == kjv
        tokens — for every verse (no token can vanish in the alignment)."""
        for v in self.app["verses"]:
            c = v["counts"]
            self.assertEqual(c["matched"] + c["omissions"], c["oshb_tokens"], v["key"])
            self.assertEqual(c["matched"] + c["additions"], c["kjv_osis_tokens"], v["key"])

    def test_all_omissions_are_function_words(self):
        for v in self.app["verses"]:
            for o in v["omissions"]:
                self.assertIn(o["code"], FUNCTION_WORDS, (v["key"], o))

    def test_v1_full_agreement(self):
        v = self.by_key["Gen.1.1"]
        self.assertEqual(v["counts"]["omissions"], 0)
        self.assertEqual(v["counts"]["additions"], 0)
        self.assertEqual(v["counts"]["matched"], 7)
        # A concrete correspondence pair from the pinned data. NOTE: the
        # artifact stores the WLC text source-verbatim in DECOMPOSED (NFD)
        # form (OSHB warns against NFC normalization) — pins use explicit
        # codepoints, editor-proof.
        pair = next(p for p in v["matched"] if p["code"] == "H1254")
        self.assertEqual(pair["kjv-osis"]["span_text"], "created")
        # Pinned as explicit codepoints in OSHB's documented glyph order:
        # consonant; dagesh; vowel; accents (bet+dagesh+qamats, resh+qamats+
        # ole, alef) — NFD verbatim.
        self.assertEqual(
            pair["oshb"]["wlc"],
            "\u05d1\u05bc\u05b8\u05e8\u05b8\u05a3\u05d0",  # bara'
        )
        self.assertEqual(pair["oshb"]["morph"], "HVqp3ms")

    def test_v3_h1961_omission_is_vayehi(self):
        """Gen.1.3: kjv-osis tags one H1961 ('Let there be' = yehi); the
        omission is the SECOND occurrence, va/yehi ('and there was'). The
        greedy first-with-first pairing lands on the semantically right one."""
        v = self.by_key["Gen.1.3"]
        self.assertEqual(len(v["omissions"]), 1)
        o = v["omissions"][0]
        self.assertEqual(o["code"], "H1961")
        # va/yehi — includes the solidus separator (0x2f) from the lemma
        # prefix notation; pinned as explicit codepoints.
        self.assertEqual(
            o["oshb"]["wlc"],
            "\u05d5\u05b7\u05bd\u002f\u05d9\u05b0\u05d4\u05b4\u05d9",
        )
        self.assertEqual(o["oshb"]["word_i"], 5)
        matched_h1961 = next(p for p in v["matched"] if p["code"] == "H1961")
        self.assertEqual(matched_h1961["kjv-osis"]["span_text"], "Let there be")
        # yehi (with ole cantillation).
        self.assertEqual(
            matched_h1961["oshb"]["wlc"],
            "\u05d9\u05b0\u05d4\u05b4\u05a3\u05d9",
        )

    def test_v16_four_object_marker_omissions(self):
        v = self.by_key["Gen.1.16"]
        om = [o for o in v["omissions"] if o["code"] == "H853"]
        self.assertEqual(len(om), 4)
        for o in om:
            # vav-prefixed forms carry the conjunction morph HC/To; the rest
            # are the plain article-object-marker HTo. (Vav+sheva pinned as
            # codepoints: no NFC composite exists, but keep the discipline.)
            vav = "\u05d5\u05b0"
            expected = "HC/To" if o["oshb"]["wlc"].startswith(vav) else "HTo"
            self.assertEqual(o["oshb"]["morph"], expected)

    def test_no_omissions_in_agree_verses(self):
        """The two multiset-agree verses must have zero omissions."""
        for key in ("Gen.1.1", "Gen.1.4"):
            self.assertEqual(self.by_key[key]["counts"]["omissions"], 0)

    def test_regeneration_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            write_apparatus(".", out_path=Path(td) / "app.json")
            committed = APPARATUS_PATH.read_text(encoding="utf-8")
            fresh = (Path(td) / "app.json").read_text(encoding="utf-8")
            self.assertEqual(
                fresh, committed,
                "Apparatus drifted from its generator. This file is GENERATED — "
                "do not hand-edit. Regenerate: python -c \"from "
                "search.agreement.apparatus import write_apparatus; "
                "write_apparatus('.')\" (then update data/PROVENANCE.md).",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)