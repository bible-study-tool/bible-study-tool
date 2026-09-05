"""Comprehensive unit test suite for search.ui (TUI, CLI, Shell, StudyService)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from search.ui.formatting import (
    BOLD,
    CYAN,
    banner,
    box_panel,
    section_header,
    strip_ansi,
    style,
    wrap_text,
)
from search.ui.shell import StudyShell
from search.ui.study_service import StudyService
from search.ui.tui import BibleStudyTUI


class FormattingTests(unittest.TestCase):
    """Test terminal formatting, ANSI styling, and text wrapping."""

    def test_strip_ansi(self):
        colored = f"{BOLD}{CYAN}Hello World\033[0m"
        self.assertEqual(strip_ansi(colored), "Hello World")

    def test_style_forced(self):
        s = style("test", BOLD, CYAN, enable=True)
        self.assertIn("\033[1m", s)
        self.assertIn("\033[36m", s)
        self.assertTrue(s.endswith("\033[0m"))

        disabled = style("test", BOLD, enable=False)
        self.assertEqual(disabled, "test")

    def test_wrap_text(self):
        text = "The quick brown fox jumps over the lazy dog repeatedly to test wrapping."
        wrapped = wrap_text(text, width=30)
        self.assertTrue(len(wrapped) >= 2)
        for line in wrapped:
            self.assertLessEqual(len(line), 30)

    def test_banner_and_headers(self):
        b = banner("Bible Study", "KJV", width=60, enable_color=False)
        self.assertIn("BIBLE STUDY", b)
        self.assertIn("[KJV]", b)

        hdr = section_header("SCRIPTURE", width=50, enable_color=False)
        self.assertIn("── SCRIPTURE", hdr)

    def test_box_panel(self):
        lines = ["Line 1", "Line 2 is longer"]
        panel = box_panel("Help", lines, width=40, enable_color=False)
        self.assertIn("┌─ Help", panel)
        self.assertIn("Line 1", panel)
        self.assertIn("Line 2 is longer", panel)
        self.assertIn("└", panel)


class StudyServiceTests(unittest.TestCase):
    """Test StudyService data retrieval across Bible, Macula, Lexicons, and EGW."""

    @classmethod
    def setUpClass(cls):
        cls.service = StudyService()

    @classmethod
    def tearDownClass(cls):
        cls.service.close()

    def test_passage_study_ot_genesis(self):
        ps = self.service.get_passage_study("Gen 1:1-2")
        self.assertEqual(ps.book_code, "Gen")
        self.assertEqual(ps.book_name, "Genesis")
        self.assertEqual(len(ps.verses), 2)

        v1 = ps.verses[0]
        self.assertEqual(v1.osis, "Gen.1.1")
        self.assertEqual(v1.chapter, 1)
        self.assertEqual(v1.verse, 1)
        self.assertIn("In the beginning God created", v1.text)
        self.assertIn("H1254", v1.strongs_list)
        self.assertTrue(len(v1.semantic_frames) >= 1)
        self.assertIn("בָּרָ֣א", v1.original_text)

    def test_passage_study_nt_john(self):
        ps = self.service.get_passage_study("John 1:1")
        self.assertEqual(ps.book_code, "John")
        self.assertEqual(len(ps.verses), 1)

        v1 = ps.verses[0]
        self.assertEqual(v1.osis, "John.1.1")
        self.assertIn("In the beginning was the Word", v1.text)
        self.assertIn("G2316", v1.strongs_list)
        self.assertTrue(len(v1.semantic_frames) >= 1)
        self.assertIn("Θεόν", v1.original_text)

    def test_lookup_word_hebrew(self):
        res = self.service.lookup_word("H1254")
        self.assertIsNotNone(res)
        self.assertEqual(res.strongs_id, "H1254")
        self.assertEqual(res.language, "Hebrew")
        self.assertIn("בָּרָא", res.word)
        self.assertIn("create", res.definition.lower())
        self.assertGreater(res.occurrences_count, 0)
        # Should have Septuagint translation equivalences
        self.assertTrue(len(res.lxx_equivalences) >= 1)

    def test_lookup_word_greek(self):
        res = self.service.lookup_word("G2316")
        self.assertIsNotNone(res)
        self.assertEqual(res.strongs_id, "G2316")
        self.assertEqual(res.language, "Greek")
        self.assertIn("θεός", res.word)
        self.assertIn("theh-os", res.translit)
        self.assertGreater(res.occurrences_count, 1000)

    def test_search_unified(self):
        res = self.service.search_unified("covenant", limit_bible=3, limit_egw=3)
        self.assertEqual(res.query, "covenant")
        self.assertTrue(len(res.bible_hits) >= 1)
        self.assertTrue(len(res.egw_hits) >= 1)

    def test_navigation_next_prev(self):
        ps = self.service.get_passage_study("Gen 1")
        nxt = self.service.next_passage(ps)
        self.assertEqual(nxt, "Gen 2")

        ps2 = self.service.get_passage_study("Gen 2")
        prv = self.service.prev_passage(ps2)
        self.assertEqual(prv, "Gen 1")

        # Crossing book boundary: Gen 50 -> Exod 1
        ps50 = self.service.get_passage_study("Gen 50")
        nxt_book = self.service.next_passage(ps50)
        self.assertEqual(nxt_book, "Exod 1")

        # Exod 1 -> Gen 50
        ps_exod1 = self.service.get_passage_study("Exod 1")
        prv_book = self.service.prev_passage(ps_exod1)
        self.assertEqual(prv_book, "Gen 50")


    def test_invalid_strongs_returns_none(self):
        self.assertIsNone(self.service.lookup_word("XYZ999"))
        self.assertIsNone(self.service.lookup_word("H999999"))

    def test_passage_study_lazy_and_ensure_frames(self):
        # Fresh service to test lazy loading without pre-warmed cache
        fresh_service = StudyService()
        ps = fresh_service.get_passage_study("Lev 1:1-2", eager_frames=False)
        self.assertEqual(len(ps.verses), 2)
        v1 = ps.verses[0]
        # Frame initially empty
        self.assertEqual(len(v1.semantic_frames), 0)
        # Ensure frames on-demand
        fresh_service.ensure_verse_frames(v1)
        self.assertTrue(len(v1.semantic_frames) >= 1)
        self.assertTrue(len(v1.original_text) > 0)
        fresh_service.close()

    def test_word_lookup_caching_and_zero_samples(self):
        # sample_limit=0 avoids table scans
        w1 = self.service.lookup_word("H7225", sample_limit=0)
        self.assertIsNotNone(w1)
        self.assertEqual(len(w1.sample_verses), 0)
        self.assertEqual(w1.occurrences_count, 68)

        # Second call should hit the in-memory cache
        w2 = self.service.lookup_word("H7225", sample_limit=0)
        self.assertIs(w1, w2)

    def test_tbesh_and_tbesg_glosses_loaded(self):
        """Verify English translation glosses are populated from TBESH and TBESG."""
        w_heb = self.service.lookup_word("H1254", sample_limit=0)
        self.assertIsNotNone(w_heb)
        self.assertEqual(w_heb.gloss, "to create")

        w_grk = self.service.lookup_word("G4160", sample_limit=0)
        self.assertIsNotNone(w_grk)
        self.assertEqual(w_grk.gloss, "to do/make: do")

    def test_get_greek_gloss(self):
        """Verify helper retrieves Greek English gloss for LXX translation equivalences."""
        gloss1 = self.service.get_greek_gloss("G4160")
        self.assertEqual(gloss1, "to do/make: do")

        gloss2 = self.service.get_greek_gloss("G2936")
        self.assertEqual(gloss2, "to create")

    def test_lookup_egw_citation_flexible_formats(self):
        """Verify EGW citation lookup supports both dot and space formats."""
        p_space = self.service.lookup_egw_citation("PP 44.1")
        self.assertIsNotNone(p_space)
        self.assertEqual(p_space["id"], "PP.44.1")
        self.assertEqual(p_space["book_title"], "Patriarchs and Prophets")
        self.assertIn("Genesis 1 and 2", p_space["text"])

        p_dot = self.service.lookup_egw_citation("PP.44.1")
        self.assertIsNotNone(p_dot)
        self.assertEqual(p_dot["id"], "PP.44.1")

        p_colon = self.service.lookup_egw_citation("PP 44:1")
        self.assertIsNotNone(p_colon)
        self.assertEqual(p_colon["id"], "PP.44.1")

    def test_lookup_egw_citation_includes_page_paragraphs(self):
        """Verify looking up an EGW citation attaches all paragraphs on the page."""
        p = self.service.lookup_egw_citation("PP 44.1")
        self.assertIsNotNone(p)
        page_paras = p.get("page_paragraphs", [])
        self.assertTrue(len(page_paras) >= 3)
        self.assertEqual(page_paras[0]["id"], "PP.44.1")

    def test_get_egw_page(self):
        """Verify direct retrieval of an EGW book page."""
        paras = self.service.get_egw_page("PP", 44)
        self.assertTrue(len(paras) >= 3)
        self.assertEqual(paras[0]["page"], 44)

    def test_passage_study_full_egw_text(self):
        """Verify PassageStudy retains full paragraph text and chapter title in egw_correlations."""
        ps = self.service.get_passage_study("Gen 1:1")
        self.assertTrue(len(ps.egw_correlations) > 0)
        c0 = ps.egw_correlations[0]
        self.assertIn("text", c0)
        self.assertTrue(len(c0["text"]) > 0)
        self.assertIn("chapter_title", c0)

    def test_lookup_egw_citation_unknown_token_returns_none(self):
        """Verify that an exact EGW citation token not in the database safely returns None without FTS fallback."""
        res = self.service.lookup_egw_citation("PP 99999.1")
        self.assertIsNone(res)

    def test_passage_study_verbal_nuances(self):
        """Verify PassageStudy verses have verbal grammar nuances pre-populated."""
        ps = self.service.get_passage_study("Gen 1:1")
        self.assertTrue(len(ps.verses) >= 1)
        v = ps.verses[0]
        self.assertTrue(len(v.verbal_nuances) >= 1)
        self.assertEqual(v.verbal_nuances[0].lemma, "בָּרָא")
        self.assertIn("Exclusively Divine Initiative", v.verbal_nuances[0].theological_nuance)

    def test_get_verse_nuance_for_strongs(self):
        """Verify retrieval of verbal nuances for a specific Strong's number in a verse."""
        ps = self.service.get_passage_study("Gen 1:1")
        v = ps.verses[0]
        nuances = self.service.get_verse_nuance_for_strongs(v, "H1254")
        self.assertEqual(len(nuances), 1)
        self.assertIn("Qal (Simple Active)", nuances[0].plain_summary)

        # Test non-matching Strong's code returns empty list
        no_match = self.service.get_verse_nuance_for_strongs(v, "H9999")
        self.assertEqual(len(no_match), 0)





