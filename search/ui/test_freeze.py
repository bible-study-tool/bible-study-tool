"""Unit and regression tests for frozen (PyInstaller/standalone) execution and Textual compatibility (WP-029 Step 1.3)."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from search.resource import (
    data_path,
    get_bundle_root,
    get_web_dir,
    is_frozen,
    resource_path,
)
from search.ui.app import BibleStudyApp
from search.ui.study_service import StudyService
from search.ui.web import build_web_parser, main


class FrozenResourceResolutionTests(unittest.TestCase):
    """Test resource resolution under simulated PyInstaller/frozen execution."""

    def test_frozen_detection_and_bundle_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_path = Path(tmpdir).resolve()
            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "_MEIPASS", str(bundle_path), create=True):
                self.assertTrue(is_frozen())
                self.assertEqual(get_bundle_root(), bundle_path)

    def test_frozen_web_dir_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_path = Path(tmpdir).resolve()
            bundled_web = bundle_path / "web"
            bundled_web.mkdir(parents=True)
            (bundled_web / "index.html").write_text("<!DOCTYPE html><html></html>", encoding="utf-8")

            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "_MEIPASS", str(bundle_path), create=True):
                web_dir = get_web_dir()
                self.assertEqual(web_dir, bundled_web)
                self.assertTrue((web_dir / "index.html").exists())

    def test_frozen_resource_path_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_path = Path(tmpdir).resolve()
            fixture = bundle_path / "search" / "fixtures" / "versemap.json.gz"
            fixture.parent.mkdir(parents=True)
            fixture.write_text("{}", encoding="utf-8")

            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "_MEIPASS", str(bundle_path), create=True):
                resolved = resource_path("search/fixtures/versemap.json.gz")
                self.assertEqual(resolved, fixture)
                self.assertTrue(resolved.exists())

    def test_frozen_data_path_sidecar_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir).resolve()
            sidecar_db = app_dir / "data" / "bible.db"
            sidecar_db.parent.mkdir(parents=True)
            sidecar_db.write_text("sqlite", encoding="utf-8")

            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "executable", str(app_dir / "bible-study"), create=True):
                resolved = data_path("bible.db")
                self.assertEqual(resolved, sidecar_db)
                self.assertTrue(resolved.exists())

    def test_frozen_data_path_skips_empty_bundle_data(self):
        """Verify that get_data_dir() prefers a candidate with bible.db over an empty bundle data dir."""
        from search.resource import get_data_dir
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bundle_dir = tmp / "bundle"
            bundle_data = bundle_dir / "data"
            bundle_data.mkdir(parents=True)
            (bundle_data / "prophetic_lexicon.json").write_text("{}", encoding="utf-8")

            repo_dir = tmp / "repo"
            repo_data = repo_dir / "data"
            repo_data.mkdir(parents=True)
            (repo_data / "bible.db").write_text("sqlite", encoding="utf-8")

            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "_MEIPASS", str(bundle_dir), create=True), \
                 patch.dict(os.environ, {"BIBLE_STUDY_REPO_ROOT": str(repo_dir)}):
                self.assertEqual(get_data_dir(), repo_data)

    def test_frozen_lexicons_path_skips_empty_bundle_lexicons(self):
        """Verify that get_lexicons_dir() prefers a candidate with *.json over an empty bundle lexicons dir."""
        from search.resource import get_lexicons_dir
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bundle_dir = tmp / "bundle"
            bundle_lex = bundle_dir / "lexicons"
            bundle_lex.mkdir(parents=True)

            repo_dir = tmp / "repo"
            repo_lex = repo_dir / "lexicons"
            repo_lex.mkdir(parents=True)
            (repo_lex / "strongs-greek.json").write_text("{}", encoding="utf-8")

            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "_MEIPASS", str(bundle_dir), create=True), \
                 patch.dict(os.environ, {"BIBLE_STUDY_REPO_ROOT": str(repo_dir)}):
                self.assertEqual(get_lexicons_dir(), repo_lex)


class TextualFrozenCompatibilityTests(unittest.TestCase):
    """Test Textual driver resolution and headless app lifecycle in frozen mode."""

    def setUp(self):
        self.service = StudyService()

    def tearDown(self):
        self.service.close()

    def test_native_driver_resolution_when_frozen(self):
        with patch.object(sys, "frozen", True, create=True):
            app = BibleStudyApp(service=self.service)
            driver_cls = app.get_driver_class()
            expected_driver = "WindowsDriver" if sys.platform == "win32" else "LinuxDriver"
            self.assertEqual(driver_cls.__name__, expected_driver)

    def test_textual_web_driver_resolution_when_frozen(self):
        """Verify that textual-web / remote driver (TEXTUAL_DRIVER) resolves cleanly when frozen."""
        import textual.constants
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(textual.constants, "DRIVER", "textual.drivers.web_driver:WebDriver"):
            app = BibleStudyApp(service=self.service)
            driver_cls = app.get_driver_class()
            self.assertEqual(driver_cls.__name__, "WebDriver")

    def test_headless_driver_resolution_when_frozen(self):
        import textual.constants
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(textual.constants, "DRIVER", "textual.drivers.headless_driver:HeadlessDriver"):
            app = BibleStudyApp(service=self.service)
            driver_cls = app.get_driver_class()
            self.assertEqual(driver_cls.__name__, "HeadlessDriver")

    def test_app_lifecycle_headless_run_when_frozen(self):
        """Confirm Textual mounts all widgets and completes pilot run without raising when frozen."""
        async def _run():
            with patch.object(sys, "frozen", True, create=True):
                app = BibleStudyApp(service=self.service, initial_ref="Gen 1:1", initial_theme="transparent")
                async with app.run_test() as pilot:
                    self.assertEqual(app.title, "Adventist Bible Study Workstation")
                    self.assertEqual(app.current_ref, "Gen 1:1")
                    await pilot.pause()

        asyncio.run(_run())


class FrozenLauncherDispatchTests(unittest.TestCase):
    """Test launcher argument parsing and dispatch under frozen execution."""

    def test_web_parser_in_frozen_mode(self):
        with patch.object(sys, "frozen", True, create=True):
            parser = build_web_parser()
            args = parser.parse_args(["--tui", "--theme", "dracula"])
            self.assertTrue(args.tui)
            self.assertEqual(args.theme, "dracula")

    @patch("search.ui.web.launch_interactive_tui")
    def test_frozen_main_tui_dispatch(self, mock_launch_tui):
        with patch.object(sys, "frozen", True, create=True):
            code = main(["--tui", "--passage", "Gen 1:1"])
            self.assertEqual(code, 0)
            mock_launch_tui.assert_called_once()

    @patch("search.ui.web.execute_subcommand", return_value=0)
    def test_frozen_main_cli_dispatch(self, mock_execute_subcommand):
        with patch.object(sys, "frozen", True, create=True):
            code = main(["read", "Gen 1:1", "--json"])
            self.assertEqual(code, 0)
            mock_execute_subcommand.assert_called_once()


if __name__ == "__main__":
    unittest.main()
