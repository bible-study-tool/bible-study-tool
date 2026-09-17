# WP-002 (DONE) — Curate Genesis 1:6-8 (Day 2 — firmament, waters)

status: complete
scope: gen-1-6-kjv.md, gen-1-7-kjv.md, gen-1-8-kjv.md (all `status: review`)
priority: medium

## Objective

Move Day 2 verses to `status: review` on the model of WP-001.

## Inputs (read these first)

- Entries: `gen-1-6-kjv.md`, `gen-1-7-kjv.md`, `gen-1-8-kjv.md`
- Apparatus rows "6", "7", "8" (notable: scrollmapper omits H1961 x2 in v6-v8
  and H853/H996 in v7 — see the ledger word_strongs rows for the full
  picture; the raqiya study in v6-8 is the lexical centerpiece)
- Gloss side-by-side keys: H7549 (firmament), H8432, H4325, H914, H8145,
  H8064, H1242, H6153, H3117, H7121, H1961, H5921
- Curated reference: `gen-1-3-kjv.md` (naming pattern: "And God called...")

## Tasks

- [x] Cross-references: 2 Peter 3:5-7 (waters above/below), Psalm 148:4,
      Ezekiel 1:22-26 (firmament imagery), Proverbs 8:27-29.
- [x] Study notes: the raqiya (expanse) interpretation question — present
      views with nuance per NOTICE.md; waters above the firmament in Adventist
      reading (pre-Flood water canopy — a standard SDA creation-week
      exposition, cite as interpretation).
- [x] AI markers on AI-assisted blocks; `status: review`; `updated: 2026-09-01`.
- [x] Review recorded.

## Conventions that apply

Same as WP-001 (AGENTS.md 1, 4, 8; NOTICE.md nuance).

## Acceptance criteria

- [x] verify_all.sh green; three entries `status: review`; AI blocks marked;
      skeleton byte-identical except status/updated; review recorded.

## Notes / findings

- Fixed xref validator (`search/validation/xrefs.py`) to support numbered
  biblical book entry IDs (e.g. `2peter-3-5-7`, `1cor-13-1`) and passages
  (e.g. `2 Peter 3:5-7`) while continuing to reject malformed targets.
- Independent project-reviewer subagent ran 161 tests, F1-F4 validators,
  and source checksums: 0 errors, all checks passed. Output verdict: APPROVED.
