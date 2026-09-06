"""Generate deterministic draft skeletons for New Testament chapters (Pillar A3).

Everything emitted here is derived from pinned sources (data/PROVENANCE.md):

  * Verse text          — scrollmapper KJV-osis (public domain KJV), verbatim
                          after stripping the OSIS tagging markup.
  * Strong's tags       — the `lemma="strong:G####"` tokens of the pinned
                          NT text (the verse's actual word-level Greek attestation).
  * Word-study facts    — lexicons/strongs-lexicon.json (Strong's Greek, public
                          domain: Greek form, transliteration, definition) and
                          lexicons/tbesg-glosses.json (STEPBible CC BY 4.0,
                          supplementary: modern brief gloss + morphology).

Scope (Pillar A3): New Testament chapters, e.g. John 1 (verses 1-51) and
John 17 (verses 1-26). Output is structured per-chapter in
`materials/bible/nt/{book}/{ch:02d}/{book}-{ch}-{v}-kjv.md`.

What is deliberately NOT generated in skeletons: cross-references, theological
notes, AI summaries. Those are added during human curation per
CONTRIBUTION_STANDARDS.md. The generator provides a verified, complete,
factual skeleton ready for curation.

Idempotence: output is a pure function of the pinned sources + GENERATION_DATE.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

# Pinned generation date for NT corpus scaffolding (Pillar A3)
GENERATION_DATE = "2026-09-06"

# Canonical Greek Strong's bound (must match lexicons/strongs-list.json)
_MAX_GREEK = 5624

_LEMMA_RE = re.compile(r"strong:G(\d{1,5})")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_NOTE_RE = re.compile(r"<note\b[^>]*>.*?</note>", re.DOTALL)


def load_pinned_sources(repo: str = ".") -> tuple[dict, dict, dict, dict]:
    """Load (kjv_osis, greek_lexicon, tbesg_entries, canonical_list) pinned data."""
    repo_path = Path(repo)
    kjv_path = repo_path / "data/KJV-osis.json"
    if not kjv_path.exists():
        raise FileNotFoundError(
            f"KJV-osis source missing at {kjv_path} — run scripts/fetch_sources.sh first"
        )
    kjv = json.loads(kjv_path.read_text(encoding="utf-8"))
    lex_payload = json.loads(
        (repo_path / "lexicons/strongs-lexicon.json").read_text(encoding="utf-8")
    )
    greek_lexicon = lex_payload.get("greek", {})
    tbesg_payload = json.loads(
        (repo_path / "lexicons/tbesg-glosses.json").read_text(encoding="utf-8")
    )
    tbesg_entries = tbesg_payload.get("entries", {})
    canonical = json.loads(
        (repo_path / "lexicons/strongs-list.json").read_text(encoding="utf-8")
    )
    return kjv, greek_lexicon, tbesg_entries, canonical


def clean_verse_text(raw: str) -> str:
    """Strip OSIS markup, keep inner text + punctuation, unescape entities."""
    text = _NOTE_RE.sub("", raw)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def verse_codes(raw_text: str) -> tuple[list[str], dict[str, int], list[str]]:
    """Distinct Greek Strong's codes in a verse + per-code lemma counts + skipped."""
    seen: dict[str, int] = {}
    skipped: list[str] = []
    n_attributes = raw_text.count("strong:G")
    matches = _LEMMA_RE.findall(raw_text)
    if len(matches) != n_attributes:
        raise ValueError(
            f"Greek lemma parse mismatch: {n_attributes} 'strong:G' attributes but "
            f"{len(matches)} parsed."
        )
    for num_s in matches:
        num = int(num_s)
        code = f"G{num}"
        if num > _MAX_GREEK or num < 1:
            skipped.append(code)
            continue
        seen[code] = seen.get(code, 0) + 1
    return list(seen), seen, skipped


def strongs_definition(lexicon_entry: dict) -> str:
    """Core definition line from a Strong's lexicon entry."""
    desc = lexicon_entry.get("desc", "")
    for line in desc.splitlines():
        if re.match(r"^\d+\.", line.strip()):
            return line.strip()
    lines = [ln.strip() for ln in desc.splitlines() if ln.strip()]
    if len(lines) > 1:
        return lines[1]
    return lines[0] if lines else ""


