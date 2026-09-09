# WP-023: Human-Accessible Original Language Framing & Direct Commentary Navigation

status: completed
scope: Enhance Textual study workstation and core services with dual-layered original language + English gloss framing, automatic KJV-word to Strong's mapping in the Lexicon inspector, full-text Spirit of Prophecy paragraph rendering, and direct EGW citation navigation (`PP 44.1`, `DA 25.3`).
priority: high

## Objective
Remove linguistic barriers for Bible students who do not read Hebrew or Greek, eliminate concordance lookup friction, and enable full-text Spirit of Prophecy reading directly within the study workstation (per ADR-013 and ADR-019).

## Inputs
- `ROADMAP.md` (Pillars A, B, D)
- `docs/decisions/ADR-019-accessible-original-languages-and-commentary-integration.md`
- `docs/decisions/ADR-018-textual-study-workstation-and-themes.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `search/ui/study_service.py`
- `search/ui/app.py`
- `search/linking/egw.py`
- `lexicons/tbesh-glosses.json` & `lexicons/tbesg-glosses.json`

## Tasks
- [x] Fix `study_service.py` to parse `entries` from `tbesh-glosses.json` and `tbesg-glosses.json` for whole-Bible Hebrew and Greek glosses.
- [x] Retain complete paragraph `"text"` in `StudyService.get_passage_study` and add EGW citation resolution (`lookup_egw_citation`, `get_egw_page`).
- [x] Update Syntax & Frames inspector in `search/ui/app.py` to display English glosses alongside Hebrew/Greek participant roles.
- [x] Update Lexicon inspector in `search/ui/app.py`:
  - Show the specific KJV English word from the selected verse corresponding to each Strong's number.
  - Show English glosses alongside Greek lemmas in the Septuagint (LXX) equivalences section.
- [x] Update Commentary inspector in `search/ui/app.py` to render full paragraph text with rich Markdown.
- [x] Extend Goto dialog (`g` / `Ctrl+P`) to accept and navigate directly to EGW citations (`PP 44.1`, `DA 25.3`).
- [x] Add comprehensive tests in `search/ui/test_ui.py` and `search/ui/test_textual.py`.
- [x] Verify full test suite with `scripts/verify_all.sh` (472 passed).
- [x] Subagent review with `code-reviewer`.

## Acceptance Criteria
- [x] Syntax tab displays English glosses for every participant role (Agent, Action, Patient, Context).
- [x] Lexicon tab identifies the translated KJV word for each entry.
- [x] LXX Greek equivalences show English glosses alongside Greek lemmas.
- [x] Commentary tab displays full paragraph text rather than 25-word snippet fragments.
- [x] Entering an EGW citation in the Jump modal navigates directly to that paragraph in the Commentary tab.
- [x] All 472 tests pass with `bash scripts/verify_all.sh`.
