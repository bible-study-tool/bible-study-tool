"""Tests for the semantic linking pipeline (layers b and c).

Run from the repo root:
    python -m search.linking.test_pipeline
"""

from __future__ import annotations

import unittest

from search.linking.loader import Loader
from search.linking.concordance import build_concordance
from search.linking.candidates import discover_candidates, _curated_pairs, _merge_existing, _candidate_key
from search.linking.embedder import get_embedder


class LoaderTests(unittest.TestCase):
    def test_loads_entries(self):
        loader = Loader(".")
        entries = loader.load_entries()
        self.assertGreaterEqual(len(entries), 3)

    def test_strongs_tags_parsed(self):
        loader = Loader(".")
        loader.load_entries()
        gen1 = next(e for e in loader.entries if e.id == "gen-1-1-kjv")
        self.assertIn("strongs-H7225", gen1.tags)

    def test_words_extracted_with_definitions(self):
        loader = Loader(".")
        loader.load_entries()
        gen1 = next(e for e in loader.entries if e.id == "gen-1-1-kjv")
        by_strongs = {w["strongs"]: w for w in gen1.words}
        self.assertIn("H7225", by_strongs)
        self.assertTrue(by_strongs["H7225"]["transliteration"])
        self.assertTrue(by_strongs["H1254"]["definition"])


class ConcordanceTests(unittest.TestCase):
    def test_builds_root_index(self):
        loader = Loader(".")
        loader.load_entries()
        data = build_concordance(loader)
        self.assertIn("H7225", data["by_strongs"])
        self.assertEqual(len(data["by_strongs"]), data["summary"]["roots"])

    def test_links_must_be_cross_referenced(self):
        loader = Loader(".")
        loader.load_entries()
        data = build_concordance(loader)
        # H1254 (bara) appears in this MVP; it should be in the index.
        self.assertIn("H1254", data["by_strongs"])


class DbIndexTests(unittest.TestCase):
    def _build(self):
        import tempfile

        tmp = tempfile.mkdtemp()
        return f"{tmp}/semantic.db"

    def test_build_and_query(self):
        from search.linking.loader import Loader
        from search.linking.dbindex import SemanticDB, build_index

        db_path = self._build()
        loader = Loader(".")
        loader.load_entries()
        db = SemanticDB(db_path=db_path)
        db.build(loader)

        self.assertEqual(db.count(), len(loader.entries))

        # metadata queries (proper SQL, no rescan)
        self.assertEqual(len(db.entries_by_strongs("H7225")), 1)
        # Golden corpus count: all 31 Genesis-1 entries carry theme/creation.
        self.assertEqual(len(db.entries_by_tag("theme/creation")), 31)

        # FTS free-text
        fts = db.search("creation light")
        self.assertGreaterEqual(len(fts), 1)

    def test_concordance_from_db(self):
        import tempfile

        from search.linking.dbindex import SemanticDB

        db_path = self._build()
        loader = Loader(".")
        loader.load_entries()
        db = SemanticDB(db_path=db_path)
        db.build(loader)

        pairs = db.concordance()
        strongs_set = {p["strongs"] for p in pairs}
        self.assertIn("H7225", strongs_set)

        # DB-backed build_concordance must equal loader-backed.
        from search.linking.concordance import build_concordance

        db_only = build_concordance(loader, db=db)
        loader_only = build_concordance(loader)
        self.assertEqual(
            set(db_only["by_strongs"]), set(loader_only["by_strongs"])
        )

    def test_db_lexemes_match_loader(self):
        import tempfile

        from search.linking.candidates import _read_lexemes
        from search.linking.dbindex import SemanticDB

        db_path = self._build()
        loader = Loader(".")
        loader.load_entries()
        db = SemanticDB(db_path=db_path)
        db.build(loader)

        via_loader = _read_lexemes(loader, db=None)
        via_db = _read_lexemes(loader, db=db)
        self.assertEqual({x.strongs for x in via_loader}, {x.strongs for x in via_db})


class CandidateTests(unittest.TestCase):
    def test_curated_pairs_are_excluded(self):
        loader = Loader(".")
        loader.load_entries()
        pairs = _curated_pairs(loader)
        # sl-002 links H1254 with G2936.
        self.assertIn(frozenset(("H1254", "G2936")), pairs)

    def test_discover_never_returns_curated_pair(self):
        loader = Loader(".")
        loader.load_entries()
        cands = discover_candidates(loader, top_k=20, min_similarity=0.4)
        curated = _curated_pairs(loader)
        for c in cands:
            strongs = {e["strongs"] for e in c["entries"]}
            self.assertNotIn(frozenset(strongs), curated, f"{strongs} already curated")

    def test_discover_high_threshold_yields_nothing_duplicated(self):
        loader = Loader(".")
        loader.load_entries()
        # With the strict default, any emitted candidate must be a novel,
        # non-curated cross-language link.
        cands = discover_candidates(loader, top_k=20, min_similarity=0.70)
        curated = _curated_pairs(loader)
        for c in cands:
            strongs = {e["strongs"] for e in c["entries"]}
            self.assertNotIn(frozenset(strongs), curated)
            langs = {e["language"] for e in c["entries"]}
            self.assertEqual(len(langs), 2, "candidates must be cross-language")

    def test_merge_preserves_review_annotations(self):
        """Human review metadata must survive regeneration (no clobbering)."""
        prior = [
            {
                "id": "aid-1",
                "type": "relation/equivalent",
                "review_status": "rejected",
                "aligns_with_doctrine": None,
                "reviewed_by": "reviewer@example",
                "review_note": "unsupported etymology",
                "entries": [{"strongs": "H1111"}, {"strongs": "G2222"}],
            }
        ]
        fresh = [
            {
                "id": "aid-20260101-001",
                "type": "relation/equivalent",
                "review_status": "pending",
                "aligns_with_doctrine": None,
                "entries": [{"strongs": "G2222"}, {"strongs": "H1111"}],
            },
            {
                "id": "aid-20260101-002",
                "type": "relation/semantic-field",
                "review_status": "pending",
                "aligns_with_doctrine": None,
                "entries": [{"strongs": "H3333"}, {"strongs": "G4444"}],
            },
        ]
        merged = _merge_existing(prior, fresh)
        self.assertEqual(len(merged), 2)
        by_pair = {_candidate_key(c): c for c in merged}
        # The reviewed pair keeps its annotations despite fresh 'pending'.
        reviewed = by_pair[frozenset({"H1111", "G2222"})]
        self.assertEqual(reviewed["review_status"], "rejected")
        self.assertEqual(reviewed["reviewed_by"], "reviewer@example")
        self.assertEqual(reviewed["review_note"], "unsupported etymology")
        # The new pair stays untouched/pending.
        new = by_pair[frozenset({"H3333", "G4444"})]
        self.assertEqual(new["review_status"], "pending")

    def test_candidate_key_is_unordered(self):
        """Identity key must not depend on entry ordering."""
        a = {"entries": [{"strongs": "H1"}, {"strongs": "G2"}]}
        b = {"entries": [{"strongs": "G2"}, {"strongs": "H1"}]}
        self.assertEqual(_candidate_key(a), _candidate_key(b))


    def test_embedder_deterministic_available(self):
        emb = get_embedder(prefer_model=False)
        import numpy as np

        v = emb.embed("בָּרָא to create")
        self.assertEqual(len(v), 512)
        self.assertAlmostEqual(float(np.linalg.norm(v)), 1.0, places=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
