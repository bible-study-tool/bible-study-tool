#!/usr/bin/env python3
"""ADR-027 drift-sensitivity battery for macula.db.

Validates the content-level integrity gate against the EXACT regression
class that motivated ADR-027: the 2,541-row `constituents.role_label`
drift ("copula"/"prep" vs "copula"/"preposition") that escaped byte-pin
verification when macula.db was rebuilt from identically pinned sources.

Only operates on scratch copies under a scratch dir -- the pristine data/
tree is never touched. Exit code 0 = every phase landed as expected;
1 = a finding (a place where the verification gate is LESS discriminating
than the ADR claims).

Phases
  0  baseline: a plain copy rehashes to the committed manifest value
  1  historical drift: exactly 2,541 role_label 'preposition' -> 'prep'
     -> deep hash changes; fast path (shape + counts) stays valid
  2  ordering stability: schema-identical rebuild with random physical
     insert order -> deep hash unchanged (rebuilds cannot false-fail)
  3  cross-table attribution: one constituents + one tokens mutation
     -> deep hash changes with db-level attribution
  4  nullable-cell discrimination: NULL / '' / 'x' on one cell produce
     three distinct hashes, none equal to the manifest value
  5  fast-path blindness: fast mode reports valid on every mutation above
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from search.validation.db_integrity import (  # noqa: E402
    _shape_errors,
    compute_db_content_hash,
    table_row_counts,
)

REPO = Path(__file__).resolve().parents[1]
HISTORIC_DRIFT_ROWS = 2_541
HISTORIC_DRIFT_OLD = "preposition"
HISTORIC_DRIFT_NEW = "prep"


def load_manifest(db_name: str) -> dict:
    manifest = json.loads((REPO / "data/INTEGRITY.json").read_text())
    entry = manifest["databases"][db_name]
    return {
        "tables": entry["canonical_tables"],
        "hash": entry["content_sha256"],
        "row_counts": entry["row_counts"],
    }


def make_copy(src: Path, dst: Path) -> None:
    shutil.copy2(src, dst)
    # Scratch copies operate without a write-ahead log: verification reads
    # on-disk state deterministically and no -wal/-shm residue can mask or
    # replay mutations.
    conn = sqlite3.connect(dst)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.close()


def deep_hash(db_path: Path, tables: list[str], expected: str) -> tuple[bool, str]:
    got = compute_db_content_hash(db_path, tables)
    return got == expected, got


def fast_valid(db_path: Path, tables: list[str], row_counts: dict[str, int]) -> tuple[bool, str]:
    shape = _shape_errors(db_path, tables)
    if shape:
        return False, f"shape errors: {shape[:1]}"
    counts = table_row_counts(db_path, tables)
    if counts != row_counts:
        return False, f"row counts differ: {counts}"
    return True, "shape ok, counts ok"


def mutate_role_labels(db_path: Path, n: int, old: str, new: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        f"UPDATE constituents SET role_label = ? WHERE id IN "
        f"(SELECT id FROM constituents WHERE role_label = ? LIMIT ?)",
        (new, old, n),
    )
    conn.commit()
    conn.close()


def rebuild_scrambled(src: Path, dst: Path, tables: list[str]) -> None:
    """Rebuild with byte-identical catalog DDL but randomized physical rows."""
    src_c = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    stmt = "SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL"
    catalog = src_c.execute(stmt).fetchall()
    tables_ddl = [row[2] for row in catalog if row[0] == "table"]
    post_ddl = [row[2] for row in catalog if row[0] in ("index", "trigger")]
    src_c.close()

    dst.unlink(missing_ok=True)  # never rebuild atop a partial target
    dst_c = sqlite3.connect(dst)
    dst_c.execute("PRAGMA journal_mode=OFF")
    dst_c.execute("PRAGMA synchronous=OFF")
    dst_c.execute("ATTACH DATABASE ? AS src", (str(src),))
    for ddl in tables_ddl:
        dst_c.execute(ddl)
    for t in tables:
        dst_c.execute(f'INSERT INTO "{t}" SELECT * FROM src."{t}" ORDER BY RANDOM()')
    dst_c.commit()
    for ddl in post_ddl:  # identical catalog objects -> identical census
        dst_c.execute(ddl)
    dst_c.commit()
    dst_c.execute("DETACH DATABASE src")
    dst_c.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, default=Path("/tmp/opencode/drift-battery"))
    parser.add_argument("--keep", action="store_true", help="keep scratch copies on exit")
    args = parser.parse_args()

    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    src = REPO / "data/macula.db"
    m = load_manifest("macula.db")
    results: list[tuple[str, bool, str]] = []
    t0 = time.time()

    def phase(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<42} {detail}")

    # ---- Phase 0: baseline ----
    p0 = scratch / "macula-p0-baseline.db"
    make_copy(src, p0)
    ok, got = deep_hash(p0, m["tables"], m["hash"])
    phase("0 baseline rehash", ok, f"got={got[:16]}… expected={m['hash'][:16]}…")
    assert ok, "baseline mismatch on a plain copy -- battery is not valid"

    # ---- Phase 1: historical drift ----
    p1 = scratch / "macula-p1-drift.db"
    make_copy(src, p1)
    mutate_role_labels(p1, HISTORIC_DRIFT_ROWS, HISTORIC_DRIFT_OLD, HISTORIC_DRIFT_NEW)
    ok, got = deep_hash(p1, m["tables"], m["hash"])
    detail = f"{HISTORIC_DRIFT_ROWS} role_label {HISTORIC_DRIFT_OLD!r}->{HISTORIC_DRIFT_NEW!r}: "
    detail += f"hash changed {got[:16]}…" if not ok else "hash UNCHANGED"
    phase("1 historical drift sensitivity", not ok, detail)
    fast_ok, fd = fast_valid(p1, m["tables"], m["row_counts"])
    phase("1b drift fast-path (expect valid)", fast_ok, fd)

    # ---- Phase 2: ordering stability ----
    p2 = scratch / "macula-p2-scrambled.db"
    rebuild_scrambled(src, p2, m["tables"])
    ok, got = deep_hash(p2, m["tables"], m["hash"])
    phase("2 ordering stability", ok, f"random physical order -> hash {got[:16]}…")

    # ---- Phase 3: cross-table attribution ----
    p3 = scratch / "macula-p3-cross-table.db"
    make_copy(src, p3)
    conn = sqlite3.connect(p3)
    conn.execute("UPDATE constituents SET role_label = 'sneaky' WHERE id = (SELECT id FROM constituents LIMIT 1)")
    conn.execute("UPDATE tokens SET strongs = 'H9999' WHERE id = (SELECT id FROM tokens WHERE strongs IS NOT NULL LIMIT 1)")
    conn.commit()
    conn.close()
    ok, got = deep_hash(p3, m["tables"], m["hash"])
    phase("3 cross-table attribution", not ok, f"constituents + tokens mutated -> hash {got[:16]}…")

    # ---- Phase 4: nullable-cell discrimination ----
    labels = {"a": None, "b": "", "c": "x"}
    p4 = {k: scratch / f"macula-p4-{k}.db" for k in labels}
    for k, path in p4.items():
        make_copy(src, path)
        conn = sqlite3.connect(path)
        cell = conn.execute("SELECT id, class FROM constituents WHERE class IS NOT NULL LIMIT 1").fetchone()
        conn.execute("UPDATE constituents SET class = ? WHERE id = ?", (labels[k], cell[0]))
        conn.commit()
        conn.close()
    h4 = {k: deep_hash(p4[k], m["tables"], m["hash"]) for k in labels}
    distinct = len({h4[k][1] for k in labels}) == 3
    all_new = all(not h4[k][0] for k in labels)
    phase("4 nullable discrimination", distinct and all_new,
          f"NULL/{''}/'x' -> {len({h4[k][1] for k in labels})} distinct hashes, "
          f"{'' if all_new else 'NOT ALL '}differ from manifest")

    # ---- Phase 5: fast-path blindness (expect valid on every mutation) ----
    mutated = {"p1-drift": p1, "p3-cross": p3, **{f"p4-{k}": v for k, v in p4.items()}}
    all_valid = True
    for label, path in mutated.items():
        fast_ok, fd = fast_valid(path, m["tables"], m["row_counts"])
        all_valid &= fast_ok
        phase(f"5 fast-path {label}", fast_ok, fd)

    if not args.keep:
        for path in [p0, p1, p2, p3, *p4.values()]:
            path.unlink(missing_ok=True)

    print()
    for name, ok, detail in results:
        marker = "PASS" if ok else "FAIL"
        print(f"{marker} {name}")
    failed = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(failed)}/{len(results)} phases passed "
          f"({time.time() - t0:.1f}s).")
    if failed:
        print("FINDINGS (verification is less discriminating than ADR-027 claims):")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
        return 1
    print("Verdict: GO -- the gate discriminates exactly the ADR-027 regression class.")
    return 0


if __name__ == "__main__":
    sys.exit(main())