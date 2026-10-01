# Download Adventist Bible Study Tool

<p align="center">
  <strong>Native, zero-cloud desktop application for in-depth biblical research.</strong><br>
  Runs 100% offline on your device with no accounts, no subscriptions, no tracking, and no cloud required.
</p>

<p align="center">
  <a href="https://github.com/bible-study-tool/bible-study-tool/releases/latest">
    <img src="https://img.shields.io/github/v/release/bible-study-tool/bible-study-tool?label=Latest%20Version&color=success&style=for-the-badge" alt="Latest Release">
  </a>
</p>

---

## ⚡ Direct Desktop Downloads (Latest Release)

Select the package for your computer below. Each package is a standalone application that includes Scripture (66 books), parallel translations, Strong's lexicons, and the complete study desk.

### 🍎 macOS
*For Apple Silicon Macs (M1, M2, M3, M4, Mac mini, MacBook Air/Pro, iMac, Mac Studio).*

| Package | Format | Direct Download |
| :--- | :--- | :--- |
| **macOS Native App** | `.dmg` Drag & Drop Installer | [**Download for macOS (Apple Silicon)**](https://github.com/bible-study-tool/bible-study-tool/releases/latest) |
| **macOS Portable Archive** | `.tar.gz` | [**Download .tar.gz Archive**](https://github.com/bible-study-tool/bible-study-tool/releases/latest) |
| **macOS Setup Helper** | `.command` Script | [**Download install-macos.command**](https://github.com/bible-study-tool/bible-study-tool/releases/latest) |

> [!IMPORTANT]
> **First-Time macOS Opening ("App is damaged and can't be opened"):**
> Because this is a free, non-profit community project built for Christian study, we do not pay Apple's $99/year commercial developer fee. When you first open the app on macOS, Apple Gatekeeper may show:
>
> *"Adventist Bible Study is damaged and can't be opened. You should move it to the Trash."*
>
> **How to open in 5 seconds (choose any method):**
>
> - **Method 1 (Automatic Setup Script — Recommended):**
>   1. Download [`install-macos.command`](https://github.com/bible-study-tool/bible-study-tool/releases/latest) (or use the one included in your downloaded archive).
>   2. **Right-click (Control-click)** `install-macos.command` ➔ select **Open** ➔ click **Open**.
>   3. The script automatically installs the app to your `Applications` folder, removes Apple's quarantine flag (`com.apple.quarantine`), applies a local signature, and launches the app!
>
> - **Method 2 (Terminal — 1 Quick Command):**
>   If you already dragged the app into `Applications`, open Terminal (Cmd+Space, type `Terminal`) and paste:
>   ```bash
>   xattr -cr "/Applications/Adventist Bible Study.app"
>   ```
>   Press Enter. The app will now open immediately like any other Mac application.
>
> - **Method 3 (System Settings — No Script or Terminal):**
>   1. Drag **Adventist Bible Study** into your **Applications** folder.
>   2. Double-click it once (it will show the warning; click **Cancel**).
>   3. Open **System Settings** ➔ **Privacy & Security**.
>   4. Scroll down to the **Security** section. You will see: *"Adventist Bible Study was blocked to protect your Mac."*
>   5. Click **"Open Anyway"** and enter your password. You only have to do this once!

---

### 🪟 Windows
*For 64-bit Windows 10 and Windows 11.*

| Package | Format | Direct Download |
| :--- | :--- | :--- |
| **Windows Setup Wizard** | `.exe` Setup Installer | [**Download Windows Setup (.exe)**](https://github.com/bible-study-tool/bible-study-tool/releases/latest) |
| **Windows MSI Package** | `.msi` Enterprise / Admin | [**Download Windows MSI (.msi)**](https://github.com/bible-study-tool/bible-study-tool/releases/latest) |
| **Windows Portable USB** | `.zip` (No install required) | [**Download Portable .zip**](https://github.com/bible-study-tool/bible-study-tool/releases/latest) |

> [!NOTE]
> **Windows SmartScreen Prompt:**
> When opening the `.exe` setup for the first time, Windows Defender SmartScreen may display:
> *"Windows protected your PC — Microsoft Defender SmartScreen prevented an unrecognized app from starting."*
>
> Simply click **"More info"** and then click **"Run anyway"**.

---

### 🐧 Linux
*For Ubuntu, Debian, Fedora, Arch, Linux Mint, Pop!_OS, and other 64-bit distributions.*

| Package | Format | Direct Download |
| :--- | :--- | :--- |
| **Linux AppImage** | `.AppImage` (Run anywhere) | [**Download .AppImage**](https://github.com/bible-study-tool/bible-study-tool/releases/latest) |
| **Debian / Ubuntu Package** | `.deb` package | [**Download .deb**](https://github.com/bible-study-tool/bible-study-tool/releases/latest) |
| **Linux Standalone Tarball** | `.tar.gz` | [**Download .tar.gz**](https://github.com/bible-study-tool/bible-study-tool/releases/latest) |

> [!TIP]
> **Running the AppImage:**
> Right-click the `.AppImage` file ➔ **Properties** ➔ **Permissions** ➔ check **"Allow executing file as program"** (or run `chmod +x Adventist*.AppImage` in terminal), then double-click to launch.

---

## 🔒 Verification & Cryptographic Checksums

Every release asset is accompanied by a SHA-256 checksum file (`.sha256`) on the [GitHub Releases page](https://github.com/bible-study-tool/bible-study-tool/releases/latest). You can verify the integrity of your download at any time:

- **macOS / Linux**:
  ```bash
  sha256sum Adventist_Bible_Study*.dmg
  # or on macOS:
  shasum -a 256 Adventist_Bible_Study*.dmg
  ```
- **Windows (PowerShell)**:
  ```powershell
  Get-FileHash -Algorithm SHA256 .\Adventist_Bible_Study*.exe
  ```

---

## 📚 What's Included in the Box?

- **Scripture Core**: Full 66-book King James Version (KJV 1769) with inline Strong's number alignments.
- **Parallel Translations**: Berean Standard Bible (BSB), American Standard Version (ASV), Young's Literal Translation (YLT).
- **Original Language Morphological Databases**: 815,000+ Hebrew, Aramaic, and Greek linguistic tokens with verbal stems, moods, voices, and glosses.
- **Whole-Bible Cross-References**: 344,000+ reciprocal Treasury of Scripture Knowledge (TSK) links.
- **Sanctuary Blueprint**: Interactive floorplan with chronological Plan of Salvation timeline.
- **Prophetic Key Table**: Historicist apocalyptic symbol chaining for Daniel and Revelation.
- **Offline Semantic Search**: 384-dimensional dense vector embeddings with zero cloud / zero telemetry.

Need help building from source or running the Terminal TUI? See the [Developer Installation Guide](INSTALL.md).
