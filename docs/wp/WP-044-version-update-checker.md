# WP-044: Version Update Checker & GUI Notification Banner

status: complete
scope: Pillar D (D2, D3), Pillar E (E3), Pillar P (P5) — Implement automated, zero-telemetry application update checking against public GitHub Releases, providing a dismissible notification banner in the web/desktop workstation and manual "Check for Updates" control in Settings, strictly honoring the existing user opt-out toggle.
priority: medium

## Objective

Provide clear, non-intrusive visibility to users when a newer version of the Adventist Bible Study Tool is released:
1. **Zero-Telemetry Version Check:** Query only public release tags (`https://api.github.com/repos/bible-study-tool/bible-study-tool/releases/latest`) using standard library HTTP requests. Absolutely zero personal information, IP logs, queries, system metrics, or hardware fingerprints are transmitted (ADR-023).
2. **Strict User Preference & Opt-Out Enforcement:** Respect the existing "Check for Application Updates" toggle (`#auto-update-toggle` in Setup Wizard and `#settings-auto-update-toggle` in Settings, stored in `localStorage.getItem("abst.auto_update")`). When toggled off, no background network calls are ever performed.
3. **Throttled & Non-Intrusive Polling:** Cache update check timestamps in `localStorage` and memory to poll at most once every 24 hours in the background. Manual "Check for Updates Now" in Settings provides instantaneous on-demand checks.
4. **Dismissible & Accessible GUI Notification Banner:** Display an accessible announcement banner (`#update-notification-banner`) right beneath the application header when a newer version is detected. Allow the user to dismiss the banner (persisting dismissed version in `localStorage` so it won't prompt again for the same release).
5. **Direct Download & Release Notes Links:** Provide direct one-click navigation to the release notes and download page.
6. **Graceful Offline Degradation:** If offline or if the update server is unreachable, fail silently without throwing modal errors, noisy alerts, or affecting study functionality.

## Inputs (read these first)
- `docs/decisions/ADR-023-zero-python-distribution-and-packaging.md`
- `docs/decisions/ADR-024-gui-first-architecture-tui-as-mode.md`
- `docs/decisions/ADR-013-design-principles-stewardship-and-scalability.md`
- `web/index.html`
- `web/styles.css`
- `web/app.js`
- `search/resource.py`
- `search/ui/web_server.py`

---

## Tasks

- [x] ### Task 1: Backend Version Checker Module & Semver Logic
  - Create `search/ui/version_check.py` with `parse_semver()`, `is_newer_version()`, and `VersionChecker`.
  - Fetch latest release tag from GitHub Releases API with timeout and error handling.
  - Implement zero-telemetry client (`User-Agent: BibleStudyTool/{version}`).
  - Add in-memory caching to avoid hitting GitHub API rate limits.

- [x] ### Task 2: Backend API Endpoint & Web Server Wiring
  - In `search/ui/web_server.py`: Add `/api/check-update` endpoint.
  - In `/api/health`: Expose `"check_update_url": "/api/check-update"`.

- [x] ### Task 3: GUI Banner & Settings UI
  - In `web/index.html`: Add `#update-notification-banner` template with release badge, download button, release notes link, and dismiss button.
  - In `web/index.html`: Enhance Settings "Network & Privacy" section with current version label, "Check for Updates Now" button, and status indicator.
  - In `web/styles.css`: Add styling for banner and settings update controls, matching theme design tokens and responsive layouts.

- [x] ### Task 4: Frontend Update Checker & Throttling
  - In `web/app.js`: Implement `initUpdateChecker()` with 24-hour background throttle, dismiss persistence (`abst.dismissed_update`), and manual "Check Now" trigger.
  - Strictly check `abst.auto_update` toggle before background checks.

- [x] ### Task 5: Comprehensive Unit & Integration Tests
  - Add unit tests in `search/ui/test_version_check.py` covering semver comparison, update detection, network timeout/offline fallbacks, and caching (9 unit tests).
  - Add integration tests in `search/ui/test_web.py` covering `/api/check-update` and `/api/health`.

- [x] ### Task 6: Verification, Review & Documentation
  - Run `bash scripts/verify_all.sh` to ensure all tests and validators pass.
  - Subagent review and documentation update.

