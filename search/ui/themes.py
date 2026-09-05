"""Terminal color themes for the Adventist Bible Study Tool.

Includes transparent background by default (honoring user's terminal emulator theme)
alongside popular standard themes: Dracula, Catppuccin Mocha, Tokyo Night, Nord,
Gruvbox Dark, and Solarized Dark.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ThemeInfo:
    id: str
    name: str
    description: str
    background: str
    surface: str
    surface_alt: str
    primary: str
    secondary: str
    accent: str
    text: str
    text_muted: str
    border: str
    highlight: str
    is_transparent: bool = False


DEFAULT_THEME: str = "transparent"

THEMES: Dict[str, ThemeInfo] = {
    "transparent": ThemeInfo(
        id="transparent",
        name="Transparent (Terminal Default)",
        description="Preserves your terminal's background, transparency, and system colors.",
        background="transparent",
        surface="transparent",
        surface_alt="rgba(255, 255, 255, 0.05)",
        primary="#00d7ff",      # Cyan
        secondary="#ffd700",    # Gold
        accent="#50fa7b",       # Emerald Green
        text="#e6edf3",
        text_muted="#8b949e",
        border="#30363d",
        highlight="rgba(0, 215, 255, 0.20)",
        is_transparent=True,
    ),
    "dracula": ThemeInfo(
        id="dracula",
        name="Dracula",
        description="Famous dark theme with rich purples, pinks, and cyans.",
        background="#282a36",
        surface="#21222c",
        surface_alt="#343746",
        primary="#bd93f9",      # Purple
        secondary="#ff79c6",    # Pink
        accent="#8be9fd",       # Cyan
        text="#f8f8f2",
        text_muted="#6272a4",
        border="#44475a",
        highlight="rgba(189, 147, 249, 0.25)",
        is_transparent=False,
    ),
    "catppuccin_mocha": ThemeInfo(
        id="catppuccin_mocha",
        name="Catppuccin Mocha",
        description="Soothing, warm dark pastel palette.",
        background="#1e1e2e",
        surface="#181825",
        surface_alt="#313244",
        primary="#cba6f7",      # Mauve
        secondary="#f5c2e7",    # Pink
        accent="#74c7ec",       # Sapphire
        text="#cdd6f4",
        text_muted="#6c7086",
        border="#45475a",
        highlight="rgba(203, 166, 247, 0.25)",
        is_transparent=False,
    ),
    "tokyo_night": ThemeInfo(
        id="tokyo_night",
        name="Tokyo Night",
        description="Clean dark theme celebrating the lights of downtown Tokyo.",
        background="#1a1b26",
        surface="#16161e",
        surface_alt="#24283b",
        primary="#7aa2f7",      # Blue
        secondary="#bb9af7",    # Magenta
        accent="#7dcfff",       # Cyan
        text="#a9b1d6",
        text_muted="#565f89",
        border="#3b4261",
        highlight="rgba(122, 162, 247, 0.25)",
        is_transparent=False,
    ),
    "nord": ThemeInfo(
        id="nord",
        name="Nord",
        description="Arctic, north-bluish clean and elegant color palette.",
        background="#2e3440",
        surface="#242933",
        surface_alt="#3b4252",
        primary="#88c0d0",      # Frost Cyan
        secondary="#81a1c1",    # Frost Blue
        accent="#a3be8c",       # Aurora Green
        text="#d8dee9",
        text_muted="#4c566a",
        border="#434c5e",
        highlight="rgba(136, 192, 208, 0.25)",
        is_transparent=False,
    ),
    "gruvbox_dark": ThemeInfo(
        id="gruvbox_dark",
        name="Gruvbox Dark",
        description="Retro groove warm earth tones.",
        background="#282828",
        surface="#1d2021",
        surface_alt="#3c3836",
        primary="#fabd2f",      # Yellow
        secondary="#fe8019",    # Orange
        accent="#b8bb26",       # Green
        text="#ebdbb2",
        text_muted="#928374",
        border="#504945",
        highlight="rgba(250, 189, 47, 0.25)",
        is_transparent=False,
    ),
    "solarized_dark": ThemeInfo(
        id="solarized_dark",
        name="Solarized Dark",
        description="Precision-engineered palette for reduced eye strain.",
        background="#002b36",
        surface="#073642",
        surface_alt="#003847",
        primary="#268bd2",      # Blue
        secondary="#2aa198",    # Cyan
        accent="#b58900",       # Yellow
        text="#93a1a1",
        text_muted="#586e75",
        border="#073642",
        highlight="rgba(38, 139, 210, 0.25)",
        is_transparent=False,
    ),
}

ORDERED_THEME_KEYS: List[str] = list(THEMES.keys())


def get_next_theme(current_key: str) -> str:
    """Return the next theme key in the rotation."""
    if current_key not in THEMES:
        return DEFAULT_THEME
    idx = ORDERED_THEME_KEYS.index(current_key)
    next_idx = (idx + 1) % len(ORDERED_THEME_KEYS)
    return ORDERED_THEME_KEYS[next_idx]


def build_single_theme_tcss(th: ThemeInfo) -> str:
    """Generate Textual CSS rules for a single theme."""
    theme_class = f"Screen.theme-{th.id}"
    bg_val = "transparent" if th.is_transparent else th.background
    hdr_bg = "transparent" if th.is_transparent else th.surface
    ftr_bg = "transparent" if th.is_transparent else th.surface
    modal_bg = th.surface if not th.is_transparent else "#111827"

    return f"""
        /* Theme: {th.name} */
        {theme_class} {{
            background: {bg_val};
            color: {th.text};
        }}

        {theme_class} Header {{
            background: {hdr_bg};
            color: {th.primary};
        }}

        {theme_class} Footer {{
            background: {ftr_bg};
            color: {th.secondary};
        }}

        {theme_class} #reader-pane {{
            border-right: solid {th.border};
        }}

        {theme_class} .verse-num {{
            color: {th.secondary};
        }}

        {theme_class} .verse-item:hover {{
            background: {th.surface_alt};
        }}

        {theme_class} .verse-selected {{
            background: {th.highlight};
            border-left: thick {th.primary};
        }}

        {theme_class} .verse-pinned {{
            background: {th.highlight};
            border-left: thick {th.accent};
        }}

        {theme_class} .inspector-title {{
            color: {th.primary};
        }}

        {theme_class} .clause-box {{
            border-left: double {th.primary};
        }}

        {theme_class} .word-card {{
            border: round {th.border};
            background: {th.surface_alt};
        }}

        {theme_class} Tab.-active {{
            color: {th.primary};
            text-style: bold;
        }}

        {theme_class} Tab {{
            color: {th.text_muted};
        }}

        {theme_class} .modal-dialog {{
            background: {modal_bg};
            border: thick {th.primary};
        }}

        {theme_class} .modal-title {{
            color: {th.primary};
        }}
    """


def build_app_tcss() -> str:
    """Generate complete Textual CSS rules supporting all registered themes."""
    css_parts: List[str] = []

    # Base structural styling across all themes
    base_css = """
    /* App Layout */
    Screen {
        layout: vertical;
        overflow: hidden;
    }

    Header {
        dock: top;
        height: 1;
    }

    Footer {
        dock: bottom;
        height: 1;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
        width: 1fr;
    }

    #reader-pane {
        width: 55%;
        height: 1fr;
        padding: 0 1;
        overflow-y: scroll;
    }

    #reader-pane.focus-mode {
        width: 100%;
        border-right: none;
    }

    #inspector-pane {
        width: 45%;
        height: 1fr;
        padding: 0 1;
        overflow-y: hidden;
    }

    #inspector-pane.hidden-pane {
        display: none;
    }

    /* Verse items */
    .verse-item {
        margin: 0 0 1 0;
        padding: 0 1;
        border-left: blank;
    }

    .verse-num {
        text-style: bold;
    }

    /* Inspector tabs & contents */
    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 1;
        overflow-y: scroll;
    }

    .inspector-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .clause-box {
        padding-left: 1;
        margin-bottom: 1;
    }

    .word-card {
        padding: 0 1;
        margin-bottom: 1;
    }

    /* Modal Dialogs */
    .modal-dialog {
        padding: 1 2;
        width: 60;
        height: auto;
    }

    .modal-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    """
    css_parts.append(base_css)

    for th in THEMES.values():
        css_parts.append(build_single_theme_tcss(th))

    return "\n".join(css_parts)


def get_theme_css(theme_key: str) -> str:
    """Return the CSS section corresponding to a specific theme."""
    th = THEMES.get(theme_key, THEMES[DEFAULT_THEME])
    return build_single_theme_tcss(th)

