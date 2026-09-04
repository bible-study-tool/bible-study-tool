"""Unit tests for search/macula/extract_greek.py (WP-020)."""

import json
from pathlib import Path
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

from search.macula.extract_greek import (
    GREEK_MACULA_TO_OSIS,
    NT_CANONICAL_ORDER,
    OSIS_TO_GREEK_MACULA,
    parse_all_greek_books,
    parse_greek_book,
    parse_greek_sentence,
    parse_greek_token,
)
from search.macula.enrichment import get_verse_semantic_frame
from search.macula.lookup import MaculaDB


SAMPLE_GREEK_SENTENCE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<book id="JHN">
  <sentence>
    <p><milestone unit="verse" id="JHN 1:1"/></p>
    <wg class="cl" rule="Conj3CL">
      <wg class="cl" rule="P-VC-S">
        <wg class="pp" role="p" rule="PrepNp">
          <w ref="JHN 1:1!1" strong="1722" class="prep" gloss="in" morph="P">Ἐν</w>
          <w ref="JHN 1:1!2" strong="746" class="noun" gloss="beginning" morph="N-DSF" after=" ">ἀρχῇ</w>
        </wg>
        <w ref="JHN 1:1!3" strong="1510" class="verb" role="vc" gloss="was" morph="V-IAI-3S" after=" ">ἦν</w>
        <wg class="np" role="s" rule="DetNP">
          <w ref="JHN 1:1!4" strong="3588" class="det" gloss="the" morph="T-NSM">ὁ</w>
          <w ref="JHN 1:1!5" strong="3056" class="noun" gloss="Word" morph="N-NSM" after=" ">Λόγος</w>
        </wg>
      </wg>
      <wg class="" rule="">
        <w ref="JHN 1:1!6" strong="2532" class="conj" gloss="and" morph="C" after=" ">καὶ</w>
        <wg class="cl" rule="S-VC-P">
          <wg class="np" role="s" rule="DetNP">
            <w ref="JHN 1:1!7" strong="3588" class="det" gloss="the" morph="T-NSM">ὁ</w>
            <w ref="JHN 1:1!8" strong="3056" class="noun" gloss="Word" morph="N-NSM" after=" ">Λόγος</w>
          </wg>
          <w ref="JHN 1:1!9" strong="1510" class="verb" role="vc" gloss="was" morph="V-IAI-3S" after=" ">ἦν</w>
          <wg class="pp" role="p" rule="PrepNp">
            <w ref="JHN 1:1!10" strong="4314" class="prep" gloss="with" morph="P">πρὸς</w>
            <wg class="np" rule="DetNP">
              <w ref="JHN 1:1!11" strong="3588" class="det" gloss="-" morph="T-ASM">τὸν</w>
              <w ref="JHN 1:1!12" strong="2316" class="noun" gloss="God" morph="N-ASM" after=" ">Θεόν</w>
            </wg>
          </wg>
        </wg>
      </wg>
      <wg class="" rule="">
        <w ref="JHN 1:1!13" strong="2532" class="conj" gloss="and" morph="C" after=" ">καὶ</w>
        <wg class="cl" rule="P-VC-S">
          <w ref="JHN 1:1!14" strong="2316" class="noun" role="p" gloss="God" morph="N-NSM" after=" ">Θεὸς</w>
          <w ref="JHN 1:1!15" strong="1510" class="verb" role="vc" gloss="was" morph="V-IAI-3S" after=" ">ἦν</w>
          <wg class="np" role="s" rule="DetNP">
            <w ref="JHN 1:1!16" strong="3588" class="det" gloss="the" morph="T-NSM">ὁ</w>
            <w ref="JHN 1:1!17" strong="3056" class="noun" gloss="Word" morph="N-NSM">Λόγος</w>
          </wg>
        </wg>
      </wg>
    </wg>
  </sentence>
