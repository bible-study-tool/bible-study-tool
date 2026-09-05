"""Macula semantic enrichment engine (Pillar B, Goal B3, ADR-0015).

Provides:
  1. Empirical Septuagint (LXX) translation-equivalence lookups.
  2. Syntactic semantic frame extraction (Agent, Action, Patient, Context).
  3. Grounded cross-language candidate discovery for ai-discovered-links.json.
  4. Non-destructive enrichment of curated semantic links.
"""

from __future__ import annotations

import copy
from datetime import date
from functools import lru_cache
from itertools import combinations
import json
from pathlib import Path
from typing import Any, Iterable

from search.macula.extract import (
    normalize_greek_strongs,
    normalize_hebrew_strongs,
    resolve_role_query,
)
from search.macula.lookup import MaculaDB, get_db

_AGENT_ROLES: frozenset[str] = frozenset(resolve_role_query("subj"))
_ACTION_ROLES: frozenset[str] = (
    frozenset(resolve_role_query("pred"))
    | frozenset(resolve_role_query("verb"))
    | frozenset(resolve_role_query("copula"))
)
_PATIENT_ROLES: frozenset[str] = frozenset(resolve_role_query("obj"))
_CONTEXT_ROLES: frozenset[str] = (
    frozenset(resolve_role_query("pp"))
    | frozenset(resolve_role_query("adv"))
    | frozenset(resolve_role_query("prep"))
)


def _clean_definition(desc: str) -> str:
    """Extract first line definition from Strong's desc text."""
    if not desc:
        return ""
    lines = [line.strip() for line in desc.splitlines() if line.strip()]
    for line in lines:
        if line[0].isdigit() and "." in line:
            return line.split(".", 1)[1].strip()
    non_headers = [l for l in lines if not l.startswith("Strong's Number")]
    return non_headers[0] if non_headers else (lines[0] if lines else "")


def get_translation_equivalences(
    strongs_query: str,
    db: MaculaDB | None = None,
    repo_root: str | Path = ".",
) -> list[dict[str, Any]]:
    """Retrieve Septuagint (LXX) translation equivalents for a Strong's number.

    Accepts Hebrew Strong's (e.g. 'H1254', '1254') or Greek Strong's ('G4160').
    Returns sorted list of attested translation equivalents with occurrence counts.
    """
    database = db or get_db(repo_root)

    # Check if Hebrew
    h_norm = normalize_hebrew_strongs(strongs_query)
    if h_norm:
        entry = database.lookup_strongs(h_norm)
        if not entry:
            return []
        equivalents = []
        for g_id, g_rec in entry.get("lxx", {}).items():
            equivalents.append({
                "hebrew_strongs": h_norm,
                "greek_strongs": g_id,
                "hebrew_lemmas": entry.get("lemmas", []),
                "hebrew_glosses": entry.get("glosses", []),
                "greek_forms": g_rec.get("greek", []),
                "count": g_rec.get("count", 0),
                "core_domains": entry.get("core_domains", []),
                "sdbh": entry.get("sdbh", []),
            })
        equivalents.sort(key=lambda x: x["count"], reverse=True)
        return equivalents

    # Check if Greek
    g_norm = normalize_greek_strongs(strongs_query)
    if g_norm:
        matches = database.lookup_lxx(g_norm)
        equivalents = []
        for m in matches:
            equivalents.append({
                "greek_strongs": g_norm,
                "hebrew_strongs": m.get("hebrew_strongs"),
                "hebrew_lemmas": m.get("lemmas", []),
                "hebrew_glosses": m.get("glosses", []),
                "greek_forms": m.get("greek_forms", []),
                "count": m.get("count", 0),
            })
        equivalents.sort(key=lambda x: x["count"], reverse=True)
        return equivalents

    return []


