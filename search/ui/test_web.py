"""Integration tests for the local-first web server (ADR-024, Phase 1 host).

Spawns the stdlib server on an ephemeral port with a real StudyService and
exercises the static + JSON API surface end-to-end over HTTP (no Mocks —
deterministic fixtures come from ensure_test_databases()).
"""

from __future__ import annotations

import dataclasses
import enum
import json
import re
import threading
import unittest
import urllib.error
import urllib.request

from search.resource import get_web_dir
from search.ui import web_server
from search.ui.study_service import StudyService


def setUpModule():
    from search.testutil import ensure_test_databases
    ensure_test_databases()


class WebServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.study = StudyService()
        cls.server = web_server.create_server(cls.study, port=0)  # ephemeral port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, _port = cls.server.server_address
        cls.base = f"http://{host}:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.study.close()

    def _get(self, path: str):
        with urllib.request.urlopen(self.base + path, timeout=15) as res:
            return res.status, res.read(), res.headers.get_content_type()

    def _get_json(self, path: str) -> dict:
        status, body, ctype = self._get(path)
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        return json.loads(body)

    # ---- static surface -------------------------------------------------

    def test_index_served(self) -> None:
        status, body, ctype = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b"Adventist Bible Study Tool", body)
        self.assertIn(b"setup-wizard-modal", body)
        self.assertIn(b"open-wizard-btn", body)
        self.assertIn(b"theme-select", body)
        self.assertIn(b"zebra-toggle", body)
        self.assertIn(b"auto-update-toggle", body)
        self.assertIn(b"pane-divider", body)
        self.assertIn(b"role=\"separator\"", body)
        self.assertIn(b"aria-controls=\"reading-pane\"", body)
        self.assertIn(b"focus-mode-btn", body)
        self.assertIn(b"exit-zoom-btn", body)
        self.assertIn(b"tab-list", body)
        self.assertIn(b'data-tab="prophecy"', body)
        self.assertIn(b'id="panel-prophecy"', body)
        self.assertIn(b'id="prophecy-search-input"', body)
        self.assertIn(b'id="prophecy-category-filter"', body)
        self.assertIn(b'id="prophecy-book-filter"', body)

    def test_pane_divider_accessibility_attributes(self) -> None:
        status, body, _ = self._get("/")
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        self.assertIn('id="pane-divider"', html)
        self.assertIn('role="separator"', html)
        self.assertIn('tabindex="0"', html)
        self.assertIn('aria-orientation="vertical"', html)
        self.assertIn('aria-valuenow="65"', html)
        self.assertIn('aria-valuemin="40"', html)
        self.assertIn('aria-valuemax="80"', html)
        self.assertIn('aria-controls="reading-pane"', html)
        self.assertIn('class="divider-handle"', html)

    def test_distraction_free_and_accessibility_controls(self) -> None:
        status, body, _ = self._get("/")
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        self.assertIn('id="focus-mode-btn"', html)
        self.assertIn('aria-pressed="false"', html)
        self.assertIn('id="exit-zoom-btn"', html)
        self.assertIn('class="tab-exit-zoom"', html)
        self.assertIn('id="panel-languages"', html)
        self.assertIn('id="panel-translations"', html)
        self.assertIn('id="panel-prophecy"', html)

    def test_prophecy_workstation_dom_integration(self) -> None:
        status, body, _ = self._get("/")
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        # Tab and container
        self.assertIn('data-tab="prophecy"', html)
        self.assertIn('id="panel-prophecy"', html)
        # Search & filters
        self.assertIn('id="prophecy-search-input"', html)
        self.assertIn('id="prophecy-category-filter"', html)
        self.assertIn('id="prophecy-book-filter"', html)
        self.assertIn('id="prophecy-reset-btn"', html)
        self.assertIn('id="prophecy-zoom-btn"', html)
        self.assertIn('id="prophecy-count-badge"', html)
        # Category options
        self.assertIn('<option value="Time">Time</option>', html)
        self.assertIn('<option value="Entities">Entities</option>', html)
        self.assertIn('<option value="Elements">Elements</option>', html)
        # Book options
        self.assertIn('<option value="Daniel">Daniel</option>', html)
        self.assertIn('<option value="Revelation">Revelation</option>', html)
        self.assertIn('<option value="Zechariah">Zechariah</option>', html)
        # Table landmarks and columns
        self.assertIn('class="prophecy-table"', html)
        self.assertIn('aria-label="Master Prophetic Key Lexicon"', html)
        self.assertIn('class="prophecy-th-symbol"', html)
        self.assertIn('class="prophecy-th-meaning"', html)
        self.assertIn('class="prophecy-th-proofs"', html)
        self.assertIn('class="prophecy-th-anchors"', html)
        self.assertIn('id="prophecy-table-body"', html)
        self.assertIn('id="prophecy-empty-state"', html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('id="prophecy-in-context"', html)

    def test_sanctuary_workstation_dom_integration(self) -> None:
        status, body, _ = self._get("/")
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        # Tab and panel
        self.assertIn('data-tab="sanctuary"', html)
        self.assertIn('id="panel-sanctuary"', html)
        # Stepper buttons and slider
        self.assertIn('class="sanctuary-toolbar"', html)
        self.assertIn('class="btn-tool sanctuary-stage-btn active" data-stage="0"', html)
        self.assertIn('data-stage="1"', html)
        self.assertIn('data-stage="2"', html)
        self.assertIn('data-stage="3"', html)
        self.assertIn('data-stage="4"', html)
        self.assertIn('id="sanctuary-stage-slider"', html)
        self.assertIn('id="sanctuary-stage-badge"', html)
        self.assertIn('id="sanctuary-zoom-btn"', html)
        # Blueprint SVG container & Legend
        self.assertIn('class="sanctuary-blueprint-container"', html)
        self.assertIn('id="sanctuary-svg"', html)
        self.assertIn('class="sanctuary-blueprint-legend"', html)
        self.assertIn('swatch-courtyard', html)
        self.assertIn('swatch-holy', html)
        self.assertIn('swatch-most-holy', html)
        # Detail Card & In-context banner
        self.assertIn('id="sanctuary-detail-card"', html)
        self.assertIn('id="sanctuary-in-context"', html)

    def test_commentary_workstation_dom_integration(self) -> None:
        status, body, _ = self._get("/")
        self.assertEqual(status, 200)
        html = body.decode("utf-8")
        # Tab and panel
        self.assertIn('id="tab-commentary"', html)
        self.assertIn('id="panel-commentary"', html)
        # Listing view and controls
        self.assertIn('id="commentary-list-view"', html)
        self.assertIn('id="commentary-chips-list"', html)
        self.assertIn('id="commentary-zoom-btn"', html)
        self.assertIn('id="commentary-count-badge"', html)
        # Reader drawer view and navigation controls
        self.assertIn('id="commentary-reader-view"', html)
        self.assertIn('id="commentary-reader-content"', html)
        self.assertIn('id="commentary-back-btn"', html)
        self.assertIn('id="commentary-prev-ch-btn"', html)
        self.assertIn('id="commentary-next-ch-btn"', html)
        self.assertIn('id="commentary-reader-zoom-btn"', html)

    def test_head_request_supported(self) -> None:
        req = urllib.request.Request(self.base + "/", method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as res:
            self.assertEqual(res.status, 200)
            self.assertIn("text/html", res.headers.get_content_type())
            self.assertEqual(res.read(), b"")
            self.assertGreater(int(res.headers.get("Content-Length", 0)), 0)

    def test_stylesheet_served(self) -> None:
        status, body, ctype = self._get("/styles.css")
        self.assertEqual(status, 200)
        self.assertIn("text/css", ctype)
        self.assertIn(b"--bg", body)  # design tokens present
        self.assertIn(b"--verse-text", body)
        self.assertIn(b"--verse-num", body)
        self.assertIn(b"--strongs-code", body)
        self.assertIn(b"--zebra-bg", body)
        self.assertIn(b"zebra-shading", body)
        self.assertIn(b"theme-select-input", body)
        self.assertIn(b"wizard-dialog", body)
        self.assertIn(b"btn-setup", body)
        self.assertIn(b"btn-tool", body)
        self.assertIn(b"pane-divider", body)
        self.assertIn(b"col-resize", body)
        self.assertIn(b"--split-percent", body)
        self.assertIn(b"focus-mode", body)
        self.assertIn(b"zoom-side", body)
        self.assertIn(b"tab-exit-zoom", body)
        self.assertIn(b"tab-list", body)
        self.assertIn(b"prefers-reduced-motion", body)
        self.assertIn(b"disclosure-card", body)
        self.assertIn(b"disclosure-summary", body)
        self.assertIn(b"disclosure-arrow", body)
        self.assertIn(b"morph-card", body)
        self.assertIn(b"translation-card", body)
        self.assertIn(b"morph-theological-card", body)
        self.assertIn(b"prophecy-table", body)
        self.assertIn(b"prophecy-toolbar", body)
        self.assertIn(b"category-badge", body)
        self.assertIn(b"prophecy-ref-link", body)
        self.assertIn(b"prophecy-consensus-details", body)
        self.assertIn(b"tab-count-badge", body)
        self.assertIn(b"verse-prophecy-badges", body)
        self.assertIn(b"prophecy-verse-badge", body)
        self.assertIn(b"prophecy-inline-card", body)
        self.assertIn(b"btn-goto-lexicon", body)
        self.assertIn(b"sanctuary-toolbar", body)
        self.assertIn(b"sanctuary-stage-btn", body)
        self.assertIn(b"sanctuary-stage-badge", body)
        self.assertIn(b"sanctuary-blueprint-container", body)
        self.assertIn(b"sanctuary-svg", body)
        self.assertIn(b"sanctuary-station-node", body)
        self.assertIn(b"station-halo", body)
        self.assertIn(b"furniture-bronze", body)
        self.assertIn(b"furniture-gold", body)
        self.assertIn(b"sanctuary-detail-card", body)
        self.assertIn(b"sanctuary-reality-callout", body)
        self.assertIn(b"sanctuary-ref-chip", body)
        self.assertIn(b"sanctuary-in-context", body)
        self.assertIn(b"sanctuary-context-tag", body)
        self.assertIn(b"verse-sanctuary-badges", body)
        self.assertIn(b"sanctuary-verse-badge", body)
        # Commentary styling assertions (WP-033 Phase 1 & 4)
        self.assertIn(b"commentary-toolbar", body)
        self.assertIn(b"commentary-chip", body)
        self.assertIn(b"chip-book-tag", body)
        self.assertIn(b"chip-read-btn", body)
        self.assertIn(b"commentary-reader-view", body)
        self.assertIn(b"reader-paragraph", body)
        self.assertIn(b"target-paragraph", body)
        self.assertIn(b"reader-page-break", body)
        self.assertIn(b"reader-page-label", body)

    def test_appjs_served(self) -> None:
        status, body, ctype = self._get("/app.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", ctype)
        self.assertIn(b"verifyBundle", body)
        self.assertIn(b"openWizard", body)
        self.assertIn(b"initPaneResizer", body)
        self.assertIn(b"initFocusAndZoomModes", body)
        self.assertIn(b"initZebraShading", body)
        self.assertIn(b"zebra_shading", body)
        self.assertIn(b"verse-text", body)
        self.assertIn(b"strongs-tag", body)
        self.assertIn(b"startsWith", body)
        self.assertIn(b"renderLanguages", body)
        self.assertIn(b"disclosure-card", body)
        self.assertIn(b"morph-card", body)
        self.assertIn(b"toggle-all-languages", body)
        self.assertIn(b"toggle-all-translations", body)
        self.assertIn(b"toggleFocusMode", body)
        self.assertIn(b"toggleSideZoom", body)
        self.assertIn(b"restoreStatusBar", body)
        self.assertIn(b"isInputFocused", body)
        self.assertIn(b"split_percent", body)
        self.assertIn(b"setPointerCapture", body)
        self.assertIn(b"switchTab", body)
        self.assertIn(b"data-strongs", body)
        self.assertIn(b"data-verse", body)
        self.assertIn(b"openNuance", body)
        self.assertIn(b"loadPropheticLexicon", body)
        self.assertIn(b"renderProphecyTable", body)
        self.assertIn(b"filterProphecySymbols", body)
        self.assertIn(b"updateProphecyInContext", body)
        self.assertIn(b"initProphecyWorkstation", body)
        self.assertIn(b"createRefChip", body)
        self.assertIn(b"currentProphecyPassageRef", body)
        self.assertIn(b"tab-count-badge", body)
        self.assertIn(b"toggleProphecyInlineCard", body)
        self.assertIn(b"verse-prophecy-badges", body)
        self.assertIn(b"prophecy-verse-badge", body)
        self.assertIn(b"prophecy-inline-card", body)
        self.assertIn(b"highlightProphecySymbolInLexicon", body)
        self.assertIn(b"loadSanctuaryData", body)
        self.assertIn(b"renderSanctuaryBlueprint", body)
        self.assertIn(b"setPlanOfSalvationStage", body)
        self.assertIn(b"selectSanctuaryStation", body)
        self.assertIn(b"renderSanctuaryStageDetail", body)
        self.assertIn(b"renderSanctuaryOverview", body)
        self.assertIn(b"initSanctuaryWorkstation", body)
        self.assertIn(b"SANCTUARY_STATION_ORDER", body)
        self.assertIn(b"createSanctuaryRefChip", body)
        self.assertIn(b"sanctuaryInContext", body)
        self.assertIn(b"verse-sanctuary-badges", body)
        self.assertIn(b"sanctuary-verse-badge", body)
        self.assertIn(b"updateSanctuaryInContext", body)
        self.assertIn(b"currentSanctuaryPassageRef", body)
        self.assertIn(b"sanctuaryRequestId", body)
        self.assertIn(b"clearSanctuaryInContext", body)
        # Commentary JS assertions (WP-033 Phase 1 & 4)
        self.assertIn(b"commentaryPanel", body)
        self.assertIn(b"tabCommentary", body)
        self.assertIn(b"clearCommentary", body)
        self.assertIn(b"updateCommentary", body)
        self.assertIn(b"renderCommentaryChips", body)
        self.assertIn(b"openCommentaryChapterByToken", body)
        self.assertIn(b"openCommentaryChapter", body)
        self.assertIn(b"renderCommentaryChapter", body)
        self.assertIn(b"initCommentaryWorkstation", body)
        self.assertIn(b"commentaryReaderZoomBtn", body)
        self.assertIn(b"reader-page-break", body)

    def test_traversal_blocked(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/../data/PROVENANCE.md")
        self.assertEqual(ctx.exception.code, 403)

    # ---- API surface ----------------------------------------------------

    def test_health_ok(self) -> None:
        data = self._get_json("/api/health")
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "0.1.0")
        self.assertEqual(data["default_theme"], "sepia")
        self.assertEqual(data["nuance_url"], "/api/nuance")
        self.assertEqual(data["prophetic_url"], "/api/prophetic")
        self.assertEqual(data["sanctuary_url"], "/api/sanctuary")
        self.assertEqual(data["commentary_url"], "/api/commentary")
        self.assertIn("verify_bundle_url", data)
        self.assertIn("egw_available", data)
        theme_ids = [t["id"] for t in data["themes"]]
        # Web-native themes are selectable (S4)...
        self.assertIn("sepia", theme_ids)
        self.assertIn("light", theme_ids)
        self.assertIn("dark", theme_ids)
        # ...and the 7 TUI palettes are ported (ADR-018 parity).
        for tid in ("transparent", "dracula", "catppuccin_mocha", "tokyo_night",
                    "nord", "gruvbox_dark", "solarized_dark"):
            self.assertIn(tid, theme_ids)

    def test_verify_bundle_endpoint(self) -> None:
        data = self._get_json("/api/verify-bundle")
        self.assertIn("status", data)
        self.assertIn("valid", data)
        self.assertIn("errors", data)
        self.assertIn("data_dir", data)

    def test_verify_bundle_endpoint_exception_handled(self) -> None:
        from unittest.mock import patch
        with patch("search.ui.web_server.verify_data_bundle", side_effect=PermissionError("Access denied")):
            data = self._get_json("/api/verify-bundle")
            self.assertEqual(data["status"], "error")
            self.assertFalse(data["valid"])
            self.assertTrue(any("Access denied" in err for err in data["errors"]))

    def test_passage_returns_verses(self) -> None:
        data = self._get_json("/api/passage?ref=Genesis%201:1")
        self.assertEqual(data["ref"], "Genesis 1:1")
        self.assertGreaterEqual(len(data["verses"]), 1)
        verse = data["verses"][0]
        self.assertIn("text", verse)
        self.assertEqual(verse["chapter"], 1)
        self.assertTrue(verse["text"].strip())

    def test_passage_multi_verse_range(self) -> None:
        data = self._get_json("/api/passage?ref=Genesis%201:1-3")
        self.assertEqual(len(data["verses"]), 3)

    def test_passage_bad_ref_is_400(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/passage?ref=NotABook%2099")
        self.assertEqual(ctx.exception.code, 400)

    def test_passage_missing_ref_is_400(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/passage")
        self.assertEqual(ctx.exception.code, 400)

    def test_passage_eager_keeps_per_verse_enrichment(self) -> None:
        # M2 regression: eager=1 must attach enrichment to each verse, never
        # collapse it onto the passage (which would drop earlier verses).
        data = self._get_json("/api/passage?ref=Genesis%201:1-3&eager=1")
        for field in ("semantic_frames", "verbal_nuances",
                      "discourse_markers", "ot_citations"):
            self.assertNotIn(field, data)  # never collapsed onto passage
            for verse in data["verses"]:
                # per-verse fields are lists when present (absent is legal)
                if field in verse:
                    self.assertIsInstance(verse[field], list)
        # Genesis 1:1 has a semantic frame; it must ride on verse 1, not the
        # passage, and verse 1:3's must not overwrite it.
        v1 = next(v for v in data["verses"] if v["osis"] == "Gen.1.1")
        self.assertIn("semantic_frames", v1)
        self.assertTrue(v1["semantic_frames"])
        v3 = next(v for v in data["verses"] if v["osis"] == "Gen.1.3")
        self.assertIn("semantic_frames", v3)
        self.assertTrue(v3["semantic_frames"])

    def test_passage_payload_excludes_egw(self) -> None:
        # Copyright boundary (ADR-002/023): the web API stays copyright-light.
        # The TUI/CLI render EGW against the local egw.db; the wire does not.
        data = self._get_json("/api/passage?ref=Genesis%201:1&eager=1")
        self.assertNotIn("egw_correlations", data)
        for verse in data["verses"]:
            self.assertNotIn("egw_correlations", verse)

    def test_passage_eager_verbal_nuances_structure(self) -> None:
        # Progressive disclosure: eager=1 attaches verbal_nuances used by Languages tab (OT & NT)
        data_ot = self._get_json("/api/passage?ref=Genesis%201:1&eager=1")
        v_ot = data_ot["verses"][0]
        self.assertIn("verbal_nuances", v_ot)
        nuances_ot = v_ot["verbal_nuances"]
        self.assertTrue(len(nuances_ot) >= 1)
        n_ot = nuances_ot[0]
        self.assertEqual(n_ot["language"], "hebrew")
        self.assertIn("stem_or_tense", n_ot)
        self.assertIn("theological_nuance", n_ot)
        self.assertEqual(n_ot["strongs"], "H1254")

        data_nt = self._get_json("/api/passage?ref=John%201:1&eager=1")
        v_nt = data_nt["verses"][0]
        self.assertIn("verbal_nuances", v_nt)
        nuances_nt = v_nt["verbal_nuances"]
        self.assertTrue(len(nuances_nt) >= 1)
        n_nt = nuances_nt[0]
        self.assertEqual(n_nt["language"], "greek")
        self.assertIn("stem_or_tense", n_nt)
        self.assertIn("theological_nuance", n_nt)

    def test_translations_endpoint(self) -> None:
        data = self._get_json("/api/translations")
        self.assertTrue(len(data["translations"]) >= 1)

    def test_nuance_endpoint_by_morph_hebrew(self) -> None:
        data = self._get_json("/api/nuance?morph=Vqp3ms&strongs=H1254")
        self.assertEqual(data["status"], "ok")
        nuance = data["nuance"]
        self.assertEqual(nuance["language"], "hebrew")
        self.assertEqual(nuance["stem_or_tense"], "Qal (Simple Active)")
        self.assertEqual(nuance["strongs"], "H1254")

    def test_nuance_endpoint_by_morph_greek(self) -> None:
        data = self._get_json("/api/nuance?morph=V-AMI-3S&lang=greek")
        self.assertEqual(data["status"], "ok")
        nuance = data["nuance"]
        self.assertEqual(nuance["language"], "greek")
        self.assertIn("Aorist Middle", nuance["stem_or_tense"])

    def test_nuance_endpoint_by_ref_genesis(self) -> None:
        data = self._get_json("/api/nuance?ref=Genesis%201:1")
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(data["count"], 1)
        nuances = data["nuances"]
        self.assertTrue(any(n["strongs"] == "H1254" for n in nuances))

    def test_nuance_endpoint_by_ref_and_strongs(self) -> None:
        data = self._get_json("/api/nuance?ref=John%201:1&strongs=G1510")
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(data["count"], 1)
        for n in data["nuances"]:
            self.assertEqual(n["strongs"], "G1510")
            self.assertEqual(n["language"], "greek")
            self.assertIn("Imperfect Active", n["stem_or_tense"])

    def test_nuance_endpoint_romans(self) -> None:
        data = self._get_json("/api/nuance?ref=Romans%203:24")
        self.assertEqual(data["status"], "ok")
        nuances = data["nuances"]
        dikai = next((n for n in nuances if n["strongs"] == "G1344"), None)
        self.assertIsNotNone(dikai)
        self.assertIn("Present Passive", dikai["stem_or_tense"])
        self.assertIn("Divine Verdict", dikai["theological_nuance"])

    def test_nuance_endpoint_missing_params_is_400(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/nuance")
        self.assertEqual(ctx.exception.code, 400)

    def test_nuance_endpoint_bad_morph_is_400(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/nuance?morph=InvalidMorph")
        self.assertEqual(ctx.exception.code, 400)

    def test_prophetic_endpoint_all_symbols(self) -> None:
        data = self._get_json("/api/prophetic")
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(data["count"], 25)
        self.assertEqual(set(data["categories"]), {"Time", "Entities", "Elements"})
        self.assertEqual(len(data["symbols"]), data["count"])

    def test_prophetic_endpoint_category_filter(self) -> None:
        data = self._get_json("/api/prophetic?category=Time")
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(data["count"], 4)
        for sym in data["symbols"]:
            self.assertEqual(sym["category"], "Time")

    def test_prophetic_endpoint_by_id(self) -> None:
        data = self._get_json("/api/prophetic?id=day-year-principle")
        self.assertEqual(data["status"], "ok")
        sym = data["symbol"]
        self.assertEqual(sym["id"], "day-year-principle")
        self.assertEqual(sym["symbol"], "Day")
        self.assertIn("Numbers 14:34", sym["proof_texts"])

    def test_prophetic_endpoint_by_id_not_found_is_404(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/prophetic?id=fake-symbol")
        self.assertEqual(ctx.exception.code, 404)

    def test_prophetic_endpoint_by_ref_daniel(self) -> None:
        data = self._get_json("/api/prophetic?ref=Daniel%207:25")
        self.assertEqual(data["status"], "ok")
        ids = [s["id"] for s in data["symbols"]]
        self.assertIn("day-year-principle", ids)
        self.assertIn("time-times-half", ids)

    def test_prophetic_endpoint_by_ref_revelation(self) -> None:
        data = self._get_json("/api/prophetic?ref=Revelation%2012:1")
        self.assertEqual(data["status"], "ok")
        ids = [s["id"] for s in data["symbols"]]
        self.assertIn("pure-woman", ids)
        self.assertIn("sun-and-moon", ids)
        self.assertIn("crowns", ids)

    def test_prophetic_endpoint_include_proofs_filtering(self) -> None:
        data_with_proofs = self._get_json("/api/prophetic?ref=Numbers%2014:34&include_proofs=1")
        self.assertEqual(data_with_proofs["status"], "ok")
        self.assertTrue(data_with_proofs["include_proofs"])
        ids_with = [s["id"] for s in data_with_proofs["symbols"]]
        self.assertIn("day-year-principle", ids_with)

        data_anchors_only = self._get_json("/api/prophetic?ref=Numbers%2014:34&include_proofs=0")
        self.assertEqual(data_anchors_only["status"], "ok")
        self.assertFalse(data_anchors_only["include_proofs"])
        ids_without = [s["id"] for s in data_anchors_only["symbols"]]
        self.assertNotIn("day-year-principle", ids_without)

    def test_passage_endpoint_in_context_prophetic_symbols(self) -> None:
        """Acceptance Criterion: In-context symbols in Daniel 7 and Revelation 12 link directly to defining scriptures."""
        # Daniel 7:25 contains Day-Year principle and 1260 Days
        data_dan = self._get_json("/api/passage?ref=Dan+7:25")
        self.assertEqual(data_dan["book_name"], "Daniel")
        self.assertEqual(len(data_dan["verses"]), 1)
        v_dan = data_dan["verses"][0]
        self.assertIn("prophetic_symbols", v_dan)
        dan_sym_ids = [s["id"] for s in v_dan["prophetic_symbols"]]
        self.assertIn("day-year-principle", dan_sym_ids)
        self.assertIn("time-times-half", dan_sym_ids)
        day_sym = next(s for s in v_dan["prophetic_symbols"] if s["id"] == "day-year-principle")
        self.assertTrue(day_sym["is_anchor"])
        self.assertIn("Numbers 14:34", day_sym["proof_texts"])
        self.assertIn("Ezekiel 4:6", day_sym["proof_texts"])

        # Revelation 12:1 contains Woman, Stars, Sun and Moon, Crowns
        data_rev = self._get_json("/api/passage?ref=Rev+12:1")
        self.assertEqual(data_rev["book_name"], "Revelation")
        v_rev = data_rev["verses"][0]
        self.assertIn("prophetic_symbols", v_rev)
        rev_sym_ids = {s["id"] for s in v_rev["prophetic_symbols"]}
        self.assertIn("pure-woman", rev_sym_ids)
        self.assertIn("sun-and-moon", rev_sym_ids)
        self.assertIn("stars", rev_sym_ids)
        self.assertIn("crowns", rev_sym_ids)
        woman_sym = next(s for s in v_rev["prophetic_symbols"] if s["id"] == "pure-woman")
        self.assertIn("Jeremiah 6:2", woman_sym["proof_texts"])
        self.assertIn("2 Corinthians 11:2", woman_sym["proof_texts"])

        # Ezekiel 4:6 recognizes Day as a defining proof text
        data_eze = self._get_json("/api/passage?ref=Ezekiel+4:6")
        v_eze = data_eze["verses"][0]
        self.assertIn("prophetic_symbols", v_eze)
        eze_day = next((s for s in v_eze["prophetic_symbols"] if s["id"] == "day-year-principle"), None)
        self.assertIsNotNone(eze_day)
        self.assertFalse(eze_day["is_anchor"])
        self.assertTrue(eze_day["is_proof"])

    def test_sanctuary_endpoint_full_dataset(self) -> None:
        data = self._get_json("/api/sanctuary")
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(len(data["compartments"]), 3)
        self.assertEqual(len(data["stations"]), 6)
        self.assertEqual(len(data["services"]), 2)
        self.assertEqual(len(data["plan_of_salvation"]), 4)

    def test_sanctuary_endpoint_by_station(self) -> None:
        data = self._get_json("/api/sanctuary?station=ark_of_the_covenant")
        self.assertEqual(data["status"], "ok")
        st = data["station"]
        self.assertEqual(st["id"], "ark_of_the_covenant")
        self.assertEqual(st["compartment"], "most_holy_place")
        self.assertIn("H727", st["strongs"])

    def test_sanctuary_endpoint_unknown_station_is_404(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/sanctuary?station=golden_calf")
        self.assertEqual(ctx.exception.code, 404)

    def test_sanctuary_endpoint_by_compartment(self) -> None:
        data = self._get_json("/api/sanctuary?compartment=courtyard")
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["count"], 2)
        station_ids = {s["id"] for s in data["stations"]}
        self.assertEqual(station_ids, {"altar_of_burnt_offering", "laver"})

    def test_sanctuary_endpoint_by_ref(self) -> None:
        data = self._get_json("/api/sanctuary?ref=Hebrews%209:4")
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(data["count"], 1)
        station_ids = [s["id"] for s in data["stations"]]
        self.assertIn("ark_of_the_covenant", station_ids)

    def test_passage_endpoint_in_context_sanctuary_stations(self) -> None:
        # Exodus 27:1 (Altar of Burnt Offering OT institution)
        data_exod = self._get_json("/api/passage?ref=Exodus+27:1")
        v_exod = data_exod["verses"][0]
        self.assertIn("sanctuary_stations", v_exod)
        altar_st = next((s for s in v_exod["sanctuary_stations"] if s["id"] == "altar_of_burnt_offering"), None)
        self.assertIsNotNone(altar_st)
        self.assertTrue(altar_st["is_ot_institution"])

        # Hebrews 13:10 (Altar of Burnt Offering NT fulfillment)
        data_heb = self._get_json("/api/passage?ref=Hebrews+13:10")
        v_heb = data_heb["verses"][0]
        self.assertIn("sanctuary_stations", v_heb)
        altar_heb = next((s for s in v_heb["sanctuary_stations"] if s["id"] == "altar_of_burnt_offering"), None)
        self.assertIsNotNone(altar_heb)
        self.assertTrue(altar_heb["is_nt_fulfillment"])

        # Revelation 11:19 (Ark of the Covenant heavenly fulfillment)
        data_rev = self._get_json("/api/passage?ref=Revelation+11:19")
        v_rev = data_rev["verses"][0]
        self.assertIn("sanctuary_stations", v_rev)
        ark_rev = next((s for s in v_rev["sanctuary_stations"] if s["id"] == "ark_of_the_covenant"), None)
        self.assertIsNotNone(ark_rev)
        self.assertTrue(ark_rev["is_nt_fulfillment"])

    def test_sanctuary_endpoint_invalid_passage_is_400(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/sanctuary?ref=InvalidBook+99:99")
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_endpoint_is_404(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/nope")
        self.assertEqual(ctx.exception.code, 404)

    def test_commentary_endpoint_missing_params_is_400(self) -> None:
        has_egw = self.study.egw_db is not None and self.study.egw_db.exists()
        if not has_egw:
            data = self._get_json("/api/commentary")
            self.assertEqual(data["status"], "ok")
            self.assertFalse(data["available"])
            return
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/commentary")
        self.assertEqual(ctx.exception.code, 400)

    def test_commentary_endpoint_by_ref(self) -> None:
        data = self._get_json("/api/commentary?ref=Gen+1")
        self.assertEqual(data["status"], "ok")
        has_egw = self.study.egw_db is not None and self.study.egw_db.exists()
        if has_egw:
            self.assertTrue(data["available"])
            self.assertIn("correlations", data)
            self.assertGreaterEqual(len(data["correlations"]), 1)
            first = data["correlations"][0]
            self.assertIn("token", first)
            self.assertIn("book_code", first)
            self.assertIn("chapter_title", first)
            self.assertIn("teaser", first)
        else:
            self.assertFalse(data["available"])

    def test_commentary_endpoint_by_token(self) -> None:
        has_egw = self.study.egw_db is not None and self.study.egw_db.exists()
        if not has_egw:
            self.skipTest("egw.db not installed")
        data = self._get_json("/api/commentary?token=PP.44.1")
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["available"])
        self.assertEqual(data["book_code"], "PP")
        self.assertEqual(data["target_id"], "PP.44.1")
        self.assertIn("paragraphs", data)
        self.assertGreaterEqual(len(data["paragraphs"]), 1)
        target = next((p for p in data["paragraphs"] if p.get("is_target")), None)
        self.assertIsNotNone(target)
        self.assertEqual(target["id"], "PP.44.1")

    def test_commentary_endpoint_by_book_and_chapter(self) -> None:
        has_egw = self.study.egw_db is not None and self.study.egw_db.exists()
        if not has_egw:
            self.skipTest("egw.db not installed")
        data = self._get_json("/api/commentary?book=PP&chapter=8")
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["available"])
        self.assertEqual(data["book_code"], "PP")
        self.assertEqual(data["chapter_num"], 8)
        self.assertIn("paragraphs", data)
        self.assertGreaterEqual(len(data["paragraphs"]), 1)

    def test_commentary_endpoint_bad_token_is_404(self) -> None:
        has_egw = self.study.egw_db is not None and self.study.egw_db.exists()
        if not has_egw:
            self.skipTest("egw.db not installed")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/commentary?token=PP.99999.1")
        self.assertEqual(ctx.exception.code, 404)

    def test_commentary_endpoint_bad_chapter_is_404(self) -> None:
        has_egw = self.study.egw_db is not None and self.study.egw_db.exists()
        if not has_egw:
            self.skipTest("egw.db not installed")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/commentary?book=PP&chapter=99999")
        self.assertEqual(ctx.exception.code, 404)

    def test_egw_route_does_not_exist(self) -> None:
        # No dedicated raw EGW route (parity: the 404 covers any /api/egw attempt).
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/egw")
        self.assertEqual(ctx.exception.code, 404)


class WebServerModuleTests(unittest.TestCase):
    """Checks that don't need a live server."""

    def test_jsonable_handles_dataclass_tree(self) -> None:
        # A nested dataclass standing in for a VerseStudy/PassageStudy.
        @dataclasses.dataclass
        class Leaf:
            text: str
            n: int

        @dataclasses.dataclass
        class Branch:
            name: str
            leaf: Leaf

        doc = web_server._jsonable(Branch("x", Leaf("hello", 7)))
        self.assertEqual(doc, {"name": "x", "leaf": {"text": "hello", "n": 7}})

    def test_jsonable_raises_on_unknown_type(self) -> None:
        # S1: fail-fast — an unrecognised type must raise, not str()-fallback.
        with self.assertRaises(TypeError):
            web_server._jsonable(object())

    def test_jsonable_handles_enum(self) -> None:
        # Real model enums (DiscourseMarker.category, OTCitation.citation_type)
        # are (str, Enum) subclasses; serialize via .value to plain str.
        class Kind(str, enum.Enum):
            ALLUSION = "allusion"
            QUOTATION = "quotation"
        self.assertEqual(web_server._jsonable(Kind.ALLUSION), "allusion")
        self.assertIsInstance(web_server._jsonable(Kind.QUOTATION), str)

    def test_wcag_aaa_contrast_ratios(self) -> None:
        """Verifies that core typography tokens meet WCAG AAA (>= 7.0:1) on surface substrates."""
        css_path = get_web_dir() / "styles.css"
        css_text = css_path.read_text(encoding="utf-8")

        def parse_theme_tokens(css: str, selector_pattern: str) -> dict[str, str]:
            pattern = selector_pattern + r"[^\{]*\{([^}]+)\}"
            m = re.search(pattern, css)
            self.assertIsNotNone(m, f"Selector {selector_pattern} not found in styles.css")
            body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.DOTALL)
            tokens = {}
            for line in body.split(";"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    tokens[k.strip()] = v.strip()
            return tokens

        def srgb_to_lin(c: int) -> float:
            c_norm = c / 255.0
            return c_norm / 12.92 if c_norm <= 0.04045 else ((c_norm + 0.055) / 1.055) ** 2.4

        def luminance(hex_str: str) -> float:
            hex_clean = hex_str.strip().lstrip("#")
            if len(hex_clean) == 3:
                hex_clean = "".join(c * 2 for c in hex_clean)
            r, g, b = [int(hex_clean[i:i + 2], 16) for i in (0, 2, 4)]
            return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)

        def contrast(c1: str, c2: str) -> float:
            l1, l2 = luminance(c1), luminance(c2)
            if l1 < l2:
                l1, l2 = l2, l1
            return (l1 + 0.05) / (l2 + 0.05)

        themes_to_check = [
            (r'\[data-theme="sepia"\]', "Sepia (Divinity Hall Desk)"),
            (r'\[data-theme="light"\]', "Light Paper"),
            (r'\[data-theme="dark"\]', "Dark Walnut (Divinity Hall Night)"),
        ]

        # AAA normal text threshold per WCAG 2.1 is 7.0:1
        AAA_THRESHOLD = 7.0

        for sel, theme_name in themes_to_check:
            tokens = parse_theme_tokens(css_text, sel)
            self.assertIn("--surface", tokens, f"--surface missing in {theme_name}")
            surface = tokens["--surface"]

            for token_key in ["--ink", "--verse-text", "--verse-num", "--strongs-code", "--primary", "--accent", "--ink-muted"]:
                self.assertIn(token_key, tokens, f"{token_key} missing in {theme_name}")
                color = tokens[token_key]
                cr = contrast(surface, color)
                self.assertGreaterEqual(
                    cr,
                    AAA_THRESHOLD,
                    f"WCAG AAA failure in {theme_name}: {token_key} ({color}) on {surface} has contrast {cr:.2f}:1 (< {AAA_THRESHOLD}:1)",
                )

    def test_styles_anti_slop_charter_compliance(self) -> None:
        """Verifies that styles.css obeys the 10 bans in ADR-025 Anti-Slop Charter."""
        css_text = (get_web_dir() / "styles.css").read_text(encoding="utf-8")

        # Ban 3: No frosted glass / backdrop-filter blur
        self.assertNotIn("backdrop-filter: blur", css_text)
        self.assertNotIn("-webkit-backdrop-filter: blur", css_text)

        # Ban 6: No magic sparkle icons
        self.assertNotIn("✨", css_text)

        # Ban 7: No bouncy spring physics
        self.assertNotIn("cubic-bezier(0.68, -0.55", css_text)
        self.assertNotIn("cubic-bezier(0.175, 0.885, 0.32, 1.275)", css_text)

        # Must support prefers-reduced-motion
        self.assertIn("@media (prefers-reduced-motion: reduce)", css_text)


if __name__ == "__main__":
    unittest.main()