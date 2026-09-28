"""Integration tests for the /api/search REST API endpoint (WP-039)."""

from __future__ import annotations

import json
import threading
import unittest
import urllib.parse
import urllib.request

from search.ui import web_server
from search.ui.study_service import StudyService


def setUpModule():
    from search.testutil import ensure_test_databases
    ensure_test_databases()


class SearchApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.study = StudyService()
        cls.server = web_server.create_server(cls.study, port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, _port = cls.server.server_address
        cls.base = f"http://{host}:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.study.close()

    def _get_json(self, path: str) -> dict:
        with urllib.request.urlopen(self.base + path, timeout=15) as res:
            self.assertEqual(res.status, 200)
            self.assertIn("application/json", res.headers.get_content_type())
            return json.loads(res.read())

    def test_health_advertises_search_url(self) -> None:
        payload = self._get_json("/api/health")
        self.assertEqual(payload.get("status"), "ok")
        self.assertEqual(payload.get("search_url"), "/api/search")

    def test_search_empty_query(self) -> None:
        res = self._get_json("/api/search?q=")
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(res.get("total_hits"), 0)
        self.assertEqual(res.get("results"), [])

    def test_search_beginning_returns_hits_and_expansion(self) -> None:
        q = urllib.parse.quote("beginning")
        res = self._get_json(f"/api/search?q={q}&limit=10")
        self.assertEqual(res.get("status"), "ok")
        self.assertGreater(res.get("total_hits", 0), 0)
        self.assertIn("counts", res)
        self.assertGreater(res["counts"]["all"], 0)
        self.assertGreater(res["counts"]["scripture"], 0)

        # Expansion
        exp = res.get("expansion", {})
        self.assertIn("H7225", exp.get("strongs", []))

        # Check results
        results = res.get("results", [])
        self.assertGreater(len(results), 0)
        top = results[0]
        self.assertIn("source", top)
        self.assertIn("id", top)
        self.assertIn("title", top)
        self.assertIn("snippet", top)
        self.assertIn("score", top)

    def test_search_operator_book(self) -> None:
        q = urllib.parse.quote("beginning book:Genesis")
        res = self._get_json(f"/api/search?q={q}&limit=5")
        self.assertEqual(res.get("status"), "ok")
        results = res.get("results", [])
        self.assertGreater(len(results), 0)
        for r in results:
            if r.get("source") == "scripture":
                self.assertEqual(r.get("metadata", {}).get("osis"), "Gen")

    def test_search_source_filtering(self) -> None:
        q = urllib.parse.quote("logos")
        res = self._get_json(f"/api/search?q={q}&sources=original&limit=5")
        self.assertEqual(res.get("status"), "ok")
        results = res.get("results", [])
        self.assertGreater(len(results), 0)
        self.assertTrue(all(r["source"] == "original" for r in results))

    def test_search_reference_detection(self) -> None:
        q = urllib.parse.quote("John 3:16")
        res = self._get_json(f"/api/search?q={q}")
        self.assertEqual(res.get("status"), "ok")
        self.assertTrue(res.get("is_reference"))
        ref_target = res.get("reference_target")
        self.assertIsNotNone(ref_target)
        self.assertEqual(ref_target.get("osis"), "John")
        self.assertEqual(ref_target.get("chapter"), 3)
        self.assertEqual(ref_target.get("start_verse"), 16)

    def test_search_modes_hybrid_keyword(self) -> None:
        q = urllib.parse.quote("beginning")
        res_hyb = self._get_json(f"/api/search?q={q}&mode=hybrid&limit=5")
        self.assertEqual(res_hyb.get("status"), "ok")
        self.assertEqual(res_hyb.get("mode"), "hybrid")

        res_kw = self._get_json(f"/api/search?q={q}&mode=keyword&limit=5")
        self.assertEqual(res_kw.get("status"), "ok")
        self.assertEqual(res_kw.get("mode"), "keyword")


if __name__ == "__main__":
    unittest.main()
