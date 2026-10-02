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
from email.parser import BytesParser
from email.policy import default
import enum
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import sqlite3
import tempfile
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, urlparse
import zipfile

from search.linking.egw_importer import BulkImporter
from search.corpus.query import query
from search.ui.study_service import StudyService
from search.ui.themes import DEFAULT_THEME, THEMES

from search.resource import __version__, get_data_dir, get_web_dir, verify_data_bundle
from search.ui.version_check import default_version_checker

WEB_ROOT = get_web_dir()


# Web-native themes beyond the TUI palettes: always present in the catalog so
# the theme dropdown and persisted prefs can select them (sepia is the default
# Study Room Desk face per ADR-025; light is daytime paper; dark is walnut).
WEB_NATIVE_THEMES: dict[str, dict[str, str]] = {
    "sepia": {
        "id": "sepia",
        "name": "Sepia (Study Room Desk)",
        "description": "Warm parchment substrate with deep indigo, gold, and olive accents.",
    },
    "light": {
        "id": "light",
        "name": "Light Paper",
        "description": "Clean light paper tone for daytime reading.",
    },
    "dark": {
        "id": "dark",
        "name": "Dark Walnut (Study Room Night)",
        "description": "Deep walnut charcoal substrate with warm parchment text.",
    },
}

# Verbose per-verse enrichment is intentionally omitted from the wire until a
# tab in the UI actually needs it (serialize on demand via ?eager=1, not by
# default). EGW commentary is deliberately NOT serialized at all: the TUI/CLI
# render it against the local egw.db, but the web API stays copyright-light
# (ADR-002/023) and its frontend does not render EGW yet.
_PASSAGE_FIELDS = ("ref", "book_code", "book_name", "start_chapter",
                   "start_verse", "end_chapter", "end_verse", "verses",
                   "prev_ref", "next_ref")


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


def _verse_payload(verse: Any) -> dict[str, Any]:
    """Wire payload for a single verse: text, translations, Strong's list, prophetic symbols."""
    payload = {
        "osis": verse.osis,
        "chapter": verse.chapter,
        "verse": verse.verse,
        "text": verse.text,
        "translations": verse.translations,
        "strongs_list": verse.strongs_list,
        "tokens": verse.tokens,
        "original_text": verse.original_text,
    }
    if getattr(verse, "prophetic_symbols", None):
        payload["prophetic_symbols"] = _jsonable(verse.prophetic_symbols)
    if getattr(verse, "sanctuary_stations", None):
        payload["sanctuary_stations"] = _jsonable(verse.sanctuary_stations)
    if getattr(verse, "cross_references", None):
        payload["cross_references"] = _jsonable(verse.cross_references)
    if getattr(verse, "curated_xrefs", None):
        payload["curated_xrefs"] = _jsonable(verse.curated_xrefs)
    return payload


# Per-verse fields included only under ?eager=1, attached to the verse (never
# collapsed onto the passage object — each verse keeps its own enrichment).
_EAGER_VERSE_FIELDS = ("semantic_frames", "verbal_nuances",
                       "discourse_markers", "ot_citations")