</book>
"""


class GreekMaculaTokenTests(unittest.TestCase):
    def test_parse_greek_token_attributes(self):
        w_el = ET.Element("w", {
            "id": "n40001001001",
            "strong": "976",
            "class": "noun",
            "role": "s",
            "gloss": "book",
            "morph": "N-NSF",
            "domain": "033005",
            "ln": "33.38",
        })
        w_el.text = "Βίβλος"

        tok = parse_greek_token(w_el)
        self.assertEqual(tok.id, "n40001001001")
        self.assertEqual(tok.text, "Βίβλος")
        self.assertEqual(tok.strongs, "G976")
        self.assertEqual(tok.raw_strongs, "976")
        self.assertEqual(tok.role, "s")
        self.assertEqual(tok.gloss, "book")
        self.assertEqual(tok.pos, "noun")
        self.assertEqual(tok.morph, "N-NSF")
        self.assertEqual(tok.core_domains, ["033005"])
        self.assertEqual(tok.lex_domains, ["33.38"])

    def test_parse_compound_strongs(self):
        w_el = ET.Element("w", {
            "strong": "1501+5140",
            "class": "num",
            "gloss": "forty",
        })
        w_el.text = "τεσσεράκοντα"
        tok = parse_greek_token(w_el)
        self.assertEqual(tok.strongs, "G1501")
        self.assertEqual(tok.raw_strongs, "1501+5140")


class GreekMaculaBookOrderTests(unittest.TestCase):
    def test_canon_mapping_counts(self):
        self.assertEqual(len(GREEK_MACULA_TO_OSIS), 27)
        self.assertEqual(len(OSIS_TO_GREEK_MACULA), 27)
        self.assertEqual(len(NT_CANONICAL_ORDER), 27)
        self.assertEqual(NT_CANONICAL_ORDER[0], "Matt")
        self.assertEqual(NT_CANONICAL_ORDER[-1], "Rev")

    def test_abbreviation_inversion(self):
        for macula_code, osis in GREEK_MACULA_TO_OSIS.items():
            self.assertEqual(OSIS_TO_GREEK_MACULA[osis], macula_code)


class GreekMaculaSentenceParserTests(unittest.TestCase):
    def test_parse_synthetic_sentence(self):
        root = ET.fromstring(SAMPLE_GREEK_SENTENCE_XML)
        s_el = root.find(".//sentence")
        self.assertIsNotNone(s_el)

        records = parse_greek_sentence(s_el, book_osis="John")
        self.assertEqual(len(records), 1)

        v = records[0]
        self.assertEqual(v.verse_id, "John.1.1")
        self.assertEqual(v.chapter, 1)
        self.assertEqual(v.verse_num, 1)
        self.assertIn("Ἐν ἀρχῇ ἦν ὁ Λόγος", v.text)
        self.assertIn("καὶ ὁ Λόγος ἦν πρὸς τὸν Θεόν", v.text)
        self.assertIn("καὶ Θεὸς ἦν ὁ Λόγος", v.text)

        # 3 coordinate clauses
        self.assertEqual(len(v.clauses), 3)

        # Clause 1: Ἐν ἀρχῇ ἦν ὁ Λόγος
        cl1 = v.clauses[0]
        self.assertEqual(cl1.rule, "P-VC-S")
        roles1 = [c.role for c in cl1.constituents]
        self.assertIn("p", roles1)
        self.assertIn("vc", roles1)
        self.assertIn("s", roles1)

        # Clause 2: καὶ ὁ Λόγος ἦν πρὸς τὸν Θεόν
        cl2 = v.clauses[1]
        self.assertEqual(cl2.rule, "S-VC-P")
        roles2 = [c.role for c in cl2.constituents]
        self.assertIn("cjp", roles2)
        self.assertIn("s", roles2)
        self.assertIn("vc", roles2)
        self.assertIn("p", roles2)

        # Clause 3: καὶ Θεὸς ἦν ὁ Λόγος
        cl3 = v.clauses[2]
        self.assertEqual(cl3.rule, "P-VC-S")
        roles3 = [c.role for c in cl3.constituents]
        self.assertIn("cjp", roles3)
        self.assertIn("p", roles3)
        self.assertIn("vc", roles3)
        self.assertIn("s", roles3)

        # Total token count matches
        total_tokens = sum(len(c.tokens) for cl in v.clauses for c in cl.constituents)
        self.assertEqual(total_tokens, 17)


class GreekMaculaLiveDiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.john_xml = Path("data/macula-greek/04-john.xml")
        if not cls.john_xml.is_file():
            raise unittest.SkipTest("data/macula-greek/04-john.xml not on disk")

    def test_parse_live_john_book(self):
        records = parse_greek_book(self.john_xml, osis_book="John")
        self.assertEqual(len(records), 879)

        # Spot check John 3:16
        j316 = next((r for r in records if r.verse_id == "John.3.16"), None)
        self.assertIsNotNone(j316)
        self.assertEqual(len(j316.clauses), 4)

        # Verify roles in John 3:16
        cl1 = j316.clauses[0]
        roles1 = {c.role: c.text for c in cl1.constituents}
        self.assertIn("adv", roles1)  # Οὕτως
        self.assertIn("v", roles1)    # ἠγάπησεν
        self.assertIn("s", roles1)    # ὁ Θεὸς
        self.assertIn("o", roles1)    # τὸν κόσμον

        cl2 = j316.clauses[1]
        roles2 = {c.role: c.text for c in cl2.constituents}
        self.assertIn("o", roles2)    # τὸν Υἱὸν τὸν μονογενῆ
        self.assertIn("v", roles2)    # ἔδωκεν

        cl3 = j316.clauses[2]
        roles3 = {c.role: c.text for c in cl3.constituents}
        self.assertIn("s", roles3)    # πᾶς ὁ πιστεύων εἰς αὐτὸν
        self.assertIn("adv", roles3)  # μὴ
        self.assertIn("v", roles3)    # ἀπόληται

        cl4 = j316.clauses[3]
        roles4 = {c.role: c.text for c in cl4.constituents}
        self.assertIn("v", roles4)    # ἔχῃ
        self.assertIn("o", roles4)    # ζωὴν αἰώνιον

    def test_stream_greek_books_filter(self):
        verses = list(parse_all_greek_books("data/macula-greek", books=["Phlm", "2John"]))
        book_ids = {v.verse_id.split(".")[0] for v in verses}
        self.assertEqual(book_ids, {"Phlm", "2John"})
        self.assertEqual(len(verses), 25 + 13)  # Philemon (25 verses), 2 John (13 verses)


class GreekMaculaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = Path("data/macula.db")
        if not cls.db_path.is_file():
            raise unittest.SkipTest("data/macula.db not on disk")
        cls.db = MaculaDB(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_greek_strongs_crosswalk(self):
        # G2316 = theos (God)
        res = self.db.lookup_strongs("G2316")
        self.assertIsNotNone(res)
        self.assertEqual(res["strongs"], "G2316")
        self.assertIn("θεός", res["lemmas"])
        self.assertGreaterEqual(res["occurrences"], 1300)

        # G3056 = logos (Word)
        res_logos = self.db.lookup_strongs("G3056")
        self.assertIsNotNone(res_logos)
        self.assertIn("λόγος", res_logos["lemmas"])

    def test_nt_semantic_frame_john_3_16(self):
        frame = get_verse_semantic_frame("John 3:16", db=self.db)
        self.assertIsNotNone(frame)
        self.assertEqual(frame["verse_id"], "John.3.16")
        self.assertEqual(len(frame["clauses"]), 4)

        # Main clause participant roles
        cl1 = frame["clauses"][0]
        ag1 = [a["text"] for a in cl1["agents"]]
        ac1 = [a["text"] for a in cl1["actions"]]
        pt1 = [p["text"] for p in cl1["patients"]]
        self.assertIn("ὁ Θεὸς", ag1)
        self.assertIn("ἠγάπησεν", ac1)
        self.assertIn("τὸν κόσμον", pt1)

    def test_cli_nt_queries(self):
        # Test CLI lookup by verse
        res_v = subprocess.run(
            [sys.executable, "scripts/macula_lookup.py", "--verse", "John 3:16", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_v.returncode, 0, res_v.stderr)
        data_v = json.loads(res_v.stdout)
        self.assertEqual(data_v["verse_id"], "John.3.16")
        self.assertEqual(len(data_v["clauses"]), 4)

        # Test CLI lookup by Greek Strongs
        res_s = subprocess.run(
            [sys.executable, "scripts/macula_lookup.py", "--strongs", "G2316", "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_s.returncode, 0, res_s.stderr)
        data_s = json.loads(res_s.stdout)
        self.assertEqual(data_s["strongs"], "G2316")

    def test_copular_semantic_frame_john_1_1(self):
        frame = get_verse_semantic_frame("John 1:1", db=self.db)
        self.assertIsNotNone(frame)
        self.assertEqual(frame["verse_id"], "John.1.1")
        actions = [a["text"] for cl in frame["clauses"] for a in cl["actions"]]
        self.assertIn("ἦν", actions)


if __name__ == "__main__":
    unittest.main()
