# Next Session Handoff

**Written:** 2026-09-06 (end of the Documentation & Pastoral Guide Overhaul session)  
**Repo state:** `master`, clean, all 565 tests passing, F1–F4 validators clean  
**Next step:** Thematic Curation Expansion (Genesis 4: Cain & Abel, or Romans 1–3 / Hebrews 8–9 Sanctuary typology)

---

## Where We Are

The project has achieved several major architectural and pastoral milestones:
1. **Interactive Textual Study Workstation (`scripts/study.py`)**: A fluid, sub-millisecond terminal interface powered by a persistent viewport engine, Rich typography, and 7 switchable themes (Transparent, Dracula, Catppuccin Mocha, Tokyo Night, Nord, Gruvbox Dark, Solarized Dark).
2. **The 5 Core Biblical Comprehension Tools**:
   - **Plain-English Hebrew & Greek Verbal Stems**: Qal, Niphal, Piel, Hiphil, Hitpael, Aorist, Middle Voice, and Perfect Passive translated into accessible ministerial meaning with theological significance.
   - **Pauline Argument Flow & Discourse Markers**: Koine Greek particles (`⟨Premise: γάρ⟩`, `⟨Therefore: οὖν⟩`, `⟨Purpose: ἵνα⟩`) visualized in the reader and mapped as an argumentative chain.
   - **Scripture Interpreting Scripture (OT Citation Anchors)**: One-key jump (`o`) between New Testament apostolic citations and their Old Testament Hebrew (WLC) and Greek (LXX) quotation roots.
   - **Multi-Translation Parallel View**: Zero-latency comparison of KJV, ASV, BSB, and YLT stacked (`v` key) or side-by-side in Tab 4.
   - **Spirit of Prophecy Integration**: Continuous page reader (`g` ➔ `PP 44.1`, `DA 19.1`), page context attachment, and chapter-level correlations (`c` toggle).
3. **Pillar A3 Closed**: Full New Testament generator (`search/corpus/build_nt.py`), 27 NT books integrated into `tags/taxonomy.json`, per-chapter directory structure across Old and New Testaments (`materials/bible/{ot,nt}/{book}/{ch:02d}/`), and deep theological curation of **John 1** (51 verses) and **John 17** (26 verses).
4. **Documentation & User Guide Overhaul**:
   - Modernized `README.md` reflecting whole-Bible databases, interactive workstation, and comprehension tools.
   - Created `docs/USER_GUIDE.md`: A warm, friendly, step-by-step guide for anyone without computer or terminal background, focusing on personal study, small groups, and teaching walkthroughs.

---

## State Summary

| Area | State |
|---|---|
| Corpus | 1,610 entries: Genesis 1–3 (80 curated), Genesis 4–50 (1,453 draft skeletons), John 1 (51 curated), John 17 (26 curated) |
| Workstation UI | `scripts/study.py`, `search/ui/app.py` (5 persistent tabs, 7 themes, parallel view, mouse support) |
| Original Languages | Full Strong's (8,674 H + 5,624 G), unabridged BDB & Abbott-Smith lexicons, Macula Hebrew MT & Greek NT syntax trees |
| Parallel Translations | Whole-Bible KJV (1769), BSB (2020), ASV (1901), YLT (1898) in `data/bible.db` (31,102 verses) |
| Spirit of Prophecy | `data/egw.db` local SQLite FTS5 database, continuous page reader, canonical token resolution (`PP 44.1`) |
| Validators | F1 Schema, F2 Strong's, F3 Cross-refs, F4 Audit: **0 errors, 0 warnings** |
| Test Suite | **565 tests passing** |
| ADRs | ADR-001 through ADR-021 accepted |
| Work Packages | WP-001 through WP-027 completed |

---

## Opening Checklist for the Next Session

1. Run `python scripts/status.py` to inspect repository state.
2. Run `bash scripts/verify_all.sh` to confirm green baseline (565 tests, 0 validator errors).
3. Choose next thematic focus:
   - **Option A (OT Genesis Curation)**: Curate Genesis 4 (Cain & Abel, the offerings, first murder, lineage of Seth) per WP-012.
   - **Option B (NT Pauline Epistle Curation)**: Curate Romans 1 or Romans 3 (righteousness by faith, Habakkuk 2:4 quotation anchor, discourse argumentation).
   - **Option C (NT Sanctuary Curation)**: Curate Hebrews 8–9 (the heavenly sanctuary, shadows and realities, High Priest intercession).
   - **Option D (Static Site / Wiki Generation)**: Set up MkDocs or static documentation generator to publish `docs/`, `materials/`, and `docs/USER_GUIDE.md` as a browsable online wiki.
