"""Content-level integrity verification for SQLite data bundles (Option B, ADR-027).

Why content-level, not byte-level:
    SQLite database files are NOT byte-reproducible across toolchains. The same
    logical content yields different bytes under different SQLite versions,
    page sizes, VACUUM runs, or insertion orders. Byte-pinning a .db file in a
    committed manifest therefore fails on every machine that did not build it
    byte-identically — a false alarm, not a real integrity signal.

    JSON artifacts (lexicons, schemas) ARE byte-reproducible and remain
    byte-pinned in data/SHA256SUMS.

    This module pins the *content* of each SQLite database instead: a
    deterministic canonical projection of the data (table schemas + every row,
    ordered and serialized canonically) hashed with SHA-256. Identical content
    -> identical hash, on every machine and toolchain. Tampered or corrupted
    data -> different hash, detected.

Canonical projection (deterministic by construction):
    - Tables enumerated in fixed order (schema-ordered: dependency order).
    - Each row serialized as comma-separated canonicalized cell values (CSV)
      with values rendered deterministically (None → "null", ints/floats
      normalized, bytes → base64, booleans → 0/1).
    - Rows ordered by the table's declared primary key (or all columns if no PK).
    - Nulls, ints, text, and JSON blobs round-trip losslessly.

Usage:
    python -m search.validation.db_integrity --generate   # emit data/INTEGRITY.json
    python -m search.validation.db_integrity --check      # verify local DBs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable

from search.dbaccess import connect_db_reader

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "bible.db"
DEFAULT_MACULA_PATH = REPO_ROOT / "data" / "macula.db"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "data" / "INTEGRITY.json"

# Canonical content tables, in schema/dependency order. FTS shadow tables and
# any internal sqlite_* tables are deliberately EXCLUDED: they are derived
# indexes whose bytes vary by FTS build, not source content.
CANONICAL_TABLES = {
    "bible.db": [
        "books",
        "translations",
        "verses",
        "translation_verses",
        "cross_references",
    ],
    "macula.db": [
        "verses",
        "clauses",
        "constituents",
        "tokens",
        "strongs_crosswalk",
    ],
}


def _table_column_names(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return column names in schema order."""
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if not cols:
        raise ValueError(f"Table {table!r} does not exist or has no schema.")
    return [c[1] for c in cols]


