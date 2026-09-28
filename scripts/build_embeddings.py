#!/usr/bin/env python3
"""Whole-Bible vector embeddings generation pipeline (WP-040, ADR-029).

Pre-computes 384-dimensional dense vectors for all 31,102 verses in data/bible.db
using the multilingual transformer multilingual-e5-small (via ONNX runtime or
fallback) and writes them into a compact, zero-cloud SQLite database:
    data/embeddings.db: verses(verse_id TEXT PRIMARY KEY, vector BLOB, magnitude REAL)

Usage:
    python scripts/build_embeddings.py
    python scripts/build_embeddings.py --limit 100 --output data/sample_embeddings.db
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import time

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from search.dbaccess import connect_db_reader
from search.linking.onnx_embedder import OnnxEmbedder
from search.linking.embedder import BaseEmbedder, CharNgramEmbedder
from search.resource import get_data_dir, get_embeddings_db_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate whole-Bible dense vector embeddings into SQLite."
    )
    parser.add_argument(
        "--bible",
        type=Path,
        default=get_data_dir() / "bible.db",
        help="Path to source bible.db",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=get_embeddings_db_path(),
        help="Path to output embeddings.db",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size for embedding inference (default: 64)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of verses to embed (for testing)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require ONNX model weights; do not fall back to n-gram hashing",
    )
    return parser.parse_args()


def load_verses(
    bible_path: Path,
    limit: int | None = None,
) -> list[tuple[str, str, int, int, str]]:
    """Load verses from bible.db joined with book names."""
    if not bible_path.is_file():
        raise FileNotFoundError(f"Source database not found: {bible_path}")

    conn = connect_db_reader(bible_path)
    cur = conn.cursor()
    query = """
        SELECT v.id, b.name, v.chapter, v.verse, v.clean_text
        FROM verses v
        JOIN books b ON v.osis = b.osis
        ORDER BY b.order_num, v.chapter, v.verse
    """
    if limit is not None:
        query += f" LIMIT {int(limit)}"

    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    return rows


def build_embeddings_db(
    bible_path: Path,
    output_path: Path,
    batch_size: int = 64,
    limit: int | None = None,
    strict: bool = False,
) -> Path:
    """Generate dense embeddings and write to output SQLite database."""
    print(f"Loading verses from {bible_path} ...")
    verses = load_verses(bible_path, limit=limit)
    total = len(verses)
    print(f"Loaded {total:,} verses to embed.")

    embedder: BaseEmbedder = OnnxEmbedder(strict=strict)
    if not embedder.available():
        if strict:
            raise RuntimeError("OnnxEmbedder weights or runtime not available in strict mode.")
        print("Notice: ONNX model weights not found. Falling back to CharNgramEmbedder.")
        embedder = CharNgramEmbedder(dim=384)
    else:
        print(f"Using neural embedder: {embedder.name} (dim={embedder.dim})")

    # Format passage strings
    passage_texts: list[str] = []
    verse_ids: list[str] = []
    for vid, bname, chap, vnum, text in verses:
        verse_ids.append(vid)
        passage_texts.append(f"passage: {bname} {chap}:{vnum} {text}")

    print(f"Embedding {total:,} passages (batch_size={batch_size}) ...")
    t0 = time.perf_counter()

    if isinstance(embedder, OnnxEmbedder) and embedder.available():
        vectors = embedder.embed_batch(passage_texts, is_query=False, batch_size=batch_size)
    else:
        # Fallback embedder
        vectors = np.stack([embedder.embed(p) for p in passage_texts]).astype(np.float32)

    elapsed = time.perf_counter() - t0
    rate = total / max(elapsed, 0.001)
    print(f"Inference completed in {elapsed:.2f}s ({rate:.1f} verses/sec).")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    print(f"Writing database to {output_path} ...")
    out_conn = sqlite3.connect(output_path)
    out_cur = out_conn.cursor()

    out_cur.execute("PRAGMA journal_mode = OFF")
    out_cur.execute("PRAGMA synchronous = OFF")

    out_cur.execute("""
        CREATE TABLE verses (
            verse_id TEXT PRIMARY KEY,
            vector BLOB NOT NULL,
            magnitude REAL NOT NULL
        )
    """)

    out_cur.execute("""
        CREATE TABLE meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    rows_to_insert = []
    for i, vid in enumerate(verse_ids):
        vec = vectors[i]
        mag = float(np.linalg.norm(vec))
        rows_to_insert.append((vid, vec.tobytes(), mag))

    out_cur.executemany(
        "INSERT INTO verses (verse_id, vector, magnitude) VALUES (?, ?, ?)",
        rows_to_insert,
    )

    meta_entries = [
        ("model", getattr(embedder, "model_name", getattr(embedder, "name", "unknown"))),
        ("dimension", str(embedder.dim)),
        ("total_verses", str(total)),
        ("normalized", "true"),
        ("created_at", datetime.now(timezone.utc).isoformat()),
    ]
    out_cur.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta_entries)

    out_conn.commit()
    out_cur.execute("VACUUM")
    out_conn.close()

    # Calculate SHA-256
    hasher = hashlib.sha256()
    with open(output_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    digest = hasher.hexdigest()

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Done! {output_path} created ({size_mb:.2f} MB, {total:,} verses).")
    print(f"SHA-256: {digest}")
    return output_path


def main() -> int:
    args = parse_args()
    build_embeddings_db(
        bible_path=args.bible,
        output_path=args.output,
        batch_size=args.batch_size,
        limit=args.limit,
        strict=args.strict,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
