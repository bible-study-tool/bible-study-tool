"""Tests for the agreement-layer fact model and source adapters (S1)."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from search.agreement.facts import (
    collect_all,
    index_facts,
    kjv_osis_facts,
    oshb_facts,
    strongs_gloss_facts,
    tbesh_gloss_facts,
    tbesg_gloss_facts,
    FACT_LEXICON_GLOSS,
    FACT_VERSE_TEXT,
    FACT_WORD_STRONGS,
)


class KjvOsisAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = kjv_osis_facts(".")

    def test_counts(self):
        verse = [f for f in self.facts if f["fact_type"] == FACT_VERSE_TEXT]
        words = [f for f in self.facts if f["fact_type"] == FACT_WORD_STRONGS]
        self.assertEqual(len(verse), 31)
        self.assertEqual(len(words), 31)

    def test_verse_text_known_value(self):
        f = next(f for f in self.facts
                 if f["fact_type"] == FACT_VERSE_TEXT and f["key"] == "Gen.1.1")
        self.assertEqual(f["value"], "In the beginning God created the heaven and the earth.")

    def test_word_multiset_known_value(self):
        """Gen 1:1 lemma tokens: H07225, H0430, H0853+H01254, H08064, H0853, H0776."""
        f = next(f for f in self.facts
                 if f["fact_type"] == FACT_WORD_STRONGS and f["key"] == "Gen.1.1")
        self.assertEqual(
            f["value"],
            sorted(["H7225", "H430", "H853", "H1254", "H8064", "H853", "H776"]),
        )
        # 6 <w> word elements; the merged one carries two codes.
        self.assertEqual(f["meta"]["word_count"], 6)
        merged = [w for w in f["meta"]["words"] if len(w["codes"]) > 1]
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["codes"], ["H853", "H1254"])
        self.assertEqual(merged[0]["text"], "created")

    def test_multiset_equals_verse_codes_expansion(self):
        """The adapter's multiset must equal the corpus generator's occurrence
        expansion — the two paths cannot drift."""
        from search.corpus.build_genesis1 import load_pinned_sources, verse_codes
        kjv, _, _, _ = load_pinned_sources(".")
        gen = next(b for b in kjv["books"] if b["name"] == "Genesis")
        ch1 = next(c for c in gen["chapters"] if c["chapter"] == 1)
        by_key = {f["key"]: f for f in self.facts if f["fact_type"] == FACT_WORD_STRONGS}
        for verse in ch1["verses"]:
            key = f"Gen.1.{verse['verse']}"
            codes, occ, _ = verse_codes(verse["text"])
            expected = sorted(c for c, n in occ.items() for _ in range(n))
            self.assertEqual(by_key[key]["value"], expected, key)


class OshbAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = oshb_facts(".")
        cls.artifact = json.loads(
            Path("lexicons/morphology-genesis1.json").read_text(encoding="utf-8")
        )

    def test_counts_match_morphology_artifact(self):
        self.assertEqual(len(self.facts), 31)
        for fact in self.facts:
            vnum = fact["key"].split(".")[-1]
            self.assertEqual(
                fact["meta"]["word_count"],
                len(self.artifact["verses"][vnum]),
                fact["key"],
            )

    def test_known_v1_agrees_with_kjv_osis_as_multiset(self):
        """Genesis 1:1 — the two independent sources agree as verse-level
        multisets despite different word segmentation (KJV-osis merges the
        object marker into the verb span; OSHB keeps it standalone)."""
        kjv = next(f for f in kjv_osis_facts(".")
                   if f["fact_type"] == FACT_WORD_STRONGS and f["key"] == "Gen.1.1")
        oshb = next(f for f in self.facts if f["key"] == "Gen.1.1")
        self.assertEqual(kjv["value"], oshb["value"])

    def test_total_code_tokens_match_artifact(self):
        artifact_tokens = sum(
            1
            for words in self.artifact["verses"].values()
            for r in words
            if r["base"]
        )
        adapter_tokens = sum(len(f["value"]) for f in self.facts)
        self.assertEqual(adapter_tokens, artifact_tokens)

    def test_consistent_with_committed_morphology_records(self):
        for fact in self.facts:
            vnum = fact["key"].split(".")[-1]
            artifact_bases = sorted(
                r["base"] for r in self.artifact["verses"][vnum] if r["base"]
            )
            self.assertEqual(fact["value"], artifact_bases, fact["key"])


class LexiconAdapterTests(unittest.TestCase):
    def test_strongs_covers_full_canonical(self):
        facts = strongs_gloss_facts(".")
        self.assertEqual(len(facts), 14298)
        by_key = {f["key"]: f["value"] for f in facts}
        self.assertIn("H1254", by_key)
        # Pinned from the committed lexicon (the curated entry's wording
        # 'to create, shape, form' is human text, not the lexicon's).
        self.assertEqual(by_key["H1254"], "1. (absolutely) to create")
        self.assertIn("G746", by_key)

    def test_tbesh_covers_all_hebrew(self):
        facts = tbesh_gloss_facts(".")
        self.assertEqual(len(facts), 8674)
        by_key = {f["key"]: f["value"] for f in facts}
        self.assertEqual(by_key["H1254"], "to create")
        self.assertEqual(by_key["H7225"], "first: beginning")

    def test_tbesg_covers_greek_subset(self):
        facts = tbesg_gloss_facts(".")
        self.assertEqual(len(facts), 5523)
        by_key = {f["key"]: f["value"] for f in facts}
        self.assertEqual(by_key["G746"], "beginning")
        self.assertEqual(by_key["G26"], "love")


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all_facts = collect_all(".")

    def test_all_five_sources_present(self):
        self.assertEqual(
            set(self.all_facts),
            {"kjv-osis", "oshb", "strongs", "tbesh", "tbesg"},
        )

    def test_collect_is_deterministic(self):
        again = collect_all(".")
        self.assertEqual(
            json.dumps(self.all_facts, sort_keys=True, ensure_ascii=False),
            json.dumps(again, sort_keys=True, ensure_ascii=False),
        )

    def test_index_groups_and_detects_duplicates(self):
        idx = index_facts(self.all_facts)
        self.assertEqual(set(idx), {FACT_VERSE_TEXT, FACT_WORD_STRONGS, FACT_LEXICON_GLOSS})
        gloss = idx[FACT_LEXICON_GLOSS]["H1254"]
        self.assertEqual(set(gloss), {"strongs", "tbesh"})
        word = idx[FACT_WORD_STRONGS]["Gen.1.1"]
        self.assertEqual(set(word), {"kjv-osis", "oshb"})

        # A duplicated fact must be rejected, not silently double-counted.
        dup = {"kjv-osis": list(self.all_facts["kjv-osis"]) + [self.all_facts["kjv-osis"][0]]}
        with self.assertRaises(ValueError):
            index_facts(dup)

    def test_gloss_keys_within_canonical(self):
        canonical = json.loads(
            Path("lexicons/strongs-list.json").read_text(encoding="utf-8")
        )
        canon = set(canonical["hebrew"]) | set(canonical["greek"])
        for source in ("strongs", "tbesh", "tbesg"):
            for f in self.all_facts[source]:
                if f["fact_type"] == FACT_LEXICON_GLOSS:
                    self.assertIn(f["key"], canon, f"{source}: {f['key']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)