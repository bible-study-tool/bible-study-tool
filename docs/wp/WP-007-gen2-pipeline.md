# WP-007: Book-level pipeline generalization + Genesis 2 skeletons (ADR-009, part 1)

status: complete
scope: pipeline generalization (per ADR-009) + Genesis 2 skeleton generation (gen-2-1..25)
priority: high

## Objective

Generalize the deterministic generation pipeline from the Genesis-1-only
`build_genesis1.py` to a **book-level** generator (per ADR-009), then produce
the Genesis 2 skeletons (25 verses) as the pilot output. After this package:
`gen-2-1-kjv.md` .. `gen-2-25-kjv.md` exist as committed skeletons
(`status: draft`); `correlations/apparatus-genesis2.json` covers Gen 2:1-25;
`lexicons/morphology-genesis2.json` covers Gen 2:1-25; the agreement ledger's
`word_strongs` rows include Gen 2:1-25; the genesis1 artifacts remain
**byte-identical** (backward compatibility); `data/PROVENANCE.md` records the
new checksums; all regeneration tripwires + tests are green.

## Inputs (read these first)

- ADR-009 (`docs/decisions/ADR-009-corpus-expansion-model.md`) — the
  governing decision (whole-book generation; genesis1 artifacts stay
  byte-identical).
- Generator: `search/corpus/build_genesis1.py` (hardcoded: `ch1 = ... chapter == 1`,
  `for v in range(4, 32)`, filename `gen-1-{v}-kjv.md`) + `search/corpus/test_corpus.py`
- Morphology: `search/corpus/build_morphology.py` (`for chapter in (1,)`),
  `search/corpus/test_morphology.py` (asserts `counts.verses == 31`)
- Apparatus: `search/agreement/apparatus.py` (fact collection chapter-agnostic;
  output/schema embed "genesis1"), `search/agreement/test_apparatus.py`
- Ledger: `search/agreement/compare.py`, `search/agreement/test_compare.py`
- Raw sources: `data/KJV-osis.json`, OSHB XML for Genesis ch. 2 (gitignored;
  fetched via `scripts/fetch_sources.sh`)
- Checksum record: `data/PROVENANCE.md`
- Conventions: AGENTS.md non-negotiables 4 (regenerate, never hand-edit) and
  5 (pins); `docs/WORKFLOW.md` Example 5 (golden-baseline tripwire)

## Tasks

- [ ] Generalize the generator to book-level: parameterize by book (and
      chapter range) so `gen-{ch}-{v}-kjv.md` is produced for any Genesis
      chapter; keep `build_genesis1.py`'s output byte-identical for Genesis 1
      (regeneration tripwire must pass unchanged).
- [ ] Generate `gen-2-1-kjv.md` .. `gen-2-25-kjv.md` skeletons (verse text,
      Strong's tags, word-study blocks) — committed as `status: draft`.
- [ ] Extend the morphology builder to include Genesis 2:1-25; produce
      `lexicons/morphology-genesis2.json` (`counts.verses == 25`, byte-identical
      regeneration test).
- [ ] Build `correlations/apparatus-genesis2.json` for keys Gen.2.1..Gen.2.25
      (same alignment model as genesis1; schema `apparatus-genesis2/v1`).
- [ ] Extend the agreement ledger `word_strongs` comparison with rows
      Gen.2.1..Gen.2.25 (or record the scoping decision if the ledger stays
      chapter-1-scoped — see Notes).
- [ ] Update `data/PROVENANCE.md` checksums for every new artifact.
- [ ] Update/add tests: golden counts, byte-identical regeneration, tag
      canonicality for the 25 new entries; Genesis 1 regeneration unchanged.
- [ ] Subagent review (project-reviewer) — engineering step; review must
      re-run generation and verify determinism + Genesis-1 byte-identity.

## Conventions that apply

- AGENTS.md non-negotiables 4 (generated artifacts regenerated, never
  hand-edited; artifact + PROVENANCE checksum committed together) and 2 (one
  step at a time — do NOT begin WP-008 curation in this package).
- ADR-009 consequences: genesis1 artifacts stay byte-identical; artifact
  naming goes per-book.
- Determinism: byte-deterministic generators; no hash-seed ordering.

## Acceptance criteria

- [ ] `python -m pytest` green (report the exact count; existing tests
      updated for the new artifacts; Genesis-1 regeneration tests unchanged
      and passing).
- [ ] `bash scripts/verify_all.sh` green — regeneration tripwires +
      PROVENANCE checksum gate included.
- [ ] `gen-2-1..25-kjv.md` exist, `status: draft`, regenerate byte-identically.
- [ ] `correlations/apparatus-genesis2.json` present with exactly Gen.2.1..2.25.
- [ ] `lexicons/morphology-genesis2.json` present with `counts.verses == 25`.
- [ ] Ledger rows for Gen 2:1-25 (or the scoping decision documented).
- [ ] `data/PROVENANCE.md` checksums updated; artifact + checksum in one commit.
- [ ] Subagent review passed; no TODO/FIXME; git status clean after commit.

## Notes / findings

- Done 2026-09-01. All 25 Genesis 2 skeletons generated (status: draft);
  morphology-genesis2.json (25 verses/328 words), apparatus-genesis2.json
  (25 verses, 257 matched, 67 omissions, 3 additions), ledger extended with
  Gen 2 rows (chapters=(1,2)). PROVENANCE updated (9 artifacts).
- **Unpadded Strong's codes**: scrollmapper writes unpadded codes (H068, H01)
  across 9,257 verses of the whole file; Genesis 1 happened to be fully
  padded. Parsers normalize to canonical unpadded form via int() — no-op for
  already-canonical codes, so Genesis 1 output stays byte-identical.
  Documented in PROVENANCE caveat 2.
- **First apparatus additions** (Genesis 1 had zero): Gen 2:9 H6779
  periphrastic double-tag ("made... to grow"); Gen 2:21 H121 proper-name
  reading ("upon Adam" vs OSHB H120 "the man") + H5307 double-tag. Golden
  baseline reviewed and accepted (documented scrollmapper tagging quirks,
  pinned by tests).
- New omission function-words beyond Genesis 1: H3808, H4480, H413, H1931,
  H8033, H5048, H4100, H905 ("alone"), H120 ("the man" merged into H121 span).
- `python scripts/wp_check.py --wp WP-007` exits 1 ("no files resolved") —
  expected: WP-007 is an engineering package with no `status: review` scope;
  F1-F4 run green over all 56 entries inside verify_all.sh. (Noted for future
  reviewers.)
- Subagent review: PASS (188 tests, byte-identity of Genesis 1 verified
  against the old generator, all artifacts regenerate byte-identically). One
  should-fix applied (generate() now mkdirs the output dir).