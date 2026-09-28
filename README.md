# Adventist Bible Study Tool

<p align="center">
  <a href="https://github.com/bible-study-tool/bible-study-tool/actions/workflows/ci.yml"><img src="https://github.com/bible-study-tool/bible-study-tool/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <a href="https://github.com/bible-study-tool/bible-study-tool/releases"><img src="https://img.shields.io/github/v/release/bible-study-tool/bible-study-tool?label=desktop%20release&color=blue" alt="Latest Release"></a>
  <a href="scripts/verify_all.sh"><img src="https://img.shields.io/badge/tests-907%20passing-brightgreen" alt="Tests"></a>
  <a href="docs/INSTALL.md"><img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-informational" alt="Platforms"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT%20%2F%20CC--BY--4.0-blue.svg" alt="License"></a>
</p>

An interactive, zero-cloud biblical research workstation that brings original Biblical Hebrew and Koine Greek into plain English, cross-references all 66 books with 344,000+ reciprocal links, and unifies Scripture, parallel translations, and historical commentary on a serene desktop study desk.

> 📖 **Quick Links**:
> - **Download Desktop App**: [Latest Native Installers (v0.1.4-beta)](#download--install-native-desktop-app) for macOS, Windows, and Linux.
> - **Visual Tour & Gallery**: Browse everyday workflows and layouts in the [Visual Tour](docs/VISUAL_TOUR.md).
> - **Study Tutorials**: Step-by-step inductive study guides in the [User & Study Guide](docs/USER_GUIDE.md) and [How to Study the Bible](docs/HOW_TO_STUDY_THE_BIBLE.md).

---

## What You Can Do With It

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  [ Genesis 1:1 ]   Translations: KJV │ ASV │ BSB │ YLT   [Search: /]   [Palettes: 9]   │
├─────────────────────────────────────────────────┬──────────────────────────────────────┤
│  SCRIPTURE READING DESK                         │ STUDY ROOM INSPECTOR                 │
│                                                 │                                      │
│  1 In the beginning God created the heaven and  │ [Languages] [TSK X-Refs] [Commentary]│
│    the earth.                                   │                                      │
│                                                 │ • בְּרֵאשִׁית (bərēʾšît) — H7225       │
│  2 And the earth was without form, and void;    │   Gloss: "in the beginning"          │
│    and darkness was upon the face of the deep.  │   Stem: Qal • Finite verbal action   │
│    And the Spirit of God moved upon the face    │                                      │
│    of the waters.                               │ • 344k Reciprocal Scripture Links    │
│                                                 │   ↳ John 1:1, Col 1:16, Heb 1:2      │
│  3 And God said, Let there be light: and there  │                                      │
│    was light.                                   │ • Sanctuary Blueprint Breadcrumb     │
│                                                 │   Courtyard ➔ Holy ➔ Most Holy Place │
└─────────────────────────────────────────────────┴──────────────────────────────────────┘
```

### The 9 Research Workstations

1. **Original Languages in Plain English**:
   - Understand theological nuances without seminary training.
   - Automatically parses Hebrew verbal stems (**Qal**, **Niphal**, **Piel**, **Hiphil**, **Hitpael**) and Greek verbal aspects/voices (**Aorist Active**, **Middle Voice**, **Perfect Passive**).
   - Maps apostolic argumentation through **Pauline Argument Flow** (`⟨Premise: γάρ⟩`, `⟨Therefore: οὖν⟩`, `⟨Purpose: ἵνα⟩`, `⟨Contrast: ἀλλά⟩`).
   - One-key jump (`o`) linking New Testament quotations directly to their Old Testament Hebrew and Septuagint (LXX) source passages.

2. **Deterministic Cross-Language Unified Search (WP-039)**:
   - Sub-millisecond, multi-database search across **all 31,102 verses** (KJV), parallel translations (ASV, BSB, YLT), Macula Hebrew & Greek morphology (815,000+ linguistic tokens), Ellen G. White commentary, and curated study notes.
   - **Bidirectional Query Expansion**: Searching English concepts (e.g. *covenant*, *sanctuary*, *atonement*) automatically discovers underlying Hebrew (*bərît* H1285) and Greek (*diathēkē* G1242) roots and semantic domains.
   - **Smart Omnibox Routing**: Entering a scripture reference (e.g. `John 3:16`, `Gen 1:1-3`) navigates the Scripture reading pane; keywords or Strong's codes auto-route to the Search workstation.
   - **Fine-Grained Filter Operators**: Search with `book:genesis`, `translation:bsb`, `strong:H7225`, `domain:sanctuary`, `egw:GC`, exact quotes (`"faith without works"`), or boolean operators (`AND`, `OR`, `NOT`).

3. **Whole-Bible Treasury of Scripture Knowledge (TSK)**:
   - Over **344,000 vote-ranked reciprocal cross-reference links** spanning all 66 books and 31,102 verses, embedded locally in SQLite (`data/bible.db`).
   - Instant reciprocal discovery: see every verse in the Bible that interprets or echoes the passage you are studying.

4. **Multi-Translation Parallel Reading Desk**:
   - Side-by-side or stacked comparative reading across 4 public-domain translations:
     - **King James Version (KJV 1769)** with Strong's number alignments.
     - **Berean Standard Bible (BSB 2020)**.
     - **American Standard Version (ASV 1901)**.
     - **Young's Literal Translation (YLT 1898)**.
   - Classical biblical typography with small-caps Tetragrammaton YHWH (`LORD` / `GOD`) and italicized supplied words.

5. **Interactive Sanctuary Typology Blueprint & Plan of Salvation**:
   - Interactive vector floorplan detailing the biblical sanctuary compartments (Courtyard, Holy Place, Most Holy Place), furniture, and sacrificial rituals.
   - Chronological **Plan of Salvation slider** traversing salvation history:
     $$\text{AD 31 Cross} \longrightarrow \text{Heavenly Inauguration} \longrightarrow \text{1844 Judgment} \longrightarrow \text{Second Coming} \longrightarrow \text{New Earth}$$
   - In-text verse badges linking theological doctrines directly to their sanctuary stations.

6. **Master Prophetic Key Table & Apocalyptic Symbol Chaining**:
   - Historicist apocalyptic symbol decoder for Daniel and Revelation.
   - Links apocalyptic beasts, horns, wings, waters, time periods (1,260 days, 2,300 evenings/mornings), and trumpets directly to their defining Old Testament keys and historical consensus citations.

7. **Spirit of Prophecy Progressive Narrative Reader**:
   - In-browser reading drawer with physical printed pagination fidelity matching the published books (e.g., `PP 44.1`, `DA 19.1`, `GC 623.2`).
   - Sequential chapter traversal (`‹ Prev / Next ›`) and direct canonical citation jumps.

8. **9 Study Room Color Palettes & Classical Typography**:
   - Designed for long, distraction-free study sessions without eye fatigue:
     - **Warm Palettes**: Warm Sepia, Dark Walnut (default Study Room Desk).
     - **Dark Themes**: Dracula, Catppuccin Mocha, Tokyo Night, Nord, Gruvbox Dark, Solarized Dark.
     - **Light Theme**: Clean archival parchment.
   - Draggable 65/35 split-pane, Fullscreen Focus Mode (`f`), Panel Zoom (`z`), and WCAG AAA compliant contrast.

9. **Terminal Power Workstation (TUI Companion)**:
   - For keyboard-driven study and SSH sessions, a full-screen [Textual](https://textual.textualize.io/) terminal app (`bible-study --tui`) is built right in.
   - Instant sub-millisecond viewport switching, full keyboard navigation (`j`/`k`, `h`/`l`, `1`–`6` tabs, `v` translations, `t` themes, `?` help).

---

## Download & Install (Native Desktop App)

Release **v0.1.4-beta** delivers native, single-click desktop applications with zero terminal commands required:

| Platform | Installer Format | Architecture | Download Link |
| :--- | :--- | :--- | :--- |
| **macOS** | `.dmg` drag-and-drop | Apple Silicon (M1/M2/M3/M4) | [Download .dmg](https://github.com/bible-study-tool/bible-study-tool/releases/download/v0.1.4-beta/Adventist.Bible.Study_0.1.4_aarch64.dmg) |
| **Windows** | `.exe` NSIS setup | 64-bit x86_64 | [Download .exe](https://github.com/bible-study-tool/bible-study-tool/releases/download/v0.1.4-beta/Adventist.Bible.Study_0.1.4_x64-setup.exe) |
| **Windows** | `.msi` package | 64-bit x86_64 | [Download .msi](https://github.com/bible-study-tool/bible-study-tool/releases/download/v0.1.4-beta/Adventist.Bible.Study_0.1.4_x64_en-US.msi) |
| **Linux** | `.AppImage` standalone | 64-bit x86_64 | [Download .AppImage](https://github.com/bible-study-tool/bible-study-tool/releases/download/v0.1.4-beta/Adventist.Bible.Study_0.1.4_amd64.AppImage) |
| **Linux** | `.deb` Debian/Ubuntu | 64-bit x86_64 | [Download .deb](https://github.com/bible-study-tool/bible-study-tool/releases/download/v0.1.4-beta/Adventist.Bible.Study_0.1.4_amd64.deb) |
| **Portable** | `.zip` (Win) / `.tar.gz` (Linux/Mac) | Portable USB / Zero-Python | [GitHub Releases](https://github.com/bible-study-tool/bible-study-tool/releases/tag/v0.1.4-beta) |

For detailed step-by-step instructions, see the [Installation Guide](docs/INSTALL.md).

---

## Workstation Tour & Screenshots

*Detailed screenshot walkthroughs and high-resolution captures are in [docs/VISUAL_TOUR.md](docs/VISUAL_TOUR.md).*

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          [ WORKSTATION GALLERY ]                         │
│                                                                          │
│   [ 1. Reading Desk & Inspector ]     [ 2. Sanctuary Plan of Salvation ] │
│   [ 3. Cross-Language Search ]        [ 4. Multi-Translation Matrix ]    │
│   [ 5. Apocalyptic Prophetic Keys ]   [ 6. Terminal TUI Interface ]      │
└──────────────────────────────────────────────────────────────────────────┘
```

*(To add or view community screenshots and workflow recordings, see [docs/VISUAL_TOUR.md](docs/VISUAL_TOUR.md).)*

---

## For Developers & Power Users

### 1. Automated Clone & Bootstrap

```bash
git clone https://github.com/bible-study-tool/bible-study-tool.git
cd bible-study-tool

# One-command bootstrap (creates .venv, installs dependencies, hydrates SQLite databases, and verifies):
./bootstrap.sh --data --verify
```

### 2. Launch the Application

```bash
# Launch the desktop web interface:
python -m search.ui.web
# (or with the installed CLI entrypoint: bible-study)

# Launch the interactive terminal TUI:
python scripts/study.py tui "John 1"
python scripts/study.py tui "Genesis 1"
```

### 3. Unified CLI Search & Linguistic Tools

```bash
# Unified cross-source search (Scripture + parallel translations + commentary):
python scripts/study.py search "covenant" --book genesis --limit 10

# Original-language lexicon lookup:
python scripts/study.py word H7225    # Hebrew: bereshit
python scripts/study.py word G3056    # Greek: logos

# Passagewise grammatical study cards:
python scripts/study.py study "John 1:1-5"

# Interactive study shell:
python scripts/study.py shell
```

### 4. Full Verification Suite

The repository enforces strict data integrity via 5 automated validators and full test coverage:

```bash
bash scripts/verify_all.sh
```
*(Runs 907 unit and integration tests, F1–F6 schema/integrity validators, and raw source cryptographic checksum gates.)*

---

## Architectural Principles & Integrity

1. **Deterministic Core is the Source of Truth**:
   The core is 100% deterministic and runs entirely offline. AI is strictly an optional research assistant; any AI-suggested semantic links are placed in a provisional review queue and gated behind human review before entering the knowledge base ([correlations/DETERMINISTIC_VS_AI.md](correlations/DETERMINISTIC_VS_AI.md)).
2. **Offline-First & Zero Telemetry**:
   All Scripture databases, lexicons, syntax trees, and commentary indexes reside locally on your machine. No telemetry, no usage tracking, no remote logging ([ADR-023](docs/decisions/ADR-023-zero-python-distribution-and-packaging.md)).
3. **Cryptographic Data Integrity (ADR-027)**:
   All SQLite databases (`bible.db`, `macula.db`, `egw.db`) are validated with canonical content-level SHA-256 projections (`data/INTEGRITY.json`) so they remain reproducible across different platforms, compilers, and architectures.

---

## Sourcing External Materials (What We Bundle & What You Supply)

We strictly follow the architectural policy: **"Link out, don't redistribute"** ([NOTICE.md](NOTICE.md), [ADR-002](docs/decisions/ADR-002-licensing-and-content-sourcing.md), [ADR-011](docs/decisions/ADR-011-whole-book-scaffolding-and-jit-egw.md)). This keeps the Git repository 100% license-clean under MIT and CC BY 4.0 while enabling powerful, offline, full-text research.

### What is bundled in the repository:
* **The Bible Text & TSK Cross-References**: All 66 books (31,102 verses) in local SQLite (`data/bible.db`) containing KJV (1769 with Strong's tags), BSB (2020), ASV (1901), YLT (1898), and 344k+ TSK cross-reference pairs.
* **Curated Corpus Entries**: Human-curated study entries for Genesis 1–3 and John 1 & 17 (`materials/bible/`), plus draft skeletons for Genesis 4–50.
* **Linguistic Data (Macula)**: Clear-Bible Macula Hebrew MT & Greek NT (Nestle 1904) Lowfat syntax trees, clause roles, and Louw-Nida semantic domains (`data/macula.db`).
* **Lexical Artifacts**: Strong's Hebrew & Greek lexicons, Brown-Driver-Briggs (BDB), Abbott-Smith Greek Lexicon, STEPBible TBESH/TBESG glosses, and the Genesis WordGraph.
* **Theological Schemas**: Historicist prophetic symbol table (`data/prophetic_lexicon.json`) and sanctuary typology blueprint (`data/sanctuary_schema.json`).

### What is NOT bundled (and how to supply it):
1. **Ellen G. White / Spirit of Prophecy Texts**:
   - *Why not bundled*: Works published after 1928 are protected under active copyright held by the Ellen G. White Estate.
   - *Official Online Research*: [egwwritings.org](https://m.egwwritings.org/). Public domain historical editions (prior to 1929) are available at the [Adventist Digital Library](https://adventistdigitallibrary.org/) and the [Internet Archive](https://archive.org/).
   - *How to use locally*: Repository entries store only canonical citation tokens (`egw:BOOK.PAGE.PARA`, e.g. `egw:PP.57.1`). If you have exported study passages in JSON format, ingest them locally with `python scripts/egw_lookup.py --ingest-json /path/to/passages.json`.
2. **Modern Copyrighted Translations**:
   - Modern translations (NIV, ESV, NASB, NKJV) belong to their respective publishers. Users supply personal translation files on-device; computations run strictly locally.
3. **Notice Regarding Scraping**:
   - This project does not ship automated bulk web scrapers for commercial or proprietary websites. Standardizing on canonical tokens honors copyright law while providing an offline research workstation.

---

## Documentation & Reference Index

| Document | Purpose |
| :--- | :--- |
| [Installation Guide](docs/INSTALL.md) | Step-by-step desktop setup for Windows, macOS, and Linux |
| [Visual Tour](docs/VISUAL_TOUR.md) | High-resolution screenshots of the workstation in everyday use |
| [User & Study Guide](docs/USER_GUIDE.md) | Practical study walkthroughs, features, and keyboard shortcuts |
| [How to Study the Bible](docs/HOW_TO_STUDY_THE_BIBLE.md) | Inductive Bible study methods, word studies, and sanctuary typology |
| [Architecture Decisions (ADRs)](docs/decisions/INDEX.md) | 28 formal architecture decision records (ADR-001 through ADR-028) |
| [Work Packages (WPs)](docs/wp/INDEX.md) | Tracked engineering milestones and delivered work packages (WP-001..039) |
| [Workflow & Engineering Guide](docs/WORKFLOW.md) | Engineering workflow, subagent reviews, and verification standards |
| [Tag Taxonomy](tags/taxonomy.json) | Controlled vocabulary for books, themes, and relationship types |
| [Roadmap](ROADMAP.md) | Living goal inventory, current progress, and sequenced milestones |

---

## License

This repository is dual-licensed by component:
- **Code** (the `search/` engine, scripts, and desktop app): [MIT License](LICENSE)
- **Original Content** (concordance data, semantic links, cross-references, taxonomies, and study notes): [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE.content)

See [NOTICE.md](NOTICE.md) for doctrinal foundations and content sourcing policies.
