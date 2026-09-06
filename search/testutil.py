"""Shared test utilities.

The deterministic test suite splits into two tiers:

1. **Offline-safe tests** — read only committed artifacts (lexicons/,
   correlations/, materials/, tags/) plus data/PROVENANCE.md. These run on a
   fresh clone and in CI (raw sources are gitignored).
2. **Raw-source-dependent tests** — regeneration tripwires, corpus fidelity
   vs data/KJV-osis.json, morphology vs data/oshb/Gen.xml, the agreement
   adapters. These require `data/` (fetched via scripts/fetch_sources.sh).

This mirrors scripts/verify_all.sh, which already skips raw-source checks
when `data/` is absent ("a fresh clone skips this step automatically, and the
committed artifacts are still verified by the checksum gate"). The committed
artifacts remain guarded offline by the PROVENANCE checksum gate
(search/corpus/test_morphology.py::ProvenanceChecksumGateTests).
"""

from __future__ import annotations

import unittest
from pathlib import Path

# The two files every raw-source-dependent test needs. fetch_sources.sh
# guarantees both exist together, so checking these two is sufficient.
_REQUIRED_RAW_SOURCES = ("data/KJV-osis.json", "data/oshb/Gen.xml")


def raw_sources_present(repo: str = ".") -> bool:
    """True when the gitignored raw sources are available locally."""
    return all((Path(repo) / p).exists() for p in _REQUIRED_RAW_SOURCES)


def require_raw_sources() -> unittest.skipUnless:
    """Skip decorator for tests that need the gitignored raw sources.

    Usage on a class or a method::

        @require_raw_sources()
        class RegenerationTripwireTests(unittest.TestCase):
            ...
    """
    return unittest.skipUnless(
        raw_sources_present(),
        "raw sources not present (data/ is gitignored; run "
        "scripts/fetch_sources.sh to enable this test)",
    )


_REPO_ROOT = Path(__file__).resolve().parent.parent