class StudyShellTests(unittest.TestCase):
    """Test interactive study shell commands without interactive I/O."""

    @classmethod
    def setUpClass(cls):
        cls.shell = StudyShell()

    def test_shell_execute_read(self):
        self.shell.execute("read Gen 1:1")
        self.assertIsNotNone(self.shell.current_passage)
        self.assertEqual(self.shell.current_passage.ref, "Gen 1:1")

    def test_shell_execute_study(self):
        self.shell.execute("study John 1:1")
        self.assertIsNotNone(self.shell.current_passage)
        self.assertEqual(self.shell.current_passage.book_code, "John")

    def test_shell_execute_frame(self):
        self.shell.execute("frame Gen 1:1")
        self.assertIsNotNone(self.shell.current_passage)

    def test_shell_execute_word(self):
        self.shell.execute("word H7225")
        self.shell.execute("word G2424")

    def test_shell_execute_search(self):
        self.shell.execute("search light")

    def test_shell_execute_egw(self):
        self.shell.execute("egw sanctuary")
        self.shell.execute("egw LF.172.3")

    def test_shell_execute_strongs_toggle(self):
        initial = self.shell.show_strongs
        self.shell.execute("strongs")
        self.assertEqual(self.shell.show_strongs, not initial)
        self.shell.execute("str")
        self.assertEqual(self.shell.show_strongs, initial)

    def test_shell_execute_invalid_passage(self):
        # Should not raise exception
        self.shell.execute("read NotABook 99:99")

    def test_shell_execute_navigation(self):
        self.shell.execute("read Gen 1")
        self.shell.execute("next")
        self.assertEqual(self.shell.current_passage.start_chapter, 2)
        self.shell.execute("prev")
        self.assertEqual(self.shell.current_passage.start_chapter, 1)

    def test_shell_help(self):
        self.shell.execute("help")


