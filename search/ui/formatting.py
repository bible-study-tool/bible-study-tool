"""Terminal formatting, ANSI styling, and text presentation utilities.

Zero-dependency formatting for human-friendly CLI and REPL outputs.
Respects NO_COLOR env var and non-interactive ttys.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
from typing import Sequence

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Standard ANSI escape codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

BG_BLUE = "\033[44m"
BG_DARK = "\033[40m"


def supports_color() -> bool:
    """Check if color is enabled (respects NO_COLOR and TTY check)."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def style(text: str, *codes: str, enable: bool | None = None) -> str:
    """Apply ANSI style codes if color is enabled."""
    active = supports_color() if enable is None else enable
    if not active or not codes:
        return text
    prefix = "".join(codes)
    return f"{prefix}{text}{RESET}"


def terminal_width(default: int = 80) -> int:
    """Get current terminal width with fallback."""
    try:
        cols, _ = shutil.get_terminal_size((default, 24))
        return min(max(cols, 40), 120)
    except Exception:
        return default


def banner(title: str, subtitle: str = "", width: int | None = None, enable_color: bool | None = None) -> str:
    """Format a styled header banner."""
    w = width or terminal_width()
    line = "━" * w
    t = f"  {title.upper()}  "
    if subtitle:
        t += f"[{subtitle}]  "
    centered = t.center(w, "━")
    return "\n" + style(centered, BOLD, CYAN, enable=enable_color) + "\n"


def section_header(title: str, width: int | None = None, enable_color: bool | None = None) -> str:
    """Format a section divider line."""
    w = width or terminal_width()
    prefix = f"── {title} "
    fill_len = max(0, w - len(prefix))
    full = prefix + ("─" * fill_len)
    return style(full, BOLD, BLUE, enable=enable_color)


def box_panel(
    title: str,
    lines: Sequence[str],
    width: int | None = None,
    border_color: str = CYAN,
    enable_color: bool | None = None,
) -> str:
    """Draw a unicode boxed panel with content lines."""
    w = width or terminal_width()
    inner_w = max(20, w - 4)

    t_styled = f" {title} "
    top_bar_len = max(0, inner_w - len(title) - 2)
    top = f"┌─{t_styled}{'─' * top_bar_len}┐"
    bottom = f"└{'─' * (inner_w + 2)}┘"

    top_rendered = style(top, border_color, BOLD, enable=enable_color)
    bottom_rendered = style(bottom, border_color, enable=enable_color)

    out = [top_rendered]
    for line in lines:
        clean_len = len(strip_ansi(line))
        padding = max(0, inner_w - clean_len)
        left_border = style("│ ", border_color, enable=enable_color)
        right_border = style(" │", border_color, enable=enable_color)
        out.append(f"{left_border}{line}{' ' * padding}{right_border}")
    out.append(bottom_rendered)
    return "\n".join(out)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text for width calculation."""
    return _ANSI_ESCAPE.sub("", text)


def wrap_text(text: str, width: int = 80, indent: str = "") -> list[str]:
    """Wrap text to specified width with optional indentation."""
    target_width = max(20, width - len(indent))
    wrapped = textwrap.wrap(text, width=target_width)
    if not wrapped:
        return [""]
    return [f"{indent}{line}" for line in wrapped]
