"""Unit and integration tests for release build pipeline and launcher signal handling (WP-029 Phase 3)."""

from __future__ import annotations

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

    def test_ensure_pinned_sources_when_present(self):
        import importlib.util
        from unittest.mock import patch

        spec = importlib.util.spec_from_file_location("build_release_data", BUILD_RELEASE_DATA_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

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
        import importlib.util
        from unittest.mock import patch

        spec = importlib.util.spec_from_file_location("build_release_data", BUILD_RELEASE_DATA_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

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
        self.assertIn("linux", matrix_targets)
        self.assertIn("windows", matrix_targets)
        self.assertIn("macos", matrix_targets)

        # Verify release publisher depends on build job and specifies write permission
        rel_job = data["jobs"]["create-github-release"]
        self.assertEqual(rel_job.get("needs"), "build-standalone")
        self.assertEqual(data.get("permissions", {}).get("contents"), "write")


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
