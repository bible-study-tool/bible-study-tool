"""Tests for the OSHB Hebrew morphology layer (Genesis 1)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from search.corpus.build_morphology import decompose_lemma, parse_book_xml
from search.testutil import require_raw_sources

FIXTURE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">
  <osisText xml:lang="he" osisIDWork="OSHB" osisRefWork="Bible">
    <div type="book" osisID="Gen">
      <chapter osisID="Gen.1">
        <verse osisID="Gen.1.1">
          <w lemma="b/7225" n="1.0" morph="HR/Ncfsa" id="01aaa1">בְּ/רֵאשִׁית</w>
          <w lemma="1254 a" morph="HVqp3ms" id="01aaa2">בָּרָא</w>
          <w lemma="430" morph="HNcmpa" id="01aaa3">אֱלֹהִים</w>
          <w lemma="c/853" morph="HC/To" id="01aaa4">וְ/אֵת</w>
          <w lemma="b" morph="HR" id="01aaa5">בְּ</w>
          <w lemma="c/l/3117" morph="HC/Sp/Ncmsa" id="01aaa6">וְ/לְ/יוֹם</w>
        </verse>
      </chapter>
    </div>
  </osisText>
</osis>
"""


class DecomposeTests(unittest.TestCase):
    def test_all_observed_forms(self):
        cases = {
            "7225": {"prefixes": [], "base": "H7225", "suffix": None},
            "b/7225": {"prefixes": ["b"], "base": "H7225", "suffix": None},
            "c/l/3117": {"prefixes": ["c", "l"], "base": "H3117", "suffix": None},
            "1254 a": {"prefixes": [], "base": "H1254", "suffix": "a"},
            "c/l/4723 c": {"prefixes": ["c", "l"], "base": "H4723", "suffix": "c"},
            "b": {"prefixes": ["b"], "base": None, "suffix": None},
        }
        for lemma, expected in cases.items():
            d = decompose_lemma(lemma)
            self.assertEqual(d["lemma"], lemma)  # verbatim always kept
            self.assertEqual(d["prefixes"], expected["prefixes"], lemma)
            self.assertEqual(d["base"], expected["base"], lemma)
            self.assertEqual(d["suffix"], expected["suffix"], lemma)

    def test_unrecognized_form_raises(self):
        with self.assertRaises(ValueError):
            decompose_lemma("123/x45")


