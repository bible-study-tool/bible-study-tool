# AGENTS.md — Project Charter

**Adventist Bible Study Tool** — a deterministic, offline-first knowledge base
for in-depth Bible study (SDA framework), where every fact is pinned, verified,
and reproducible. Full workflow with examples: `docs/WORKFLOW.md` (read it
before your first task).

## Non-negotiables

1. **Deterministic core is the source of truth.** AI output is provisional,
   marked `<!-- AI-GENERATED -->`, and gated behind human review. Never let AI
   content enter `correlations/semantic-links.json` or curated entries without
   review status.
2. **One step at a time.** Implement → verify → **subagent review of every
   substantive step** → commit → regroup with the user. Never batch steps.
3. **Fail fast, never silently accept.** Bad data raises; generators never
   "repair" source data; parsers reject unrecognized shapes.
4. **Generated artifacts are never hand-edited.** `lexicons/*.json`,
   `correlations/agreement-ledger.json`, `correlations/apparatus-*.json`,
   generated corpus entries — regenerate with the documented command, commit
   artifact + updated `data/PROVENANCE.md` checksum together.
5. **Pin everything.** Third-party sources get upstream commit pins + SHA-256
   in `data/PROVENANCE.md`; fetched via `scripts/fetch_sources.sh` (raw data
   is gitignored; only derived, attributed artifacts are committed).
6. **Data integrity precedes scale.** Validators (F1-F4) and tripwires gate
   every change; CI = `python -m pytest` + validators.
7. **Commit style:** `type(scope): summary` with a body that states what and
   why. **Accurate counts only** — verify test counts before writing them.
8. **Big decision made? Write an ADR** (`docs/decisions/`) — ask the current
   assistant to draft it if you're mid-conversation. Undocumented decisions
   rot.
9. **Do the best without being wasteful (ADR-0013).** We build for God. We
   reject shortsighted toy solutions that do not scale to the whole Bible
   (66 books, ~31,102 verses) or full commentary corpuses, and we reject
   bloated enterprise overkill with unneeded dependencies. We stand on the
   shoulders of open-source giants: study, incorporate, adapt, and attribute
   generously.

## Session workflow (always)

1. **Start:** `python scripts/status.py` — ground truth, not memory. Read
   `ROADMAP.md` (state + plan) and the open work package in `docs/wp/`.
2. **Work:** one package/step at a time per Non-negotiable 2. Data questions
   are answered from the pinned artifacts (lexicons/, apparatus, ledger), not
   from memory.
3. **Close:** `bash scripts/verify_all.sh` → must be green. Commit per style.
   Update ROADMAP checkboxes and the work package status.
4. **Regroup with the user** after each step before starting the next.

## Where things live

| What | Where |
| --- | --- |
| State + plan | `ROADMAP.md` |
| Session briefing | `python scripts/status.py` |
| Source lineage + pins | `data/PROVENANCE.md` |
| Decision rationale | `docs/decisions/` (INDEX.md) |
| Rules for contributions | `CONTRIBUTION_STANDARDS.md`, `NOTICE.md`, `kc-schema.md` |
| Work packages | `docs/wp/` (INDEX.md) |
| Doctrinal basis | `NOTICE.md` |
| Full workflow + examples | `docs/WORKFLOW.md` |
