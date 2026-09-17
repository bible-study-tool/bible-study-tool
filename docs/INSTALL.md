# Installation & Quick Start Guide: Adventist Bible Study Tool

*A simple, one-page guide to getting started with the Adventist Bible Study Tool on Windows, macOS, and Linux — zero programming, zero terminal, and zero Python required.*

---

## 🚀 The Three-Step Quick Start

```
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│  1. DOWNLOAD         │ ──> │  2. DOUBLE-CLICK     │ ──> │  3. START STUDYING   │
│  Release package for │     │  Launch the study    │     │  Browser opens       │
│  your platform       │     │  workstation app     │     │  to your study desk  │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

You **do not need** Python, Git, Docker, or any developer tools installed. Everything you need—Scripture text (66 books), original Hebrew and Greek morphological databases, Strong's lexicons, prophetic key tables, and the local study engine—is pre-packaged and ready to run.

---

## 📥 Platform Instructions

### 🪟 Windows (10 & 11)

1. **Download:** Grab `bible-study-windows-x86_64.zip` from the [Releases Page](https://gitlab.com/adventist-bible-study/bible-study-tool/-/releases).
2. **Extract:** Right-click the `.zip` file and select **Extract All...** to extract the folder.
3. **Open:** Double-click `bible-study.exe` inside the extracted folder.
4. **Study:** Your default web browser will automatically open to `http://localhost:8000` with your study workstation.

> [!NOTE]
> **Windows SmartScreen Notice:** If Windows displays a "Windows protected your PC" prompt on first launch, click **More info** and then select **Run anyway**. This is standard for independent open-source software before code signing reputation is established.

---

### 🍎 macOS (Apple Silicon & Intel)

