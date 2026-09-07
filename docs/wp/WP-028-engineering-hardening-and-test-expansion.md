# WP-028: Engineering Hardening & Test Expansion

status: open
scope: Pillar G (G2, G3) — systematic elimination of test fragility, coverage gaps, and CI blind spots identified during the beta-tester pass and ongoing development.
priority: high

## Objective

Harden the engineering layer so that regressions are caught by the test suite rather than by beta testers, and so that the CI pipeline remains trustworthy as the codebase and corpus grow. This package closes G2 (test expansion) and partially advances G3 (incremental rebuild performance).

## Background

The beta-tester pass (2026-09-05/06) revealed that the CI pipeline had been red for 6 consecutive pushes due to a Psalm reference normalization bug (`Ps.3.0` → `PSA 3:1`). The test suite had no coverage for the passage-normalization edge cases that caused the failure. Additionally, `test_syntax_viewport_verbal_nuances` is intermittently flaky in CI due to Textual async timing — a known category of fragility that needs a systematic fix pattern.

Three gaps identified:

1. **No property/consistency tests** — the corpus is assumed to be self-consistent (all Strong's tags valid, all cross-reference targets resolve, all YAML well-formed) only because the F1–F4 validators run at CI time. But the validators are not themselves tested for their own correctness with edge-case inputs.
2. **No golden tests over generated artifacts** — the deterministic generators (`build_genesis1.py`, `build_nt.py`, `build_morphology.py`) are run manually. There are no regression tests that would catch a generator output change.
3. **Flaky Textual async tests** — `test_syntax_viewport_verbal_nuances` and similar tests occasionally fail with "No verse selected" because the Textual app hasn't fully initialized before assertions run. The fix pattern (`_wait_until_ready`) exists but isn't applied consistently.

## Inputs
- Current test suite: `search/ui/test_textual.py` (37 async), `search/ui/test_ui.py` (57+)
- Validators: `search/validation/schema.py`, `strongs.py`, `xrefs.py`, `audit.py`
- Generators: `search/corpus/build_genesis1.py`, `build_nt.py`, `build_morphology.py`
- Beta-tester report findings (H2, M1 root cause analysis)
- `scripts/verify_all.sh` — the canonical CI gate

## Conventions that Apply
- ADR-0005 (Data integrity precedes scale)
- ADR-0013 (Stewardship: no bloated test infra; tests must be fast and deterministic)
- AGENTS.md Non-negotiable 6 (validators gate every change)

## Implementation Tasks

### Phase 1 — Validator Self-Tests (F1–F4 unit tests)
- [ ] `search/validation/test_schema.py` — add edge-case property tests:
  - Valid entry with every optional field present → 0 errors
  - Entry with `historical_context:` block (new ADR-0022 field) → 0 errors (unknown keys ignored)
  - Entry missing `id` → exactly 1 `missing-field` error
  - Entry with `strongs/kjv.go` stale reference pattern → verify F2 catches it
  - Tag with unknown prefix → `unknown-tag` error
- [ ] `search/validation/test_strongs.py` — property tests for boundary values (H1, H8674, G1, G5624, G5625 = invalid)
- [ ] `search/validation/test_xrefs.py` — test that a cross-reference to a non-existent entry raises, but `advisory: true` refs do not
- [ ] `search/validation/test_audit.py` — golden snapshot of audit output over the current curated corpus (Gen 1–3 + John 1 + John 17)

### Phase 2 — Passage Normalization Tests (CI regression prevention)
- [ ] `search/corpus/test_passage_normalization.py` — parametric tests covering:
  - Standard: `Gen 1:1`, `John 3:16`, `Rev 22:21`
  - Abbreviations: `Ps 23:1`, `Isa 53:5`, `1Co 13:4`, `Eph 2:8`
  - Edge cases that broke CI: `Ps.3.0` → `PSA 3:1` (the beta CI failure), `Song 1:1`, `3Jn 1:1`
  - Chapter-only: `Gen 1`, `John 17`
  - Multi-verse ranges: `Rom 3:21-26`, `John 1:1-5`
- [ ] Verify the normalization function used by F3 (`xrefs.py`) and by `BibleDB.get_passage()` are the same function — no silent divergence

### Phase 3 — Generator Golden Tests
- [ ] `search/corpus/test_generators.py`:
  - Run `build_nt.py` against a single test verse (John 1:1) in a temp directory
  - Assert output YAML frontmatter fields match the schema exactly
  - Assert the Strong's tags are a subset of `lexicons/strongs-list.json`
  - Assert `historical_context:` key is preserved if present in the source
- [ ] Add a `--dry-run` flag to `build_nt.py` and `build_genesis1.py` that validates without writing to disk (safe for CI)

### Phase 4 — Textual Async Flakiness Elimination
- [ ] Audit all `test_textual.py` tests for raw `pilot.pause()` calls without `_wait_until_ready`
- [ ] Replace each with `await _wait_until_ready(pilot, app)` + assertion, following the pattern established in `test_chapter_navigation`
- [ ] Add `@pytest.mark.flaky(reruns=2)` as a fallback to the 3 most timing-sensitive tests (requires `pytest-rerunfailures` in `pyproject.toml` dev deps)
- [ ] Document the `_wait_until_ready` pattern in a docstring at the top of `test_textual.py`

### Phase 5 — CI Health Dashboard (G3 partial)
- [ ] Add a `scripts/ci_health.py` script that:
  - Counts tests by category (unit, integration, async Textual, schema validation)
  - Reports corpus entry counts by status (draft / review / final) and book
  - Reports coverage gaps (books with 0 curated entries)
  - Outputs a clean summary to stdout (feeds into `scripts/status.py`)
- [ ] Integrate the entry-count breakdown into `scripts/status.py` output

## Acceptance Criteria
- `python -m pytest` exits 0 on 5 consecutive clean runs (no intermittent failures)
- F1–F4 validators each have ≥ 10 unit tests covering error, warning, and valid cases
- The `Ps.3.0` class of normalization failure is covered by a named regression test
- Generator golden test catches any future output-format change within the same PR
- `scripts/ci_health.py` runs in < 2 seconds and is included in `verify_all.sh`

## Estimated Effort
3–5 focused sessions. Phase 1 and 2 are highest priority and can ship independently.
