# User & Study Guide: Adventist Bible Study Tool

*A Friendly, Step-by-Step Guide for Personal Study, Small Groups, and Deeper Understanding — No Computer, Python, or Terminal Background Required*

---

## 1. Welcome & Biblical Purpose

> *"For what man knoweth the things of a man, save the spirit of man which is in him? even so the things of God knoweth no man, but the Spirit of God... comparing spiritual things with spiritual."*  
> — **1 Corinthians 2:11, 13**

Welcome! Whether you are opening the Scriptures for personal morning devotions, preparing a Sabbath School lesson, leading a small group study, sharing truth with a neighbor, or preaching a sermon, this tool was created for you.

You **do not need to be a programmer**, understand Python, or have any previous experience with a command line to use this workstation. It is designed to be as friendly and responsive as an e-reader, while putting deep biblical research tools at your fingertips without the cost, complexity, or internet dependency of commercial software.

### What Makes This Tool Unique?
- **100% Offline & Private**: Runs entirely on your personal computer. It never transmits your studies, notes, or searches to the cloud. Whether you are on a flight, at a prayer retreat, or in a remote area without Wi-Fi, your complete Bible study desk is always available.
- **Scripture Interpreting Scripture**: Built on the foundational Protestant and Adventist principle that the Bible is its own best interpreter. It automatically reveals Old Testament prophecies and Hebrew roots behind New Testament passages.
- **Original Languages Made Simple**: You do not need to read Biblical Hebrew or Koine Greek. The tool automatically translates grammatical forms (verbal stems, voices, and moods) into **clear, plain English** and highlights their spiritual and theological significance.
- **Spirit of Prophecy Integration**: Connects inspired commentary from Ellen G. White (*Patriarchs and Prophets*, *The Desire of Ages*, *The Great Controversy*, *Steps to Christ*, and more) directly alongside the biblical text.
- **Instant & Distraction-Free**: No advertisements, no social notifications, no loading delays. The interface responds in less than a single millisecond.

---

## 2. Opening Your Study Desk in 60 Seconds

Opening the study workstation takes just one simple command. Open your terminal or command prompt and run:

```bash
# Launch the interactive study workstation
python scripts/study.py
```

### Opening Directly to Any Passage
If you already have a passage in mind for your personal study or teaching, you can jump straight into it:

```bash
# Study the Prologue of John
python scripts/study.py tui "John 1:1-18"

# Study Creation and the Sabbath
python scripts/study.py tui "Genesis 1:1-2:3"

# Study Christ's High Priestly Prayer
python scripts/study.py tui "John 17:1-26"

# Study Paul's Gospel thesis
python scripts/study.py tui "Romans 1:16-17"
```

---

## 3. Understanding the Workstation Layout

When you launch the workstation, your screen is organized into two clean, readable windows:

```
┌─────────────────────────────────────────┬──────────────────────────────────────────┐
│  📖 SCRIPTURE READER (Left Pane)        │  🔍 STUDY INSPECTOR (Right Pane)         │
├─────────────────────────────────────────┼──────────────────────────────────────────┤
│                                         │  [1] Syntax  [2] Lexicon  [3] Commentary │
│  John 1:14                              │  [4] Parallel  [5] Search                │
│  And the Word was made flesh, and       ├──────────────────────────────────────────┤
│  dwelt among us, (and we beheld         │  VERBAL STEMS & THEOLOGICAL NUANCES      │
│  his glory, the glory as of the         │  • ἐγένετο (G1096) — Aorist Middle       │
│  only begotten of the Father,) full     │    "Came into being / became"            │
│  of grace and truth.                    │    The eternal Word entered human flesh  │
│                                         │                                          │
│  John 1:15                              │  • ἐσκήνωσεν (G4637) — Aorist Active     │
│  John bare witness of him...            │    "Tabernacled / pitched tent"          │
│                                         │    Sanctuary presence among His people   │
└─────────────────────────────────────────┴──────────────────────────────────────────┘
```

### The Left Window: The Scripture Reader
- Shows the biblical chapter in clear, comfortable typography.
- The **currently selected verse** is highlighted with a distinct border.
- Small visual badges tell you when a verse quotes the Old Testament (`⟨OT Anchor: ...⟩`) or contains an inspired logical connector (`⟨Premise: γάρ⟩`, `⟨Therefore: οὖν⟩`).

