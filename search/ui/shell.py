"""Interactive Readline Study Shell for Adventist Bible Study Tool.

Zero-dependency, resilient terminal REPL providing immediate, rich Scripture
study, original language exploration, Strong's concordances, and commentary lookups.
"""

from __future__ import annotations

import atexit
import os
import readline
import shlex
import sys
from pathlib import Path
from typing import Sequence

from search.corpus.bible_books import CANONICAL_OSIS_ORDER, BIBLE_BOOKS
from search.linking.egw import is_egw_token, normalize_token
from search.ui.formatting import (
    BOLD,
    CYAN,
    GREEN,
    MAGENTA,
    YELLOW,
    BLUE,
    DIM,
    RESET,
    banner,
    box_panel,
    section_header,
    style,
    terminal_width,
    wrap_text,
)
from search.ui.study_service import PassageStudy, StudyService, UnifiedSearchResult, WordStudyResult

HISTORY_FILE = Path.home() / ".bible_study_shell_history"

COMMANDS = [
    "read",
    "study",
    "search",
    "word",
    "egw",
    "frame",
    "strongs",
    "next",
    "prev",
    "tui",
    "help",
    "quit",
    "exit",
    "clear",
]


class StudyShellCompleter:
    """Readline tab completer for commands and biblical book names."""

    def __init__(self) -> None:
        self.words = list(COMMANDS)
        for b in BIBLE_BOOKS.values():
            self.words.append(b.name)
            self.words.append(b.osis)

    def complete(self, text: str, state: int) -> str | None:
        line = ""
        try:
            line = readline.get_line_buffer()
        except Exception:
            pass

        tokens = line.lstrip().split()
        if not tokens or (len(tokens) == 1 and not line.endswith(" ")):
            matches = [w for w in self.words if w.lower().startswith(text.lower())]
        else:
            # Completing an argument
            remainder = line[len(tokens[0]):].strip()
            matches = [w for w in self.words if w.lower().startswith(remainder.lower())]
            if not matches:
                matches = [w for w in self.words if w.lower().startswith(text.lower())]

        if state < len(matches):
            return matches[state]
        return None


