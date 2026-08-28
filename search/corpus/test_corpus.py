"""Tests for the Genesis 1 corpus generation (A1) and corpus-wide integrity."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from search.corpus.build_genesis1 import (
    GENERATION_DATE,
    clean_verse_text,
    load_pinned_sources,
)

GENESIS_DIR = Path("materials/bible/ot/genesis")


class CleanTextTests(unittest.TestCase):
    def test_strips_notes_but_keeps_supplied_words(self):
        raw = (
            '<w lemma="strong:H0430">And God</w> <w lemma="strong:H0853 strong:H07200">saw</w> '
            '<w lemma="strong:H0216">the light</w>, <w lemma="strong:H03588">that</w> '
            '<transChange type="added">it was</transChange> <w lemma="strong:H02896">good</w>: '
            '<note type="study"><catchWord>the light from…</catchWord>: Heb. '
            '<rdg type="x-literal">between the light</rdg></note> '
            '<w lemma="strong:H02822">the darkness</w>.'
        )
        self.assertEqual(
            clean_verse_text(raw),
            "And God saw the light, that it was good: the darkness.",
        )

    def test_no_note_leakage_in_generated_entries(self):
        for p in GENESIS_DIR.glob("gen-1-*-kjv.md"):
            quote = next(
                (l for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("> ")),
                "",
            )
            for marker in ("…", "<", "&", "Heb. ", "catchWord"):
                self.assertNotIn(
                    marker, quote, f"{p.name}: leaked '{marker}' into verse text"
                )


class PipelineFidelityTests(unittest.TestCase):
    """The extraction pipeline applied to the CURATED verses (1-3) must
    reproduce the hand-curated entries' KJV quotes exactly — proving the
    generator's text pipeline is faithful to the pinned source."""

    @classmethod
    def setUpClass(cls):
        cls.kjv, _, _, _ = load_pinned_sources(".")
        gen = next(b for b in cls.kjv["books"] if b["name"] == "Genesis")
        ch1 = next(c for c in gen["chapters"] if c["chapter"] == 1)
        cls.verses = {v["verse"]: v for v in ch1["verses"]}

    def _curated_quote(self, v: int) -> str:
        path = GENESIS_DIR / f"gen-1-{v}-kjv.md"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("> "):
                return line[2:].strip()
        raise AssertionError(f"no quoted verse text in {path}")

    def test_pipeline_reproduces_curated_v1_2_3(self):
        """v1/v3 must match the curated quotes exactly. v2 is a KNOWN, pinned
        KJV-edition variant: the scrollmapper source reads 'And the earth was
        without form and void' while the hand-curated entry (typed from a
        different printing) reads 'The earth was without form, and void' —
        the 1769 Cambridge standard is 'And the earth was without form, and
        void'. The curated entry is human content and stays untouched; the
        pinned source stays authoritative for generated entries. Any OTHER
        divergence must fail here."""
        for v in (1, 3):
            generated = clean_verse_text(self.verses[v]["text"])
            curated = self._curated_quote(v)
            self.assertEqual(
                generated, curated,
                f"Genesis 1:{v}: generator text differs from curated entry",
            )
        # v2: the ONLY allowed differences are the two known variant tokens.
        generated = clean_verse_text(self.verses[2]["text"])
        curated = self._curated_quote(2)
        normalized_curated = curated.replace(
            "The earth was without form, and void",
            "And the earth was without form and void",
            1,
        )
        self.assertEqual(generated, normalized_curated)
        self.assertNotEqual(generated, curated)  # variant must stay visible

    def test_generated_verse_text_matches_pinned_source(self):
        for v in range(4, 32):
            path = GENESIS_DIR / f"gen-1-{v}-kjv.md"
            quote = next(
                (l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("> ")),
                "",
            )[2:].strip()
            self.assertEqual(
                quote, clean_verse_text(self.verses[v]["text"]),
                f"Genesis 1:{v}: entry quote does not match pinned source",
            )


class CorpusIntegrityTests(unittest.TestCase):
    """Golden corpus counts + tag canonicality for the whole Genesis chapter."""

    @classmethod
    def setUpClass(cls):
        cls.canonical = json.loads(
            Path("lexicons/strongs-list.json").read_text(encoding="utf-8")
        )
        cls.canon_all = set(cls.canonical["hebrew"]) | set(cls.canonical["greek"])

    def test_genesis_1_is_complete(self):
        files = sorted(GENESIS_DIR.glob("gen-1-*-kjv.md"))
        self.assertEqual(len(files), 31, "Genesis 1 must have exactly 31 entries")

    def test_new_entries_are_draft_skeletons(self):
        """Generated entries (4-31) must be status: draft with the pinned
        generation date and NO fabricated cross-references/semantic links."""
        for v in range(4, 32):
            text = (GENESIS_DIR / f"gen-1-{v}-kjv.md").read_text(encoding="utf-8")
            self.assertIn("status: draft", text)
            self.assertIn(f"created: {GENERATION_DATE}", text)
            self.assertNotIn("cross_references:", text)
            self.assertNotIn("semantic_links:", text)
            self.assertNotIn("AI Summary", text)

    def test_curated_entries_untouched_status(self):
        for v in (1, 2, 3):
            text = (GENESIS_DIR / f"gen-1-{v}-kjv.md").read_text(encoding="utf-8")
            self.assertIn("status: review", text)

    def test_all_tags_in_canonical_list(self):
        for p in GENESIS_DIR.glob("gen-1-*-kjv.md"):
            text = p.read_text(encoding="utf-8")
            for tag in (l.strip("- ").strip() for l in text.splitlines()
                        if l.lstrip().startswith("- strongs-")):
                self.assertIn(
                    tag.removeprefix("strongs-"), self.canon_all,
                    f"{p.name}: tag {tag} not in canonical Strong's list",
                )

    def test_corpus_wide_schema_and_canonical_validation(self):
        """Full pipeline: every Genesis entry passes F1 schema + F2 canonical."""
        from search.linking.loader import Loader
        from search.validation.schema import Taxonomy, validate_all as schema_all
        from search.validation.strongs import StrongsCanonical, validate_all as strongs_all

        tax = Taxonomy("tags/taxonomy.json")
        loader = Loader(".")
        loader.load_entries()
        schema_issues = [i for i in schema_all(loader, tax) if i.severity == "error"]
        self.assertEqual(schema_issues, [], f"F1 errors: {[str(i) for i in schema_issues]}")

        canon = StrongsCanonical(
            hebrew=set(self.canonical["hebrew"]), greek=set(self.canonical["greek"])
        )
        strongs_issues = [i for i in strongs_all(loader, canon) if i.severity == "error"]
        self.assertEqual(strongs_issues, [], f"F2 errors: {[str(i) for i in strongs_issues]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
