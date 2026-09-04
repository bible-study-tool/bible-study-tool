"""Unit tests for search/macula/extract.py."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from search.macula.extract import (
    map_mt_to_canonical_verse,
    normalize_greek_strongs,
    normalize_hebrew_strongs,
    parse_chapter_xml,
    parse_clause,
    parse_constituent,
    parse_sentence,
    parse_token,
)

SAMPLE_SENTENCE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<chapter lang="he" id="GEN 1">
   <sentence id="GEN 1:1">
      <p><milestone unit="verse" id="GEN 1:1">GEN 1:1</milestone> בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים</p>
      <wg class="cl" rule="PP-V-S" head="true">
         <wg role="pp" class="pp" rule="PrepNp">
            <w xml:id="o010010010011" strongnumberx="0871a" greekstrong="1722" greek="ἐν" gloss="in" pos="preposition" morph="R">בְּ</w>
            <w xml:id="o010010010012" strongnumberx="7225" greekstrong="746" greek="ἀρξῇ" gloss="beginning" pos="noun" morph="Ncfsa" sdbh="006653001001000" coredomain="168" lexdomain="002001001042">רֵאשִׁ֖ית</w>
         </wg>
         <w xml:id="o010010010021" class="verb" role="v" strongnumberx="1254" greekstrong="4160" greek="ἐποίησεν" gloss="created" pos="verb" morph="Vqp3ms" sdbh="001156001002000" coredomain="028 055">בָּרָ֣א</w>
         <w xml:id="o010010010031" class="noun" role="s" strongnumberx="0430" greekstrong="2316" greek="θεὸς" gloss="God" pos="noun" morph="Ncmpa" sdbh="000397001003000" coredomain="055">אֱלֹהִ֑ים</w>
      </wg>
   </sentence>
</chapter>
"""


class MaculaNormalizationTests(unittest.TestCase):
    def test_normalize_hebrew_strongs(self):
        self.assertEqual(normalize_hebrew_strongs("0871a"), "H871")
        self.assertEqual(normalize_hebrew_strongs("7225"), "H7225")
        self.assertEqual(normalize_hebrew_strongs("H0430"), "H430")
        self.assertEqual(normalize_hebrew_strongs("0001"), "H1")
        self.assertEqual(normalize_hebrew_strongs("H8674"), "H8674")
        self.assertIsNone(normalize_hebrew_strongs(""))
        self.assertIsNone(normalize_hebrew_strongs(None))
        self.assertIsNone(normalize_hebrew_strongs("abc"))
        self.assertIsNone(normalize_hebrew_strongs("0"))
        self.assertIsNone(normalize_hebrew_strongs("8675"))  # out of canonical range

    def test_normalize_greek_strongs(self):
        self.assertEqual(normalize_greek_strongs("1722"), "G1722")
        self.assertEqual(normalize_greek_strongs("746"), "G746")
        self.assertEqual(normalize_greek_strongs("0746"), "G746")
        self.assertEqual(normalize_greek_strongs("G2316"), "G2316")
        self.assertEqual(normalize_greek_strongs("G5624"), "G5624")
        self.assertIsNone(normalize_greek_strongs(""))
        self.assertIsNone(normalize_greek_strongs(None))
        self.assertIsNone(normalize_greek_strongs("abc"))
        self.assertIsNone(normalize_greek_strongs("0"))
        self.assertIsNone(normalize_greek_strongs("5625"))  # out of canonical range

    def test_map_mt_to_canonical_verse(self):
        # Normal 1:1 verse
        self.assertEqual(map_mt_to_canonical_verse(1, 1), ("Gen.1.1", "GEN 1:1"))
        self.assertEqual(map_mt_to_canonical_verse(31, 54), ("Gen.31.54", "GEN 31:54"))
        # Gen 31:55 / Gen 32:1 MT versification divergence
        self.assertEqual(map_mt_to_canonical_verse(32, 1), ("Gen.31.55", "GEN 32:1"))
        self.assertEqual(map_mt_to_canonical_verse(32, 2), ("Gen.32.1", "GEN 32:2"))
        self.assertEqual(map_mt_to_canonical_verse(32, 33), ("Gen.32.32", "GEN 32:33"))


