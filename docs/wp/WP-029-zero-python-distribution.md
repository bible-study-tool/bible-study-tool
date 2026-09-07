# WP-029: Zero-Python Distribution — "Open the Book" Installer

status: open
scope: Pillar P (new — Public Distribution) — package the full workstation as a single downloadable application that requires no Python, no terminal fluency, and no configuration from the end user.
priority: high

## Objective

> *"What's the point of having the word and not sharing it?"*

The Adventist Bible Study Tool has reached a level of theological depth and usability that makes it genuinely valuable to anyone who wants to study Scripture seriously — pastors, Sabbath School teachers, academy students, interested seekers, anyone. But right now, the installation requirement is `git clone` + `python -m venv` + `pip install` + `bash scripts/...`. That gates the tool behind a Python/terminal literacy barrier that most of our intended audience will never cross.

This work package designs and implements a distribution path that a pastor, a grandmother, or a teenager with no computer science background can follow to get the full workstation running in under five minutes.

## The Target User

- Never opened a terminal
- Does not know what Python is
- Runs Windows, macOS, or a mainstream Linux desktop (Ubuntu, Fedora)
- Has enough disk space for the databases (~500 MB total)
- Can follow a "download this file, double-click it" instruction
- Can read a one-page illustrated quick-start card

## Proposed Distribution Approach

### Option A — PyInstaller / Nuitka Frozen Binary (Recommended for first release)

Bundle the entire Python runtime, all dependencies (Textual, SQLite, Rich), and the pre-built databases into a single self-contained executable per platform.

| Platform | Output | Size estimate |
|---|---|---|
| Windows | `AdventistBibleStudy.exe` | ~80–120 MB |
| macOS | `AdventistBibleStudy.app` (zipped) | ~90–130 MB |
| Linux | `AdventistBibleStudy.AppImage` | ~80–110 MB |

**Why Textual works frozen:** Textual uses the system terminal — it does not embed a GUI framework. The frozen binary opens the user's existing terminal emulator (Windows Terminal, Terminal.app, GNOME Terminal). This is standard practice for TUI apps.

**Database distribution:** Pre-built `data/bible.db` (KJV/ASV/BSB/YLT, 31,102 verses), `data/macula.db`, and `lexicons/` are bundled inside the binary or as a `data/` folder alongside it. `data/egw.db` is NOT bundled (copyright); the installer shows a one-click "Download Spirit of Prophecy public domain texts" button post-install.

### Option B — Docker / Container Image

A `Dockerfile` that produces a container running the workstation in a web-based terminal (ttyd or wetty), accessible at `http://localhost:8080`. Useful for servers, NAS devices (Synology, QNAP), or technically confident users who want isolation.

**Constraint:** Requires Docker Desktop — still a technical barrier. Option B is a good companion to A, not a replacement.

### Option C — GitHub/GitLab Releases with Install Script

A `install.sh` (macOS/Linux) and `install.ps1` (Windows) that:
1. Downloads the correct Python if needed (using `uv` or the official python.org installer)
2. Creates the venv and installs the package
3. Builds the databases
4. Creates a desktop shortcut / launcher

Simpler to maintain than a frozen binary but still requires some terminal interaction.

**Recommendation:** Ship Option A for Windows and macOS first (highest user count among non-technical users), then Option C as a fallback for Linux. Option B for power users.

## Implementation Tasks

### Phase 1 — Audit & Freeze Preparation
- [ ] Audit all `import` chains for dynamic imports, `__file__` path assumptions, and anything that breaks in a frozen context
- [ ] Replace any `Path(__file__).parent` relative lookups with a `_resource_path()` helper that is PyInstaller-aware
- [ ] Confirm Textual 1.x works correctly in a frozen binary (known to work; verify against our version)
- [ ] Add `pyproject.toml` `[project.scripts]` entry: `bible-study = "search.ui.app:main"` as a clean entrypoint

### Phase 2 — Database Bundling Strategy
- [ ] Define a `data/` bundle layout: `bible.db`, `macula.db`, `lexicons/` (all pre-built and gitignored raw → committed derived)
- [ ] Write `scripts/build_release_data.sh` — builds all databases from pinned sources and packages them into `dist/data/`
- [ ] Document SHA-256 of the release data bundle in `data/PROVENANCE.md`

### Phase 3 — PyInstaller Spec & Build Pipeline
- [ ] Write `bible_study.spec` (PyInstaller spec file)
- [ ] Add `scripts/build_release.sh` — cross-platform release build using PyInstaller (or Nuitka for better performance/size)
- [ ] Test frozen binary on:
  - Windows 11 (no Python installed)
  - macOS 14 Sonoma (no Python installed)
  - Ubuntu 24.04 LTS (no Python installed)
- [ ] Add a `.gitlab-ci.yml` `release` stage that builds binaries on tagged commits and uploads to GitLab Releases

### Phase 4 — User-Facing Installer Experience
- [ ] `docs/INSTALL.md` — one-page illustrated guide: "Download → Open → Start studying"
  - Windows: download `.exe`, double-click, allow Windows Defender (first run), terminal opens
  - macOS: download `.app.zip`, unzip, right-click → Open (Gatekeeper), terminal opens
  - Linux: download `.AppImage`, `chmod +x`, double-click
- [ ] First-run wizard (in the workstation itself): if `data/bible.db` is not found, show a setup screen with one button: "Build my Bible database (takes ~10 seconds)"
- [ ] Post-install EGW prompt: after first successful launch, offer one-click public-domain EGW download (10 works, ~28 seconds)
- [ ] Update `docs/USER_GUIDE.md` with the installer path as the primary entry point (terminal method as "advanced")

### Phase 5 — ADR & Governance
- [ ] Write ADR-0023 (Distribution & Packaging) documenting the frozen-binary decision, database bundling strategy, and the EGW copyright boundary in the distribution context
- [ ] Update `ROADMAP.md` Pillar P entries as tasks complete
- [ ] Tag the first public release `v0.1.0-alpha` with GitLab Releases + changelog

## Acceptance Criteria
- A person with no Python or terminal experience can get the workstation running on Windows or macOS by following a 5-step illustrated guide
- The frozen binary passes all 566 tests when run against itself (i.e., `AdventistBibleStudy --test` works)
- `data/egw.db` is NOT bundled; public-domain download is offered post-install
- Release binary size is < 150 MB compressed
- GitLab CI builds binaries automatically on `v*` tags

## Estimated Effort
- Phase 1–2: 1–2 sessions (pure engineering, no new features)
- Phase 3: 2–3 sessions (cross-platform testing is the hard part)
- Phase 4: 1 session
- Phase 5: 1 session (ADR + ROADMAP)

## Open Questions for Discussion
1. **Windows Terminal dependency**: Textual requires a modern terminal. On Windows 10 < 2019, the legacy `cmd.exe` doesn't support ANSI. Should we bundle Windows Terminal or require Windows 11?
2. **Auto-update**: Should the frozen binary check for updates on launch? If so, what channel (GitLab Releases API)?
3. **EGW public-domain scope**: The one-click download covers works published before 1929. Should we also offer a link to egwwritings.org for the full collection?
4. **Mobile / tablet**: Out of scope for this WP, but worth a future ADR.
