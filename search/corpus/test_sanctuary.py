"""Unit and tripwire validation tests for Sanctuary Typology Blueprint (WP-032 Phase 1 & 2).

Verifies:
1. Deterministic JSON schema and integrity of data/sanctuary_schema.json.
2. Canonical resolution in BibleDB for all OT passages, NT fulfillments, service scriptures, and plan anchors.
3. Lexical validity of Strong's concordance codes against lexicons/strongs-lexicon.json.
4. Querying and filtering capabilities of SanctuaryEngine.
5. Verse and passage overlap detection for Leviticus 16, Hebrews 9, Revelation 11, etc.
"""

from __future__ import annotations

import json
import unittest

from search.corpus.extract_kjv import BibleDB
from search.corpus.sanctuary import (
    VALID_COMPARTMENTS,
    SanctuaryEngine,
    get_sanctuary_engine,
)
from search.resource import data_path


class SanctuaryDatasetValidationTests(unittest.TestCase):
    """Integrity and tripwire tests for data/sanctuary_schema.json."""

    @classmethod
    def setUpClass(cls):
        cls.path = data_path("sanctuary_schema.json")
        cls.assertTrue(cls.path.is_file(), f"Dataset not found at {cls.path}")
        with open(cls.path, "r", encoding="utf-8") as f:
            cls.raw = json.load(f)
        cls.bible = BibleDB()
        with open("lexicons/strongs-lexicon.json", "r", encoding="utf-8") as f:
            cls.strongs_lex = json.load(f)

    @classmethod
    def tearDownClass(cls):
        cls.bible.close()

    def test_schema_top_level(self):
        self.assertIn("version", self.raw)
        self.assertIn("title", self.raw)
        self.assertIn("description", self.raw)
        self.assertIn("compartments", self.raw)
        self.assertIn("stations", self.raw)
        self.assertIn("services", self.raw)
        self.assertIn("plan_of_salvation", self.raw)

    def test_compartment_structure(self):
        comps = self.raw["compartments"]
        self.assertEqual(len(comps), 3)
        comp_ids = {c["id"] for c in comps}
        self.assertEqual(comp_ids, VALID_COMPARTMENTS)

        for c in comps:
            self.assertTrue(c["name"].strip())
            self.assertTrue(c["hebrew_name"].strip())
            self.assertTrue(c["significance"].strip())
            self.assertTrue(c["spiritual_reality"].strip())
            self.assertGreaterEqual(len(c["scriptures"]), 1)

    def test_station_inventory(self):
        stations = self.raw["stations"]
        self.assertEqual(len(stations), 6, "Must contain all 6 primary articles of sanctuary furniture")

        expected_ids = {
            "altar_of_burnt_offering",
            "laver",
            "golden_lampstand",
            "table_of_shewbread",
            "altar_of_incense",
            "ark_of_the_covenant",
        }
        self.assertEqual({s["id"] for s in stations}, expected_ids)

        for s in stations:
            self.assertIn(s["compartment"], VALID_COMPARTMENTS)
            self.assertTrue(s["name"].strip())
            self.assertTrue(s["common_name"].strip())
            self.assertTrue(s["theological_meaning"].strip())
            self.assertTrue(s["spiritual_reality"].strip())
            self.assertTrue(s["priestly_service"].strip())
            self.assertTrue(s["sda_consensus"].strip())
            self.assertGreaterEqual(len(s["ot_passages"]), 1)
            self.assertGreaterEqual(len(s["nt_fulfillment"]), 1)
            self.assertGreaterEqual(len(s["strongs"]), 1)
            self.assertIn("svg_coords", s)

    def test_services_structure(self):
        services = self.raw["services"]
        self.assertEqual(len(services), 2)
        srv_ids = {s["id"] for s in services}
        self.assertEqual(srv_ids, {"daily_service", "yearly_service"})

        for srv in services:
            self.assertTrue(srv["name"].strip())
            self.assertTrue(srv["focus"].strip())
            self.assertTrue(srv["process"].strip())
            self.assertTrue(srv["christological_antitype"].strip())
            self.assertGreaterEqual(len(srv["scriptures"]), 2)

    def test_plan_of_salvation_structure(self):
        phases = self.raw["plan_of_salvation"]
        self.assertEqual(len(phases), 4)
        for p in phases:
            self.assertGreaterEqual(p["stage_number"], 1)
            self.assertTrue(p["title"].strip())
            self.assertTrue(p["historical_event"].strip())
            self.assertTrue(p["theological_significance"].strip())
            self.assertGreaterEqual(len(p["biblical_anchors"]), 1)

    def test_strongs_codes_validity(self):
        """Tripwire: Every Strong's code in sanctuary stations must exist in strongs-lexicon."""
        for s in self.raw["stations"]:
            for code in s["strongs"]:
                if code.startswith("H"):
                    self.assertIn(
                        code,
                        self.strongs_lex["hebrew"],
                        f"Hebrew Strong's code {code} in {s['id']} not found in strongs-lexicon",
                    )
                else:
                    self.assertIn(
                        code,
                        self.strongs_lex["greek"],
                        f"Greek Strong's code {code} in {s['id']} not found in strongs-lexicon",
                    )

    def test_all_ot_passages_resolve_in_bibledb(self):
        """Tripwire: Every OT passage in stations must resolve to actual verses in BibleDB."""
        missing = []
        for s in self.raw["stations"]:
            for ref in s["ot_passages"]:
                verses = self.bible.get_passage(ref)
                if not verses:
                    missing.append((s["id"], "ot_passage", ref))
        self.assertEqual(missing, [], f"Unresolvable OT passages found: {missing}")

    def test_all_nt_fulfillments_resolve_in_bibledb(self):
        """Tripwire: Every NT fulfillment passage in stations must resolve to actual verses in BibleDB."""
        missing = []
        for s in self.raw["stations"]:
            for ref in s["nt_fulfillment"]:
                verses = self.bible.get_passage(ref)
                if not verses:
                    missing.append((s["id"], "nt_fulfillment", ref))
        self.assertEqual(missing, [], f"Unresolvable NT fulfillment passages found: {missing}")

    def test_all_service_scriptures_resolve_in_bibledb(self):
        """Tripwire: Every service scripture must resolve in BibleDB."""
        missing = []
        for srv in self.raw["services"]:
            for ref in srv["scriptures"]:
                verses = self.bible.get_passage(ref)
                if not verses:
                    missing.append((srv["id"], "service_scripture", ref))
        self.assertEqual(missing, [], f"Unresolvable service scriptures found: {missing}")

    def test_all_plan_anchors_resolve_in_bibledb(self):
        """Tripwire: Every Plan of Salvation biblical anchor must resolve in BibleDB."""
        missing = []
        for p in self.raw["plan_of_salvation"]:
            for ref in p["biblical_anchors"]:
                verses = self.bible.get_passage(ref)
                if not verses:
                    missing.append((p["id"], "plan_anchor", ref))
        self.assertEqual(missing, [], f"Unresolvable plan anchors found: {missing}")


