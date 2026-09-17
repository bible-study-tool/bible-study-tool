# WP-001 (DONE) — Curate Genesis 1:4-5 (Day 1 completion)

status: complete
scope: gen-1-4-kjv.md, gen-1-5-kjv.md (both `status: draft`)
priority: high

## Objective

Move Genesis 1:4-5 from verified skeleton to `status: review`: cross-
references, study notes, and theological connections added; AI-assisted
drafts marked; the deterministic skeleton untouched. Completes the Day 1
unit with the already-curated v1-3.

## Inputs (read these first)

- Entries: `materials/bible/ot/genesis/gen-1-4-kjv.md`, `gen-1-5-kjv.md`
  (skeletons: verse text, Strong's tags, word studies with Strong's
  definition + TBESH modern gloss + morphology)
- Apparatus rows: `correlations/apparatus-genesis1.json` -> verses "4", "5"
  (which Hebrew words the English hides — e.g. Gen 1:4 has an untagged
  object-marker pattern around "the light")
- Gloss side-by-side: `correlations/agreement-ledger.json` ->
  comparisons.lexicon_gloss, keys H216, H2822, H2896, H3588, H430, H7200,
  H853, H914, H996, H1961 (v5)
- Curated neighbors: `gen-1-1-kjv.md` .. `gen-1-3-kjv.md` (style + depth
  reference; they are `status: review`)
- Schema/conventions: `kc-schema.md`, `CONTRIBUTION_STANDARDS.md`,
  `NOTICE.md` (doctrinal basis)

## Tasks

- [ ] For each entry: add `cross_references` (use xref/ types from the
      taxonomy; targets may be forward references — F3 treats them as
      warnings, not errors). Candidate material: John 1:4-5 (light/darkness),
      2 Corinthians 4:6, 1 John 1:5; day-name study for v5.
- [ ] Add a `## Study Notes` section: interpretive observations (e.g. the
      first naming in Scripture; "evening and morning" as the day boundary —
      relevant to the biblical sunset-to-sunset day).
- [ ] Where content is AI-assisted: wrap in `<!-- AI-GENERATED -->` ...
      `<!-- END AI-GENERATED -->` and add `ai/insight` tag per standards.
- [ ] Set `status: review` and `updated: <today>` in both frontmatters.
- [ ] Human review of the added content (per CONTRIBUTION_STANDARDS Review
      Workflow) — record reviewer in the package Notes.

## Conventions that apply

- AGENTS.md non-negotiables 1 (AI marking), 4 (skeleton untouched), 8 (ADR if
  a decision emerges, e.g. day-boundary interpretation policy).
- Theologically: present interpretive options with nuance (see NOTICE.md);
  Adventist framework per NOTICE.md.

## Acceptance criteria

- [ ] `bash scripts/verify_all.sh` green (F1 schema passes with the new
      frontmatter; F3 cross-refs well-formed).
- [ ] Both entries `status: review`; AI blocks marked; skeleton fields
      (verse text, tags) byte-identical to the committed drafts except
      status/updated.
- [ ] Human review recorded in this file's Notes.

## Notes / findings

(appended during work)
