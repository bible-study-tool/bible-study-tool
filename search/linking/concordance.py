"""Layer (b): Deterministic Strong's root concordance.

This is the *authoritative*, human-verified core. It groups all entries that
share the same original-language lexeme (Strong's number) and connects that
lexeme's attestations across passages, translations, and languages (Hebrew
root -> LXX Greek -> English).

It is fully deterministic: given the same materials tree it always produces
the same output. It never invents connections — every edge here is grounded in
an explicit Strong's tag or a curated semantic link.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def _extract_strongs(entry) -> list[str]:
    """Strong's tags look like 'strongs-H7225' -> 'H7225'."""
    result = []
    for tag in entry.tags:
        if tag.startswith("strongs-"):
            result.append(tag[len("strongs-") :])
    return result


def _language_of(entry) -> str:
    return entry.frontmatter.get("language", "")


def _translation_of(entry) -> str:
    return entry.frontmatter.get("translation", "")


def build_concordance(loader, db=None) -> dict:
    """Build the deterministic concordance index.

    If a SemanticDB (`db`) is provided, the Strong's->entry pairs are read
    from the index rather than rescanning the Markdown tree. `loader` is still
    used for the curated `semantic-links.json` lookup.

    Returns a dict:
    {
      "by_strongs": { "H7225": {entries, semantic_field} },
      "links": [ { deterministic cross-passage links } ],
      "summary": {...}
    }
    """
    if db is not None:
        # DB-backed: pairs come from the SQLite index.
        pairs = db.concordance()
        by_strongs: dict[str, list[dict]] = defaultdict(list)
        for p in pairs:
            by_strongs[p["strongs"]].append(p)
        entries = db.entries()
    else:
        entries = loader.entries
        # strongs -> list of entries using it
        by_strongs = defaultdict(list)
        for entry in entries:
            for strongs in _extract_strongs(entry):
                by_strongs[strongs].append(
                    {
                        "entry_id": entry.id,
                        "path": entry.path,
                        "passage": entry.passage,
                        "language": _language_of(entry),
                        "translation": _translation_of(entry),
                        "word": entry.frontmatter.get("word", ""),
                    }
                )

    # Deterministic same-lexeme cross-passage links.
    # An edge exists when a single Strong's root appears in >= 2 distinct
    # passage/entry locations, OR the same passage is attestted across
    # multiple translations/languages.
    links = []
    for strongs, refs in sorted(by_strongs.items()):
        if len(refs) < 2:
            # Single attestation but present in entry word studies still
            # meaningful if it has a curated semantic link; handled by the
            # curated index separately. Keep single-entry roots in the index.
            links.append(_root_link(strongs, refs, multi=False))
            continue
        links.append(_root_link(strongs, refs, multi=True))

    # Strong's -> linked English concept notes pulled from curated semantic
    # links so the display layer can show "these share a root" annotations.
    curated = loader.load_links()
    curated_by_strongs: dict[str, str] = {}
    if curated:
        for link in curated.get("links", []):
            for ent in link.get("entries", []):
                s = ent.get("strongs")
                if s:
                    curated_by_strongs.setdefault(s, link.get("semantic_field", link.get("type", "")))

    by_strongs_out = {}
    for strongs, refs in sorted(by_strongs.items()):
        by_strongs_out[strongs] = {
            "entries": refs,
            "semantic_field": curated_by_strongs.get(strongs, ""),
        }

    return {
        "version": "concordance/v1",
        "last_updated": _today(),
        "description": "Deterministic Strong's root concordance: same-lexeme cross-passage and cross-language links",
        "by_strongs": by_strongs_out,
        "links": links,
        "summary": {
            "roots": len(by_strongs),
            "links": len(links),
            "entries": len(entries),
        },
    }


def _root_link(strongs: str, refs: list[dict], multi: bool) -> dict:
    languages = sorted({r["language"] for r in refs if r["language"]})
    passages = sorted({r["passage"] for r in refs if r["passage"]})
    return {
        "strongs": strongs,
        "kind": "concordance/multi-root" if multi else "concordance/root",
        "languages": languages,
        "cross_language": len(languages) > 1,
        "passages": passages,
        "entries": [r["entry_id"] for r in refs],
        "note": "Same original-language lexeme (Strong's) shared across these passages; English hides the link, the original language reveals it."
        if multi
        else "Strong's root attested in this passage.",
    }


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


def write_concordance(loader, out_path: str | Path = "index/concordance.json", db=None) -> dict:
    data = build_concordance(loader, db=db)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data