class MaculaXmlParserTests(unittest.TestCase):
    def setUp(self):
        self.root = ET.fromstring(SAMPLE_SENTENCE_XML)

    def _find_w(self, target_id: str) -> ET.Element:
        for w in self.root.findall(".//w"):
            wid = w.attrib.get("{http://www.w3.org/XML/1998/namespace}id", w.attrib.get("xml:id", w.attrib.get("id")))
            if wid == target_id:
                return w
        raise AssertionError(f"Token {target_id} not found")

    def test_parse_token(self):
        w = self._find_w("o010010010012")
        tok = parse_token(w, default_role="pp")
        self.assertEqual(tok.id, "o010010010012")
        self.assertEqual(tok.text, "רֵאשִׁ֖ית")
        self.assertEqual(tok.strongs, "H7225")
        self.assertEqual(tok.lxx_strongs, "G746")
        self.assertEqual(tok.lxx, "ἀρξῇ")
        self.assertEqual(tok.gloss, "beginning")
        self.assertEqual(tok.sdbh, "006653001001000")
        self.assertEqual(tok.core_domains, ["168"])
        self.assertEqual(tok.lex_domains, ["002001001042"])

    def test_parse_constituent_phrase(self):
        wg = self.root.find(".//wg[@class='pp']")
        self.assertIsNotNone(wg)
        const = parse_constituent(wg)
        self.assertEqual(const.role, "pp")
        self.assertEqual(const.role_label, "prepositional_phrase")
        self.assertEqual(const.phrase_class, "pp")
        self.assertEqual(const.rule, "PrepNp")
        self.assertEqual(const.text, "בְּ רֵאשִׁ֖ית")
        self.assertEqual(len(const.tokens), 2)
        self.assertEqual(const.tokens[0].strongs, "H871")
        self.assertEqual(const.tokens[1].strongs, "H7225")

    def test_parse_constituent_word(self):
        w = self._find_w("o010010010021")
        const = parse_constituent(w)
        self.assertEqual(const.role, "v")
        self.assertEqual(const.role_label, "predicate_verb")
        self.assertEqual(const.text, "בָּרָ֣א")
        self.assertEqual(len(const.tokens), 1)
        self.assertEqual(const.tokens[0].strongs, "H1254")
        self.assertEqual(const.tokens[0].lxx_strongs, "G4160")

    def test_parse_clause(self):
        cl = self.root.find(".//wg[@class='cl']")
        self.assertIsNotNone(cl)
        clause_rec = parse_clause(cl)
        self.assertEqual(clause_rec.rule, "PP-V-S")
        self.assertEqual(len(clause_rec.constituents), 3)
        self.assertEqual(clause_rec.constituents[0].role, "pp")
        self.assertEqual(clause_rec.constituents[1].role, "v")
        self.assertEqual(clause_rec.constituents[2].role, "s")

    def test_parse_sentence(self):
        s = self.root.find(".//sentence")
        self.assertIsNotNone(s)
        verse_rec = parse_sentence(s, chapter=1, canonical_versification=True)
        self.assertEqual(verse_rec.verse_id, "Gen.1.1")
        self.assertEqual(verse_rec.mt_id, "GEN 1:1")
        self.assertEqual(verse_rec.chapter, 1)
        self.assertEqual(verse_rec.verse_num, 1)
        self.assertIn("בְּרֵאשִׁ֖ית", verse_rec.text)
        self.assertEqual(len(verse_rec.clauses), 1)

    def test_parse_chapter_xml_real_file(self):
        path = Path("data/macula-hebrew/01-Gen-001-lowfat.xml")
        if not path.exists():
            self.skipTest("Raw Macula Hebrew source not present")
        verses = parse_chapter_xml(path, chapter=1)
        self.assertEqual(len(verses), 31)
        self.assertEqual(verses[0].verse_id, "Gen.1.1")
        self.assertEqual(verses[-1].verse_id, "Gen.1.31")


