#!/usr/bin/env python3
"""Canonical session briefing — ground truth, not memory.

Usage:  python scripts/status.py

A new session (or a returning one) runs this FIRST. It assembles the
project's state from reality — git, ROADMAP, PROVENANCE, the work packages,
and the test inventory — so decisions are made from artifacts, not from a
model's recollection.

This is a developer tool, not part of the tested pipeline: its failure mode
is cosmetic (a stale or missing section), never data corruption, so it has no
formal test.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=ROOT, check=True
    )
    return out.stdout.strip()


def roadmap_progress() -> list[tuple[str, int, int, str]]:
    """Per-pillar (done, total) checkbox counts + first open item."""
    text = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    pillar = None
    counts: dict[str, list[int]] = {}
    first_open: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^### ([A-Z])\. (.+)$", line)
        if m:
            pillar = f"{m.group(1)} — {m.group(2).split('*')[0].strip()}"
            counts.setdefault(pillar, [0, 0])
            continue
        if pillar is None:
            continue
        if line.startswith("- `[x]`"):
            counts[pillar][0] += 1
            counts[pillar][1] += 1
        elif line.startswith(("- `[~]`", "- `[ ]`")):
            counts[pillar][1] += 1
            first_open.setdefault(pillar, line[7:].strip()[:72])
    return [(k, v[0], v[1], first_open.get(k, "")) for k, v in counts.items()]


def provenance_artifacts() -> list[str]:
    text = (ROOT / "data/PROVENANCE.md").read_text(encoding="utf-8")
    return re.findall(r"^[0-9a-f]{64}  \.\./(\S+)$", text, re.MULTILINE)


def work_packages() -> list[tuple[str, str, str]]:
    out = []
    wp_dir = ROOT / "docs/wp"
    if not wp_dir.exists():
        return out
    for p in sorted(wp_dir.glob("WP-*.md")):
        text = p.read_text(encoding="utf-8")
        status = next(
            (l.split(":", 1)[1].strip() for l in text.splitlines()
             if l.lower().startswith("status:")),
            "unknown",
        )
        title = next(
            (l.lstrip("# ").strip() for l in text.splitlines() if l.startswith("# ")),
            p.stem,
        )
        out.append((p.name, status, title))
    return out


def curation_frontier() -> dict:
    """Scan materials/bible/ and return curation status metrics.

    Returns a dict with keys:
        total, approved, review, draft, pending_scaffolding,
        by_book (dict: book_key -> {approved, review, draft}),
        velocity_7d, velocity_30d (entries promoted to approved in last N days),
        next_chapter (first chapter with review entries, for focus recommendation).
    """
    materials_dir = ROOT / "materials" / "bible"
    if not materials_dir.is_dir():
        return {"error": f"materials/bible/ not found at {materials_dir}"}

    _STATUS_RE = re.compile(r"^status:\s*(\S+)", re.MULTILINE)
    _UPDATED_RE = re.compile(r"^updated:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
    _BOOK_RE = re.compile(r"^book:\s*(\S+)", re.MULTILINE)
    _PASSAGE_RE = re.compile(r"^passage:\s*\"?([^\"]+)\"?", re.MULTILINE)

    totals: dict[str, int] = defaultdict(int)
    by_book: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    velocity_7d = 0
    velocity_30d = 0
    today = date.today()
    cutoff_7 = today - timedelta(days=7)
    cutoff_30 = today - timedelta(days=30)
    next_review_chapter: str | None = None

    for md_path in sorted(materials_dir.rglob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        sm = _STATUS_RE.search(raw)
        if not sm:
            totals["pending_scaffolding"] += 1
            continue

        status = sm.group(1).strip().lower()
        # Normalise legacy "final" → treat as approved for counting
        if status == "final":
            status = "approved"

        bm = _BOOK_RE.search(raw)
        book_key = bm.group(1).strip() if bm else "unknown"

        totals[status] += 1
        totals["total"] += 1
        by_book[book_key][status] += 1

        if status == "approved":
            um = _UPDATED_RE.search(raw)
            if um:
                try:
                    updated = date.fromisoformat(um.group(1))
                    if updated >= cutoff_7:
                        velocity_7d += 1
                    if updated >= cutoff_30:
                        velocity_30d += 1
                except ValueError:
                    pass

        if status == "review" and next_review_chapter is None:
            pm = _PASSAGE_RE.search(raw)
            if pm:
                passage = pm.group(1).strip()
                # Extract chapter from "Book Chapter:Verse"
                parts = passage.rsplit(":", 1)
                next_review_chapter = parts[0] if parts else passage

    return {
        "total": totals.get("total", 0),
        "approved": totals.get("approved", 0),
        "review": totals.get("review", 0),
        "draft": totals.get("draft", 0),
        "pending_scaffolding": totals.get("pending_scaffolding", 0),
        "by_book": {k: dict(v) for k, v in by_book.items()},
        "velocity_7d": velocity_7d,
        "velocity_30d": velocity_30d,
        "next_chapter": next_review_chapter,
    }


def test_count() -> str:
    import importlib.util

    py_exec = sys.executable
    venv_py = ROOT / ".venv/bin/python"
    if venv_py.is_file() and importlib.util.find_spec("pytest") is None:
        py_exec = str(venv_py)

    out = subprocess.run(
        [py_exec, "-m", "pytest", "--collect-only"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if out.returncode != 0:
        combined = out.stderr + out.stdout
        if "No module named" in combined:
            return "dependencies missing — run ./scripts/bootstrap.sh"
        return "pytest failed"
    m = re.search(r"(\d+)\s+(?:tests?\s+collected|passed)", out.stdout)
    if m:
        return f"{m.group(1)} tests collected"
    lines = [l for l in out.stdout.splitlines() if l.strip()]
    return lines[-1].strip(" =") if lines else "pytest: 0 tests collected"


def main() -> int:
    print("=" * 62)
    print("PROJECT BRIEFING — Adventist Bible Study Tool")
    print("=" * 62)

    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    head = _git("log", "-1", "--format=%h %s")
    dirty = _git("status", "--porcelain")
    print(f"\nbranch: {branch}")
    print(f"HEAD:   {head}")
    print(f"tree:   {'CLEAN' if not dirty else 'DIRTY — uncommitted changes:'}")
    if dirty:
        for line in dirty.splitlines():
            print(f"    {line}")

    print("\n--- last 5 commits ---")
    print(_git("log", "-5", "--oneline"))

    print("\n--- ROADMAP progress (done/total per pillar) ---")
    for name, done, total, first_open in roadmap_progress():
        print(f"  {name}: {done}/{total}")
        if first_open and done < total:
            print(f"      next: {first_open}")

    # --- Curation Frontier ---
    print("\n--- curation frontier ---")
    cf = curation_frontier()
    if "error" in cf:
        print(f"  {cf['error']}")
    else:
        total = cf["total"]
        approved = cf["approved"]
        review = cf["review"]
        draft = cf["draft"]
        pending = cf["pending_scaffolding"]
        pct_approved = f"{approved / total * 100:.1f}%" if total else "0.0%"
        pct_review = f"{review / total * 100:.1f}%" if total else "0.0%"
        print(f"  Total entries : {total}")
        print(f"  Approved      : {approved:>5}  ({pct_approved})")
        print(f"  In Review     : {review:>5}  ({pct_review})")
        print(f"  Draft         : {draft:>5}")
        print(f"  Unscaffolded  : {pending:>5}")
        print(f"  Velocity 7d   : {cf['velocity_7d']} entries promoted to approved")
        print(f"  Velocity 30d  : {cf['velocity_30d']} entries promoted to approved")
        if cf["next_chapter"]:
            print(f"  Next focus    : {cf['next_chapter']}  ← first chapter with review entries")
        # Book-level breakdown (only books with non-draft activity)
        active_books = {
            b: counts for b, counts in cf["by_book"].items()
            if counts.get("approved", 0) + counts.get("review", 0) > 0
        }
        if active_books:
            print("  Book progress (approved / review / draft):")
            for book_key, counts in sorted(active_books.items()):
                short = book_key.replace("book/", "")
                a = counts.get("approved", 0)
                r = counts.get("review", 0)
                d = counts.get("draft", 0)
                print(f"    {short:<22} approved={a}  review={r}  draft={d}")

    print("\n--- generated artifacts (PROVENANCE inventory) ---")
    for name in provenance_artifacts():
        print(f"  {name}")

    print("\n--- work packages ---")
    wps = work_packages()
    if not wps:
        print("  (none)")
    for name, status, title in wps:
        print(f"  {name} [{status}] {title}")

    print("\n--- tests ---")
    print(f"  {test_count()}")

    print("\n--- next actions ---")
    print("  1. Read ROADMAP.md for the current phase and the next open item.")
    print("  2. Pick an open work package in docs/wp/ (or create one).")
    print("  3. Work one step at a time; subagent-review each step; close with")
    print("     scripts/verify_all.sh (see docs/WORKFLOW.md for examples).")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())