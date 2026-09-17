# WP-025: Pauline Argument Flow & Discourse Markers

status: complete
scope: Deterministic detection, classification, and presentation of Koine Greek and Biblical Hebrew logical discourse markers (premises, conclusions, divine purposes, adversative pivots, analogies) to clarify the apostle Paul's argument flow across epistles and the biblical canon.
priority: high

## Objective

To fulfill the user's primary North Star:
> *"Everything this tool is is in the search and benefit of understanding the word of God better, and at a deeper level. To be able to truly understand what the Holy Spirit is trying to tell us."*
> *"Sometimes, reading Paul's letters, I have no idea of what he's saying until I've read it several times in different translations... The depth of meaning in the Hebrew words is very foreign to modern, surface-level English."*

This work package implements **Feature 3** of the comprehension architecture:
1. Deterministic classification of Greek and Hebrew logical connectors into six high-yield categories:
   - **PREMISE / GROUND** (`γάρ` / `כִּי` / `διότι`): Explains the divine reality or theological bedrock behind an assertion (*Why*).
   - **INFERENCE / CONCLUSION** (`οὖν` / `ἄρα` / `עַל־כֵּן` / `διό`): The decisive turning point establishing ethical or doctrinal conclusions (*Therefore*).
   - **PURPOSE / INTENTION** (`ἵνα` / `ὅπως` / `לְמַעַן`): God's supreme design, goal, and sovereign purpose (*In order that*).
   - **ADVERSATIVE / CONTRAST** (`ἀλλά` / `אוּלָם` / `δέ`): Divine holy redirection and contrast to human helplessness (*But God*).
   - **CONDITION / CONTINGENCY** (`εἰ` / `ἐάν` / `אִם`): Covenant conditions and suppositions (*If... then*).
   - **ANALOGY / ARCHETYPE** (`καθώς` / `כַּאֲשֶׁר` / `ὥσπερ`): Linking believer conduct directly to Christ's divine pattern (*Just as... even as*).
2. Deep explanatory annotations translating raw syntax into plain-English argument flow.
3. Visual integration in the Textual workstation:
   - **Syntax & Frames Tab (Tab 1):** Detailed `ARGUMENT FLOW & LOGICAL CONNECTORS` section breaking down the connectors in the inspected verse.
   - **Reader Pane Badges:** Highlighting logical pivots (`⟨Premise: γάρ⟩`, `⟨Inference: οὖν⟩`, `⟨Purpose: ἵνα⟩`) on verse headers to reveal the structural spine of chapters at a glance.
4. Comprehensive test coverage with unit tests and async UI tests.

## Implementation Tasks

### 1. Discourse Flow Engine (`search/corpus/discourse_flow.py`)
- [x] Define `DiscourseCategory` (enum/str: `PREMISE`, `CONCLUSION`, `PURPOSE`, `CONTRAST`, `CONDITION`, `ANALOGY`).
- [x] Define `DiscourseMarker` dataclass storing marker category, original word, transliteration, Strong's number, English KJV/BSB token span, theological function summary, and argument flow explanation.
- [x] Implement canonical lookup tables for Greek NT and Hebrew OT discourse particles.
- [x] Implement `extract_verse_discourse_markers(tokens: list, text: str)` to parse tokens from `BibleDB` or `MaculaSqliteDB`.
- [x] Implement `analyze_passage_argument_flow(verses: list)` to connect sequential markers into an argument outline.

### 2. Backend Service Integration (`search/ui/study_service.py`)
- [x] Add `discourse_markers: list[DiscourseMarker]` to `VerseStudy`.
- [x] In `get_passage_study`, batch-extract discourse markers across the loaded chapter in a single pass (<1ms).
- [x] Provide helper methods for retrieving discourse markers by Strong's code or verse index.

### 3. Workstation UI Integration (`search/ui/app.py`)
- [x] Update `VerseWidget`: Render subtle, color-coded discourse cue badges in the verse header line (e.g., `⟨Premise: γάρ⟩`, `⟨Inference: οὖν⟩`, `⟨Purpose: ἵνα⟩`, `⟨Pivot: ἀλλά⟩`).
- [x] Update Tab 1 (`Syntax & Frames`): Add dedicated `ARGUMENT FLOW & LOGICAL CONNECTORS` section rendering:
  - Connector badge, original word, and Strong's number.
  - Plain-English explanation of the logical role.
  - Surrounding context and theological significance (e.g., Pauline "For... For... For..." premise chains or the Romans 12:1 "Therefore" turning point).
- [x] Ensure persistent viewport updates remain under <1ms with zero DOM thrashing.

### 4. Verification & Testing
- [x] Create `search/corpus/test_discourse_flow.py` testing:
  - Greek premise markers (`γάρ` Rom 1:16-17).
  - Greek inference markers (`οὖν` Rom 12:1).
  - Greek purpose markers (`ἵνα` Eph 1:4).
  - Greek adversative markers (`ἀλλά` Eph 2:4).
  - Greek analogy markers (`καθώς` Eph 5:25).
  - Hebrew markers (`כִּי`, `עַל־כֵּן`, `לְמַעַן`).
- [x] Add UI tests in `search/ui/test_ui.py` and async headless tests in `search/ui/test_textual.py`.
- [x] Run subagent review with `code-reviewer`.
- [x] Verify full pass with `bash scripts/verify_all.sh`.

## Acceptance Criteria
- [x] Discourse markers are correctly extracted for all 27 New Testament books and 39 Old Testament books.
- [x] Pauline epistles (Romans, Ephesians, Galatians, etc.) display immediate argument flow cues in the workstation.
- [x] Verse stepping and tab switching remain instantaneous (<1ms).
- [x] All 532 tests pass clean via `bash scripts/verify_all.sh`.