def _short_gloss(gloss: str) -> str:
    """First gloss segment for the word-study title (split on ';' / ':')."""
    for sep in (";", ":", "/"):
        if sep in gloss:
            gloss = gloss.split(sep, 1)[0].strip()
    return gloss


def word_study_block(
    code: str,
    occurrences: int,
    greek_lexicon: dict,
    tbesg_entries: dict,
) -> str:
    """Render one '### <word> - Strong's G####' block for NT entries."""
    lex_entry = greek_lexicon.get(code, {})
    tbesg_list = tbesg_entries.get(code, [])
    tbesg_item = tbesg_list[0] if tbesg_list else {}

    translit = lex_entry.get("translit") or tbesg_item.get("translit") or ""
    definition = strongs_definition(lex_entry)
    gloss = tbesg_item.get("gloss") or ""
    morph = tbesg_item.get("morph") or ""

    if translit and gloss:
        header = f"### {translit} ({_short_gloss(gloss)}) - Strong's {code}"
    elif translit:
        header = f"### {translit} - Strong's {code}"
    else:
        header = f"### Strong's {code}"

    lines = [
        header,
        "",
        f"*   Transliteration: {translit}",
        f"*   Definition: {definition}",
    ]
    if gloss:
        lines.append(f"*   Modern Gloss (TBESG): {gloss}")
    if morph:
        lines.append(f"*   Morphology (STEPBible): {morph}")
    lines.append(f"*   Lemma occurrences in this verse: {occurrences}")
    return "\n".join(lines)


def build_entry_markdown(
    verse: dict,
    greek_lexicon: dict,
    tbesg_entries: dict,
    book_label: str = "John",
    book_code: str = "john",
    book_tag: str = "book/john",
    chapter: int = 1,
    default_theme: str = "theme/christ",
) -> tuple[str, list[str]]:
    """Render one complete deterministic NT verse entry markdown."""
    v = verse["verse"]
    raw = verse["text"]
    text = clean_verse_text(raw)
    codes, occurrences_map, skipped = verse_codes(raw)
    if skipped:
        raise ValueError(
            f"{book_label} {chapter}:{v} contains non-canonical Greek codes {skipped}"
        )

    missing = [c for c in codes if c not in greek_lexicon]
    if missing:
        raise ValueError(
            f"{book_label} {chapter}:{v}: codes missing from strongs-lexicon.json: {missing}"
        )

    tags = [
        "material/bible",
        book_tag,
        default_theme,
        "translation/kjv",
        "lang/greek",
    ] + [f"strongs-{c}" for c in sorted(codes)]

    fm = "\n".join([
        "---",
        f"id: {book_code}-{chapter}-{v}-kjv",
        "type: material/bible",
        f"book: {book_tag}",
        f'passage: "{book_label} {chapter}:{v}"',
        "tags:",
        *(f"  - {t}" for t in tags),
        "source: source/bible",
        "language: greek",
        "translation: kjv",
        "level: intro",
        "status: draft",
        f"created: {GENERATION_DATE}",
        f"updated: {GENERATION_DATE}",
        "---",
    ])

    block_lines = [
        word_study_block(c, occurrences_map[c], greek_lexicon, tbesg_entries) + "\n"
        for c in sorted(codes)
    ]
    src_notes = [
        "- Verse text and Strong's tags are extracted verbatim from the pinned",
        "  tagged KJV (scrollmapper KJV-osis; see data/PROVENANCE.md).",
        "- Word-study facts come from lexicons/strongs-lexicon.json (Strong's Greek,",
        "  public domain) and lexicons/tbesg-glosses.json (STEPBible, CC BY 4.0 —",
        "  supplementary modern glosses).",
        "- Status: draft. Deterministic skeleton only — cross-references and",
        "  theological notes await human curation per CONTRIBUTION_STANDARDS.md.",
        "",
    ]

    body = "\n".join([
        "",
        f"# {book_label} {chapter}:{v} - KJV",
        "",
        f"> {text}",
        "",
        "## Greek Word Study",
        "",
        *block_lines,
        "## Source Notes",
        "",
        *src_notes,
    ])

    return fm + "\n" + body, codes


