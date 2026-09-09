# ADR-002: Dual licensing + link-out content sourcing

**Status:** Accepted · **Date:** 2026-08-31; recorded 2026-09-01

## Context

The project mixes code, original analytical content, public-domain sources,
and copyrighted SDA materials (EGW writings, SDABC) that must not be
redistributed. Licenses also cannot enforce doctrinal alignment — that is a
curation concern (see ADR-001).

## Decision

* **Code** (`search/`, tooling): MIT (`LICENSE`).
* **Original content** (concordance data, semantic links, taxonomies, word
  studies): CC BY 4.0 (`LICENSE.content`).
* **EGW/SDA and copyrighted translations:** link-out / user-supplied-text,
  never bundled (`NOTICE.md`).
* **Third-party lexical data** (Strong's via gmlewis Apache-2.0, scrollmapper
  MIT, OSHB CC BY 4.0, STEPBible CC BY 4.0): raw sources fetched on demand and
  gitignored; only derived, attributed, changes-recorded artifacts are
  committed.
* Doctrinal basis (Bible as standard, Adventist framework, humility of
  progressive light) is encoded as policy in `NOTICE.md`, enforced by the
  review workflow — not by the license.

## Consequences

* Clean redistribution of everything committed; attribution obligations are
  documented per artifact.
* Future sources must clear a license check (per-file!) before ingest — the
  STEPBible TBESH Online-Bible caveat and the MorphGNT CC BY-SA + SBLGNT EULA
  conflict are the precedents.
