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

You do not need Python, Git, Docker, or any developer tools installed. Everything you need (Scripture text, original Greek and Hebrew morphological databases, Strong's lexicons, and the study engine) is included in the package.

---

## 📥 Platform Instructions

### 🪟 Windows (10 & 11)

1. **Download:** Grab `bible-study-windows-x86_64.zip` from the [Releases Page](https://gitlab.com/adventist-bible-study/bible-study-tool/-/releases).
2. **Extract:** Right-click the `.zip` file and select **Extract All...** to extract the folder.
3. **Open:** Double-click `bible-study.exe` inside the extracted folder.
4. **Study:** Your default web browser will automatically open to `http://127.0.0.1:8000` with the study workstation.

> [!NOTE]
> **Windows SmartScreen Notice:** If Windows displays a "Windows protected your PC" prompt on first launch, click **More info** and then select **Run anyway**. This is standard for independent open-source software before code signing reputation is established.

---

### 🍎 macOS (Apple Silicon & Intel)

1. **Download:** Grab `bible-study-macos-arm64.tar.gz` (M1/M2/M3) or `bible-study-macos-x86_64.tar.gz` (Intel) from the [Releases Page](https://gitlab.com/adventist-bible-study/bible-study-tool/-/releases).
2. **Extract:** Double-click the downloaded `.tar.gz` archive to extract it.
3. **Open:** Double-click `bible-study`.
4. **Study:** Your default browser opens automatically to your study desk.

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
   *(Or double-click the `bible-study` binary in your file manager.)*
4. **Study:** Your default browser opens to your study desk.

---

## 🪄 First-Run Setup Wizard

When you launch the workstation for the first time, an interactive **Setup Wizard** guides you through:

1. **Data Integrity Verification:** Checks the sidecar data bundle (`bible.db`, `macula.db`, and `lexicons/`) against authoritative SHA-256 checksums to ensure zero data corruption.
2. **Updates & Privacy Sovereignty:** Gives you complete control over update checking. Auto-updates send only a single anonymous version query to GitLab Releases. **Zero tracking, zero analytics, and zero study habits are ever sent over the network.**
3. **Historical Commentary Collection:** Outlines the 10 public-domain works of Ellen G. White (*The Great Controversy*, *The Desire of Ages*, *Steps to Christ*, etc.). If offline, you can safely skip this step and continue studying Scripture immediately.
4. **Study Tips & Official Library Link:** Provides quick keyboard shortcuts and a direct link to [egwwritings.org](https://m.egwwritings.org/) for the complete, official Spirit of Prophecy research library.

You can reopen the wizard at any time by clicking the **⚙ Setup** button in the upper-right corner of the workstation.

---

## 🔒 100% Offline & Private Guarantee

- **No Internet Required:** Once downloaded, every feature—including whole-Bible reading, King James parallel translations, Macula Hebrew/Greek lexical breakdowns, and Strong's concordance queries—works entirely offline.
- **Your Data Remains Yours:** All notes, highlights, and history are stored locally on your own machine.
- **Clean Distribution:** No proprietary or copyrighted commentary is pre-bundled in release packages.

---

## 🛠 Advanced Usage & Command-Line Options

For power users, pastors, and developers who prefer the terminal:

| Command | Description |
| :--- | :--- |
| `bible-study` | Default GUI launcher (starts background server & opens browser) |
| `bible-study --no-browser` | Starts the server without automatically opening a browser tab |
| `bible-study --host 0.0.0.0 --port 8080` | Listens on all interfaces (useful for remote servers or local networks) |
| `bible-study --tui` | Launches the interactive Terminal User Interface (TUI) |
| `bible-study read "John 1:1-5"` | Prints Scripture text and parallel translations directly to stdout |
| `bible-study word H1254` | Performs an instant lexical lookup for a Hebrew or Greek Strong's number |
| `bible-study --help` | Displays all available commands and flags |

---

## ❓ Frequently Asked Questions & Troubleshooting

### Why didn't my browser open automatically?
If your system has no default browser configured (or you are running on a headless remote server), simply open any web browser manually and navigate to:
```
http://localhost:8000
```

### How do I stop the application?
In your terminal, press `Ctrl + C`. If running in the background, closing the terminal or ending the `bible-study` process stops the server cleanly.

### Where can I get help or report an issue?
Visit our project repository at [GitLab](https://gitlab.com/adventist-bible-study/bible-study-tool) to report issues, contribute translations, or read technical architectural decision records (ADRs).
