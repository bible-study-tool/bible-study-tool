"""Unit tests for search.corpus.grammar_nuance (ADR-0020, WP-024 Phase 2)."""

from __future__ import annotations

import unittest
from search.corpus.grammar_nuance import (
    GrammarNuance,
    explain_hebrew_morph,
    explain_greek_morph,
    explain_morph,
    get_verse_grammar_nuances,
    get_verse_nuance_by_strongs,
    get_verses_grammar_nuances_batch,
)
from search.macula.db import MaculaSqliteDB


class HebrewGrammarNuanceTests(unittest.TestCase):
    """Test OSHB Hebrew verbal morphology decoding and theological nuances."""

    def test_qal_perfect_creation(self):
        gn = explain_morph("Vqp3ms", lemma="בָּרָא", text="בָּרָא", gloss="he.created", strongs="H1254")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.language, "hebrew")
        self.assertEqual(gn.stem_or_tense, "Qal (Simple Active)")
        self.assertEqual(gn.conjugation_or_mood, "Perfect (Qatal)")
        self.assertEqual(gn.voice, "Active")
        self.assertEqual(gn.strongs, "H1254")
        self.assertIn("Exclusively Divine Initiative", gn.theological_nuance)
        self.assertIn("Qal (Simple Active)", gn.plain_summary)

    def test_piel_sanctification(self):
        gn = explain_morph("Vprmsa", lemma="קָדַשׁ", text="מְקַדֵּשׁ", gloss="sanctifying", strongs="H6942")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.stem_or_tense, "Piel (Intensive / Transformative Active)")
        self.assertEqual(gn.conjugation_or_mood, "Participle Active")
        self.assertIn("Operative Consecration", gn.theological_nuance)

    def test_hiphil_causative(self):
        gn = explain_morph("Vhp3ms", lemma="מָלַךְ", text="הִמְלִיךְ", gloss="he.made.king", strongs="H4427")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.stem_or_tense, "Hiphil (Causative Active)")
        self.assertIn("divine causation and initiative", gn.theological_nuance)

    def test_hitpael_communion(self):
        gn = explain_morph("Vtrmsa", lemma="הָלַךְ", text="מִתְהַלֵּךְ", gloss="walking", strongs="H1980")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.stem_or_tense, "Hitpael (Reflexive / Iterative / Reciprocal)")
        self.assertEqual(gn.voice, "Reflexive / Iterative")
        self.assertIn("Habitual Intimate Communion", gn.theological_nuance)

    def test_hishtaphel_worship(self):
        gn = explain_morph("Vvi1cp", lemma="חוה", text="נִשְׁתַּחֲוֶה", gloss="we.will.worship", strongs="H7812")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.stem_or_tense, "Hishtaphel (Reflexive-Causative / Worship)")
        self.assertIn("Humble Adoration", gn.theological_nuance)

    def test_wayyiqtol_narrative_past(self):
        gn = explain_morph("Vqw3ms", lemma="אָמַר", text="וַיֹּאמֶר", gloss="and.he.said", strongs="H559")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.conjugation_or_mood, "Wayyiqtol (Sequential Imperfect / Narrative Past)")

    def test_aramaic_verb(self):
        gn = explain_morph("ARAM", lemma="קְרָא", text="קְרָא", gloss="he.called")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.language, "aramaic")

    def test_hebrew_prefix_and_suffix_stripping(self):
        # ETCBC HV prefix and pronominal suffix /Sp3ms
        gn = explain_morph("HVqp3ms/Sp3ms", lemma="בָּרָא", text="בְּרָאָם", gloss="he.created.them")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.stem_or_tense, "Qal (Simple Active)")
        self.assertEqual(gn.conjugation_or_mood, "Perfect (Qatal)")
        self.assertEqual(gn.person_number, "3rd Person Masculine Singular")


