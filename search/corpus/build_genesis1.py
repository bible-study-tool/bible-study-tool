"""Generate deterministic draft skeletons for Genesis chapters (book-level).

Everything emitted here is derived from pinned sources (data/PROVENANCE.md):

  * Verse text          — scrollmapper KJV-osis (public domain KJV), verbatim
                          after stripping the OSIS tagging markup.
  * Strong's tags       — the `lemma="strong:H####"` tokens of the same pinned
                          file (the verse's actual word-level attestation).
  * Word-study facts    — lexicons/strongs-lexicon.json (Strong's 1890, public
                          domain: word form, transliteration, definition) and
                          lexicons/tbesh-glosses.json (STEPBible CC BY 4.0,
                          supplementary: modern brief gloss + morphology).

Scope (per ADR-009): any Genesis chapter, e.g. chapter 1 verses 4-31
(generated; verses 1-3 are the hand-curated MVP entries, never touched) or
chapter 2 verses 1-25 (whole chapter, all generated).

What is deliberately NOT generated: cross-references, theological notes,
AI summaries, translation-comparison tables. Those require human curation
(CONTRIBUTION_STANDARDS.md review workflow) and would be AI-generated content
needing review. The result is a verified, complete, factual skeleton that a
curator can enrich.

Idempotence: output is a pure function of the pinned sources + the pinned
GENERATION_DATE constant, so regeneration is byte-identical. The
GENERATION_DATE stamps the pinned source state, not the wall-clock date —
new chapters generated from the same pinned sources carry the same stamp.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

# Pinned generation date: keeps regeneration byte-identical. Bump explicitly
# when regenerating after a source update (and record it in the MR).
GENERATION_DATE = "2026-08-28"

# Canonical Strong's bounds (must match lexicons/strongs-list.json; enforced
# by the tests). Used as a defensive pre-filter for lemma tokens.
_MAX_HEBREW = 8674
_MAX_GREEK = 5624

# OSIS markup of the scrollmapper KJV-osis file.
# NOTE: scrollmapper writes codes WITHOUT canonical zero-padding in places
# (e.g. H068 for H68, H01 for H1 — 9,257 verses across the file; Genesis 1
# happens to be fully padded like H0430). The numeric value is unambiguous,
# so codes are normalized to the canonical unpadded form at parse time
# (int() strips leading zeros, matching lexicons/strongs-list.json keys).
# Truly malformed attributes (no digits) still fail the attribute-count check.
_LEMMA_RE = re.compile(r"strong:([HG])(\d{1,5})")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
# KJV marginal/study apparatus: <note> elements (wrapping <catchWord> and
# <rdg>) are translator margin notes, NOT verse text — strip them whole
# BEFORE the generic tag-strip, or their inner text leaks into the quote.
_NOTE_RE = re.compile(r"<note\b[^>]*>.*?</note>", re.DOTALL)

_BOOK_RE = re.compile(r"^(H|G)(\d+)$")


def load_pinned_sources(repo: str = ".") -> tuple[dict, dict, dict, dict]:
    """Load (kjv_osis, strongs_lexicon, tbesh, canonical_list) pinned data.

    The Strong's lexicon payload nests entries under hebrew/greek keys; it is
    flattened here into a single {code: entry} map for lookup.
    """
    kjv = json.loads(Path(repo, "data/KJV-osis.json").read_text(encoding="utf-8"))
    lex_payload = json.loads(
        Path(repo, "lexicons/strongs-lexicon.json").read_text(encoding="utf-8")
    )
    lexicon = {**lex_payload.get("hebrew", {}), **lex_payload.get("greek", {})}
    tbesh = json.loads(
        Path(repo, "lexicons/tbesh-glosses.json").read_text(encoding="utf-8")
    )
    canonical = json.loads(
        Path(repo, "lexicons/strongs-list.json").read_text(encoding="utf-8")
    )
    return kjv, lexicon, tbesh, canonical


def clean_verse_text(raw: str) -> str:
    """Strip OSIS markup, keep inner text + punctuation, unescape entities.

    Kept: <w> word text and <transChange> (KJV supplied words such as 'it
    was' — part of the translation). Removed: <note> margin apparatus
    (whole element, inner text included), <milestone>/<chapter> markers,
    and all remaining tags.
    """
    text = _NOTE_RE.sub("", raw)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def verse_codes(raw_text: str) -> tuple[list[str], dict[str, int], list[str]]:
    """Distinct Strong's codes in a verse + per-code lemma counts + skipped.

    Returns (codes_in_first_seen_order, {code: lemma_token_count}, skipped).
    Multi-lemma words ('strong:H0853 strong:H07200') contribute every lemma.
    Codes outside the canonical enumeration are counted and skipped (defensive:
    the pinned KJV is expected to contain none).
    """
    seen: dict[str, int] = {}
    skipped: list[str] = []
    n_attributes = raw_text.count("strong:")
    for letter, num_s in _LEMMA_RE.findall(raw_text):
        num = int(num_s)
        # Canonical unpadded form (int() strips source leading zeros, e.g.
        # H0430 -> H430; H068 -> H68): matches lexicons/strongs-list.json
        # keys. A no-op for already-canonical codes, so regeneration of the
        # seeded Genesis-1 entries stays byte-identical.
        code = f"{letter}{num}"
        if (letter == "H" and num > _MAX_HEBREW) or (letter == "G" and num > _MAX_GREEK):
            skipped.append(code)
            continue
        seen.setdefault(code, 0)
        seen[code] += 1
    # Fail-fast against silent lemma drop: every 'strong:' attribute in the
    # verse must have been parsed (a future source writing unpadded 'strong:H1'
    # would otherwise vanish from tags and word studies without a trace).
    n_parsed = sum(1 for letter, num_s in _LEMMA_RE.findall(raw_text))
    if n_parsed + len(skipped) != n_attributes:
        raise ValueError(
            f"lemma parse mismatch: {n_attributes} 'strong:' attributes but "
            f"{n_parsed} parsed + {len(skipped)} skipped — source format "
            "changed; regenerate after review."
        )
    return list(seen), seen, skipped


def strongs_definition(lexicon_entry: dict) -> str:
    """Core definition line from a Strong's lexicon entry ('1. ...' line)."""
    desc = lexicon_entry.get("desc", "")
    for line in desc.splitlines():
        if re.match(r"^\d+\.", line.strip()):
            return line.strip()
    # Fallback: first line after the "Strong's Number ..." head, else head.
    lines = [ln.strip() for ln in desc.splitlines() if ln.strip()]
    if len(lines) > 1:
        return lines[1]
    return lines[0] if lines else ""


def _short_gloss(gloss: str) -> str:
    """First gloss segment for the word-study title (split on ';' / ':')."""
    for sep in (";", ":"):
        if sep in gloss:
            gloss = gloss.split(sep, 1)[0].strip()
    return gloss


def word_study_block(code: str, occurrences: int, lexicon: dict, tbesh: dict) -> str:
    """One '### word - Strong's CODE' block, MVP loader-compatible format.

    The '### <title> - Strong's H####' header and the 'Transliteration:' /
    'Definition:' bullet fields follow the convention parsed by
    search.linking.loader._extract_words so the linking pipeline picks these
    words up like the curated MVP entries.
    """
    lex_entry = lexicon.get(code, {})
    translit = lex_entry.get("translit", "")
    if not translit:
        tbesh_variants = tbesh.get("entries", {}).get(code, [])
        if tbesh_variants:
            translit = tbesh_variants[0].get("translit", "")
    title_word = translit or code
    definition = strongs_definition(lex_entry) if lex_entry else ""

    # Deterministic "primary record" convention: when a code has multiple
    # TBESH records (e.g. H226 sign/indicator), file-order [0] is used.
    tbesh_variants = tbesh.get("entries", {}).get(code, [])
    gloss = _short_gloss(tbesh_variants[0]["gloss"]) if tbesh_variants else ""
    morph = tbesh_variants[0].get("morph", "") if tbesh_variants else ""

    title_gloss = f" ({gloss})" if gloss else ""
    lines = [f"### {title_word}{title_gloss} - Strong's {code}", ""]
    if translit:
        lines.append(f"*   Transliteration: {translit}")
    if definition:
        lines.append(f"*   Definition: {definition}")
    if gloss:
        src = "TBESH" if code.startswith("H") else "TBESG"
        lines.append(f"*   Modern Gloss ({src}): {tbesh_variants[0]['gloss']}")
    if morph:
        lines.append(f"*   Morphology (STEPBible): {morph}")
    lines.append(f"*   Lemma occurrences in this verse: {occurrences}")
    return "\n".join(lines)


def build_entry_markdown(
    verse: dict,
    lexicon: dict,
    tbesh: dict,
    book_label: str = "Genesis",
    book_code: str = "gen",
    book_tag: str = "book/genesis",
    chapter: int = 1,
    engine=None,
) -> tuple[str, list[str]]:
    """Render one entry. Returns (markdown, codes); raises if any code is
    missing from both lexicons (a fact we must not fabricate).

    ``book_code`` is the filename/id prefix (e.g. 'gen'); ``book_tag`` is the
    taxonomy book tag (e.g. 'book/genesis') — they differ and must stay
    separate. ``engine``: an optional draft-engine instance (WP-010); when
    given, word-study blocks are assembled from the WordGraph and the Source
    Notes carry the graph provenance. Default (None) keeps the legacy
    word_study_block path — Genesis 1-2 byte-identity preserved.
    """
    v = verse["verse"]
    raw = verse["text"]
    text = clean_verse_text(raw)
    codes, occurrences_map, skipped = verse_codes(raw)
    if skipped:
        raise ValueError(
            f"{book_label} {chapter}:{v} contains non-canonical Strong's codes "
            f"{skipped} — source changed; regenerate after review."
        )

    # Facts check: every code must have a Strong's lexicon entry (definition).
    missing = [c for c in codes if c not in lexicon]
    if missing:
        raise ValueError(
            f"{book_label} {chapter}:{v}: codes missing from "
            f"strongs-lexicon.json: {missing}"
        )

    tags = ["material/bible", book_tag, "theme/creation", "theme/origins",
            "translation/kjv", "lang/hebrew"] + [f"strongs-{c}" for c in sorted(codes)]

    fm = "\n".join([
        "---",
        f"id: {book_code}-{chapter}-{v}-kjv",
        "type: material/bible",
        f"book: {book_tag}",
        f'passage: "{book_label} {chapter}:{v}"',
        "tags:",
        *(f"  - {t}" for t in tags),
        "source: source/bible",
        "language: hebrew",
        "translation: kjv",
        "level: intro",
        "status: draft",
        f"created: {GENERATION_DATE}",
        f"updated: {GENERATION_DATE}",
        "---",
    ])

    if engine is not None:
        blocks = engine.verse_blocks(raw, codes)
        block_lines = [blocks[c] + "\n" for c in sorted(codes)]
        src_notes = [
            "- Verse text and Strong's tags are extracted verbatim from the pinned",
            "  tagged KJV (scrollmapper KJV-osis; see data/PROVENANCE.md).",
            f"- Word-study blocks assembled deterministically from the WordGraph",
            f"  ({engine.provenance}; see lexicons/wordgraph-genesis.json) —",
            "  generated, never hand-edited.",
            "- Status: draft. Deterministic skeleton only — cross-references and",
            "  theological notes await human curation per CONTRIBUTION_STANDARDS.md.",
            "",
        ]
    else:
        block_lines = [
            word_study_block(c, occurrences_map[c], lexicon, tbesh) + "\n"
            for c in sorted(codes)
        ]
        src_notes = [
            "- Verse text and Strong's tags are extracted verbatim from the pinned",
            "  tagged KJV (scrollmapper KJV-osis; see data/PROVENANCE.md).",
            "- Word-study facts come from lexicons/strongs-lexicon.json (Strong's,",
            "  public domain) and lexicons/tbesh-glosses.json (STEPBible, CC BY 4.0 —",
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
        "## Hebrew Word Study",
        "",
        *block_lines,
        "## Source Notes",
        "",
        *src_notes,
    ])

    return fm + "\n" + body, codes


