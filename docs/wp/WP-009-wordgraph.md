# WP-009: Build the WordGraph lexical knowledge graph for Genesis (ADR-0010)

status: open
scope: wordgraph-genesis.json (Genesis 1-2) — the lemma-centric spine + aggregate-first dictionary
priority: high

## Objective

Build the first WordGraph artifact per ADR-0010: a deterministic, lemma-centric
lexical knowledge graph over Genesis 1-2 that links every word token to a
lexeme entry carrying morphology, glosses, occurrence index, and cross-source
metadata — the substrate that (a) the WP-010 draft engine consumes to assemble
word-study blocks deterministically, and (b) later Macula/SDBH integration
enriches. After this package: `lexicons/wordgraph-genesis.json` exists, is
byte-identical under regeneration, is recorded in `data/PROVENANCE.md`, and
the existing artifacts (strongs-*, tbesh-*, morphology-*, apparatus-*, ledger)
are unchanged.

## Inputs (read these first)

- ADR-0010 (`docs/decisions/ADR-0010-wordgraph.md`) — the governing decision
  (three-layer identifier stack: token id / lexeme + homograph index / Strong's
  legacy crosswalk; aggregate-first dictionary; Strong's demoted to crosswalk).
- Existing artifacts (the graph CONSUMES these, never modifies):
  `lexicons/morphology-genesis1.json` + `morphology-genesis2.json` (token ids,
  WLC, morph, base, homonym `n` attr), `lexicons/strongs-list.json`,
  `lexicons/strongs-lexicon.json` (definitions, translit), `lexicons/tbesh-glosses.json`
  + `tbesg-glosses.json` (brief glosses), `correlations/agreement-ledger.json`
  (gloss side-by-sides + statuses), `correlations/apparatus-genesis1.json` +
  `apparatus-genesis2.json` (kjv-osis <-> oshb pairing).
- Conventions: AGENTS.md non-negotiables 4 (generated artifact, never
  hand-edited; artifact + PROVENANCE checksum committed together) and 5 (pins);
  `docs/WORKFLOW.md` Example 5.

## Tasks

- [ ] Design the `wordgraph-genesis` schema: per-lexeme records keyed by
      canonical lexeme id (OSHB base + homograph index), each carrying:
      - `lexeme` — canonical id (e.g. `H430` + homograph disambiguation where
        the OSHB `n` attribute or TBESH variant structure demands it)
      - `strongs` — the legacy crosswalk code(s)
      - `glosses` — verbatim Strong's definition + TBESH/TBESG gloss(es) +
        ledger status (agree/info/one-sided)
      - `morphology` — observed morph codes + counts (from the morphology
        artifacts)
      - `occurrences` — per-verse token index (book/chapter/verse, token ids,
        WLC forms) — the inverse index enabling "pull metadata per verse"
      - `attestation` — counts (verses, tokens)
      - `notes` — curated homograph notes (initially empty; grown through review)
- [ ] Write the generator `search/corpus/build_wordgraph.py` (deterministic;
      consumes the committed artifacts only — no raw `data/` dependency, so it
      also runs in CI).
- [ ] Handle homographs honestly: seed a minimal curated homograph list for the
      Genesis 1-2 lexemes where the OSHB `n` attribute (e.g. `1254 a` vs `1254
      b`) or TBESH variant records indicate distinct senses; document the
      convention in the artifact. This is a bounded, grown-through-review task —
      do NOT try to solve all homographs in this package.
- [ ] Generate `lexicons/wordgraph-genesis.json`; regenerate byte-identical
      test; add to the PROVENANCE inventory pin + checksum.
- [ ] Tests: schema shape, byte-identical regeneration, every token id in the
      morphology artifacts appears in the graph, every lexeme's Strong's code
      resolves in strongs-list.json, occurrences counts reconcile with the
      morphology artifacts, the graph contains no raw-source dependency.
- [ ] Subagent review (project-reviewer) — re-run generation, verify
      determinism + reconciliation, review the homograph convention.

## Conventions that apply

- AGENTS.md non-negotiables 4 + 5; ADR-0010 (three-layer stack; aggregate-first).
- Determinism: byte-identical regeneration; no hash-seed ordering.
- The WordGraph is GENERATED — never hand-edited; curated homograph notes live
  in a separate reviewed input (e.g. `lexicons/wordgraph-notes-genesis.json`,
  hand content) consumed by the generator, NOT edited in the artifact.
- Do NOT begin WP-010 (draft engine) in this package.

## Acceptance criteria

- [ ] `python -m pytest` green (report exact count; new tests included).
- [ ] `bash scripts/verify_all.sh` green — including the regeneration
      tripwire + PROVENANCE checksum gate (now 10 artifacts).
- [ ] `lexicons/wordgraph-genesis.json` exists, regenerates byte-identically,
      schema documented; every token/lexeme reconciled against the source
      artifacts; homograph convention documented.
- [ ] Existing artifacts byte-identical (strongs/morphology/apparatus/ledger
      unchanged — the graph only consumes them).
- [ ] Subagent review passed; no TODO/FIXME; git status clean after commit.

## Notes / findings

(appended during work)