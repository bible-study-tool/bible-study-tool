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


if __name__ == "__main__":
    unittest.main()
