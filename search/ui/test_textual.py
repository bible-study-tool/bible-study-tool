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
from textual.containers import VerticalScroll
from textual.widgets import TabbedContent


def _extract_text(widget) -> str:
    """Recursively extract text representations from a Textual widget tree."""
    texts: list[str] = []
    nodes = [widget] + list(widget.walk_children())
    for node in nodes:
        if hasattr(node, "render"):
            try:
                r = str(node.render())
                if r and not r.startswith("<"):
                    texts.append(r)
            except Exception:
                pass
    return " ".join(texts)


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

    async def test_syntax_frames_rendering_with_glosses(self):
        """Verify syntax & frames inspector tab displays both original text and English glosses."""
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            syntax_scroll = app.query_one("#syntax-content", VerticalScroll)
            content_text = _extract_text(syntax_scroll)

            # Both Hebrew original and English translation gloss must be present
            self.assertIn("אֱלֹהִ֑ים", content_text)
            self.assertIn("God", content_text)
            self.assertIn("בָּרָ֣א", content_text)
            self.assertIn("he created", content_text)

    async def test_lexicon_rendering_with_kjv_word_mapping_and_lxx_glosses(self):
        """Verify lexicon tab displays KJV word mapping and Septuagint English glosses."""
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_tab_lexicon()
            await pilot.pause()
            lexicon_scroll = app.query_one("#lexicon-content", VerticalScroll)
            content_text = _extract_text(lexicon_scroll)

            # KJV word to Strong's code mapping
            self.assertIn('"created" ➔ H1254', content_text)
            self.assertIn("Translation Gloss: to create", content_text)

            # LXX equivalence with Greek English gloss
            self.assertIn("G4160", content_text)
            self.assertIn("to do/make: do", content_text)

    async def test_commentary_rendering_full_text(self):
        """Verify commentary tab renders full paragraph text instead of truncated snippets."""
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_tab_commentary()
            await pilot.pause()
            commentary_scroll = app.query_one("#commentary-content", VerticalScroll)
            content_text = _extract_text(commentary_scroll)

            # Must contain heading and paragraph text
            self.assertIn("SPIRIT OF PROPHECY CORRELATIONS", content_text)
            self.assertIn("Genesis 1", content_text)

    async def test_egw_citation_direct_navigation(self):
        """Verify direct jump to an EGW citation renders full page context in the commentary tab."""
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            tabs = app.query_one("#inspector-tabs", TabbedContent)

            # Direct jump to PP 44.1
            worker = app.load_egw_citation_async("PP 44.1")
            await worker.wait()
            await pilot.pause()

            self.assertEqual(tabs.active, "tab-commentary")
            commentary_scroll = app.query_one("#commentary-content", VerticalScroll)
            content_text = _extract_text(commentary_scroll)

            self.assertIn("Patriarchs and Prophets", content_text)
            self.assertIn("PP.44.1", content_text)
            self.assertIn("This chapter is based on Genesis 1 and 2", content_text)

    async def test_goto_modal_disambiguation_bible_vs_egw(self):
        """Verify that Goto correctly loads Bible book Colossians for 'Col 1:1' instead of EGW Christ's Object Lessons."""
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            # Simulate goto "Col 1:1"
            app.action_goto_passage()
            await pilot.pause()
            self.assertIsInstance(app.screen, GotoModal)
            app.screen.dismiss("Col 1:1")
            await pilot.pause()
            # Wait for background worker
            await pilot.pause(0.2)
            self.assertIn("COL", app.current_ref.upper())
            self.assertEqual(app.current_passage.book_name, "Colossians")

    async def test_lazy_tab_rendering_and_dirty_tracking(self):
        """Verify that tabs are only rendered when active and dirty flags are tracked."""
        app = BibleStudyApp(initial_ref="Gen 1:1-3")
        async with app.run_test() as pilot:
            await pilot.pause()
            tabs = app.query_one("#inspector-tabs", TabbedContent)
            self.assertEqual(tabs.active, "tab-syntax")

            # Syntax tab should be clean, lexicon and commentary dirty
            self.assertNotIn("tab-syntax", app._dirty_tabs)
            self.assertIn("tab-lexicon", app._dirty_tabs)
            self.assertIn("tab-commentary", app._dirty_tabs)

            # Switch to Lexicon: it should render and become clean
            app.action_tab_lexicon()
            await pilot.pause()
            self.assertEqual(tabs.active, "tab-lexicon")
            self.assertNotIn("tab-lexicon", app._dirty_tabs)

            # Move to next verse while on Lexicon tab
            app.action_next_verse()
            await pilot.pause()
            self.assertEqual(app.selected_verse_idx, 1)
            # Lexicon was rendered immediately; syntax became dirty
            self.assertNotIn("tab-lexicon", app._dirty_tabs)
            self.assertIn("tab-syntax", app._dirty_tabs)

            # Switch back to Syntax: it should re-render and become clean
            app.action_tab_syntax()
            await pilot.pause()
            self.assertNotIn("tab-syntax", app._dirty_tabs)

    async def test_rapid_verse_stepping_performance(self):
        """Verify rapid verse stepping incurs zero DOM allocations and completes instantly."""
        app = BibleStudyApp(initial_ref="Gen 1:1-10")
        async with app.run_test() as pilot:
            await pilot.pause()
            initial_widget_count = len(app.query("*"))

            # Rapidly step through verses 1 to 9
            for _ in range(9):
                app.action_next_verse()

            await pilot.pause()
            self.assertEqual(app.selected_verse_idx, 9)

            # DOM tree size must remain constant (no DOM thrashing / leaking)
            final_widget_count = len(app.query("*"))
            self.assertEqual(initial_widget_count, final_widget_count)

    async def test_syntax_viewport_verbal_nuances(self):
        """Verify syntax viewport displays verbal stems and theological nuances."""
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            syntax_scroll = app.query_one("#syntax-content", VerticalScroll)
            content_text = _extract_text(syntax_scroll)

            self.assertIn("VERBAL STEMS & THEOLOGICAL NUANCES", content_text)
            self.assertIn("Qal (Simple Active)", content_text)
            self.assertIn("Exclusively Divine Initiative", content_text)

    async def test_lexicon_viewport_verbal_nuances(self):
        """Verify lexicon viewport displays verbal stems and theological nuances on Strong's cards."""
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_tab_lexicon()
            await pilot.pause()
            lexicon_scroll = app.query_one("#lexicon-content", VerticalScroll)
            content_text = _extract_text(lexicon_scroll)

            self.assertIn("Verbal Stem / Form:", content_text)
            self.assertIn("Qal (Simple Active)", content_text)
            self.assertIn("Exclusively Divine Initiative", content_text)

    async def test_greek_verbal_nuances_ephesians(self):
        """Verify Greek verbal nuances (Middle Voice loving choice) render in Ephesians 1:4."""
        app = BibleStudyApp(initial_ref="Eph 1:4")
        async with app.run_test() as pilot:
            await pilot.pause()
            syntax_scroll = app.query_one("#syntax-content", VerticalScroll)
            syntax_text = _extract_text(syntax_scroll)
            self.assertIn("Aorist Middle", syntax_text)
            self.assertIn("Loving Personal Choice", syntax_text)

            app.action_tab_lexicon()
            await pilot.pause()
            lexicon_scroll = app.query_one("#lexicon-content", VerticalScroll)
            lexicon_text = _extract_text(lexicon_scroll)
    async def test_parallel_tab_viewport(self):
        """Verify parallel translations tab renders KJV, BSB, ASV, and YLT."""
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            app.action_tab_parallel()
            await pilot.pause()
            parallel_scroll = app.query_one("#parallel-content", VerticalScroll)
            content_text = _extract_text(parallel_scroll)

            self.assertIn("PARALLEL TRANSLATIONS — Gen.1.1", content_text)
            self.assertIn("King James Version (KJV 1769)", content_text)
            self.assertIn("Berean Standard Bible (BSB 2020)", content_text)
            self.assertIn("American Standard Version (ASV 1901)", content_text)
            self.assertIn("Young's Literal Translation (YLT 1898)", content_text)
            self.assertIn("God created the heavens", content_text)

    async def test_toggle_parallel_reader(self):
        """Verify 'v' key toggles stacked parallel translations in Reader pane."""
        app = BibleStudyApp(initial_ref="Gen 1:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            w = app.verse_widgets[0]
            initial_text = _extract_text(w)
            self.assertNotIn("BSB:", initial_text)

            # Toggle parallel translations ON
            app.action_toggle_parallel()
            await pilot.pause()
            self.assertTrue(app.show_parallel)
            parallel_text = _extract_text(w)
            self.assertIn("BSB:", parallel_text)
            self.assertIn("ASV:", parallel_text)
            self.assertIn("YLT:", parallel_text)

            # Toggle parallel translations OFF
            app.action_toggle_parallel()
            await pilot.pause()
            self.assertFalse(app.show_parallel)
            final_text = _extract_text(w)
            self.assertNotIn("BSB:", final_text)

    async def test_tab_navigation_keys_and_dirty_tracking(self):
        """Verify tab switching for parallel tab and dirty tracking."""
        app = BibleStudyApp(initial_ref="Gen 1:1-5")
        async with app.run_test() as pilot:
            await pilot.pause()
            tabs = app.query_one("#inspector-tabs", TabbedContent)

            # Switch to tab-parallel
            app.action_tab_parallel()
            await pilot.pause()
            self.assertEqual(tabs.active, "tab-parallel")
            self.assertNotIn("tab-parallel", app._dirty_tabs)

            # Stepping verse marks tab-parallel dirty
            app.action_next_verse()
            await pilot.pause()
            self.assertNotIn("tab-parallel", app._dirty_tabs)  # Re-rendered immediately because active!

            # Switch to tab-syntax
            app.action_tab_syntax()
            await pilot.pause()
            self.assertEqual(tabs.active, "tab-syntax")

            # Stepping verse marks inactive tab-parallel dirty
            app.action_next_verse()
            await pilot.pause()
            self.assertIn("tab-parallel", app._dirty_tabs)

            # Switch to tab-search (key 5)
            app.action_tab_search()
            await pilot.pause()
            self.assertEqual(tabs.active, "tab-search")

    async def test_reader_pane_discourse_badges(self):
        """Verify verse widget in reader pane displays discourse logic badges."""
        app = BibleStudyApp(initial_ref="Rom 1:16")
        async with app.run_test() as pilot:
            await pilot.pause()
            w = app.verse_widgets[0]
            w_text = _extract_text(w)
            self.assertIn("Premise", w_text)
            self.assertIn("γάρ", w_text)

    async def test_syntax_tab_discourse_section(self):
        """Verify syntax tab renders detailed argument flow and discourse connector breakdown."""
        app = BibleStudyApp(initial_ref="Rom 12:1")
        async with app.run_test() as pilot:
            await pilot.pause()
            # Tab 1 (syntax) is active by default
            syntax_scroll = app.query_one("#syntax-content", VerticalScroll)
            syntax_text = _extract_text(syntax_scroll)

            self.assertIn("ARGUMENT FLOW & LOGICAL CONNECTORS", syntax_text)
            self.assertIn("Deductive Turning Point / Therefore", syntax_text)
            self.assertIn("οὖν", syntax_text)
            self.assertIn("G3767", syntax_text)
            self.assertIn("therefore", syntax_text)
            self.assertIn("doctrine to holy living", syntax_text)
            self.assertIn("Passage Context:", syntax_text)



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
