"""Unit tests for the New Testament corpus generator (build_nt.py)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from search.corpus.build_nt import (
    clean_verse_text,
    verse_codes,
    word_study_block,
    build_entry_markdown,
    load_pinned_sources,
    generate,
)
from search.testutil import require_raw_sources


class TestBuildNTCleanText(unittest.TestCase):
    def test_clean_verse_text_strips_tags_and_notes(self):
        raw = (
            '<w lemma="strong:G1722 lemma.TR:εν" morph="robinson:PREP" src="1">In</w> '
            '<w lemma="strong:G746 lemma.TR:αρχη" morph="robinson:N-DSF" src="2">the beginning</w> '
            '<note type="study">margin note</note>'
            '<w lemma="strong:G1510 lemma.TR:ην" morph="robinson:V-IAI-3S" src="3">was</w>.'
        )
        self.assertEqual(clean_verse_text(raw), "In the beginning was.")

    def test_verse_codes_extracts_greek_strongs(self):
        raw = (
            '<w lemma="strong:G1722">In</w> '
            '<w lemma="strong:G746">the beginning</w> '
            '<w lemma="strong:G1510">was</w> '
            '<w lemma="strong:G3588 strong:G3056">the Word</w>'
        )
        codes, counts, skipped = verse_codes(raw)
        self.assertEqual(codes, ["G1722", "G746", "G1510", "G3588", "G3056"])
        self.assertEqual(counts["G3056"], 1)
    def test_verse_codes_skipped_out_of_range(self):
        raw = '<w lemma="strong:G1722">In</w> <w lemma="strong:G9999">invalid</w>'
        codes, counts, skipped = verse_codes(raw)
        self.assertEqual(codes, ["G1722"])
        self.assertEqual(skipped, ["G9999"])
        self.assertEqual(counts, {"G1722": 1})


class TestBuildNTWordStudyBlock(unittest.TestCase):
    def test_word_study_block_formatting(self):
        greek_lexicon = {
            "G3056": {
                "word": "λόγος",
                "translit": "logos",
                "desc": "1. a word, speech, divine expression\nStrong's number G3056",
            }
        }
        tbesg_entries = {
            "G3056": [
                {
                    "form": "λόγος",
                    "translit": "logos",
                    "gloss": "word: message",
                    "morph": "G:N-M",
                }
            ]
        }
        block = word_study_block("G3056", 2, greek_lexicon, tbesg_entries)
        self.assertIn("### logos (word) - Strong's G3056", block)
        self.assertIn("*   Transliteration: logos", block)
        self.assertIn("*   Definition: 1. a word, speech, divine expression", block)
        self.assertIn("*   Modern Gloss (TBESG): word: message", block)
        self.assertIn("*   Morphology (STEPBible): G:N-M", block)
        self.assertIn("*   Lemma occurrences in this verse: 2", block)

    def test_word_study_block_without_gloss(self):
        greek_lexicon = {
            "G3056": {
                "word": "λόγος",
                "translit": "logos",
                "desc": "1. a word, speech, divine expression",
            }
        }
        block = word_study_block("G3056", 1, greek_lexicon, {})
        self.assertIn("### logos - Strong's G3056", block)
        self.assertNotIn("(logos)", block)

    def test_short_gloss_delimiters(self):
        from search.corpus.build_nt import _short_gloss
        self.assertEqual(_short_gloss("word: message"), "word")
        self.assertEqual(_short_gloss("create; fashion"), "create")
        self.assertEqual(_short_gloss("life/breath"), "life")


@require_raw_sources()
class TestBuildNTIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kjv, cls.greek_lex, cls.tbesg, cls.canonical = load_pinned_sources(".")

    def test_build_entry_markdown_john_1_1(self):
        book = next(b for b in self.kjv["books"] if b["name"] == "John")
        ch1 = next(c for c in book["chapters"] if c["chapter"] == 1)
        v1 = ch1["verses"][0]

        md, codes = build_entry_markdown(
            v1,
            self.greek_lex,
            self.tbesg,
            book_label="John",
            book_code="john",
            book_tag="book/john",
            chapter=1,
            default_theme="theme/christ",
        )
        self.assertIn("id: john-1-1-kjv", md)
        self.assertIn("book: book/john", md)
        self.assertIn("language: greek", md)
        self.assertIn("translation: kjv", md)
        self.assertIn("theme/christ", md)
        self.assertIn("strongs-G3056", md)
        self.assertIn("# John 1:1 - KJV", md)
        self.assertIn("## Greek Word Study", md)
        self.assertIn("## Source Notes", md)
        self.assertIn("G3056", codes)

    def test_generate_temporary_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            written = generate(
                repo=".",
                out_subdir=f"{tmpdir}/materials/bible/nt/john",
                book_label="John",
                book_code="john",
                book_tag="book/john",
                chapter=1,
                verses=(1, 3),
            )
            self.assertEqual(len(written), 3)
            p1 = Path(written[0])
            self.assertTrue(p1.exists())
            self.assertIn("01/john-1-1-kjv.md", str(p1))
            self.assertIn("In the beginning was the Word", p1.read_text(encoding="utf-8"))

    def test_generate_preloaded_sources(self):
        sources = (self.kjv, self.greek_lex, self.tbesg, self.canonical)
        with tempfile.TemporaryDirectory() as tmpdir:
            written = generate(
                repo=".",
                out_subdir=f"{tmpdir}/materials/bible/nt/john",
                book_label="John",
                book_code="john",
                book_tag="book/john",
                chapter=17,
                verses=(1, 2),
                sources=sources,
            )
            self.assertEqual(len(written), 2)
            p1 = Path(written[0])
            self.assertTrue(p1.exists())
            self.assertIn("17/john-17-1-kjv.md", str(p1))


if __name__ == "__main__":
    unittest.main()
