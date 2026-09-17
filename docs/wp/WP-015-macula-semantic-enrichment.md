# WP-015: Macula Semantic Enrichment (Pillar B, Goal B3)

status: complete
scope: Semantic enrichment engine (`search/macula/enrichment.py`) connecting Macula syntactic clause roles and empirical Septuagint (LXX) translation equivalences to the semantic linking and candidate discovery pipelines (ADR-012, ADR-014, ADR-015).
priority: high

## Objective
Implement Phase 3 of Pillar B (Goal B3):
1. Extract empirical Septuagint (LXX) translation-equivalence relations from Macula data to ground cross-language semantic links in biblical translation history.
2. Extract syntactic participant frames (Agent/Subject, Action/Predicate, Patient/Theme, Spatiotemporal Context) from Macula clause trees to explain grammatical and theological relationships.
3. Integrate translation equivalence into the discovery pipeline (`search/linking/candidates.py`), proposing verifiable `relation/translation-equivalence` candidates with frequency counts and SDBH domains into `correlations/ai-discovered-links.json` without modifying the deterministic core (`correlations/semantic-links.json`).
4. Provide CLI utilities to inspect verse semantic frames and translation equivalence.

## Inputs (read these first)
- `ROADMAP.md` (Pillar B, Goal B3)
- `correlations/MACULA_INTEGRATION.md`
- `correlations/SEMANTIC_LINKING_GUIDE.md`
- `docs/decisions/ADR-012-macula-hebrew-linguistic-integration.md`
- `docs/decisions/ADR-014-whole-bible-macula-sqlite-architecture.md`
- `docs/decisions/ADR-015-macula-semantic-enrichment.md`
- `search/macula/lookup.py` & `search/macula/db.py`
- `search/linking/candidates.py` & `search/linking/cli.py`

## Tasks
- [x] Implement `search/macula/enrichment.py`:
  - `get_translation_equivalences(strongs_num, db=None)`: extract Greek LXX equivalents, frequencies, and Greek forms.
  - `get_verse_semantic_frame(verse_ref, db=None)`: extract parsed Agent, Action, Patient, and Context constituents.
  - `discover_translation_equivalence_candidates(loader, min_lxx_count=1, db=None)`: generate grounded cross-language candidate proposals.
  - `enrich_curated_link(link_dict, db=None)`: enrich curated semantic links with empirical LXX attestation data.
- [x] Update `search/linking/candidates.py` & `search/linking/cli.py`:
  - Support integrating Macula empirical translation equivalence proposals alongside vector similarity proposals.
  - Add `--macula-enrich` flag to `search/linking/cli.py`.
- [x] Update `scripts/macula_lookup.py`:
  - Add `--frame` / `--enrich-verse` flag to inspect semantic participant roles for a verse.
  - Add `--equiv` flag to inspect LXX translation equivalences.
- [x] Create comprehensive test suite in `search/macula/test_enrichment.py`.
- [x] Verify test suite with `bash scripts/verify_all.sh`.
- [x] Subagent review by `code-reviewer`.

## Acceptance criteria
- [x] `get_verse_semantic_frame("Gen.1.1")` identifies God as Subject/Agent, create as Action, heavens & earth as Patient/Object.
- [x] `get_translation_equivalences("H1254")` identifies LXX *poieō* (G4160) and *ktizō* (G2936).
- [x] Candidate discovery produces verifiable cross-language links with empirical LXX citations in `ai-discovered-links.json`.
- [x] Deterministic core (`correlations/semantic-links.json`) remains completely uncorrupted by automated runs.
- [x] All tests pass (321 tests), `verify_all.sh` green.