class StudyShell:
    """Interactive CLI study environment."""

    def __init__(self, service: StudyService | None = None) -> None:
        self.service = service or StudyService()
        self.current_passage: PassageStudy | None = None
        self.show_strongs: bool = False
        self._setup_readline()

    def _setup_readline(self) -> None:
        try:
            completer = StudyShellCompleter()
            readline.set_completer(completer.complete)
            readline.set_completer_delims(" \t\n`~!@#$%^&*()=+[{]}\\|;:'\",<>?")
            readline.parse_and_bind("tab: complete")
            if HISTORY_FILE.exists():
                try:
                    readline.read_history_file(str(HISTORY_FILE))
                except Exception:
                    pass
            atexit.register(self._save_history)
        except Exception:
            pass

    def _save_history(self) -> None:
        try:
            readline.set_history_length(1000)
            readline.write_history_file(str(HISTORY_FILE))
        except Exception:
            pass

    def run(self) -> None:
        """Run the interactive REPL loop."""
        w = terminal_width()
        print(banner("Adventist Bible Study Tool", "Interactive Study Shell", width=w))
        print(style("  Type 'help' for commands, or enter a passage (e.g. 'John 1', 'Gen 1:1-5').", DIM))
        print(style("  Type 'tui' to open full-screen interface, 'exit' or 'q' to leave.\n", DIM))

        while True:
            try:
                prompt_label = self.current_passage.ref if self.current_passage else "study"
                prompt = style(f"[{prompt_label}]> ", BOLD, CYAN)
                line = input(prompt).strip()
                if not line:
                    continue

                if line.lower() in ("exit", "quit", "q", ":q"):
                    print(style("\nGrace and peace in your study. Goodbye!\n", BOLD, GREEN))
                    break

                self.execute(line)

            except (KeyboardInterrupt, EOFError):
                print(style("\nExiting Bible Study Tool.\n", DIM))
                break
            except Exception as e:
                print(style(f"\nError: {e}\n", BOLD, YELLOW))

    def execute(self, cmd_line: str) -> None:
        """Parse and execute a study command string."""
        try:
            parts = shlex.split(cmd_line)
        except ValueError:
            parts = cmd_line.split()

        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ("help", "?"):
            self.cmd_help()
        elif cmd in ("clear", "cls"):
            os.system("clear" if os.name == "posix" else "cls")
        elif cmd == "tui":
            from search.ui.tui import run_tui
            run_tui(self.service, initial_ref=self.current_passage.ref if self.current_passage else "Gen 1:1")
        elif cmd in ("read", "r"):
            ref = " ".join(args) if args else (self.current_passage.ref if self.current_passage else "Gen 1")
            self.cmd_read(ref)
        elif cmd in ("study", "s"):
            ref = " ".join(args) if args else (self.current_passage.ref if self.current_passage else "Gen 1:1")
            self.cmd_study(ref)
        elif cmd in ("frame", "f"):
            ref = " ".join(args) if args else (self.current_passage.ref if self.current_passage else "Gen 1:1")
            self.cmd_frame(ref)
        elif cmd in ("strongs", "str"):
            self.show_strongs = not self.show_strongs
            status = "ENABLED" if self.show_strongs else "DISABLED"
            print(style(f"Inline Strong's concordance tags: {status}", CYAN))
            if self.current_passage:
                self.cmd_read(self.current_passage.ref)
        elif cmd in ("word", "w"):
            if not args:
                print(style("Usage: word <strongs_code> (e.g. 'word H1254', 'word G2316')", YELLOW))
                return
            self.cmd_word(args[0])
        elif cmd in ("egw", "commentary"):
            if not args:
                print(style("Usage: egw <query_or_token> (e.g. 'egw sanctuary', 'egw PP.57.1')", YELLOW))
                return
            self.cmd_egw(" ".join(args))
        elif cmd in ("search", "/"):
            if not args:
                print(style("Usage: search <keywords> (e.g. 'search covenant of peace')", YELLOW))
                return
            self.cmd_search(" ".join(args))
        elif cmd in ("next", "n"):
            self.cmd_next()
        elif cmd in ("prev", "p"):
            self.cmd_prev()
        else:
            # Check if input directly looks like a scripture reference
            try:
                self.cmd_read(cmd_line)
            except Exception:
                print(style(f"Unknown command: '{cmd}'. Type 'help' for available commands.", YELLOW))

    def cmd_read(self, passage_ref: str) -> None:
        """Render readable scripture passage with verse numbers."""
        try:
            study = self.service.get_passage_study(passage_ref)
        except (ValueError, KeyError) as e:
            print(style(f"Invalid passage reference '{passage_ref}': {e}", YELLOW))
            return
        if not study.verses:
            print(style(f"No verses found for reference '{passage_ref}'.", YELLOW))
            return

        self.current_passage = study
        w = terminal_width()

        header_str = f"{study.book_name} {study.start_chapter}"
        if study.start_verse != study.end_verse:
            header_str += f":{study.start_verse}-{study.end_verse}"
        elif study.start_verse:
            header_str += f":{study.start_verse}"

        print(section_header(f"SCRIPTURE: {header_str} (King James Version)", width=w))

        for v in study.verses:
            v_num = style(f" {v.verse:>2} ", BOLD, YELLOW)
            if self.show_strongs:
                # Render inline Strong's tokens
                token_parts = []
                for tok in v.tokens:
                    t_text = tok.get("text", "")
                    s_codes = tok.get("strongs", [])
                    if s_codes:
                        s_str = style(f"[{','.join(s_codes)}]", MAGENTA, DIM)
                        token_parts.append(f"{t_text}{s_str}")
                    else:
                        token_parts.append(t_text)
                verse_text = " ".join(token_parts)
            else:
                verse_text = v.text

            wrapped = wrap_text(verse_text, width=w, indent="     ")
            if wrapped:
                wrapped[0] = f"{v_num} {wrapped[0].strip()}"
                print("\n".join(wrapped))

        print()

    def cmd_study(self, passage_ref: str) -> None:
        """Render comprehensive multi-dimensional study view."""
        try:
            study = self.service.get_passage_study(passage_ref)
        except (ValueError, KeyError) as e:
            print(style(f"Invalid passage reference '{passage_ref}': {e}", YELLOW))
            return
        if not study.verses:
            print(style(f"No verses found for '{passage_ref}'.", YELLOW))
            return

        self.current_passage = study
        w = terminal_width()

        header_str = f"{study.book_name} {study.start_chapter}"
        if study.start_verse != study.end_verse:
            header_str += f":{study.start_verse}-{study.end_verse}"
        elif study.start_verse:
            header_str += f":{study.start_verse}"

        print(banner(f"Study: {header_str}", "Scripture · Original Language · Lexicon · Spirit of Prophecy", width=w))

        # 1. Scripture Text
        print(section_header("1. SCRIPTURE PASSAGE (KJV)", width=w))
        for v in study.verses:
            v_num = style(f" {v.verse:>2} ", BOLD, YELLOW)
            print(f"{v_num} {v.text}")
        print()

        # 2. Original Language & Syntactic Frames
        print(section_header("2. ORIGINAL LANGUAGE & SYNTACTIC FRAMES (MACULA)", width=w))
        for v in study.verses:
            if v.original_text:
                print(style(f"  [{v.osis}] Original Text: ", BOLD, GREEN) + v.original_text)
            if v.semantic_frames:
                for cl in v.semantic_frames:
                    c_num = cl.get("clause_num", 1)
                    summary = cl.get("summary", "")
                    print(style(f"    Clause {c_num}: ", CYAN, BOLD) + summary)
            else:
                print(style(f"    (No syntactic clause trees recorded for {v.osis})", DIM))
        print()

        # 3. Key Lexical Words (Strong's)
        print(section_header("3. KEY LEXICAL CONCORDANCE (STRONG'S)", width=w))
        seen_strongs = set()
        for v in study.verses:
            for s_code in v.strongs_list[:6]:
                if s_code in seen_strongs:
                    continue
                seen_strongs.add(s_code)
                w_res = self.service.lookup_word(s_code)
                if w_res:
                    word_display = f"{w_res.word} ({w_res.translit})" if w_res.translit else w_res.word
                    gloss_display = f" - {w_res.gloss}" if w_res.gloss else ""
                    print(
                        style(f"  {w_res.strongs_id:>6}: ", BOLD, MAGENTA)
                        + style(word_display, BOLD, GREEN)
                        + style(gloss_display, CYAN)
                    )
                    # First line of definition
                    def_lines = [l for l in w_res.definition.splitlines() if l.strip() and not l.startswith("Strong's Number")]
                    if def_lines:
                        print(style(f"          {def_lines[0]}", DIM))
        print()

        # 4. Spirit of Prophecy Cross-References
        print(section_header("4. SPIRIT OF PROPHECY & COMMENTARY CORRELATIONS", width=w))
        if study.egw_correlations:
            for egw in study.egw_correlations[:3]:
                tok_str = style(f"  [{egw['token']}]", BOLD, BLUE)
                head_str = style(f" {egw['heading']}", BOLD) if egw.get("heading") else ""
                print(f"{tok_str}{head_str}")
                snip = egw.get("snippet", "").replace("[b]", style("", BOLD, YELLOW)).replace("[/b]", style("", RESET))
                wrapped_snip = wrap_text(snip, width=w, indent="    ")
                print("\n".join(wrapped_snip))
                print()
        else:
            print(style("  No direct Spirit of Prophecy commentary citations found for this chapter.\n", DIM))

    def cmd_frame(self, passage_ref: str) -> None:
        """Display detailed syntactic participant frames."""
        try:
            study = self.service.get_passage_study(passage_ref)
        except (ValueError, KeyError) as e:
            print(style(f"Invalid passage reference '{passage_ref}': {e}", YELLOW))
            return
        if not study.verses:
            print(style(f"No verses found for '{passage_ref}'.", YELLOW))
            return
        self.current_passage = study
        w = terminal_width()
        print(section_header(f"SYNTACTIC PARTICIPANT FRAMES: {study.ref}", width=w))
        for v in study.verses:
            print(style(f"\n--- {v.osis} ---", BOLD, YELLOW))
            if v.original_text:
                print(style("Original Text: ", GREEN, BOLD) + v.original_text)
            for cl in v.semantic_frames:
                c_num = cl.get("clause_num", 1)
                rule = cl.get("rule", "")
                print(style(f"  Clause {c_num} [{rule}]:", CYAN, BOLD))
                for role_group, items in [
                    ("Agent / Subject", cl.get("agents", [])),
                    ("Action / Predicate", cl.get("actions", [])),
                    ("Patient / Object", cl.get("patients", [])),
                    ("Context / PP / Adv", cl.get("context", [])),
                ]:
                    if items:
                        item_texts = ", ".join(f"{it['text']} ({it.get('role_label', '')})" for it in items)
                        print(f"    * {style(role_group, BOLD)}: {item_texts}")
        print()

    def cmd_word(self, strongs_query: str) -> None:
        """Display deep lexical study for a Strong's number."""
        res = self.service.lookup_word(strongs_query)
        if not res:
            print(style(f"No Strong's entry found for '{strongs_query}'. Use 'H...' or 'G...'.", YELLOW))
            return

        w = terminal_width()
        print(banner(f"Word Study: {res.strongs_id} ({res.language})", res.word, width=w))
        print(style("Transliteration: ", BOLD) + res.translit)
        if res.gloss:
            print(style("TBES Gloss:      ", BOLD) + res.gloss)
        print(style("KJV Occurrences: ", BOLD) + f"{res.occurrences_count} times in Old/New Testament")

        if res.lxx_equivalences:
            print("\n" + style("Septuagint (LXX) Greek Translation Equivalences:", BOLD, CYAN))
            for eq in res.lxx_equivalences[:5]:
                forms = ", ".join(eq.get("greek_forms", []))
                print(f"  * {style(eq['greek_strongs'], BOLD, MAGENTA)}: {forms} ({eq['count']} occurrences in LXX)")

        print("\n" + style("Strong's Lexicon Definition:", BOLD, BLUE))
        for line in res.definition.splitlines():
            print(f"  {line}")

        if res.sample_verses:
            print("\n" + style("Sample Biblical Occurrences:", BOLD, YELLOW))
            for sv in res.sample_verses:
                print(f"  * {style(sv['osis'], BOLD)}: {sv.get('clean_text', '')}")
        print()

    def cmd_egw(self, query_or_token: str) -> None:
        """Look up EGW citation or search writings."""
        w = terminal_width()
        if not self.service.egw_db:
            print(style("EGW database not found at data/egw.db.", YELLOW))
            return

        clean = query_or_token.strip()
        if is_egw_token(clean):
            para = self.service.egw_db.get_paragraph(clean)
            if not para:
                print(style(f"Citation '{clean}' not found in data/egw.db.", YELLOW))
                return
            token_display = para.get("ref_code") or para.get("id") or clean
            book_name = para.get("book_title") or para.get("book_code", "")
            heading = para.get("chapter_title") or para.get("heading", "")
            print(banner(f"Spirit of Prophecy: {token_display}", book_name, width=w))
            if heading:
                print(style(f"Chapter/Heading: {heading}\n", BOLD))
            for line in wrap_text(para.get("text", ""), width=w):
                print(line)
            print()
            return

        # Keyword search
        hits = self.service.egw_db.search(clean, limit=5)
        print(banner(f"EGW Search: '{clean}'", f"{len(hits)} results", width=w))
        for h in hits:
            tok_id = h.get("ref_code") or h.get("id") or h.get("canonical_token", "")
            tok = style(f"[{tok_id}]", BOLD, CYAN)
            book = style(h.get("book_title") or h.get("book_name", ""), BOLD)
            print(f"  {tok} {book}")
            ch_title = h.get("chapter_title") or h.get("heading", "")
            if ch_title:
                print(style(f"  Chapter: {ch_title}", DIM))
            snip = h.get("snippet", "").replace("[b]", style("", BOLD, YELLOW)).replace("[/b]", style("", RESET))
            for line in wrap_text(snip, width=w, indent="    "):
                print(line)
            print()

    def cmd_search(
        self,
        query: str,
        results: UnifiedSearchResult | None = None,
        limit_bible: int = 5,
        limit_egw: int = 3,
        book_filter: str | None = None,
    ) -> None:
        """Search both Scripture and EGW writings."""
        res = results or self.service.search_unified(
            query, limit_bible=limit_bible, limit_egw=limit_egw, book_filter=book_filter
        )
        w = terminal_width()
        print(banner(f"Unified Search: '{query}'", f"{len(res.bible_hits)} Bible, {len(res.egw_hits)} EGW", width=w))

        print(section_header(f"SCRIPTURE MATCHES ({len(res.bible_hits)})", width=w))
        if res.bible_hits:
            for b in res.bible_hits:
                osis_ref = f"{b.get('osis')}.{b.get('chapter')}.{b.get('verse')}"
                ref_styled = style(f"  {osis_ref:<14}", BOLD, YELLOW)
                txt = b.get("clean_text") or b.get("text", "")
                print(f"{ref_styled} {txt}")
        else:
            print(style("  No biblical verses matched query.", DIM))
        print()

        print(section_header(f"SPIRIT OF PROPHECY MATCHES ({len(res.egw_hits)})", width=w))
        if res.egw_hits:
            for e in res.egw_hits:
                tok_styled = style(f"  {e['token']:<14}", BOLD, CYAN)
                snip = e.get("snippet", "").replace("[b]", style("", BOLD, YELLOW)).replace("[/b]", style("", RESET))
                print(f"{tok_styled} {snip}")
        else:
            print(style("  No commentary paragraphs matched query.", DIM))
        print()

    def cmd_next(self) -> None:
        if not self.current_passage:
            self.cmd_read("Gen 1")
            return
        nxt = self.service.next_passage(self.current_passage)
        if nxt:
            self.cmd_read(nxt)
        else:
            print(style("Reached the end of Revelation!", YELLOW))

    def cmd_prev(self) -> None:
        if not self.current_passage:
            self.cmd_read("Gen 1")
            return
        prv = self.service.prev_passage(self.current_passage)
        if prv:
            self.cmd_read(prv)
        else:
            print(style("Reached the beginning of Genesis!", YELLOW))

    def cmd_help(self) -> None:
        """Display help overview."""
        w = terminal_width()
        lines = [
            style("Commands:", BOLD, CYAN),
            "  read <ref>         Read passage (e.g. 'read John 1', 'read Ps 23', 'read Rom 8:28')",
            "  study <ref>        Deep multi-pane study (Scripture + Macula Frames + Lexicon + EGW)",
            "  frame <ref>        Inspect Macula clause participant frames (Agent, Action, Patient)",
            "  word <strongs>     Deep lexical word study (e.g. 'word H1254', 'word G2316')",
            "  search <query>     Unified full-text search across Scripture and EGW writings",
            "  egw <query/token>  Look up EGW citation ('egw PP.57.1') or search topics ('egw Sabbath')",
            "  next / n           Advance to the next chapter",
            "  prev / p           Return to the previous chapter",
            "  tui                Launch the full-screen interactive Terminal User Interface",
            "  clear              Clear the terminal screen",
            "  quit / exit / q    Exit the study shell",
            "",
            style("Tip:", BOLD, YELLOW) + " You can also enter biblical references directly without 'read' (e.g. 'John 3:16').",
        ]
        print("\n" + box_panel("Adventist Bible Study Shell — Help", lines, width=w) + "\n")
