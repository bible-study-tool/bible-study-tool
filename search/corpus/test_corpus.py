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
from search.testutil import require_raw_sources

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


@require_raw_sources()
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


@require_raw_sources()
class RegenerationTripwireTests(unittest.TestCase):
    """The committed entries must equal what the generator produces from the
    pinned sources — byte for byte. This catches hand-edits and partial
    regeneration, the same drift-tripwire pattern used for the lexicons."""

    @classmethod
    def setUpClass(cls):
        from search.corpus.build_genesis1 import build_entry_markdown, load_pinned_sources
        cls.kjv, cls.lexicon, cls.tbesh, _ = load_pinned_sources(".")
        cls.build_entry_markdown = staticmethod(build_entry_markdown)
        gen = next(b for b in cls.kjv["books"] if b["name"] == "Genesis")
        ch1 = next(c for c in gen["chapters"] if c["chapter"] == 1)
        cls.verses = {v["verse"]: v for v in ch1["verses"]}

    def test_committed_entries_match_generator_byte_for_byte(self):
        """Uncurated (status: draft) entries must equal what the generator
        produces from the pinned sources — byte for byte. This catches hand-edits
        and partial regeneration on draft skeletons."""
        for v in range(1, 32):
            path = GENESIS_DIR / f"gen-1-{v}-kjv.md"
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if "status: draft" in text:
                expected, _ = self.build_entry_markdown(
                    self.verses[v], self.lexicon, self.tbesh
                )
                self.assertEqual(
                    text, expected,
                    f"{path.name}: draft skeleton differs from generator output "
                    "(hand-edit or stale regeneration) — re-run "
                    "python -m search.corpus.build_genesis1",
                )

    def test_word_study_facts_match_lexicons(self):
        """Every word-study block in the committed entries must be exactly
        what word_study_block() emits from the committed lexicons — a hand-edit
        of a Definition/Gloss line fails here."""
        from search.corpus.build_genesis1 import word_study_block
        import re
        block_header = re.compile(r"^### .+ - Strong's ([HG]\d+)$", re.MULTILINE)
        for v in range(4, 32):
            path = GENESIS_DIR / f"gen-1-{v}-kjv.md"
            text = path.read_text(encoding="utf-8")
            for m in block_header.finditer(text):
                code = m.group(1)
                # Rebuild just this code's block with its source occurrence
                # count and require verbatim presence.
                from search.corpus.build_genesis1 import verse_codes
                _, occ_map, _ = verse_codes(self.verses[v]["text"])
                block = word_study_block(code, occ_map[code], self.lexicon, self.tbesh)
                self.assertIn(block, text, f"{path.name}: word block for {code} drifted")