def extract_semantic_frames_from_verse(verse_data: dict[str, Any]) -> dict[str, Any]:
    """Extract syntactic semantic frame (Agent, Action, Patient, Context) from raw verse data."""
    clause_frames = []
    for idx, cl in enumerate(verse_data.get("clauses", []), 1):
        rule = cl.get("rule", "")
        agents = []
        actions = []
        patients = []
        context = []
        other = []

        for const in cl.get("constituents", []):
            role = (const.get("role") or "").lower()
            role_label = (const.get("role_label") or "").lower()
            c_info = {
                "text": const.get("text", ""),
                "role": const.get("role"),
                "role_label": const.get("role_label"),
                "class": const.get("class"),
                "tokens": [
                    {
                        "text": tok.get("text"),
                        "lemma": tok.get("lemma"),
                        "strongs": tok.get("strongs"),
                        "lxx_strongs": tok.get("lxx_strongs"),
                        "gloss": tok.get("gloss"),
                    }
                    for tok in const.get("tokens", [])
                ],
            }

            if role in _AGENT_ROLES or role_label in _AGENT_ROLES:
                agents.append(c_info)
            elif role in _ACTION_ROLES or role_label in _ACTION_ROLES:
                actions.append(c_info)
            elif role in _PATIENT_ROLES or role_label in _PATIENT_ROLES:
                patients.append(c_info)
            elif role in _CONTEXT_ROLES or role_label in _CONTEXT_ROLES:
                context.append(c_info)
            else:
                other.append(c_info)

        # Build concise frame summary
        role_groups = (
            ("Agent", agents),
            ("Action", actions),
            ("Patient", patients),
            ("Context", context),
        )
        parts = [
            f"{label}: {', '.join(item['text'] for item in items)}"
            for label, items in role_groups
            if items
        ]
        summary = " | ".join(parts) if parts else f"Clause {idx}"

        clause_frames.append({
            "clause_num": idx,
            "rule": rule,
            "summary": summary,
            "agents": agents,
            "actions": actions,
            "patients": patients,
            "context": context,
            "other": other,
        })

    return {
        "verse_id": verse_data.get("verse_id"),
        "mt_id": verse_data.get("mt_id"),
        "text": verse_data.get("text"),
        "clauses": clause_frames,
    }


def get_verse_semantic_frame(
    verse_ref: str,
    db: MaculaDB | None = None,
    repo_root: str | Path = ".",
) -> dict[str, Any] | None:
    """Extract syntactic semantic frame (Agent, Action, Patient, Context) for a verse."""
    database = db or get_db(repo_root)
    verse_data = database.lookup_verse(verse_ref)
    if not verse_data:
        return None
    return extract_semantic_frames_from_verse(verse_data)


def get_verse_semantic_frames_batch(
    verse_refs: list[str],
    db: MaculaDB | None = None,
    repo_root: str | Path = ".",
) -> dict[str, dict[str, Any]]:
    """Extract syntactic semantic frames for multiple verses in a fast batch query."""
    if not verse_refs:
        return {}
    database = db or get_db(repo_root)
    raw_map: dict[str, dict[str, Any]] = {}
    if hasattr(database, "lookup_verses_batch"):
        raw_map = database.lookup_verses_batch(verse_refs)
    elif hasattr(database, "_sqlite") and database._sqlite and hasattr(database._sqlite, "lookup_verses_batch"):
        raw_map = database._sqlite.lookup_verses_batch(verse_refs)
    else:
        for r in verse_refs:
            vd = database.lookup_verse(r)
            if vd:
                raw_map[r] = vd

    results: dict[str, dict[str, Any]] = {}
    extracted_by_id: dict[int, dict[str, Any]] = {}
    for ref_key, vd in raw_map.items():
        vd_id = id(vd)
        if vd_id not in extracted_by_id:
            extracted_by_id[vd_id] = extract_semantic_frames_from_verse(vd)
        results[ref_key] = extracted_by_id[vd_id]
    return results