### The Right Window: The Study Inspector
The inspector contains 5 dedicated tabs:
1. **[1] Syntax & Frames**: Original sentence structure, plain-English verbal stems, clause participants (who did what to whom), and argumentative logic.
2. **[2] Lexicon & Strong's**: Unabridged Hebrew (Brown-Driver-Briggs) and Greek (Abbott-Smith) dictionary entries, Strong's concordance definitions, and King James translation renderings.
3. **[3] Commentary**: Continuous reading of Ellen G. White's writings correlating to the active verse and chapter.
4. **[4] Parallel Translations**: Side-by-side comparison of 4 trusted translations: King James Version (KJV 1769), Berean Standard Bible (BSB 2020), American Standard Version (ASV 1901), and Young's Literal Translation (YLT 1898).
5. **[5] Search Findings**: Results from topical word searches and cross-reference lookups.

---

## 4. The 5 Core Comprehension Tools

The workstation provides five specialized study tools to help you discover deeper meaning:

### Tool 1: Plain-English Hebrew & Greek Nuances (Tab 1)
Ancient languages often express rich dimensions of meaning that single English words cannot fully capture. The tool automatically decodes these grammatical forms into **plain English**:

- **Hebrew Verb Stems**:
  - *Qal*: Simple, direct action (e.g. "he created").
  - *Niphal*: Passive or reflexive action (e.g. "it was revealed").
  - *Piel*: Intensive or transformative action (e.g. *qādash* in Genesis 2:3 — God actively *set apart and sanctified* the Sabbath).
  - *Hiphil*: Causative action (e.g. God *causes* righteousness to spring forth).
  - *Hitpael*: Reflexive, intimate communion (e.g. Enoch *walked habitually with God*).
- **Greek Voices & Tenses**:
  - *Aorist*: A decisive, completed historical reality (e.g. "the Word *became* flesh" in John 1:14).
  - *Present*: Continuous, ongoing, day-by-day experience in Christian life.
  - *Middle Voice*: Deep personal involvement and love (e.g. Ephesians 1:4 — God chose us *for Himself* out of affectionate personal interest).

### Tool 2: Argument Flow & Discourse Markers (Tab 1)
When reading the New Testament epistles, the inspired apostles built careful, step-by-step arguments. The tool highlights these logical connectors:
- `⟨Premise: γάρ⟩` (*gar* = "For / Because"): Introduces the divine reason or doctrinal foundation.
- `⟨Therefore: οὖν⟩` (*oun* = "Therefore"): Marks the practical conclusion — because God has done this for us, how should we live?
- `⟨Purpose: ἵνα⟩` (*hina* = "In order that / With the aim that"): Reveals God's ultimate purpose in redemption.
- `⟨Contrast: ἀλλά⟩` (*alla* = "Yet / But on the contrary"): Highlights the sharp contrast between human weakness and divine grace.

*Study Tip*: Look at the badges across Romans 1:15–18. Notice how Paul connects each thought with a premise: "I am ready to preach the gospel... **FOR** I am not ashamed... **FOR** it is the power of God... **FOR** therein is the righteousness of God revealed... **FOR** the wrath of God is revealed." You can follow the Holy Spirit's exact line of reasoning!

### Tool 3: Scripture Interpreting Scripture: OT Citation Anchors
The New Testament writers constantly rooted their teachings in the Old Testament Scriptures.
- Whenever a verse quotes an Old Testament passage, you will see a badge such as `⟨OT Anchor: Habakkuk 2:4⟩` (on Romans 1:17) or `⟨OT Anchor: Exodus 34:6⟩` (on John 1:14).
- **Press `o`** on your keyboard: The workstation instantly leaps to the Old Testament source passage.
- In Tab 1, inspect the original Hebrew text, the ancient Greek Septuagint translation, and the covenant context.
- **Press `o` again** to return immediately to your New Testament reading passage.

