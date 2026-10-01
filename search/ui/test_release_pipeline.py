"""Unit and integration tests for release build pipeline and launcher signal handling (WP-029 Phase 3)."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import yaml

from search.resource import get_repo_root

BUILD_RELEASE_SCRIPT = get_repo_root() / "scripts" / "build_release.sh"
BUILD_RELEASE_PY = get_repo_root() / "scripts" / "build_release.py"
BUILD_RELEASE_DATA_PY = get_repo_root() / "scripts" / "build_release_data.py"


class ReleasePipelineScriptTests(unittest.TestCase):
    """Test CLI flags and behaviors of scripts/build_release.sh and scripts/build_release.py."""

    @unittest.skipUnless(shutil.which("bash"), "bash executable not available")
    def test_build_release_syntax(self):
        res = subprocess.run(
            ["bash", "-n", str(BUILD_RELEASE_SCRIPT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"bash -n failed: {res.stderr}")

    @unittest.skipUnless(shutil.which("bash"), "bash executable not available")
    def test_install_macos_command_syntax_and_structure(self):
        script_path = get_repo_root() / "scripts" / "install-macos.command"
        self.assertTrue(script_path.is_file(), "scripts/install-macos.command must exist")
        self.assertTrue(os.access(script_path, os.X_OK), "scripts/install-macos.command must be executable (+x)")
        res = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"bash -n failed on install-macos.command: {res.stderr}")
        content = script_path.read_text(encoding="utf-8")
        self.assertIn("com.apple.quarantine", content)
        self.assertIn("xattr", content)
        self.assertIn("Adventist Bible Study.app", content)
        self.assertIn("codesign", content)
        self.assertIn("open", content)

    @unittest.skipUnless(shutil.which("bash"), "bash executable not available")
    def test_build_release_help(self):
        res = subprocess.run(
            ["bash", str(BUILD_RELEASE_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Release Build Pipeline", res.stdout)
        self.assertIn("--skip-tests", res.stdout)
        self.assertIn("--no-data", res.stdout)
        self.assertIn("--zip", res.stdout)
        self.assertIn("--clean", res.stdout)

    @unittest.skipUnless(shutil.which("bash"), "bash executable not available")
    def test_build_release_invalid_arg(self):
        res = subprocess.run(
            ["bash", str(BUILD_RELEASE_SCRIPT), "--invalid-flag"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2)
        self.assertIn("Unknown option", res.stderr)

    def test_build_release_py_help(self):
        res = subprocess.run(
            [sys.executable, str(BUILD_RELEASE_PY), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Release Build Pipeline", res.stdout)
        self.assertIn("--skip-tests", res.stdout)
        self.assertIn("--no-data", res.stdout)
        self.assertIn("--zip", res.stdout)
        self.assertIn("--clean", res.stdout)

    def test_build_release_py_invalid_arg(self):
        res = subprocess.run(
            [sys.executable, str(BUILD_RELEASE_PY), "--invalid-flag"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2)
        self.assertIn("Unknown option", res.stderr)

    def test_build_release_data_py_help(self):
        res = subprocess.run(
            [sys.executable, str(BUILD_RELEASE_DATA_PY), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Release Data Bundler", res.stdout)
        self.assertIn("--no-archive", res.stdout)
        self.assertIn("--zip", res.stdout)
        self.assertIn("--check", res.stdout)

    @staticmethod
    def _load_build_release_data():
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_release_data", BUILD_RELEASE_DATA_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_ensure_pinned_sources_when_present(self):
        from unittest.mock import patch
        mod = self._load_build_release_data()

        with tempfile.TemporaryDirectory() as td:
            tmp_repo = Path(td)
            data_dir = tmp_repo / "data"
            data_dir.mkdir()
            for name in ["KJV-osis.json", "ASV.json", "BSB.json", "YLT.json", "cross-references.zip"]:
                (data_dir / name).touch()
            (data_dir / "macula-greek").mkdir()
            (data_dir / "macula-greek" / "27-revelation.xml").touch()
            (data_dir / "macula-hebrew").mkdir()
            (data_dir / "macula-hebrew" / "39-Mal-003-lowfat.xml").touch()

            with patch("subprocess.run") as mock_run:
                mod.ensure_pinned_sources(tmp_repo)
                mock_run.assert_not_called()

    def test_ensure_pinned_sources_missing_triggers_bash(self):
        from unittest.mock import patch
        mod = self._load_build_release_data()

        with tempfile.TemporaryDirectory() as td:
            tmp_repo = Path(td)
            (tmp_repo / "data").mkdir()
            (tmp_repo / "scripts").mkdir()
            (tmp_repo / "scripts" / "fetch_sources.sh").touch()

            with patch("shutil.which", return_value="/bin/bash"), patch("subprocess.run") as mock_run:
                mod.ensure_pinned_sources(tmp_repo)
                mock_run.assert_called_once()
                args, _ = mock_run.call_args
                self.assertIn("fetch_sources.sh", str(args[0]))

    def test_assemble_data_bundle_requires_embeddings_db(self):
        from unittest.mock import patch
        mod = self._load_build_release_data()

        with tempfile.TemporaryDirectory() as td:
            tmp_repo = Path(td)
            data_dir = tmp_repo / "data"
            data_dir.mkdir()
            (data_dir / "bible.db").touch()
            (data_dir / "macula.db").touch()
            out_dir = tmp_repo / "out"

            with patch("subprocess.run"):
                with self.assertRaises(SystemExit) as cm:
                    mod.assemble_data_bundle(out_dir, tmp_repo)
                self.assertEqual(cm.exception.code, 1)

    def test_assemble_data_bundle_requires_onnx_models(self):
        import sqlite3
        from unittest.mock import patch
        mod = self._load_build_release_data()

        with tempfile.TemporaryDirectory() as td:
            tmp_repo = Path(td)
            data_dir = tmp_repo / "data"
            data_dir.mkdir()
            (tmp_repo / "lexicons").mkdir()
            for name in ["bible.db", "macula.db", "embeddings.db"]:
                conn = sqlite3.connect(str(data_dir / name))
                conn.execute("CREATE TABLE t (id INT)")
                conn.close()
            out_dir = tmp_repo / "out"

            with patch("subprocess.run"):
                with self.assertRaises(SystemExit) as cm:
                    mod.assemble_data_bundle(out_dir, tmp_repo)
                self.assertEqual(cm.exception.code, 1)

    def test_assemble_data_bundle_excludes_copyright_dbs(self):
        import sqlite3
        from unittest.mock import patch
        mod = self._load_build_release_data()

        with tempfile.TemporaryDirectory() as td:
            tmp_repo = Path(td)
            data_dir = tmp_repo / "data"
            data_dir.mkdir()
            (tmp_repo / "lexicons").mkdir()
            for name in ["bible.db", "macula.db", "embeddings.db"]:
                conn = sqlite3.connect(str(data_dir / name))
                conn.execute("CREATE TABLE t (id INT)")
                conn.close()
            models_dir = data_dir / "models" / "multilingual-e5-small"
            models_dir.mkdir(parents=True)
            (models_dir / "model.onnx").touch()
            (models_dir / "tokenizer.json").touch()
            out_dir = tmp_repo / "out"

            for forbidden_name in ("egw.db", "library_embeddings.db"):
                with self.subTest(forbidden=forbidden_name):
                    def inject_forbidden(*args, **kwargs):
                        (out_dir / forbidden_name).touch()

                    with patch("subprocess.run"), patch("shutil.copytree", side_effect=inject_forbidden):
                        with self.assertRaises(SystemExit) as cm:
                            mod.assemble_data_bundle(out_dir, tmp_repo)
                        self.assertEqual(cm.exception.code, 1)
class GitlabCIConfigTests(unittest.TestCase):
    """Verify integrity and schema of .gitlab-ci.yml."""

    def test_gitlab_ci_yaml_valid(self):
        repo_root = get_repo_root()
        ci_file = repo_root / ".gitlab-ci.yml"
        self.assertTrue(ci_file.is_file())
        with open(ci_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIn("stages", data)
        self.assertIn("release", data["stages"])

        # Verify Linux standalone build job
        self.assertIn("build-standalone-linux", data)
        job = data["build-standalone-linux"]
        self.assertEqual(job["stage"], "release")
        self.assertIn("artifacts", job)
        self.assertTrue(any("dist/*.tar.gz" in p for p in job["artifacts"]["paths"]))
        self.assertTrue(any("scripts/build_release.py" in s for s in job["script"]))

        # Verify Windows and macOS multi-platform build jobs
        self.assertIn("build-standalone-windows", data)
        win_job = data["build-standalone-windows"]
        self.assertEqual(win_job["stage"], "release")
        self.assertTrue(win_job.get("allow_failure"))
        self.assertTrue(any("dist/*.zip" in p for p in win_job["artifacts"]["paths"]))
        self.assertTrue(any("scripts/build_release.py" in s for s in win_job["script"]))

        self.assertIn("build-standalone-macos", data)
        mac_job = data["build-standalone-macos"]
        self.assertEqual(mac_job["stage"], "release")
        self.assertEqual(mac_job["tags"], ["macos"])
        self.assertTrue(mac_job.get("allow_failure"))
        self.assertTrue(any("dist/*.tar.gz" in p for p in mac_job["artifacts"]["paths"]))
        self.assertTrue(any("scripts/build_release.py" in s for s in mac_job["script"]))

        # Verify automated release publisher job with glab CLI
        self.assertIn("create-gitlab-release", data)
        rel_job = data["create-gitlab-release"]
        self.assertEqual(rel_job["stage"], "release")
        self.assertEqual(rel_job["image"], "registry.gitlab.com/gitlab-org/cli:latest")
        self.assertIn("needs", rel_job)
        needs_jobs = {item["job"]: item for item in rel_job["needs"]}
        self.assertIn("build-standalone-linux", needs_jobs)
        self.assertIn("build-standalone-windows", needs_jobs)
        self.assertIn("build-standalone-macos", needs_jobs)
        self.assertTrue(needs_jobs["build-standalone-windows"].get("optional"))
        self.assertTrue(needs_jobs["build-standalone-macos"].get("optional"))
        self.assertEqual(rel_job["variables"].get("GLAB_ENABLE_CI_AUTOLOGIN"), "true")
        script_text = " ".join(rel_job["script"])
        self.assertIn("glab release create", script_text)
        self.assertIn("--notes-file dist/RELEASE_NOTES.md", script_text)
        self.assertIn("--use-package-registry", script_text)


class GitHubActionsConfigTests(unittest.TestCase):
    """Verify integrity and schema of GitHub Actions workflows."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = get_repo_root()

    def _load_workflow(self, filename: str) -> dict:
        workflow_path = self.repo_root / ".github" / "workflows" / filename
        self.assertTrue(workflow_path.is_file(), f"Workflow file missing: {workflow_path}")
        with open(workflow_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_github_ci_yaml_valid(self):
        data = self._load_workflow("ci.yml")

        self.assertIn("jobs", data)
        self.assertIn("test", data["jobs"])
        self.assertIn("validate", data["jobs"])

        # Verify triggers
        triggers = data.get("on") or data.get(True, {})
        self.assertIn("push", triggers)
        self.assertIn("pull_request", triggers)
        self.assertIn("main", triggers["push"]["branches"])

        # Verify test job
        test_job = data["jobs"]["test"]
        self.assertEqual(test_job["runs-on"], "ubuntu-latest")
        test_steps = [s.get("name", "") for s in test_job.get("steps", [])]
        self.assertTrue(any("Run pytest" in name for name in test_steps))

        # Verify validator job gates F1-F5
        val_job = data["jobs"]["validate"]
        self.assertEqual(val_job["runs-on"], "ubuntu-latest")
        val_steps = [s.get("name", "") for s in val_job.get("steps", [])]
        for gate in ("F1", "F2", "F3", "F4", "F5"):
            self.assertTrue(any(gate in name for name in val_steps), f"Missing gate {gate} in validate job")

    def test_github_release_yaml_valid(self):
        data = self._load_workflow("release.yml")

        # Verify tag trigger glob syntax
        triggers = data.get("on") or data.get(True, {})
        tag_filters = triggers.get("push", {}).get("tags", [])
        self.assertTrue(any(t == "v*" or t == "v[0-9]*" for t in tag_filters), "Release workflow must match v* tags")

        self.assertIn("jobs", data)
        self.assertIn("build-standalone", data["jobs"])
        self.assertIn("create-github-release", data["jobs"])

        build_job = data["jobs"]["build-standalone"]
        matrix_targets = [m["target"] for m in build_job["strategy"]["matrix"]["include"]]
        self.assertIn("linux-x86_64", matrix_targets)
        self.assertIn("windows-x86_64", matrix_targets)
        self.assertIn("macos-arm64", matrix_targets)

        # Verify release publisher depends on build job and specifies write permission
        rel_job = data["jobs"]["create-github-release"]
        self.assertEqual(rel_job.get("needs"), "build-standalone")
        self.assertEqual(data.get("permissions", {}).get("contents"), "write")

        # Verify git autocrlf and schannel revocation are configured before checkout
        build_steps = build_job.get("steps", [])
        git_config_idx = next(
            (i for i, s in enumerate(build_steps) if "core.autocrlf false" in s.get("run", "") and "http.schannelCheckRevoke false" in s.get("run", "")),
            -1,
        )
        checkout_idx = next(
            (i for i, s in enumerate(build_steps) if "actions/checkout" in s.get("uses", "")),
            -1,
        )
        self.assertNotEqual(git_config_idx, -1, "Release workflow must disable core.autocrlf and schannelCheckRevoke")
        self.assertNotEqual(checkout_idx, -1, "Release workflow must check out repository")
        self.assertLess(
            git_config_idx,
            checkout_idx,
            "Git configuration (autocrlf and schannelCheckRevoke) must be executed before actions/checkout step",
        )

    def test_release_workflow_includes_tauri_desktop_build(self):
        """Verify release workflow invokes build_desktop.py and publishes native desktop installers."""
        release_yml = get_repo_root() / ".github" / "workflows" / "release.yml"
        data = yaml.safe_load(release_yml.read_text(encoding="utf-8"))

        build_steps = data["jobs"]["build-standalone"].get("steps", [])
        step_runs = " ".join(s.get("run", "") for s in build_steps)
        self.assertIn("build_desktop.py", step_runs, "Release workflow must invoke build_desktop.py")

        rel_steps = data["jobs"]["create-github-release"]["steps"]
        gh_release_step = next((s for s in rel_steps if "action-gh-release" in s.get("uses", "")), None)
        self.assertIsNotNone(gh_release_step, "Release job must have action-gh-release step")
        rel_files = gh_release_step.get("with", {}).get("files", "")
        self.assertIn("*.dmg", rel_files, "Release files must include macOS .dmg")
        self.assertIn("*.exe", rel_files, "Release files must include Windows .exe")
        self.assertIn("*.AppImage", rel_files, "Release files must include Linux .AppImage")
        self.assertIn("*.msi", rel_files, "Release files must include Windows .msi")
        self.assertIn("*.deb", rel_files, "Release files must include Linux .deb")
        self.assertNotIn("*.rpm", rel_files, "Release files must not publish .rpm (slow, unused package)")

    def test_gitattributes_enforces_lf(self):
        gitattributes = get_repo_root() / ".gitattributes"
        self.assertTrue(gitattributes.is_file(), ".gitattributes must exist at repo root")
        content = gitattributes.read_text(encoding="utf-8")
        self.assertIn("* text=auto eol=lf", content)
        self.assertIn("*.json text eol=lf", content)
        self.assertIn("*.xml text eol=lf", content)
        self.assertIn("*.zip binary", content)

    def test_fetch_sources_disables_autocrlf(self):
        fetch_script = get_repo_root() / "scripts" / "fetch_sources.sh"
        content = fetch_script.read_text(encoding="utf-8")
        self.assertGreaterEqual(
            content.count("core.autocrlf=false"),
            2,
            "Both macula-hebrew and macula-greek shallow clones must disable autocrlf",
        )

    def test_fetch_sources_handles_windows_ssl_revocation(self):
        fetch_script = get_repo_root() / "scripts" / "fetch_sources.sh"
        content = fetch_script.read_text(encoding="utf-8")
        self.assertIn("--ssl-no-revoke", content)
        self.assertIn('curl "${CURL_OPTS[@]}"', content, "fetch_sources.sh must invoke curl via CURL_OPTS array")
        self.assertGreaterEqual(
            content.count("http.schannelCheckRevoke=false"),
            2,
            "Both macula-hebrew and macula-greek shallow clones must disable schannel CRL checks",
        )

    def test_windows_curses_dependency_declared(self):
        pyproject = get_repo_root() / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        self.assertIn("windows-curses", content)
        self.assertIn("sys_platform == 'win32'", content)

    def test_shell_handles_missing_readline(self):
        import importlib
        import unittest.mock
        import search.ui.shell
        self.addCleanup(importlib.reload, search.ui.shell)
        with unittest.mock.patch.dict("sys.modules", {"readline": None}):
            importlib.reload(search.ui.shell)
            self.assertIsNone(search.ui.shell.readline)
            completer = search.ui.shell.StudyShellCompleter()
            self.assertIsNone(completer.complete("read", 0))

    def test_tui_handles_missing_curses(self):
        import importlib
        import unittest.mock
        import search.ui.tui
        self.addCleanup(importlib.reload, search.ui.tui)
        with unittest.mock.patch.dict("sys.modules", {"curses": None}):
            importlib.reload(search.ui.tui)
            self.assertIsNone(search.ui.tui.curses)
            with self.assertRaises(RuntimeError):
                search.ui.tui.run_tui(None)

    def test_build_release_macos_staging_helper(self):
        build_release = get_repo_root() / "scripts" / "build_release.py"
        content = build_release.read_text(encoding="utf-8")
        self.assertIn("open-macos.command", content)
        self.assertIn("codesign", content)


class ReleaseNotesExtractorTests(unittest.TestCase):
    """Test behavior of scripts/extract_release_notes.py."""

    def test_extract_release_notes_cli(self):
        repo_root = get_repo_root()
        script = repo_root / "scripts" / "extract_release_notes.py"
        res = subprocess.run(
            ["python", str(script), "v0.1.1-alpha"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Study Room Visual Identity", res.stdout)
        self.assertIn("Master Historicist Prophetic Lexicon", res.stdout)
        self.assertIn("Sanctuary Typology Blueprint", res.stdout)

    def test_extract_release_notes_cli_v012(self):
        repo_root = get_repo_root()
        script = repo_root / "scripts" / "extract_release_notes.py"
        res = subprocess.run(
            ["python", str(script), "v0.1.2-alpha"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Treasury of Scripture Knowledge", res.stdout)
        self.assertIn("Cross-Source BM25 Search Engine", res.stdout)
        self.assertIn("Two-Layer Cryptographic Data Integrity", res.stdout)

    def test_extract_release_notes_cli_v013(self):
        repo_root = get_repo_root()
        script = repo_root / "scripts" / "extract_release_notes.py"
        res = subprocess.run(
            ["python", str(script), "v0.1.3-alpha"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Multi-Platform Standalone Release Matrix", res.stdout)
        self.assertIn("GitHub Actions CI/CD Pipeline", res.stdout)
        self.assertIn("Fresh CI Environment Packaging", res.stdout)

    def test_extract_release_notes_cli_v014(self):
        repo_root = get_repo_root()
        script = repo_root / "scripts" / "extract_release_notes.py"
        res = subprocess.run(
            ["python", str(script), "v0.1.4-beta"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Native Desktop Application Packaging & Window Architecture", res.stdout)
        self.assertIn("Deterministic Cross-Language Unified Search Workstation", res.stdout)
        self.assertIn("High-Fidelity Biblical Typography", res.stdout)
        self.assertIn("Headless CI Test Environment & Integrity", res.stdout)

    def test_extract_release_notes_fallback(self):
        repo_root = get_repo_root()
        script = repo_root / "scripts" / "extract_release_notes.py"
        res = subprocess.run(
            ["python", str(script), "v99.99.99-unknown"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Release v99.99.99-unknown", res.stdout)
        self.assertIn("Automated release build", res.stdout)

    def test_extract_release_notes_collision_avoidance(self):
        import importlib.util
        repo_root = get_repo_root()
        script_path = repo_root / "scripts" / "extract_release_notes.py"
        spec = importlib.util.spec_from_file_location("extract_release_notes", script_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        synthetic_changelog = """# Changelog

## [0.1.10] - 2026-10-01
Notes for version 0.1.10.

## [0.1.1] - 2026-09-15
Notes for version 0.1.1.
"""
        notes_0110 = mod.extract_notes_from_changelog(synthetic_changelog, "0.1.10")
        notes_011 = mod.extract_notes_from_changelog(synthetic_changelog, "0.1.1")
        self.assertEqual(notes_0110, "Notes for version 0.1.10.")
        self.assertEqual(notes_011, "Notes for version 0.1.1.")


if __name__ == "__main__":
    unittest.main()
