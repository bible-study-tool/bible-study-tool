# ADR-027: Content-Level Integrity Verification for SQLite Data Bundles

* **Status:** Accepted
* **Date:** 2026-09-16
* **Scope:** Pillar C (Search & Semantic Engine), Pillar P (Distribution)
* **Deciders:** Project Maintainer & Strategic Orchestrator
* **Consulted:** [ADR-005](ADR-005-data-integrity-precedes-scale.md) (Data Integrity Precedes Scale), [ADR-006](ADR-006-provenance-and-generated-artifacts.md) (Provenance & Pins), [ADR-014](ADR-014-whole-bible-macula-sqlite-architecture.md) (Macula SQLite Architecture), [ADR-024](ADR-024-gui-first-architecture-tui-as-mode.md) (GUI-First Architecture)
* **Informs:** WP-029 (zero-Python distribution packaging), data/INTEGRITY.json, scripts/verify_all.sh (F6), scripts/build_release_data.sh, scripts/build_release.sh

---

## Context

`data/bible.db` and `data/macula.db` were verified by **byte-level** SHA-256 pins committed in `data/SHA256SUMS` and the release-wide manifests. Byte-pinning assumes SQLite files are byte-reproducible given identical logical content.

Empirically they are **not**:

1. **Toolchain variance:** Different SQLite versions, `VACUUM` behaviors, or insertion orders produce different bytes for identical content. A content hash of `bible.db` matched byte-for-byte across two machines (same logical content) while the raw files differed.
2. **Verified divergence:** `macula.db` rebuilt on a VM from identically pinned sources (stale build code) diverged in **2,541 rows** of the `role_label` column (`"copula"`/`"prep"` vs the expanded `"copula"`/`"preposition"`). Byte checks would pass on the reference machine, but a user verifying a rebuilt bundle on another machine would see a *false failure* — or worse, trust diverged content.

Byte-pinning therefore fails both ways: it false-fails on honest rebuilds and cannot distinguish "different bytes" from "different content." Per [ADR-005](ADR-005-data-integrity-precedes-scale.md), verification exists so end users can trust that their local data carries correct references and commentaries — it must verify **content**, not file bytes.

## Decision

Adopt **content-level integrity verification** for SQLite data bundle members (`Option B`): replace byte-pins on `bible.db`/`macula.db` with a committed *content* manifest (`data/INTEGRITY.json`) computed deterministically from database content, independent of the toolchain that produced the file.

### 1. Content Hash Definition

`content_sha256` = SHA-256 over, in fixed order:

1. **Schema census:** one line per object in `sqlite_master` — type, name, and full SQL — for canonical tables, views, triggers, and indexes. FTS5 shadow tables are **derived** from actual `CREATE VIRTUAL TABLE ... USING fts5` linkage (never from name suffixes, which would let a rogue table named `x_data` masquerade), and FTS-maintenance triggers (AFTER INSERT/DELETE/UPDATE writing into an FTS virtual table) are excluded as machinery. The FTS virtual table itself remains in the census (its schema is part of the surface).
2. **Canonical table rows:** for each canonical table (in a fixed declared order): a header line of column names, then every row serialized as CSV with `PRIMARY KEY` ordering and canonical value rendering (`NULL` → `null`, floats/ints normalized to plain literals).

Schema objects and rows outside the canonical table set **raise** (fail fast, per Non-negotiable 3: "Bad data raises; generators never repair source data"). Views and handwritten triggers are rejected as unrecognized shapes.

### 2. Two Verification Modes

* **`deep=True`** (default): full per-row content hash — the authoritative CI/manual gate and the **user-facing `/api/verify-bundle` endpoint** (backing the settings-panel "Verify data bundle" button; a user-initiated action can afford the ~25 s run, and the fast check would report valid on cell-level tampering — defeating user-facing verification). `?deep=0` opts into the fast path for lightweight callers.
* **`deep=False`**: schema shape + row counts only — sub-second; reserved for lightweight per-request surfaces (currently unused by the UI, still unit-tested). The shape gate (rejecting unrecognized tables/views/triggers) runs in **both** modes; it is cheap and guards the fast path against silent divergence.

### 3. Manifest Layout

`data/INTEGRITY.json` (schema `data/integrity/v1`):

```json
{
  "$schema": "data/integrity/v1",
  "databases": {
    "bible.db":  { "canonical_tables": [...], "content_sha256": "...", "row_counts": {...} },
    "macula.db": { "canonical_tables": [...], "content_sha256": "...", "row_counts": {...} }
  }
}
```

Committed to the repo. Generated/verified by `python -m search.validation.db_integrity --generate | --check`.

### 4. Layered Bundle Integrity

* **Layer 1 (content):** SQLite DBs against `INTEGRITY.json` — the honest cross-machine check.
* **Layer 2 (byte):** JSON artifacts (lexicons, schemas) against `data/SHA256SUMS` as before — these are byte-deterministic and cheap to pin. DB entries are dropped from `SHA256SUMS` where the content manifest exists.

## Consequences

* **Positive:** Verification now proves *content* equality — a rebuilt bundle on any toolchain passes if and only if it carries the same canonical rows and schema.
* **Positive:** The stale-code regression class (2,541-row drift) is caught deterministically by CI gate F6, not discovered by users.
* **Neutral:** Adds `data/INTEGRITY.json` (small JSON) as a committed generated artifact; regenerated whenever the DB build changes (`build_release_data.sh` step 6a).
* **Neutral:** Deep verification is ~24 s — acceptable for CI/manual gates; interactive UI uses the sub-second fast path.
* **Negative:** `data/SHA256SUMS` no longer byte-documents the DBs in isolation; the content manifest is the authority and must be regenerated in lockstep with DB rebuilds (guarded by release self-check step 7).