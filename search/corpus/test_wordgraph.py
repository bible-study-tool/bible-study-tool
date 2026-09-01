"""Tests for the WordGraph lexical knowledge graph (WP-009, ADR-0010).

The WordGraph is a DERIVED artifact consuming only committed artifacts (no
raw data/ sources) — so these tests run in CI (fresh clone) as well.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from search.corpus.build_wordgraph import build, write

GRAPH_PATH = Path("lexicons/wordgraph-genesis.json")


class WordGraphArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
        cls.by_id = {l["id"]: l for l in cls.graph["lexemes"]}

    def test_schema_and_scope(self):
        self.assertEqual(self.graph["$schema"], "wordgraph-genesis/v1")
        self.assertEqual(self.graph["scope"]["book"], "genesis")
        self.assertEqual(self.graph["scope"]["chapters"], [1, 2])
        # Derived from the artifacts (not hardcoded): 31 Gen-1 + 25 Gen-2
        # distinct osisIDs.
        self.assertEqual(self.graph["scope"]["verses"], 56)

    def test_verses_count_derived_from_occurrences(self):
        """The scope verses count must equal the distinct occurrence passages
        (no hardcoded drift)."""
        passages = {
            occ["passage"]
            for l in self.graph["lexemes"]
            for occ in l["occurrences"]
        }
        self.assertEqual(len(passages), self.graph["scope"]["verses"])

    def test_lexeme_count(self):
        self.assertEqual(len(self.graph["lexemes"]), 183)

    def test_every_lexeme_has_required_fields(self):
        for l in self.graph["lexemes"]:
            self.assertIn("id", l)
            self.assertIn("strongs", l)
            self.assertIn("oshb_homonyms", l)
            self.assertIn("glosses", l)
            self.assertIn("morphology", l)
            self.assertIn("attestation", l)
            self.assertIn("occurrences", l)
            self.assertIn("homograph", l)
            self.assertIn("status", l["homograph"])
            # Agreed design: all homographs seeded 'unresolved' (option A).
            self.assertEqual(l["homograph"]["status"], "unresolved")

    def test_glosses_reference_ledger(self):
        """Ledger status must be a real status from the agreement ledger
        (agree/info/one-sided/no_reading) — or None when the row is absent."""
        ledger = json.loads(
            Path("correlations/agreement-ledger.json").read_text(encoding="utf-8")
        )
        gloss_rows = {r["key"]: r for r in ledger["comparisons"]["lexicon_gloss"]}
        for l in self.graph["lexemes"]:
            status = l["glosses"]["ledger_status"]
            row = gloss_rows.get(l["id"])
            if row is None:
                self.assertIsNone(status, l["id"])
            else:
                self.assertEqual(status, row["status"], l["id"])

    def test_known_lexemes(self):
        """Pinned representative records."""
        h1254 = self.by_id["H1254"]
        self.assertEqual(h1254["glosses"]["strongs"], "1. (absolutely) to create")
        self.assertEqual(h1254["glosses"]["tbesh"], ["to create", "to fatten"])
        self.assertEqual(h1254["glosses"]["ledger_status"], "agree")
        self.assertEqual(h1254["attestation"]["verses"], 5)
        self.assertEqual(h1254["attestation"]["tokens"], 7)
        self.assertEqual(
            [o["passage"] for o in h1254["occurrences"]],
            ["Gen.1.1", "Gen.1.21", "Gen.1.27", "Gen.2.3", "Gen.2.4"],
        )

        h7673 = self.by_id["H7673"]
        self.assertEqual(h7673["glosses"]["ledger_status"], "info")
        self.assertEqual(
            h7673["homograph"]["candidate_senses"], ["to cease", "to keep"]
        )
        self.assertEqual(
            [o["passage"] for o in h7673["occurrences"]], ["Gen.2.2", "Gen.2.3"]
        )

        h7307 = self.by_id["H7307"]
        self.assertEqual(h7307["glosses"]["strongs"], "1. wind")
        self.assertEqual(
            [o["passage"] for o in h7307["occurrences"]], ["Gen.1.2"]
        )

    def test_oshb_homonyms_verbatim_counts(self):
        """The OSHB n-attribute is stored verbatim as counts, never identity."""
        h216 = self.by_id["H216"]
        # H216 'light' carries BOTH 0 and 1 in Genesis 1 (proven unreliable as
        # a homograph signal) — the graph must record that honestly.
        self.assertIn("0", h216["oshb_homonyms"])
        self.assertIn("1", h216["oshb_homonyms"])

    def test_occurrence_token_ids_resolve_in_morphology(self):
        """Every token id in the graph must exist in the morphology artifacts
        (no fabricated ids)."""
        morph_ids = set()
        for fname in ("lexicons/morphology-genesis1.json",
                      "lexicons/morphology-genesis2.json"):
            morph = json.loads(Path(fname).read_text(encoding="utf-8"))
            for words in morph["verses"].values():
                for w in words:
                    morph_ids.add(w["id"])
        for l in self.graph["lexemes"]:
            for o in l["occurrences"]:
                for tid in o["token_ids"]:
                    self.assertIn(tid, morph_ids, f"{l['id']}: {tid} not in morphology")

    def test_attestation_reconciles_with_occurrences(self):
        for l in self.graph["lexemes"]:
            self.assertEqual(l["attestation"]["verses"], len(l["occurrences"]))
            self.assertEqual(
                l["attestation"]["tokens"],
                sum(len(o["token_ids"]) for o in l["occurrences"]),
            )

    def test_regeneration_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            write(".", out_path=Path(td) / "wordgraph.json")
            committed = GRAPH_PATH.read_text(encoding="utf-8")
            fresh = (Path(td) / "wordgraph.json").read_text(encoding="utf-8")
            self.assertEqual(
                fresh, committed,
                "WordGraph drifted from its generator. This file is GENERATED — "
                "do not hand-edit. Regenerate: python -m "
                "search.corpus.build_wordgraph --repo . (then update "
                "data/PROVENANCE.md checksum).",
            )

    def test_consumes_committed_artifacts_only(self):
        """The graph must build from committed artifacts alone (runs in CI)."""
        with tempfile.TemporaryDirectory() as td:
            # The committed artifacts are symlinked; raw data/ is absent.
            for rel in ("lexicons", "correlations"):
                src = Path(rel)
                dst = Path(td) / rel
                dst.mkdir(parents=True, exist_ok=True)
                for f in src.glob("*.json"):
                    os.symlink(f.resolve(), dst / f.name)
            payload = build(td)
            self.assertEqual(len(payload["lexemes"]), 183)

    def test_homograph_notes_file_consumed(self):
        """The curated homograph candidates come from the reviewed notes file
        (hand content), not the generator — a code edit must not be needed
        for a data change."""
        notes = json.loads(
            Path("lexicons/wordgraph-notes-genesis.json").read_text(encoding="utf-8")
        )
        self.assertIn("H7673", notes["candidates"])
        # Build from a temp dir with ONLY the notes file replaced: removing
        # the notes file must fail loudly (fail-fast, not silent empty).
        with tempfile.TemporaryDirectory() as td:
            for rel in ("lexicons", "correlations"):
                src = Path(rel)
                dst = Path(td) / rel
                dst.mkdir(parents=True, exist_ok=True)
                for f in src.glob("*.json"):
                    os.symlink(f.resolve(), dst / f.name)
            os.remove(Path(td) / "lexicons" / "wordgraph-notes-genesis.json")
            with self.assertRaises(FileNotFoundError):
                build(td)


if __name__ == "__main__":
    unittest.main(verbosity=2)