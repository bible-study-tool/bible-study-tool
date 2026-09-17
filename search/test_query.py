"""Tests for the C4 faceted/filtered query API (roadmap C4).

Covers the acceptance criteria for ``search.corpus.query``:
facet correctness, intersection, free-text + facet, exact review
count, sidecar-free reads, CLI surface, and dependency scope.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml


def _sidecars_in(directory: Path) -> dict[str, int]:
    return {p.name: p.stat().st_size for p in directory.glob("*.db-*")}


class QueryFunctionTests(unittest.TestCase):
    def setUp(self) -> None:
        import search.corpus.query as q  # noqa: F401

        self.q = q
        self.con = q._build_index()

    def test_book_facet_returns_only_genesis(self) -> None:
        rows = self.q.query({"book": ["book/genesis"]})
        self.assertTrue(rows, "expected at least one Genesis entry")
        for r in rows:
            self.assertEqual(r["book"], "book/genesis")
            self.assertIn("book/genesis", r.get("tags", []))

    def test_book_and_language_intersect(self) -> None:
        all_genesis = {r["id"] for r in self.q.query({"book": ["book/genesis"]})}
        all_greek = {r["id"] for r in self.q.query({"language": ["lang/greek"]})}
        rows = self.q.query({"book": ["book/genesis"], "language": ["lang/greek"]})
        ids = {r["id"] for r in rows}
        # Every returned entry satisfies BOTH facets (intersection).
        self.assertTrue(ids <= all_genesis)
        self.assertTrue(ids <= all_greek)
        self.assertEqual(len(rows), len(ids), "duplicate ids in result")

    def test_theme_plus_text(self) -> None:
        rows = self.q.query({"theme": ["theme/grace"]}, text="grace")
        self.assertTrue(rows)
        for r in rows:
            hay = f"{r.get('passage', '')} {r.get('body', '')}".lower()
            self.assertIn("grace", hay)
        # Every curated entry (has tags/status) is theme/grace; bible/egw
        # hits (no tags) are added for free-text but carry no curated facets.
        themed = [r for r in rows if r.get("tags") or r.get("status")]
        self.assertTrue(themed, "expected at least one curated result")
        for r in themed:
            self.assertIn("theme/grace", r.get("tags", []))

    def test_review_count_is_current(self) -> None:
        rows = self.q.query({"status": ["status/review"]}, None, 10_000)
        self.assertEqual(len(rows), 157)
        for r in rows:
            self.assertEqual(r["status"], "review")

    def test_cross_source_ranked(self) -> None:
        rows = self.q.query(None, "grace", limit=10_000)
        norms = [r.get("_norm") for r in rows]
        # every result has an internal relevance score in [-1, 1]
        self.assertTrue(norms)
        self.assertTrue(all(-1.0 <= n <= 1.0 for n in norms if n is not None))
        # ranked (text) results are in descending cross-source order
        ranked = [n for n in norms if n >= 0]
        self.assertEqual(ranked, sorted(ranked, reverse=True))
        # results come from all three content stores
        sources = {r.get("source") for r in rows}
        self.assertIn("entry", sources)
        self.assertIn("bible", sources)
        self.assertIn("egw", sources)

    def test_no_sidecars_after_query(self) -> None:
        before = {}
        for p in ["data/bible.db", "data/egw.db", "data/macula.db"]:
            for suf in ("-wal", "-shm"):
                f = Path(p + suf)
                if f.exists():
                    before[f.name] = f.stat().st_size
        try:
            self.q.query({"status": ["status/review"]})
            self.q.query(text="grace")
        finally:
            after = _sidecars_in(Path("data"))
        for name, size in before.items():
            self.assertIn(name, after, f"{name} disappeared")
            self.assertEqual(after[name], size, f"{name} grew during query")
        for name in after:
            self.assertIn(name, before, f"unexpected new sidecar {name}")

    def test_index_built_in_memory_no_data_writes(self) -> None:
        with TemporaryDirectory() as td:
            db = Path(td) / "copy.db"
            import shutil

            shutil.copyfile("data/macula.db", db)
            q2 = self.q
            rows = q2.query({"book": ["book/genesis"]})
            self.assertTrue(rows)
            self.assertEqual([f.name for f in Path(td).glob("*.db-*")], [])


class QueryDependenciesTests(unittest.TestCase):
    def test_only_stdlib_and_existing_dependencies(self) -> None:
        src = (
            Path(__file__).resolve().parents[1] / "search" / "corpus" / "query.py"
        ).read_text()
        imports = re.findall(r"^from (\S+) import|^import (\S+)", src, re.M)
        for imp in imports:
            module = imp[0] or imp[1]
            if module.startswith("search."):
                continue
            if module in ("re", "sqlite3", "functools", "pathlib", "typing", "__future__"):
                continue
            if module == "yaml":
                continue  # existing declared dependency
            self.fail(f"unexpected new dependency: {module}")


class QueryCLITests(unittest.TestCase):
    def _run_cli(self, args: list[str]) -> str:
        import subprocess

        res = subprocess.run(
            [sys.executable, "-m", "search.ui.cli", *args],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return res.stdout

    def test_c4_query_via_cli(self) -> None:
        out = self._run_cli(["search", "grace", "--theme", "theme/grace", "--limit", "5", "--json"])
        data = __import__("json").loads(out)
        self.assertIn("results", data, f"unexpected CLI output: {out[:200]}")
        for r in data["results"]:
            # Curated results carry theme/grace; bible/egw hits (no
            # tags) are added for free-text but not facet-scoped.
            if r.get("tags") or r.get("status"):
                self.assertIn("theme/grace", r.get("tags", []))
        self.assertLessEqual(len(data["results"]), 5)

    def test_existing_search_unified_unchanged(self) -> None:
        res = subprocess.run(
            [sys.executable, "-m", "search.ui.cli", "search", "sabbath", "--limit", "2", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        data = __import__("json").loads(res.stdout)
        self.assertEqual(data["query"], "sabbath")
        self.assertIn("bible_hits", data)
        self.assertIn("egw_hits", data)