def generate(
    repo: str = ".",
    out_subdir: str = "materials/bible/ot/genesis",
    book_label: str = "Genesis",
    book_code: str = "gen",
    book_tag: str = "book/genesis",
    chapter: int = 1,
    verses: tuple[int, int] = (4, 31),
    engine=None,
) -> list[str]:
    """Generate entries for one Genesis chapter. Returns written paths.

    Defaults reproduce the Genesis 1:4-31 MVP output byte-for-byte. The
    canonical list is authoritative: refuse to emit tags outside it.
    ``engine`` (optional): draft-engine instance (WP-010) — when given,
    word-study blocks are assembled from the WordGraph.
    """
    kjv, lexicon, tbesh, canonical = load_pinned_sources(repo)

    canon_h, canon_g = set(canonical["hebrew"]), set(canonical["greek"])

    gen = next(b for b in kjv["books"] if b["name"] == "Genesis")
    ch = next(c for c in gen["chapters"] if c["chapter"] == chapter)
    verses_map = {v["verse"]: v for v in ch["verses"]}

    written: list[str] = []
    out_dir = Path(repo) / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    start, end = verses
    ch_dir = out_dir / f"{chapter:02d}"
    ch_dir.mkdir(parents=True, exist_ok=True)
    for v in range(start, end + 1):
        verse = verses_map.get(v)
        if verse is None:
            raise ValueError(f"Genesis {chapter}:{v} missing from pinned KJV-osis source")
        md, codes = build_entry_markdown(
            verse, lexicon, tbesh,
            book_label=book_label, book_code=book_code, book_tag=book_tag,
            chapter=chapter, engine=engine,
        )
        bad = [c for c in codes if c not in canon_h and c not in canon_g]
        if bad:
            raise ValueError(f"Genesis {chapter}:{v}: tags outside canonical list: {bad}")
        path = ch_dir / f"{book_code}-{chapter}-{v}-kjv.md"
        path.write_text(md, encoding="utf-8")
        written.append(str(path))
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Genesis chapter draft entries (deterministic skeletons)"
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--book", default="Genesis", help="Book label (default: Genesis)")
    parser.add_argument("--book-code", default="gen", help="Book id code (default: gen)")
    parser.add_argument("--book-tag", default="book/genesis", help="Taxonomy book tag (default: book/genesis)")
    parser.add_argument("--chapter", type=int, default=1)
    parser.add_argument(
        "--verses", default="4-31",
        help="Verse range as START-END (default 4-31; use 1-25 for a whole chapter)",
    )
    parser.add_argument(
        "--draft-engine", action="store_true",
        help="Assemble word-study blocks from the WordGraph (WP-010) instead of "
             "the raw lexicons",
    )
    args = parser.parse_args(argv)
    start_s, _, end_s = args.verses.partition("-")
    verses = (int(start_s), int(end_s))
    engine = None
    if args.draft_engine:
        from search.corpus.draft_engine import DraftEngine
        engine = DraftEngine(args.repo)
    written = generate(
        args.repo,
        book_label=args.book,
        book_code=args.book_code,
        book_tag=args.book_tag,
        chapter=args.chapter,
        verses=verses,
        engine=engine,
    )
    print(
        f"Wrote {len(written)} entries (Genesis {args.chapter}:{args.verses}) — "
        "deterministic draft skeletons"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