def enrich_curated_link(
    link: dict[str, Any],
    db: MaculaDB | None = None,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Enrich a curated semantic link with empirical LXX witness data without mutating."""
    database = db or get_db(repo_root)
    result = copy.deepcopy(link)

    h_strongs = None
    g_strongs = None
    for ent in result.get("entries", []):
        s = ent.get("strongs", "")
        norm_h = normalize_hebrew_strongs(s)
        norm_g = normalize_greek_strongs(s)
        if norm_h and not h_strongs:
            h_strongs = norm_h
        elif norm_g and not g_strongs:
            g_strongs = norm_g

    if h_strongs and g_strongs:
        eqs = get_translation_equivalences(h_strongs, db=database, repo_root=repo_root)
        for eq in eqs:
            if eq.get("greek_strongs") == g_strongs:
                result["empirical_evidence"] = {
                    "source": "macula/lxx-alignment",
                    "attestation_count": eq.get("count", 0),
                    "greek_forms": eq.get("greek_forms", []),
                    "core_domains": eq.get("core_domains", []),
                }
                break

    return result


@lru_cache(maxsize=2)
def _load_strongs_lexicon(repo_root: str | Path = ".") -> dict[str, dict]:
    """Load definitions and transliterations from strongs-lexicon.json."""
    path = Path(repo_root) / "lexicons" / "strongs-lexicon.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {**data.get("hebrew", {}), **data.get("greek", {})}
    except Exception:
        return {}


def _curated_strongs_pairs(repo_root: str | Path = ".") -> set[frozenset[str]]:
    """Collect Strong's pairs already present in semantic-links.json."""
    path = Path(repo_root) / "correlations" / "semantic-links.json"
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        pairs = set()
        for link in data.get("links", []):
            strongs = [
                norm
                for e in link.get("entries", [])
                if (s := e.get("strongs"))
                and (norm := normalize_hebrew_strongs(s) or normalize_greek_strongs(s) or s)
            ]
            for s1, s2 in combinations(strongs, 2):
                pairs.add(frozenset((s1, s2)))
        return pairs
    except Exception:
        return set()


def discover_translation_equivalence_candidates(
    strongs_filter: Iterable[str] | None = None,
    min_lxx_count: int = 2,
    limit: int = 50,
    repo_root: str | Path = ".",
    db: MaculaDB | None = None,
) -> list[dict[str, Any]]:
    """Discover cross-language translation-equivalence candidates from Macula LXX alignments."""
    database = db or get_db(repo_root)
    lexicon = _load_strongs_lexicon(repo_root)
    curated_pairs = _curated_strongs_pairs(repo_root)

    candidates: list[dict[str, Any]] = []
    seen_pairs: set[frozenset[str]] = set()

    # Determine candidate Hebrew Strong's to examine
    if strongs_filter:
        seen_h: set[str] = set()
        h_codes = []
        for s in strongs_filter:
            c = normalize_hebrew_strongs(s)
            if c and c not in seen_h:
                seen_h.add(c)
                h_codes.append(c)
    else:
        # If no filter provided, inspect crosswalk from database
        if database.is_sqlite and getattr(database, "_sqlite", None) and database._sqlite.exists():
            cur = database._sqlite.conn.execute("SELECT strongs FROM strongs_crosswalk ORDER BY occurrences DESC;")
            h_codes = [r[0] for r in cur.fetchall()]
        elif getattr(database, "_crosswalk", None):
            h_codes = sorted(
                database._crosswalk.keys(),
                key=lambda k: database._crosswalk[k].get("occurrences", 0),
                reverse=True,
            )
        else:
            h_codes = []

    today_str = date.today().isoformat()
    counter = 1

    for h_id in h_codes:
        equivalents = get_translation_equivalences(h_id, db=database, repo_root=repo_root)
        for eq in equivalents:
            g_id = eq.get("greek_strongs")
            count = eq.get("count", 0)
            if not g_id or count < min_lxx_count:
                continue

            pair = frozenset((h_id, g_id))
            if pair in curated_pairs or pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            h_lex = lexicon.get(h_id, {})
            g_lex = lexicon.get(g_id, {})

            h_word = h_lex.get("word") or (eq.get("hebrew_lemmas") or [""])[0]
            g_word = g_lex.get("word") or (eq.get("greek_forms") or [""])[0]
            h_def = _clean_definition(h_lex.get("desc", "")) or ", ".join(eq.get("hebrew_glosses", []))
            g_def = _clean_definition(g_lex.get("desc", ""))

            confidence = "high" if count >= 3 else "medium"

            cand = {
                "id": f"aid-lxx-{today_str.replace('-', '')}-{counter:03d}",
                "type": "relation/translation-equivalence",
                "confidence": confidence,
                "source": "macula/lxx-alignment",
                "review_status": "pending",
                "aligns_with_doctrine": None,
                "created": today_str,
                "lxx_count": count,
                "entries": [
                    {
                        "strongs": h_id,
                        "language": "hebrew",
                        "word": h_word,
                        "transliteration": h_lex.get("translit", ""),
                        "definition": h_def,
                        "core_domains": eq.get("core_domains", []),
                    },
                    {
                        "strongs": g_id,
                        "language": "greek",
                        "word": g_word,
                        "transliteration": g_lex.get("translit", ""),
                        "definition": g_def,
                        "greek_forms": eq.get("greek_forms", []),
                    },
                ],
                "rationale": (
                    f"Macula empirical Septuagint (LXX) alignment: {h_id} ({h_word}) is translated "
                    f"by {g_id} ({g_word}) {count}x in Genesis."
                ),
                "review_required": True,
            }
            candidates.append(cand)
            counter += 1
            if len(candidates) >= limit:
                return candidates

    return candidates
