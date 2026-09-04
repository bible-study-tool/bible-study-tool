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
from search.testutil import require_raw_sources


@require_raw_sources()
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

    def test_verse_text_fidelity_vs_committed_entries(self):
        """Pipeline-fidelity pattern: verse_text facts must equal the KJV
        quotes in all 31 committed entries — EXCEPT the pinned Gen.1.2
        KJV-edition variant (curated entry reads 'The earth was without
        form, and void'; pinned source reads 'And the earth was without form
        and void'; see search/corpus/test_corpus.py and data/PROVENANCE.md).
        The variant stays visible; any OTHER divergence fails."""
        for v in range(1, 32):
            path = Path("materials/bible/ot/genesis") / f"gen-1-{v}-kjv.md"
            quote = next(
                (l[2:].strip() for l in path.read_text(encoding="utf-8").splitlines()
                 if l.startswith("> ")),
            )
            fact = next(f for f in self.facts
                        if f["fact_type"] == FACT_VERSE_TEXT and f["key"] == f"Gen.1.{v}")
            if v == 2:
                normalized = quote.replace(
                    "The earth was without form, and void",
                    "And the earth was without form and void",
                    1,
                )
                self.assertEqual(fact["value"], normalized, f"Gen.1.{v}")
                self.assertNotEqual(fact["value"], quote)  # variant stays visible
            else:
                self.assertEqual(fact["value"], quote, f"Gen.1.{v}")

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

    def test_word_detail_agrees_with_multiset_all_verses(self):
        """The two-path invariant, asserted for every verse (not just v1)."""
        for f in self.facts:
            if f["fact_type"] != FACT_WORD_STRONGS:
                continue
            flat = sorted(c for w in f["meta"]["words"] for c in w["codes"])
            self.assertEqual(flat, f["value"], f["key"])

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

    def test_self_closing_w_tag_handled_without_token_loss(self):
        # Gen 44:10 contains self-closing <w lemma="strong:H03651"/>
        ch44_facts = kjv_osis_facts(".", chapter=44)
        v10 = next(
            f for f in ch44_facts
            if f["key"] == "Gen.44.10" and f["fact_type"] == FACT_WORD_STRONGS
        )
        self.assertIn("H3651", v10["value"])
        # Verify subsequent tokens were not dropped:
        self.assertIn("H4672", v10["value"])


@require_raw_sources()
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
            artifact_records = self.artifact["verses"][vnum]
            artifact_bases = sorted(r["base"] for r in artifact_records if r["base"])
            self.assertEqual(fact["value"], artifact_bases, fact["key"])
            # Document order and stable ids must match the artifact exactly
            # (the meta is S4's alignment substrate — pin it).
            self.assertEqual(
                [w["id"] for w in fact["meta"]["words"]],
                [r["id"] for r in artifact_records],
                fact["key"],
            )
            self.assertEqual(
                [w["i"] for w in fact["meta"]["words"]],
                list(range(1, len(artifact_records) + 1)),
                fact["key"],
            )

    def test_meta_carries_homonym_and_variant_fields(self):
        """S4 needs the OSHB homonym attr (n) and lemma suffix — e.g. the
        '1254 a' record must expose suffix 'a' in meta."""
        v1 = next(f for f in self.facts if f["key"] == "Gen.1.1")
        bara = v1["meta"]["words"][1]
        self.assertEqual(bara["suffix"], "a")
        self.assertEqual(bara["prefixes"], [])
        reshith = v1["meta"]["words"][0]
        self.assertEqual(reshith["prefixes"], ["b"])
        self.assertIsNotNone(reshith["n"])


class LexiconAdapterTests(unittest.TestCase):
    # Exactly the codes whose Strong's desc lacks a numbered definition
    # (verified against the committed lexicon; 3 Hebrew + 1 + 100 Greek).
    NO_DEFINITION = (
        {"H2492", "H5774", "H7114"}
        | {"G2717"}
        | {f"G{n}" for n in range(3203, 3303)}
    )

    def test_strongs_covers_full_canonical(self):
        facts = strongs_gloss_facts(".")
        self.assertEqual(len(facts), 14298)
        by_key = {f["key"]: f["value"] for f in facts}
        self.assertIn("H1254", by_key)
        # Pinned from the committed lexicon (the curated entry's wording
        # 'to create, shape, form' is human text, not the lexicon's).
        self.assertEqual(by_key["H1254"], "1. (absolutely) to create")
        self.assertIn("G746", by_key)

    def test_no_definition_codes_are_marked(self):
        """Scraper-header 'glosses' must be flagged no_definition so S2 emits
        no_reading — never a manufactured disagreement. Includes H5774 ('to
        fly'), which IS a Genesis 1 word."""
        facts = strongs_gloss_facts(".")
        for f in facts:
            expected = "no_definition" if f["key"] in self.NO_DEFINITION else "definition"
            self.assertEqual(f["meta"]["gloss_status"], expected, f["key"])
        self.assertEqual(len(self.NO_DEFINITION), 104)
        # The verbatim header is still kept as the value (lossless).
        h5774 = next(f for f in facts if f["key"] == "H5774")
        self.assertEqual(h5774["meta"]["gloss_status"], "no_definition")
        self.assertIn("Strong's Number H5774", h5774["value"])

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

    def test_primary_record_is_lexical_head(self):
        """Pins the [0]-is-head convention on known multi-variant codes: H1
        (father vs part-of compounds), H1254 (create/fatten), H226
        (sign: miraculous vs indicator)."""
        by_key = {f["key"]: f["value"] for f in tbesh_gloss_facts(".")}
        self.assertEqual(by_key["H1"], "father")
        self.assertEqual(by_key["H1254"], "to create")
        self.assertEqual(by_key["H226"], "sign: miraculous")


@require_raw_sources()
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