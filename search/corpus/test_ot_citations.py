"""Unit tests for the deterministic Old Testament Citations engine (WP-026)."""

import unittest
from search.corpus.ot_citations import (
    CitationType,
    OTCitation,
    lookup_ot_citations_for_nt_verse,
    lookup_nt_citations_for_ot_verse,
    lookup_citations_for_verse,
    get_passage_ot_citations_batch,
    format_citation_badge,
    render_citation_card,
)


class OTCitationsTests(unittest.TestCase):
    """Test suite for OT citation anchors in NT Epistles and Gospels."""

    def test_romans_habakkuk_justification_by_faith(self):
        cits = lookup_ot_citations_for_nt_verse("Rom.1.17")
        self.assertEqual(len(cits), 1)
        cit = cits[0]
        self.assertEqual(cit.ot_osis, "Hab.2.4")
        self.assertEqual(cit.ot_book, "Habakkuk")
        self.assertEqual(cit.citation_type, CitationType.DIRECT_QUOTE)
        self.assertIn("καθὼς γέγραπται", cit.introductory_formula)
        self.assertIn("just shall live by faith", cit.nt_text_snippet)
        self.assertEqual(cit.ot_hebrew, "וְצַדִּיק בֶּאֱמוּנָתוֹ יִחְיֶה")
        self.assertIn("Habakkuk", cit.theological_significance)

    def test_bidirectional_lookup_habakkuk(self):
        # Habakkuk 2:4 is quoted in Rom 1:17, Gal 3:11, and Heb 10:38
        nt_cits = lookup_nt_citations_for_ot_verse("Hab.2.4")
        nt_osises = {c.nt_osis for c in nt_cits}
        self.assertIn("Rom.1.17", nt_osises)
        self.assertIn("Gal.3.11", nt_osises)
        self.assertIn("Heb.10.38", nt_osises)

    def test_bidirectional_lookup_genesis_15_6(self):
        # Gen 15:6 is quoted in Rom 4:3 and Gal 3:6
        cits = lookup_nt_citations_for_ot_verse("Gen.15.6")
        nt_osises = {c.nt_osis for c in cits}
        self.assertIn("Rom.4.3", nt_osises)
        self.assertIn("Gal.3.6", nt_osises)

    def test_lookup_citations_for_verse_unified(self):
        # From NT side
        cits_nt = lookup_citations_for_verse("Rom.4.3")
        self.assertEqual(len(cits_nt), 1)
        self.assertEqual(cits_nt[0].ot_osis, "Gen.15.6")

        # From OT side
        cits_ot = lookup_citations_for_verse("Gen.15.6")
        self.assertTrue(len(cits_ot) >= 2)

        # Empty or non-matching
        self.assertEqual(lookup_citations_for_verse(""), [])
        self.assertEqual(lookup_citations_for_verse("3John.1.1"), [])

    def test_hebrews_sanctuary_and_sabbath_citations(self):
        # Heb 4:4 quotes Gen 2:2 (Sabbath creation rest)
        cits_sabbath = lookup_ot_citations_for_nt_verse("Heb.4.4")
        self.assertEqual(len(cits_sabbath), 1)
        self.assertEqual(cits_sabbath[0].ot_osis, "Gen.2.2")

        # Heb 5:6 quotes Ps 110:4 (Melchizedek)
        cits_melch = lookup_ot_citations_for_nt_verse("Heb.5.6")
        self.assertEqual(len(cits_melch), 1)
        self.assertEqual(cits_melch[0].ot_osis, "Ps.110.4")

        # Heb 8:8 quotes Jer 31:31 (New Covenant)
        cits_nc = lookup_ot_citations_for_nt_verse("Heb.8.8")
        self.assertEqual(len(cits_nc), 1)
        self.assertEqual(cits_nc[0].ot_osis, "Jer.31.31")

    def test_galatians_tree_curse(self):
        # Gal 3:13 quotes Deut 21:23
        cits = lookup_ot_citations_for_nt_verse("Gal.3.13")
        self.assertEqual(len(cits), 1)
        cit = cits[0]
        self.assertEqual(cit.ot_osis, "Deut.21.23")
        self.assertIn("tree", cit.nt_text_snippet)
        self.assertIn("Substitutionary Atonement", cit.covenant_theme)

    def test_passage_batch_extraction(self):
        # Romans 3 has multiple citations (Ps 51:4, Ps 14:1, etc.)
        batch = get_passage_ot_citations_batch("Rom", 3)
        self.assertIn("Rom.3.4", batch)
        self.assertIn("Rom.3.10", batch)
        self.assertIn("Rom.3.18", batch)
        self.assertIn("Rom.3.20", batch)

    def test_badge_and_card_rendering(self):
        cits = lookup_ot_citations_for_nt_verse("Rom.1.17")
        self.assertTrue(cits)
        cit = cits[0]

        # Badge for NT verse
        badge_nt = format_citation_badge(cit, "Rom.1.17")
        self.assertIn("Habakkuk 2:4", badge_nt)
        self.assertIn("OT Anchor", badge_nt)

        # Badge for OT verse
        badge_ot = format_citation_badge(cit, "Hab.2.4")
        self.assertIn("Romans 1:17", badge_ot)
        self.assertIn("Cited in NT", badge_ot)

        # Card rendering
        card = render_citation_card(cit)
        self.assertIn("SCRIPTURE INTERPRETING SCRIPTURE", card)
        self.assertIn("Habakkuk 2:4", card)
        self.assertIn("WLC Hebrew:", card)
        self.assertIn("Septuagint (LXX):", card)
        self.assertIn("Apostolic Hermeneutic", card)

    def test_genesis_1_creation_citations(self):
        # Gen 1:1 cited in Heb 1:2 and Heb 11:3
        gen1_cits = lookup_nt_citations_for_ot_verse("Gen.1.1")
        self.assertTrue(len(gen1_cits) >= 2)
        gen1_nt_osises = {c.nt_osis for c in gen1_cits}
        self.assertIn("Heb.1.2", gen1_nt_osises)
        self.assertIn("Heb.11.3", gen1_nt_osises)

        # Gen 1:26 cited in Jas 3:9
        gen26_cits = lookup_nt_citations_for_ot_verse("Gen.1.26")
        self.assertTrue(len(gen26_cits) >= 1)
        self.assertEqual(gen26_cits[0].nt_osis, "Jas.3.9")

        # Gen 1:27 cited in Matt 19:4, 1 Cor 11:7, Col 3:10
        gen27_cits = lookup_nt_citations_for_ot_verse("Gen.1.27")
        self.assertTrue(len(gen27_cits) >= 3)
        gen27_nt_osises = {c.nt_osis for c in gen27_cits}
        self.assertIn("Matt.19.4", gen27_nt_osises)
        self.assertIn("1Cor.11.7", gen27_nt_osises)
        self.assertIn("Col.3.10", gen27_nt_osises)

        # Verify bidirectional lookup
        hits_from_ot = lookup_citations_for_verse("Gen.1.1")
        self.assertTrue(len(hits_from_ot) >= 2)
        hits_from_nt = lookup_citations_for_verse("Heb.1.2")
        self.assertTrue(len(hits_from_nt) >= 1)
        self.assertEqual(hits_from_nt[0].ot_osis, "Gen.1.1")

        # Test target_for_verse helper
        target_from_nt, disp_from_nt = hits_from_nt[0].target_for_verse("Heb.1.2")
        self.assertEqual(target_from_nt, "Gen.1.1")
        self.assertEqual(disp_from_nt, "Genesis 1:1")
        target_from_ot, disp_from_ot = hits_from_nt[0].target_for_verse("Gen.1.1")
        self.assertEqual(target_from_ot, "Heb.1.2")
        self.assertEqual(disp_from_ot, "Hebrews 1:2")


if __name__ == "__main__":
    unittest.main()
