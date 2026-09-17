# C4 — Faceted/Filtered Querying (implementation plan)

Status: **approved — Phase 2 shipped**

See `ROADMAP.md` C4: *"Faceted/filtered querying — by book/theme/translation/language/status; clean query API."*
This is a structural plan only; no content generation, no dependencies, no changes to the deterministic core.

## Objective

Deliver a single, clean, reusable query API for the curated corpus supporting free-text + facet filtering
(book, theme, translation, language, status — and any other frontmatter tag), exposed through CLI and web surfaces.

## Why now (grounded facts)

- **The corpus exists**: `materials/bible/**/*.md` — 1,612 curated entries with structured frontmatter carrying all
  C4 facets (`status: review/approved/draft` = 157 review; `language` greek/hebrew; `translation` kjv/...; `book` 68;
  13 tag categories). Markdown is the source of truth (git-tracked, no DB required).
- **No unified faceted query exists today**:
  - `BibleDB.search` — FTS5 + book/testament filter only (`search/corpus/extract_kjv.py:370`)
  - `EgwDB.search` — FTS5 + book_code only (`search/linking/egw.py:631`)
  - `study_service.search_unified` — book_filter only (`search/ui/study_service.py:758`)
  - `index/semantic.db` / `dbindex` — 3 entries only (near-empty), so not a viable corpus-scale foundation
- Reads are now sidecar-free (ADR-027 §5); this work inherits that guarantee.

## Scope (this step)

- New module `search/corpus/query.py` with entry point
  `query(facets: dict[str, list[str]], text: str | None = None, limit: int = 50) -> list[dict]`
  - Each value in `facets` is an OR-set within a facet; facets combine by AND/intersection.
  - `text` optional free-text, spanning **all content** (`data/bible.db` verses, `data/egw.db`
    paragraphs, `materials/bible/**/*.md` entries); combined with facets via intersection (or standalone).
  - **Facets apply where structured data exists** — primarily `materials/bible` (it carries all
    C4 facets). `book` and `translation` are also derivable for `data/bible.db` verses; where a
    facet can't be computed for a source, it's simply absent from that result (never faked).
  - Returns results (id, passage, body, tags, source, …) — shape finalized at implementation.
- Surfaces that grow from it:
  - CLI: extend `bible-study search` with `--book`, `--theme`, `--translation`, `--language`, `--status`, `--text` flags.
  - Web: thin `/api/query` endpoint that delegates to the same API (Phase 1, see Decisions below).
- Facet filter set starts at the C5-facets list and is open-ended (any tag category works).

## Design (minimal, ADR-013 compliant)

- **Zero new dependencies.**
- **Backend**: SQLite in-memory, built once per process from parsed frontmatter of `materials/bible/**/*.md`.
  - Schema mirrors `index/semantic.db`'s proven pattern: entry rows + normalized `entry_tags` join table
    (book/genesis, theme/creation, …, status/review, …), plus passage + body text columns for FTS5.
  - FTS5 (`entries_fts`) over passage + body for free-text across sources; plain SQL WHERE/JOIN
    on `entry_tags` for facets; results from all sources merged by the API.
  - Read-only; material files are never modified.
- **Sidecar-free** by construction (no WAL-mode source DB touched).

## Phases

- **Phase 1 (this step)**: the API + CLI flags + thin web endpoint, acceptance-tested.
- **Phase 2 (later, out of scope here)**: per-DB verse/paragraph search integration
  (`BibleDB.search` / `EgwDB.search`) behind a unified backend.

## Explicit non-scope

- No content generation or AI (per the agreement: "no generation or anything").
- No embeddings (C1/C2).
- No `index/semantic.db` rebuild or corpus ingest changes.
- No curation status transitions — `status` is a filter, not a setter.

## Acceptance criteria (testable)

1. `query({"book": ["book/genesis"]})` returns only Genesis entries.
2. `query({"book": ["book/genesis"], "language": ["lang/greek"]})` returns the correct intersection
   (empty for Genesis — no Greek Genesis entries exist).
3. `query({"theme": ["theme/grace"]})` intersects correctly;
   `query({"text": "grace"}, {"theme": ["theme/grace"]})` returns grace-themed entries mentioning "grace".
4. `query({"status": ["status/review"]}, limit=10_000)` returns exactly the 157 review entries
   (no more, no fewer); default page size of 50 applies to calls without an explicit limit.
5. `query({"status": ["status/review"]})` creates **no** `data/*-wal`/`-shm` (sidecar-free guarantee).
6. CLI `bible-study search --book=book/genesis --theme=theme/grace` returns the same result set as the API for those facets.
7. Zero new dependencies (lockfile unchanged).
8. `scripts/verify_all.sh` (F6 content gate + full pytest) green.

## Decisions (from your answer; to confirm)

**Free-text — all content.** You confirmed free-text should cover everything:
`data/bible.db` verses, `data/egw.db` paragraphs, and `materials/bible/**/*.md` entries,
unified by one API. Implementation reuses the existing FTS5 engines
(`BibleDB.search`, `EgwDB.search`, and the `entries_fts` index); the API merges hits
from all three.

**Ranking** (my recommendation — replace if you disagree): when a user types words,
many things can match, so results need an order. I propose the same relevance scoring
the search already uses (FTS5 BM25 — a proven "how well do these words match" score),
i.e. most-relevant first. No new ordering to invent; if you prefer insertion/date order
for filtered (no-text) queries, say so.

**Web endpoint `/api/query`** (my recommendation — replace if you disagree): the web
UI is the primary face of the tool (ADR-024), and C4's value *shows up there* (the
interface already has filter dropdowns for prophecy symbols and cross-references — a
general facet surface is the natural next step). A thin endpoint that just forwards
`facets + text` to the API gives the web something real to render in Phase 1. No new
logic — it's a 1:1 pass-through. Deferring it to Phase 2 would mean C4 ships with no
web surface, which is the surface it's meant for.

## Phases

- **Phase 1 (this step)**: the API + CLI flags + thin web endpoint, acceptance-tested.
- **Phase 2**: per-DB verse/paragraph search integrated behind the unified backend
