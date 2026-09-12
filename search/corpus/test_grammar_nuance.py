"""Unit tests for search.corpus.grammar_nuance (ADR-020, WP-024 Phase 2)."""

from __future__ import annotations

import unittest
from search.corpus.grammar_nuance import (
    GrammarNuance,
    explain_hebrew_morph,
    explain_greek_morph,
    explain_morph,
    explain_verb,
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

    def test_all_seven_hebrew_stems_coverage(self):
        stems = [
            ("Vqp3ms", "Qal"),
            ("VNp3ms", "Niphal"),
            ("Vpp3ms", "Piel"),
            ("VPp3ms", "Pual"),
            ("Vhp3ms", "Hiphil"),
            ("VHp3ms", "Hophal"),
            ("Vtp3ms", "Hitpael"),
        ]
        for code, expected_stem in stems:
            gn = explain_morph(code)
            self.assertIsNotNone(gn, f"Failed to explain {code}")
            self.assertIn(expected_stem, gn.stem_or_tense)

    def test_explain_verb_hebrew_routing(self):
        gn = explain_verb("Vqp3ms", language="hebrew", lemma="בָּרָא", text="בָּרָא", gloss="he created", strongs="H1254")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.language, "hebrew")
        self.assertEqual(gn.stem_or_tense, "Qal (Simple Active)")
        self.assertEqual(gn.strongs, "H1254")
        self.assertIn("Exclusively Divine Initiative", gn.theological_nuance)


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

    def test_all_greek_aspects_and_voices_coverage(self):
        greek_aspects = [
            ("V-AAI-3S", "Aorist", "Active"),
            ("V-AMI-3S", "Aorist", "Middle"),
            ("V-API-3S", "Aorist", "Passive"),
            ("V-PAI-3S", "Present", "Active"),
            ("V-PMI-3S", "Present", "Middle"),
            ("V-RAI-3S", "Perfect", "Active"),
            ("V-RPI-3S", "Perfect", "Passive"),
            ("V-IAI-3S", "Imperfect", "Active"),
        ]
        for code, exp_tense, exp_voice in greek_aspects:
            gn = explain_morph(code)
            self.assertIsNotNone(gn, f"Failed to explain {code}")
            self.assertIn(exp_tense, gn.stem_or_tense)
            self.assertIn(exp_voice, gn.voice)

    def test_explain_verb_greek_routing(self):
        gn = explain_verb("V-AMI-3S", language="greek", lemma="ἐκλέγω", text="ἐξελέξατο", gloss="He chose", strongs="G1586")
        self.assertIsNotNone(gn)
        self.assertEqual(gn.language, "greek")
        self.assertIn("Aorist Middle", gn.stem_or_tense)
        self.assertEqual(gn.strongs, "G1586")
        self.assertIn("Loving Personal Choice", gn.theological_nuance)


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

    def test_acceptance_criteria_passages_genesis_john_romans(self):
        """Verifies WP-031 acceptance criteria: Gen 1:1, John 1:1, and Rom 3:24 verbs produce rich nuance cards."""
        if not self.db.exists():
            self.skipTest("macula.db not initialized")

        # Genesis 1:1 — bārāʾ (H1254) Qal Perfect
        gen_nuances = get_verse_grammar_nuances("Gen.1.1", db=self.db)
        self.assertTrue(len(gen_nuances) >= 1)
        gen_bara = next(n for n in gen_nuances if n.strongs == "H1254")
        self.assertEqual(gen_bara.language, "hebrew")
        self.assertEqual(gen_bara.stem_or_tense, "Qal (Simple Active)")
        self.assertIn("Exclusively Divine Initiative", gen_bara.theological_nuance)

        # John 1:1 — ēn (G1510) Imperfect Active
        john_nuances = get_verse_grammar_nuances("John.1.1", db=self.db)
        self.assertTrue(len(john_nuances) >= 1)
        john_en = next(n for n in john_nuances if n.strongs == "G1510")
        self.assertEqual(john_en.language, "greek")
        self.assertEqual(john_en.stem_or_tense, "Imperfect Active Voice")
        self.assertIn("Past Continuous Aspect", john_en.theological_nuance)

        # Romans 3:24 — dikaioumenoi (G1344) Present Passive
        rom_nuances = get_verse_grammar_nuances("Rom.3.24", db=self.db)
        self.assertTrue(len(rom_nuances) >= 1)
        rom_dikai = next(n for n in rom_nuances if n.strongs == "G1344")
        self.assertEqual(rom_dikai.language, "greek")
        self.assertEqual(rom_dikai.stem_or_tense, "Present Passive Voice (Divine Sovereign Action)")
        self.assertIn("Divine Verdict", rom_dikai.theological_nuance)


if __name__ == "__main__":
    unittest.main()