class BibleStudyTUITests(unittest.TestCase):
    """Test TUI state management and navigation."""

    def test_tui_state_init(self):
        tui = BibleStudyTUI(initial_ref="Gen 1:1")
        tui._load_passage("Gen 1:1")
        self.assertIsNotNone(tui.current_passage)
        self.assertEqual(tui.current_passage.book_code, "Gen")
        self.assertEqual(tui.active_pane, "reader")
        self.assertTrue(tui.show_syntax)
        self.assertTrue(tui.show_lexicon)
        self.assertTrue(tui.show_commentary)
        self.assertFalse(tui.show_search)
        self.assertFalse(tui.focus_mode)

    def test_tui_scroll_and_verse_pinning(self):
        tui = BibleStudyTUI(initial_ref="Gen 1:1-5")
        tui._load_passage("Gen 1:1-5")

        # Scroll down
        tui._scroll_down()
        self.assertEqual(tui.selected_verse_idx, 1)
        tui._scroll_up()
        self.assertEqual(tui.selected_verse_idx, 0)

        # Pinning verse
        self.assertIsNone(tui.pinned_verse_idx)
        tui._toggle_verse_pin()
        self.assertEqual(tui.pinned_verse_idx, 0)

        # Move cursor to verse 2, pinned verse stays at 0
        tui._scroll_down()
        self.assertEqual(tui.selected_verse_idx, 1)
        self.assertEqual(tui.pinned_verse_idx, 0)

        # Unpinning
        tui.selected_verse_idx = 0
        tui._toggle_verse_pin()
        self.assertIsNone(tui.pinned_verse_idx)

    def test_tui_focus_mode_toggle(self):
        tui = BibleStudyTUI(initial_ref="Gen 1:1")
        self.assertFalse(tui.focus_mode)
        tui.focus_mode = True
        self.assertTrue(tui.focus_mode)
        tui.focus_mode = False
        self.assertFalse(tui.focus_mode)

    def test_tui_multi_section_toggles(self):
        tui = BibleStudyTUI(initial_ref="Gen 1:1")
        # Toggle sections
        tui.show_syntax = False
        self.assertFalse(tui.show_syntax)
        tui.show_search = True
        self.assertTrue(tui.show_search)
        # Multiple sections active simultaneously
        active_count = sum([tui.show_syntax, tui.show_lexicon, tui.show_commentary, tui.show_search])
        self.assertEqual(active_count, 3)

    def test_tui_invalid_passage(self):
        tui = BibleStudyTUI()
        tui._load_passage("NoSuchBook 99:99")
        self.assertIn("Error", tui.status_msg)


