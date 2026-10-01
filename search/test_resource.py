"""Unit tests for PyInstaller-aware resource and data path resolver (search.resource)."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from search.resource import (
    data_path,
    get_app_dir,
    get_bundle_root,
    get_data_dir,
    get_lexicons_dir,
    get_repo_root,
    get_web_dir,
    is_frozen,
    lexicon_path,
    resource_path,
)


class ResourcePathTests(unittest.TestCase):
    """Test path resolution in standard source/development environment."""

    def test_not_frozen_by_default(self) -> None:
        self.assertFalse(is_frozen())

    def test_bundle_root_is_repo(self) -> None:
        root = get_bundle_root()
        self.assertTrue(root.is_dir())
        self.assertTrue((root / "README.md").is_file())
        self.assertTrue((root / "pyproject.toml").is_file())

    def test_app_dir_matches_bundle_root_in_dev(self) -> None:
        self.assertEqual(get_app_dir(), get_bundle_root())

    def test_repo_root_matches_app_dir_in_dev(self) -> None:
        self.assertEqual(get_repo_root(), get_app_dir())

    def test_data_dir_resolves_existing_data(self) -> None:
        data_dir = get_data_dir()
        self.assertTrue(data_dir.is_dir())
        self.assertEqual(data_dir.name, "data")
        # In this repo, data/PROVENANCE.md is committed and always exists
        self.assertTrue((data_dir / "PROVENANCE.md").is_file())

    def test_web_dir_resolves_existing_frontend(self) -> None:
        web_dir = get_web_dir()
        self.assertTrue(web_dir.is_dir())
        self.assertTrue((web_dir / "index.html").is_file())
        self.assertTrue((web_dir / "styles.css").is_file())
        self.assertTrue((web_dir / "app.js").is_file())

    def test_lexicons_dir_resolves_existing_lexicons(self) -> None:
        lex_dir = get_lexicons_dir()
        self.assertTrue(lex_dir.is_dir())
        self.assertTrue((lex_dir / "strongs-lexicon.json").is_file())

    def test_data_path_normalizes_data_prefix(self) -> None:
        p1 = data_path("PROVENANCE.md")
        p2 = data_path("data/PROVENANCE.md")
        self.assertEqual(p1, p2)
        self.assertTrue(p1.is_file())

    def test_data_path_absolute_passthrough(self) -> None:
        abs_p = Path("/tmp/custom_test_db.db").resolve()
        self.assertEqual(data_path(abs_p), abs_p)

    def test_lexicon_path_normalizes_lexicons_prefix(self) -> None:
        p1 = lexicon_path("strongs-lexicon.json")
        p2 = lexicon_path("lexicons/strongs-lexicon.json")
        self.assertEqual(p1, p2)
        self.assertTrue(p1.is_file())

    def test_resource_path_finds_fixtures(self) -> None:
        p = resource_path("search/fixtures/sample_test_data.json.gz")
        self.assertTrue(p.is_file())


class ResourceEnvironmentOverrideTests(unittest.TestCase):
    """Test environment variable overrides for custom deployment setups."""

    def test_repo_root_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir).resolve()
            with patch.dict(os.environ, {"BIBLE_STUDY_REPO_ROOT": str(tmp)}):
                self.assertEqual(get_repo_root(), tmp)

    def test_data_dir_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir).resolve()
            with patch.dict(os.environ, {"BIBLE_STUDY_DATA_DIR": str(tmp)}):
                self.assertEqual(get_data_dir(), tmp)
                self.assertEqual(data_path("test.db"), tmp / "test.db")

    def test_web_dir_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir).resolve()
            with patch.dict(os.environ, {"BIBLE_STUDY_WEB_DIR": str(tmp)}):
                self.assertEqual(get_web_dir(), tmp)

    def test_lexicons_dir_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir).resolve()
            with patch.dict(os.environ, {"BIBLE_STUDY_LEXICONS_DIR": str(tmp)}):
                self.assertEqual(get_lexicons_dir(), tmp)
                self.assertEqual(lexicon_path("custom.json"), tmp / "custom.json")


class FrozenEnvironmentSimulationTests(unittest.TestCase):
    """Test behavior when running under simulated PyInstaller/Nuitka frozen state."""

    def test_simulated_onefile_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as meipass_dir, tempfile.TemporaryDirectory() as app_dir:
            meipass_path = Path(meipass_dir).resolve()
            app_path = Path(app_dir).resolve()
            fake_exe = app_path / "AdventistBibleStudy"
            fake_exe.touch()

            # Create sidecar data/ next to the executable
            sidecar_data = app_path / "data"
            sidecar_data.mkdir()
            fake_bible_db = sidecar_data / "bible.db"
            fake_bible_db.write_text("sqlite-stub")

            # Create bundled web/ inside _MEIPASS
            bundled_web = meipass_path / "web"
            bundled_web.mkdir()
            (bundled_web / "index.html").write_text("<html></html>")

            with patch.object(sys, "frozen", True, create=True), \
                 patch.object(sys, "_MEIPASS", str(meipass_path), create=True), \
                 patch.object(sys, "executable", str(fake_exe)):

                self.assertTrue(is_frozen())
                self.assertEqual(get_bundle_root(), meipass_path)
                self.assertEqual(get_app_dir(), app_path)
                self.assertEqual(get_data_dir(), sidecar_data)
                self.assertEqual(get_web_dir(), bundled_web)
                self.assertEqual(data_path("bible.db"), fake_bible_db)
                self.assertEqual(data_path("data/bible.db"), fake_bible_db)


if __name__ == "__main__":
    unittest.main()
