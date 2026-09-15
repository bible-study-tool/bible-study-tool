"""Unit and integration tests for release build pipeline and launcher signal handling (WP-029 Phase 3)."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest
import yaml

from search.resource import get_repo_root

BUILD_RELEASE_SCRIPT = get_repo_root() / "scripts" / "build_release.sh"


class ReleasePipelineScriptTests(unittest.TestCase):
    """Test CLI flags and behaviors of scripts/build_release.sh."""

    def test_build_release_syntax(self):
        res = subprocess.run(
            ["bash", "-n", str(BUILD_RELEASE_SCRIPT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"bash -n failed: {res.stderr}")

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

    def test_build_release_invalid_arg(self):
        res = subprocess.run(
            ["bash", str(BUILD_RELEASE_SCRIPT), "--invalid-flag"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 2)
        self.assertIn("Unknown option", res.stderr)


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
        self.assertIn("build-standalone-release", data)
        job = data["build-standalone-release"]
        self.assertEqual(job["stage"], "release")
        self.assertIn("artifacts", job)
        self.assertTrue(any("dist/*.tar.gz" in p for p in job["artifacts"]["paths"]))

        # Verify automated release publisher job with glab CLI
        self.assertIn("create-gitlab-release", data)
        rel_job = data["create-gitlab-release"]
        self.assertEqual(rel_job["stage"], "release")
        self.assertEqual(rel_job["image"], "registry.gitlab.com/gitlab-org/cli:latest")
        self.assertIn("needs", rel_job)
        self.assertEqual(rel_job["variables"].get("GLAB_ENABLE_CI_AUTOLOGIN"), "true")
        script_text = " ".join(rel_job["script"])
        self.assertIn("glab release create", script_text)
        self.assertIn("--notes-file dist/RELEASE_NOTES.md", script_text)
        self.assertIn("--use-package-registry", script_text)


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
