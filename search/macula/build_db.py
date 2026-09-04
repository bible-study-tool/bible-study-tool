"""Build script for compiling Macula linguistic data into data/macula.db (ADR-0014).

Usage:
  python -m search.macula.build_db --repo .
  python -m search.macula.build_db --from-json lexicons/macula-genesis.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from search.macula.db import DEFAULT_MACULA_DB, MaculaSqliteDB


def compile_macula_db(
    repo_root: str | Path = ".",
    from_json: str | Path | None = None,
    out_db: str | Path | None = None,
) -> Path:
    root = Path(repo_root)
    db_path = root / (out_db or DEFAULT_MACULA_DB)

    start_time = time.time()
    db = MaculaSqliteDB(db_path=db_path)
    db.init_db(force=True)

    if from_json:
        json_src = root / from_json
        if not json_src.is_file():
            raise FileNotFoundError(f"Specified JSON artifact not found: {json_src}")
        data = json.loads(json_src.read_text(encoding="utf-8"))
    else:
        default_json = root / "lexicons/macula-genesis.json"
        if default_json.is_file():
            data = json.loads(default_json.read_text(encoding="utf-8"))
        else:
            from search.macula.build_crosswalk import build_macula_genesis_artifact
            data = build_macula_genesis_artifact(root / "data" / "macula-hebrew")

    verses = list(data.get("verses", {}).values())
    crosswalk = data.get("strongs_crosswalk", {})
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
    parser.add_argument("--out", default=None, help="Path to output SQLite database")
    args = parser.parse_args(argv)

    compile_macula_db(repo_root=args.repo, from_json=args.from_json, out_db=args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
