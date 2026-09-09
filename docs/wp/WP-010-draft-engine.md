# WP-010: Deterministic word-study draft engine (ADR-010, part 2)

status: done
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
(per ADR-010 consequence: word studies drop from O(verses) LLM cost to
O(lexemes) deterministic assembly). This is the production half of the
"draft engine" idea: the LLM's role shrinks to the genuinely interpretive
layer (theological connections, summary prose) or disappears for routine
verses.

## Inputs (read these first)

- ADR-010 (governing decision), WP-009 output (`lexicons/wordgraph-genesis.json`).
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
  only after this lands); ADR-010.
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

### Design (agreed with user 2026-09-01, before implementation)

- WordGraph extended with a `word_study` sub-record per lexeme (translit,
  definition, gloss short/full, morph, source_label) — the complete
  block-source, derived with the EXACT conventions of
  `build_genesis1.word_study_block`, so the engine consumes ONLY the graph
  (never the raw lexicons). User approved.
- Demo = **Genesis 3** (the WP-specified choice; the WordGraph scope was
  extended to chapters 1-3 to cover it — morphology-genesis3 +
  apparatus-genesis3 generated first).

### Implementation outcome (2026-09-01)

- `search/corpus/draft_engine.py`: DraftEngine (loads the graph, renders
  blocks, provenance = graph `$schema`, fail-fast on missing `$schema` and
  unknown codes); `verse_blocks` counts occurrences like `verse_codes`.
- `build_genesis1.py`: optional `engine` param on build_entry_markdown /
  generate / main (`--draft-engine`); engine path adds the WordGraph
  provenance marker to Source Notes; default path untouched (Genesis 1-2
  byte-identity preserved).
- **Drop-in proof**: engine output byte-identical to `word_study_block` for
  ALL 516 Genesis 1-2 blocks (pinned by test).
- **kjv-osis attestation merge**: the graph now merges apparatus additions
  into lexeme occurrences with an explicit per-passage `source` (oshb |
  kjv-osis | oshb+kjv-osis). Genuine kjv-only lexemes get
  `oshb_attested=false`; H121 'Adam' is OSHB-attested at Gen 3:17 AND
  kjv-osis-attested at Gen 2:21 (both recorded). Honesty rules updated.
  (Subagent must-fix: the earlier claim that H121 was kjv-only was FALSE —
  the additions are aligner misses; fixed by merging + recording truth.)
- Genesis 3 demo: 24 skeletons generated via `--draft-engine`, all
  `status: draft`, WordGraph provenance marker, byte-identical regeneration.
- Verification: 214 tests local (ALL CHECKS PASSED); 162 passed / 52 skipped
  in fresh clone; subagent review PASS after must-fix (kjv-only merge +
  honesty rules) and should-fixes (module-level imports, provenance
  fail-fast, _load message).
- `python scripts/wp_check.py --wp WP-010` is N/A (infra package, no
  `status: review` scope); format compatibility is covered by
  `test_engine_blocks_format_compatible` + the loader parsing test.