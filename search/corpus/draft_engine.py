"""Deterministic word-study draft engine (WP-010, ADR-010).

Consumes the WordGraph (``lexicons/wordgraph-genesis.json``) and renders the
word-study block layer of a verse entry — the same ``### <word> - Strong's
<code>`` format produced by ``build_genesis1.word_study_block``, assembled
from the graph's per-lexeme ``word_study`` records instead of the raw
lexicons. No LLM, no raw data/ sources, no direct lexicon/TBESH access: the
graph is the engine's only data input (per ADR-010 consequence: word studies
drop from O(verses) LLM cost to O(lexemes) deterministic assembly).

The engine is a DROP-IN for ``word_study_block``: for the Genesis 1-2 verses
(which were generated from the raw lexicons), engine output is byte-identical
— pinned by the tests. New chapters generated via the engine carry a
WordGraph-provenance marker in the entry Source Notes (the graph version the
blocks were assembled from), so a graph change triggers a documented
regeneration, never silent drift.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

# The WordGraph artifact (version-scoped provenance marker).
_GRAPH_REL = "lexicons/wordgraph-genesis.json"

# Strong's code in a verse's tagged text — same shape the corpus generator
# parses (canonical unpadded form after int() normalization).
_LEMMA_RE = re.compile(r"strong:([HG])(\d{1,5})")


class DraftEngine:
    """Loads the WordGraph once and renders word-study blocks for verses."""

    def __init__(self, repo: str = "."):
        path = Path(repo) / _GRAPH_REL
        if not path.exists():
            raise FileNotFoundError(
                f"DraftEngine: WordGraph missing: {path} — run "
                "python -m search.corpus.build_wordgraph --repo . first"
            )
        self.graph = json.loads(path.read_text(encoding="utf-8"))
        version = self.graph.get("$schema")
        if not version:
            raise ValueError(
                f"DraftEngine: WordGraph {path} has no $schema — refusing to "
                "claim provenance from a malformed graph"
            )
        self.version = version
        self._by_id = {l["id"]: l for l in self.graph["lexemes"]}

    @property
    def provenance(self) -> str:
        """The WordGraph version the engine assembles from (for Source Notes)."""
        return self.version

    def word_study_block(self, code: str, occurrences: int) -> str:
        """Render one '### <word> - Strong's <code>' block from the graph.

        Format-compatible with build_genesis1.word_study_block (the loader's
        _extract_words and wp_check's skeleton checks parse this shape).
        Raises KeyError if the code is not in the graph (fail-fast: a verse
        code outside the graph is a data error, never silently skipped).
        """
        record = self._by_id[code]["word_study"]
        translit = record["translit"]
        definition = record["definition"]
        gloss = record["gloss"]
        gloss_full = record["gloss_full"]
        morph = record["morph"]
        source_label = record["source_label"]

        title_word = translit or code
        title_gloss = f" ({gloss})" if gloss else ""
        lines = [f"### {title_word}{title_gloss} - Strong's {code}", ""]
        if translit:
            lines.append(f"*   Transliteration: {translit}")
        if definition:
            lines.append(f"*   Definition: {definition}")
        if gloss:
            lines.append(f"*   Modern Gloss ({source_label}): {gloss_full}")
        if morph:
            lines.append(f"*   Morphology (STEPBible): {morph}")
        lines.append(f"*   Lemma occurrences in this verse: {occurrences}")
        return "\n".join(lines)

    def verse_blocks(self, raw_verse_text: str, codes: list[str]) -> dict[str, str]:
        """Render the block set for a verse.

        ``codes``: the verse's distinct Strong's codes in the canonical
        generator order (see build_genesis1.verse_codes). Returns
        {code: block_markdown} — deterministic, sorted by the caller.
        """
        occ_map = Counter(
            f"{letter}{int(num)}"
            for letter, num in _LEMMA_RE.findall(raw_verse_text)
        )
        blocks = {}
        for code in codes:
            blocks[code] = self.word_study_block(code, occ_map[code])
        return blocks


def main(argv=None) -> int:
    """CLI smoke test: load the graph and report coverage."""
    import argparse
    parser = argparse.ArgumentParser(
        description="Draft engine — deterministic word-study assembly from the WordGraph"
    )
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    engine = DraftEngine(args.repo)
    print(f"DraftEngine ready: {engine.provenance}, "
          f"{len(engine._by_id)} lexemes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())