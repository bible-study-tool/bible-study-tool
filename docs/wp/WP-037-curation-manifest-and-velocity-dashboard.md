# WP-037: Curation Velocity Dashboard & Verifiable Terminal Manifest

status: open
scope: Pillar A (Corpus & Content), Pillar F (Integrity), Pillar H (Governance & Tooling)
priority: high
decisions: [ADR-001](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-001-deterministic-core-vs-ai.md), [ADR-003](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-003-standard-yaml-frontmatter.md), [ADR-005](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-005-data-integrity-precedes-scale.md), [ADR-006](file:///home/archvm/projects/bible-study-tool/docs/decisions/ADR-006-provenance-and-generated-artifacts.md)

---

## 1. Objective

Close the gap between skeleton generation and verifiable human review by introducing a terminal `approved` curation status, generating a cryptographic curation manifest (`data/curation-manifest.json`), and integrating a curation velocity and coverage dashboard directly into `scripts/status.py`.

---

## 2. Background

Currently, `status: review` is the highest status an entry reaches in its frontmatter. As noted during architectural review, there is no terminal approved state and no canonical artifact recording that human review actually concluded. Furthermore, while the deterministic pipeline efficiently generates drafts, the human review bottleneck remains invisible because `scripts/status.py` reports repository commits and artifact presence, but not curation progress across the 31,102 verses of the Bible.

This work package converts subjective review status into a verifiable fact and gives the project honest, real-time visibility into the curation frontier.

---

## 3. Implementation Plan

### Phase 1 — Terminal Status & Taxonomy Update
* [ ] Update `tags/taxonomy.json` to formally define three lifecycle statuses:
  - `draft`: Machine-generated skeleton, unverified by human eyes.
  - `review`: Under active theological/editorial inspection.
  - `approved`: Formally approved by human review, sealed and verified.
* [ ] Update `search/validation/schema.py` (F1) to recognize and enforce `approved` status.

### Phase 2 — Cryptographic Curation Manifest (`data/curation-manifest.json`)
* [ ] Build `search/corpus/curation_manifest.py` with CLI (`--check`, `--generate`):
  - Scans all entries under `materials/bible/`.
  - For each `status: approved` entry, records:
    - Canonical verse ID (e.g. `gen-01-01`).
    - File path and relative URI.
    - Content SHA-256 checksum (excluding mutable timestamps).
    - Review metadata (reviewer, approval date, doctrinal framework notes).
  - Serializes to sorted, deterministic `data/curation-manifest.json`.
* [ ] Wire manifest validation into `scripts/verify_all.sh`:
  - If any file marked `approved` has been tampered with or modified without updating the manifest, CI fails fast.

### Phase 3 — Curation Velocity Dashboard in `scripts/status.py`
* [ ] Enhance `scripts/status.py` with a dedicated **Curation Frontier** briefing section:
  - Total verses categorized: `Approved` | `In Review` | `Draft` | `Pending Scaffolding`.
  - Book-by-book progress table (e.g. Genesis: 31 approved, 49 in review, 1,453 draft).
  - Curation velocity metrics (verses promoted over the past 7 days and 30 days).
  - Explicit notification of the next recommended chapter for curation focus.

### Phase 4 — Unit Tests & Validation Gates
* [ ] Add `search/corpus/test_curation_manifest.py`:
  - Test manifest generation from sample entries.
  - Test tampering detection (modified content with unchanged manifest raises error).
  - Test schema conformance of `data/curation-manifest.json`.
* [ ] Add unit tests verifying `scripts/status.py` curation calculations.

---

## 4. Acceptance Criteria

1. `status: approved` is fully recognized and validated by F1 schema validator.
2. `data/curation-manifest.json` cryptographically pins every approved entry in the repository.
3. Modifying an approved markdown file without regenerating the manifest causes `scripts/verify_all.sh` to fail fast.
4. `python scripts/status.py` outputs a clean, executive curation status report in <0.5s.
