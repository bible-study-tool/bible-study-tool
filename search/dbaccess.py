"""Sidecar-free read access to source SQLite databases (ADR-027).

The shipped data/*.db files are WAL-mode and fully checkpointed by the
builders (``journal_mode=WAL`` + ``wal_checkpoint(TRUNCATE)`` in
``scripts/build_release_data.sh``). Readers of those files must not open
them with ``mode=ro``: empirically that materializes ``-wal`` + ``-shm``
sidecars next to the file, and a WAL database with no existing ``-shm``
fails on first read under strict ``mode=ro``.

Strategy (``connect_db_reader``):

1. **No hot WAL** (the steady state, and the shipped files): open with
   ``mode=ro&immutable=1`` -- no locks, no sidecar creation.
2. **Hot WAL present** (uncheckpointed frames, e.g. an ingest in another
   process): ``immutable=1`` would ignore those frames and silently read
   stale content, so fall back to a normal WAL-aware connection -- which is
   also what any other reader would see. This matters for correctness, not
   just convenience: verification must hash what readers actually see.

Callers must only issue reads through the returned connection; this is
enforced with ``PRAGMA query_only = ON`` on both branches.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def _wal_has_frames(db_path: Path) -> bool:
    wal = db_path.with_name(db_path.name + "-wal")
    try:
        return wal.is_file() and wal.stat().st_size > 0
    except OSError:
        return False


def connect_db_reader(
    db_path: str | Path,
    *,
    row_factory: type | None = None,
    check_same_thread: bool = True,
) -> sqlite3.Connection:
    """Open a source SQLite database for reading, sidecar-free when possible."""
    path = Path(db_path).resolve()
    if _wal_has_frames(path):
        conn = sqlite3.connect(str(path), check_same_thread=check_same_thread)
    else:
        conn = sqlite3.connect(
            f"file:{path}?mode=ro&immutable=1",
            uri=True,
            check_same_thread=check_same_thread,
        )
    # Enforce the read-only contract on both branches: the WAL-aware fallback
    # is write-capable at the SQLite level, and source DBs must never be
    # mutated (Non-negotiable 3). Writes then raise ``SQLITE_READONLY``.
    conn.execute("PRAGMA query_only = ON;")
    if row_factory is not None:
        conn.row_factory = row_factory
    return conn