class MaculaMultiBookExtractTests(unittest.TestCase):
    """Tests for Whole-OT book normalization, versification, and chapter parsing."""

    def test_resolve_osis_book(self):
        from search.macula.extract import resolve_osis_book
        self.assertEqual(resolve_osis_book("genesis"), "Gen")
        self.assertEqual(resolve_osis_book("GEN"), "Gen")
        self.assertEqual(resolve_osis_book("1 samuel"), "1Sam")
        self.assertEqual(resolve_osis_book("II Kings"), "2Kgs")
        self.assertEqual(resolve_osis_book("psalms"), "Ps")
        self.assertEqual(resolve_osis_book("psalm"), "Ps")
        self.assertEqual(resolve_osis_book("song of solomon"), "Song")
        self.assertEqual(resolve_osis_book("dan"), "Dan")
        self.assertEqual(resolve_osis_book("malachi"), "Mal")

    def test_map_mt_to_canonical_verse_multi_book(self):
        # Malachi 3:19 MT -> Malachi 4:1 KJV
        self.assertEqual(
            map_mt_to_canonical_verse(3, 19, book_code="MAL"),
            ("Mal.4.1", "MAL 3:19"),
        )
        self.assertEqual(
            map_mt_to_canonical_verse(3, 24, book_code="MAL"),
            ("Mal.4.6", "MAL 3:24"),
        )
        # Daniel 8:14 identity
        self.assertEqual(
            map_mt_to_canonical_verse(8, 14, book_code="DAN"),
            ("Dan.8.14", "DAN 8:14"),
        )
        # Psalm 3 (shifted title)
        self.assertEqual(
            map_mt_to_canonical_verse(3, 1, book_code="PSA"),
            ("Ps.3.0", "PSA 3:1"),
        )
        self.assertEqual(
            map_mt_to_canonical_verse(3, 2, book_code="PSA"),
            ("Ps.3.1", "PSA 3:2"),
        )
        # Psalm 51 (2-verse title)
        self.assertEqual(
            map_mt_to_canonical_verse(51, 1, book_code="PSA"),
            ("Ps.51.0", "PSA 51:1"),
        )
        self.assertEqual(
            map_mt_to_canonical_verse(51, 2, book_code="PSA"),
            ("Ps.51.0b", "PSA 51:2"),
        )
        self.assertEqual(
            map_mt_to_canonical_verse(51, 3, book_code="PSA"),
            ("Ps.51.1", "PSA 51:3"),
        )

    def test_parse_real_files_isaiah_daniel_malachi(self):
        isa_path = Path("data/macula-hebrew/23-Isa-053-lowfat.xml")
        dan_path = Path("data/macula-hebrew/27-Dan-008-lowfat.xml")
        mal_path = Path("data/macula-hebrew/39-Mal-003-lowfat.xml")

        if not isa_path.exists():
            self.skipTest("Whole-OT Macula XMLs not present")

        isa_verses = parse_chapter_xml(isa_path)
        self.assertEqual(len(isa_verses), 12)
        self.assertEqual(isa_verses[0].verse_id, "Isa.53.1")
        self.assertEqual(isa_verses[4].verse_id, "Isa.53.5")
        self.assertIn("מְחֹלָ֣ל", isa_verses[4].text)

        dan_verses = parse_chapter_xml(dan_path)
        self.assertEqual(len(dan_verses), 27)
        dan8_14 = next(v for v in dan_verses if v.verse_id == "Dan.8.14")
        self.assertEqual(dan8_14.mt_id, "DAN 8:14")
        self.assertGreaterEqual(len(dan8_14.clauses), 3)

        mal_verses = parse_chapter_xml(mal_path)
        self.assertEqual(len(mal_verses), 24)
        mal4_6 = mal_verses[-1]
        self.assertEqual(mal4_6.verse_id, "Mal.4.6")
        self.assertEqual(mal4_6.mt_id, "MAL 3:24")

    def test_iter_chapter_files(self):
        from search.macula.extract import iter_chapter_files
        xml_dir = Path("data/macula-hebrew")
        if not xml_dir.exists():
            self.skipTest("data/macula-hebrew not present")

        all_files = iter_chapter_files(xml_dir)
        self.assertEqual(len(all_files), 929)

        dan_files = iter_chapter_files(xml_dir, books=["Dan"])
        self.assertEqual(len(dan_files), 12)

        gen_files = iter_chapter_files(xml_dir, books=["Genesis"])
        self.assertEqual(len(gen_files), 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
