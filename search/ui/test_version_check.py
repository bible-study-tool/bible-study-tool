"""Unit tests for Application Version Update Checker & GitHub Releases Client (WP-044)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import urllib.error
import unittest

from search.ui.version_check import (
    GITHUB_API_LATEST_RELEASE,
    GITHUB_RELEASES_WEB_URL,
    VersionChecker,
    is_newer_version,
    parse_semver,
)


class TestSemverParsing(unittest.TestCase):
    """Test suite for semantic version string normalization and comparison."""

    def test_parse_semver_standard(self):
        self.assertEqual(parse_semver("0.1.6"), (0, 1, 6))
        self.assertEqual(parse_semver("v0.1.7"), (0, 1, 7))
        self.assertEqual(parse_semver("1.2.3"), (1, 2, 3))
        self.assertEqual(parse_semver("V2.0.0"), (2, 0, 0))

    def test_parse_semver_pre_release_and_build(self):
        self.assertEqual(parse_semver("0.1.7-beta.1"), (0, 1, 7))
        self.assertEqual(parse_semver("v1.0.0-rc.2+20261002"), (1, 0, 0))
        self.assertEqual(parse_semver("0.2.0-alpha"), (0, 2, 0))

    def test_parse_semver_short_and_invalid(self):
        self.assertEqual(parse_semver("1"), (1, 0, 0))
        self.assertEqual(parse_semver("1.2"), (1, 2, 0))
        self.assertEqual(parse_semver(""), (0, 0, 0))
        self.assertEqual(parse_semver("invalid"), (0, 0, 0))

    def test_is_newer_version(self):
        # Patch updates
        self.assertTrue(is_newer_version("0.1.6", "0.1.7"))
        self.assertTrue(is_newer_version("0.1.6", "v0.1.7"))
        self.assertFalse(is_newer_version("0.1.7", "0.1.6"))

        # Minor updates
        self.assertTrue(is_newer_version("0.1.6", "0.2.0"))
        self.assertFalse(is_newer_version("0.2.0", "0.1.9"))

        # Major updates
        self.assertTrue(is_newer_version("0.9.9", "1.0.0"))
        self.assertFalse(is_newer_version("2.0.0", "1.9.9"))

        # Equivalent versions
        self.assertFalse(is_newer_version("0.1.6", "0.1.6"))
        self.assertFalse(is_newer_version("0.1.6", "v0.1.6"))
        self.assertFalse(is_newer_version("v0.1.6", "0.1.6"))


class TestVersionChecker(unittest.TestCase):
    """Test suite for VersionChecker HTTP client, caching, and fallback behavior."""

    def setUp(self):
        self.checker = VersionChecker(cache_ttl_seconds=3600.0)

    def test_check_for_updates_new_release_available(self):
        mock_payload = {
            "tag_name": "v0.1.7",
            "name": "v0.1.7 - Neural Hybrid Search & EGW Enhancements",
            "html_url": "https://github.com/bible-study-tool/bible-study-tool/releases/tag/v0.1.7",
            "published_at": "2026-10-02T12:00:00Z",
            "body": "Detailed release notes for v0.1.7...",
            "assets": [
                {
                    "name": "bible-study-tool-0.1.7-x86_64.AppImage",
                    "browser_download_url": "https://github.com/bible-study-tool/bible-study-tool/releases/download/v0.1.7/app.AppImage",
                }
            ],
        }

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = self.checker.check_for_updates(current_version="0.1.6")

            mock_urlopen.assert_called_once()
            req = mock_urlopen.call_args[0][0]
            self.assertIn("BibleStudyTool/0.1.6", req.headers["User-agent"])
            self.assertEqual(req.headers["Accept"], "application/vnd.github.v3+json")

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["current_version"], "0.1.6")
            self.assertEqual(result["latest_version"], "v0.1.7")
            self.assertTrue(result["update_available"])
            self.assertEqual(result["release_name"], "v0.1.7 - Neural Hybrid Search & EGW Enhancements")
            self.assertEqual(result["release_notes_url"], mock_payload["html_url"])
            self.assertEqual(result["download_url"], mock_payload["assets"][0]["browser_download_url"])
            self.assertIn("v0.1.7", result["body"])

    def test_check_for_updates_already_on_latest(self):
        mock_payload = {
            "tag_name": "v0.1.6",
            "name": "v0.1.6",
            "html_url": "https://github.com/bible-study-tool/bible-study-tool/releases/tag/v0.1.6",
            "published_at": "2026-10-01T12:00:00Z",
            "body": "Notes for v0.1.6",
            "assets": [],
        }

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = self.checker.check_for_updates(current_version="0.1.6")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["latest_version"], "v0.1.6")
            self.assertFalse(result["update_available"])

    def test_in_memory_caching(self):
        mock_payload = {
            "tag_name": "v0.1.8",
            "name": "v0.1.8",
            "html_url": "https://github.com/bible-study-tool/releases/v0.1.8",
            "assets": [],
        }

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            # First call fetches live
            res1 = self.checker.check_for_updates(current_version="0.1.6")
            self.assertEqual(mock_urlopen.call_count, 1)
            self.assertFalse(res1.get("cached", False))

            # Second call within TTL returns cached result
            res2 = self.checker.check_for_updates(current_version="0.1.6")
            self.assertEqual(mock_urlopen.call_count, 1)  # Still 1
            self.assertTrue(res2.get("cached", False))

            # Force bypass fetches live again
            res3 = self.checker.check_for_updates(current_version="0.1.6", force=True)
            self.assertEqual(mock_urlopen.call_count, 2)
            self.assertFalse(res3.get("cached", False))

    def test_offline_and_network_error_resilience(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network unreachable")):
            result = self.checker.check_for_updates(current_version="0.1.6")
            self.assertEqual(result["status"], "offline")
            self.assertFalse(result["update_available"])
            self.assertIsNone(result["latest_version"])
            self.assertIn("Network unreachable", result["error"])
            self.assertEqual(result["release_notes_url"], GITHUB_RELEASES_WEB_URL)

    def test_timeout_resilience(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
            result = self.checker.check_for_updates(current_version="0.1.6")
            self.assertEqual(result["status"], "offline")
            self.assertFalse(result["update_available"])
            self.assertIn("Connection timed out", result["error"])


if __name__ == "__main__":
    unittest.main()
