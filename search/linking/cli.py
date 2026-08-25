#!/usr/bin/env python3
"""CLI for the bible-study-tool semantic linking pipeline.

Runs both cooperating layers:

  (b) deterministic concordance   -> index/concordance.json
  (c) multilingual discovery      -> correlations/ai-discovered-links.json

Example:
  python search/linking/cli.py --repo . --deterministic
  python search/linking/cli.py --repo . --discover --top-k 5
  python search/linking/cli.py --repo . --all
"""

from __future__ import annotations

import argparse
import json
import sys


def _load(repo: str):
    from .loader import Loader

    loader = Loader(repo)
    n = len(loader.load_entries())
    if n == 0:
        print("No entries loaded. Check --repo / materials layout.", file=sys.stderr)
    else:
        print(f"Loaded {n} entries")
    return loader


def _db(repo: str, db_path: str, force: bool):
    """Build the SQLite index from Markdown (authoritative), then return SemanticDB."""
    from .dbindex import SemanticDB, build_index

    if force or not db_path or not __import__("pathlib").Path(db_path).exists():
        build_index(repo=repo, db_path=db_path)
    return SemanticDB(repo_root=repo, db_path=db_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bible Study Tool semantic linking pipeline")
    parser.add_argument("--repo", default=".", help="Path to the knowledge base repo")
    parser.add_argument("--db", default="index/semantic.db", help="Path to the SQLite index (generated artifact)")
    parser.add_argument("--rebuild-db", action="store_true", help="Force rebuild of the SQLite index")
    parser.add_argument("--deterministic", action="store_true", help="(b) build deterministic concordance")
    parser.add_argument("--discover", action="store_true", help="(c) discover multilingual semantic candidates")
    parser.add_argument("--all", action="store_true", help="Run both layers")
    parser.add_argument("--top-k", type=int, default=5, help="Max candidates to keep")
    parser.add_argument(
        "--min-sim",
        type=float,
        default=None,
        help="Minimum similarity for a candidate to pass the gate "
        "(default: 0.82 transformer space / 0.70 deterministic space)",
    )
    parser.add_argument("--seed", action="store_true", help="Print discovered candidates to stdout (JSON)")
    args = parser.parse_args(argv)

    if not (args.all or args.deterministic or args.discover):
        parser.print_help()
        return 1

    loader = _load(args.repo)

    # Build/refresh the SQLite index once; layers query it (no rescan).
    if args.deterministic or args.all or args.discover:
        db = _db(args.repo, args.db, args.rebuild_db)
        print(f"[db] using index {args.db} ({db.count()} entries)")

    if args.deterministic or args.all:
        from .concordance import write_concordance

        data = write_concordance(loader, db=db)
        s = data["summary"]
        print(f"[b] concordance written: {s['roots']} roots, {len(data['links'])} links "
              f"(source: index={args.db})")

    if args.discover or args.all:
        from .candidates import write_candidates
        from .embedder import get_embedder

        embedder = get_embedder()
        min_sim = args.min_sim if args.min_sim is not None else (
            0.82 if embedder.name == "sentence-transformers" else 0.70
        )
        cands = write_candidates(
            loader, embedder=embedder, top_k=args.top_k, min_similarity=min_sim, db=db
        )
        label = "candidate" if len(cands) == 1 else "candidates"
        print(f"[c] {len(cands)} {label} written to correlations/ai-discovered-links.json "
              f"(pending human review; embedder={embedder.name}, min_sim={min_sim})")
        if args.seed:
            print(json.dumps(cands, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
