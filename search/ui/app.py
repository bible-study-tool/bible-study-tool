"""Modern interactive Terminal Study Workstation built with Textual.

Provides fluid, asynchronous Scripture reading, original language syntax inspection,
Strong's lexical concordance, Spirit of Prophecy commentary, and multi-theme support.
"""

from __future__ import annotations

from typing import Any, List, Optional

from rich.markup import escape
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
)

from search.corpus.discourse_flow import (
    DISCOURSE_CATEGORY_COLORS,
    DiscourseCategory,
    format_discourse_badge,
)
from search.corpus.ot_citations import (
    format_citation_badge,
    render_citation_card,
)
from search.ui.study_service import PassageStudy, StudyService, VerseStudy
from search.ui.themes import (
    DEFAULT_THEME,
    THEMES,
    build_app_tcss,
    get_next_theme,
)


class VerseClicked(Message):
    """Event emitted when a verse is clicked in the reader."""

    def __init__(self, verse_index: int) -> None:
        super().__init__()
        self.verse_index = verse_index


class VerseWidget(Static):
    """Interactive verse row in the Scripture Reader."""

    def __init__(
        self,
        verse: VerseStudy,
        index: int,
        show_strongs: bool = False,
        show_parallel: bool = False,
    ) -> None:
        super().__init__(classes="verse-item")
        self.verse = verse
        self.index = index
        self.show_strongs = show_strongs
        self.show_parallel = show_parallel

    def on_click(self) -> None:
        self.post_message(VerseClicked(self.index))

    def render_content(self, is_selected: bool, is_pinned: bool) -> str:
        self.remove_class("verse-selected")
        self.remove_class("verse-pinned")
        if is_selected:
            self.add_class("verse-selected")
        elif is_pinned:
            self.add_class("verse-pinned")

        pin_indicator = "📌 " if is_pinned else ""
        num_str = f"[bold cyan]{pin_indicator}{self.verse.verse}[/bold cyan] "

        # Discourse logic cue badge (e.g. ⟨Premise: γάρ⟩, ⟨Therefore: οὖν⟩)
        badge = format_discourse_badge(self.verse.discourse_markers)
        badge_str = f"{badge} " if badge else ""

        # OT citation cue badge (e.g. ⟨OT Anchor: Hab 2:4⟩ or ⟨Cited in NT: Rom 1:17⟩)
        citation_badge = ""
        if self.verse.ot_citations:
            badges = [format_citation_badge(c, self.verse.osis) for c in self.verse.ot_citations]
            citation_badge = f"{' '.join(badges)} "

        if self.show_strongs and self.verse.tokens:
            token_parts = []
            for tok in self.verse.tokens:
                t_word = escape(tok.get("text", ""))
                s_codes = tok.get("strongs", [])
                if s_codes:
                    token_parts.append(f"{t_word}[green]\\[{','.join(s_codes)}][/green]")
                else:
                    token_parts.append(t_word)
            text = " ".join(token_parts)
        else:
            text = escape(self.verse.text)

        lines = [f"{num_str}{badge_str}{citation_badge}{text}"]

        if self.show_parallel and self.verse.translations:
            # Render BSB, ASV, and YLT stacked under the primary KJV verse
            for t_id, label, color in [("bsb", "BSB", "green"), ("asv", "ASV", "magenta"), ("ylt", "YLT", "blue")]:
                t_val = self.verse.translations.get(t_id)
                if t_val:
                    lines.append(f"   [bold {color}]{label}:[/bold {color}] [dim]{escape(t_val)}[/dim]")

        return "\n".join(lines)


class GotoModal(ModalScreen[Optional[str]]):
    """Modal dialog for jumping to a specific passage or Spirit of Prophecy citation."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def action_cancel(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("GOTO PASSAGE OR SPIRIT OF PROPHECY", classes="modal-title")
            yield Label("Enter Scripture (e.g. 'John 3:16', 'Rom 8') or EGW citation (e.g. 'PP 44.1', '[PP.44.1]', 'DA 25.3'):")
            yield Input(id="goto-input", placeholder="e.g. 'John 3:16', 'PP 44.1', or '[PP.44.1]'")
            with Horizontal():
                yield Button("Go", variant="primary", id="btn-go")
                yield Button("Cancel", variant="default", id="btn-cancel")

    @on(Input.Submitted, "#goto-input")
    def on_submit(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        self.dismiss(val if val else None)

    @on(Button.Pressed, "#btn-go")
    def on_go(self) -> None:
        inp = self.query_one("#goto-input", Input)
        val = inp.value.strip()
        self.dismiss(val if val else None)

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)


class SearchModal(ModalScreen[Optional[str]]):
    """Modal dialog for searching Bible and Spirit of Prophecy."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def action_cancel(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("SEARCH SCRIPTURE & SPIRIT OF PROPHECY", classes="modal-title")
            yield Label("Enter search keywords or phrase:")
            yield Input(id="search-input", placeholder="e.g. 'covenant', 'sanctuary', 'sabbath'")
            with Horizontal():
                yield Button("Search", variant="primary", id="btn-search")
                yield Button("Cancel", variant="default", id="btn-cancel")

    @on(Input.Submitted, "#search-input")
    def on_submit(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        self.dismiss(val if val else None)

    @on(Button.Pressed, "#btn-search")
    def on_search(self) -> None:
        inp = self.query_one("#search-input", Input)
        val = inp.value.strip()
        self.dismiss(val if val else None)

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)


class HelpModal(ModalScreen[None]):
    """Modal dialog displaying keyboard shortcuts and study workflow."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Dismiss"),
        Binding("q", "dismiss_modal", "Dismiss"),
    ]

    def action_dismiss_modal(self) -> None:
        self.dismiss()

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Label("BIBLE STUDY WORKSTATION — KEYBOARD SHORTCUTS", classes="modal-title")
            help_md = """
