"""Comprehensive unit and async test suite for Textual Bible Study workstation (WP-022, ADR-0018)."""

from __future__ import annotations

import subprocess
import sys
import unittest

from search.ui.app import BibleStudyApp, GotoModal, HelpModal, SearchModal
from search.ui.themes import (
    DEFAULT_THEME,
    THEMES,
    get_next_theme,
    get_theme_css,
)
from textual.widgets import TabbedContent


class ThemeSystemTests(unittest.TestCase):
    """Test theme registry, color schemes, and dynamic TCSS generation."""

    def test_theme_registry_contains_all_themes(self):
        expected = [
            "transparent",
            "dracula",
            "catppuccin_mocha",
            "tokyo_night",
            "nord",
            "gruvbox_dark",
            "solarized_dark",
        ]
        for theme_id in expected:
            self.assertIn(theme_id, THEMES)
            theme = THEMES[theme_id]
            self.assertEqual(theme.id, theme_id)
            self.assertTrue(len(theme.name) > 0)
            self.assertTrue(len(theme.description) > 0)

    def test_default_theme_is_transparent(self):
        self.assertEqual(DEFAULT_THEME, "transparent")
        self.assertEqual(THEMES[DEFAULT_THEME].id, "transparent")

    def test_theme_cycling_sequence(self):
        cur = "transparent"
        visited = [cur]
        for _ in range(len(THEMES) - 1):
            cur = get_next_theme(cur)
            visited.append(cur)
        # Verify all themes visited once
        self.assertEqual(set(visited), set(THEMES.keys()))
        # Verify wrap-around
        self.assertEqual(get_next_theme(cur), "transparent")

    def test_transparent_theme_css_preserves_host_terminal(self):
        css = get_theme_css("transparent")
        self.assertIn("background: transparent;", css)
        self.assertIn(".theme-transparent", css)
        self.assertIn(".verse-selected", css)

    def test_all_themes_generate_valid_css(self):
        for theme_id in THEMES:
            css = get_theme_css(theme_id)
            self.assertTrue(len(css) > 100)
            self.assertIn(f".theme-{theme_id}", css)
            self.assertIn("#reader-pane", css)
            self.assertIn(".verse-selected", css)


