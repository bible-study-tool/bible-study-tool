"""Comparison engine + Agreement Ledger generation (S2).

Consumes the fact index (search.agreement.facts) and emits
``correlations/agreement-ledger.json`` — the committed, byte-verified record
of what every pinned source says about every shared key, and where sources
agree or part ways.

## Status policy (approved: integrity-first)

  * ``agree``      — all comparable readings equal (objective equality).
  * ``disagree``   — comparable readings UNEQUAL — reserved for
                     objective-equality fact types only (``word_strongs``
                     multiset equality; ``verse_text`` exact string when a
                     second same-translation source exists). A disagreement
                     here is real signal: two independent sources read the
                     same fact differently.
  * ``info``       — gloss readings that do not normalize equal. Per the
                     approved policy, gloss PHRASING differences between an
                     1890 concordance and modern brief glosses are expected
                     nuance, not findings: the row carries the verbatim
                     side-by-side readings for study, and never auto-fails
                     review.
  * ``one-sided``  — fewer than two comparable readings present.
  * ``no_reading`` — every present reading is flagged no_definition (the
                     source has no comparable content for this key).

Facts are stored VERBATIM; ``normalize_gloss`` is used only for gloss status
computation, and each row also records the normalized form so the policy is
auditable. Nothing is ever auto-resolved.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from search.agreement.facts import (
    collect_all,
    index_facts,
    FACT_LEXICON_GLOSS,
    FACT_VERSE_TEXT,
    FACT_WORD_STRONGS,
)

# Lemma normalization for gloss status computation ONLY (values stay verbatim
# in the ledger). Deterministic: number-prefix strip -> parenthetical removal
# -> first ';' / ':' segment -> lowercase -> whitespace collapse.
_NUM_PREFIX_RE = re.compile(r"^\d+\.\s*")
_PARENS_RE = re.compile(r"\([^)]*\)")
_WS_RE = re.compile(r"\s+")


def normalize_gloss(value: str) -> str:
    out = _NUM_PREFIX_RE.sub("", value.strip())
    prev = None
    while prev != out:  # nested parentheticals, if any
        prev = out
        out = _PARENS_RE.sub("", out)
    for sep in (";", ":"):
        if sep in out:
            out = out.split(sep, 1)[0]
    return _WS_RE.sub(" ", out).lower().strip()


def _sort_key(key: str):
    """'Gen.1.4' -> (1, 4);  'H1254' -> ('H', 1254). Numeric within prefix."""
    parts = key.split(".")
    if len(parts) == 3 and parts[0] == "Gen":
        return (0, int(parts[1]), int(parts[2]))
    m = re.match(r"^([HG])(\d+)$", key)
    if m:
        return (1, m.group(1), int(m.group(2)))
    return (2, key)


def _row(key: str, status: str, readings: list[dict], note: str | None = None) -> dict:
    row = {"key": key, "status": status, "readings": readings}
    if note:
        row["note"] = note
    return row


def _compare_verse_text(key: str, readings: dict) -> dict:
    rows = [{"source": s, "value": f["value"]} for s, f in sorted(readings.items())]
    if len(rows) < 2:
        return _row(key, "one-sided", rows,
                    note="single source — cross-translation comparison arrives "
                         "with additional verse_text sources")
    values = {r["value"] for r in rows}
    return _row(key, "agree" if len(values) == 1 else "disagree", rows)


def _compare_word_strongs(key: str, readings: dict) -> dict:
    rows = [{"source": s, "value": f["value"]} for s, f in sorted(readings.items())]
    if len(rows) < 2:
        return _row(key, "one-sided", rows)
    # Defensive sort: multiset equality must not depend on the adapter
    # pre-sorting (a future adapter emitting document-order lists would
    # otherwise silently degrade this to list equality).
    values = {json.dumps(sorted(r["value"])) for r in rows}
    return _row(key, "agree" if len(values) == 1 else "disagree", rows)


def _compare_gloss(key: str, readings: dict) -> dict:
    rows = []
    for source, fact in sorted(readings.items()):
        status = fact.get("meta", {}).get("gloss_status", "definition")
        row = {"source": source, "value": fact["value"], "gloss_status": status}
        if status == "definition":
            row["normalized"] = normalize_gloss(fact["value"])
        rows.append(row)

    comparable = [r for r in rows if r["gloss_status"] == "definition"]
    if not comparable:
        return _row(key, "no_reading", rows,
                    note="source has no comparable definition for this key")
    if len(comparable) < 2:
        return _row(key, "one-sided", rows)
    normalized = {r["normalized"] for r in comparable}
    # Policy (a): gloss phrasing differences are 'info' (side-by-side
    # readings), never 'disagree'.
    status = "agree" if len(normalized) == 1 else "info"
    note = None
    if status == "agree" and any(":" in r["value"] or ";" in r["value"]
                                 for r in comparable):
        # Sense-truncation caveat: a multi-sense gloss truncated to its first
        # segment can match a single-sense reading (e.g. 'common: unsanctified'
        # vs 'common'). Verbatim readings remain side-by-side for review.
        note = "agree after sense truncation (first ';' / ':' segment)"
    return _row(key, status, rows, note=note)


_COMPARATORS = {
    FACT_VERSE_TEXT: _compare_verse_text,
    FACT_WORD_STRONGS: _compare_word_strongs,
    FACT_LEXICON_GLOSS: _compare_gloss,
}

# Per-type allowed statuses — the machine-checkable encoding of policy (a).
ALLOWED_STATUSES = {
    FACT_VERSE_TEXT: {"agree", "disagree", "one-sided"},
    FACT_WORD_STRONGS: {"agree", "disagree", "one-sided"},
    FACT_LEXICON_GLOSS: {"agree", "info", "one-sided", "no_reading"},
}

_SOURCES = {
    "kjv-osis": "scrollmapper tagged KJV (data/KJV-osis.json; MIT, KJV PD)",
    "oshb": "Open Scriptures Hebrew Bible v2.2 (data/oshb/; WLC PD, morphology CC BY 4.0)",
    "strongs": "Strong's lexicon artifact (lexicons/strongs-lexicon.json; PD)",
    "tbesh": "STEPBible TBESH (lexicons/tbesh-glosses.json; CC BY 4.0)",
    "tbesg": "STEPBible TBESG (lexicons/tbesg-glosses.json; CC BY 4.0)",
}


def build_ledger(repo: str = ".") -> dict:
    """Compare every fact key across sources and assemble the ledger."""
    idx = index_facts(collect_all(repo))

    sections: dict[str, list[dict]] = {}
    for fact_type, comparator in _COMPARATORS.items():
        rows = [comparator(key, readings)
                for key, readings in sorted(idx.get(fact_type, {}).items(),
                                            key=lambda kv: _sort_key(kv[0]))]
        for row in rows:
            if row["status"] not in ALLOWED_STATUSES[fact_type]:
                raise ValueError(
                    f"status {row['status']!r} not allowed for {fact_type} "
                    f"(policy violation at key {row['key']})"
                )
        sections[fact_type] = rows

    summary: dict[str, dict[str, int]] = {}
    for fact_type, rows in sections.items():
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        summary[fact_type] = dict(sorted(counts.items()))

    return {
        "$schema": "agreement-ledger/v1",
        "policy": {
            "disagree_reserved_for": [FACT_WORD_STRONGS, FACT_VERSE_TEXT],
            # sorted(): set iteration order varies across processes
            # (PYTHONHASHSEED) — policy must be byte-reproducible.
            "lexicon_gloss_statuses": sorted(ALLOWED_STATUSES[FACT_LEXICON_GLOSS]),
            "rationale": (
                "Gloss phrasing differences between sources of different eras "
                "are expected nuance (info readings), not findings. "
                "Disagreement is reserved for objective-equality facts. "
                "Nothing is auto-resolved; readings are verbatim. Caveat: "
                "'agree' for glosses is computed on the first ';'/':' segment, "
                "so a multi-sense gloss truncated to its first sense can agree "
                "with a single-sense reading — consult the verbatim readings."
            ),
        },
        "sources": _SOURCES,
        "summary": summary,
        "comparisons": sections,
    }


def write_ledger(repo: str = ".",
                 out_path: str | Path = "correlations/agreement-ledger.json") -> dict:
    ledger = build_ledger(repo)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    total = sum(len(rows) for rows in ledger["comparisons"].values())
    print(f"Wrote agreement ledger: {total} rows across "
          f"{len(ledger['comparisons'])} fact types -> {path}")
    for fact_type, counts in ledger["summary"].items():
        print(f"  {fact_type}: {counts}")
    return ledger