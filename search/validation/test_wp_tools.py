"""Tests for work package automation tools (curate_context.py and wp_check.py)."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.curate_context import build_briefing, find_wp_file, parse_verse_range
from scripts.wp_check import check_entry_ai_markers, resolve_wp_files, run_wp_check
from search.testutil import require_raw_sources


class CurateContextTests(unittest.TestCase):
    def test_parse_verse_range(self):
        self.assertEqual(parse_verse_range("9..13"), [9, 10, 11, 12, 13])
        self.assertEqual(parse_verse_range("6-8"), [6, 7, 8])
        self.assertEqual(parse_verse_range("1,2,3"), [1, 2, 3])
        self.assertEqual(parse_verse_range("5"), [5])

    def test_find_wp_file_and_verses(self):
        repo_root = Path(".")
        target_wp, verses = find_wp_file(repo_root, "WP-002")
        self.assertIsNotNone(target_wp)
        self.assertEqual(verses, [6, 7, 8])

        target_wp3, verses3 = find_wp_file(repo_root, "WP-003")
        self.assertIsNotNone(target_wp3)
        self.assertEqual(verses3, [9, 10, 11, 12, 13])

    def test_find_wp_file_chapter_detection(self):
        repo_root = Path(".")
        res_wp2 = find_wp_file(repo_root, "WP-002")
        self.assertEqual(res_wp2.chapter, 1)
        self.assertEqual(res_wp2.verses, [6, 7, 8])
        self.assertEqual(res_wp2[0], res_wp2.target_file)
        self.assertEqual(res_wp2[1], res_wp2.verses)

        res_wp8 = find_wp_file(repo_root, "WP-008")
        self.assertEqual(res_wp8.chapter, 2)
        self.assertEqual(len(res_wp8.verses), 25)

        res_wp11 = find_wp_file(repo_root, "WP-011")
        self.assertEqual(res_wp11.chapter, 3)
        self.assertEqual(len(res_wp11.verses), 24)

    def test_build_briefing_outputs_required_sections(self):
        repo_root = Path(".")
        briefing = build_briefing(repo_root, 1, [6, 7])
        self.assertIn("Genesis 1:6", briefing)
        self.assertIn("Genesis 1:7", briefing)
        self.assertIn("Apparatus Alignment", briefing)
        self.assertIn("Key Lexemes in Verse", briefing)

    def test_build_briefing_empty_verses(self):
        repo_root = Path(".")
        briefing = build_briefing(repo_root, 1, [])
        self.assertIn("no verses specified", briefing)


class WpCheckTests(unittest.TestCase):
    def test_resolve_wp_files(self):
        repo_root = Path(".")
        target_wp, files = resolve_wp_files(repo_root, "WP-002")
        self.assertIsNotNone(target_wp)
        self.assertEqual(len(files), 3)
        self.assertTrue(all(f.exists() for f in files))

    def test_check_entry_ai_markers_balanced(self):
        balanced = "<!-- AI-GENERATED -->\nNote\n<!-- END AI-GENERATED -->\n`<!-- AI-GENERATED -->`"
        errs = check_entry_ai_markers(Path("dummy.md"), balanced)
        self.assertEqual(errs, [])

    def test_check_entry_ai_markers_unbalanced_fails(self):
        unbalanced = "<!-- AI-GENERATED -->\nNote without close"
        errs = check_entry_ai_markers(Path("dummy.md"), unbalanced)
        self.assertTrue(len(errs) > 0)

    @require_raw_sources()
    def test_run_wp_check_on_existing_curated_wps(self):
        repo_root = Path(".")
        for wp_name in ("WP-001", "WP-002"):
            target_wp, files = resolve_wp_files(repo_root, wp_name)
            code = run_wp_check(repo_root, target_wp, files)
            self.assertEqual(code, 0, f"{wp_name} should pass wp_check")


if __name__ == "__main__":
    unittest.main(verbosity=2)
