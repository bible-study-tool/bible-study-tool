"""Local-first web server for the Adventist Bible Study Tool (ADR-024).

Serves the static frontend (``web/``) and a minimal JSON API over localhost,
backed by :class:`search.ui.study_service.StudyService`. Stdlib-only on
purpose (ADR-013): no framework, no build step, no telemetry.

Phase 1 of ADR-024 hosts this in the browser tab; Phase 2 (Tauri) will host
the *same* assets. Nothing in this module is TUI-specific.

Run from the repo root::

    python -m search.ui.web_server            # http://127.0.0.1:8000
    python -m search.ui.web_server --port 8123 --host 127.0.0.1
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, urlparse

from search.ui.study_service import StudyService
from search.ui.themes import DEFAULT_THEME, THEMES

from search.resource import get_data_dir, get_web_dir, verify_data_bundle

WEB_ROOT = get_web_dir()

# Web-native themes beyond the TUI palettes: always present in the catalog so
# the theme dropdown and persisted prefs can select them (sepia is the default
# Divinity Hall Desk face per ADR-025; light is daytime paper; dark is walnut).
WEB_NATIVE_THEMES: dict[str, dict[str, str]] = {
    "sepia": {
        "id": "sepia",
        "name": "Sepia (Divinity Hall Desk)",
        "description": "Warm parchment substrate with deep indigo, gold, and olive accents.",
    },
    "light": {
        "id": "light",
        "name": "Light Paper",
        "description": "Clean light paper tone for daytime reading.",
    },
    "dark": {
        "id": "dark",
        "name": "Dark Walnut (Divinity Hall Night)",
        "description": "Deep walnut charcoal substrate with warm parchment text.",
    },
}

# Verbose per-verse enrichment is intentionally omitted from the wire until a
# tab in the UI actually needs it (serialize on demand via ?eager=1, not by
# default). EGW commentary is deliberately NOT serialized at all: the TUI/CLI
# render it against the local egw.db, but the web API stays copyright-light
# (ADR-002/023) and its frontend does not render EGW yet.
_PASSAGE_FIELDS = ("ref", "book_code", "book_name", "start_chapter",
                   "start_verse", "end_chapter", "end_verse", "verses")


def _jsonable(value: Any) -> Any:
    """Convert a nested dataclass/dict/list/Enum tree into JSON-safe primitives.

    Fail-fast per AGENTS.md: an unrecognised type raises rather than silently
    shipping as ``str(...)``, forcing the serializer to be extended when the
    data model grows.
    """
    if dataclasses.is_dataclass(value):
        return {
            f.name: _jsonable(getattr(value, f.name))
            for f in dataclasses.fields(value)
            if not f.name.startswith("_")
        }
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, enum.Enum):
        return _jsonable(value.value)
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"cannot serialize {type(value).__name__} to JSON")


def _verse_payload(study: StudyService, verse: Any) -> dict[str, Any]:
    """Wire payload for a single verse: text, translations, Strong's list, prophetic symbols."""
    payload = {
        "osis": verse.osis,
        "chapter": verse.chapter,
        "verse": verse.verse,
        "text": verse.text,
        "translations": verse.translations,
        "strongs_list": verse.strongs_list,
    }
    if getattr(verse, "prophetic_symbols", None):
        payload["prophetic_symbols"] = _jsonable(verse.prophetic_symbols)
    return payload


# Per-verse fields included only under ?eager=1, attached to the verse (never
# collapsed onto the passage object — each verse keeps its own enrichment).
_EAGER_VERSE_FIELDS = ("semantic_frames", "verbal_nuances",
                       "discourse_markers", "ot_citations")


def _passage_payload(passage: Any, eager_frames: bool) -> dict[str, Any]:
    """Serialize a PassageStudy to the wire shape (omits heavy per-verse data).

    EGW correlations are deliberately excluded (copyright-light web API).
    Argument flow is cheap and useful; include when present.
    """
    data = {name: getattr(passage, name) for name in _PASSAGE_FIELDS}
    data["verses"] = [_verse_payload(passage, v) for v in passage.verses]
    if getattr(passage, "argument_flow", None):
        data["argument_flow"] = _jsonable(passage.argument_flow)
    if eager_frames:
        # data["verses"] and passage.verses are index-parallel (built in the
        # same order from the same source), so per-verse enrichment attaches
        # to the correct verse without a keyed lookup.
        for i, verse in enumerate(data["verses"]):
            for field in _EAGER_VERSE_FIELDS:
                value = getattr(passage.verses[i], field, None)
                if value:
                    verse[field] = _jsonable(value)
    return data


