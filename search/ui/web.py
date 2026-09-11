"""Primary application entrypoint for Adventist Bible Study Tool (WP-029, ADR-024).

GUI-first launcher:
- Default invocation launches local web study workstation and opens default browser.
- '--tui' flag launches full-screen interactive Textual terminal workstation.
- Standard CLI subcommands ('read', 'study', 'word', 'search', 'egw', 'frame', 'shell')
  are supported directly.
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from typing import Callable, Sequence

from search.ui.cli import (
    DEFAULT_THEME,
    THEMES,
    add_cli_subparsers,
    execute_subcommand,
    launch_interactive_tui,
)
from search.ui.study_service import StudyService
from search.ui.web_server import create_server


def _launch_browser_in_background(
    browser_url: str,
    probe_url: str,
    timeout_sec: float = 3.0,
    open_fn: Callable[[str], bool | None] | None = None,
) -> threading.Thread:
    """Probe the health endpoint in a background daemon thread until ready, then open browser."""
    def _worker() -> None:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                req = urllib.request.Request(probe_url, method="HEAD")
                with urllib.request.urlopen(req, timeout=0.2) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.05)

        target_fn = open_fn or webbrowser.open
        try:
            target_fn(browser_url)
        except Exception:
            # Headless or browser-less environments must fail soft without crashing
            pass

    t = threading.Thread(target=_worker, daemon=True, name="WebBrowserLauncher")
    t.start()
    return t


def run_web_server(
    study: StudyService | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    no_browser: bool = False,
    passage: str | None = None,
    open_browser_fn: Callable[[str], bool | None] | None = None,
    server_factory: Callable[..., object] | None = None,
    ready_event: threading.Event | None = None,
) -> int:
    """Start local web server and open browser."""
    service = study or StudyService()
    factory = server_factory or create_server
    try:
        server = factory(service, host=host, port=port)
    except OSError as err:
        sys.stderr.write(f"Error starting web server on {host}:{port}: {err}\n")
        if study is None:
            service.close()
        return 1

    local_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
    query = f"?ref={urllib.parse.quote(passage)}" if passage else ""
    browser_url = f"http://{local_host}:{port}/{query}"
    probe_url = f"http://{local_host}:{port}/api/health"

    if host in ("0.0.0.0", ""):
        print(f"Adventist Bible Study Tool — serving at http://0.0.0.0:{port} (local: {browser_url})", flush=True)
    else:
        print(f"Adventist Bible Study Tool — serving at {browser_url}", flush=True)

    if not no_browser:
        _launch_browser_in_background(browser_url, probe_url, open_fn=open_browser_fn)

    if ready_event:
        ready_event.set()

    old_sigterm = None
    if threading.current_thread() is threading.main_thread():
        try:
            def _handle_sigterm(signum: int, frame: object) -> None:
                raise KeyboardInterrupt()

            old_sigterm = signal.signal(signal.SIGTERM, _handle_sigterm)
        except (ValueError, AttributeError):
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if old_sigterm is not None:
            try:
                signal.signal(signal.SIGTERM, old_sigterm)
            except Exception:
                pass
        server.server_close()
        if study is None:
            service.close()
    return 0


def build_web_parser(prog: str = "bible-study") -> argparse.ArgumentParser:
    """Build the top-level argument parser for the bible-study CLI."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Adventist Bible Study Tool — Local Web Workstation & Deterministic Study Platform (ADR-024)",
    )
    parser.add_argument("--version", "-v", action="version", version="bible-study-tool 0.1.0")

    # Web server options
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP server host address (default: 127.0.0.1; use 0.0.0.0 for LAN/remote access)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP server TCP port (default: 8000)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="do not open web browser automatically",
    )

    # TUI options
    parser.add_argument(
        "--tui",
        action="store_true",
        help="launch full-screen terminal user interface (TUI) instead of web server",
    )
    parser.add_argument(
        "--curses",
        action="store_true",
        help="force classic curses interface instead of Textual for TUI mode",
    )
    parser.add_argument(
        "--theme",
        choices=list(THEMES.keys()) if THEMES else None,
        default=DEFAULT_THEME,
        help="color theme for Textual TUI",
    )
    parser.add_argument(
        "--passage",
        help="initial passage reference (e.g. 'John 3:16', 'Gen 1:1-3')",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Study commands")

    # Subcommand: serve (use SUPPRESS on defaults so parent flags take precedence)
    p_serve = subparsers.add_parser("serve", help="Launch the local web study workstation (default)")
    p_serve.add_argument("--host", default=argparse.SUPPRESS, help="HTTP server host address (default: 127.0.0.1)")
    p_serve.add_argument("--port", type=int, default=argparse.SUPPRESS, help="HTTP server TCP port (default: 8000)")
    p_serve.add_argument("--no-browser", action="store_true", default=argparse.SUPPRESS, help="do not open web browser automatically")
    p_serve.add_argument("--passage", default=argparse.SUPPRESS, help="initial passage reference to display")

    # Standard CLI subcommands: tui, read, study, word, search, egw, frame, shell
    add_cli_subparsers(subparsers)

    return parser


def main(
    argv: Sequence[str] | None = None,
    open_browser_fn: Callable[[str], bool | None] | None = None,
    server_factory: Callable[..., object] | None = None,
    ready_event: threading.Event | None = None,
) -> int:
    """Primary application entrypoint."""
    parser = build_web_parser(prog="bible-study")
    args = parser.parse_args(argv)

    # Dispatch to TUI mode
    if getattr(args, "tui", False) or args.subcommand == "tui":
        service = StudyService()
        try:
            passage = getattr(args, "passage", None) or "Gen 1:1"
            theme = getattr(args, "theme", DEFAULT_THEME) or DEFAULT_THEME
            force_curses = getattr(args, "curses", False)
            launch_interactive_tui(service, passage=passage, theme=theme, force_curses=force_curses)
            return 0
        finally:
            service.close()

    # Dispatch to CLI subcommands
    if args.subcommand in ("read", "study", "word", "search", "egw", "frame", "shell"):
        service = StudyService()
        try:
            return execute_subcommand(service, args)
        finally:
            service.close()

    # Default: launch local web server
    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", 8000)
    no_browser = getattr(args, "no_browser", False)
    passage = getattr(args, "passage", None)

    return run_web_server(
        host=host,
        port=port,
        no_browser=no_browser,
        passage=passage,
        open_browser_fn=open_browser_fn,
        server_factory=server_factory,
        ready_event=ready_event,
    )


if __name__ == "__main__":
    raise SystemExit(main())
