"""Unit tests for the Tauri native desktop application configuration and pipeline (WP-038, ADR-028)."""

from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib
import unittest

from search.resource import __version__

REPO_ROOT = Path(__file__).resolve().parents[2]


class TauriDesktopConfigurationTests(unittest.TestCase):
    """Test suite verifying Tauri project structure, configuration, and packaging harness."""

    def setUp(self):
        self.src_tauri = REPO_ROOT / "src-tauri"
        self.tauri_conf = self.src_tauri / "tauri.conf.json"
        self.cargo_toml = self.src_tauri / "Cargo.toml"
        self.lib_rs = self.src_tauri / "src" / "lib.rs"
        self.main_rs = self.src_tauri / "src" / "main.rs"
        self.build_script = REPO_ROOT / "scripts" / "build_desktop.py"

    def test_tauri_files_exist(self):
        """Verify all core Tauri source and configuration files exist."""
        self.assertTrue(self.src_tauri.is_dir(), "src-tauri directory must exist")
        self.assertTrue(self.tauri_conf.is_file(), "tauri.conf.json must exist")
        self.assertTrue(self.cargo_toml.is_file(), "Cargo.toml must exist")
        self.assertTrue(self.lib_rs.is_file(), "src/lib.rs must exist")
        self.assertTrue(self.main_rs.is_file(), "src/main.rs must exist")
        self.assertTrue(self.build_script.is_file(), "scripts/build_desktop.py must exist")

    def test_binaries_placeholder_exists(self):
        """Verify placeholder.txt exists so Tauri bundle resource glob matches in dev mode."""
        placeholder = self.src_tauri / "binaries" / "placeholder.txt"
        self.assertTrue(placeholder.is_file(), "src-tauri/binaries/placeholder.txt must exist")
        build_rs = (self.src_tauri / "build.rs").read_text(encoding="utf-8")
        self.assertIn("placeholder.txt", build_rs, "build.rs must defensively ensure placeholder exists")

    def test_tauri_conf_json_validity(self):
        """Verify tauri.conf.json satisfies ADR-024 and ADR-028 requirements."""
        data = json.loads(self.tauri_conf.read_text(encoding="utf-8"))

        self.assertEqual(data.get("productName"), "Adventist Bible Study")
        self.assertEqual(data.get("identifier"), "org.biblestudytool.desktop")
        self.assertEqual(data.get("version"), __version__)

        # Zero-build web assets (ADR-013, ADR-024 §5)
        build_cfg = data.get("build", {})
        self.assertEqual(build_cfg.get("frontendDist"), "../web")
        self.assertNotIn("beforeBuildCommand", build_cfg, "No node/npm build commands allowed")
        self.assertNotIn("beforeDevCommand", build_cfg, "No node/npm dev commands allowed")

        # Study Room Desk window dimensions
        windows = data.get("app", {}).get("windows", [])
        self.assertGreaterEqual(len(windows), 1, "At least one window must be configured")
        main_win = windows[0]
        self.assertEqual(main_win.get("label"), "main")
        self.assertEqual(main_win.get("title"), "Adventist Bible Study")
        self.assertEqual(main_win.get("width"), 1280)
        self.assertEqual(main_win.get("height"), 860)
        self.assertEqual(main_win.get("minWidth"), 900)
        self.assertEqual(main_win.get("minHeight"), 600)
        self.assertEqual(main_win.get("backgroundColor"), "#1c1815")

        # macOS / Desktop bundle configuration
        bundle_cfg = data.get("bundle", {})
        self.assertTrue(bundle_cfg.get("active"))
        self.assertEqual(bundle_cfg.get("targets"), "all")
        self.assertIn("binaries/", bundle_cfg.get("resources", []))
        self.assertIn("icons/icon.icns", bundle_cfg.get("icon", []))
        self.assertIn("icons/icon.ico", bundle_cfg.get("icon", []))

    def test_cargo_toml_validity(self):
        """Verify src-tauri/Cargo.toml package metadata and dependencies."""
        data = tomllib.loads(self.cargo_toml.read_text(encoding="utf-8"))

        pkg = data.get("package", {})
        self.assertEqual(pkg.get("name"), "adventist-bible-study")
        self.assertEqual(pkg.get("version"), __version__)
        self.assertEqual(pkg.get("license"), "MIT")

        deps = data.get("dependencies", {})
        self.assertIn("tauri", deps)
        self.assertIn("serde", deps)
        self.assertIn("serde_json", deps)

    def test_rust_sidecar_supervisor_implementation(self):
        """Verify that lib.rs implements process supervision and lifecycle handlers."""
        code = self.lib_rs.read_text(encoding="utf-8")

        # Port negotiation
        self.assertIn("find_available_port", code)
        self.assertIn("TcpListener::bind", code)

        # Sidecar and development engine resolution
        self.assertIn("find_repo_root", code)
        self.assertIn("resolve_engine_path", code)
        self.assertIn("resolve_engine_command", code)
        self.assertIn("configure_engine_env", code)
        self.assertIn("BIBLE_STUDY_DATA_DIR", code)
        self.assertIn("search.ui.web", code)
        self.assertIn("bible-study", code)

        # Health checking & timeouts
        self.assertIn("wait_for_server", code)
        self.assertIn("/api/health", code)
        self.assertIn("set_read_timeout", code)
        self.assertIn("set_write_timeout", code)

        # Process management and clean stop
        self.assertIn("CREATE_NO_WINDOW", code)
        self.assertIn("current_dir", code)
        self.assertIn("Stdio::null", code)
        self.assertIn("pub fn new(", code)
        self.assertIn("pub fn set_child(", code)
        self.assertIn("pub fn stop(", code)
        self.assertIn("impl Drop for EngineState", code)
        self.assertIn("into_inner()", code)
        self.assertIn("child.kill()", code)

    def test_web_app_js_supports_dynamic_api_base(self):
        """Verify web/app.js supports dynamic API_BASE for desktop webview."""
        app_js = (REPO_ROOT / "web" / "app.js").read_text(encoding="utf-8")

        self.assertIn("API_BASE", app_js)
        self.assertIn("window.__BIBLE_STUDY_API_BASE__", app_js)
        self.assertIn("function apiUrl(", app_js)

    def test_build_desktop_prerequisites_check(self):
        """Verify scripts/build_desktop.py prerequisite check functionality."""
        from scripts.build_desktop import check_tauri_prerequisites, resolve_tauri_command

        prereqs = check_tauri_prerequisites()
        self.assertIsInstance(prereqs, dict)
        self.assertIn("cargo", prereqs)
        self.assertIn("rustc", prereqs)

        cmd = resolve_tauri_command()
        self.assertIsInstance(cmd, list)
        self.assertGreaterEqual(len(cmd), 1)

    def test_web_cli_parser_tolerates_server_flag(self):
        """Verify that build_web_parser parses the --server flag without error (ADR-028)."""
        from search.ui.web import build_web_parser
        parser = build_web_parser()
        args = parser.parse_args(["--server", "--port", "9000", "--no-browser"])
        self.assertTrue(args.server)
        self.assertEqual(args.port, 9000)
        self.assertTrue(args.no_browser)


if __name__ == "__main__":
    unittest.main()