def _table_primary_key(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return the primary key column names (empty if none declared)."""
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    pk_cols = [c[1] for c in cols if c[5] > 0]
    # PRAGMA returns pk column order already; sort by pk position for stability.
    return [c[1] for c in sorted((c for c in cols if c[5] > 0), key=lambda c: c[5])]


def _canonicalize_value(value: Any) -> str:
    """Serialize a single cell losslessly and deterministically.

    JSON strings/ints/floats/None round-trip exactly. bytes are base64-encoded
    (sqlite3 may return bytes for BLOB columns). Booleans normalize to ints.
    """
    if isinstance(value, bytes):
        import base64

        return f'"{base64.b64encode(value).decode("ascii")}"'
    if isinstance(value, bool):
        return "1" if value else "0"
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


_FTS5_SHADOW_SUFFIXES = ("_data", "_idx", "_docsize", "_config", "_content")


def _schema_census(
    conn: sqlite3.Connection, expected_tables: list[str]
) -> tuple[list[str], str]:
    """Validate the database shape and produce a canonical schema census.

    FTS shadow tables are derived from the actual `CREATE VIRTUAL TABLE ... USING
    fts5` entries in sqlite_master (never guessed from name suffixes), so a table
    merely *named* like a shadow is correctly treated as real (and rejected if it
    is not canonical). Views and triggers are rejected outright — they are not
    part of the canonical data model.

    Returns (errors, census_string) where errors is empty iff the shape is valid.
    """
    rows = conn.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()

    tables: dict[str, str | None] = {}
    views: dict[str, str | None] = {}
    triggers: dict[str, str | None] = {}
    indexes: dict[str, str | None] = {}
    virtual_tables: set[str] = set()

    for typ, name, sql in rows:
        if typ == "table":
            tables[name] = sql
            if sql and sql.strip().upper().startswith("CREATE VIRTUAL TABLE"):
                virtual_tables.add(name)
        elif typ == "view":
            views[name] = sql
        elif typ == "trigger":
            triggers[name] = sql
        elif typ == "index":
            indexes[name] = sql

    # FTS virtual tables AND their shadow tables are derived indexes, not
    # canonical content. Both are excluded from the real-table check.
    fts_derived: set[str] = set(virtual_tables)
    for v in virtual_tables:
        for suffix in _FTS5_SHADOW_SUFFIXES:
            if v + suffix in tables:
                fts_derived.add(v + suffix)

    real_tables = set(tables) - fts_derived

    # FTS-maintenance triggers (AFTER INSERT/DELETE/UPDATE on a canonical table
    # that writes into an FTS virtual table) are derived machinery, not content.
    # They are identified structurally (the trigger body references a virtual
    # table), never by name alone. The match is word-bounded so a virtual table
    # named e.g. `bible_fts` cannot be confused with a different object
    # `bible_fts_extra`.
    fts_trigger_names: set[str] = set()
    if virtual_tables and triggers:
        # Match against trig_sql.upper(), so the pattern must be built from
        # UPPERCASED virtual-table names (a trigger writes e.g.
        # `INSERT INTO bible_fts(...)`).
        fts_ref_pattern = re.compile(
            r"\b(" + "|".join(re.escape(v.upper()) for v in sorted(virtual_tables)) + r")\b"
        )
        for trig_name, trig_sql in triggers.items():
            if trig_sql is not None and fts_ref_pattern.search(trig_sql.upper()):
                fts_trigger_names.add(trig_name)

    errors: list[str] = []
    missing = [t for t in expected_tables if t not in real_tables]
    if missing:
        errors.append(f"Missing canonical tables: {', '.join(missing)}")
    extra = sorted(real_tables - set(expected_tables))
    if extra:
        errors.append(f"Unexpected tables present: {', '.join(extra)}")
    if views:
        errors.append(f"Unexpected views present: {', '.join(sorted(views))}")
    rogue_triggers = sorted(set(triggers) - fts_trigger_names)
    if rogue_triggers:
        errors.append(f"Unexpected triggers present: {', '.join(rogue_triggers)}")

    # Canonical schema census: table DDL (incl. virtual) + indexes + views + triggers.
    census: list[str] = []
    index_lines = [
        f"index:{name}:{sql or ''}"
        for name, sql in sorted(indexes.items())
    ]
    for t in expected_tables:
        census.append(f"table:{t}:{tables.get(t) or '<missing>'}")
    for v in sorted(virtual_tables):
        census.append(f"virtual:{v}:{tables.get(v) or ''}")
    census.extend(index_lines)
    for name in sorted(views):
        census.append(f"view:{name}:{views[name] or ''}")
    for name in sorted(triggers):
        census.append(f"trigger:{name}:{triggers[name] or ''}")
    census_str = "\n".join(census) + "\n"
    return errors, census_str


def _quote_ident(ident: str) -> str:
    """Quote a SQL identifier safely, doubling any embedded double-quotes."""
    return '"' + ident.replace('"', '""') + '"'


def compute_db_content_hash(db_path: str | Path, expected_tables: list[str]) -> str:
    """Compute the canonical content hash for a SQLite database."""
    db_path = Path(db_path)
    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = connect_db_reader(db_path)
    try:
        errors, census_str = _schema_census(conn, expected_tables)
        if errors:
            raise ValueError("; ".join(errors))

        h = hashlib.sha256()
        # NOTE: the filename is deliberately NOT hashed — content integrity must
        # hold regardless of the file's name or path (the manifest keys by name).
        # Full schema census first (reject unrecognized shapes), then row content.
        h.update(census_str.encode("utf-8"))
        for table in expected_tables:
            h.update(f"table:{table}\n".encode("utf-8"))
            cols = _table_column_names(conn, table)
            h.update(
                f"columns:{json.dumps(cols, ensure_ascii=False)}\n".encode("utf-8")
            )
            order_by = ", ".join(_table_primary_key(conn, table)) or ", ".join(cols)
            col_list = ", ".join(_quote_ident(c) for c in cols)
            sql = (
                f"SELECT {col_list} FROM {_quote_ident(table)} ORDER BY {order_by}"
            )
            for row in conn.execute(sql):
                h.update(
                    (",".join(_canonicalize_value(v) for v in row) + "\n").encode(
                        "utf-8"
                    )
                )
        return h.hexdigest()
    finally:
        conn.close()


def _shape_errors(db_path: str | Path, expected_tables: list[str]) -> list[str]:
    """Run only the (cheap) schema-shape gate. Returns error strings ([] == valid)."""
    conn = connect_db_reader(db_path)
    try:
        errors, _census = _schema_census(conn, expected_tables)
        return errors
    finally:
        conn.close()


def table_row_counts(db_path: str | Path, expected_tables: list[str]) -> dict[str, int]:
    """Return row counts for the canonical tables (fast integrity signal)."""
    conn = connect_db_reader(db_path)
    try:
        return {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in expected_tables}
    finally:
        conn.close()


def generate_manifest(
    bible_path: str | Path = DEFAULT_DB_PATH,
    macula_path: str | Path = DEFAULT_MACULA_PATH,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    """Generate the content-level integrity manifest for the data bundle."""
    bible_path = Path(bible_path)
    macula_path = Path(macula_path)
    manifest: dict[str, Any] = {
        "$schema": "data/integrity/v1",
        "generated_by": "search.validation.db_integrity",
        "description": (
            "Content-level SHA-256 hashes of SQLite data bundles. SQLite files are "
            "not byte-reproducible across toolchains; these hashes pin the logical "
            "content (schemas + every row, canonically serialized) so identical "
            "data verifies on any machine."
        ),
        "databases": {},
    }

    for db_name, path, tables in (
        ("bible.db", bible_path, CANONICAL_TABLES["bible.db"]),
        ("macula.db", macula_path, CANONICAL_TABLES["macula.db"]),
    ):
        if not Path(path).is_file():
            print(f"SKIP {db_name}: not found at {path}", file=sys.stderr)
            continue
        manifest["databases"][db_name] = {
            "content_sha256": compute_db_content_hash(path, tables),
            "row_counts": table_row_counts(path, tables),
            "canonical_tables": tables,
        }

    manifest_path = Path(manifest_path)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"✔ Content integrity manifest written: {manifest_path}")
    return manifest


def check_manifest(
    bible_path: str | Path = DEFAULT_DB_PATH,
    macula_path: str | Path = DEFAULT_MACULA_PATH,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    deep: bool = True,
) -> tuple[bool, list[str]]:
    """Verify local DBs against the content integrity manifest.

    Args:
        deep: When True (default), run the full canonical content hash over
            every row (~24s on whole-Bible data). When False, run the fast
            structural checks (schema shape + row counts) only — suitable for
            interactive per-request verification in the web UI.

    Returns (is_valid, errors). Any divergence (hash mismatch, shape change,
    row-count drift, missing DB) is an error.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        return False, [f"Integrity manifest not found: {manifest_path}"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    db_paths = {
        "bible.db": Path(bible_path),
        "macula.db": Path(macula_path),
    }
    for db_name, entry in manifest.get("databases", {}).items():
        path = db_paths.get(db_name)
        if path is None:
            errors.append(f"Manifest contains unknown database key: {db_name}")
            continue
        if not path.is_file():
            errors.append(f"Missing database: {db_name} ({path})")
            continue

        tables = entry.get("canonical_tables")
        if not isinstance(tables, list) or not tables:
            errors.append(
                f"Manifest entry for {db_name} is missing canonical_tables; manifest is malformed"
            )
            continue

        # Shape gate runs in BOTH modes: it is the fail-fast guard against
        # unrecognized/rogue schema objects, and it is cheap (one sqlite_master
        # query), so it must protect the interactive fast path too.
        try:
            shape_errors = _shape_errors(path, tables)
        except Exception as exc:
            errors.append(f"{db_name}: cannot validate schema shape: {exc}")
            continue
        errors.extend(shape_errors)

        if deep:
            try:
                actual = compute_db_content_hash(path, tables)
            except Exception as exc:
                errors.append(f"{db_name}: cannot compute content hash: {exc}")
                continue

            expected = entry.get("content_sha256")
            if not expected:
                errors.append(
                    f"Manifest entry for {db_name} has no content_sha256; manifest is malformed"
                )
                continue
            if actual != expected:
                errors.append(
                    f"Content mismatch for {db_name}: expected {expected}, got {actual}"
                )

        # Fast structural signal: row counts must match. A missing row_counts
        # block is itself a manifest defect (fast mode cannot verify anything),
        # not a silent pass.
        expected_counts = entry.get("row_counts")
        if expected_counts is None:
            errors.append(
                f"Manifest entry for {db_name} has no row_counts; manifest is malformed"
            )
            continue
        try:
            actual_counts = table_row_counts(path, tables)
        except Exception as exc:
            errors.append(f"{db_name}: cannot read row counts: {exc}")
            continue
        for table, expected_count in expected_counts.items():
            if actual_counts.get(table) != expected_count:
                errors.append(
                    f"Row count mismatch for {db_name}.{table}: "
                    f"expected {expected_count}, got {actual_counts.get(table)}"
                )

    if not manifest.get("databases"):
        errors.append("Manifest contains no database entries")
    return len(errors) == 0, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m search.validation.db_integrity",
        description="Content-level integrity verification for SQLite data bundles.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--generate", action="store_true", help="Generate data/INTEGRITY.json")
    group.add_argument("--check", action="store_true", help="Verify DBs against the manifest")
    parser.add_argument("--bible-db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--macula-db", default=str(DEFAULT_MACULA_PATH))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    args = parser.parse_args(argv)

    if args.generate:
        generate_manifest(args.bible_db, args.macula_db, args.manifest)
        return 0

    is_valid, errors = check_manifest(args.bible_db, args.macula_db, args.manifest)
    for err in errors:
        print(f"✘ {err}")
    if is_valid:
        print("✔ SQLite content integrity verified against manifest.")
        return 0
    print("FAILED: SQLite content integrity check.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())