### Tool 4: Multi-Translation Parallel Reading (Key `v` or Tab 4)
Comparing translations is one of the easiest and most effective ways to understand Scripture.
- **Press `v`** while reading any chapter: The workstation immediately expands the Reader Window to show color-coded, stacked parallel lines for:
  - **KJV** (King James Version 1769): Pinned historical text with Strong's concordance numbers.
  - **BSB** (Berean Standard Bible 2020): Modern, accurate, and easy-to-read English.
  - **ASV** (American Standard Version 1901): Close word-for-word grammatical fidelity.
  - **YLT** (Young's Literal Translation 1898): Strict literal rendering preserving Hebrew/Greek verb tenses.
- Press `v` again to return to single-column reading, or switch to **Tab 4 (`Parallel`)** for side-by-side comparison cards for the active verse.

### Tool 5: Continuous Spirit of Prophecy Commentary (Tab 3 & Key `g`)
The writings of Ellen G. White provide inspiring theological commentary and practical spiritual applications.
- Whenever you select a verse, Tab 3 automatically loads commentary paragraphs from Ellen G. White.
- **Press `g`** (Goto) and type any standard citation token (e.g. `PP 44.1`, `DA 19.1`, `GC 678.1`, `SC 62.2`): The workstation immediately loads the continuous page view, allowing you to read the full chapter context.
- **Press `c`** anytime in Tab 3 to toggle between the continuous page reader and all chapter-level thematic correlations.

---

## 5. Step-by-Step Study & Teaching Walkthroughs

### Walkthrough 1: The Incarnation (John 1:14)
*Goal: Understand the deep sanctuary meaning of "The Word Dwelt Among Us" for personal devotion, small group study, or a sermon.*

1. **Launch the passage**:
   ```bash
   python scripts/study.py tui "John 1:1-18"
   ```
2. **Navigate to verse 14**: Press `j` or the Down Arrow until verse 14 is highlighted.
3. **Inspect the Greek Verbs (Tab 1)**:
   - Look at `ἐσκήνωσεν` (*eskēnōsen*): Derived from *skēnoō*, literally meaning "to pitch a tent or tabernacle."
   - *Spiritual Insight*: Jesus did not merely visit the earth as a distant observer; He pitched His tent in our human neighborhood. Just as the Shekinah glory filled the desert tabernacle (Exodus 40:34), God's glory tabernacled in human flesh.
4. **Notice the Old Testament Sanctuary Connection**:
   - The phrase "full of grace and truth" translates *plērēs charitos kai alētheias*.
   - Look at the OT Anchor: This is the exact Greek translation of the Hebrew *rav chesed ve-’emet* ("abundant in steadfast love and faithfulness") from Exodus 34:6, when the LORD revealed His character to Moses on Mount Sinai.
   - *Insight*: In Christ, God's Sinai covenant character is revealed not on cold stone tablets, but in a living human life.
5. **Check Spirit of Prophecy Commentary (Tab 3)**:
   - Read from *The Desire of Ages*, Chapter 1 ("God With Us"):
     > *"By coming to dwell with us, Jesus was to reveal God both to men and to angels... His name shall be called Emmanuel, 'God with us.'"* (DA 19.1)
6. **Compare Translations (Press `v`)**:
   - Compare KJV "dwelt among us" with BSB and YLT "tabernacled among us."

---

### Walkthrough 2: The Righteousness of Faith (Romans 1:16–17)
*Goal: Follow Paul's train of thought on "The Just Shall Live by Faith" and connect it to Habakkuk 2:4.*

1. **Launch Romans 1**:
   ```bash
   python scripts/study.py tui "Romans 1:1-18"
   ```
2. **Trace the Argument Flow (Tab 1)**:
   - Step from verse 15 to verse 16 to verse 17.
   - Observe the `⟨Premise: γάρ⟩` markers linking every single sentence:
     - v15: Ready to preach the gospel...
     - v16: **FOR** it is the power of God unto salvation...
     - v17: **FOR** therein is the righteousness of God revealed...
3. **Jump to the Old Testament Anchor (Press `o`)**:
   - On verse 17, notice the badge `⟨OT Anchor: Habakkuk 2:4⟩`.
   - Press `o`. The workstation jumps immediately to Habakkuk 2:4 ("the just shall live by his faith").
   - Inspect the Hebrew word *’ĕmûnāh* (H0530): Notice that biblical faith is not passive mental assent, but steadfast trust and loyalty in God's promises amidst a trembling world.
   - Press `o` to return to Romans 1:17.

---

### Walkthrough 3: Christ’s Prayer for You (John 17:1–5, 21–23)
*Goal: Study Jesus' High Priestly prayer, His Trinitarian love, and His desire for unity.*

1. **Launch John 17**:
   ```bash
   python scripts/study.py tui "John 17:1-26"
   ```
2. **Examine the High Priestly Prayer**:
   - Verse 1: "Father, the hour is come; glorify thy Son..."
   - Tab 1 displays the Aorist active imperative `δόξασον` (*doxason*): Jesus speaks with holy confidence as our High Priest, offering His life for the salvation of the world.
3. **Inspect Verse 3 in the Lexicon (Tab 2)**:
   - "And this is life eternal, that they might know thee..."
   - Select `ginōskō` (G1097): Notice that this knowledge is not mere intellectual information, but intimate, experiential, covenant communion.
4. **Trace the Unity Theme (Verses 21–23)**:
   - Press `j` down to verse 21: Observe Jesus praying "that they all may be one; as thou, Father, art in me, and I in thee."
   - Tab 1 highlights the divine purpose clause `⟨Purpose: ἵνα⟩`: Believer unity is the crowning testimony that convinces the world of the Father's love.
5. **Consult EGW Commentary (Tab 3)**:
   - Read from *The Desire of Ages*, Chapter 73 ("Let Not Your Heart Be Troubled").

---

## 6. Keyboard Cheat Sheet

Keep this quick-reference guide handy beside your computer:

| Key | Action | Description |
|:---:|:---|:---|
| `j` or `↓` | Next Verse | Advance down one verse in the chapter |
| `k` or `↑` | Previous Verse | Move up one verse in the chapter |
| `PgDn` / `PgUp` | Page Down / Up | Scroll quickly through the chapter text |
| `h` or `←` | Previous Chapter | Jump backward by full chapter (also `p`) |
| `l` or `→` | Next Chapter | Jump forward by full chapter (also `n`) |
| `Space` or `Enter` | Pin Verse | Locks the inspector to current verse while scrolling |
| `1` | Tab 1: Syntax & Frames | Original languages, verbal stems, argument flow |
| `2` | Tab 2: Lexicon & Strong's | Unabridged BDB / Abbott-Smith dictionaries |
| `3` | Tab 3: Commentary | Spirit of Prophecy paragraphs & page reader |
| `4` | Tab 4: Parallel | Compare KJV, BSB, ASV, and YLT side-by-side |
| `5` | Tab 5: Search Findings | View active search and concordance results |
| `v` | Toggle Parallel View | Stacks 4 translations under each verse in the reader |
| `s` | Toggle Strong's | Displays inline Strong's concordance tags in Reader |
| `f` | Focus Mode | Toggles full-width reader (hides Study Inspector) |
| `o` | Jump OT Anchor | Jumps to quoting NT or source OT passage |
| `g` | Goto Passage / EGW | Dialog to jump to any Bible verse or EGW token (`PP 44.1`) |
| `c` | Toggle Commentary View | Toggles continuous EGW page reader vs chapter correlations |
| `t` | Cycle Theme | Switches between 7 color schemes |
| `/` | Quick Search | Search Bible text or Strong's numbers |
| `?` | Help Modal | Displays full interactive help screen |
| `q` | Quit | Safely exit the study workstation |

*Mouse Support*: You can also click directly on any verse to select it, click on inspector tabs to switch views, and scroll with your mouse wheel or trackpad.

---

## 7. Selecting Your Favorite Theme

Everyone's eyes and lighting conditions are different. Press `t` to cycle through the 7 themes:

1. **Transparent** (Default): Preserves your native terminal background and transparency.
2. **Dracula**: Dark palette with vibrant purple, pink, and cyan highlights.
3. **Catppuccin Mocha**: Soothing, warm pastel palette for eye comfort.
4. **Tokyo Night**: Clean dark theme inspired by Tokyo neon lights.
5. **Nord**: Cool Arctic blues and slate grays for focused reading.
6. **Gruvbox Dark**: Warm retro earthy tones.
7. **Solarized Dark**: Precision-engineered palette reducing eye strain.

---

## 8. Summary: Scripture in Your Hands

Ellen G. White wrote in *Christ’s Object Lessons*:

> *"The Bible is its own expositor. Scripture is to be compared with scripture. The student should learn to view the word as a whole, and to see the relation of its parts. He should gain a knowledge of its grand central theme, of God’s original purpose for the world, of the rise of the great controversy, and of the work of redemption."* (COL 128.1)

May this tool be a joyful blessing to you as you explore the living, inspired Word of God!
