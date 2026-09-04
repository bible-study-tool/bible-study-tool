"""Layer (c): Multilingual semantic candidate discovery (AI layer).

This is the *suggestive* layer. Unlike layer (b) it can propose links that
go beyond a shared Strong's number — e.g. Hebrew ``bara`` (divine create)
with Greek ``ktizo`` (divine create) which belong to a common conceptual
field but are *different* lexemes and *different* scripts.

Strictness rules (non-negotiable, enforced in code):
1. Candidates are ONLY proposed across different languages, or between a
   lexeme and its own explicit cross-language curated group.
2. A candidate must exceed a similarity threshold (default 0.82 in the
   deterministic space) — low-confidence proposals are dropped.
3. Only relationship types from the tag taxonomy's ``relation/`` vocabulary
   are emitted.
4. Every candidate carries a ``confidence`` (high/medium/low) and
   ``review_status``.
5. Output is ALWAYS written to ``ai-discovered-links.json`` — never to the
   deterministic ``semantic-links.json``.
6. Candidates already present as curated links are skipped (dedupe by
   strongs pair).
7. Theological alignment is a human review gate, indicated by a dedicated
   ``aligns_with_doctrine`` field that is always ``None`` until a reviewer
   sets it.

Every candidate is provisional until a human promotes it into the
deterministic core.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Iterable

from .embedder import get_embedder

# Only these relationship vocab entries may be proposed by the AI layer.
ALLOWED_RELATION_TYPES = {
    "relation/equivalent",
    "relation/translation-equivalence",
    "relation/semantic-field",
    "relation/etymology",
    "relation/metaphor",
    "relation/figurative",
}

# Contrast is intentionally *not* auto-proposed: it requires human judgment.
RULE_ARCHIVE = {
    "min_similarity": 0.82,
    "cross_language_required": True,
    "allowed_relation_types": sorted(ALLOWED_RELATION_TYPES),
    "contrast_requires_human": True,
    "output": "correlations/ai-discovered-links.json",
    "deterministic_core_protected": True,
}


@dataclass
class Lexeme:
    """A lexical unit that can participate in semantic candidates."""

    strongs: str
    word: str
    transliteration: str
    definition: str
    language: str
    entry_ids: list = field(default_factory=list)
    semantic_fields: list = field(default_factory=list)


def _read_lexemes(loader, db=None) -> list[Lexeme]:
    """Collect lexemes from (a) entry word-study blocks and (b) curated links.

    If a SemanticDB (`db`) is supplied the entries come from the stored index
    (bodies are rehydrated) rather than rescanning the Markdown tree.
    """
    from .dbindex import SemanticDB  # local import to avoid cycles

    by_key: dict[tuple, Lexeme] = {}

    def add(strongs, word, transliteration, definition, language, entry_id, field_name):
        if not strongs:
            return
        key = (strongs, language)
        lex = by_key.get(key)
        if lex is None:
            lex = Lexeme(
                strongs=strongs,
                word=word,
                transliteration=transliteration,
                definition=definition,
                language=language,
            )
            by_key[key] = lex
        if entry_id and entry_id not in lex.entry_ids:
            lex.entry_ids.append(entry_id)
        if field_name and field_name not in lex.semantic_fields:
            lex.semantic_fields.append(field_name)
        if not lex.definition and definition:
            lex.definition = definition
        if not lex.word and word:
            lex.word = word
        if not lex.transliteration and transliteration:
            lex.transliteration = transliteration

    if db is not None:
        # DB-backed: entries with body come from the index.
        from .loader import _extract_words

        for row in db.entries():
            fm = {}
            try:
                import json

                fm = json.loads(row.get("frontmatter") or "{}")
            except Exception:
                fm = {}
            for w in _extract_words(row.get("body") or ""):
                add(
                    w.get("strongs", ""),
                    w.get("word", ""),
                    w.get("transliteration", ""),
                    w.get("definition", ""),
                    str(fm.get("language") or ""),
                    row.get("id"),
                    None,
                )
    else:
        for entry in loader.entries:
            for w in entry.words:
                add(
                    w.get("strongs", ""),
                    w.get("word", ""),
                    w.get("transliteration", ""),
                    w.get("definition", ""),
                    entry.frontmatter.get("language", ""),
                    entry.id,
                    None,
                )

    curated = loader.load_links()
    if curated:
        for link in curated.get("links", []):
            sem_field = link.get("semantic_field", "")
            for ent in link.get("entries", []):
                add(
                    ent.get("strongs", ""),
                    ent.get("word", ""),
                    ent.get("transliteration", ""),
                    ent.get("definition", ""),
                    ent.get("language", ""),
                    None,
                    sem_field,
                )
    return list(by_key.values())


def _text_for_embedding(lex: Lexeme) -> str:
    """Build a searchable surface that works across scripts."""
    parts = [lex.word, lex.transliteration, lex.definition, " ".join(lex.semantic_fields)]
    return " ".join(p for p in parts if p).strip()


def _relation_for(lex_a: Lexeme, lex_b: Lexeme, sim: float) -> str:
    # If they already share a semantic field -> semantic-field.
    shared = set(lex_a.semantic_fields) & set(lex_b.semantic_fields)
    if shared:
        return "relation/semantic-field"
    if sim >= 0.9:
        return "relation/equivalent"
    return "relation/translation-equivalence"


def _confidence(sim: float) -> str:
    if sim >= 0.92:
        return "high"
    if sim >= 0.86:
        return "medium"
    return "low"


@dataclass
class Candidate:
    lex_a: Lexeme
    lex_b: Lexeme
    similarity: float
    relation: str
    confidence: str
    rationale: str


class GateKeeper:
    """Applies the strict acceptance rules to raw pairwise proposals."""

    def __init__(self, min_similarity: float = RULE_ARCHIVE["min_similarity"]):
        self.min_similarity = min_similarity
        self.accepted = []
        self.rejected = []

    def propose(self, lex_a: Lexeme, lex_b: Lexeme, similarity: float) -> Candidate | None:
        # Rule 1: cross-language required (Hebrew vs Greek, Hebrew vs English,
        # Greek vs English) — same-language pairs are concordance territory (b).
        if lex_a.language == lex_b.language:
            self.rejected.append((lex_a, lex_b, "same_language"))
            return None
        # Rule 2: similarity threshold.
        if similarity < self.min_similarity:
            self.rejected.append((lex_a, lex_b, f"below_threshold:{similarity:.3f}"))
            return None
        relation = _relation_for(lex_a, lex_b, similarity)
        if relation not in ALLOWED_RELATION_TYPES:
            self.rejected.append((lex_a, lex_b, "relation_not_allowed"))
            return None
        candidate = Candidate(
            lex_a=lex_a,
            lex_b=lex_b,
            similarity=similarity,
            relation=relation,
            confidence=_confidence(similarity),
            rationale=(
                f"Cross-language semantic overlap between {_label(lex_a)} "
                f"({lex_a.language}) and {_label(lex_b)} ({lex_b.language}); "
                f"similarity {similarity:.2f}."
            ),
        )
        self.accepted.append(candidate)
        return candidate

    def already_curated(self, lex_a: Lexeme, lex_b: Lexeme, curated_pairs: set) -> bool:
        pair = frozenset((lex_a.strongs, lex_b.strongs))
        return pair in curated_pairs


def _label(lex: Lexeme) -> str:
    base = lex.word or lex.transliteration or lex.strongs
    return f"{base} ({lex.strongs})"


def _curated_pairs(loader) -> set:
    pairs: set = set()
    curated = loader.load_links()
    if not curated:
        return pairs
    for link in curated.get("links", []):
        strongs_list = [e.get("strongs") for e in link.get("entries", []) if e.get("strongs")]
        for s in strongs_list:
            for t in strongs_list:
                if s != t:
                    pairs.add(frozenset((s, t)))
    return pairs


def discover_candidates(
    loader,
    embedder=None,
    top_k: int = 5,
    min_similarity: float = RULE_ARCHIVE["min_similarity"],
    db=None,
    include_macula: bool = False,
    min_lxx_count: int = 2,
) -> list[dict]:
    lexemes = _read_lexemes(loader, db=db)
    embedder = embedder or get_embedder()

    # Index vectors.
    vectors = {id(lx): embedder.embed(_text_for_embedding(lx)) for lx in lexemes}

    curated_pairs = _curated_pairs(loader)
    gate = GateKeeper(min_similarity=min_similarity)
    proposals: list[Candidate] = []
    seen_pairs: set = set()

    for a, b in combinations(lexemes, 2):
        if gate.already_curated(a, b, curated_pairs):
            continue
        pair_key = frozenset((a.strongs, b.strongs))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        try:
            import numpy as np

            va = vectors[id(a)]
            vb = vectors[id(b)]
            denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1.0
            sim = float(np.dot(va, vb) / denom)
        except Exception:  # pragma: no cover
            sim = 0.0

        cand = gate.propose(a, b, sim)
        if cand is not None:
            proposals.append(cand)

    # Keep only the strongest N proposals.
    proposals.sort(key=lambda c: c.similarity, reverse=True)
    proposals = proposals[:top_k]

    results = [
        {
            "id": f"aid-{date.today():%Y%m%d}-{i + 1:03d}",
            "type": c.relation,
            "confidence": c.confidence,
            "source": "ai",
            "review_status": "pending",
            "aligns_with_doctrine": None,
            "created": date.today().isoformat(),
            "similarity": round(c.similarity, 3),
            "entries": [
                {
                    "strongs": c.lex_a.strongs,
                    "language": c.lex_a.language,
                    "word": c.lex_a.word,
                    "transliteration": c.lex_a.transliteration,
                    "definition": c.lex_a.definition,
                    "semantic_fields": c.lex_a.semantic_fields,
                },
                {
                    "strongs": c.lex_b.strongs,
                    "language": c.lex_b.language,
                    "word": c.lex_b.word,
                    "transliteration": c.lex_b.transliteration,
                    "definition": c.lex_b.definition,
                    "semantic_fields": c.lex_b.semantic_fields,
                },
            ],
            "rationale": c.rationale,
            "review_required": True,
        }
        for i, c in enumerate(proposals)
    ]

    if include_macula:
        from search.macula.enrichment import discover_translation_equivalence_candidates

        hebrew_strongs = [lx.strongs for lx in lexemes if lx.language == "hebrew"]
        macula_proposals = discover_translation_equivalence_candidates(
            strongs_filter=hebrew_strongs,
            min_lxx_count=min_lxx_count,
            limit=top_k,
            repo_root=getattr(loader, "repo_root", getattr(loader, "repo", ".")),
        )
        existing_keys = {_candidate_key(r) for r in results}
        for mc in macula_proposals:
            key = _candidate_key(mc)
            if key not in existing_keys:
                results.append(mc)
                existing_keys.add(key)

    return results



def _candidate_key(cand: dict) -> frozenset:
    """Stable identity key for a candidate: its unordered Strong's pair.

    Two runs of the pipeline produce the same pair for the same two lexemes,
    so this lets us carry forward human review annotations across
    regenerations instead of clobbering them.
    """
    strongs = {e.get("strongs") for e in cand.get("entries", [])}
    return frozenset(s for s in strongs if s)


# Review metadata that a human may have set on a candidate; these must survive
# regeneration so decisions (and rejected-link traceability) are not lost.
_PRESERVED_FIELDS = ("review_status", "aligns_with_doctrine", "reviewed_by", "review_note")


def _merge_existing(existing_cands: list[dict], fresh_cands: list[dict]) -> list[dict]:
    """Carry forward human review annotations from prior candidates.

    ``existing_cands`` come from the file on disk (which is now tracked);
    ``fresh_cands`` are this run's freshly discovered proposals. For each
    fresh candidate, if a prior candidate had the same Strong's pair and had
    been reviewed (non-default review metadata), copy that metadata forward.
    This prevents a ``--discover`` run from discarding human decisions.
    """
    by_pair: dict[frozenset, dict] = {}
    for prior in existing_cands:
        key = _candidate_key(prior)
        if key and (prior.get("review_status") != "pending" or prior.get("aligns_with_doctrine") is not None):
            by_pair[key] = prior

    merged = []
    for cand in fresh_cands:
        prior = by_pair.get(_candidate_key(cand))
        if prior is not None:
            cand = {**cand}
            for field in _PRESERVED_FIELDS:
                if field in prior and prior[field] is not None:
                    cand[field] = prior[field]
        merged.append(cand)
    return merged


def write_candidates(
    loader,
    out_path: str | Path = "correlations/ai-discovered-links.json",
    min_similarity: float = RULE_ARCHIVE["min_similarity"],
    **kw,
) -> list[dict]:
    """Discover and persist candidates to ai-discovered-links.json.

    ``min_similarity`` is threaded into the acceptance gate so callers can
    tune it for the active embedder space (transformer space is typically
    ~0.82+; the deterministic fallback space is ~0.7+).

    Human review annotations on existing candidates are preserved across
    runs: a fresh discovery never clobbers prior ``review_status`` /
    ``aligns_with_doctrine`` / ``reviewed_by`` / ``review_note`` for the same
    Strong's pair.
    """
    fresh = discover_candidates(loader, min_similarity=min_similarity, **kw)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_cands: list[dict] = []
    if path.exists():
        try:
            with open(path, encoding="utf-8") as fh:
                existing = json.load(fh)
            existing_cands = existing.get("candidates", []) if isinstance(existing, dict) else []
        except Exception:
            existing_cands = []

    candidates = _merge_existing(existing_cands, fresh)
    payload = {
        "$schema": "ai-discovered-links/v1",
        "version": "1.0.0",
        "last_updated": date.today().isoformat(),
        "description": "AI-suggested cross-language semantic links awaiting human review. Deterministic core is never modified.",
        "rules": {**RULE_ARCHIVE, "min_similarity": min_similarity},
        "candidates": candidates,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return candidates