class StudyCLITests(unittest.TestCase):
    """Test scripts/study.py CLI commands end-to-end."""

    def _run_cli(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, "scripts/study.py"] + args
        return subprocess.run(cmd, capture_output=True, text=True, check=True)

    def test_cli_read(self):
        res = self._run_cli(["read", "Gen 1:1", "--json"])
        data = json.loads(res.stdout)
        self.assertEqual(data["ref"], "Gen 1:1")
        self.assertEqual(len(data["verses"]), 1)
        self.assertIn("In the beginning", data["verses"][0]["text"])

    def test_cli_study(self):
        res = self._run_cli(["study", "Rev 14:7", "--json"])
        data = json.loads(res.stdout)
        self.assertEqual(data["ref"], "Rev 14:7")
        self.assertTrue(len(data["verses"]) >= 1)
        v = data["verses"][0]
        self.assertIn("Fear God", v["text"])
        self.assertTrue(len(v["semantic_frames"]) >= 1)

    def test_cli_word(self):
        res = self._run_cli(["word", "H1254", "--json"])
        data = json.loads(res.stdout)
        self.assertEqual(data["strongs_id"], "H1254")
        self.assertEqual(data["word"], "בָּרָא")
        self.assertGreater(data["occurrences_count"], 0)

    def test_cli_search(self):
        res = self._run_cli(["search", "sabbath", "--limit", "2", "--json"])
        data = json.loads(res.stdout)
        self.assertEqual(data["query"], "sabbath")
        self.assertTrue(len(data["bible_hits"]) >= 1)
        self.assertLessEqual(len(data["bible_hits"]), 2)

    def test_cli_search_with_book_filter(self):
        res = self._run_cli(["search", "covenant", "--limit", "3", "--book", "Heb", "--json"])
        data = json.loads(res.stdout)
        self.assertEqual(data["query"], "covenant")
        for hit in data["bible_hits"]:
            self.assertEqual(hit["osis"], "Heb")

    def test_cli_egw(self):
        res = self._run_cli(["egw", "LF.172.3", "--json"])
        data = json.loads(res.stdout)
        self.assertEqual(data["token"], "LF 172.3")
        self.assertIn("sanctuary", data["text"].lower())

    def test_cli_frame(self):
        res = self._run_cli(["frame", "John 1:1", "--json"])
        data = json.loads(res.stdout)
        self.assertEqual(data["ref"], "John 1:1")
        self.assertTrue(len(data["verses"][0]["semantic_frames"]) >= 1)


if __name__ == "__main__":
    unittest.main()
