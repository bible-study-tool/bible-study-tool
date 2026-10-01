# Installation & Quick Start Guide: Adventist Bible Study Tool

*A simple, practical guide to downloading, opening, and using the Adventist Bible Study Tool on macOS, Windows, and Linux — zero programming, zero terminal, and zero Python required.*

---

## 🚀 The Three-Step Quick Start

```
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│  1. DOWNLOAD         │ ──> │  2. LAUNCH           │ ──> │  3. START STUDYING   │
│  Native desktop app  │     │  Double-click the    │     │  Your study desk     │
│  for your computer   │     │  app icon            │     │  opens instantly     │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

You **do not need** developer tools or programming experience to run the workstation. Everything you need—Scripture text (all 66 books), parallel translations (BSB, ASV, YLT), original Hebrew and Greek morphological databases, Strong's lexicons, prophetic key tables, and the local study engine—is included in the package.

> [!TIP]
> Looking for quick direct download links? Visit the **[Downloads Portal (docs/DOWNLOADS.md)](DOWNLOADS.md)** or grab the latest release from **[GitHub Releases](https://github.com/bible-study-tool/bible-study-tool/releases/latest)**.

---

## 📥 Desktop App Installation by Platform

### 🍎 macOS (Apple Silicon M1 / M2 / M3 / M4)

1. **Download:** Grab the latest `.dmg` installer from [GitHub Releases](https://github.com/bible-study-tool/bible-study-tool/releases/latest) (e.g. `Adventist_Bible_Study_0.1.4_aarch64.dmg`).
2. **Install:** Double-click the downloaded `.dmg` file and drag **Adventist Bible Study** into your **Applications** folder.
3. **Open:** Open your **Applications** folder and double-click **Adventist Bible Study**.

> [!IMPORTANT]
> **First-Time macOS Warning ("App is damaged and can't be opened"):**
> Because this is a free, non-profit community project built for Christian study, we do not pay Apple's $99/year commercial developer fee to notarize binaries. When opening on macOS for the first time, Apple Gatekeeper may show:
>
> *"Adventist Bible Study is damaged and can't be opened. You should move it to the Trash."*
>
> **How to open in 5 seconds (choose either method):**
>
> - **Method A (System Settings — No Terminal):**
>   1. Double-click the app in `/Applications` (it shows the warning dialog; click **Cancel**).
>   2. Open your Mac's **System Settings** ➔ **Privacy & Security**.
>   3. Scroll down to the **Security** section. You will see: *"Adventist Bible Study was blocked to protect your Mac."*
>   4. Click **"Open Anyway"** and enter your Mac password. You only have to do this once!
>
> - **Method B (Terminal — 1 Line):**
>   Open Terminal (press Cmd+Space, type `Terminal`) and paste:
>   ```bash
>   xattr -cr "/Applications/Adventist Bible Study.app"
>   ```
>   Press Enter. The app will open immediately without any warnings.

---

### 🪟 Windows (Windows 10 & 11, 64-bit)

1. **Download:** Grab the latest `.exe` setup installer or portable `.zip` from [GitHub Releases](https://github.com/bible-study-tool/bible-study-tool/releases/latest) (e.g. `Adventist_Bible_Study_0.1.4_x64-setup.exe`).
2. **Install:** Double-click the setup file and follow the standard installation wizard.
3. **Open:** Launch **Adventist Bible Study** from your Start Menu or Desktop shortcut.

> [!NOTE]
> **Windows SmartScreen Prompt:**
> If Windows Defender SmartScreen shows *"Windows protected your PC"*, simply click **"More info"** and then **"Run anyway"**.

---

### 🐧 Linux (64-bit Ubuntu, Debian, Fedora, Arch, Mint, etc.)

We provide both an `.AppImage` (runs on any modern Linux distribution) and a native `.deb` package:

- **AppImage (Universal):**
  1. Download the `.AppImage` file from [GitHub Releases](https://github.com/bible-study-tool/bible-study-tool/releases/latest).
  2. Make it executable:
     ```bash
     chmod +x Adventist_Bible_Study*.AppImage
     ```
  3. Double-click or run `./Adventist_Bible_Study*.AppImage`.

- **Debian / Ubuntu (.deb):**
  ```bash
  sudo dpkg -i Adventist_Bible_Study*.deb
  # If any system webkit dependencies are needed:
  sudo apt-get install -f
  ```

---

## 🪄 First-Run Setup Wizard

When you launch the workstation for the first time, a gentle **Setup Wizard** introduces your study desk:

1. **Cryptographic Data Integrity:** Automatically checks the core data bundle (`data/bible.db`, `data/macula.db`, and `lexicons/`) against authoritative SHA-256 hashes in `data/INTEGRITY.json` to verify that no files were corrupted during download.
2. **Appearance & Visual Theme:** Choose your preferred reading environment:
   - **Sepia (Study Room Desk)** *(Default)*: Warm parchment tone designed for low glare and long, peaceful study sessions.
   - **Light Paper**: Crisp daylight contrast for bright study environments.
   - **Dark Walnut**: Deep charcoal-walnut substrate for comfortable evening reading.
   - *Strong's Numbers & Content Font Scale*: Configure your reading font size and inline Strong's number visibility.
3. **Historical Commentary Collection:** Outlines the pre-1929 public-domain works of Ellen G. White (*The Great Controversy*, *The Desire of Ages*, *Steps to Christ*, etc.). Includes an interactive drag-and-drop book dropzone supporting `.epub`, `.txt`, `.md`, `.json`, `.zip`, or `egw.db`. If you are offline, you can safely skip this step and study Scripture immediately.
4. **Study Tips & Official Library Link:** Displays essential keyboard shortcuts and a direct link to [egwwritings.org](https://m.egwwritings.org/) for the complete, official published research library.

You can reopen the wizard or change settings at any time by clicking the **⚙ Settings** button in the upper-right corner of the workstation.

---

## 🔒 100% Offline & Private Guarantee

- **No Internet Required:** Once downloaded, every feature—including whole-Bible reading, parallel translations, Macula Hebrew/Greek lexical breakdowns, Strong's concordance queries, Sanctuary blueprint, and Prophetic Key Table—works entirely offline.
- **Your Data Remains Yours:** All notes, highlights, and history are stored locally on your own machine.
- **Zero Generative Hallucination:** The search engine uses local mathematical vector geometry (multilingual E5 dense embeddings on CPU) and SQLite BM25 indexing. No AI chatbots, no synthetic text fabrication, and zero telemetry.
- **Sidecar-Free Guarantee (ADR-027):** Reads leave zero temporary SQLite `-wal` or `-shm` sidecar files behind, preventing database lockups and filesystem clutter.

---

## 💻 Developer Quickstart (Running from Source)

If you are developing features or prefer running directly from a Git clone:

### Prerequisites
- **Python 3.10 or higher**: macOS Sonoma ships with Python 3.9 and no `/usr/bin/python`. If needed, install modern Python via Homebrew (`brew install python`) or from [python.org](https://www.python.org/downloads/).
- **Git**

```bash
# 1. Clone the repository
git clone https://github.com/bible-study-tool/bible-study-tool.git
cd bible-study-tool

