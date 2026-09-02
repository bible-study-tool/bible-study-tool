# Next Session Handoff

**Written:** 2026-09-01 (end of the Genesis-1-to-Genesis-2 completion session)
**Repo state:** `master` at `add6ee5`, clean, pushed to GitLab
**Next step:** WP-011 — Curate Genesis 3 (the Fall)

## Where we are

The MVP (Genesis 1) and the first book-level expansion (Genesis 2) are
complete. The deterministic cost model is live: word-study blocks are
assembled from the WordGraph (ADR-0010) by the draft engine (WP-010), and
the LLM writes only the interpretive layer. Genesis 3 skeletons already exist
(engine-generated) and await curation.

## State summary

| Area | State |
|---|---|
| Corpus | Genesis 1-2 curated (56 entries, `status: review`); Genesis 3 skeletons (24, `status: draft`) |
| Pipeline | Book-level (ADR-0009); any Genesis chapter generatable |
| WordGraph | `lexicons/wordgraph-genesis.json` — 251 lexemes, chapters 1-3 (ADR-0010) |
| Draft engine | `search/corpus/draft_engine.py` + `--draft-engine` flag (WP-010) |
| Validators | F1-F4 + PROVENANCE gate + regeneration tripwires; **214 tests** |
| CI | Green (clone-safe test suite); GitLab pipelines now pass |
| ADRs | ADR-0001..0010 (0008 Proposed; 0009/0010 Accepted) |

## Work packages (docs/wp/INDEX.md)

- **WP-011 (open, next)** — Curate Genesis 3 (the Fall): `docs/wp/WP-011-gen3-fall.md`
- WP-001..010 all `done`
- Future: WP-012 (Genesis 4), then continue chapter by chapter (ADR-0009)

## Commands the next session needs

```bash
python scripts/status.py                          # ground truth
python scripts/curate_context.py --verses 1..24 --chapter 3   # curation briefing
python scripts/wp_check.py --wp WP-011            # pre-flight (chapter-aware)
bash scripts/verify_all.sh                        # full gate (214+ tests)
python -m pytest                                  # explicit test count
```

## ⚠️ Workflow review (requested by the user)

The next session must **review the workflow with the new tools and
infrastructure** before starting WP-011. Since the WordGraph + draft engine
(WP-009/010) landed, the curation workflow has new moving parts. Audit and
update `docs/WORKFLOW.md` (and `AGENTS.md` if needed) to reflect:

1. **The new cost model** — word-study blocks are now assembled from the
   WordGraph by the draft engine, NOT LLM-drafted. The curation cycle in
   `WORKFLOW.md` Example 4 ("Curating a work package") still describes the
   old per-verse drafting; update it to say the LLM writes only Correlations +
   Study Notes, and skeletons carry WordGraph provenance.
2. **wp_check is now chapter-aware** — `wp_check.py` was fixed (was silently
   skipping chapter 2+ skeleton checks). Document that `--wp WP-0XX` now
   genuinely verifies skeletons for any chapter.
3. **`curate_context.py` has a WP-scope quirk** — `--wp WP-008` resolved to
   chapter 1 (the WP-scope regex ignores the chapter). Workaround:
   `--verses 1..24 --chapter 3`. Consider fixing the tool (or documenting the
   workaround) — flagged, not yet done.
4. **New commands** — the draft-engine flag, the WordGraph regen command, the
   morphology/apparatus per-chapter commands are in `data/PROVENANCE.md`
   "How to reproduce"; cross-link from WORKFLOW.
5. **WordGraph notes file** — `lexicons/wordgraph-notes-genesis.json` is hand
   content (homograph candidates); document how it's edited and consumed.
6. **Genesis 3 is the first engine-generated curation** — treat it as the
   validation case for the whole cost model; the WP-011 Notes should record
   whether the engine skeletons held up under curation.

## Known minor issues (deferred)

- `curate_context.py` WP-scope chapter quirk (see above).
- `docs/wp/INDEX.md` header still says "Scope (Gen 1)" and "grouped by
  creation day" — now it's per-chapter; refresh the prose.
- ROADMAP `status.py` "next: A3" wording predates the A2 redefinition —
  A2 (complete Genesis) is the actual next pillar step.

## Next-session opening checklist

1. Read this file, then `python scripts/status.py`.
2. Do the **workflow review** (above) — update `docs/WORKFLOW.md`, decide on
   the `curate_context.py` fix, commit it.
3. Start WP-011 (Genesis 3 curation) — the full implement → verify →
   subagent-review → commit cycle.
4. Regroup with the user after each step.
