"""Build the Macula Hebrew crosswalk and syntax knowledge artifact for Genesis.

Generates lexicons/macula-genesis.json from data/macula-hebrew/01-Gen-*-lowfat.xml.
The artifact provides:
  1. Strong's Hebrew ↔ LXX Greek Strong's crosswalk with frequency counts,
     Greek lemma equivalents, and SDBH semantic domains.
  2. Syntactic tree annotations per verse (clauses, constituents, participant roles).

Every output is deterministic, sorted, and pinned to a fixed GENERATION_DATE.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

from search.macula.extract import (
    VerseRecord,
    parse_book_directory,
)

GENERATION_DATE = "2026-09-04"
DEFAULT_MACULA_DIR = "data/macula-hebrew"
DEFAULT_OUT_FILE = "lexicons/macula-genesis.json"


def build_macula_genesis_artifact(
    macula_dir: str | Path = DEFAULT_MACULA_DIR,
    chapters: range | tuple[int, ...] = range(1, 51),
) -> dict:
    """Extract and compile Macula Hebrew data for Genesis into a structured dictionary."""
    verses: list[VerseRecord] = parse_book_directory(macula_dir, chapters=chapters)

    strongs_crosswalk: dict[str, dict] = {}
    verses_data: dict[str, dict] = {}

    total_clauses = 0
    total_tokens = 0

    for v in verses:
        v_dict = v.to_dict()
        verses_data[v.verse_id] = v_dict
        total_clauses += len(v.clauses)

        for cl in v.clauses:
            for const in cl.constituents:
                for tok in const.tokens:
                    total_tokens += 1
                    s_id = tok.strongs
                    if not s_id:
                        continue

                    entry = strongs_crosswalk.setdefault(
                        s_id,
                        {
                            "strongs": s_id,
                            "lemmas": set(),
                            "glosses": set(),
                            "sdbh": set(),
                            "core_domains": set(),
                            "lex_domains": set(),
                            "lxx": defaultdict(lambda: {"count": 0, "forms": set()}),
                            "count": 0,
                        },
                    )
                    entry["count"] += 1
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

    # Convert sets and defaultdicts to sorted lists for deterministic JSON output
    def _sort_strongs_key(k: str) -> int:
        return int(k[1:]) if len(k) > 1 and k[1:].isdigit() else 999999

    sorted_crosswalk: dict[str, dict] = {}
    for s_id in sorted(strongs_crosswalk.keys(), key=_sort_strongs_key):
        item = strongs_crosswalk[s_id]
        lxx_data: dict[str, dict] = {}
        for g_id in sorted(item["lxx"].keys(), key=_sort_strongs_key):
            g_rec = item["lxx"][g_id]
            lxx_data[g_id] = {
                "strongs": g_id,
                "greek": sorted(g_rec["forms"]),
                "count": g_rec["count"],
            }

        sorted_crosswalk[s_id] = {
            "strongs": s_id,
            "lemmas": sorted(item["lemmas"]),
            "glosses": sorted(item["glosses"]),
            "sdbh": sorted(item["sdbh"]),
            "core_domains": sorted(item["core_domains"]),
            "lex_domains": sorted(item["lex_domains"]),
            "lxx": lxx_data,
            "occurrences": item["count"],
        }

    return {
        "$schema": "macula-genesis/v1",
        "source": {
            "upstream": "https://github.com/Clear-Bible/macula-hebrew",
            "commit": "47db250bd55d0d8577f2a94fba114ef16c35b23c",
            "license": "CC BY 4.0",
            "attribution": "Clear-Bible Macula Hebrew project, based on Open Scriptures Hebrew Bible / WLC.",
        },
        "generation_date": GENERATION_DATE,
        "counts": {
            "chapters": len(chapters),
            "verses": len(verses),
            "clauses": total_clauses,
            "tokens": total_tokens,
            "strongs_crosswalk_entries": len(sorted_crosswalk),
        },
        "strongs_crosswalk": sorted_crosswalk,
        "verses": verses_data,
    }


def write_artifact(
    repo_root: str | Path = ".",
    macula_dir: str | Path | None = None,
    out_file: str | Path | None = None,
) -> Path:
    """Build and write lexicons/macula-genesis.json."""
    root = Path(repo_root)
    m_dir = root / (macula_dir or DEFAULT_MACULA_DIR)
    out_path = root / (out_file or DEFAULT_OUT_FILE)

    if not m_dir.exists():
        raise FileNotFoundError(
            f"Macula directory missing: {m_dir} — run scripts/fetch_sources.sh to download."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = build_macula_genesis_artifact(m_dir)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Macula Genesis artifact")
    parser.add_argument("--repo", default=".", help="Repository root path")
    parser.add_argument("--macula-dir", default=None, help="Directory with lowfat XMLs")
    parser.add_argument("--out", default=None, help="Output JSON path")
    args = parser.parse_args(argv)

    out = write_artifact(repo_root=args.repo, macula_dir=args.macula_dir, out_file=args.out)
    print(f"Generated {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