class ParseBookTests(unittest.TestCase):
    def _fixture(self, td):
        p = Path(td) / "Gen.xml"
        p.write_text(FIXTURE_XML, encoding="utf-8")
        return str(p)

    def test_parse_order_and_fields(self):
        with tempfile.TemporaryDirectory() as td:
            records = parse_book_xml(self._fixture(td), 1)
            self.assertEqual(len(records), 6)
            # Order preserved; first word spot-checked.
            self.assertEqual(records[0]["id"], "01aaa1")
            self.assertEqual(records[0]["base"], "H7225")
            self.assertEqual(records[0]["prefixes"], ["b"])
            self.assertEqual(records[0]["morph"], "HR/Ncfsa")
            self.assertEqual(records[0]["n"], "1.0")
            self.assertEqual(records[0]["osisID"], "Gen.1.1")

    def test_suffix_split(self):
        with tempfile.TemporaryDirectory() as td:
            records = parse_book_xml(self._fixture(td), 1)
            self.assertEqual(records[1]["lemma"], "1254 a")
            self.assertEqual(records[1]["base"], "H1254")
            self.assertEqual(records[1]["suffix"], "a")

    def test_prefix_only_word_has_no_base(self):
        with tempfile.TemporaryDirectory() as td:
            records = parse_book_xml(self._fixture(td), 1)
            self.assertEqual(records[4]["lemma"], "b")
            self.assertIsNone(records[4]["base"])
            self.assertEqual(records[4]["prefixes"], ["b"])

    def test_malformed_morph_raises(self):
        bad = FIXTURE_XML.replace('morph="HR/Ncfsa"', 'morph="X"')
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "Gen.xml"
            p.write_text(bad, encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_book_xml(str(p), 1)


class ArtifactTests(unittest.TestCase):
    """The committed morphology artifact must match the pinned sources."""

    @classmethod
    def setUpClass(cls):
        with open("lexicons/morphology-genesis1.json", encoding="utf-8") as fh:
            cls.art = json.load(fh)
        with open("lexicons/strongs-list.json", encoding="utf-8") as fh:
            cls.canonical = json.load(fh)
        cls.canon_h = set(cls.canonical["hebrew"])

    def test_license_and_attribution(self):
        self.assertIn("public domain", self.art["license"])
        self.assertIn("CC BY 4.0", self.art["license"])
        self.assertIn("Open Scriptures", self.art["attribution"])

    def test_counts(self):
        self.assertEqual(self.art["counts"]["verses"], 31)
        self.assertEqual(self.art["counts"]["words"], sum(
            len(w) for w in self.art["verses"].values()
        ))

    def test_every_base_in_canonical(self):
        for words in self.art["verses"].values():
            for r in words:
                if r["base"]:
                    self.assertIn(r["base"], self.canon_h, r)

    def test_ids_unique(self):
        ids = [r["id"] for words in self.art["verses"].values() for r in words]
        self.assertEqual(len(ids), len(set(ids)))

    def test_morph_code_shape(self):
        import re
        for words in self.art["verses"].values():
            for r in words:
                self.assertRegex(r["morph"], r"^H[A-Za-z0-9/]+$", r["id"])

    def test_known_words(self):
        """Genesis 1:1 word-level facts, pinned from the source."""
        v1 = self.art["verses"]["1"]
        self.assertEqual(len(v1), 7)
        self.assertEqual(v1[0]["lemma"], "b/7225")
        self.assertEqual(v1[0]["base"], "H7225")
        self.assertEqual(v1[0]["prefixes"], ["b"])
        self.assertEqual(v1[0]["morph"], "HR/Ncfsa")
        self.assertEqual(v1[1]["base"], "H1254")
        self.assertEqual(v1[1]["suffix"], "a")
        self.assertEqual(v1[2]["base"], "H430")
        self.assertEqual([w["base"] for w in v1],
                         ["H7225", "H1254", "H430", "H853", "H8064", "H853", "H776"])

    @require_raw_sources()
    def test_word_counts_match_source(self):
        """Word count per verse must equal the <w> element count in the XML."""
        import xml.etree.ElementTree as ET
        root = ET.parse("data/oshb/Gen.xml").getroot()
        ns = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"
        for verse in root.iter(ns + "verse"):
            osis_id = verse.get("osisID", "")
            if not osis_id.startswith("Gen.1."):
                continue
            vnum = osis_id.split(".")[-1]
            src_count = sum(1 for _ in verse.iter(ns + "w"))
            self.assertEqual(
                len(self.art["verses"][vnum]), src_count,
                f"Gen.1.{vnum}: artifact word count != source",
            )

    @require_raw_sources()
    def test_regeneration_byte_identical(self):
        """Drift tripwire: committed artifact must equal a fresh build — at
        the BYTE level (not just structurally), so formatting drift also
        fails and the PROVENANCE checksum stays authoritative."""
        from search.corpus.build_morphology import build
        with tempfile.TemporaryDirectory() as td:
            build(".", out_dir=td)
            committed = Path("lexicons/morphology-genesis1.json").read_text(
                encoding="utf-8"
            )
            fresh = (Path(td) / "morphology-genesis1.json").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                fresh, committed,
                "Morphology artifact drifted from its generator. This file is "
                "GENERATED — do not hand-edit. Regenerate with: python -m "
                "search.corpus.build_morphology --repo . (then update the "
                "data/PROVENANCE.md checksum).",
            )


