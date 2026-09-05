# WP-026: Scripture Interpreting Scripture — Old Testament Citation Anchors in New Testament Epistles

status: completed
scope: Deterministic detection, cross-referencing, and multi-dimensional presentation of Old Testament quotations, prophetic fulfillments, and covenant anchors in the New Testament epistles and Gospels, bridging Hebrew WLC, Greek LXX, and apostolic theology.
priority: high

## Objective

To fulfill the foundational Protestant and Adventist hermeneutic principle:
> *"The Bible is its own expositor. Scripture is to be compared with scripture. The student should learn to view the word as a whole, and to see the relation of its parts."* — Ellen G. White, *Education*, p. 190.
> *"Everything this tool is is in the search and benefit of understanding the word of God better, and at a deeper level. To be able to truly understand what the Holy Spirit is trying to tell us."*

When reading the apostolic epistles (Romans, Galatians, Ephesians, Hebrews, 1 & 2 Peter), modern readers frequently struggle with Paul's or Peter's logic because apostolic arguments are built directly upon the Hebrew Scriptures. When Paul writes *"The just shall live by faith"* (Rom 1:17), he is quoting Habakkuk 2:4; when he explains righteousness without works (Rom 4), he is expounding Genesis 15:6 and Psalm 32:1-2; when he proclaims Christ's substitutionary curse (Gal 3:13), he is anchoring into Deuteronomy 21:23.

This work package implements **Feature 4** of the comprehension architecture:
1. **Deterministic Canonical OT Citation Database (`search/corpus/ot_citations.py`)**:
   - Over 100 canonical Old Testament citations and major covenant anchors across Romans, Galatians, 1 & 2 Corinthians, Ephesians, Hebrews, 1 & 2 Peter, James, and the Gospels/Acts.
   - Structured metadata: NT OSIS reference, OT OSIS source, introductory apostolic formula (e.g. *καθὼς γέγραπται* / *λέγει γὰρ ἡ γραφή*), NT text snippet, OT KJV text, Hebrew WLC text, Septuagint (LXX) textual reading, covenant theme, and deep theological exposition.
2. **Bi-directional Cross-Referencing**:
   - In New Testament passages: surfaces the original Hebrew Old Testament passage and its covenant setting.
   - In Old Testament passages: surfaces which apostolic authors quote or fulfill the passage in the New Testament (e.g., viewing Gen 15:6 shows Rom 4:3, Gal 3:6, Jas 2:23).
3. **Workstation UI Integration (`search/ui/app.py`)**:
   - **Reader Pane Badges**: Compact cues in verse headers (e.g., `⟨OT Anchor: Hab 2:4⟩` or `⟨Cited in NT: Rom 1:17⟩`).
   - **Syntax & Frames Tab (Tab 1)**: Dedicated `SCRIPTURE INTERPRETING SCRIPTURE: OLD TESTAMENT CITATION ANCHOR` card displaying side-by-side NT citation vs OT Hebrew source, LXX variations, and apostolic theological exposition.
   - **One-Key Passage Jump**: Ability to jump directly between the quoting NT verse and the quoted OT source.
4. **Comprehensive Test Coverage & Verification**:
   - Unit tests in `search/corpus/test_ot_citations.py`.
   - Integration tests in `search/ui/test_ui.py` and async headless tests in `search/ui/test_textual.py`.
   - Complete gate pass with `bash scripts/verify_all.sh`.

## Implementation Tasks

### 1. OT Citations Engine (`search/corpus/ot_citations.py`)
- [x] Define `CitationType` enum (`DIRECT_QUOTE`, `ALLUSION`, `PROPHETIC_FULFILLMENT`, `COVENANT_TYPOLOGY`).
- [x] Define `OTCitation` dataclass.
- [x] Implement canonical dataset containing 100+ major OT citations across NT epistles and Gospels.
- [x] Implement indexed lookup functions:
  - `lookup_ot_citations_for_nt_verse(nt_osis: str) -> list[OTCitation]`
  - `lookup_nt_citations_for_ot_verse(ot_osis: str) -> list[OTCitation]`
  - `get_passage_ot_citations_batch(book: str, chapter: int) -> dict[str, list[OTCitation]]`
- [x] Implement rich display formatting helper: `render_citation_card(citation: OTCitation) -> str`.

### 2. Backend Service Integration (`search/ui/study_service.py`)
- [x] Add `ot_citations: list[OTCitation]` and `nt_citations: list[OTCitation]` to `VerseStudy`.
- [x] In `get_passage_study`, batch-extract citations across the loaded chapter in a single pass (<0.2ms).
- [x] Provide helper `get_citation_ot_verse_text(citation: OTCitation) -> str` to fetch full OT verse text on demand.

### 3. Workstation UI Integration (`search/ui/app.py`)
- [x] Update `VerseWidget`: Render subtle, color-coded citation cue badges in the verse header line (e.g., `⟨OT Quote: Hab 2:4⟩` or `⟨Cited in NT: Rom 4:3, Gal 3:6⟩`).
- [x] Update Tab 1 (`Syntax & Frames`): Add dedicated `SCRIPTURE INTERPRETING SCRIPTURE: OLD TESTAMENT CITATION ANCHOR` section.
- [x] Add keyboard shortcut `o` (`action_jump_citation`) to jump to the linked OT verse if an active citation exists.

### 4. Verification & Testing
- [x] Create `search/corpus/test_ot_citations.py` covering NT and OT lookups, batch queries, and badge/card rendering.
- [x] Add tests in `search/ui/test_ui.py` and `search/ui/test_textual.py`.
- [x] Run subagent review with `code-reviewer`.
- [x] Verify full pass with `bash scripts/verify_all.sh`.

## Acceptance Criteria
- [x] All major Pauline epistolary citations (Romans 1:17, 3:10-18, 4:3, 8:36, 9-11, 12:19, Gal 3:10-13, Eph 4:8) and Hebrews citations are deterministically resolved.
- [x] Bi-directional linking functions smoothly (NT -> OT and OT -> NT).
- [x] Workstation navigation remains instantaneous (<1ms).
- [x] All test suites pass clean via `bash scripts/verify_all.sh`.
