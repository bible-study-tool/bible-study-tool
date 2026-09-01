# ADR-0006: Source pinning + generated-artifact discipline

**Status:** Accepted · **Date:** 2026-08-31; recorded 2026-09-01

## Context

Generators derive committed artifacts from third-party sources. Without
pinned, checksummed inputs and regeneration discipline, artifacts drift from
sources silently and can never be audited or reproduced.

## Decision

* Every third-party source is pinned in `data/PROVENANCE.md` (upstream commit
  / tag + SHA-256 of every file), fetched by `scripts/fetch_sources.sh`
  (idempotent, checksum-verified, fails closed on mismatch).
* Generated artifacts (`lexicons/*.json`, `correlations/agreement-ledger.json`,
  `correlations/apparatus-*.json`, generated corpus entries) are **never
  hand-edited**: each has a generator, a byte-identical-regeneration tripwire
  test, and a recorded checksum. The PROVENANCE checksum gate test enforces an
  EXACT inventory (a new generated artifact committed without registration
  fails CI).
* Raw sources are gitignored; a fresh clone reproduces everything via the
  fetch script + documented generator commands.

## Consequences

* Full audit chain: committed artifact -> checksum -> pinned source -> live
  upstream.
* Contributors must learn the regenerate-don't-edit rule; every failure
  message teaches its remedy (scripts/verify_all.sh).