def _passage_payload(passage: Any, eager_frames: bool, study: StudyService | None = None) -> dict[str, Any]:
    """Serialize a PassageStudy to the wire shape (omits heavy per-verse data).

    EGW correlations are deliberately excluded (copyright-light web API).
    Argument flow is cheap and useful; include when present.
    """
    data = {name: getattr(passage, name) for name in _PASSAGE_FIELDS}
    data["verses"] = [_verse_payload(v) for v in passage.verses]
    if getattr(passage, "argument_flow", None):
        data["argument_flow"] = _jsonable(passage.argument_flow)
    if eager_frames:
        # data["verses"] and passage.verses are index-parallel (built in the
        # same order from the same source), so per-verse enrichment attaches
        # to the correct verse without a keyed lookup.
        for i, verse in enumerate(data["verses"]):
            verse_obj = passage.verses[i]
            for field in _EAGER_VERSE_FIELDS:
                value = getattr(verse_obj, field, None)
                if value:
                    verse[field] = _jsonable(value)
            if study and hasattr(study, "get_verse_lexicon"):
                lex = study.get_verse_lexicon(verse_obj)
                if lex:
                    verse["lexicon"] = _jsonable(lex)
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
                ".png": "image/png",
                ".ico": "image/x-icon",
                ".svg": "image/svg+xml",
                ".webp": "image/webp",
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
                self._api_verify_bundle(query)
            elif path == "/api/passage":
                self._api_passage(query)
            elif path == "/api/translations":
                self._api_translations()
            elif path == "/api/nuance":
                self._api_nuance(query)
            elif path == "/api/prophetic":
                self._api_prophetic(query)
            elif path == "/api/sanctuary":
                self._api_sanctuary(query)
            elif path == "/api/commentary":
                self._api_commentary(query)
            elif path == "/api/xrefs":
                self._api_xrefs(query)
            elif path == "/api/c4-query":
                self._api_c4_query(query)
            elif path == "/api/search":
                self._api_search(query)
            elif path == "/api/import-books":
                self._api_import_books_status()
            elif path == "/api/model/status":
                self._api_model_status()
            elif path == "/api/model/download/progress":
                self._api_model_download_progress()
            elif path == "/api/library/vectorize/progress":
                self._api_library_vectorize_progress()
            elif path == "/api/check-update":
                self._api_check_update(query)
            elif path.startswith("/api/"):
                self._reply_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            else:
                self._serve_static(path)

        def do_POST(self) -> None:  # noqa: N802 (http.server naming)
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if path == "/api/import-books":
                self._api_import_books(query)
            elif path == "/api/model/download":
                self._api_model_download()
            elif path == "/api/library/vectorize":
                self._api_library_vectorize(query)
            elif path.startswith("/api/"):
                self._reply_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            else:
                self._reply_error(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")

        def _api_health(self) -> None:
            themes = [
                {"id": tid, "name": t.name, "description": t.description}
                for tid, t in THEMES.items()
            ]
            # Web-native themes first so the default face ("sepia") is selectable.
            themes = list(WEB_NATIVE_THEMES.values()) + themes
            has_egw = study.egw_db is not None and study.egw_db.db_path.is_file()
            egw_stats = study.get_egw_stats()
            self._reply_json(HTTPStatus.OK, {
                "status": "ok",
                "version": __version__,
                # The web face defaults to the Study Room Desk sepia token set (ADR-025);
                # the TUI keeps its own DEFAULT_THEME (transparent) internally.
                "default_theme": "sepia",
                "themes": themes,
                "translations_url": "/api/translations",
                "search_url": "/api/search",
                "nuance_url": "/api/nuance",
                "prophetic_url": "/api/prophetic",
                "sanctuary_url": "/api/sanctuary",
                "commentary_url": "/api/commentary",
                "xrefs_url": "/api/xrefs",
                "verify_bundle_url": "/api/verify-bundle",
                "import_books_url": "/api/import-books",
                "model_status_url": "/api/model/status",
                "model_download_url": "/api/model/download",
                "library_vectorize_url": "/api/library/vectorize",
                "check_update_url": "/api/check-update",
                "egw_available": has_egw,
                "egw_stats": egw_stats,
            })

        def _api_check_update(self, query: dict[str, list[str]]) -> None:
            force = query.get("force", ["0"])[0].lower() in ("1", "true", "yes")
            result = default_version_checker.check_for_updates(current_version=__version__, force=force)
            self._reply_json(HTTPStatus.OK, result)

        def _api_search(self, query: dict[str, list[str]]) -> None:
            raw_q = query.get("q", query.get("query", [""]))[0].strip()
            if not raw_q:
                self._reply_json(HTTPStatus.OK, {
                    "status": "ok",
                    "query": "",
                    "is_reference": False,
                    "reference_target": None,
                    "expansion": {},
                    "total_hits": 0,
                    "counts": {"all": 0, "scripture": 0, "translations": 0, "original": 0, "commentary": 0, "curated": 0},
                    "results": [],
                })
                return

            sources_raw = query.get("sources", query.get("source", ["all"]))[0].strip()
            sources = [s.strip().lower() for s in sources_raw.split(",") if s.strip()] if sources_raw else ["all"]
            limit_str = query.get("limit", ["50"])[0].strip()
            try:
                limit = max(1, min(200, int(limit_str)))
            except ValueError:
                limit = 50

            book = query.get("book", [None])[0]
            testament = query.get("testament", [None])[0]
            translation = query.get("translation", [None])[0]
            strongs = query.get("strongs", [None])[0]
            domain = query.get("domain", [None])[0]
            egw_book = query.get("egw_book", query.get("egw", [None]))[0]
            expand_raw = query.get("expand", ["1"])[0].strip().lower()
            expand = expand_raw not in ("0", "false", "no")
            mode = query.get("mode", ["hybrid"])[0].strip().lower()

            try:
                res = study.search(
                    query=raw_q,
                    sources=sources,
                    limit=limit,
                    mode=mode,
                    book=book,
                    testament=testament,
                    translation=translation,
                    strongs=strongs,
                    domain=domain,
                    egw_book=egw_book,
                    expand=expand,
                )
                self._reply_json(HTTPStatus.OK, {"status": "ok", **_jsonable(res)})
            except Exception as exc:
                self._reply_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"search error: {exc}")

        def _api_c4_query(self, params: dict[str, list[str]]) -> None:
            # Thin pass-through to search.corpus.query (roadmap C4).
            # Facets from query params; free-text from q/text/query.
            facets: dict[str, list[str]] = {}
            for facet in ("book", "theme", "translation", "language", "status"):
                values = params.get(facet, [])
                if values:
                    facets[facet] = [str(v) for v in values]
            text = params.get("q", params.get("text", params.get("query", [""])))[0].strip() or None
            limit = int(params.get("limit", ["50"])[0])
            try:
                results = query(facets or None, text, limit)
            except Exception as exc:
                self._reply_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"c4 query failed: {exc}")
                return
            self._reply_json(HTTPStatus.OK, {
                "status": "ok",
                "facets": facets,
                "text": text,
                "results": _jsonable(results),
                "count": len(results),
            })

        def _api_verify_bundle(self, query: dict[str, list[str]]) -> None:
            # This endpoint backs the user-initiated "Verify data bundle"
            # action in the settings panel, so it runs the AUTHORITATIVE deep
            # content check by default (~25-30 s on whole-Bible data): the fast
            # structural check would report valid on cell-level tampering,
            # which defeats the purpose of user-facing verification (ADR-027).
            # `?deep=0` opts into the fast path for lightweight callers.
            deep = query.get("deep", ["1"])[0].strip().lower() not in ("0", "false", "no")
            try:
                is_valid, errors = verify_data_bundle(deep=deep)
            except Exception as exc:
                self._reply_json(HTTPStatus.OK, {
                    "status": "error",
                    "valid": False,
                    "deep": deep,
                    "errors": [f"Bundle verification failed: {exc}"],
                    "data_dir": str(get_data_dir()),
                })
                return
            self._reply_json(HTTPStatus.OK, {
                "status": "ok" if is_valid else "error",
                "valid": is_valid,
                "deep": deep,
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
                payload = _passage_payload(passage, eager, study=study)
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

        def _api_sanctuary(self, query: dict[str, list[str]]) -> None:
            station_id = query.get("station", query.get("id", [""]))[0].strip()
            if station_id:
                station = study.get_sanctuary_station(station_id)
                if not station:
                    self._reply_error(HTTPStatus.NOT_FOUND, f"unknown sanctuary station {station_id!r}")
                    return
                self._reply_json(HTTPStatus.OK, {
                    "status": "ok",
                    "station": _jsonable(station),
                })
                return

            ref = query.get("ref", [""])[0].strip()
            if ref:
                try:
                    stations = study.get_annotated_sanctuary_stations_for_passage(ref)
                    self._reply_json(HTTPStatus.OK, {
                        "status": "ok",
                        "ref": ref,
                        "stations": _jsonable(stations),
                        "count": len(stations),
                    })
                    return
                except ValueError as exc:
                    self._reply_error(HTTPStatus.BAD_REQUEST, f"cannot resolve sanctuary passage {ref!r}: {exc}")
                    return
                except Exception as exc:
                    self._reply_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"error resolving sanctuary stations: {exc}")
                    return

            compartment = query.get("compartment", [""])[0].strip() or None
            q = query.get("q", query.get("query", [""]))[0].strip() or None

            if compartment or q:
                stations = study.get_sanctuary_stations(compartment=compartment, query=q)
                self._reply_json(HTTPStatus.OK, {
                    "status": "ok",
                    "compartment": compartment,
                    "query": q,
                    "stations": _jsonable(stations),
                    "count": len(stations),
                })
                return

            # No filter parameters -> return full structured knowledge graph
            sanctuary_data = study.get_sanctuary_data()
            self._reply_json(HTTPStatus.OK, {
                "status": "ok",
                **_jsonable(sanctuary_data),
            })

        def _api_commentary(self, query: dict[str, list[str]]) -> None:
            has_egw = study.egw_db is not None and study.egw_db.exists()
            if not has_egw:
                self._reply_json(HTTPStatus.OK, {
                    "status": "ok",
                    "available": False,
                    "message": "Spirit of Prophecy database (egw.db) not installed.",
                    "correlations": [],
                    "count": 0,
                })
                return

            token = query.get("token", [""])[0].strip()
            if token:
                ch_data = study.get_egw_chapter_for_token(token)
                if not ch_data:
                    self._reply_error(HTTPStatus.NOT_FOUND, f"unknown EGW citation token {token!r}")
                    return
                b_code = ch_data["book_code"]
                ch_num = ch_data.get("chapter_num")
                prev_ch, next_ch = study.get_egw_adjacent_chapters(b_code, ch_num) if ch_num is not None else (None, None)
                self._reply_json(HTTPStatus.OK, {
                    "status": "ok",
                    "available": True,
                    "token": token,
                    "book_code": b_code,
                    "book_title": ch_data["book_title"],
                    "chapter_num": ch_num,
                    "chapter_title": ch_data["chapter_title"],
                    "target_id": ch_data["target_id"],
                    "target_page": ch_data["target_page"],
                    "target_paragraph": ch_data["target_paragraph"],
                    "prev_chapter": prev_ch,
                    "next_chapter": next_ch,
                    "paragraphs": ch_data["paragraphs"],
                    "count": len(ch_data["paragraphs"]),
                })
                return

            book = query.get("book", [""])[0].strip().upper()
            raw_chap = query.get("chapter", [""])[0].strip()
            if book and raw_chap:
                try:
                    ch_num = int(raw_chap)
                except ValueError:
                    self._reply_error(HTTPStatus.BAD_REQUEST, f"invalid chapter number {raw_chap!r}")
                    return
                paras = study.get_egw_chapter(book, ch_num)
                info = study.get_egw_chapter_info(book, ch_num)
                if not paras and not info:
                    self._reply_error(HTTPStatus.NOT_FOUND, f"chapter {ch_num} not found in book {book}")
                    return
                prev_ch, next_ch = study.get_egw_adjacent_chapters(book, ch_num)
                title = (info and info.get("chapter_title")) or (paras and paras[0].get("chapter_title")) or f"Chapter {ch_num}"
                btitle = (info and info.get("book_title")) or (paras and paras[0].get("book_title")) or book
                self._reply_json(HTTPStatus.OK, {
                    "status": "ok",
                    "available": True,
                    "book_code": book,
                    "book_title": btitle,
                    "chapter_num": ch_num,
                    "chapter_title": title,
                    "prev_chapter": prev_ch,
                    "next_chapter": next_ch,
                    "paragraphs": paras,
                    "count": len(paras),
                })
                return

            ref = query.get("ref", [""])[0].strip()
            if ref:
                limit_str = query.get("limit", ["10"])[0].strip()
                try:
                    limit = max(1, min(50, int(limit_str)))
                except ValueError:
                    limit = 10
                correlations = study.get_egw_correlations_for_passage(ref, limit=limit)
                self._reply_json(HTTPStatus.OK, {
                    "status": "ok",
                    "available": True,
                    "ref": ref,
                    "correlations": correlations,
                    "count": len(correlations),
                })
                return

            self._reply_error(HTTPStatus.BAD_REQUEST, "missing 'ref', 'token', or 'book'+'chapter' parameters")

        def _api_xrefs(self, query: dict[str, list[str]]) -> None:
            raw_ref = query.get("verse", [None])[0] or query.get("ref", [None])[0]
            if not raw_ref or not raw_ref.strip():
                self._reply_error(HTTPStatus.BAD_REQUEST, "missing 'verse' or 'ref' query parameter")
                return

            limit_raw = query.get("limit", ["25"])[0]
            try:
                limit = max(1, min(100, int(limit_raw)))
            except ValueError:
                limit = 25

            min_votes_raw = query.get("min_votes", ["0"])[0]
            try:
                min_votes = max(0, int(min_votes_raw))
            except ValueError:
                min_votes = 0

            bundle = study.get_cross_reference_bundle(
                raw_ref.strip(), limit=limit, min_votes=min_votes
            )
            self._reply_json(HTTPStatus.OK, _jsonable(bundle))

        def _api_import_books_status(self) -> None:
            stats = study.get_egw_stats()
            self._reply_json(HTTPStatus.OK, {
                "status": "ok",
                "stats": stats,
            })

        def _api_import_books(self, query: dict[str, list[str]]) -> None:
            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                self._reply_error(HTTPStatus.BAD_REQUEST, "invalid Content-Length header")
                return

            if content_length <= 0:
                self._reply_error(HTTPStatus.BAD_REQUEST, "empty upload body")
                return

            # Reject files larger than 500 MB to protect memory
            if content_length > 500 * 1024 * 1024:
                self._reply_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "file exceeds maximum allowed size (500 MB)")
                return

            body = self.rfile.read(content_length)
            content_type = self.headers.get("Content-Type", "")

            uploaded_files: list[tuple[str, bytes]] = []

            if "multipart/form-data" in content_type:
                try:
                    full_payload = b"Content-Type: " + content_type.encode("utf-8") + b"\r\n\r\n" + body
                    msg = BytesParser(policy=default).parsebytes(full_payload)
                    for part in msg.iter_parts():
                        fname = part.get_filename()
                        if fname:
                            payload = part.get_payload(decode=True)
                            if payload:
                                uploaded_files.append((fname, payload))
                except Exception as exc:
                    self._reply_error(HTTPStatus.BAD_REQUEST, f"failed to parse multipart upload: {exc}")
                    return
            else:
                # Direct binary upload with header or query param
                fname = query.get("filename", [""])[0] or self.headers.get("X-Filename", "")
                if not fname:
                    cd = self.headers.get("Content-Disposition", "")
                    if "filename=" in cd:
                        fname = cd.split("filename=")[-1].strip('"\'; ')
                if not fname:
                    fname = "uploaded_book.epub"
                uploaded_files.append((fname, body))

            if not uploaded_files:
                self._reply_error(HTTPStatus.BAD_REQUEST, "no valid files detected in upload")
                return

            results = []
            total_paras_added = 0

            with study.lock:
                with tempfile.TemporaryDirectory() as tmp_dir_str:
                    tmp_dir = Path(tmp_dir_str)
                    for raw_name, data in uploaded_files:
                        fname = Path(raw_name).name
                        ext = Path(fname).suffix.lower()

                        if ext in (".db", ".sqlite", ".sqlite3") or fname == "egw.db":
                            target_tmp = tmp_dir / fname
                            target_tmp.write_bytes(data)
                            try:
                                test_conn = sqlite3.connect(str(target_tmp))
                                cur = test_conn.execute(
                                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('egw_paragraphs', 'egw_books');"
                                )
                                has_table = cur.fetchone() is not None
                                test_conn.close()
                            except Exception as exc:
                                results.append({"filename": fname, "status": "error", "error": f"Invalid SQLite file: {exc}"})
                                continue

                            if not has_table:
                                results.append({
                                    "filename": fname,
                                    "status": "error",
                                    "error": "Missing egw_paragraphs table in uploaded SQLite database.",
                                })
                                continue

                            # Atomically replace egw.db
                            study.replace_egw_db(target_tmp)
                            stats = study.get_egw_stats()
                            results.append({
                                "filename": fname,
                                "status": "ok",
                                "type": "database",
                                "total_paragraphs": stats["paragraphs_count"],
                                "total_books": stats["books_count"],
                            })

                        elif ext == ".zip":
                            zip_file_path = tmp_dir / fname
                            zip_file_path.write_bytes(data)
                            extract_dir = tmp_dir / f"extracted_{fname}"
                            extract_dir.mkdir(exist_ok=True)
                            try:
                                with zipfile.ZipFile(zip_file_path, "r") as zf:
                                    for member in zf.infolist():
                                        target_p = (extract_dir / member.filename).resolve()
                                        if not str(target_p).startswith(str(extract_dir.resolve())):
                                            raise ValueError(f"Dangerous path in archive: {member.filename}")
                                    zf.extractall(extract_dir)
                            except Exception as exc:
                                results.append({"filename": fname, "status": "error", "error": f"Invalid ZIP archive: {exc}"})
                                continue

                            # Check if a .db is inside the zip
                            db_files = list(extract_dir.glob("**/*.db")) + list(extract_dir.glob("**/*.sqlite*"))
                            db_imported = False
                            if db_files:
                                best_db = db_files[0]
                                try:
                                    test_conn = sqlite3.connect(str(best_db))
                                    cur = test_conn.execute(
                                        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('egw_paragraphs', 'egw_books');"
                                    )
                                    has_table = cur.fetchone() is not None
                                    test_conn.close()
                                except Exception:
                                    has_table = False
                                if has_table:
                                    study.replace_egw_db(best_db)
                                    stats = study.get_egw_stats()
                                    results.append({
                                        "filename": fname,
                                        "status": "ok",
                                        "type": "database_from_zip",
                                        "total_paragraphs": stats["paragraphs_count"],
                                        "total_books": stats["books_count"],
                                    })
                                    db_imported = True

                            if not db_imported:
                                egw_inst = study.ensure_egw_db()
                                importer = BulkImporter(egw_inst)
                                imported_counts = importer.import_directory(extract_dir, recursive=True)
                                added = sum(max(0, c) for c in imported_counts.values())
                                total_paras_added += added
                                results.append({
                                    "filename": fname,
                                    "status": "ok",
                                    "type": "zip_archive",
                                    "files_imported": len(imported_counts),
                                    "paragraphs_added": added,
                                })

                        elif ext in (".epub", ".txt", ".md", ".json"):
                            target_tmp = tmp_dir / fname
                            target_tmp.write_bytes(data)
                            egw_inst = study.ensure_egw_db()
                            importer = BulkImporter(egw_inst)
                            try:
                                added = importer.import_file(target_tmp)
                                total_paras_added += max(0, added)
                                results.append({
                                    "filename": fname,
                                    "status": "ok",
                                    "type": ext.lstrip("."),
                                    "paragraphs_added": added,
                                })
                            except Exception as exc:
                                results.append({"filename": fname, "status": "error", "error": str(exc)})
                        else:
                            results.append({
                                "filename": fname,
                                "status": "error",
                                "error": f"Unsupported format '{ext}'. Expected .epub, .txt, .md, .json, .zip, or .db",
                            })

                    study.reload_egw_db()
                    final_stats = study.get_egw_stats()

            self._reply_json(HTTPStatus.OK, {
                "status": "ok",
                "results": results,
                "paragraphs_added": total_paras_added,
                "stats": final_stats,
            })

        def _api_model_status(self) -> None:
            status = study.get_neural_model_status()
            self._reply_json(HTTPStatus.OK, status)

        def _api_model_download(self) -> None:
            try:
                res = study.start_model_download()
                self._reply_json(HTTPStatus.OK, res)
            except Exception as exc:
                self._reply_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                    "status": "error",
                    "error": str(exc),
                })

        def _api_model_download_progress(self) -> None:
            res = study.get_model_download_progress()
            self._reply_json(HTTPStatus.OK, {
                "status": "ok",
                **res,
            })

        def _api_library_vectorize(self, query: dict[str, list[str]]) -> None:
            model_status = study.get_neural_model_status()
            if not model_status.get("model_available"):
                self._reply_error(
                    HTTPStatus.BAD_REQUEST,
                    "Neural model is not installed. Please download the model first.",
                )
                return

            force = query.get("force", ["0"])[0].lower() in ("1", "true", "yes")
            batch_size_str = query.get("batch_size", ["32"])[0]
            try:
                batch_size = max(1, min(128, int(batch_size_str)))
            except ValueError:
                batch_size = 32

            try:
                res = study.start_library_vectorization(batch_size=batch_size, force=force)
                self._reply_json(HTTPStatus.OK, res)
            except (ValueError, RuntimeError) as exc:
                self._reply_error(HTTPStatus.BAD_REQUEST, str(exc))
            except Exception as exc:
                self._reply_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

        def _api_library_vectorize_progress(self) -> None:
            res = study.get_library_vectorize_progress()
            self._reply_json(HTTPStatus.OK, {
                "status": "ok",
                **res,
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