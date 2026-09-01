"""Generate the WordGraph lexical knowledge graph for Genesis (ADR-0010).

``lexicons/wordgraph-genesis.json`` is the lemma-centric spine over the
existing deterministic artifacts. It is a DERIVED, aggregate-first artifact:
it consumes ONLY committed artifacts (no raw data/ sources), so it also runs
in CI. Per ADR-0010:

  * three-layer identifier stack: token layer (OSHB ids, in occurrences) /
    lexeme layer (canonical id = Strong's for the pilot, homograph-suffixed
    only when split) / legacy crosswalk (strongs list).
  * Strong's is demoted to crosswalk, not identity — the schema is
    forward-compatible with ETCBC-style homograph numbering (Macula).
  * aggregate-first dictionary: glosses (Strong's + TBESH verbatim + ledger
    status), morphology counts, attestation, occurrence index.

Honesty rules baked in:

  * The OSHB ``n`` attribute is stored VERBATIM as counts per value, never
    used as identity (it proved unreliable as a homograph signal: H216 gets
    n=0 and n=1 in the same verse; H7307 has none).
  * TBESH variant lists are kept verbatim; the generator NEVER decides which
    sense applies — the review workflow does (deterministic core never
    guesses).
  * The ``homograph`` field is the one curated human input, seeded
    ``unresolved`` with candidate senses; a split is made only when a
    conflicting occurrence appears in scope.

Determinism: pure function of the committed artifacts; byte-identical
regeneration; no timestamps; no hash-seed-dependent ordering.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# The committed artifacts the graph consumes (all must exist).
_CONSUMED = (
    "lexicons/morphology-genesis1.json",
    "lexicons/morphology-genesis2.json",
    "lexicons/strongs-list.json",
    "lexicons/strongs-lexicon.json",
    "lexicons/tbesh-glosses.json",
    "correlations/agreement-ledger.json",
)
# The curated, REVIEWED homograph candidate file (hand content, separate from
# the generated artifact — per WP-009 convention). The generator consumes it;
# a split is made only when a conflicting occurrence appears in scope.
_HOMOGRAPH_NOTES = "lexicons/wordgraph-notes-genesis.json"


def _load(repo: str, rel: str) -> dict:
    path = Path(repo) / rel
    if not path.exists():
        raise FileNotFoundError(f"WordGraph input missing: {path} — run the "
                                "Genesis 1-2 pipeline first (WP-007)")
    return json.loads(path.read_text(encoding="utf-8"))


def _strongs_definition(lexicon_entry: dict) -> str:
    """Core definition line ('1. ...') — same extraction as the corpus
    generator / facts adapter, so the graph cannot drift from the entries."""
    desc = lexicon_entry.get("desc", "")
    for line in desc.splitlines():
        if line.strip()[:2].rstrip(".").isdigit() and "." in line[:4]:
            return line.strip()
    lines = [ln.strip() for ln in desc.splitlines() if ln.strip()]
    if len(lines) > 1:
        return lines[1]
    return lines[0] if lines else ""


def _load_homograph_notes(repo: str) -> dict:
    """Load the curated homograph candidate file (hand content)."""
    path = Path(repo) / _HOMOGRAPH_NOTES
    if not path.exists():
        raise FileNotFoundError(
            f"WordGraph homograph notes missing: {path} — this hand-curated "
            "file is required (reviewed input, per WP-009)"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates", {})
    if not isinstance(candidates, dict):
        raise ValueError(f"{_HOMOGRAPH_NOTES}: 'candidates' must be an object")
    return candidates


def _homograph_seed(code: str, candidates: dict) -> dict:
    """The curated homograph field for the pilot: all records are seeded
    'unresolved' with candidate senses listed (option A, agreed). A split is
    made only when a conflicting occurrence appears in scope. Candidate
    senses come from the reviewed notes file (TBESH variant records for a
    DISTINCT second root, plus Strong's-sense cases); the generator only
    lists them — it never decides."""
    return {
        "status": "unresolved",
        "candidate_senses": candidates.get(code, []),
        "note": "Seeded unresolved (option A): no split until a conflicting "
                "occurrence appears in scope; reviewed via the curation workflow.",
    }


def _gloss_record(lexicon: dict, tbesh: dict, ledger_gloss: dict, code: str) -> dict:
    """Assemble the gloss record for one lexeme."""
    rec = {}
    lex_entry = lexicon.get(code, {})
    rec["strongs"] = _strongs_definition(lex_entry) if lex_entry else ""
    tbesh_variants = tbesh.get("entries", {}).get(code, [])
    rec["tbesh"] = [v["gloss"] for v in tbesh_variants] if tbesh_variants else []
    # Ledger status: from the committed agreement ledger (single source of
    # truth for cross-source agreement). Missing row => None (never guess).
    row = ledger_gloss.get(code)
    rec["ledger_status"] = row.get("status") if row else None
    return rec


def build(repo: str = ".") -> dict:
    m1 = _load(repo, "lexicons/morphology-genesis1.json")
    m2 = _load(repo, "lexicons/morphology-genesis2.json")
    canonical = _load(repo, "lexicons/strongs-list.json")
    lexicon_payload = _load(repo, "lexicons/strongs-lexicon.json")
    lexicon = {**lexicon_payload.get("hebrew", {}), **lexicon_payload.get("greek", {})}
    tbesh = _load(repo, "lexicons/tbesh-glosses.json")
    ledger = _load(repo, "correlations/agreement-ledger.json")
    ledger_gloss = {r["key"]: r for r in ledger["comparisons"]["lexicon_gloss"]}
    homograph_candidates = _load_homograph_notes(repo)

    canon_all = set(canonical["hebrew"]) | set(canonical["greek"])

    # Accumulate per-lexeme data across both morphology artifacts.
    # key: canonical Strong's code (unpadded, as in the morphology base).
    morph_counts: dict[str, Counter] = {}
    n_attr_counts: dict[str, Counter] = {}
    occurrences: dict[str, list[dict]] = {}
    attestation: dict[str, Counter] = {}

    for morph in (m1, m2):
        for vkey, words in morph["verses"].items():
            for w in words:
                base = w["base"]
                if not base:
                    continue  # prefix-only words (no lexeme)
                if base not in canon_all:
                    raise ValueError(
                        f"WordGraph: lexeme {base} not in canonical Strong's list"
                    )
                morph_counts.setdefault(base, Counter())[w["morph"]] += 1
                n = w["n"]
                n_attr_counts.setdefault(base, Counter())[str(n)] += 1
                if not w["id"]:
                    raise ValueError(
                        f"WordGraph: morphology word missing id for lexeme {base} "
                        f"(passage {w.get('osisID')}) — a token without an id "
                        "would silently vanish from occurrences"
                    )
                occurrences.setdefault(base, []).append(
                    {
                        "passage": w["osisID"],
                        "token_ids": [w["id"]],
                        "wlc": [w["wlc"]],
                    }
                )
                attestation.setdefault(base, Counter())[w["osisID"]] += 1

    lexemes = []
    for code in sorted(occurrences):
        mcounts = dict(sorted(morph_counts[code].items()))
        ncounts = dict(sorted(n_attr_counts[code].items()))
        # occurrence index: group by passage, deterministic order
        occ_by_passage: dict[str, dict] = {}
        for occ in occurrences[code]:
            p = occ["passage"]
            if p not in occ_by_passage:
                occ_by_passage[p] = {"passage": p, "token_ids": [], "wlc": []}
            occ_by_passage[p]["token_ids"].extend(occ["token_ids"])
            occ_by_passage[p]["wlc"].extend(occ["wlc"])
        occ_list = [
            {"passage": p, "token_ids": o["token_ids"], "wlc": o["wlc"]}
            for p, o in sorted(occ_by_passage.items())
        ]
        n_verses = len(occ_list)
        n_tokens = sum(len(o["token_ids"]) for o in occ_list)

        lexemes.append(
            {
                "id": code,
                "strongs": [code],
                "oshb_homonyms": ncounts,
                "glosses": _gloss_record(lexicon, tbesh, ledger_gloss, code),
                "morphology": mcounts,
                "attestation": {"verses": n_verses, "tokens": n_tokens},
                "occurrences": occ_list,
                "homograph": _homograph_seed(code, homograph_candidates),
            }
        )

    scope_chapters = [1, 2]
    # Verses derived from the artifacts (never hardcoded): the distinct
    # osisIDs across the morphology layers.
    n_verses = len(
        {
            occ["passage"]
            for lexeme in lexemes
            for occ in lexeme["occurrences"]
        }
    )
    payload = {
        "$schema": "wordgraph-genesis/v1",
        "scope": {"book": "genesis", "chapters": scope_chapters, "verses": n_verses},
        "generated_from": [
            "lexicons/morphology-genesis1.json",
            "lexicons/morphology-genesis2.json",
            "lexicons/strongs-list.json",
            "lexicons/strongs-lexicon.json",
            "lexicons/tbesh-glosses.json",
            "correlations/agreement-ledger.json",
            "lexicons/wordgraph-notes-genesis.json",
        ],
        "identity_model": (
            "Three-layer stack per ADR-0010: token layer (OSHB ids in "
            "occurrences), lexeme layer (canonical id = Strong's for the "
            "pilot; homograph-suffixed only when split), legacy crosswalk "
            "(strongs). Full ETCBC-style homograph numbering arrives with "
            "Macula/BHSA; schema is forward-compatible."
        ),
        "honesty_rules": [
            "OSHB n-attribute stored verbatim as counts, never as identity "
            "(unreliable as homograph signal).",
            "TBESH variants verbatim; generator never decides sense — the "
            "review workflow does.",
            "Homograph field is the one curated human input, seeded "
            "unresolved with candidate senses (option A); splits only when a "
            "conflicting occurrence appears in scope.",
            "Theological prose per lexeme deferred indefinitely (thin human "
            "layer).",
            "TBESG (Greek glosses) intentionally not consumed: Genesis 1-2 is "
            "all-Hebrew — the Greek gloss layer applies when a Greek-scope "
            "book is added.",
        ],
        "lexemes": lexemes,
    }
    return payload


def write(repo: str = ".", out_path: str | Path = "lexicons/wordgraph-genesis.json") -> dict:
    payload = build(repo)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_lexemes = len(payload["lexemes"])
    n_tokens = sum(l["attestation"]["tokens"] for l in payload["lexemes"])
    print(f"Wrote WordGraph: {n_lexemes} lexemes, {n_tokens} tokens -> {path}")
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the WordGraph lexical knowledge graph for Genesis"
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    out = args.out or "lexicons/wordgraph-genesis.json"
    write(args.repo, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())