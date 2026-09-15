"""Unit and integration tests for the unified web launcher and CLI entrypoint (WP-029 Step 1.2)."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from search.ui.web import (
    _launch_browser_in_background,
    build_web_parser,
    main,
    run_web_server,
)


class WebLauncherParserTests(unittest.TestCase):
    """Test argument parsing for search.ui.web."""

    def test_parser_defaults(self):
        parser = build_web_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.subcommand)
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8000)
        self.assertFalse(args.no_browser)
        self.assertFalse(args.tui)
        self.assertFalse(args.curses)
        self.assertEqual(args.theme, "transparent")
        self.assertIsNone(args.passage)

    def test_parser_web_server_flags(self):
        parser = build_web_parser()
        args = parser.parse_args([
            "--host", "0.0.0.0",
            "--port", "8080",
            "--no-browser",
            "--passage", "Rev 14:6-7",
        ])
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 8080)
        self.assertTrue(args.no_browser)
        self.assertEqual(args.passage, "Rev 14:6-7")

    def test_parser_tui_flags(self):
        parser = build_web_parser()
        args = parser.parse_args([
            "--tui",
            "--curses",
            "--theme", "dracula",
            "--passage", "John 1:1",
        ])
        self.assertTrue(args.tui)
        self.assertTrue(args.curses)
        self.assertEqual(args.theme, "dracula")
        self.assertEqual(args.passage, "John 1:1")

    def test_parser_serve_subcommand(self):
        parser = build_web_parser()
        args = parser.parse_args(["serve", "--port", "9090", "--no-browser"])
        self.assertEqual(args.subcommand, "serve")
        self.assertEqual(args.port, 9090)
        self.assertTrue(args.no_browser)

    def test_parser_parent_flags_precedence_over_subcommand(self):
        parser = build_web_parser()
        # Flags specified before subcommand 'serve' should be preserved
        args = parser.parse_args(["--port", "9090", "--host", "10.0.0.1", "serve"])
        self.assertEqual(args.subcommand, "serve")
        self.assertEqual(args.port, 9090)
        self.assertEqual(args.host, "10.0.0.1")

    def test_parser_tui_subcommand(self):
        parser = build_web_parser()
        args = parser.parse_args(["tui", "Gen 1:1", "--theme", "nord"])
        self.assertEqual(args.subcommand, "tui")
        self.assertEqual(args.passage, "Gen 1:1")
        self.assertEqual(args.theme, "nord")

    def test_parser_read_subcommand(self):
        parser = build_web_parser()
        args = parser.parse_args(["read", "John 3:16", "-s", "--json"])
        self.assertEqual(args.subcommand, "read")
        self.assertEqual(args.passage, "John 3:16")
        self.assertTrue(args.strongs)
        self.assertTrue(args.json)


class WebLauncherExecutionTests(unittest.TestCase):
    """Test dispatch and server execution logic in search.ui.web."""

    @patch("search.ui.web.launch_interactive_tui")
    def test_main_tui_flag_dispatch(self, mock_launch_tui):
        code = main(["--tui", "--passage", "Gen 1:1", "--theme", "dracula"])
        self.assertEqual(code, 0)
        mock_launch_tui.assert_called_once()
        args, kwargs = mock_launch_tui.call_args
        self.assertEqual(kwargs.get("passage"), "Gen 1:1")
        self.assertEqual(kwargs.get("theme"), "dracula")
        self.assertFalse(kwargs.get("force_curses"))

    @patch("search.ui.web.launch_interactive_tui")
    def test_main_tui_subcommand_dispatch(self, mock_launch_tui):
        code = main(["tui", "Rev 14:7", "--curses"])
        self.assertEqual(code, 0)
        mock_launch_tui.assert_called_once()
        args, kwargs = mock_launch_tui.call_args
        self.assertEqual(kwargs.get("passage"), "Rev 14:7")
        self.assertTrue(kwargs.get("force_curses"))

    @patch("search.ui.web.execute_subcommand", return_value=0)
    def test_main_cli_subcommand_dispatch(self, mock_exec_subcommand):
        code = main(["read", "Gen 1:1", "--json"])
        self.assertEqual(code, 0)
        mock_exec_subcommand.assert_called_once()

    def test_run_web_server_with_mock_factory_and_browser(self):
        mock_server = MagicMock()
        mock_server.serve_forever.side_effect = KeyboardInterrupt
        mock_factory = MagicMock(return_value=mock_server)
        opened_urls = []

        def mock_open(url: str):
            opened_urls.append(url)
            return True

        ready_evt = threading.Event()
        code = run_web_server(
            host="127.0.0.1",
            port=8765,
            no_browser=False,
            passage="Gen 1:1",
            open_browser_fn=mock_open,
            server_factory=mock_factory,
            ready_event=ready_evt,
        )

        self.assertEqual(code, 0)
        self.assertTrue(ready_evt.is_set())
        mock_factory.assert_called_once()
        mock_server.serve_forever.assert_called_once()
        mock_server.server_close.assert_called_once()

    def test_run_web_server_no_browser_flag(self):
        mock_server = MagicMock()
        mock_server.serve_forever.side_effect = KeyboardInterrupt
        mock_factory = MagicMock(return_value=mock_server)
        mock_browser_fn = MagicMock()

        code = run_web_server(
            host="127.0.0.1",
            port=8766,
            no_browser=True,
            open_browser_fn=mock_browser_fn,
            server_factory=mock_factory,
        )

        self.assertEqual(code, 0)
        mock_browser_fn.assert_not_called()

    def test_browser_launcher_handles_exceptions_softly(self):
        def failing_open(url: str):
            raise RuntimeError("Browser not installed")

        # Probing a non-listening port with short timeout should time out safely and not crash
        t = _launch_browser_in_background(
            "http://127.0.0.1:99999",
            "http://127.0.0.1:99999/api/health",
            timeout_sec=0.1,
            open_fn=failing_open,
        )
        t.join(timeout=1.0)
        self.assertFalse(t.is_alive())


class WebLauncherE2ETests(unittest.TestCase):
    """End-to-end subprocess tests for the bible-study entrypoint and CLI."""

    def test_bible_study_module_help(self):
        res = subprocess.run(
            [sys.executable, "-m", "search.ui.web", "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Adventist Bible Study Tool", res.stdout)
        self.assertIn("--no-browser", res.stdout)
        self.assertIn("--tui", res.stdout)
        self.assertIn("serve", res.stdout)
        self.assertIn("read", res.stdout)

    def test_bible_study_module_version(self):
        res = subprocess.run(
            [sys.executable, "-m", "search.ui.web", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("0.1.1", res.stdout)

    def test_bible_study_module_read_json(self):
        res = subprocess.run(
            [sys.executable, "-m", "search.ui.web", "read", "Gen 1:1", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data["ref"], "Gen 1:1")
        self.assertIn("In the beginning", data["verses"][0]["text"])

    def test_bible_study_console_script_e2e(self):
        # Verify that the registered console script executes cross-platform
        bin_dir = "Scripts" if sys.platform == "win32" else "bin"
        script_path = shutil.which("bible-study") or str(Path(sys.prefix) / bin_dir / "bible-study")
        if not Path(script_path).exists() and not Path(f"{script_path}.exe").exists():
            self.skipTest("bible-study console script not installed in environment")
        res = subprocess.run(
            [script_path, "read", "Gen 1:1", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data["ref"], "Gen 1:1")


if __name__ == "__main__":
    unittest.main()
