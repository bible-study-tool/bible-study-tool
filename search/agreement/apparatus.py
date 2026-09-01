"""Word-level apparatus: aligning source tokens verse-by-verse (S4).

Takes the S1 word_strongs facts (which agree or disagree as verse-level
MULTISETS) and aligns the actual tokens, producing
``correlations/apparatus-genesis1.json`` — the per-verse correspondence
table between kjv-osis (English spans) and oshb (Hebrew words):

  * ``matched``   — the same Strong's code attested by both sources; each
                    pair carries BOTH sides' detail (English span text and
                    WLC word, morph, stable id), so a reader can see which
                    Hebrew word an English phrase renders.
  * ``omissions`` — tokens present in oshb but UNTAGGED in kjv-osis: the 94
                    function words (object marker H853, 'all' H3605,
                    'between' H996, relatives H834/H3588, ...) that English
                    leaves untranslated and scrollmapper leaves untagged.
                    Each omission is concrete: WLC text, position, morph, id.
  * ``additions`` — tokens present in kjv-osis but absent in oshb (expected
                    zero for the pinned sources; the apparatus detects them
                    if a re-pin introduces any).

Alignment semantics (documented honestly):
  * Pairing is PER CODE by order of occurrence: the k-th occurrence of code X
    in kjv-osis pairs with the k-th occurrence in oshb. Matched pairs assert
    "same lexeme attested in this verse", NOT word-order correspondence
    (English and Hebrew word orders differ; e.g. 'God created' vs
    'bara elohim').
  * When counts differ, the surplus occurrences on the larger side become
    omissions/additions; WHICH occurrence is 'the matched one' is then
    approximate (first-with-first). The omissions themselves are exact.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from search.agreement.facts import (
    OSHB,
    collect_all,
    index_facts,
    FACT_WORD_STRONGS,
)


def _flatten_tokens(meta_words: list[dict], fields_map: dict[str, str]) -> list[dict]:
    """Shared token flattening: one record per Strong's-coded token, in
    document order. ``fields_map`` maps token-field -> word-meta-field (they
    differ, e.g. kjv 'text' is surfaced as 'span_text')."""
    tokens = []
    n = 0
    for w in meta_words:
        for code in w["codes"]:
            n += 1
            token = {"code": code, "word_i": w["i"], "token_i": n}
            for tok_key, word_key in fields_map.items():
                token[tok_key] = w[word_key]
            tokens.append(token)
    return tokens


def _tokens_kjv(fact: dict) -> list[dict]:
    """Flatten kjv-osis word detail into per-token records."""
    return _flatten_tokens(fact["meta"]["words"], {"span_text": "text"})


def _tokens_oshb(fact: dict) -> list[dict]:
    """Flatten oshb word detail into per-token records.

    Prefix-only words (null base) carry no Strong's code and are excluded —
    they contribute no token to the alignment or to the omissions.
    """
    return _flatten_tokens(
        fact["meta"]["words"], {"wlc": "text", "morph": "morph", "id": "id"}
    )


def align_verse(key: str, kjv_fact: dict, oshb_fact: dict) -> dict:
    """Align one verse's tokens between the two sources (order-free, per-code
    occurrence pairing). Returns the apparatus row."""
    kjv = _tokens_kjv(kjv_fact)
    oshb = _tokens_oshb(oshb_fact)

    by_code_kjv: dict[str, list[dict]] = {}
    for t in kjv:
        by_code_kjv.setdefault(t["code"], []).append(t)
    by_code_oshb: dict[str, list[dict]] = {}
    for t in oshb:
        by_code_oshb.setdefault(t["code"], []).append(t)

    matched, omissions, additions = [], [], []
    for code in sorted(set(by_code_kjv) | set(by_code_oshb)):
        a = by_code_kjv.get(code, [])
        b = by_code_oshb.get(code, [])
        common = min(len(a), len(b))
        for k in range(common):
            matched.append({"code": code, "kjv-osis": a[k], "oshb": b[k]})
        for t in b[common:]:
            omissions.append({"code": code, "oshb": t})
        for t in a[common:]:
            additions.append({"code": code, "kjv-osis": t})

    return {
        "key": key,
        "matched": matched,
        "omissions": omissions,
        "additions": additions,
        "counts": {
            "kjv_osis_tokens": len(kjv),
            "oshb_tokens": len(oshb),
            "matched": len(matched),
            "omissions": len(omissions),
            "additions": len(additions),
        },
    }


def _verse_sort_key(key: str) -> tuple[int, int]:
    """'Gen.1.16' -> (1, 16); chapter-aware so mixed-chapter builds sort
    correctly (Gen.1.9 before Gen.1.10, Gen.1.31 before Gen.2.1)."""
    _, ch, v = key.split(".")
    return (int(ch), int(v))


def build_apparatus(repo: str = ".", chapters: tuple[int, ...] = (1,)) -> dict:
    """Build the apparatus for the given Genesis chapters from the S1 fact
    layer. Default (1,) reproduces the seeded apparatus-genesis1.json."""
    idx = index_facts(collect_all(repo, chapters))[FACT_WORD_STRONGS]
    verses = []
    for key in sorted(idx, key=_verse_sort_key):
        readings = idx[key]
        verses.append(align_verse(key, readings["kjv-osis"], readings["oshb"]))

    # Prefix-only OSHB words (no Strong's number) are excluded from alignment;
    # the count is computed from the facts so the prose stays exact per scope.
    oshb_facts = collect_all(repo, chapters)[OSHB]
    n_prefix_only = sum(
        1
        for fact in oshb_facts
        for w in fact["meta"]["words"]
        if not w["codes"]
    )

    omissions_by_code = Counter(o["code"] for v in verses for o in v["omissions"])
    summary = {
        "verses": len(verses),
        "matched_tokens": sum(v["counts"]["matched"] for v in verses),
        "omissions": sum(v["counts"]["omissions"] for v in verses),
        "additions": sum(v["counts"]["additions"] for v in verses),
        "omissions_by_code": {
            code: n
            for code, n in sorted(
                omissions_by_code.items(), key=lambda kv: (-kv[1], kv[0])
            )
        },
    }

    label = "-".join(str(c) for c in chapters)
    return {
        "$schema": f"apparatus-genesis{label}/v1",
        "alignment": (
            "Order-free, per-code occurrence pairing (k-th occurrence of a "
            "code in kjv-osis pairs with the k-th in oshb). Matched pairs "
            "assert 'same lexeme attested in this verse', not word-order "
            "correspondence. Surplus occurrences become omissions/additions; "
            "the omissions themselves are exact. Excluded from alignment on "
            "both sides: tokens with no Strong's number "
            f"({n_prefix_only} OSHB prefix-only words in Genesis {label}) — "
            "counts and omissions cover coded tokens only. Quirk: scrollmapper "
            "sometimes merges the object marker H853 into a verb span (e.g. "
            "'created' carries H853+H1254), so matched H853 pairs show the "
            "verb's English span against the standalone Hebrew word et."
        ),
        "sources": {
            "kjv-osis": "scrollmapper tagged KJV (English spans; some lemmas merged)",
            "oshb": "Open Scriptures Hebrew Bible (Hebrew words; complete tagging)",
        },
        "summary": summary,
        "verses": verses,
    }


def write_apparatus(
    repo: str = ".",
    out_path: str | Path = "correlations/apparatus-genesis1.json",
    chapters: tuple[int, ...] = (1,),
) -> dict:
    apparatus = build_apparatus(repo, chapters)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(apparatus, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    s = apparatus["summary"]
    print(
        f"Wrote apparatus: {s['verses']} verses, {s['matched_tokens']} matched, "
        f"{s['omissions']} omissions, {s['additions']} additions -> {path}"
    )
    print(f"  omissions by code: {s['omissions_by_code']}")
    return apparatus


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the word-level apparatus for Genesis chapter(s)"
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--chapters", default="1",
        help="Comma-separated Genesis chapters (default: 1)",
    )
    parser.add_argument(
        "--out", default=None,
        help="Output path (default: correlations/apparatus-genesis{chapters}.json)",
    )
    args = parser.parse_args(argv)
    chapters = tuple(int(c) for c in args.chapters.split(","))
    label = "-".join(str(c) for c in chapters)
    out_path = args.out or f"correlations/apparatus-genesis{label}.json"
    write_apparatus(args.repo, out_path=out_path, chapters=chapters)
    return 0