class GreekGrammarNuanceTests(unittest.TestCase):
    """Test Macula Greek verbal morphology decoding and theological nuances."""

    def test_aorist_middle_loving_choice(self):
        gn = explain_morph("V-AMI-3S", lemma="ἐκλέγω", text="ἐξελέξατο", gloss="He chose", strongs="G1586")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.language, "greek")
        self.assertEqual(gn.stem_or_tense, "Aorist Middle Voice (Personal Interest)")
        self.assertEqual(gn.conjugation_or_mood, "Indicative Mood")
        self.assertEqual(gn.voice, "Middle Voice (Personal Interest)")
        self.assertEqual(gn.person_number, "3rd Person Singular")
        self.assertIn("Loving Personal Choice", gn.theological_nuance)
        self.assertIn("for Himself", gn.theological_nuance)

    def test_perfect_passive_abiding_salvation(self):
        gn = explain_morph("V-RPP-NPM", lemma="σῴζω", text="σεσῳσμένοι", gloss="saved", strongs="G4982")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.stem_or_tense, "Perfect Passive Voice (Divine Sovereign Action)")
        self.assertEqual(gn.conjugation_or_mood, "Participle Mood")
        self.assertEqual(gn.person_number, "Nominative Plural Masculine")
        self.assertIn("Settled, Enduring Salvation", gn.theological_nuance)

    def test_aorist_passive_justification(self):
        gn = explain_morph("V-APP-NPM", lemma="δικαιόω", text="Δικαιωθέντες", gloss="having been justified", strongs="G1344")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.stem_or_tense, "Aorist Passive Voice (Divine Sovereign Action)")
        self.assertIn("Decisive Justification", gn.theological_nuance)

    def test_present_active_continuous_habit(self):
        gn = explain_morph("V-PAI-3S", lemma="ποιέω", text="ποιεῖ", gloss="practices", strongs="G4160")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.stem_or_tense, "Present Active Voice")
        self.assertIn("Habitual Practice", gn.theological_nuance)

    def test_second_aorist_lemma_override(self):
        gn = explain_morph("V-2AMI-3S", lemma="ἐκλέγω", text="ἐξελέξατο", gloss="He chose", strongs="G1586")
        self.assertIsNotNone(gn)
        self.assertIn("Loving Personal Choice", gn.theological_nuance)

    def test_attic_suffix_handling(self):
        gn = explain_morph("V-2AAI-3P-ATT", lemma="γινώσκω", text="ἔγνωσαν", gloss="they knew")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.conjugation_or_mood, "Indicative Mood")


class DatabaseNuanceQueryTests(unittest.TestCase):
    """Test querying verbal nuances directly from Macula SQLite DB."""

    @classmethod
    def setUpClass(cls):
        cls.db = MaculaSqliteDB()

    def test_get_verse_grammar_nuances_hebrew(self):
        if not self.db.exists():
            self.skipTest("macula.db not initialized")
        nuances = get_verse_grammar_nuances("Gen.1.1", db=self.db)
        self.assertTrue(len(nuances) >= 1)
        self.assertEqual(nuances[0].lemma, "בָּרָא")
        self.assertEqual(nuances[0].strongs, "H1254")

    def test_get_verse_grammar_nuances_greek(self):
        if not self.db.exists():
            self.skipTest("macula.db not initialized")
        nuances = get_verse_grammar_nuances("Eph.1.4", db=self.db)
        self.assertTrue(len(nuances) >= 2)
        strongs_found = [n.strongs for n in nuances]
        self.assertIn("G1586", strongs_found)

    def test_get_verse_nuance_by_strongs(self):
        if not self.db.exists():
            self.skipTest("macula.db not initialized")
        by_s = get_verse_nuance_by_strongs("Gen 1:1", db=self.db)
        self.assertIn("H1254", by_s)
        self.assertEqual(len(by_s["H1254"]), 1)
        self.assertEqual(by_s["H1254"][0].lemma, "בָּרָא")

    def test_get_verses_grammar_nuances_batch(self):
        if not self.db.exists():
            self.skipTest("macula.db not initialized")
        res = get_verses_grammar_nuances_batch(["Gen.1.1", "Eph.1.4"], db=self.db)
        self.assertIn("Gen.1.1", res)
        self.assertIn("Eph.1.4", res)
        self.assertTrue(len(res["Gen.1.1"]) >= 1)
        self.assertTrue(len(res["Eph.1.4"]) >= 2)


if __name__ == "__main__":
    unittest.main()