def generate(
    repo: str = ".",
    out_subdir: str | None = None,
    book_label: str = "John",
    book_code: str = "john",
    book_tag: str = "book/john",
    chapter: int = 1,
    verses: tuple[int, int] | None = None,
    default_theme: str = "theme/christ",
    sources: tuple[dict, dict, dict, dict] | None = None,
) -> list[str]:
    """Generate entries for one NT chapter. Returns list of written file paths."""
    from search.corpus.bible_books import get_book_info

    kjv, greek_lexicon, tbesg_entries, canonical = sources or load_pinned_sources(repo)
    canon_g = set(canonical["greek"])

    # Locate the canonical book in KJV osis
    canonical_name = get_book_info(book_label).name
    book_entry = next(
        (b for b in kjv.get("books", []) if b["name"].lower() == canonical_name.lower()),
        None,
    )
    if book_entry is None:
        raise ValueError(f"Book '{book_label}' ({canonical_name}) not found in KJV-osis source")

    ch_entry = next(
        (c for c in book_entry.get("chapters", []) if c["chapter"] == chapter),
        None,
    )
    if ch_entry is None:
        raise ValueError(f"{canonical_name} chapter {chapter} not found in KJV-osis source")

    verses_map = {v["verse"]: v for v in ch_entry.get("verses", [])}
    if not verses_map:
        raise ValueError(f"{canonical_name} chapter {chapter} contains no verses in KJV-osis source")
    if verses is None:
        start, end = 1, max(verses_map.keys())
    else:
        start, end = verses
        if start > end or start < 1:
            raise ValueError(f"Invalid verse range {start}-{end} for {canonical_name} {chapter}")

    target_subdir = out_subdir or f"materials/bible/nt/{book_code}"
    out_dir = Path(repo) / target_subdir / f"{chapter:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for v in range(start, end + 1):
        verse = verses_map.get(v)
        if verse is None:
            raise ValueError(f"{canonical_name} {chapter}:{v} missing from pinned KJV-osis source")
        md, codes = build_entry_markdown(
            verse,
            greek_lexicon,
            tbesg_entries,
            book_label=canonical_name,
            book_code=book_code,
            book_tag=book_tag,
            chapter=chapter,
            default_theme=default_theme,
        )
        bad = [c for c in codes if c not in canon_g]
        if bad:
            raise ValueError(f"{canonical_name} {chapter}:{v}: tags outside canonical list: {bad}")
        path = out_dir / f"{book_code}-{chapter}-{v}-kjv.md"
        path.write_text(md, encoding="utf-8")
        written.append(str(path))
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate New Testament chapter draft entries (deterministic skeletons)"
    )
    parser.add_argument("--repo", default=".", help="Repository root (default: .)")
    parser.add_argument("--book", default="John", help="Book name (default: John)")
    parser.add_argument("--book-code", default="john", help="Book id prefix (default: john)")
    parser.add_argument("--chapter", type=int, default=1, help="Chapter number (default: 1)")
    parser.add_argument(
        "--verses",
        default=None,
        help="Verse range 'start-end' (e.g. 1-51) or single verse (e.g. 1); default is full chapter",
    )
    parser.add_argument("--theme", default="theme/christ", help="Default theme tag")
    args = parser.parse_args(argv)

    v_range = None
    if args.verses:
        if "-" in args.verses:
            s, e = args.verses.split("-", 1)
            v_range = (int(s), int(e))
        else:
            v = int(args.verses)
            v_range = (v, v)

    written = generate(
        repo=args.repo,
        out_subdir=f"materials/bible/nt/{args.book_code}",
        book_label=args.book,
        book_code=args.book_code,
        book_tag=f"book/{args.book_code}",
        chapter=args.chapter,
        verses=v_range,
        default_theme=args.theme,
    )
    print(f"Generated {len(written)} NT entries for {args.book} {args.chapter}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