@require_raw_sources()
class Genesis2SkeletonTests(unittest.TestCase):
    """Genesis 2 (WP-007, ADR-0009 book-level expansion): 25 generated
    skeletons, byte-identical to the generator, all status: draft."""

    @classmethod
    def setUpClass(cls):
        from search.corpus.build_genesis1 import build_entry_markdown, load_pinned_sources
        cls.kjv, cls.lexicon, cls.tbesh, _ = load_pinned_sources(".")
        cls.build_entry_markdown = staticmethod(build_entry_markdown)
        gen = next(b for b in cls.kjv["books"] if b["name"] == "Genesis")
        ch2 = next(c for c in gen["chapters"] if c["chapter"] == 2)
        cls.verses = {v["verse"]: v for v in ch2["verses"]}

    def test_genesis_2_is_complete(self):
        files = sorted(GENESIS_DIR.glob("gen-2-*-kjv.md"))
        self.assertEqual(len(files), 25, "Genesis 2 must have exactly 25 entries")

    def test_all_draft_and_matching_generator_byte_for_byte(self):
        for v in range(1, 26):
            path = GENESIS_DIR / f"gen-2-{v}-kjv.md"
            text = path.read_text(encoding="utf-8")
            self.assertIn("status: draft", text, f"{path.name}: not a draft skeleton")
            expected, _ = self.build_entry_markdown(
                self.verses[v], self.lexicon, self.tbesh, chapter=2
            )
            self.assertEqual(
                text, expected,
                f"{path.name}: draft skeleton differs from generator output "
                "(hand-edit or stale regeneration) — re-run "
                "python -m search.corpus.build_genesis1 --chapter 2 --verses 1-25",
            )

    def test_word_study_facts_match_lexicons(self):
        """Every word-study block in the committed Genesis-2 entries must be
        exactly what word_study_block() emits from the committed lexicons."""
        from search.corpus.build_genesis1 import verse_codes, word_study_block
        import re
        block_header = re.compile(r"^### .+ - Strong's ([HG]\d+)$", re.MULTILINE)
        for v in range(1, 26):
            path = GENESIS_DIR / f"gen-2-{v}-kjv.md"
            text = path.read_text(encoding="utf-8")
            for m in block_header.finditer(text):
                code = m.group(1)
                _, occ_map, _ = verse_codes(self.verses[v]["text"])
                block = word_study_block(code, occ_map[code], self.lexicon, self.tbesh)
                self.assertIn(block, text, f"{path.name}: word block for {code} drifted")

    def test_genesis_2_verses_match_pinned_source(self):
        for v in range(1, 26):
            path = GENESIS_DIR / f"gen-2-{v}-kjv.md"
            quote = next(
                (l for l in path.read_text(encoding="utf-8").splitlines() if l.startswith("> ")),
                "",
            )[2:].strip()
            self.assertEqual(
                quote, clean_verse_text(self.verses[v]["text"]),
                f"Genesis 2:{v}: entry quote does not match pinned source",
            )

    def test_unpadded_code_normalization(self):
        """The pinned source writes unpadded codes (H068, H01); the generator
        must normalize to canonical unpadded form (H68, H1)."""
        v12 = GENESIS_DIR.joinpath("gen-2-12-kjv.md").read_text(encoding="utf-8")
        self.assertIn("strongs-H68", v12)
        v24 = GENESIS_DIR.joinpath("gen-2-24-kjv.md").read_text(encoding="utf-8")
        self.assertIn("strongs-H1", v24)


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

    def test_corpus_entry_lifecycle_and_invariants(self):
        """Every Genesis 1 entry is either status: draft (unmodified skeleton)
        or status: review/final (curated with cross-references and valid update)."""
        files = sorted(GENESIS_DIR.glob("gen-1-*-kjv.md"))
        self.assertEqual(len(files), 31, "Genesis 1 must have exactly 31 entries")
        for p in files:
            text = p.read_text(encoding="utf-8")
            if "status: draft" in text:
                self.assertIn(f"created: {GENERATION_DATE}", text, f"{p.name}: draft creation date")
                self.assertNotIn("cross_references:", text, f"{p.name}: uncurated draft should not have xrefs")
                self.assertNotIn("AI Summary", text, f"{p.name}: uncurated draft should not have AI summary")
            elif "status: review" in text or "status: final" in text:
                self.assertIn("cross_references:", text, f"{p.name}: curated entry must include cross_references")
                self.assertIn("updated:", text, f"{p.name}: curated entry must include updated date")
            else:
                self.fail(f"{p.name}: unrecognized entry status")

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
        """Full pipeline: every Genesis entry passes F1 schema, F2 canonical
        Strong's, F3 xref integrity, and F4 dead-reference audit."""
        from search.linking.loader import Loader
        from search.validation.schema import Taxonomy, validate_all as schema_all
        from search.validation.strongs import StrongsCanonical, validate_all as strongs_all
        from search.validation import xrefs as f3
        from search.validation import audit as f4

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

        f3_issues = [i for i in f3.validate_all(loader) if i.severity == "error"]
        self.assertEqual(f3_issues, [], f"F3 errors: {[str(i) for i in f3_issues]}")

        f4_issues = [i for i in f4.audit_all(loader, ".") if i.severity == "error"]
        self.assertEqual(f4_issues, [], f"F4 errors: {[str(i) for i in f4_issues]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
