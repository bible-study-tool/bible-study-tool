"""Unit tests for Macula semantic enrichment engine (Pillar B, Goal B3, ADR-015)."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from search.macula.enrichment import (
    discover_translation_equivalence_candidates,
    enrich_curated_link,
    get_translation_equivalences,
    get_verse_semantic_frame,
)
import scripts.macula_lookup as macula_cli

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestTranslationEquivalences(unittest.TestCase):
    """Test Septuagint (LXX) translation-equivalence extraction."""

    def test_hebrew_strongs_equivalences(self):
        eqs = get_translation_equivalences("H1254", repo_root=REPO_ROOT)
        self.assertGreater(len(eqs), 0)
        # H1254 (bara) is translated by G4160 (poieo)
        poieo_match = next((eq for eq in eqs if eq["greek_strongs"] == "G4160"), None)
        self.assertIsNotNone(poieo_match)
        self.assertEqual(poieo_match["hebrew_strongs"], "H1254")
        self.assertIn("בָּרָא", poieo_match["hebrew_lemmas"])
        self.assertGreaterEqual(poieo_match["count"], 10)
        self.assertIn("028", poieo_match["core_domains"])

    def test_hebrew_reshit_equivalences(self):
        eqs = get_translation_equivalences("H7225", repo_root=REPO_ROOT)
        self.assertGreater(len(eqs), 0)
        arche_match = next((eq for eq in eqs if eq["greek_strongs"] == "G746"), None)
        self.assertIsNotNone(arche_match)
        self.assertEqual(arche_match["hebrew_strongs"], "H7225")
        self.assertIn("רֵאשִׁית", arche_match["hebrew_lemmas"])
        self.assertGreaterEqual(arche_match["count"], 1)

    def test_greek_strongs_reverse_lookup(self):
        eqs = get_translation_equivalences("G746", repo_root=REPO_ROOT)
        self.assertGreater(len(eqs), 0)
        h_match = next((eq for eq in eqs if eq["hebrew_strongs"] == "H7225"), None)
        self.assertIsNotNone(h_match)
        self.assertEqual(h_match["greek_strongs"], "G746")

    def test_unknown_strongs_returns_empty(self):
        self.assertEqual(get_translation_equivalences("H99999", repo_root=REPO_ROOT), [])
        self.assertEqual(get_translation_equivalences("G99999", repo_root=REPO_ROOT), [])


class TestVerseSemanticFrame(unittest.TestCase):
    """Test syntactic semantic frame extraction (Agent, Action, Patient, Context)."""

    def test_genesis_1_1_frame(self):
        frame = get_verse_semantic_frame("Gen.1.1", repo_root=REPO_ROOT)
        self.assertIsNotNone(frame)
        self.assertEqual(frame["verse_id"], "Gen.1.1")
        self.assertGreaterEqual(len(frame["clauses"]), 1)

        c1 = frame["clauses"][0]
        self.assertEqual(c1["rule"], "PP-V-S-O")

        # Agent should be God (elohim)
        agents = c1["agents"]
        self.assertEqual(len(agents), 1)
        self.assertIn("אֱלֹהִ֑ים", agents[0]["text"])

        # Action should be create (bara)
        actions = c1["actions"]
        self.assertEqual(len(actions), 1)
        self.assertIn("בָּרָ֣א", actions[0]["text"])

        # Patient should be heavens and earth
        patients = c1["patients"]
        self.assertEqual(len(patients), 1)
        self.assertIn("שָּׁמַ֖יִם", patients[0]["text"])

        # Context should be in the beginning (bereshit)
        context = c1["context"]
        self.assertIn("רֵאשִׁ֖ית", context[0]["text"])


        # Summary contains all components
        self.assertIn("Agent:", c1["summary"])
        self.assertIn("Action:", c1["summary"])
        self.assertIn("Patient:", c1["summary"])
        self.assertIn("Context:", c1["summary"])

    def test_genesis_1_3_frame(self):
        frame = get_verse_semantic_frame("Gen.1.3", repo_root=REPO_ROOT)
        self.assertIsNotNone(frame)
        self.assertGreaterEqual(len(frame["clauses"]), 1)
        c1 = frame["clauses"][0]
        self.assertTrue(any("אֱלֹהִ֖ים" in a["text"] for a in c1["agents"]))
        self.assertTrue(any("יֹּ֥אמֶר" in a["text"] for a in c1["actions"]))

    def test_unknown_verse_returns_none(self):
        self.assertIsNone(get_verse_semantic_frame("Gen.99.99", repo_root=REPO_ROOT))


class TestEnrichCuratedLink(unittest.TestCase):
    """Test non-destructive empirical enrichment of curated semantic links."""

    def test_enrich_sl_001_with_empirical_witness(self):
        raw_link = {
            "id": "sl-001",
            "type": "relation/equivalent",
            "entries": [
                {"strongs": "H7225", "language": "hebrew", "word": "רֵאשִׁית"},
                {"strongs": "G746", "language": "greek", "word": "ἀρχή"},
            ],
        }
        enriched = enrich_curated_link(raw_link, repo_root=REPO_ROOT)
        self.assertNotIn("empirical_evidence", raw_link, "Source curated link must not be mutated!")
        self.assertIn("empirical_evidence", enriched)
        ev = enriched["empirical_evidence"]
        self.assertEqual(ev["source"], "macula/lxx-alignment")
        self.assertGreaterEqual(ev["attestation_count"], 1)
        self.assertIn("168", ev["core_domains"])

    def test_enrich_link_without_lxx_alignment_remains_intact(self):
        link_without_lxx = {
            "id": "sl-mock",
            "type": "relation/semantic-field",
            "entries": [
                {"strongs": "H99999", "language": "hebrew"},
                {"strongs": "G99999", "language": "greek"},
            ],
        }
        enriched = enrich_curated_link(link_without_lxx, repo_root=REPO_ROOT)
        self.assertNotIn("empirical_evidence", enriched)
        self.assertEqual(enriched["id"], "sl-mock")


class TestDiscoverTranslationEquivalenceCandidates(unittest.TestCase):
    """Test automated discovery of cross-language translation equivalence candidates."""

    def test_discover_candidates_from_macula(self):
        # Examine creation verb H1254 (bara)
        cands = discover_translation_equivalence_candidates(
            strongs_filter=["H1254"],
            min_lxx_count=2,
            repo_root=REPO_ROOT,
        )
        self.assertGreater(len(cands), 0)
        c0 = cands[0]
        self.assertEqual(c0["type"], "relation/translation-equivalence")
        self.assertEqual(c0["source"], "macula/lxx-alignment")
        self.assertEqual(c0["review_status"], "pending")
        self.assertIsNone(c0["aligns_with_doctrine"])
        self.assertTrue(c0["review_required"])
        self.assertEqual(len(c0["entries"]), 2)
        self.assertEqual(c0["entries"][0]["strongs"], "H1254")
        self.assertEqual(c0["entries"][1]["strongs"], "G4160")
        self.assertGreaterEqual(c0["lxx_count"], 2)

    def test_deduplicates_against_curated_pairs(self):
        # sl-001 in semantic-links.json is (H7225, G746). It must not be proposed.
        cands = discover_translation_equivalence_candidates(
            strongs_filter=["H7225"],
            min_lxx_count=1,
            repo_root=REPO_ROOT,
        )
        for c in cands:
            pair = {c["entries"][0]["strongs"], c["entries"][1]["strongs"]}
            self.assertNotEqual(pair, {"H7225", "G746"})


class TestEnrichmentCLI(unittest.TestCase):
    """Test CLI commands for semantic frames and translation equivalences."""

    def test_cli_verse_frame(self):
        rc = macula_cli.main(["--verse", "Gen.1.1", "--frame"])
        self.assertEqual(rc, 0)

    def test_cli_verse_frame_json(self):
        rc = macula_cli.main(["--verse", "Gen.1.1", "--frame", "--json"])
        self.assertEqual(rc, 0)

    def test_cli_strongs_equiv(self):
        rc = macula_cli.main(["--strongs", "H1254", "--equiv"])
        self.assertEqual(rc, 0)

    def test_cli_strongs_equiv_json(self):
        rc = macula_cli.main(["--strongs", "H1254", "--equiv", "--json"])
        self.assertEqual(rc, 0)

    def test_cli_lxx_equiv(self):
        rc = macula_cli.main(["--lxx", "G4160", "--equiv"])
        self.assertEqual(rc, 0)

    def test_cli_frame_without_verse_fails(self):
        rc = macula_cli.main(["--frame"])
        self.assertEqual(rc, 1)

    def test_cli_equiv_without_strongs_or_lxx_fails(self):
        rc = macula_cli.main(["--equiv"])
        self.assertEqual(rc, 1)

    def test_cli_equiv_not_found(self):
        rc = macula_cli.main(["--strongs", "H99999", "--equiv"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
