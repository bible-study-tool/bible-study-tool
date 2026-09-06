"""Full-screen interactive Terminal User Interface (TUI) for Bible Study.

Zero-dependency curses-based interface providing dual-pane scripture reading,
original language syntactic frame inspection, Strong's lexicon lookup,
and Spirit of Prophecy correlations.
"""

from __future__ import annotations

import curses
import os
import sys
import textwrap
from typing import Any

from search.corpus.bible_books import BIBLE_BOOKS, CANONICAL_OSIS_ORDER
from search.ui.formatting import strip_ansi
from search.ui.study_service import PassageStudy, StudyService, VerseStudy, WordStudyResult


class BibleStudyTUI:
    """Curses-driven full-screen Bible study workstation."""

    def __init__(self, service: StudyService | None = None, initial_ref: str = "Gen 1:1") -> None:
        self.service = service or StudyService()
        self.initial_ref = initial_ref
        self.current_passage: PassageStudy | None = None
        self.selected_verse_idx: int = 0
        self.pinned_verse_idx: int | None = None
        self.reader_scroll: int = 0
        self.inspector_scroll: int = 0
        self.active_pane: str = "reader"  # 'reader' or 'inspector'
        self.show_syntax: bool = True
        self.show_lexicon: bool = True
        self.show_commentary: bool = True
        self.show_search: bool = False
        self.focus_mode: bool = False
        self.show_strongs: bool = False
        self.search_results: list[dict[str, Any]] = []
        self.last_search_query: str = ""
        self.status_msg: str = "Welcome! Use [g]oto, [n/p] nav, [Space] pin, [1-4] sections, [f]ocus, [q]uit."
        self.stdscr: Any = None
        self._cached_inspector_lines: list[tuple[str, int]] = []
        self._cached_inspector_key: tuple[Any, ...] | None = None

    def start(self) -> None:
        """Entry point with curses initialization and graceful fallback."""
        try:
            curses.wrapper(self._main_loop)
        except curses.error as e:
            # Terminal might not support curses (dumb terminal, piped stdin)
            print(f"Terminal does not support full-screen curses ({e}). Launching shell...")
            from search.ui.shell import StudyShell
            shell = StudyShell(self.service)
            shell.run()

    def _main_loop(self, stdscr: Any) -> None:
        self.stdscr = stdscr
        curses.curs_set(0)
        curses.use_default_colors()
        stdscr.keypad(True)
        stdscr.timeout(100)  # Non-blocking input refresh every 100ms

        # Color pairs setup
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_CYAN, -1)     # Header/Title
            curses.init_pair(2, curses.COLOR_YELLOW, -1)   # Verse numbers / highlights
            curses.init_pair(3, curses.COLOR_GREEN, -1)    # Original text / Success
            curses.init_pair(4, curses.COLOR_MAGENTA, -1)  # Strong's numbers
            curses.init_pair(5, curses.COLOR_BLUE, -1)     # Sub-headers
            curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Status bar
            curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_CYAN)  # Selected tab

        # Load initial passage
        self._load_passage(self.initial_ref)

        needs_render = True
        while True:
            if needs_render:
                self._render()
                needs_render = False

            try:
                ch = stdscr.getch()
            except Exception:
                continue

            if ch == -1:
                continue

            needs_render = True

            if ch in (ord("q"), ord("Q")):
                break
            elif ch == curses.KEY_RESIZE:
                stdscr.clear()
            elif ch in (ord("\t"), 9):  # Tab
                self.active_pane = "inspector" if self.active_pane == "reader" else "reader"
            elif ch in (ord("l"), ord("L"), ord("n"), ord("N"), curses.KEY_RIGHT):
                self._next_chapter()
            elif ch in (ord("h"), ord("H"), ord("p"), ord("P"), curses.KEY_LEFT):
                self._prev_chapter()
            elif ch in (ord("f"), ord("F")):
                self.focus_mode = not self.focus_mode
                self.status_msg = f"Focus Mode: {'ENABLED (Full-Width Reader)' if self.focus_mode else 'DISABLED (Split View)'}"
            elif ch in (ord(" "), 10, 13):  # Space or Enter
                self._toggle_verse_pin()
            elif ch in (ord("s"), ord("S")):
                self.show_strongs = not self.show_strongs
                self.status_msg = f"Strong's display: {'ENABLED' if self.show_strongs else 'DISABLED'}"
            elif ch in (ord("g"), ord("G")):
                self._prompt_goto()
            elif ch in (ord("/"),):
                self._prompt_search()
            elif ch == ord("1"):
                self.show_syntax = not self.show_syntax
                self.inspector_scroll = 0
                self.status_msg = f"Syntax section: {'ENABLED' if self.show_syntax else 'DISABLED'}"
            elif ch == ord("2"):
                self.show_lexicon = not self.show_lexicon
                self.inspector_scroll = 0
                self.status_msg = f"Lexicon section: {'ENABLED' if self.show_lexicon else 'DISABLED'}"
            elif ch == ord("3"):
                self.show_commentary = not self.show_commentary
                self.inspector_scroll = 0
                self.status_msg = f"EGW Commentary section: {'ENABLED' if self.show_commentary else 'DISABLED'}"
            elif ch == ord("4"):
                self.show_search = not self.show_search
                self.inspector_scroll = 0
                self.status_msg = f"Search section: {'ENABLED' if self.show_search else 'DISABLED'}"
            elif ch == ord("?"):
                self._show_help()
            elif ch == curses.KEY_DOWN or ch == ord("j"):
                self._scroll_down()
            elif ch == curses.KEY_UP or ch == ord("k"):
                self._scroll_up()
            elif ch == curses.KEY_NPAGE:  # Page Down
                for _ in range(10):
                    self._scroll_down()
            elif ch == curses.KEY_PPAGE:  # Page Up
                for _ in range(10):
                    self._scroll_up()

    def _toggle_verse_pin(self) -> None:
        if not self.current_passage or not self.current_passage.verses:
            return
        if self.pinned_verse_idx == self.selected_verse_idx:
            self.pinned_verse_idx = None
            v = self.current_passage.verses[self.selected_verse_idx]
            self.status_msg = f"Verse {v.verse} unpinned (inspector follows cursor)"
        else:
            self.pinned_verse_idx = self.selected_verse_idx
            v = self.current_passage.verses[self.selected_verse_idx]
            self.status_msg = f"Verse {v.verse} pinned for inspection (press Space/Enter to unpin)"

    def _load_passage(self, passage_ref: str) -> None:
        try:
            study = self.service.get_passage_study(passage_ref)
            if study.verses:
                self.current_passage = study
                self.selected_verse_idx = 0
                self.pinned_verse_idx = None
                self.reader_scroll = 0
                self.inspector_scroll = 0
                self.status_msg = f"Loaded {study.book_name} {study.start_chapter}"
            else:
                self.status_msg = f"No verses found for '{passage_ref}'"
        except Exception as e:
            self.status_msg = f"Error loading passage '{passage_ref}': {e}"

    def _next_chapter(self) -> None:
        if not self.current_passage:
            return
        nxt = self.service.next_passage(self.current_passage)
        if nxt:
            self._load_passage(nxt)
        else:
            self.status_msg = "Reached the end of Revelation!"

    def _prev_chapter(self) -> None:
        if not self.current_passage:
            return
        prv = self.service.prev_passage(self.current_passage)
        if prv:
            self._load_passage(prv)
        else:
            self.status_msg = "Reached the beginning of Genesis!"

    def _scroll_down(self) -> None:
        if self.active_pane == "reader" or self.focus_mode:
            if self.current_passage and self.selected_verse_idx + 1 < len(self.current_passage.verses):
                self.selected_verse_idx += 1
                max_y, _ = self.stdscr.getmaxyx() if self.stdscr else (24, 80)
                visible_threshold = max(3, (max_y - 6) // 2)
                if self.selected_verse_idx - self.reader_scroll > visible_threshold:
                    self.reader_scroll += 1
        else:
            self.inspector_scroll += 1

    def _scroll_up(self) -> None:
        if self.active_pane == "reader" or self.focus_mode:
            if self.selected_verse_idx > 0:
                self.selected_verse_idx -= 1
                if self.selected_verse_idx < self.reader_scroll:
                    self.reader_scroll = max(0, self.reader_scroll - 1)
        else:
            self.inspector_scroll = max(0, self.inspector_scroll - 1)

    def _prompt_goto(self) -> None:
        ref = self._prompt_input("Goto passage (e.g. 'John 3:16', 'Ps 23', 'Rom 8'): ")
        if ref:
            self._load_passage(ref)

    def _prompt_search(self) -> None:
        query = self._prompt_input("Search Bible & EGW: ")
        if query:
            self.last_search_query = query
            res = self.service.search_unified(query, limit_bible=10, limit_egw=5)
            self.search_results = []
            for b in res.bible_hits:
                osis_ref = f"{b.get('osis')}.{b.get('chapter')}.{b.get('verse')}"
                self.search_results.append({
                    "type": "bible",
                    "ref": osis_ref,
                    "text": b.get("clean_text") or b.get("text", ""),
                })
            for e in res.egw_hits:
                self.search_results.append({
                    "type": "egw",
                    "ref": e.get("token", ""),
                    "text": e.get("snippet", ""),
                })
            self.show_search = True
            self.active_pane = "inspector"
            self.status_msg = f"Search '{query}' returned {len(self.search_results)} results (Section 4 active)"

    def _prompt_input(self, prompt: str) -> str:
        max_y, max_x = self.stdscr.getmaxyx()
        self.stdscr.attron(curses.color_pair(6) if curses.has_colors() else curses.A_REVERSE)
        self.stdscr.addstr(max_y - 1, 0, " " * (max_x - 1))
        self.stdscr.addstr(max_y - 1, 1, prompt[:max_x - 2])
        self.stdscr.attroff(curses.color_pair(6) if curses.has_colors() else curses.A_REVERSE)
        self.stdscr.refresh()

        curses.noecho()
        curses.curs_set(1)
        buf: list[str] = []
        prompt_len = len(prompt) + 1
        while True:
            ch = self.stdscr.getch()
            if ch in (10, 13):  # Enter
                break
            elif ch in (27,):  # Escape
                buf = []
                break
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                if buf:
                    buf.pop()
                    self.stdscr.addstr(max_y - 1, prompt_len + len(buf), " ")
                    self.stdscr.move(max_y - 1, prompt_len + len(buf))
            elif 32 <= ch <= 126:
                if prompt_len + len(buf) < max_x - 2:
                    buf.append(chr(ch))
                    self.stdscr.addstr(max_y - 1, prompt_len + len(buf) - 1, chr(ch))

        curses.curs_set(0)
        return "".join(buf).strip()

    def _show_help(self) -> None:
        max_y, max_x = self.stdscr.getmaxyx()
        h, w = min(20, max_y - 4), min(72, max_x - 4)
        top, left = (max_y - h) // 2, (max_x - w) // 2
        win = curses.newwin(h, w, top, left)
        win.box()
        win.keypad(True)
        title = " BIBLE STUDY TOOL — KEYBOARD SHORTCUTS "
        win.addstr(0, max(1, (w - len(title)) // 2), title, curses.A_BOLD)

        shortcuts = [
            ("g", "Goto passage (e.g. 'John 3:16', 'Ps 23', 'Rom 8')"),
            ("h / l", "Previous / Next chapter (also n / p)"),
            ("Space/Enter", "Pin / unpin selected verse for side panel study"),
            ("Tab", "Toggle focus between Scripture Reader and Inspector"),
            ("j / k", "Scroll down / up (or Up/Down arrow keys)"),
            ("PgUp/Dn", "Page up / Page down"),
            ("1 - 4", "Toggle Inspector sections (1:Syntax, 2:Lex, 3:EGW, 4:Find)"),
            ("f", "Toggle Focus Mode (full-width reader)"),
            ("s", "Toggle inline Strong's numbers in reader"),
            ("/", "Search Bible and Spirit of Prophecy writings"),
            ("?", "Show this help screen"),
            ("q", "Quit Bible Study Tool"),
        ]

        for idx, (key, desc) in enumerate(shortcuts, 1):
            if idx + 1 >= h - 1:
                break
            win.addstr(idx + 1, 3, f"{key:<12}", curses.A_BOLD)
            win.addstr(idx + 1, 16, desc[:w - 18])

        footer = " Press any key to return "
        win.addstr(h - 1, max(1, (w - len(footer)) // 2), footer, curses.A_DIM)
        win.refresh()
        win.getch()

    def _render(self) -> None:
        max_y, max_x = self.stdscr.getmaxyx()
        if max_y < 16 or max_x < 50:
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, "Terminal too small. Resize to at least 80x24.")
            self.stdscr.refresh()
            return

        self.stdscr.erase()

        # 1. Header Bar (Row 0)
        self._render_header(max_x)

        # 2. Panes
        pane_h = max_y - 3  # Leave row 0 for header, bottom 2 rows for status/keys
        if self.focus_mode:
            self._render_reader_pane(1, 0, pane_h, max_x)
        else:
            reader_w = int(max_x * 0.55)
            inspector_w = max_x - reader_w
            self._render_reader_pane(1, 0, pane_h, reader_w)
            self._render_inspector_pane(1, reader_w, pane_h, inspector_w)

        # 3. Bottom Status & Hotkeys Bar
        self._render_footer(max_y, max_x)

        self.stdscr.refresh()

    def _render_header(self, max_x: int) -> None:
        title = " ADVENTIST BIBLE STUDY TOOL "
        p_ref = self.current_passage.ref.upper() if self.current_passage else "NO PASSAGE"
        focus_tag = " [FOCUS MODE]" if self.focus_mode else ""
        hdr_right = f" {p_ref} (KJV){focus_tag} "

        self.stdscr.attron(curses.color_pair(6) if curses.has_colors() else curses.A_REVERSE)
        self.stdscr.addstr(0, 0, " " * (max_x - 1))
        self.stdscr.addstr(0, 1, title[:max_x - 2], curses.A_BOLD)
        if len(title) + len(hdr_right) < max_x:
            self.stdscr.addstr(0, max_x - len(hdr_right) - 1, hdr_right, curses.A_BOLD)
        self.stdscr.attroff(curses.color_pair(6) if curses.has_colors() else curses.A_REVERSE)

    def _render_reader_pane(self, top: int, left: int, height: int, width: int) -> None:
        win = self.stdscr.subwin(height, width, top, left)
        is_active = self.active_pane == "reader" or self.focus_mode
        border_attr = curses.color_pair(1) if (is_active and curses.has_colors()) else curses.A_DIM
        win.attron(border_attr)
        win.box()
        title = f" SCRIPTURE READER {'[ACTIVE]' if is_active else ''} "
        win.addstr(0, 2, title[:width - 4], curses.A_BOLD | (curses.color_pair(2) if is_active else 0))
        win.attroff(border_attr)

        if not self.current_passage or not self.current_passage.verses:
            win.addstr(2, 2, "No passage loaded. Press 'g' to goto a book/chapter.")
            return

        verses = self.current_passage.verses
        visible_lines = height - 2
        y = 1

        for idx in range(self.reader_scroll, len(verses)):
            if y >= visible_lines:
                break
            v = verses[idx]
            is_selected = idx == self.selected_verse_idx
            is_pinned = idx == self.pinned_verse_idx

            pin_marker = "*" if is_pinned else " "
            prefix = f"{v.verse:>3}{pin_marker} "
            v_text = v.text
            if self.show_strongs:
                tokens_str = []
                for tok in v.tokens:
                    t_text = tok.get("text", "")
                    s_codes = tok.get("strongs", [])
                    if s_codes:
                        tokens_str.append(f"{t_text}[{','.join(s_codes)}]")
                    else:
                        tokens_str.append(t_text)
                v_text = " ".join(tokens_str)

            # Text wrapping for the verse
            wrapped = textwrap.wrap(v_text, width=width - 8)
            if not wrapped:
                wrapped = [""]

            for line_idx, line in enumerate(wrapped):
                if y >= visible_lines:
                    break
                line_prefix = prefix if line_idx == 0 else "      "
                
                # Selection highlight
                if is_selected:
                    line_attr = curses.color_pair(2) | curses.A_BOLD if curses.has_colors() else curses.A_STANDOUT
                    pointer = ">" if line_idx == 0 else " "
                    win.addstr(y, 1, pointer, line_attr)
                    win.addstr(y, 2, line_prefix, line_attr)
                    win.addstr(y, 2 + len(line_prefix), line[:width - len(line_prefix) - 4], line_attr)
                elif is_pinned:
                    line_attr = curses.color_pair(1) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
                    win.addstr(y, 2, line_prefix, line_attr)
                    win.addstr(y, 2 + len(line_prefix), line[:width - len(line_prefix) - 4], line_attr)
                else:
                    win.addstr(y, 2, line_prefix, curses.color_pair(2) | curses.A_BOLD if line_idx == 0 else 0)
                    win.addstr(y, 2 + len(line_prefix), line[:width - len(line_prefix) - 4])
                y += 1

            y += 1  # Blank line between verses

    def _render_inspector_pane(self, top: int, left: int, height: int, width: int) -> None:
        win = self.stdscr.subwin(height, width, top, left)
        is_active = self.active_pane == "inspector"
        border_attr = curses.color_pair(1) if (is_active and curses.has_colors()) else curses.A_DIM
        win.attron(border_attr)
        win.box()

        # Tabs / badges at top border indicating active sections
        tabs = [
            ("1:Syntax", self.show_syntax),
            ("2:Lex", self.show_lexicon),
            ("3:EGW", self.show_commentary),
            ("4:Find", self.show_search),
        ]
        tab_x = 2
        for t_label, is_on in tabs:
            badge = f"[{t_label} {'✓' if is_on else ' '}]"
            if tab_x + len(badge) >= width - 2:
                break
            t_style = (curses.color_pair(7) | curses.A_BOLD) if is_on else curses.A_DIM
            win.addstr(0, tab_x, badge, t_style)
            tab_x += len(badge) + 1

        win.attroff(border_attr)

        cur_verse: VerseStudy | None = None
        inspected_idx = self.pinned_verse_idx if self.pinned_verse_idx is not None else self.selected_verse_idx
        if self.current_passage and self.current_passage.verses:
            if 0 <= inspected_idx < len(self.current_passage.verses):
                cur_verse = self.current_passage.verses[inspected_idx]
                if self.show_syntax:
                    self.service.ensure_verse_frames(cur_verse)

        is_pinned = self.pinned_verse_idx is not None
        cache_key = (
            cur_verse.osis if cur_verse else None,
            is_pinned,
            self.show_syntax,
            self.show_lexicon,
            self.show_commentary,
            self.show_search,
            len(self.search_results),
            self.last_search_query,
            width,
        )

        if cache_key == self._cached_inspector_key:
            content_lines = self._cached_inspector_lines
        else:
            content_lines = []
            pin_tag = " [PINNED]" if is_pinned else ""
            v_title = f"VERSE INSPECTOR: {cur_verse.osis}{pin_tag}" if cur_verse else "VERSE INSPECTOR"
            content_lines.append((v_title, curses.color_pair(2) | curses.A_BOLD))
            content_lines.append(("", 0))

            if not (self.show_syntax or self.show_lexicon or self.show_commentary or self.show_search):
                content_lines.append(("ALL INSPECTOR SECTIONS ARE HIDDEN", curses.color_pair(1) | curses.A_BOLD))
                content_lines.append(("", 0))
                content_lines.append(("Press [1] to toggle Original Syntax", curses.A_NORMAL))
                content_lines.append(("Press [2] to toggle Concordance & Strong's", curses.A_NORMAL))
                content_lines.append(("Press [3] to toggle Spirit of Prophecy / EGW", curses.A_NORMAL))
                content_lines.append(("Press [4] to toggle Search Results", curses.A_NORMAL))
                content_lines.append(("", 0))
                content_lines.append(("Press [Space] or [Enter] on a verse to pin it.", curses.A_DIM))

            # Section 1: Original Language Syntax & Semantic Frames
            if self.show_syntax:
                content_lines.append(("── [1: ORIGINAL SYNTAX & CLAUSE FRAMES] ──", curses.color_pair(1) | curses.A_BOLD))
                if cur_verse:
                    if cur_verse.original_text:
                        content_lines.append((f"Text: {cur_verse.original_text}", curses.color_pair(3) | curses.A_BOLD))
                        content_lines.append(("", 0))

                    if cur_verse.semantic_frames:
                        for cl in cur_verse.semantic_frames:
                            c_num = cl.get("clause_num", 1)
                            content_lines.append((f"Clause {c_num} [{cl.get('rule', '')}]:", curses.color_pair(1) | curses.A_BOLD))
                            for label, items in [
                                ("Agent", cl.get("agents", [])),
                                ("Action", cl.get("actions", [])),
                                ("Patient", cl.get("patients", [])),
                                ("Context", cl.get("context", [])),
                            ]:
                                if items:
                                    it_str = ", ".join(f"{it['text']}" for it in items)
                                    content_lines.append((f"  * {label}: {it_str}", 0))
                            content_lines.append(("", 0))
                    else:
                        content_lines.append(("No syntactic clause tree available for this verse.", curses.A_DIM))
                else:
                    content_lines.append(("No verse selected.", curses.A_DIM))
                content_lines.append(("", 0))

            # Section 2: Lexicon & Strong's Concordance
            if self.show_lexicon:
                content_lines.append(("── [2: CONCORDANCE & STRONG'S LEXICON] ──", curses.color_pair(4) | curses.A_BOLD))
                if cur_verse:
                    seen = set()
                    strongs_entries_found = 0
                    for s_code in cur_verse.strongs_list:
                        if s_code in seen:
                            continue
                        seen.add(s_code)
                        w_res = self.service.lookup_word(s_code, sample_limit=0)
                        if w_res:
                            strongs_entries_found += 1
                            content_lines.append((f"• {w_res.strongs_id} ({w_res.language}): {w_res.word} ({w_res.translit})", curses.color_pair(3) | curses.A_BOLD))
                            if w_res.gloss:
                                content_lines.append((f"  Gloss: {w_res.gloss}", curses.color_pair(1)))
                            content_lines.append((f"  Occurrences in KJV: {w_res.occurrences_count}", curses.A_DIM))
                            def_lines = [l.strip() for l in w_res.definition.splitlines() if l.strip() and not l.startswith("Strong's Number")]
                            if def_lines:
                                content_lines.append((f"  Def: {def_lines[0]}", 0))
                            content_lines.append(("", 0))
                    if strongs_entries_found == 0:
                        content_lines.append(("No Strong's concordance numbers tagged for this verse.", curses.A_DIM))
                else:
                    content_lines.append(("No verse selected.", curses.A_DIM))
                content_lines.append(("", 0))

            # Section 3: Spirit of Prophecy / EGW Correlations
            if self.show_commentary:
                content_lines.append(("── [3: SPIRIT OF PROPHECY CORRELATIONS] ──", curses.color_pair(2) | curses.A_BOLD))
                if self.current_passage and self.current_passage.egw_correlations:
                    for egw in self.current_passage.egw_correlations:
                        content_lines.append((f"[{egw['token']}] {egw.get('heading', '')}", curses.color_pair(1) | curses.A_BOLD))
                        snip = egw.get("snippet", "").replace("[b]", "").replace("[/b]", "")
                        content_lines.append((snip, 0))
                        content_lines.append(("", 0))
                else:
                    content_lines.append(("No direct EGW chapter correlations found for this chapter.", curses.A_DIM))
                    content_lines.append(("Press [/] to search all EGW writings by keyword.", curses.A_DIM))
                content_lines.append(("", 0))

            # Section 4: Search Results & Findings
            if self.show_search:
                content_lines.append((f"── [4: SEARCH FINDINGS: '{self.last_search_query}'] ──", curses.color_pair(5) | curses.A_BOLD))
                if self.search_results:
                    for item in self.search_results:
                        tag = "[BIBLE]" if item["type"] == "bible" else "[EGW]"
                        color = curses.color_pair(2) if item["type"] == "bible" else curses.color_pair(1)
                        content_lines.append((f"{tag} {item['ref']}", color | curses.A_BOLD))
                        content_lines.append((item["text"][:width - 4], 0))
                        content_lines.append(("", 0))
                else:
                    content_lines.append(("No search performed yet. Press [/] to search.", curses.A_DIM))
                content_lines.append(("", 0))

            self._cached_inspector_key = cache_key
            self._cached_inspector_lines = content_lines

        # Render content lines with word wrap and inspector scroll
        y = 1
        visible_lines = height - 2
        line_idx = 0

        for text, attr in content_lines:
            if not text:
                if line_idx >= self.inspector_scroll and y < visible_lines:
                    y += 1
                line_idx += 1
                continue

            wrapped = textwrap.wrap(text, width=width - 4)
            for w_line in wrapped:
                if line_idx >= self.inspector_scroll:
                    if y < visible_lines:
                        win.addstr(y, 2, w_line[:width - 4], attr)
                        y += 1
                line_idx += 1

    def _render_footer(self, max_y: int, max_x: int) -> None:
        # Line max_y - 2: Status Message
        msg = f" {self.status_msg} "
        self.stdscr.addstr(max_y - 2, 0, msg[:max_x - 1], curses.color_pair(2) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD)

        # Line max_y - 1: Hotkeys Overview
        hotkeys = " [g]oto  [h/l] Nav  [Space] Pin  [1-4] Sections  [f]ocus  [s]trongs  [/] Find  [?] Help  [q]uit"
        self.stdscr.attron(curses.color_pair(6) if curses.has_colors() else curses.A_REVERSE)
        self.stdscr.addstr(max_y - 1, 0, " " * (max_x - 1))
        self.stdscr.addstr(max_y - 1, 0, hotkeys[:max_x - 1])
        self.stdscr.attroff(curses.color_pair(6) if curses.has_colors() else curses.A_REVERSE)


def run_tui(service: StudyService | None = None, initial_ref: str = "Gen 1:1") -> None:
    """Launch the interactive terminal user interface."""
    app = BibleStudyTUI(service=service, initial_ref=initial_ref)
    app.start()
