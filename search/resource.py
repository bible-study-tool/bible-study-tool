"""Resource and path resolution for source and frozen environments (WP-029, ADR-024).

Provides centralized, PyInstaller-aware resolution for:
1. Application and bundle roots (sys._MEIPASS when frozen, repo root when in source/dev).
2. Sidecar data directories (data/ directory alongside the executable or repo root).
3. Static web assets (web/ directory).
4. Lexicons (lexicons/ directory).
5. Internal package fixtures and bundled resources.

This eliminates hardcoded `Path(__file__)` assumptions and current-working-directory
dependencies across the engine and UI layers.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys


def is_frozen() -> bool:
    """Return True if running in a frozen executable (e.g. PyInstaller or Nuitka)."""
    return getattr(sys, "frozen", False)


def get_bundle_root() -> Path:
    """Return the base directory for bundled code and package assets.

    In a frozen onefile/onedir app, this is ``sys._MEIPASS`` (or the executable directory).
    In a source checkout or venv, this is the repository root directory.
    """
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    # __file__ is search/resource.py -> parents[1] is repo root
    return Path(__file__).resolve().parents[1]


def get_app_dir() -> Path:
    """Return the runtime directory containing the executable or main script.

    In a frozen application, sidecar folders (such as ``data/`` and ``lexicons/``)
    live alongside the executable in this directory per ADR-024.
    In development, this matches the repository root.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return get_bundle_root()


def get_repo_root() -> Path:
    """Return the repository or application root directory."""
    env_root = os.environ.get("BIBLE_STUDY_REPO_ROOT")
    if env_root:
        p = Path(env_root).resolve()
        if p.exists():
            return p
    return get_app_dir()


def get_data_dir() -> Path:
    """Return the directory where database files (bible.db, macula.db, egw.db) reside.

    Precedence:
    1. ``BIBLE_STUDY_DATA_DIR`` environment variable if set and existing.
    2. Sidecar ``data/`` alongside the application executable (``get_app_dir() / "data"``).
    3. Bundled ``data/`` in the bundle root (``get_bundle_root() / "data"``).
    4. Current working directory ``Path.cwd() / "data"``.
    5. Fallback: ``get_app_dir() / "data"``.
    """
    env_data = os.environ.get("BIBLE_STUDY_DATA_DIR")
    if env_data:
        p = Path(env_data).resolve()
        if p.exists():
            return p

    app_data = get_app_dir() / "data"
    if app_data.is_dir():
        return app_data

    bundle_data = get_bundle_root() / "data"
    if bundle_data.is_dir():
        return bundle_data

    cwd_data = Path.cwd() / "data"
    if cwd_data.is_dir():
        return cwd_data

    return app_data


def get_web_dir() -> Path:
    """Return the directory containing static web frontend assets (HTML, CSS, JS).

    Precedence:
    1. ``BIBLE_STUDY_WEB_DIR`` environment variable if set and existing.
    2. Bundled ``web/`` in the bundle root (``get_bundle_root() / "web"``).
    3. Sidecar ``web/`` alongside the executable (``get_app_dir() / "web"``).
    4. Packaged ``search/ui/web`` in bundle root.
    5. Fallback: ``get_bundle_root() / "web"``.
    """
    env_web = os.environ.get("BIBLE_STUDY_WEB_DIR")
    if env_web:
        p = Path(env_web).resolve()
        if p.exists():
            return p

    bundle_web = get_bundle_root() / "web"
    if bundle_web.is_dir():
        return bundle_web

    app_web = get_app_dir() / "web"
    if app_web.is_dir():
        return app_web

    pkg_web = get_bundle_root() / "search" / "ui" / "web"
    if pkg_web.is_dir():
        return pkg_web

    return bundle_web


def get_lexicons_dir() -> Path:
    """Return the directory containing canonical lexicons.

    Precedence:
    1. ``BIBLE_STUDY_LEXICONS_DIR`` environment variable if set and existing.
    2. Sidecar ``lexicons/`` alongside the executable (``get_app_dir() / "lexicons"``).
    3. ``get_data_dir() / "lexicons"`` (if sidecar layout packages lexicons in data/).
    4. Bundled ``lexicons/`` in bundle root (``get_bundle_root() / "lexicons"``).
    5. Current working directory ``Path.cwd() / "lexicons"``.
    6. Fallback: ``get_app_dir() / "lexicons"``.
    """
    env_lex = os.environ.get("BIBLE_STUDY_LEXICONS_DIR")
    if env_lex:
        p = Path(env_lex).resolve()
        if p.exists():
            return p

    app_lex = get_app_dir() / "lexicons"
    if app_lex.is_dir():
        return app_lex

    data_lex = get_data_dir() / "lexicons"
    if data_lex.is_dir():
        return data_lex

    bundle_lex = get_bundle_root() / "lexicons"
    if bundle_lex.is_dir():
        return bundle_lex

    cwd_lex = Path.cwd() / "lexicons"
    if cwd_lex.is_dir():
        return cwd_lex

    return app_lex


def data_path(rel_path: str | Path) -> Path:
    """Resolve a database or data asset path.

    Accepts relative paths with or without the leading ``data/`` prefix.
    If the path is already absolute, it is returned directly.
    """
    p = Path(rel_path)
    if p.is_absolute():
        return p

    # Strip leading 'data/' or 'data\\' if present
    parts = p.parts
    if parts and parts[0] == "data":
        rel = Path(*parts[1:])
    else:
        rel = p

    # 1. Look inside get_data_dir()
    cand = get_data_dir() / rel
    if cand.exists():
        return cand

    # 2. Look relative to get_app_dir() directly
    cand_app = get_app_dir() / p
    if cand_app.exists():
        return cand_app

    # 3. Look relative to CWD
    cand_cwd = Path.cwd() / p
    if cand_cwd.exists():
        return cand_cwd

    # Default to expected location under data dir
    return get_data_dir() / rel


def lexicon_path(rel_path: str | Path) -> Path:
    """Resolve a lexicon file path (e.g. strongs-lexicon.json).

    Accepts relative paths with or without the leading ``lexicons/`` prefix.
    If the path is already absolute, it is returned directly.
    """
    p = Path(rel_path)
    if p.is_absolute():
        return p

    parts = p.parts
    if parts and parts[0] == "lexicons":
        rel = Path(*parts[1:])
    else:
        rel = p

    cand = get_lexicons_dir() / rel
    if cand.exists():
        return cand

    cand_app = get_app_dir() / p
    if cand_app.exists():
        return cand_app

    cand_cwd = Path.cwd() / p
    if cand_cwd.exists():
        return cand_cwd

    return get_lexicons_dir() / rel


def resource_path(rel_path: str | Path) -> Path:
    """Resolve an internal bundled package resource or fixture.

    Searches bundle root (sys._MEIPASS or source repo) and app directory.
    """
    p = Path(rel_path)
    if p.is_absolute():
        return p

    cand_bundle = get_bundle_root() / p
    if cand_bundle.exists():
        return cand_bundle

    if p.parts and p.parts[0] == "search":
        cand_stripped = get_bundle_root() / Path(*p.parts[1:])
        if cand_stripped.exists():
            return cand_stripped

    cand_app = get_app_dir() / p
    if cand_app.exists():
        return cand_app

    return cand_bundle
