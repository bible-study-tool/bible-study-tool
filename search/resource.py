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

import hashlib
import os
from pathlib import Path
import sys

__version__ = "0.1.2"


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

    candidates = (
        get_data_dir() / rel,
        get_app_dir() / "data" / rel,
        get_app_dir() / p,
        Path.cwd() / p,
        Path.cwd() / "data" / rel,
    )
    seen = set()
    for cand in candidates:
        if cand not in seen:
            seen.add(cand)
            if cand.exists():
                return cand

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


def verify_data_bundle(
    data_dir: Path | None = None,
    deep: bool = False,
) -> tuple[bool, list[str]]:
    """Verify integrity of the sidecar data bundle.

    Two complementary layers (ADR-027):
      1. Content-level: SQLite DBs (bible.db, macula.db) are verified against
         data/INTEGRITY.json by canonical content hash (schema + every row),
         NOT raw bytes. SQLite files are not byte-reproducible across
         toolchains, so content hashing is the only honest cross-machine check.
      2. Byte-level: JSON artifacts (lexicons, schemas) are byte-deterministic
         and verified against data/SHA256SUMS as before.

    Args:
        data_dir: Path to the data directory (defaults to get_data_dir()).
        deep: When True, run the full per-row content hash (~24s on whole-Bible
            data). When False (default), run fast structural checks (schema
            shape + row counts) only — suitable for interactive per-request UI
            verification. The deep hash is the authoritative CI/manual gate.

    Returns:
        A tuple (is_valid, errors) where is_valid is True if all checks pass,
        and errors is a list of descriptive error strings.
    """
    root = (data_dir or get_data_dir()).resolve()
    errors: list[str] = []

    # --- Layer 1: content-level verification of SQLite DBs -------------------
    integrity_file = root / "INTEGRITY.json"
    if integrity_file.is_file():
        try:
            from search.validation.db_integrity import check_manifest

            is_ok, db_errors = check_manifest(
                bible_path=root / "bible.db",
                macula_path=root / "macula.db",
                manifest_path=integrity_file,
                deep=deep,
            )
            errors.extend(db_errors)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"Content integrity check errored: {exc}")
    else:
        # No content manifest: fall back to byte-level for the DBs (release
        # bundles predating INTEGRITY.json, or tests). This is the legacy
        # degraded path; the manifest is canonical going forward. Not an error
        # when SHA256SUMS covers the bundle.
        integrity_file = None

    # --- Layer 2: byte-level verification of JSON artifacts -------------------
    sums_file = root / "SHA256SUMS"
    if not sums_file.is_file():
        dist_sums = root.parent / "dist" / "data" / "SHA256SUMS"
        if dist_sums.is_file():
            sums_file = dist_sums
        else:
            errors.append(f"SHA256SUMS not found in data directory: {root}")
            return len(errors) == 0, errors

    lines = sums_file.read_text(encoding="utf-8").splitlines()
    checked_count = 0

    # SQLite DBs are verified by content in Layer 1 (if INTEGRITY.json exists);
    # skip their byte entries in SHA256SUMS to avoid duplicate/conflicting checks.
    content_checked_dbs = {
        "bible.db",
        "macula.db",
    } if integrity_file is not None else set()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            errors.append(f"Malformed line in SHA256SUMS: {line!r}")
            continue

        expected_sha256, raw_path = parts
        if len(expected_sha256) != 64 or not all(c in "0123456789abcdefABCDEF" for c in expected_sha256):
            errors.append(f"Malformed SHA-256 hash in SHA256SUMS: {expected_sha256!r}")
            continue

        # Strip coreutils binary indicator (*) and normalize path separators
        clean_rel = raw_path.lstrip("*").strip().replace("\\", "/")
        rel_obj = Path(clean_rel)

        # Skip SQLite DBs already verified by content integrity (Layer 1).
        if rel_obj.name in content_checked_dbs:
            checked_count += 1
            continue

        if rel_obj.is_absolute() or ".." in rel_obj.parts:
            errors.append(f"Invalid path traversal in SHA256SUMS: {raw_path!r}")
            continue

        file_path = root / rel_obj

        # Handle both root/lexicons/ and root/../lexicons/ layouts
        if not file_path.is_file() and (root.parent / rel_obj).is_file():
            file_path = root.parent / rel_obj

        if not file_path.is_file():
            errors.append(f"Missing bundle file: {clean_rel}")
            continue

        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_sha256 = h.hexdigest()

        if actual_sha256.lower() != expected_sha256.lower():
            errors.append(
                f"Checksum mismatch for {clean_rel}: expected {expected_sha256}, got {actual_sha256}"
            )
        else:
            checked_count += 1

    if checked_count == 0 and not errors:
        return False, ["SHA256SUMS contains no valid file entries"]

    return len(errors) == 0, errors