# 2. Automated one-command bootstrap (creates .venv, installs dependencies, hydrates databases, and verifies):
./bootstrap.sh --data --verify

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Launch the desktop web interface
python -m search.ui.web
# Or run with the installed console entrypoint:
bible-study
# (Alternatively, run directly without activating: .venv/bin/python -m search.ui.web)

# Or launch the interactive terminal TUI:
python scripts/study.py tui "John 1:1-18"

# 5. Run the complete test and verification suite
bash scripts/verify_all.sh
```

---

## ❓ Frequently Asked Questions & Troubleshooting

### Why did macOS say the app is "damaged"?
Apple attaches an internet quarantine flag to any application downloaded via a web browser that is not notarized with a paid Apple Developer certificate. Running `xattr -cr "/Applications/Adventist Bible Study.app"` or clicking **"Open Anyway"** in **System Settings ➔ Privacy & Security** clears the quarantine attribute.

### How do I scale the Scripture reading text without changing the UI buttons?
Use the keyboard shortcuts `<kbd>+</kbd>` to increase reading text size, `<kbd>-</kbd>` to decrease, and `<kbd>0</kbd>` to reset to 100%. You can also adjust font scale anytime inside **⚙ Settings** or Step 2 of the **Setup Wizard**.

### How do I switch side panel tabs quickly?
Press number keys `<kbd>1</kbd>` through `<kbd>8</kbd>`:
- `1`: Translations
- `2`: Languages (Hebrew/Greek)
- `3`: Cross-References (TSK)
- `4`: Prophetic Keys
- `5`: Sanctuary Blueprint
- `6`: Commentary
- `7`: Study Notes
- `8`: Search Workstation

Press `<kbd>?</kbd>` anywhere in the app to view the complete keyboard shortcuts cheat sheet.

### Where can I learn how to use all the study tools?
- **[User & Study Guide (docs/USER_GUIDE.md)](USER_GUIDE.md)**: Comprehensive explanation of all 8 core comprehension tools and 5 step-by-step study walkthroughs.
- **[Downloads Portal (docs/DOWNLOADS.md)](DOWNLOADS.md)**: Direct download links and platform packages.
- **[Visual Tour (docs/VISUAL_TOUR.md)](VISUAL_TOUR.md)**: Visual walkthrough of the study desk layout and features.
- **[How to Study the Bible Deeply (docs/HOW_TO_STUDY_THE_BIBLE.md)](HOW_TO_STUDY_THE_BIBLE.md)**: Foundational exegesis methods grounded in the Adventist historicist framework.
- **[GitHub Repository](https://github.com/bible-study-tool/bible-study-tool)**: Report issues, inspect Architectural Decision Records (ADRs), or contribute code.