class Genesis2ArtifactTests(unittest.TestCase):
    """The committed Genesis-2 morphology artifact must match the pinned
    sources (WP-007, ADR-0009 book-level expansion)."""

    @classmethod
    def setUpClass(cls):
        with open("lexicons/morphology-genesis2.json", encoding="utf-8") as fh:
            cls.art = json.load(fh)
        with open("lexicons/strongs-list.json", encoding="utf-8") as fh:
            cls.canonical = json.load(fh)
        cls.canon_h = set(cls.canonical["hebrew"])

    def test_counts(self):
        self.assertEqual(self.art["counts"]["verses"], 25)
        self.assertEqual(self.art["counts"]["words"], sum(
            len(w) for w in self.art["verses"].values()
        ))

    def test_schema(self):
        self.assertEqual(self.art["$schema"], "morphology-genesis2/v1")

    def test_known_words(self):
        """Genesis 2:1 word-level facts: 'finished' (kalah H3615) and the
        host (tsaba H6635), pinned from the source."""
        v1 = self.art["verses"]["1"]
        self.assertEqual(len(v1), 5)
        self.assertEqual([w["base"] for w in v1],
                         ["H3615", "H8064", "H776", "H3605", "H6635"])

    def test_unpadded_lemma_normalization(self):
        """OSHB lemmas are canonically unpadded in Genesis 2 (H1 father at
        2:24, H68 stone at 2:12) — they must already be canonical here (the
        OSHB side needs no normalization; this pins the KJV-side quirk
        handling end-to-end via the apparatus/ledger tests)."""
        v24 = {r["id"]: r for r in self.art["verses"]["24"]}
        self.assertIn("H1", [r["base"] for r in self.art["verses"]["24"]])
        self.assertIn("H68", [r["base"] for r in self.art["verses"]["12"]])

    def test_every_base_in_canonical(self):
        for words in self.art["verses"].values():
            for r in words:
                if r["base"]:
                    self.assertIn(r["base"], self.canon_h, r)

    def test_ids_unique(self):
        ids = [r["id"] for words in self.art["verses"].values() for r in words]
        self.assertEqual(len(ids), len(set(ids)))

    @require_raw_sources()
    def test_regeneration_byte_identical(self):
        from search.corpus.build_morphology import build
        with tempfile.TemporaryDirectory() as td:
            build(".", out_dir=td, chapters=(2,))
            committed = Path("lexicons/morphology-genesis2.json").read_text(
                encoding="utf-8"
            )
            fresh = (Path(td) / "morphology-genesis2.json").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                fresh, committed,
                "Genesis-2 morphology artifact drifted from its generator. "
                "Regenerate: python -m search.corpus.build_morphology --repo . "
                "--chapters 2 (then update the data/PROVENANCE.md checksum).",
            )


class ProvenanceChecksumGateTests(unittest.TestCase):
    """Offline drift gate: every committed generated artifact's SHA-256 must
    match the checksum recorded in data/PROVENANCE.md. CI cannot run
    fetch_sources.sh (data/ is gitignored), so this test IS the artifact
    integrity gate in the pipeline. Covers lexicons/*.json and any
    correlations/ artifact recorded with a '../' path."""

    def test_all_committed_artifacts_match_provenance(self):
        import hashlib
        import re
        prov = Path("data/PROVENANCE.md").read_text(encoding="utf-8")
        recorded = {
            name: sha
            for sha, name in re.findall(
                r"^([0-9a-f]{64})  \.\./([A-Za-z0-9._/-]+)$",
                prov,
                re.MULTILINE,
            )
        }
        # Exact inventory pin: removing any artifact from PROVENANCE must
        # fail here, not slide under a floor.
        self.assertEqual(
            set(recorded),
            {
                "lexicons/strongs-list.json",
                "lexicons/strongs-lexicon.json",
                "lexicons/tbesh-glosses.json",
                "lexicons/tbesg-glosses.json",
                "lexicons/morphology-genesis1.json",
                "lexicons/morphology-genesis2.json",
                "lexicons/morphology-genesis3.json",
                "lexicons/wordgraph-genesis.json",
                "correlations/agreement-ledger.json",
                "correlations/apparatus-genesis1.json",
                "correlations/apparatus-genesis2.json",
                "correlations/apparatus-genesis3.json",
            },
        )
        for name, sha in recorded.items():
            path = Path(name)
            self.assertTrue(path.exists(), f"{name} recorded but missing")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(
                actual, sha,
                f"{name}: committed file does not match PROVENANCE checksum "
                "(hand-edit or stale regeneration)",
            )
        # Generated artifacts must ALL be recorded: every lexicons/*.json,
        # plus any correlations/*.json outside the hand-curated/review set
        # (a future generated artifact committed without a PROVENANCE entry
        # fails loudly here).
        hand_curated = {
            "correlations/semantic-links.json",
            "correlations/semantic-links-index.json",
            # Review queue: regenerated with merge-preservation + human edits;
            # deliberately NOT byte-checksummed.
            "correlations/ai-discovered-links.json",
            # WordGraph homograph notes: HAND content (reviewed input consumed
            # by the generator) — deliberately NOT byte-checksummed.
            "lexicons/wordgraph-notes-genesis.json",
        }
        generated = {p.as_posix() for p in Path("lexicons").glob("*.json")
                     if p.as_posix() not in hand_curated}
        generated |= {
            p.as_posix() for p in Path("correlations").glob("*.json")
            if p.as_posix() not in hand_curated
        }
        self.assertEqual(
            generated, set(recorded),
            "generated-artifact inventory diverged from PROVENANCE.md",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)