def ensure_test_databases(repo: str | Path | None = None) -> None:
    """Ensure minimal test SQLite databases exist in data/ for CI and clean clones.

    If data/bible.db, data/macula.db, and data/egw.db are already present (e.g. in
    local development after scripts/fetch_sources.sh), this function is a fast no-op.
    In headless CI environments where production databases are not present, this
    hydrates minimal test fixture databases so the full suite of UI, CLI, TUI,
    and analysis integration tests can run and pass offline without network access.
    """
    import gzip
    import json
    import sqlite3

    repo_path = _REPO_ROOT if repo is None or repo == "." else Path(repo).resolve()
    data_dir = repo_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    bible_db_path = data_dir / "bible.db"
    macula_db_path = data_dir / "macula.db"
    egw_db_path = data_dir / "egw.db"

    # Fast return if all 3 databases exist and have content
    if (
        bible_db_path.is_file() and bible_db_path.stat().st_size > 10_000
        and macula_db_path.is_file() and macula_db_path.stat().st_size > 10_000
        and egw_db_path.is_file() and egw_db_path.stat().st_size > 10_000
    ):
        return

    fixture_path = Path(__file__).resolve().parent / "fixtures" / "sample_test_data.json.gz"
    if not fixture_path.is_file():
        return

    with gzip.open(fixture_path, "rt", encoding="utf-8") as f:
        pkg = json.load(f)

    # 1. Hydrate Bible DB if missing or empty
    if not bible_db_path.is_file() or bible_db_path.stat().st_size < 10_000:
        from search.corpus.extract_kjv import BibleDB
        bdb = BibleDB(bible_db_path)
        bdb.init_db(force=True)
        try:
            with bdb.conn:
                bdb.conn.executemany(
                    "INSERT OR REPLACE INTO books VALUES (?, ?, ?, ?, ?, ?)",
                    ((b["osis"], b["order_num"], b["name"], b["testament"], b["chapters"], b["verses"]) for b in pkg["bible"]["books"]),
                )
                bdb.conn.executemany(
                    "INSERT OR REPLACE INTO verses VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ((v["id"], v["osis"], v["chapter"], v["verse"], v["text"], v["clean_text"], v["strongs_json"], v["tokens_json"]) for v in pkg["bible"]["verses"]),
                )
                bdb.conn.executemany(
                    "INSERT OR REPLACE INTO translations VALUES (?, ?, ?, ?, ?)",
                    ((t["id"], t["name"], t["year"], t["license"], t["is_default"]) for t in pkg["bible"]["translations"]),
                )
                bdb.conn.executemany(
                    "INSERT OR REPLACE INTO translation_verses VALUES (?, ?, ?, ?, ?, ?)",
                    ((tv["translation_id"], tv["verse_id"], tv["osis"], tv["chapter"], tv["verse"], tv["text"]) for tv in pkg["bible"]["translation_verses"]),
                )
        finally:
            bdb.close()

    # 2. Hydrate Macula DB if missing or empty
    if not macula_db_path.is_file() or macula_db_path.stat().st_size < 10_000:
        from search.macula.db import MaculaSqliteDB
        from search.macula.build_db import compile_macula_db

        mdb = MaculaSqliteDB(db_path=macula_db_path)
        mdb.init_db(force=True)
        mdb.close()

        gen_json = repo_path / "lexicons" / "macula-genesis.json"
        if gen_json.is_file():
            compile_macula_db(repo_root=repo_path, from_json=gen_json, out_db=macula_db_path)

        mconn = sqlite3.connect(str(macula_db_path))
        mg = pkg.get("macula_curated", pkg.get("macula_greek", {}))
        try:
            with mconn:
                if mg.get("verses"):
                    mconn.executemany(
                        "INSERT OR REPLACE INTO verses VALUES (?, ?, ?, ?, ?, ?)",
                        ((v["id"], v["book_code"], v["chapter"], v["verse"], v["mt_id"], v["text"]) for v in mg["verses"]),
                    )
                if mg.get("clauses"):
                    mconn.executemany(
                        "INSERT OR REPLACE INTO clauses VALUES (?, ?, ?, ?)",
                        ((cl["id"], cl["verse_id"], cl["clause_num"], cl["rule"]) for cl in mg["clauses"]),
                    )
                if mg.get("constituents"):
                    mconn.executemany(
                        "INSERT OR REPLACE INTO constituents VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        ((c["id"], c["clause_id"], c["verse_id"], c["constituent_num"], c["role"], c["role_label"], c["class"], c["text"]) for c in mg["constituents"]),
                    )
                if mg.get("tokens"):
                    mconn.executemany(
                        "INSERT OR REPLACE INTO tokens VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            (
                                tok["id"], tok["constituent_id"], tok["verse_id"], tok["token_num"], tok["text"],
                                tok["lemma"], tok["morph"], tok["pos"], tok["strongs"], tok["lxx"], tok["lxx_strongs"],
                                tok["sdbh"], tok["core_domains"], tok["lex_domains"], tok["gloss"],
                            )
                            for tok in mg["tokens"]
                        ),
                    )
                if mg.get("crosswalk"):
                    mconn.executemany(
                        "INSERT OR REPLACE INTO strongs_crosswalk VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            (
                                cw["strongs"], cw["lemmas_json"], cw["glosses_json"], cw["sdbh_json"],
                                cw["core_domains_json"], cw["lex_domains_json"], cw["lxx_json"], cw["occurrences"],
                            )
                            for cw in mg["crosswalk"]
                        ),
                    )
        finally:
            mconn.close()

    # 3. Hydrate Egw DB if missing or empty
    if not egw_db_path.is_file() or egw_db_path.stat().st_size < 10_000:
        from search.linking.egw import EgwDB
        edb = EgwDB(egw_db_path)
        edb.init_db(force=True)
        try:
            with edb.conn:
                paragraphs = pkg.get("egw", {}).get("paragraphs", [])
                if paragraphs:
                    edb.conn.executemany(
                        """
                        INSERT OR REPLACE INTO egw_paragraphs (id, book_code, book_title, chapter_num, chapter_title, page, paragraph, ref_code, text)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            (p["id"], p["book_code"], p["book_title"], p["chapter_num"], p["chapter_title"], p["page"], p["paragraph"], p["ref_code"], p["text"])
                            for p in paragraphs
                        ),
                    )
        finally:
            edb.close()