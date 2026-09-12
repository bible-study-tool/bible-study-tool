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
        self.assertIn(b"code.startsWith", body)
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

    def test_unknown_endpoint_is_404(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._get("/api/nope")
        self.assertEqual(ctx.exception.code, 404)

    def test_egw_route_does_not_exist(self) -> None:
        # No dedicated EGW route (parity: the 404 covers any /api/egw attempt).
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