class SanctuaryEngineTests(unittest.TestCase):
    """Unit tests for SanctuaryEngine querying, filtering, and verse resolution."""

    def setUp(self):
        self.engine = SanctuaryEngine()

    def test_singleton_getter(self):
        e1 = get_sanctuary_engine()
        e2 = get_sanctuary_engine()
        self.assertIs(e1, e2)

    def test_get_compartments(self):
        comps = self.engine.list_compartments()
        self.assertEqual(len(comps), 3)
        c_court = self.engine.get_compartment("courtyard")
        self.assertIsNotNone(c_court)
        self.assertEqual(c_court.name, "The Courtyard")
        self.assertEqual(c_court.hebrew_name, "חָצֵר")

    def test_get_station_by_id(self):
        st = self.engine.get_station("altar_of_burnt_offering")
        self.assertIsNotNone(st)
        self.assertEqual(st.common_name, "Brazen Altar")
        self.assertEqual(st.compartment, "courtyard")
        self.assertIn("H4196", st.strongs)
        self.assertIn("Exodus 27:1-8", st.ot_passages)
        self.assertIn("Hebrews 13:10-12", st.nt_fulfillment)

    def test_get_nonexistent_station_returns_none(self):
        self.assertIsNone(self.engine.get_station("nonexistent_vessel"))

    def test_list_stations_filtered_by_compartment(self):
        holy_stations = self.engine.list_stations(compartment="holy_place")
        ids = {s.id for s in holy_stations}
        self.assertEqual(ids, {"golden_lampstand", "table_of_shewbread", "altar_of_incense"})

    def test_list_stations_query_search(self):
        results = self.engine.list_stations(query="Mercy Seat")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "ark_of_the_covenant")

        bread_res = self.engine.list_stations(query="Bread")
        self.assertEqual(len(bread_res), 1)
        self.assertEqual(bread_res[0].id, "table_of_shewbread")

    def test_list_services(self):
        srvs = self.engine.list_services()
        self.assertEqual(len(srvs), 2)
        daily = self.engine.get_service("daily_service")
        self.assertIsNotNone(daily)
        self.assertEqual(daily.transliteration, "Tamid")

    def test_list_plan_phases(self):
        phases = self.engine.list_plan_phases()
        self.assertEqual(len(phases), 4)
        stage3 = next(p for p in phases if p.stage_number == 3)
        self.assertEqual(stage3.id, "investigative_judgment")
        self.assertIn("Daniel 8:14", stage3.biblical_anchors)

    def test_verse_overlap_exodus_altar(self):
        # Exodus 27:1 is part of Exodus 27:1-8 (Altar of Burnt Offering)
        stations = self.engine.get_annotated_stations_for_verse("Exod", 27, 1)
        self.assertTrue(any(s.id == "altar_of_burnt_offering" and s.is_ot_institution for s in stations))

    def test_verse_overlap_hebrews_fulfillment(self):
        # Hebrews 13:10 is in Hebrews 13:10-12 (Brazen Altar fulfillment)
        stations = self.engine.get_annotated_stations_for_verse("Heb", 13, 10)
        self.assertTrue(any(s.id == "altar_of_burnt_offering" and s.is_nt_fulfillment for s in stations))

    def test_verse_overlap_revelation_ark(self):
        # Revelation 11:19 reveals the Ark of His Testament in heaven
        stations = self.engine.get_annotated_stations_for_verse("Rev", 11, 19)
        self.assertTrue(any(s.id == "ark_of_the_covenant" and s.is_nt_fulfillment for s in stations))

    def test_verse_overlap_non_sanctuary_verse_returns_empty(self):
        # Genesis 1:1 does not overlap any sanctuary furniture station
        stations = self.engine.get_annotated_stations_for_verse("Gen", 1, 1)
        self.assertEqual(stations, [])

    def test_passage_overlap_invalid_ref_raises(self):
        # Malformed passage reference raises ValueError (fail fast)
        with self.assertRaises(ValueError):
            self.engine.get_annotated_stations_for_passage("InvalidBook 99:99")

    def test_passage_overlap_leviticus_16(self):
        # Leviticus 16:14 (Ark / Mercy seat sprinkling)
        stations = self.engine.get_annotated_stations_for_passage("Leviticus 16:14")
        self.assertTrue(any(s.id == "ark_of_the_covenant" for s in stations))

    def test_get_all_data_payload(self):
        payload = self.engine.get_all_data()
        self.assertEqual(payload["version"], "1.0.0")
        self.assertEqual(len(payload["compartments"]), 3)
        self.assertEqual(len(payload["stations"]), 6)
        self.assertEqual(len(payload["services"]), 2)
        self.assertEqual(len(payload["plan_of_salvation"]), 4)


if __name__ == "__main__":
    unittest.main()
