# Workflow — how work actually happens here

This document is the **explicit, exemplified guide** to the project's working
method. `AGENTS.md` is the thin charter; this is the "how". Every example
below uses real commands and real paths from this repo.

## The mental model

```
Session start ──► status.py (ground truth) ──► pick ONE work package/step
      ▲                                              │
      │                                              ▼
      │                                    implement (small, verifiable)
      │                                              │
      │                                              ▼
      └── regroup with user ◄── subagent review ◄── verify (verify_all.sh)
                                                     │
                                                     ▼
                                            commit (accurate counts)
```

Two file classes rule everything else:

| | Hand content | Generated artifacts |
| --- | --- | --- |
| Examples | `materials/**.md` you author | `lexicons/*.json`, `correlations/{agreement-ledger,apparatus-*}.json`, generated corpus entries |
| Changed by | humans (+ AI drafts, marked `<!-- AI-GENERATED -->`) | generators only — **never hand-edit** |
| Gated by | F1-F4 validators | byte-regeneration tripwires + PROVENANCE checksum gate |
| Failure remedy | fix the entry per the validator message | regenerate with the printed command; commit artifact + updated `data/PROVENANCE.md` checksum |

## Example 1 — Starting a session (fresh or returning)

```bash
python scripts/status.py        # ground truth: branch, tree state, roadmap
```

Then read, in this order: the current phase in `ROADMAP.md`, the open work
package in `docs/wp/` (if working from one), and — only if a decision is
unclear — the relevant ADR in `docs/decisions/`. Do **not** rely on chat
memory; `status.py` + ROADMAP are the source of truth. If the tree is DIRTY
from a previous session, resolve that first (commit or restore).

## Example 2 — Doing a step (implement → verify → review → commit)

1. **Implement** one verifiable step (a generator, a validator, one work
   package's curation). Keep it small enough that a reviewer can re-derive
   everything.
2. **Verify locally:**

   ```bash
   python -m pytest                                   # the suite
   python -m search.validation.schema --repo .        # F1 (etc.)
   bash scripts/verify_all.sh                         # everything, with remedies
   ```

3. **Subagent review** — mandatory for every substantive step. Invoke the
   project reviewer subagent (`.opencode/agent/project-reviewer.md`) with a
   short brief: *what changed, which claims to verify, which raw data to
   spot-check*. The reviewer re-runs commands and checks conventions
   independently; never accept "looks good" without evidence.
4. **Fix findings** and re-verify. Findings are prioritized: Bugs/must-fix →
   Should-fix → Minor. Apply must-fixes before committing; should-fixes
   usually ride along.
5. **Commit**, style: `type(scope): summary` + body stating what and why.
   **Counts must be verified** (run the suite, read the number). Examples:

   ```
   feat(corpus): complete Genesis 1 — 28 deterministic draft entries (A1)
   fix(lexicon): restore canonical 8674/5624 totals + fix transliteration
   docs(roadmap): mark Phase 1 (F1-F4) complete
   ```

6. **Regroup with the user** before starting the next step.

## Example 3 — You made a big decision (write an ADR)

Any decision that is hard to reverse, shapes future work, or was genuinely
debated gets an ADR **at decision time**. If you're mid-conversation with an
assistant, the flow is literally:

> "That's a decision worth recording — draft ADR-0008 for it and add it to
> the index."

The assistant writes `docs/decisions/ADR-0008-<slug>.md` (Context → Decision
→ Consequences, under ~40 lines), adds it to `docs/decisions/INDEX.md`, and
it ships in the same commit as whatever it decided. Seeded examples:
ADR-0001 (deterministic-vs-AI), ADR-0007 (agreement-layer status policy).

## Example 4 — Curating a work package (the common case)

Work packages live in `docs/wp/` (index in `docs/wp/INDEX.md`). A package is
self-contained: it lists the verses, the files to edit, the data sources to
use, the conventions, and the acceptance criteria. A session doing curation
needs **only** AGENTS.md + the package file.

For each verse in the package (see `docs/wp/TEMPLATE.md` for the skeleton):

1. Read the generated draft (`materials/bible/ot/genesis/gen-1-N-kjv.md`,
   `status: draft`) and its supporting rows: the apparatus
   (`correlations/apparatus-genesis1.json`, which Hebrew words the English
   hides), the gloss side-by-side (`correlations/agreement-ledger.json`,
   lexicon_gloss section), and the lexicons.
2. Write the interpretive content: cross-references, study notes, theological
   connections (per `CONTRIBUTION_STANDARDS.md`). AI-assisted drafting is
   fine — **mark every AI-generated block** `<!-- AI-GENERATED -->` …
   `<!-- END AI-GENERATED -->`, set `status: review` when done, and leave
   promotion to `final` to human review.
3. Verify + review + commit per Example 2. Never edit the generated
   skeleton's deterministic parts (verse text, Strong's tags) by hand — if a
   fact is wrong, that's a source issue: fix the source, regenerate.

## Example 5 — A source was re-pinned (the golden-baseline tripwire)

If `data/` sources were updated and regenerated artifacts differ:

1. `scripts/verify_all.sh` fails on the ledger/apparatus/lexicon tripwires —
   **this is the review gate working**, not a build error.
2. Inspect the diff of the affected artifact FIRST: what changed upstream?
   Review new disagreements (`disagree` rows) before accepting them.
3. Regenerate, update the `data/PROVENANCE.md` checksum(s), and commit the
   artifact + checksum + source pin together, with the review noted in the
   commit body.

## Example 6 — CI fails on an MR

CI runs exactly what `verify_all.sh` runs locally. If it fails where your
local run passed, check for: a stale local artifact, a hash-seed ordering
difference (all generators are required to be byte-deterministic — that's a
bug, report it), or an uncommitted file. `git status` first, always.
