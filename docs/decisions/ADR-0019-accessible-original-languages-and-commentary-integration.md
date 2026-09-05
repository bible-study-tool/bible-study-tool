# ADR-0019: Human-Accessible Original Language Framing and Direct Commentary Navigation

- **Status:** Accepted
- **Date:** 2026-09-04
- **Author:** Assistant & User Pair
- **Deciders:** Assistant, Project Lead
- **Consulted:** ADR-0013 (Stewardship, Scale, and Usefulness), ADR-0017 (TUI Architecture), ADR-0018 (Textual Workstation)
- **Informs:** WP-023

## Context

Following the initial delivery of the Textual study workstation (ADR-0018, WP-022), user evaluation identified critical usability friction in how original language data and Spirit of Prophecy commentary are presented:

1. **Linguistic Inaccessibility:** The Macula Syntax & Participant Frames tab and Strong's Lexicon tab previously displayed content solely in raw Hebrew (square script) and Greek (polytonic). While linguistically precise, this created a barrier for students and readers who cannot read biblical Hebrew or Greek. The data was present in the underlying corpus, but opaque to the user.
2. **Concordance Mapping Friction:** Users had to manually toggle Strong's concordance tags on the Scripture reader to identify which English words corresponded to which lexical cards in the inspector pane. Furthermore, Septuagint (LXX) translation equivalences listed only Greek lemmas without English definitions, obscuring theological cross-testament connections (e.g. Hebrew *bara* ➔ Greek *poieo* / *ktizo*).
3. **Commentary Truncation & Lack of Direct Citation Access:** The Commentary tab previously rendered only 25-word snippet fragments from FTS5 index matches instead of the full paragraph text. Moreover, readers could not navigate directly to a specific Spirit of Prophecy paragraph (e.g. `PP 44.1`, `DA 25.3`, `GC 423.1`) or read continuous chapters without external tools.
4. **Terminal Transparency Mechanism:** In curses, `-1` default color pairs allow terminal background pass-through. Textual's compositor by default clears and paints full-screen cells with ANSI background colors.

## Decision

We commit to the principle that **rigorous scholarly data must always be paired with intuitive human-readable English representations**:

1. **Dual-Layered Participant Frames (Hebrew/Greek + English Glosses):**
   - The Syntax tab will display both the original lemma and the interlinear English gloss for every syntactic participant (Agent, Action, Patient, Context).
   - Example: `• Agent: אֱלֹהִ֑ים [God]` | `• Action: בָּרָ֣א [he created]` | `• Patient: אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ [the heavens and the earth]`.

2. **Bidirectional English ↔ Lemma Concordance Alignment:**
   - In the Lexicon tab, every lexical card will explicitly identify the translated KJV English word from the active verse (e.g. `KJV Word: "created" ➔ H1254`).
   - Septuagint (LXX) cross-testament equivalences will resolve both the Greek lemma and its English gloss (e.g. `G4160 (ποιέω — "to make, do"): 20x`).
   - Fix dictionary schema consumption in `study_service.py` to load `entries` from `tbesh-glosses.json` and `tbesg-glosses.json`.

3. **Full-Text Commentary & Unified Citation Navigation:**
   - The Commentary tab will render complete, unabridged Spirit of Prophecy paragraphs formatted with rich Markdown.
   - The Jump Dialog (`g` / `Ctrl+P`) will accept both Scripture references (`John 3:16`, `Gen 1`) and standard EGW citations (`PP 44.1`, `DA 25.3`, `GC 423`). When an EGW token is provided, the workstation will immediately switch to the Commentary tab and present the full text.

## Consequences

- **Positive:**
  - Non-Hebrew/Greek readers can immediately understand syntactic roles and cross-testament word usage.
  - Zero-friction alignment between English Scripture and Strong's lexicons.
  - Full-text reading of Ellen G. White commentary directly inside the workstation.
  - Upholds ADR-0013 stewardship by making deep scholarship accessible to everyday Bible students.
- **Negative / Trade-offs:**
  - Slightly more screen real estate required per clause in the inspector pane (handled via existing scrolling).
