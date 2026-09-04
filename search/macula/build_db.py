"""Build script for compiling Macula linguistic data into data/macula.db (ADR-0014).

Compiles whole-Old-Testament syntactic, lexical, and Strong's crosswalk data
from Clear-Bible Macula Hebrew Lowfat XMLs (all 39 books, 929 chapters) or
from pre-compiled JSON artifacts (such as lexicons/macula-genesis.json).

Usage:
  python -m search.macula.build_db --repo .
  python -m search.macula.build_db --from-json lexicons/macula-genesis.json
  python -m search.macula.build_db --books Gen,Dan,Isa
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable

from search.macula.db import DEFAULT_MACULA_DB, MaculaSqliteDB
from search.macula.extract import (
    parse_all_chapters,
    parse_verse_id,
)


def _compile_from_xml_directory(
    db: MaculaSqliteDB,
    xml_dir: Path,
    books: Iterable[str] | None = None,
    batch_size: int = 500,
) -> None:
    """Stream-compile Lowfat XML chapters directly into SQLite with low memory."""
    # Prepare high-speed bulk build settings
    db.init_db(force=True, create_indices=False)
    db.conn.execute("PRAGMA synchronous = OFF;")
    db.conn.execute("PRAGMA journal_mode = MEMORY;")

    crosswalk_accum: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "lemmas": set(),
        "glosses": set(),
        "sdbh": set(),
        "core_domains": set(),
        "lex_domains": set(),
        "lxx": defaultdict(lambda: {"count": 0, "forms": set()}),
        "occurrences": 0,
    })

    verse_rows: list[tuple] = []
    clause_rows: list[tuple] = []
    const_rows: list[tuple] = []
    token_rows: list[tuple] = []

    def flush_batch() -> None:
        with db.conn:
            if verse_rows:
                db.conn.executemany(
                    "INSERT OR REPLACE INTO verses VALUES (?, ?, ?, ?, ?, ?);",
                    verse_rows,
                )
            if clause_rows:
                db.conn.executemany(
                    "INSERT OR REPLACE INTO clauses VALUES (?, ?, ?, ?);",
                    clause_rows,
                )
            if const_rows:
                db.conn.executemany(
                    "INSERT OR REPLACE INTO constituents VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                    const_rows,
                )
            if token_rows:
                db.conn.executemany(
                    "INSERT OR REPLACE INTO tokens VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                    token_rows,
                )
        verse_rows.clear()
        clause_rows.clear()
        const_rows.clear()
        token_rows.clear()

    v_count = 0
    for v in parse_all_chapters(xml_dir, books=books, canonical_versification=True):
        v_count += 1
        b_code, ch, vs = parse_verse_id(v.verse_id)
        verse_rows.append((v.verse_id, b_code, ch, vs, v.mt_id, v.text))

        for cl_idx, cl in enumerate(v.clauses, 1):
            cl_id = f"c:{v.verse_id}:{cl_idx}"
            clause_rows.append((cl_id, v.verse_id, cl_idx, cl.rule))

            for c_idx, const in enumerate(cl.constituents, 1):
                const_id = f"{cl_id}:{c_idx}"
                const_rows.append((
                    const_id,
                    cl_id,
                    v.verse_id,
                    c_idx,
                    const.role,
                    const.role_label,
                    const.phrase_class,
                    const.text,
                ))

                for t_idx, tok in enumerate(const.tokens, 1):
                    tok_id = f"{const_id}:{t_idx}"
                    token_rows.append((
                        tok_id,
                        const_id,
                        v.verse_id,
                        t_idx,
                        tok.text,
                        tok.lemma,
                        tok.morph,
                        tok.pos,
                        tok.strongs,
                        tok.lxx,
                        tok.lxx_strongs,
                        tok.sdbh,
                        json.dumps(tok.core_domains),
                        json.dumps(tok.lex_domains),
                        tok.gloss,
                    ))

                    s_id = tok.strongs
                    if s_id:
                        entry = crosswalk_accum[s_id]
                        entry["occurrences"] += 1
                        if tok.lemma:
                            entry["lemmas"].add(tok.lemma)
                        if tok.gloss:
                            entry["glosses"].add(tok.gloss)
                        if tok.sdbh:
                            entry["sdbh"].add(tok.sdbh)
                        for cd in tok.core_domains:
                            entry["core_domains"].add(cd)
                        for ld in tok.lex_domains:
                            entry["lex_domains"].add(ld)
                        if tok.lxx_strongs:
                            g_id = tok.lxx_strongs
                            entry["lxx"][g_id]["count"] += 1
                            if tok.lxx:
                                entry["lxx"][g_id]["forms"].add(tok.lxx)

        if len(verse_rows) >= batch_size:
            flush_batch()

    if v_count == 0:
        raise FileNotFoundError(f"No Lowfat XML chapter files found in {xml_dir}")

    flush_batch()

    # Insert accumulated Strong's crosswalk
    cw_rows = []
    for s_id, d in crosswalk_accum.items():
        lxx_dict = {
            g: {
                "strongs": g,
                "greek": sorted(list(data["forms"])),
                "count": data["count"],
            }
            for g, data in sorted(d["lxx"].items())
        }
        cw_rows.append((
            s_id,
            json.dumps(sorted(list(d["lemmas"]))),
            json.dumps(sorted(list(d["glosses"]))),
            json.dumps(sorted(list(d["sdbh"]))),
            json.dumps(sorted(list(d["core_domains"]))),
            json.dumps(sorted(list(d["lex_domains"]))),
            json.dumps(lxx_dict),
            d["occurrences"],
        ))

    with db.conn:
        db.conn.executemany(
            "INSERT OR REPLACE INTO strongs_crosswalk VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            cw_rows,
        )

    # Build post-insert B-Tree indices and restore standard WAL journaling
    db.create_indices()
    db.conn.execute("PRAGMA journal_mode = WAL;")
    db.conn.execute("PRAGMA synchronous = NORMAL;")
    db.conn.commit()


def compile_macula_db(
    repo_root: str | Path = ".",
    from_json: str | Path | None = None,
    xml_dir: str | Path | None = None,
    out_db: str | Path | None = None,
    books: Iterable[str] | None = None,
    batch_size: int = 500,
) -> Path:
    """Compile Macula SQLite database from Lowfat XML directory or prebuilt JSON."""
    root = Path(repo_root)
    db_path = root / (out_db or DEFAULT_MACULA_DB)

    start_time = time.time()
    db = MaculaSqliteDB(db_path=db_path)

    xml_target = root / (xml_dir or "data/macula-hebrew")

    if from_json:
        json_src = root / from_json
        if not json_src.is_file():
            raise FileNotFoundError(f"Specified JSON artifact not found: {json_src}")
        data = json.loads(json_src.read_text(encoding="utf-8"))
        verses = list(data.get("verses", {}).values())
        crosswalk = data.get("strongs_crosswalk", {})
        db.init_db(force=True)
        db.insert_verse_batch(verses, strongs_crosswalk=crosswalk)
    elif xml_target.is_dir() and any(xml_target.glob("*-lowfat.xml")):
        _compile_from_xml_directory(db, xml_target, books=books, batch_size=batch_size)
    else:
        default_json = root / "lexicons/macula-genesis.json"
        if default_json.is_file():
            data = json.loads(default_json.read_text(encoding="utf-8"))
        else:
            from search.macula.build_crosswalk import build_macula_genesis_artifact
            data = build_macula_genesis_artifact(root / "data" / "macula-hebrew")
        verses = list(data.get("verses", {}).values())
        crosswalk = data.get("strongs_crosswalk", {})
        db.init_db(force=True)
        db.insert_verse_batch(verses, strongs_crosswalk=crosswalk)

    elapsed = time.time() - start_time
    counts = db.counts
    print(f"Compiled {db_path} in {elapsed:.2f}s:")
    for k, v in counts.items():
        print(f"  - {k}: {v}")

    db.close()
    return db_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Macula SQLite database (ADR-0014).")
    parser.add_argument("--repo", default=".", help="Repository root path")
    parser.add_argument("--from-json", default=None, help="Path to macula JSON artifact to compile from")
    parser.add_argument("--xml-dir", default=None, help="Path to Macula Lowfat XML directory (default: data/macula-hebrew)")
    parser.add_argument("--books", default=None, help="Comma-separated book list to compile (e.g. Gen,Dan,Isa)")
    parser.add_argument("--out", default=None, help="Path to output SQLite database")
    args = parser.parse_args(argv)

    book_list = [b.strip() for b in args.books.split(",")] if args.books else None
    compile_macula_db(
        repo_root=args.repo,
        from_json=args.from_json,
        xml_dir=args.xml_dir,
        out_db=args.out,
        books=book_list,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
