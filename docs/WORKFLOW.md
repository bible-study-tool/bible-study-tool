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
| Examples | `materials/**.md` you author, `lexicons/wordgraph-notes-*.json` (curated homographs) | `lexicons/*.json` (except `wordgraph-notes-*.json`), `correlations/{agreement-ledger,apparatus-*}.json`, `lexicons/wordgraph-*.json`, generated corpus entries |
| Changed by | humans (+ AI drafts, marked `<!-- AI-GENERATED -->`) | generators only — **never hand-edit** |
| Gated by | F1-F4 validators | byte-regeneration tripwires + PROVENANCE checksum gate |
| Failure remedy | fix the entry per the validator message | regenerate with the printed command; commit artifact + updated `data/PROVENANCE.md` checksum |

## Example 1 — Starting a session (fresh or returning)

```bash
# On a fresh clone or updated branch, initialize dependencies & environment:
./bootstrap.sh --data

# Ground truth: branch, tree state, roadmap status:
python scripts/status.py
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

> "That's a decision worth recording — draft ADR-008 for it and add it to
> the index."

The assistant writes `docs/decisions/ADR-008-<slug>.md` (Context → Decision
→ Consequences, under ~40 lines), adds it to `docs/decisions/INDEX.md`, and
it ships in the same commit as whatever it decided. Seeded examples:
ADR-001 (deterministic-vs-AI), ADR-007 (agreement-layer status policy).

## Example 4 — Curating a work package (the common case)

Work packages live in `docs/wp/` (index in `docs/wp/INDEX.md`). A package is
self-contained: it lists the verses, the files to edit, the data sources to
use, the conventions, and the acceptance criteria.

The streamlined curation cycle:

1. **Extract targeted context** (avoids reading raw multi-thousand-line JSONs):
   ```bash
   python scripts/curate_context.py --wp WP-011   # or --wp WP-003, --verses 1..24 --chapter 3
   ```
   The tool automatically resolves the target chapter and verse range from the
   work package's `scope:` line. It outputs a concise brief with KJV verse quotes,
   apparatus omissions/alignments, and lexical definitions.

2. **The WordGraph cost model (ADR-010 / WP-010) & Broad Scaffolding (ADR-011)**:
   Deterministic word-study blocks (`### <word> — Strong's <code>`) in entry
   skeletons are assembled directly from the WordGraph (`lexicons/wordgraph-genesis.json`)
   by the draft engine (`search/corpus/draft_engine.py`), NOT drafted by an LLM.
   Per ADR-011, draft skeletons for all 50 chapters of Genesis (all 1,533 verses)
   are already pre-generated in `materials/bible/ot/genesis/`. Curators never
   need to regenerate skeletons from scratch for Genesis; they simply open the
   existing draft files for the scoped verses. Skeletons carry WordGraph provenance
   (`wordgraph-genesis/v1`) in `## Source Notes`. Never modify deterministic blocks
   or verse quotes by hand.

   The curator (human or LLM assistant) authors **only the interpretive layer**:
   - `cross_references:` in YAML frontmatter (with valid taxonomy tags).
     Use canonical Spirit of Prophecy citation tokens where applicable (`egw:PP.57.1`).
     Query or verify passages via `python scripts/egw_lookup.py --token egw:PP.57.1`
     or search via `python scripts/egw_lookup.py --search "phrase"`.
   - `## Correlations`
   - `## Study Notes`

   Every AI-assisted block must be marked `<!-- AI-GENERATED -->` …
   `<!-- END AI-GENERATED -->`. Set `status: review` and `updated: <today>` in
   the YAML frontmatter. Promotion to `status: final` is reserved for human review.

3. **Pre-flight verify**:
   ```bash
   python scripts/wp_check.py --wp WP-011
   ```
   `wp_check.py` is chapter-aware across the entire book of Genesis. It
   deterministically validates frontmatter fields, AI comment tag balance,
   verbatim preservation of the deterministic skeleton (verse text quote and
   word-study blocks against pinned sources/WordGraph), and scoped F1-F4 schema
   rules in milliseconds.

4. **Artifact regeneration reference (PROVENANCE cross-link)**:
   Deterministic artifacts are never hand-edited. Full commands are documented
   in `data/PROVENANCE.md` ("How to reproduce"):
   - Morphology: `python -m search.corpus.build_morphology --repo . --chapters <N>`
   - Apparatus: `python -c "from search.agreement.apparatus import write_apparatus; write_apparatus('.', out_path='correlations/apparatus-genesis<N>.json', chapters=(<N>,))"`
   - WordGraph: `python -m search.corpus.build_wordgraph --repo .`
   - Draft skeletons: `python -m search.corpus.build_genesis1 --repo . --chapter <N> --verses <start>-<end> --draft-engine`
   - Curated homograph notes: `lexicons/wordgraph-notes-genesis.json` (hand content consumed by the WordGraph builder).

5. **Verify + review + commit**:
   ```bash
   bash scripts/verify_all.sh
   ```
   Run subagent review per `AGENTS.md` (mandatory for every substantive step),
   update the work package status, and commit per repo conventions.

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

## Example 7 — Portable Study Backup & Air-Gapped Migration (ADR-016)

The project provides an offline-first backup and migration engine:

```bash
# 1. Standard Study Backup (Databases + Personal Annotations):
python scripts/backup.py export -o data/study_backup.tar.gz

# 2. Complete Backup (Databases + Annotations + Raw BYOD Bookshelf):
python scripts/backup.py export --complete -o data/full_migration.tar.gz

# 3. Inspect archive manifest, modes, and database table statistics:
python scripts/backup.py inspect data/full_migration.tar.gz

# 4. Cryptographically verify SHA-256 integrity:
python scripts/backup.py verify data/full_migration.tar.gz

# 5. Restore onto an air-gapped system:
python scripts/backup.py restore data/full_migration.tar.gz --overwrite
```