class TextualAppTests(unittest.IsolatedAsyncioTestCase):
    """Async headless tests for BibleStudyApp using Textual test pilot."""

    async def test_app_initial_mount_and_verses(self):
        app = BibleStudyApp(initial_ref="Gen 1:1-3", initial_theme="transparent")
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIsNotNone(app.current_passage)
            self.assertEqual(app.current_passage.ref, "Gen 1:1-3")
            self.assertEqual(len(app.current_passage.verses), 3)
            self.assertEqual(app.selected_verse_idx, 0)
            self.assertEqual(app.active_theme_id, "transparent")
            self.assertIn("GEN 1:1-3", app.title)

    async def test_verse_navigation(self):
        app = BibleStudyApp(initial_ref="Gen 1:1-3")
        async with app.run_test() as pilot:
            await pilot.pause()
            # Move next
            app.action_next_verse()
            self.assertEqual(app.selected_verse_idx, 1)

            app.action_next_verse()
            self.assertEqual(app.selected_verse_idx, 2)

            # Bound check at end
            app.action_next_verse()
            self.assertEqual(app.selected_verse_idx, 2)

            # Move prev
            app.action_prev_verse()
            self.assertEqual(app.selected_verse_idx, 1)

            app.action_prev_verse()
            self.assertEqual(app.selected_verse_idx, 0)

            # Bound check at start
            app.action_prev_verse()
            self.assertEqual(app.selected_verse_idx, 0)

    async def test_chapter_navigation(self):
        app = BibleStudyApp(initial_ref="Gen 1:1-31")
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertEqual(app.current_passage.start_chapter, 1)

            # Advance to next chapter (Gen 2)
            app.action_next_chapter()
            for w in app.workers:
                if not w.is_finished:
                    await w.wait()
            await pilot.pause()
            self.assertEqual(app.current_passage.start_chapter, 2)

            # Return to previous chapter (Gen 1)
            app.action_prev_chapter()
            for w in app.workers:
                if not w.is_finished:
                    await w.wait()
            await pilot.pause()
            self.assertEqual(app.current_passage.start_chapter, 1)

    async def test_pin_and_unpin_inspection(self):
        app = BibleStudyApp(initial_ref="Gen 1:1-3")
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIsNone(app.pinned_verse_idx)

            # Pin verse 1 (index 0)
            app.action_toggle_pin()
            self.assertEqual(app.pinned_verse_idx, 0)

            # Move selection to verse 2 (index 1)
            app.action_next_verse()
            self.assertEqual(app.selected_verse_idx, 1)
            # Inspected verse must still be verse 1 because it's pinned
            self.assertEqual(app._get_inspected_verse().verse, 1)

            # Unpin
            app.action_toggle_pin()
            self.assertIsNone(app.pinned_verse_idx)
            # Inspected verse now follows selection (verse 2)
            self.assertEqual(app._get_inspected_verse().verse, 2)

    async def test_strongs_and_focus_toggles(self):
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()

            # Strongs toggle
            self.assertFalse(app.show_strongs)
            self.assertFalse(app.verse_widgets[0].show_strongs)
            rendered_off = app.verse_widgets[0].render_content(is_selected=True, is_pinned=False)
            self.assertNotIn("\\[H", rendered_off)

            # Enable Strong's
            app.action_toggle_strongs()
            self.assertTrue(app.show_strongs)
            self.assertTrue(app.verse_widgets[0].show_strongs)
            rendered_on = app.verse_widgets[0].render_content(is_selected=True, is_pinned=False)
            self.assertIn("\\[H", rendered_on)

            # Disable Strong's
            app.action_toggle_strongs()
            self.assertFalse(app.show_strongs)
            self.assertFalse(app.verse_widgets[0].show_strongs)

            # Focus mode toggle
            self.assertFalse(app.focus_mode)
            app.action_toggle_focus()
            self.assertTrue(app.focus_mode)
            app.action_toggle_focus()
            self.assertFalse(app.focus_mode)

    async def test_theme_cycling_action(self):
        app = BibleStudyApp(initial_ref="Gen 1:1", initial_theme="transparent")
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertEqual(app.active_theme_id, "transparent")
            self.assertTrue(app.screen.has_class("theme-transparent"))

            # Cycle to dracula
            app.action_cycle_theme()
            self.assertEqual(app.active_theme_id, "dracula")
            self.assertTrue(app.screen.has_class("theme-dracula"))
            self.assertFalse(app.screen.has_class("theme-transparent"))

    async def test_tabs_and_search_execution(self):
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            tabs = app.query_one("#inspector-tabs", TabbedContent)

            app.action_tab_lexicon()
            self.assertEqual(tabs.active, "tab-lexicon")

            app.action_tab_commentary()
            self.assertEqual(tabs.active, "tab-commentary")

            app.action_tab_search()
            self.assertEqual(tabs.active, "tab-search")

            app.action_tab_syntax()
            self.assertEqual(tabs.active, "tab-syntax")

            # Execute search
            worker = app.execute_search_async("sanctuary")
            await worker.wait()
            await pilot.pause()
            self.assertEqual(tabs.active, "tab-search")

    async def test_modals_dialogs(self):
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()

            # Help modal - open and dismiss via escape key action
            app.action_show_help()
            await pilot.pause()
            self.assertIsInstance(app.screen, HelpModal)
            app.screen.action_dismiss_modal()
            await pilot.pause()
            self.assertNotIsInstance(app.screen, HelpModal)

            # Goto modal - open and cancel via escape key action
            app.action_goto_passage()
            await pilot.pause()
            self.assertIsInstance(app.screen, GotoModal)
            app.screen.action_cancel()
            await pilot.pause()
            self.assertNotIsInstance(app.screen, GotoModal)

            # Search modal - open and cancel via escape key action
            app.action_search_dialog()
            await pilot.pause()
            self.assertIsInstance(app.screen, SearchModal)
            app.screen.action_cancel()
            await pilot.pause()
            self.assertNotIsInstance(app.screen, SearchModal)



class StudyCLITextualIntegrationTests(unittest.TestCase):
    """Test CLI help flags and theme options for study.py."""

    def test_cli_help_includes_theme_and_curses_options(self):
        res = subprocess.run(
            [sys.executable, "scripts/study.py", "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("--theme", res.stdout)
        self.assertIn("--curses", res.stdout)
        self.assertIn("transparent", res.stdout)
        self.assertIn("dracula", res.stdout)

    def test_cli_tui_subcommand_help(self):
        res = subprocess.run(
            [sys.executable, "scripts/study.py", "tui", "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("--theme", res.stdout)
        self.assertIn("--curses", res.stdout)


if __name__ == "__main__":
    unittest.main()