1. **Download:** Grab `bible-study-macos-arm64.tar.gz` (Apple Silicon M1/M2/M3/M4) or `bible-study-macos-x86_64.tar.gz` (Intel) from the [Releases Page](https://gitlab.com/adventist-bible-study/bible-study-tool/-/releases).
2. **Extract:** Double-click the downloaded `.tar.gz` archive to extract it.
3. **Open:** Double-click `bible-study`.
4. **Study:** Your default browser opens automatically to your study desk at `http://localhost:8000`.

> [!NOTE]
> **macOS Gatekeeper Notice:** If macOS warns that the developer cannot be verified, right-click (or Control-click) `bible-study`, select **Open**, and click **Open** in the dialog.

---

### 🐧 Linux (x86_64)

1. **Download:** Grab `bible-study-linux-x86_64.tar.gz` from the [Releases Page](https://gitlab.com/adventist-bible-study/bible-study-tool/-/releases).
2. **Extract:** Extract the archive:
   ```bash
   tar -xzf bible-study-linux-x86_64.tar.gz
   cd bible-study-linux-x86_64
   ```
3. **Open:** Run the executable:
   ```bash
   ./bible-study
   ```
   *(Or double-click the `bible-study` binary in your desktop file manager.)*
4. **Study:** Your default browser opens to your study desk at `http://localhost:8000`.

---

## 🪄 First-Run Setup Wizard

When you launch the workstation for the first time, an interactive **Setup Wizard** guides you through four simple steps:

1. **Cryptographic Data Integrity:** Automatically verifies the core data bundle (`data/bible.db`, `data/macula.db`, and `lexicons/`) against authoritative SHA-256 hashes in `data/INTEGRITY.json` (ADR-006, ADR-024, ADR-025, ADR-027) to ensure zero corruption.
2. **Appearance & Visual Theme:** Choose your preferred reading environment:
   - **Sepia (Study Room Desk)** *(Default)*: Warm parchment tone designed for low glare and long study sessions.
   - **Light Paper**: Crisp daylight paper contrast for bright rooms.
   - **Dark Walnut (Study Room Night)**: Rich charcoal-walnut substrate for comfortable evening reading.
   - *Auto-update checking with zero-telemetry guarantee*: Only queries the public release tag; no personal data, IP logs, or reading habits are ever transmitted.
3. **Historical Commentary Collection:** Outlines the 10 pre-1929 public-domain works of Ellen G. White (*The Great Controversy*, *The Desire of Ages*, *Steps to Christ*, etc.). Includes an interactive drag-and-drop book dropzone supporting `.epub`, `.txt`, `.md`, `.json`, `.zip`, or `egw.db`. If you are offline, you can safely skip this step and study Scripture immediately.
4. **Study Tips & Official Library Link:** Displays essential keyboard shortcuts and a direct link to [egwwritings.org](https://m.egwwritings.org/) for the complete, official published research library.

You can reopen the wizard or change settings at any time by clicking the **⚙ Settings** button in the upper-right corner of the workstation.

---

## 🔒 100% Offline & Private Guarantee

- **No Internet Required:** Once downloaded, every feature—including whole-Bible reading, King James parallel translations, Macula Hebrew/Greek lexical breakdowns, Strong's concordance queries, Sanctuary blueprint, and Prophetic Key Table—works entirely offline.
- **Your Data Remains Yours:** All notes, highlights, and history are stored locally on your own machine.
- **Sidecar-Free Guarantee (ADR-027):** Reads leave zero temporary SQLite `-wal` or `-shm` sidecar files behind, preventing database lockups and filesystem clutter.
- **Clean Distribution:** No proprietary or copyrighted commentary is pre-bundled in release packages, ensuring full legal and copyright compliance.

---

## 🛠 Advanced Usage & Command-Line Options

### For Developers & Power Users (Command Line & TUI)

If you prefer operating from a terminal emulator, the binary supports rich command-line and interactive TUI modes:

| Command | Description |
| :--- | :--- |
| `bible-study` | Default GUI launcher (starts local background server & opens browser) |
| `bible-study --no-browser` | Starts the local server without automatically opening a browser window |
| `bible-study --host 0.0.0.0 --port 8080` | Binds to custom network interface or port (useful for home servers) |
| `bible-study --tui` | Launches the interactive Terminal User Interface (TUI companion) |
| `bible-study tui "John 1:1-18"` | Opens the TUI directly to a specific passage |
| `bible-study read "John 1:1-5"` | Prints Scripture text with translation comparisons directly to stdout |
| `bible-study word H1254` | Performs an instant lexical lookup for a Hebrew or Greek Strong's number |
| `bible-study search "grace" --theme=theme/grace` | Searches the curated corpus by query and facet (theme, book, status, translation) |
| `bible-study --help` | Displays all available subcommands and flags |

---

## 💻 Developer Quickstart (Running from Source)

If you are developing features or running directly from the Git repository:

```bash
# 1. Clone the repository
git clone https://gitlab.com/adventist-bible-study/bible-study-tool.git
cd bible-study-tool

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies in editable mode
pip install -e .

# 4. Launch the local web workstation
python -m search.ui.web

# Or launch the interactive terminal interface
python scripts/study.py tui "John 1:1-18"

# 5. Run the complete test and verification suite
bash scripts/verify_all.sh
```

---

## ❓ Frequently Asked Questions & Troubleshooting

### Why didn't my browser open automatically?
If your system has no default browser configured (or you are working on a headless remote server), open any web browser manually and navigate to:
```
http://localhost:8000
```

### Port 8000 is already in use by another program. What do I do?
Launch the application with a custom port number:
```bash
bible-study --port 8080
# or from source:
python -m search.ui.web --port 8080
```
Then navigate to `http://localhost:8080` in your browser.

### How do I stop the application?
In the terminal where the program was launched, press `Ctrl + C`. If running in the background, closing the terminal window stops the server cleanly.

### Where can I learn how to use all the study tools?
- **[User & Study Guide (docs/USER_GUIDE.md)](USER_GUIDE.md)**: Detailed explanation of all 8 core comprehension tools and 5 step-by-step study walkthroughs.
- **[Visual Tour (docs/VISUAL_TOUR.md)](VISUAL_TOUR.md)**: Screenshots of Focus Mode, Syntax inspector, Parallel translations, and Sanctuary blueprint.
- **[How to Study the Bible Deeply (docs/HOW_TO_STUDY_THE_BIBLE.md)](HOW_TO_STUDY_THE_BIBLE.md)**: Foundational exegesis methods grounded in the Adventist historicist framework.
- **[GitLab Repository](https://gitlab.com/adventist-bible-study/bible-study-tool)**: Report issues, inspect Architectural Decision Records (ADRs), or contribute code.
