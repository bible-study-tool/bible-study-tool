"""Tests for the WordGraph draft engine (WP-010, ADR-010).

The engine assembles word-study blocks from the WordGraph — no LLM, no raw
data/ sources, no direct lexicon/TBESH access. It must be a DROP-IN for
build_genesis1.word_study_block (pinned byte-identically) and format-
compatible with the loader's _extract_words and wp_check's skeleton checks.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from search.corpus.build_genesis1 import load_pinned_sources, word_study_block
from search.corpus.draft_engine import DraftEngine
from search.testutil import require_raw_sources


class EngineUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DraftEngine(".")

    def test_provenance_is_schema_version(self):
        self.assertEqual(self.engine.provenance, "wordgraph-genesis/v1")

    def test_unknown_code_raises(self):
        """Fail-fast: a code outside the graph is a data error, never a
        silent empty block."""
        with self.assertRaises(KeyError):
            self.engine.word_study_block("H9999", 1)

    def test_verse_blocks_counts(self):
        """verse_blocks must count occurrences from the raw verse text the
        same way the corpus generator does."""
        raw = (
            '<w lemma="strong:H0430">God</w> <w lemma="strong:H01254">created</w> '
            '<w lemma="strong:H0853 strong:H07225">the beginning</w>'
        )
        blocks = self.engine.verse_blocks(raw, ["H430", "H1254", "H853", "H7225"])
        self.assertIn("*   Lemma occurrences in this verse: 1", blocks["H430"])
        self.assertIn("*   Lemma occurrences in this verse: 1", blocks["H853"])
        self.assertIn("*   Lemma occurrences in this verse: 1", blocks["H7225"])


@require_raw_sources()
class EngineDropInTests(unittest.TestCase):
    """The engine must reproduce the legacy word_study_block byte-for-byte
    for EVERY Genesis 1-2 verse — proving it is a drop-in replacement before
    it ever touches a new chapter."""

    def test_single_lexeme_byte_identical(self):
        """Engine output for a known lexeme equals the legacy block."""
        _, lexicon, tbesh, _ = load_pinned_sources(".")
        legacy = word_study_block("H1254", 3, lexicon, tbesh)
        new = DraftEngine(".").word_study_block("H1254", 3)
        self.assertEqual(new, legacy)

    def test_all_genesis_1_2_blocks_byte_identical(self):
        from search.corpus.build_genesis1 import verse_codes
        kjv, lexicon, tbesh, _ = load_pinned_sources(".")
        engine = DraftEngine(".")
        gen = next(b for b in kjv["books"] if b["name"] == "Genesis")
        diffs = 0
        checked = 0
        for ch in (1, 2):
            chdata = next(c for c in gen["chapters"] if c["chapter"] == ch)
            for v in chdata["verses"]:
                codes, occ, _ = verse_codes(v["text"])
                for code in codes:
                    checked += 1
                    legacy = word_study_block(code, occ[code], lexicon, tbesh)
                    new = engine.word_study_block(code, occ[code])
                    if legacy != new:
                        diffs += 1
                        self.fail(
                            f"Gen {ch}:{v['verse']} {code} differs — engine is "
                            "not a drop-in"
                        )
        self.assertEqual(checked, 516)
        self.assertEqual(diffs, 0)

    def test_loader_parses_engine_blocks(self):
        """The loader's _extract_words must parse engine-rendered blocks the
        same as legacy ones (format compatibility)."""
        from search.linking.loader import _extract_words
        engine = DraftEngine(".")
        _, lexicon, tbesh, _ = load_pinned_sources(".")
        legacy = word_study_block("H1254", 3, lexicon, tbesh)
        new = engine.word_study_block("H1254", 3)
        lw = _extract_words(f"## Hebrew Word Study\n\n{legacy}")
        nw = _extract_words(f"## Hebrew Word Study\n\n{new}")
        self.assertEqual(lw, nw)
        self.assertEqual(lw[0]["strongs"], "H1254")
        self.assertEqual(lw[0]["word"], "baw-raw'")


@require_raw_sources()
class EngineBuildIntegrationTests(unittest.TestCase):
    """The generator with --draft-engine produces valid, engine-assembled
    entries; the default path is untouched."""

    def test_engine_entry_has_provenance_marker(self):
        from search.corpus.build_genesis1 import build_entry_markdown, load_pinned_sources
        kjv, lexicon, tbesh, _ = load_pinned_sources(".")
        gen = next(b for b in kjv["books"] if b["name"] == "Genesis")
        ch2 = next(c for c in gen["chapters"] if c["chapter"] == 2)
        v1 = next(v for v in ch2["verses"] if v["verse"] == 1)
        engine = DraftEngine(".")
        md, _ = build_entry_markdown(
            v1, lexicon, tbesh, chapter=2, engine=engine
        )
        self.assertIn("assembled deterministically from the WordGraph", md)
        self.assertIn("wordgraph-genesis/v1", md)
        self.assertIn("### kaw-law' (to end) - Strong's H3615", md)

    def test_default_path_no_provenance(self):
        from search.corpus.build_genesis1 import build_entry_markdown, load_pinned_sources
        kjv, lexicon, tbesh, _ = load_pinned_sources(".")
        gen = next(b for b in kjv["books"] if b["name"] == "Genesis")
        ch2 = next(c for c in gen["chapters"] if c["chapter"] == 2)
        v1 = next(v for v in ch2["verses"] if v["verse"] == 1)
        md, _ = build_entry_markdown(v1, lexicon, tbesh, chapter=2)
        self.assertNotIn("WordGraph", md)
        self.assertNotIn("wordgraph-genesis/v1", md)

    def test_generator_clone_safe_with_engine(self):
        """The engine path must work from committed artifacts alone (CI)."""
        with tempfile.TemporaryDirectory() as td:
            import os
            for rel in ("lexicons", "correlations"):
                src = Path(rel)
                dst = Path(td) / rel
                dst.mkdir(parents=True, exist_ok=True)
                for f in src.glob("*.json"):
                    os.symlink(f.resolve(), dst / f.name)
            engine = DraftEngine(td)
            self.assertEqual(engine.provenance, "wordgraph-genesis/v1")
            # H121 (kjv-osis-only) must be present — the graph includes it.
            self.assertIn("H121", engine._by_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)