| Key | Action |
| :--- | :--- |
| **`j` / `Down`** | Move to next verse |
| **`k` / `Up`** | Move to previous verse |
| **`h` / `l`** | Previous / Next chapter (also `Left` / `Right`, `p` / `n`) |
| **`Space` / `Enter`** | Pin / unpin selected verse for side panel study |
| **`g` / `Ctrl+P`** | Jump to passage (e.g. *John 3:16*) or EGW citation (e.g. *PP 44.1*, *[PP.44.1]*) |
| **`/`** | Search Bible & Spirit of Prophecy writings |
| **`s`** | Toggle inline Strong's concordance numbers |
| **`v`** | Toggle stacked parallel translations (BSB, ASV, YLT) in Reader |
| **`o`** | Jump to Scripture Citation Anchor (OT source or NT quote; finds citations in chapter) |
| **`c`** | Toggle EGW Commentary (Chapter correlations <-> Full page reader) |
| **`t`** | Cycle color themes (Transparent, Dracula, Catppuccin, etc.) |
| **`f`** | Toggle Focus Mode (full-width Scripture reader) |
| **`1 - 5`** | Jump directly to Inspector tabs (Syntax, Lexicon, EGW, Parallel, Search) |
| **`6` / `x`** | Jump to Cross-References (Layer A Curated + Layer B TSK) |
| **`Tab`** | Toggle focus between Reader and Inspector panes |
| **`?`** | Open this help screen |
| **`q`** | Quit application |
            """
            yield Markdown(help_md)
            yield Button("Close", variant="primary", id="btn-close-help")

    @on(Button.Pressed, "#btn-close-help")
    def on_close(self) -> None:
        self.dismiss(None)


class BibleStudyApp(App):
    """Textual interactive Bible Study Workstation."""

    TITLE = "Adventist Bible Study Workstation"
    SUB_TITLE = "Offline-First Deterministic Knowledge Base"
    CSS = build_app_tcss()

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("j", "next_verse", "Down", show=False),
        Binding("k", "prev_verse", "Up", show=False),
        Binding("down", "next_verse", "Down", show=False),
        Binding("up", "prev_verse", "Up", show=False),
        Binding("h", "prev_chapter", "Prev Ch", show=True),
        Binding("l", "next_chapter", "Next Ch", show=True),
        Binding("left", "prev_chapter", "Prev Ch", show=False),
        Binding("right", "next_chapter", "Next Ch", show=False),
        Binding("p", "prev_chapter", "Prev Ch", show=False),
        Binding("n", "next_chapter", "Next Ch", show=False),
        Binding("space", "toggle_pin", "Pin Verse", show=True),
        Binding("enter", "toggle_pin", "Pin", show=False),
        Binding("g", "goto_passage", "Goto", show=True),
        Binding("ctrl+p", "goto_passage", "Goto", show=False),
        Binding("slash", "search_dialog", "Find", show=True),
        Binding("s", "toggle_strongs", "Strong's", show=True),
        Binding("v", "toggle_parallel", "Parallel", show=True),
        Binding("o", "jump_citation", "Anchor", show=True),
        Binding("c", "toggle_commentary_view", "Commentary", show=True),
        Binding("t", "cycle_theme", "Theme", show=True),
        Binding("f", "toggle_focus", "Focus", show=True),
        Binding("1", "tab_syntax", "1:Syntax", show=False),
        Binding("2", "tab_lexicon", "2:Lexicon", show=False),
        Binding("3", "tab_commentary", "3:EGW", show=False),
        Binding("4", "tab_parallel", "4:Parallel", show=False),
        Binding("5", "tab_search", "5:Search", show=False),
        Binding("6", "tab_xrefs", "6:XRefs", show=False),
        Binding("x", "tab_xrefs", "XRefs", show=True),
        Binding("question_mark", "show_help", "Help", show=True),
    ]

    def __init__(
        self,
        service: StudyService | None = None,
        initial_ref: str = "Gen 1:1",
        initial_theme: str = DEFAULT_THEME,
    ) -> None:
        super().__init__()
        self.service = service or StudyService()
        self.current_ref = initial_ref
        self.active_theme_id = initial_theme if initial_theme in THEMES else DEFAULT_THEME
        self.current_passage: Optional[PassageStudy] = None
        self.selected_verse_idx: int = 0
        self.pinned_verse_idx: Optional[int] = None
        self.show_strongs: bool = False
        self.show_parallel: bool = False
        self.focus_mode: bool = False
        self.verse_widgets: List[VerseWidget] = []
        self._dirty_tabs: set[str] = {"tab-syntax", "tab-lexicon", "tab-commentary", "tab-parallel", "tab-xrefs"}
        self._active_egw_citation: Optional[dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            with VerticalScroll(id="reader-pane"):
                yield Label("Loading scripture...", id="reader-loading")
            with Container(id="inspector-pane"):
                with TabbedContent(initial="tab-syntax", id="inspector-tabs"):
                    with TabPane("1: Syntax & Frames", id="tab-syntax"):
                        with VerticalScroll(id="syntax-content"):
                            yield Static(id="syntax-body")
                    with TabPane("2: Lexicon", id="tab-lexicon"):
                        with VerticalScroll(id="lexicon-content"):
                            yield Static(id="lexicon-body")
                    with TabPane("3: Commentary", id="tab-commentary"):
                        with VerticalScroll(id="commentary-content"):
                            yield Static(id="commentary-body")
                    with TabPane("4: Parallel", id="tab-parallel"):
                        with VerticalScroll(id="parallel-content"):
                            yield Static(id="parallel-body")
                    with TabPane("5: Search Findings", id="tab-search"):
                        with VerticalScroll(id="search-content"):
                            yield Static(id="search-body")
                    with TabPane("6: Cross-Refs", id="tab-xrefs"):
                        with VerticalScroll(id="xrefs-content"):
                            yield Static(id="xrefs-body")
        yield Footer()

    def on_mount(self) -> None:
        # Apply theme class
        self.screen.add_class(f"theme-{self.active_theme_id}")
        self.sub_title = f"{THEMES[self.active_theme_id].name} | [?] Help"
        self.load_passage_async(self.current_ref)

    @work(exclusive=True, thread=True)
    def load_passage_async(self, passage_ref: str) -> None:
        """Asynchronously fetch passage study, pre-warm caches, and populate UI."""
        from textual.worker import get_current_worker
        worker = get_current_worker()
        try:
            # Eager batch fetch ensures syntax frames are loaded in ~50ms
            study = self.service.get_passage_study(passage_ref, eager_frames=True)
            if worker.is_cancelled:
                return

            try:
                unique_strongs = {sc for v in study.verses for sc in v.strongs_list}
                for sc in unique_strongs:
                    if worker.is_cancelled:
                        return
                    self.service.lookup_word(sc, sample_limit=0)
            except Exception:
                pass  # Non-fatal cache pre-warm failure

            if not worker.is_cancelled:
                self.call_from_thread(self._apply_loaded_passage, study)
        except Exception as e:
            if not worker.is_cancelled:
                self.call_from_thread(self.notify, f"Error loading passage '{passage_ref}': {e}", severity="error", markup=False)

    def _apply_loaded_passage(self, study: PassageStudy) -> None:
        self.current_passage = study
        self._active_egw_citation = None

        # Position selection at target verse (e.g. Rom 1:17 or Hab 2:4)
        target_idx = (
            next((i for i, v in enumerate(study.verses) if v.verse == study.start_verse), 0)
            if study.start_verse
            else 0
        )
        self.selected_verse_idx = target_idx
        self.pinned_verse_idx = None
        self.current_ref = study.ref

        # Update app title
        focus_str = " [FOCUS MODE]" if self.focus_mode else ""
        self.title = f"Adventist Bible Study — {study.ref.upper()} (KJV){focus_str}"

        # Populate Reader Pane in single batch mount
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        reader_pane.remove_children()
        self.verse_widgets = []

        header_label = Static(f"[bold green]── {study.book_name.upper()} CHAPTER {study.start_chapter} ──[/bold green]\n")
        widgets_to_mount: list[Widget] = [header_label]

        for idx, v in enumerate(study.verses):
            w = VerseWidget(v, idx, show_strongs=self.show_strongs, show_parallel=self.show_parallel)
            self.verse_widgets.append(w)
            widgets_to_mount.append(w)

        reader_pane.mount_all(widgets_to_mount)

        self._update_selection_visuals()
        self._scroll_to_selected()
        self._dirty_tabs = {"tab-syntax", "tab-lexicon", "tab-commentary", "tab-parallel", "tab-xrefs"}
        self._render_active_tab()

    def _update_selection_visuals(self, previous_idx: Optional[int] = None) -> None:
        """Refresh highlight classes only for changed verse widgets (or all if previous_idx is None)."""
        if previous_idx is not None:
            indices = {self.selected_verse_idx, self.pinned_verse_idx, previous_idx}
            targets = [i for i in indices if i is not None and 0 <= i < len(self.verse_widgets)]
        else:
            targets = list(range(len(self.verse_widgets)))

        for idx in targets:
            w = self.verse_widgets[idx]
            is_sel = idx == self.selected_verse_idx
            is_pin = idx == self.pinned_verse_idx
            rendered = w.render_content(is_selected=is_sel, is_pinned=is_pin)
            w.update(rendered)

    @on(VerseClicked)
    def handle_verse_clicked(self, event: VerseClicked) -> None:
        prev = self.selected_verse_idx
        self.selected_verse_idx = event.verse_index
        self._update_selection_visuals(previous_idx=prev)
        self._update_inspector()

    def _get_inspected_verse(self) -> Optional[VerseStudy]:
        if not self.current_passage or not self.current_passage.verses:
            return None
        idx = self.pinned_verse_idx if self.pinned_verse_idx is not None else self.selected_verse_idx
        if 0 <= idx < len(self.current_passage.verses):
            return self.current_passage.verses[idx]
        return None

    @on(TabbedContent.TabActivated)
    def handle_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """When switching tabs, render if the activated tab is marked dirty."""
        self._render_active_tab()

    def _render_active_tab(self, force: bool = False) -> None:
        """Render the currently active inspector tab if marked dirty (or force=True)."""
        try:
            tabs = self.query_one("#inspector-tabs", TabbedContent)
            active_tab = tabs.active
        except Exception:
            return

        if not force and active_tab not in self._dirty_tabs:
            return

        if active_tab == "tab-syntax":
            self._update_syntax_viewport()
            self._dirty_tabs.discard("tab-syntax")
        elif active_tab == "tab-lexicon":
            self._update_lexicon_viewport()
            self._dirty_tabs.discard("tab-lexicon")
        elif active_tab == "tab-commentary":
            self._update_commentary_viewport()
            self._dirty_tabs.discard("tab-commentary")
        elif active_tab == "tab-parallel":
            self._update_parallel_viewport()
            self._dirty_tabs.discard("tab-parallel")
        elif active_tab == "tab-xrefs":
            self._update_xrefs_viewport()
            self._dirty_tabs.discard("tab-xrefs")

    def _update_commentary(self) -> None:
        """Backward-compatible commentary update: marks commentary dirty and renders if active."""
        self._dirty_tabs.add("tab-commentary")
        self._render_active_tab()

    def _update_commentary_viewport(self) -> None:
        """Update Commentary Tab (chapter-level correlations or active EGW page reader)."""
        commentary_body = self.query_one("#commentary-body", Static)

        if self._active_egw_citation:
            p = self._active_egw_citation
            cid = p.get("id") or p.get("token", "")
            btitle = p.get("book_title") or p.get("book_code", "")
            chtitle = p.get("chapter_title", "")
            page = p.get("page", 0)
            ref_code = p.get("ref_code") or f"{btitle} {page}"

            lines: list[str] = []
            lines.append(f"[bold cyan]SPIRIT OF PROPHECY READER: {escape(ref_code)}[/bold cyan] [dim](Press \\[c\\] for chapter correlations)[/dim]\n")
            lines.append(f"[bold]{escape(btitle)}[/bold]\n[bold green]{escape(chtitle)}[/bold green]\n[dim]Page {page}[/dim]\n[dim]────────────────────────────────────────[/dim]\n")

            page_paras = p.get("page_paragraphs")
            if page_paras:
                for item in page_paras:
                    item_id = item.get("id", "")
                    is_target = item_id == cid
                    item_para = item.get("paragraph", 1)
                    item_text = escape(item.get("text", ""))
                    prefix = f"[bold yellow]\\[{escape(item_id)}\\] (Paragraph {item_para})[/bold yellow]\n"
                    if is_target:
                        lines.append(f"{prefix}[bold white]{item_text}[/bold white]\n\n[dim]────────────────────────────────────────[/dim]\n")
                    else:
                        lines.append(f"{prefix}{item_text}\n\n[dim]────────────────────────────────────────[/dim]\n")
            else:
                p_text = escape(p.get("text", ""))
                lines.append(f"[bold yellow]\\[{escape(cid)}\\][/bold yellow]\n{p_text}\n\n[dim]────────────────────────────────────────[/dim]\n")

            commentary_body.update("\n".join(lines))
            self.query_one("#commentary-content", VerticalScroll).scroll_home(animate=False)
            return

        lines: list[str] = []
        lines.append("[bold cyan]SPIRIT OF PROPHECY CORRELATIONS[/bold cyan]\n")
        lines.append("[dim]Press \\[c\\] to read full page context, or \\[g\\] to jump to any citation (e.g. PP 44.1, \\[PP.44.1\\])[/dim]\n")

        if self.current_passage and self.current_passage.egw_correlations:
            for egw in self.current_passage.egw_correlations:
                book_title = egw.get("book_title") or egw.get("book_code") or "Spirit of Prophecy"
                ch_title = egw.get("chapter_title") or egw.get("heading") or ""
                token = egw.get("token", "")
                page = egw.get("page")
                para = egw.get("paragraph")
                full_text = egw.get("text") or egw.get("snippet", "")

                loc_str = f"Page {page}, par. {para}" if page else ""
                hdr_sub = f" — {escape(ch_title)}" if ch_title else ""
                teaser = egw.get("teaser")
                if not teaser:
                    raw = (egw.get("text") or egw.get("snippet", "")).strip()
                    s = " ".join(raw.split())
                    teaser = s[:140] + ("…" if len(s) > 140 else "")
                lines.append(f"[bold yellow]\\[{escape(token)}\\] {escape(book_title)}{hdr_sub}[/bold yellow]")
                if loc_str:
                    lines.append(f"[dim]{escape(loc_str)}[/dim]")
                lines.append(f"  [italic]{escape(teaser)}[/italic]")
                lines.append(f"  [dim cyan]→ Press \\[c\\] to read full context, or \\[g\\] to jump directly[/dim cyan]\n[dim]────────────────────────────────────────[/dim]\n")
        else:
            lines.append(
                "[dim]No direct Spirit of Prophecy correlations for this chapter. Press \\[/\\] to search all writings or \\[g\\] to jump directly to a citation (e.g. PP 44.1).[/dim]"
            )

        commentary_body.update("\n".join(lines))
        self.query_one("#commentary-content", VerticalScroll).scroll_home(animate=False)

    def _render_parallel_content(self, v: VerseStudy) -> str:
        """Format parallel translations comparison for the active verse."""
        lines: list[str] = []
        pin_tag = " [PINNED]" if self.pinned_verse_idx is not None else ""
        lines.append(f"[bold cyan]PARALLEL TRANSLATIONS — {v.osis}{pin_tag}[/bold cyan]\n")

        # 1. Primary Reference: KJV
        kjv_text = v.translations.get("kjv") or v.text
        lines.append("[bold yellow]King James Version (KJV 1769)[/bold yellow]")
        lines.append(f"  {escape(kjv_text)}\n")

        # 2. Modern English: BSB
        bsb_text = v.translations.get("bsb")
        if bsb_text:
            lines.append("[bold green]Berean Standard Bible (BSB 2020) — Accessible Modern English[/bold green]")
            lines.append(f"  {escape(bsb_text)}\n")

        # 3. Classic Literal: ASV
        asv_text = v.translations.get("asv")
        if asv_text:
            lines.append("[bold magenta]American Standard Version (ASV 1901) — Formal Equivalence[/bold magenta]")
            lines.append(f"  {escape(asv_text)}\n")

        # 4. Ultra-Literal Verbal Aspect: YLT
        ylt_text = v.translations.get("ylt")
        if ylt_text:
            lines.append("[bold blue]Young's Literal Translation (YLT 1898) — Strict Verbal Aspect[/bold blue]")
            lines.append(f"  {escape(ylt_text)}\n")

        # 5. Any additional ingested translations
        known_keys = {"kjv", "bsb", "asv", "ylt"}
        for tid, ttext in sorted(v.translations.items()):
            if tid not in known_keys and ttext:
                lines.append(f"[bold white]{escape(tid.upper())}[/bold white]")
                lines.append(f"  {escape(ttext)}\n")

        lines.append("[dim]────────────────────────────────────────[/dim]")
        lines.append("[dim]Press \\[v\\] in the Reader pane to toggle stacked parallel translations under each verse.[/dim]")

        return "\n".join(lines)

    def _update_parallel_viewport(self) -> None:
        """Update Parallel Translations Tab."""
        v = self._get_inspected_verse()
        parallel_body = self.query_one("#parallel-body", Static)
        if not v:
            parallel_body.update("[dim]No verse selected.[/dim]")
            return

        rendered = self._render_parallel_content(v)
        parallel_body.update(rendered)
        self.query_one("#parallel-content", VerticalScroll).scroll_home(animate=False)

    def _render_xrefs_content(self, v: VerseStudy) -> str:
        """Format cross-references for active verse (Layer A curated + Layer B TSK)."""
        lines: list[str] = []
        pin_tag = " [PINNED]" if self.pinned_verse_idx is not None else ""
        lines.append(f"[bold cyan]CROSS-REFERENCES — {v.osis}{pin_tag}[/bold cyan]\n")

        has_content = False

        # 1. Layer A: Curated Thematic & Theological Connections
        if v.curated_xrefs:
            has_content = True
            lines.append(f"[bold yellow]THEMATIC & THEOLOGICAL CONNECTIONS (Layer A — {len(v.curated_xrefs)} entries):[/bold yellow]")
            for cx in v.curated_xrefs:
                type_lbl = cx.get("type_label") or "Cross Reference"
                disp = cx.get("display_target") or cx.get("target") or ""
                lines.append(f"  [bold green]• {escape(type_lbl)}:[/bold green] [bold white]{escape(disp)}[/bold white]")
                note = cx.get("note")
                if note:
                    lines.append(f"    [dim]{escape(note)}[/dim]")
            lines.append("")

        # 2. Layer B: Treasury of Scripture Knowledge (TSK)
        if v.cross_references:
            has_content = True
            lines.append(f"[bold yellow]TREASURY OF SCRIPTURE KNOWLEDGE (Layer B — {len(v.cross_references)} citations):[/bold yellow]")
            for rx in v.cross_references:
                to_ref = rx.get("to_ref", "")
                votes = rx.get("votes", 0)
                preview = rx.get("preview_text", "")
                lines.append(f"  [bold cyan]{escape(to_ref)}[/bold cyan] [dim](★ {votes})[/dim]")
                if preview:
                    lines.append(f"    [dim italic]{escape(preview)}[/dim italic]")
            lines.append("")

        if not has_content:
            lines.append("[dim]No cross references available for this verse.[/dim]\n")

        lines.append("[dim]────────────────────────────────────────[/dim]")
        lines.append("[dim]Press \\[x\\] again to jump directly to the top cross-reference.[/dim]")
        return "\n".join(lines)

    def _update_xrefs_viewport(self) -> None:
        """Update Cross-References Tab."""
        v = self._get_inspected_verse()
        xrefs_body = self.query_one("#xrefs-body", Static)
        if not v:
            xrefs_body.update("[dim]No verse selected.[/dim]")
            return

        rendered = self._render_xrefs_content(v)
        xrefs_body.update(rendered)
        self.query_one("#xrefs-content", VerticalScroll).scroll_home(animate=False)

    def _update_inspector(self, force_all: bool = False) -> None:
        """Update inspector views: marks tabs dirty and updates viewports without DOM thrashing."""
        self._dirty_tabs.update({"tab-syntax", "tab-lexicon", "tab-parallel", "tab-xrefs"})
        if force_all:
            self._update_syntax_viewport()
            self._update_lexicon_viewport()
            self._update_parallel_viewport()
            self._update_xrefs_viewport()
            self._dirty_tabs.discard("tab-syntax")
            self._dirty_tabs.discard("tab-lexicon")
            self._dirty_tabs.discard("tab-parallel")
            self._dirty_tabs.discard("tab-xrefs")
        else:
            self._render_active_tab()

    def _render_syntax_content(self, v: VerseStudy) -> str:
        lines: list[str] = []
        pin_tag = " [PINNED]" if self.pinned_verse_idx is not None else ""
        lines.append(f"[bold cyan]VERSE SYNTAX & CLAUSE FRAMES: {v.osis}{pin_tag}[/bold cyan]\n")

        if v.original_text:
            lines.append(f"[bold green]Original Text:[/bold green] {escape(v.original_text)}\n")

        # Scripture Interpreting Scripture: OT Citation Anchors
        if v.ot_citations:
            for cit in v.ot_citations:
                lines.append(render_citation_card(cit, for_verse_osis=v.osis))

        # Argument Flow & Discourse Connectors
        lines.append("[bold cyan]ARGUMENT FLOW & LOGICAL CONNECTORS:[/bold cyan]")
        if v.discourse_markers:
            for m in v.discourse_markers:
                color = DISCOURSE_CATEGORY_COLORS.get(m.category, "green")
                orig_tag = f"{m.original_word} ({m.transliteration} / {m.strongs})" if m.strongs else m.original_word
                lines.append(f"  • [bold {color}]● {m.role_label}[/bold {color}] ➔ [bold white]\"{escape(m.english_text)}\"[/bold white] [dim]({escape(orig_tag)})[/dim]")
                lines.append(f"    [bold]Function:[/] {escape(m.function_summary)}")
                lines.append(f"    [bold]Theological Insight:[/] {escape(m.theological_significance)}")
                lines.append("")
        else:
            lines.append("  [dim]No explicit logical discourse connector (continuation of established argument).[/dim]\n")

        # Passage Argument Context
        if self.current_passage and self.current_passage.argument_flow:
            step = next(
                (s for s in self.current_passage.argument_flow if s.osis == v.osis or (s.chapter == v.chapter and s.verse == v.verse)),
                None,
            )
            if step:
                lines.append(f"  [dim]Passage Context:[/] [bold]{escape(step.primary_role)}[/bold] — {escape(step.flow_description)}\n")

        if v.semantic_frames:
            for cl in v.semantic_frames:
                c_num = cl.get("clause_num", 1)
                lines.append(f"[bold cyan]Clause {c_num} [{cl.get('rule', '')}]:[/bold cyan]")
                for label, items in [
                    ("Agent", cl.get("agents", [])),
                    ("Action", cl.get("actions", [])),
                    ("Patient", cl.get("patients", [])),
                    ("Context", cl.get("context", [])),
                ]:
                    if items:
                        val_strs = []
                        for it in items:
                            orig = escape(it.get("text", ""))
                            gloss_parts = [
                                t.get("gloss")
                                for t in it.get("tokens", [])
                                if t.get("gloss") and t.get("gloss") not in ("(et)", "-", None)
                            ]
                            gloss_str = escape(" ".join(gloss_parts).replace(".", " "))
                            if gloss_str:
                                val_strs.append(f"{orig} [green]({gloss_str})[/green]")
                            else:
                                val_strs.append(orig)
                        val_joined = ", ".join(val_strs)
                        lines.append(f"  • [bold]{label}:[/bold] {val_joined}")
                lines.append("")
        else:
            lines.append("[dim]No syntactic clause tree available for this verse.[/dim]")

        # Verbal Stems & Theological Nuances
        if v.verbal_nuances:
            lines.append("\n[bold magenta]VERBAL STEMS & THEOLOGICAL NUANCES:[/bold magenta]")
            for n in v.verbal_nuances:
                lang_tag = "Hebrew" if n.language == "hebrew" else ("Greek" if n.language == "greek" else "Aramaic")
                orig_disp = f"[bold green]{escape(n.text)}[/bold green] ({escape(n.lemma)})" if n.text else escape(n.lemma)
                lines.append(f"  • {orig_disp} [dim][{lang_tag}][/dim] ➔ [bold yellow]{escape(n.plain_summary)}[/bold yellow]")
                lines.append(f"    {escape(n.theological_nuance)}")
                if n.aspect_meaning and n.aspect_meaning != n.theological_nuance:
                    lines.append(f"    [dim]Aspect: {escape(n.aspect_meaning)}[/dim]")
                lines.append("")

        return "\n".join(lines)

    def _update_syntax_viewport(self) -> None:
        """Render syntactic analysis and semantic clause frames for inspected verse."""
        v = self._get_inspected_verse()
        syntax_body = self.query_one("#syntax-body", Static)
        if not v:
            syntax_body.update("[dim]No verse selected.[/dim]")
            return

        self.service.ensure_verse_frames(v)
        rendered = self._render_syntax_content(v)
        syntax_body.update(rendered)
        self.query_one("#syntax-content", VerticalScroll).scroll_home(animate=False)

    def _render_lexicon_content(self, v: VerseStudy) -> str:
        lines: list[str] = []
        lines.append(f"[bold cyan]STRONG'S CONCORDANCE & LEXICON: {v.osis}[/bold cyan]\n")

        # Build Strong's to KJV word(s) mapping from verse tokens
        s_to_kjv: dict[str, list[str]] = {}
        for tok in v.tokens:
            t_text = tok.get("text", "").strip()
            for sc in tok.get("strongs", []):
                norm_sc = sc.upper()
                canon_sc = norm_sc[0] + norm_sc[1:].lstrip("0") if len(norm_sc) > 1 else norm_sc
                for key in (norm_sc, canon_sc):
                    if key not in s_to_kjv:
                        s_to_kjv[key] = []
                    if t_text and t_text not in s_to_kjv[key]:
                        s_to_kjv[key].append(t_text)

        seen = set()
        words_found = 0
        for s_code in v.strongs_list:
            if s_code in seen:
                continue
            seen.add(s_code)
            w_res = self.service.lookup_word(s_code, sample_limit=0)
            if w_res:
                words_found += 1
                # Find matching KJV word
                matching_words = [escape(w) for w in (s_to_kjv.get(w_res.strongs_id, []) or s_to_kjv.get(s_code.upper(), []))]
                kjv_prefix = f"[bold yellow]\"{', '.join(matching_words)}\"[/bold yellow] ➔ " if matching_words else ""

                lines.append(
                    f"{kjv_prefix}[bold cyan]{w_res.strongs_id}[/bold cyan] ({w_res.language}): [bold green]{escape(w_res.word)}[/bold green] [dim]({escape(w_res.translit)})[/dim]"
                )
                if w_res.gloss:
                    lines.append(f"  [bold]Translation Gloss:[/bold] [yellow]{escape(w_res.gloss)}[/yellow]")
                lines.append(f"  [dim]KJV Occurrences: {w_res.occurrences_count}[/dim]")

                # Strong's senses (multi-sense descriptions)
                if w_res.strongs_senses:
                    lines.append("  [bold]Strong's Senses:[/bold]")
                    for s in w_res.strongs_senses:
                        lines.append(f"    [bold yellow]•[/bold yellow] {escape(s)}")
                else:
                    def_lines = [l.strip() for l in w_res.definition.splitlines() if l.strip() and not l.startswith("Strong's Number")]
                    if def_lines:
                        lines.append(f"  [bold]Definition:[/bold] {escape(def_lines[0])}")

                # KJV translation renderings and etymology
                if w_res.kjv_renderings:
                    lines.append(f"  [bold]KJV Translation Renderings:[/bold] [italic green]{escape(w_res.kjv_renderings)}[/italic green]")
                if w_res.etymology:
                    lines.append(f"  [bold]Etymology / Root:[/bold] [dim]{escape(w_res.etymology)}[/dim]")

                # Verbal stem and theological nuances for verbs
                v_nuances = self.service.get_verse_nuance_for_strongs(v, w_res.strongs_id) or self.service.get_verse_nuance_for_strongs(v, s_code)
                if v_nuances:
                    for vn in v_nuances:
                        lines.append(f"  [bold magenta]Verbal Stem / Form:[/bold magenta] [bold yellow]{escape(vn.plain_summary)}[/bold yellow]")
                        lines.append(f"  [bold magenta]Theological Nuance:[/bold magenta] {escape(vn.theological_nuance)}")

                # Septuagint translation equivalences with Greek glosses
                if w_res.lxx_equivalences:
                    lxx_top = w_res.lxx_equivalences[:3]
                    lxx_parts = []
                    for eq in lxx_top:
                        g_sc = eq.get("greek_strongs", "")
                        g_forms = escape(",".join(eq.get("greek_forms", [])))
                        g_count = eq.get("count", 0)
                        g_gloss = self.service.get_greek_gloss(g_sc) if g_sc else ""
                        if g_gloss:
                            lxx_parts.append(f"{g_sc} ({g_forms} — \"{escape(g_gloss)}\"): {g_count}x")
                        else:
                            lxx_parts.append(f"{g_sc} ({g_forms}): {g_count}x")
                    lines.append(f"  [dim]LXX Equivalences: {' | '.join(lxx_parts)}[/dim]")

                # Unabridged Scholarly Lexicon (Brown-Driver-Briggs / Abbott-Smith)
                if w_res.scholarly_definition:
                    lines.append(f"\n  [bold green]═══ SCHOLARLY UNABRIDGED LEXICON ({escape(w_res.source_lexicon)}) ═══[/bold green]")
                    for s_line in w_res.scholarly_definition.splitlines():
                        lines.append(f"  {s_line}")
                lines.append("")

        if words_found == 0:
            lines.append("[dim]No Strong's concordance tags found for this verse.[/dim]")

        return "\n".join(lines)

    def _update_lexicon_viewport(self) -> None:
        """Render Strong's concordance, word definitions, and LXX translation equivalences."""
        v = self._get_inspected_verse()
        lexicon_body = self.query_one("#lexicon-body", Static)
        if not v:
            lexicon_body.update("[dim]No verse selected.[/dim]")
            return

        self.service.ensure_verse_frames(v)
        rendered = self._render_lexicon_content(v)
        try:
            lexicon_body.update(rendered)
        except Exception:
            lexicon_body.update(escape(rendered))
        self.query_one("#lexicon-content", VerticalScroll).scroll_home(animate=False)

    def action_next_verse(self) -> None:
        if self.current_passage and self.selected_verse_idx + 1 < len(self.current_passage.verses):
            prev = self.selected_verse_idx
            self.selected_verse_idx += 1
            self._update_selection_visuals(previous_idx=prev)
            self._update_inspector()
            self._scroll_to_selected()

    def action_prev_verse(self) -> None:
        if self.selected_verse_idx > 0:
            prev = self.selected_verse_idx
            self.selected_verse_idx -= 1
            self._update_selection_visuals(previous_idx=prev)
            self._update_inspector()
            self._scroll_to_selected()

    def _scroll_to_selected(self) -> None:
        if 0 <= self.selected_verse_idx < len(self.verse_widgets):
            w = self.verse_widgets[self.selected_verse_idx]
            w.scroll_visible()

    def action_toggle_pin(self) -> None:
        prev = self.pinned_verse_idx
        if self.pinned_verse_idx is not None:
            self.pinned_verse_idx = None
            self.notify("Verse unpinned: Inspector now follows cursor", timeout=2)
        else:
            self.pinned_verse_idx = self.selected_verse_idx
            v = self._get_inspected_verse()
            v_ref = v.osis if v else ""
            self.notify(f"Verse {v_ref} pinned for inspection", timeout=2)
        self._update_selection_visuals(previous_idx=prev)
        self._update_inspector()


    def action_next_chapter(self) -> None:
        if not self.current_passage:
            return
        nxt = self.service.next_passage(self.current_passage)
        if nxt:
            self.load_passage_async(nxt)
        else:
            self.notify("Reached the end of Revelation!", severity="warning")

    def action_prev_chapter(self) -> None:
        if not self.current_passage:
            return
        prv = self.service.prev_passage(self.current_passage)
        if prv:
            self.load_passage_async(prv)
        else:
            self.notify("Reached the beginning of Genesis!", severity="warning")

    def action_goto_passage(self) -> None:
        def on_goto_done(ref: Optional[str]) -> None:
            if ref:
                clean_ref = ref.strip().strip("[]").strip()
                # Check if reference is a valid Bible passage within canon bounds
                try:
                    from search.corpus.bible_books import parse_passage_ref, BIBLE_BOOKS
                    osis, ch, _, _ = parse_passage_ref(clean_ref)
                    if osis in BIBLE_BOOKS and 1 <= ch <= BIBLE_BOOKS[osis].chapters:
                        self.load_passage_async(clean_ref)
                        return
                except Exception:
                    pass

                from search.linking.egw import is_egw_token
                if is_egw_token(clean_ref):
                    self.load_egw_citation_async(clean_ref)
                else:
                    self.load_passage_async(clean_ref)

        self.push_screen(GotoModal(), on_goto_done)

    @work(exclusive=True, thread=True)
    def load_egw_citation_async(self, citation_or_token: str) -> None:
        """Asynchronously load and display a specific Spirit of Prophecy citation."""
        clean_tok = citation_or_token.strip().strip("[]").strip()
        try:
            res = self.service.lookup_egw_citation(clean_tok)
            if res:
                self.call_from_thread(self._apply_loaded_egw_citation, res)
            else:
                self.call_from_thread(
                    self.notify,
                    f"Citation '{clean_tok}' not found in Spirit of Prophecy corpus.",
                    severity="warning",
                    markup=False,
                )
        except Exception as e:
            self.call_from_thread(self.notify, f"Error loading EGW citation: {e}", severity="error", markup=False)

    def _apply_loaded_egw_citation(self, p: dict[str, Any]) -> None:
        """Render a fetched EGW citation and surrounding page context into the Commentary tab."""
        self._active_egw_citation = p
        self._update_commentary_viewport()
        self._dirty_tabs.discard("tab-commentary")

        # Switch to Commentary tab
        tabs = self.query_one("#inspector-tabs", TabbedContent)
        tabs.active = "tab-commentary"

        btitle = p.get("book_title") or p.get("book_code", "")
        page = p.get("page", 0)
        ref_code = p.get("ref_code") or f"{btitle} {page}"
        self.notify(f"Loaded: {ref_code} ({btitle})", timeout=3, markup=False)

    def action_search_dialog(self) -> None:
        def on_search_done(query: Optional[str]) -> None:
            if query:
                self.execute_search_async(query)

        self.push_screen(SearchModal(), on_search_done)

    @work(exclusive=True, thread=True)
    def execute_search_async(self, query: str) -> None:
        """Run unified search in background thread."""
        try:
            res = self.service.search_unified(query, limit_bible=10, limit_egw=5)
            self.call_from_thread(self._apply_search_results, query, res)
        except Exception as e:
            self.call_from_thread(self.notify, f"Search error: {e}", severity="error", markup=False)

    def _apply_search_results(self, query: str, res: Any) -> None:
        search_body = self.query_one("#search-body", Static)
        total_hits = len(res.bible_hits) + len(res.egw_hits)

        lines: list[str] = []
        lines.append(f"[bold cyan]SEARCH RESULTS FOR: '{escape(query)}'[/bold cyan]\n")
        lines.append(f"[bold]Found {total_hits} matches[/bold] ({len(res.bible_hits)} Scripture, {len(res.egw_hits)} Spirit of Prophecy)\n")

        if res.bible_hits:
            lines.append("[bold green]── SCRIPTURE RESULTS ──[/bold green]")
            for b in res.bible_hits:
                osis_str = f"{b.get('osis')}.{b.get('chapter')}.{b.get('verse')}"
                b_text = b.get("clean_text") or b.get("text", "")
                lines.append(f"[bold cyan]{escape(osis_str)}:[/bold cyan] {escape(b_text)}\n")

        if res.egw_hits:
            lines.append("[bold yellow]── SPIRIT OF PROPHECY RESULTS ──[/bold yellow]")
            for e in res.egw_hits:
                tok = e.get("token", "")
                raw_snippet = escape(e.get("snippet", ""))
                formatted_snippet = raw_snippet.replace("\\[b\\]", "[bold underline]").replace("\\[/b\\]", "[/bold underline]")
                lines.append(f"[bold yellow]\\[{escape(tok)}\\][/bold yellow] {formatted_snippet}\n")

        search_body.update("\n".join(lines))
        self.query_one("#search-content", VerticalScroll).scroll_home(animate=False)

        # Switch to Search tab
        tabs = self.query_one("#inspector-tabs", TabbedContent)
        tabs.active = "tab-search"
        self.notify(f"Search completed: {total_hits} results found", timeout=3)

    def action_toggle_strongs(self) -> None:
        self.show_strongs = not self.show_strongs
        for w in self.verse_widgets:
            w.show_strongs = self.show_strongs
        state_str = "ENABLED" if self.show_strongs else "DISABLED"
        self.notify(f"Strong's display: {state_str}", timeout=2)
        self._update_selection_visuals()

    def action_toggle_parallel(self) -> None:
        """Toggle stacked parallel translations display in the Reader pane."""
        self.show_parallel = not self.show_parallel
        for w in self.verse_widgets:
            w.show_parallel = self.show_parallel
        state_str = "ENABLED" if self.show_parallel else "DISABLED"
        self.notify(f"Stacked parallel translations: {state_str}", timeout=2)
        self._update_selection_visuals()

    def action_jump_citation(self) -> None:
        """Jump to the linked Old Testament source verse (or NT apostolic citation)."""
        v = self._get_inspected_verse()
        if not v:
            return

        # 1. If active verse has an anchor, jump across testaments immediately
        if v.ot_citations:
            cit = v.ot_citations[0]
            target, target_display = cit.target_for_verse(v.osis)
            self.notify(f"Navigating to Scripture anchor: {target_display}", markup=False)
            self.load_passage_async(target)
            return

        # 2. Smart Anchor Discovery: find next verse in current chapter with a citation
        if self.current_passage and self.current_passage.verses:
            num_verses = len(self.current_passage.verses)
            for offset in range(1, num_verses):
                cand_idx = (self.selected_verse_idx + offset) % num_verses
                cand_v = self.current_passage.verses[cand_idx]
                if cand_v.ot_citations:
                    prev = self.selected_verse_idx
                    self.pinned_verse_idx = None
                    self.selected_verse_idx = cand_idx
                    self._update_selection_visuals(previous_idx=prev)
                    self._update_inspector()
                    self._scroll_to_selected()
                    cand_cit = cand_v.ot_citations[0]
                    _, target_disp = cand_cit.target_for_verse(cand_v.osis)
                    self.notify(f"Moved to {cand_v.osis} with anchor: {target_disp} (press [o] to jump)", markup=False)
                    return

        ch_name = f"{self.current_passage.book_name} {self.current_passage.start_chapter}" if self.current_passage else "current chapter"
        self.notify(f"No Scripture citation anchors in {ch_name}", severity="information", markup=False)

    def action_toggle_commentary_view(self) -> None:
        """Toggle between loaded EGW continuous page reader and chapter correlation overview."""
        tabs = self.query_one("#inspector-tabs", TabbedContent)
        if tabs.active != "tab-commentary":
            self.action_tab_commentary()
            return
        if self._active_egw_citation:
            self._active_egw_citation = None
            self.notify("Showing chapter commentary correlations", timeout=2)
            self._update_commentary_viewport()
        else:
            if self.current_passage and self.current_passage.egw_correlations:
                first_tok = self.current_passage.egw_correlations[0].get("token")
                if first_tok:
                    self.load_egw_citation_async(first_tok)
            else:
                self.notify("No Spirit of Prophecy correlations for this chapter", severity="information", markup=False)

    def action_toggle_focus(self) -> None:
        self.focus_mode = not self.focus_mode
        reader = self.query_one("#reader-pane", VerticalScroll)
        inspector = self.query_one("#inspector-pane", Container)
        if self.focus_mode:
            reader.add_class("focus-mode")
            inspector.add_class("hidden-pane")
            self.notify("Focus mode: Enabled (Full-Width Reader)", timeout=2)
        else:
            reader.remove_class("focus-mode")
            inspector.remove_class("hidden-pane")
            self.notify("Focus mode: Disabled (Dual Pane)", timeout=2)

    def action_cycle_theme(self) -> None:
        old_theme = self.active_theme_id
        self.active_theme_id = get_next_theme(self.active_theme_id)
        self.screen.remove_class(f"theme-{old_theme}")
        self.screen.add_class(f"theme-{self.active_theme_id}")
        th_info = THEMES[self.active_theme_id]
        self.sub_title = f"{th_info.name} | [?] Help"
        self.notify(f"Theme switched to: {th_info.name}", timeout=2)

    def _switch_tab(self, tab_id: str) -> None:
        """Switch active inspector tab and re-render if dirty."""
        tabs = self.query_one("#inspector-tabs", TabbedContent)
        tabs.active = tab_id
        self._render_active_tab()

    def action_tab_syntax(self) -> None:
        self._switch_tab("tab-syntax")

    def action_tab_lexicon(self) -> None:
        self._switch_tab("tab-lexicon")

    def action_tab_commentary(self) -> None:
        self._switch_tab("tab-commentary")

    def action_tab_parallel(self) -> None:
        self._switch_tab("tab-parallel")

    def action_tab_search(self) -> None:
        self._switch_tab("tab-search")

    def action_tab_xrefs(self) -> None:
        tabs = self.query_one("#inspector-tabs", TabbedContent)
        if tabs.active == "tab-xrefs":
            v = self._get_inspected_verse()
            if v and v.curated_xrefs:
                top_cx = v.curated_xrefs[0]
                top_nav = top_cx.get("nav_ref") or top_cx.get("target")
                if top_nav:
                    from search.linking.egw import is_egw_token
                    if is_egw_token(top_nav):
                        self.notify(f"Opening commentary: {top_nav}", markup=False)
                        self.load_egw_citation_async(top_nav)
                        self.action_tab_commentary()
                        return
                    self.notify(f"Navigating to thematic link: {top_nav}", markup=False)
                    self.load_passage_async(top_nav)
                    return
            elif v and v.cross_references:
                top_ref = v.cross_references[0].get("to_ref")
                if top_ref:
                    self.notify(f"Navigating to cross-reference: {top_ref}", markup=False)
                    self.load_passage_async(top_ref)
                    return
        self._switch_tab("tab-xrefs")

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())


def run_textual_app(service: StudyService | None = None, initial_ref: str = "Gen 1:1", initial_theme: str = DEFAULT_THEME) -> None:
    """Launch the modern Textual Bible Study workstation."""
    app = BibleStudyApp(service=service, initial_ref=initial_ref, initial_theme=initial_theme)
    app.run()


if __name__ == "__main__":
    run_textual_app()
