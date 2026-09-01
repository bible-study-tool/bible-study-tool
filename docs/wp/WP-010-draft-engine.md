# WP-010: Deterministic word-study draft engine (ADR-0010, part 2)

status: open
scope: word-study block assembly from the WordGraph + integration into the skeleton generator
priority: high

## Objective

Build the draft engine: the deterministic assembler that produces the
word-study layer of a verse entry from the WordGraph (lexeme metadata,
morphology, occurrences, glosses) instead of LLM-drafting it per verse. After
this package: `search/corpus/draft_engine.py` (or the equivalent module)
consumes `lexicons/wordgraph-genesis.json` and emits the word-study blocks
byte-identically; the skeleton generator can be pointed at the engine; and a
new chapter's skeletons are generated with WordGraph-assembled word studies
(per ADR-0010 consequence: word studies drop from O(verses) LLM cost to
O(lexemes) deterministic assembly). This is the production half of the
"draft engine" idea: the LLM's role shrinks to the genuinely interpretive
layer (theological connections, summary prose) or disappears for routine
verses.

## Inputs (read these first)

- ADR-0010 (governing decision), WP-009 output (`lexicons/wordgraph-genesis.json`).
- Current skeleton generator `search/corpus/build_genesis1.py`
  (`word_study_block`, `build_entry_markdown`, `generate`) — the engine must
  slot in WITHOUT breaking Genesis 1 byte-identity.
- The existing word-study block format (consumed by
  `search.linking.loader._extract_words` and the wp_check skeleton invariance
  checks) — the engine's output must stay format-compatible.

## Tasks

- [ ] Design the engine: input = verse (book/chapter/verse) + WordGraph;
      output = the word-study block set for that verse (same `### <word> -
      Strong's <code>` format), assembled from the graph's per-lexeme records
      + the verse's token index. No LLM, no raw sources.
- [ ] Implement `draft_engine.py` (deterministic; consumes the graph + the
      verse's Strong's codes only).
- [ ] Integrate into `build_genesis1.py` behind a flag (e.g. `--draft-engine`)
      OR as the default for new chapters — with Genesis 1 output still
      byte-identical under the existing path. Decide + document (small ADR if
      it changes the word-study format).
- [ ] Generate a demo: Genesis 3 (next chapter) skeletons with the engine —
      OR regenerate Genesis 2 skeletons through the engine (tripwire-safe but
      noisier) — the decision is made in WP-010 Notes; the demo must show the
      engine's output is byte-stable and format-compatible.
- [ ] Tests: engine unit tests (synthetic verse -> expected blocks), golden
      test over the demo chapter, byte-identity of Genesis 1 unchanged,
      format-compat with the loader/wp_check.
- [ ] Subagent review (project-reviewer) — re-run the engine, verify
      determinism + format compatibility + Genesis 1 byte-identity.

## Conventions that apply

- AGENTS.md non-negotiables 4 + 2 (one step at a time — WP-008 curation begins
  only after this lands); ADR-0010.
- Determinism: byte-identical regeneration; no hash-seed ordering.
- The engine is GENERATED-output code; the graph is its only data input.
- Do NOT begin WP-008 curation in this package.

## Acceptance criteria

- [ ] `python -m pytest` green (report exact count); `bash scripts/verify_all.sh` green.
- [ ] Engine output for the demo chapter is byte-stable + format-compatible
      (loader + wp_check accept it); Genesis 1 output byte-identical.
- [ ] Word-study blocks carry WordGraph provenance (the graph version they
      were assembled from) — so a graph change triggers a documented
      regeneration, not silent drift.
- [ ] Subagent review passed; no TODO/FIXME; git status clean after commit.

## Notes / findings

(appended during work)