def build_handler(study: StudyService, web_root: Path = WEB_ROOT) -> Callable:
    """Return an HTTP handler class bound to a StudyService and web root."""

    class StudyHandler(BaseHTTPRequestHandler):
        # Silence default stderr logging (a GUI binary should not log noise).
        def log_message(self, _format: str, *args: Any) -> None:  # noqa: D102
            pass

        def _reply(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _reply_json(self, code: int, payload: dict[str, Any]) -> None:
            text = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            self._reply(code, text, "application/json; charset=utf-8")

        def _reply_error(self, code: int, message: str) -> None:
            self._reply_json(code, {"error": message, "code": code})

        def _serve_static(self, rel_path: str) -> None:
            # Normalize and prevent directory traversal.
            root = self.server.web_root  # type: ignore[attr-defined]
            target = (root / rel_path.lstrip("/")).resolve()
            if root.resolve() not in target.parents and target != root.resolve():
                self._reply_error(HTTPStatus.FORBIDDEN, "forbidden path")
                return
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                self._reply_error(HTTPStatus.NOT_FOUND, "not found")
                return
            ctype = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
            }.get(target.suffix, "application/octet-stream")
            self._reply(HTTPStatus.OK, target.read_bytes(), ctype)

        def do_HEAD(self) -> None:  # noqa: N802 (http.server naming)
            self.do_GET()

        def do_GET(self) -> None:  # noqa: N802 (http.server naming)
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if path == "/api/health":
                self._api_health()
            elif path == "/api/verify-bundle":
                self._api_verify_bundle()
            elif path == "/api/passage":
                self._api_passage(query)
            elif path == "/api/translations":
                self._api_translations()
            elif path == "/api/nuance":
                self._api_nuance(query)
            elif path == "/api/prophetic":
                self._api_prophetic(query)
            elif path.startswith("/api/"):
                self._reply_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            else:
                self._serve_static(path)

        def _api_health(self) -> None:
            themes = [
                {"id": tid, "name": t.name, "description": t.description}
                for tid, t in THEMES.items()
            ]
            # Web-native themes first so the default face ("sepia") is selectable.
            themes = list(WEB_NATIVE_THEMES.values()) + themes
            has_egw = study.egw_db is not None and study.egw_db.db_path.is_file()
            self._reply_json(HTTPStatus.OK, {
                "status": "ok",
                "version": "0.1.0",
                # The web face defaults to the Divinity Hall Desk sepia token set (ADR-025);
                # the TUI keeps its own DEFAULT_THEME (transparent) internally.
                "default_theme": "sepia",
                "themes": themes,
                "translations_url": "/api/translations",
                "nuance_url": "/api/nuance",
                "prophetic_url": "/api/prophetic",
                "verify_bundle_url": "/api/verify-bundle",
                "egw_available": has_egw,
            })

        def _api_verify_bundle(self) -> None:
            try:
                is_valid, errors = verify_data_bundle()
            except Exception as exc:
                self._reply_json(HTTPStatus.OK, {
                    "status": "error",
                    "valid": False,
                    "errors": [f"Bundle verification failed: {exc}"],
                    "data_dir": str(get_data_dir()),
                })
                return
            self._reply_json(HTTPStatus.OK, {
                "status": "ok" if is_valid else "error",
                "valid": is_valid,
                "errors": errors,
                "data_dir": str(get_data_dir()),
            })

        def _api_passage(self, query: dict[str, list[str]]) -> None:
            refs = query.get("ref")
            if not refs or not refs[0].strip():
                self._reply_error(HTTPStatus.BAD_REQUEST, "missing 'ref' parameter")
                return
            eager = query.get("eager", ["0"])[0] in ("1", "true", "yes")
            try:
                passage = study.get_passage_study(refs[0].strip(), eager_frames=eager)
            except ValueError as exc:  # unknown book / malformed reference
                self._reply_error(HTTPStatus.BAD_REQUEST,
                                  f"cannot load passage {refs[0]!r}: {exc}")
                return
            except Exception as exc:  # unexpected engine failure -> 500, not 400
                self._reply_error(HTTPStatus.INTERNAL_SERVER_ERROR,
                                  f"engine error: {exc}")
                return
            try:
                payload = _passage_payload(passage, eager)
            except Exception as exc:  # e.g. _jsonable fail-fast (S1) -> clean 500
                self._reply_error(HTTPStatus.INTERNAL_SERVER_ERROR,
                                  f"serialization error: {exc}")
                return
            self._reply_json(HTTPStatus.OK, payload)

        def _api_translations(self) -> None:
            self._reply_json(HTTPStatus.OK, {
                "translations": _jsonable(study.get_available_translations()),
            })

        def _api_nuance(self, query: dict[str, list[str]]) -> None:
            morph = query.get("morph", [""])[0].strip()
            ref = query.get("ref", query.get("verse", [""]))[0].strip()
            strongs = query.get("strongs", [""])[0].strip()
            lang = query.get("lang", query.get("language", [""]))[0].strip()
            lemma = query.get("lemma", [""])[0].strip()
            text = query.get("text", [""])[0].strip()
            gloss = query.get("gloss", [""])[0].strip()

            if morph:
                gn = study.explain_verb(
                    morph,
                    language=lang,
                    lemma=lemma,
                    text=text,
                    gloss=gloss,
                    strongs=strongs,
                )
                if not gn:
                    self._reply_error(HTTPStatus.BAD_REQUEST, f"cannot explain morphology code {morph!r}")
                    return
                self._reply_json(HTTPStatus.OK, {
                    "status": "ok",
                    "nuance": _jsonable(gn),
                })
                return

            if ref:
                try:
                    nuances = study.get_verse_nuances(ref, strongs=strongs)
                    self._reply_json(HTTPStatus.OK, {
                        "status": "ok",
                        "ref": ref,
                        "strongs": strongs or None,
                        "nuances": _jsonable(nuances),
                        "count": len(nuances),
                    })
                    return
                except Exception as exc:
                    self._reply_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"error fetching nuances: {exc}")
                    return

            self._reply_error(HTTPStatus.BAD_REQUEST, "missing 'morph' or 'ref' parameter")

        def _api_prophetic(self, query: dict[str, list[str]]) -> None:
            symbol_id = query.get("id", [""])[0].strip()
            if symbol_id:
                sym = study.get_prophetic_symbol(symbol_id)
                if not sym:
                    self._reply_error(HTTPStatus.NOT_FOUND, f"unknown symbol {symbol_id!r}")
                    return
                self._reply_json(HTTPStatus.OK, {
                    "status": "ok",
                    "symbol": _jsonable(sym),
                })
                return

            ref = query.get("ref", [""])[0].strip()
            if ref:
                raw_proofs = query.get("include_proofs", ["true"])[0].strip().lower()
                include_proofs = raw_proofs not in ("false", "0", "no")
                try:
                    symbols = study.get_annotated_prophetic_symbols_for_passage(ref, include_proofs=include_proofs)
                    self._reply_json(HTTPStatus.OK, {
                        "status": "ok",
                        "ref": ref,
                        "include_proofs": include_proofs,
                        "symbols": _jsonable(symbols),
                        "count": len(symbols),
                    })
                    return
                except Exception as exc:
                    self._reply_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"error resolving prophetic symbols: {exc}")
                    return

            category = query.get("category", [""])[0].strip() or None
            book = query.get("book", [""])[0].strip() or None
            q = query.get("q", query.get("query", [""]))[0].strip() or None

            lex = study.get_prophetic_lexicon()
            symbols = study.get_prophetic_symbols(category=category, book=book, query=q)
            self._reply_json(HTTPStatus.OK, {
                "status": "ok",
                "version": lex.version,
                "title": lex.title,
                "categories": lex.categories,
                "symbols": _jsonable(symbols),
                "count": len(symbols),
            })

    return StudyHandler


def create_server(
    study: StudyService,
    web_root: Path = WEB_ROOT,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> ThreadingHTTPServer:
    """Create and bind a ThreadingHTTPServer without starting it."""
    handler = build_handler(study, web_root)

    class BoundServer(ThreadingHTTPServer):
        # `web_root` is attached after definition (a class body cannot see
        # enclosing function locals). Exposed so the handler can resolve static.
        daemon_threads: bool = True

    BoundServer.web_root = web_root
    return BoundServer((host, port), handler)


def main(argv: Iterable[str] | None = None) -> int:
    """Console/launcher entrypoint for the local web server."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address (default 127.0.0.1; keep localhost)")
    parser.add_argument("--port", type=int, default=8000, help="TCP port (default 8000)")
    args = parser.parse_args(argv)

    study = StudyService()  # resolves data/ + lexicons/ under the repo root
    server = create_server(study, host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}"
    print(f"Adventist Bible Study Tool — serving at {url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        study.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())