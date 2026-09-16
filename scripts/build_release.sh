#!/usr/bin/env bash
# build_release.sh — Unified release packaging pipeline (WP-029 Phase 3, ADR-024).
#
# Builds the standalone zero-Python distribution:
# 1. Runs pre-flight test verification (unless --skip-tests)
# 2. Builds sidecar data bundle (via scripts/build_release_data.sh)
# 3. Freezes application binary with PyInstaller (via bible_study.spec)
# 4. Assembles release layout:
#      <release_root>/
#      ├── bible-study              # Standalone executable
#      ├── _internal/               # Bundled runtime and web assets
#      ├── data/                    # Sidecar databases & lexicons (ADR-024)
#      │   ├── bible.db
#      │   ├── macula.db
#      │   ├── SHA256SUMS
#      │   └── lexicons/
#      ├── SHA256SUMS               # Release-wide integrity manifest
#      ├── README.md
#      └── NOTICE.md
# 5. Packages compressed distribution archives (.tar.gz and optional .zip)
# 6. Runs smoke test against the assembled standalone binary
#
# Usage:
#   scripts/build_release.sh               # full release build + smoke test
#   scripts/build_release.sh --skip-tests  # build without running test suite first
#   scripts/build_release.sh --no-data     # build executable only (skip sidecar data)
#   scripts/build_release.sh --zip         # create .zip archive alongside .tar.gz
#   scripts/build_release.sh --clean       # remove previous build/ and dist/ first

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
  else
    PYTHON="python"
  fi
fi

VERSION="${VERSION:-}"
if [[ -z "$VERSION" && -n "${CI_COMMIT_TAG:-}" ]]; then
  VERSION="${CI_COMMIT_TAG#v}"
fi
if [[ -z "$VERSION" ]]; then
  VERSION="$("$PYTHON" -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null || echo "0.1.0")"
fi

SKIP_TESTS=false
BUILD_DATA=true
CREATE_ZIP=false
DO_CLEAN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-tests)
      SKIP_TESTS=true
      shift
      ;;
    --no-data)
      BUILD_DATA=false
      shift
      ;;
    --zip)
      CREATE_ZIP=true
      shift
      ;;
    --clean)
      DO_CLEAN=true
      shift
      ;;
    -h|--help)
      echo "Adventist Bible Study Tool — Release Build Pipeline (WP-029, ADR-024)"
      echo
      echo "Usage: $0 [--skip-tests] [--no-data] [--zip] [--clean]"
      echo
      echo "Options:"
      echo "  --skip-tests  Skip pre-flight test verification"
      echo "  --no-data     Skip sidecar data bundle compilation"
      echo "  --zip         Create .zip archive in addition to .tar.gz"
      echo "  --clean       Clean build/ and dist/ directories before building"
      echo "  -h, --help    Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

echo "=============================================================="
echo "Adventist Bible Study Tool — Release Build Pipeline v$VERSION"
echo "=============================================================="

# Detect platform
OS_NAME="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$OS_NAME" in
  mingw*|msys*|cygwin*) OS_NAME="windows" ;;
esac
ARCH_NAME="$(uname -m)"
PLATFORM_TAG="${OS_NAME}-${ARCH_NAME}"
DIST_DIR="$REPO_ROOT/dist"
ARCHIVE_TAG="${CI_COMMIT_TAG:-$VERSION}"
STAGE_NAME="bible-study-${ARCHIVE_TAG}-${PLATFORM_TAG}"
STAGE_DIR="$DIST_DIR/$STAGE_NAME"

echo "Target Platform: $PLATFORM_TAG"
echo "Staging Dir:     $STAGE_DIR"
echo "Python:          $("$PYTHON" --version 2>&1) ($PYTHON)"

# Ensure PyInstaller is installed
if ! "$PYTHON" -m PyInstaller --version >/dev/null 2>&1 && ! "$PYTHON" -m pyinstaller --version >/dev/null 2>&1 && ! command -v pyinstaller >/dev/null 2>&1; then
  echo "ERROR: PyInstaller is not installed in the target Python environment." >&2
  echo "Run ./scripts/bootstrap.sh --dist or uv pip install --python '$PYTHON' pyinstaller" >&2
  exit 1
fi
echo "PyInstaller:     $("$PYTHON" -m PyInstaller --version)"

# 0. Clean if requested
if [[ "$DO_CLEAN" = true ]]; then
  echo "Cleaning previous build artifacts..."
  rm -rf "$REPO_ROOT/build" "$DIST_DIR"
fi

# 1. Pre-flight verification
if [[ "$SKIP_TESTS" = false ]]; then
  echo
  echo "--- 1. Running pre-flight verification ---"
  "$PYTHON" -m pytest -q
  echo "✔ Test suite passed."
fi

# 2. Freeze binary with PyInstaller
echo
echo "--- 2. Freezing standalone application binary ---"
"$PYTHON" -m PyInstaller --clean -y "$REPO_ROOT/bible_study.spec"
echo "✔ Standalone executable built: $DIST_DIR/bible-study/bible-study"

# 3. Prepare release staging directory
echo
echo "--- 3. Assembling release bundle layout ---"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

# Copy binary and PyInstaller internal dependencies
cp -a "$DIST_DIR/bible-study"/* "$STAGE_DIR/"

# Copy release documentation & notices
for doc in README.md NOTICE.md LICENSE CONTRIBUTION_STANDARDS.md; do
  if [[ -f "$REPO_ROOT/$doc" ]]; then
    cp "$REPO_ROOT/$doc" "$STAGE_DIR/"
  fi
done

# 4. Assemble sidecar data bundle (ADR-024 §7)
if [[ "$BUILD_DATA" = true ]]; then
  echo
  echo "--- 4. Building sidecar data bundle ---"
  bash "$REPO_ROOT/scripts/build_release_data.sh" --no-archive --out-dir "$STAGE_DIR/data"
  echo "✔ Sidecar data bundle assembled in $STAGE_DIR/data/"
fi

# 5. Generate release-wide SHA256SUMS manifest
echo
echo "--- 5. Generating release integrity manifest ---"
(
  cd "$STAGE_DIR"
  export LC_ALL=C
  # SQLite DBs are verified by CONTENT (data/INTEGRITY.json, ADR-027),
  # not bytes — .db files are not byte-reproducible across toolchains. Exclude
  # them from the release-wide byte manifest; step 8b runs the content check.
  find . -type f \( -name "*.db" -o -name "INTEGRITY.json" \) -prune -o \
    -type f ! -name "SHA256SUMS" -print | sort | sed 's|^\./||' \
    | xargs sha256sum > SHA256SUMS
)
echo "✔ Generated $STAGE_DIR/SHA256SUMS ($(wc -l < "$STAGE_DIR/SHA256SUMS") entries; SQLite DBs handled by content manifest)."

# 6. Verify release staging self-integrity
echo
echo "--- 6. Verifying release staging integrity ---"
(
  cd "$STAGE_DIR"
  sha256sum --quiet -c SHA256SUMS
)
echo "✔ Release staging integrity verified."

# 7. Smoke test the assembled standalone binary
echo
echo "--- 7. Running smoke test on standalone binary ---"
EXE="$STAGE_DIR/bible-study"
if [[ -f "${EXE}.exe" ]]; then
  EXE="${EXE}.exe"
fi
"$EXE" --version >/dev/null
"$EXE" --help >/dev/null

if [[ "$BUILD_DATA" = true ]]; then
  SMOKE_OUT="$("$EXE" read 'Gen 1:1' --json)"
  if [[ "$SMOKE_OUT" != *"In the beginning God created"* ]]; then
    echo "ERROR: Standalone binary failed smoke test on Gen 1:1" >&2
    exit 1
  fi
  echo "✔ CLI Scripture reading verified."

  WORD_OUT="$("$EXE" word H1254 --json)"
  if [[ "$WORD_OUT" != *"H1254"* ]]; then
    echo "ERROR: Standalone binary failed smoke test on word H1254" >&2
    exit 1
  fi
  echo "✔ Lexical concordance verified."

  TUI_OUT="$(echo "exit" | "$EXE" --tui 2>&1 || true)"
  if [[ "$TUI_OUT" != *"ADVENTIST BIBLE STUDY TOOL"* ]]; then
    echo "ERROR: Standalone binary failed TUI / shell smoke test" >&2
    exit 1
  fi
  echo "✔ TUI mode smoke test verified."
fi
echo "✔ Smoke tests passed successfully."

# Re-verify staging integrity post-smoke test
echo "--- 7b. Verifying staging integrity post-smoke test ---"
(
  cd "$STAGE_DIR"
  sha256sum --quiet -c SHA256SUMS
)
echo "✔ Release staging integrity unchanged by smoke tests."

# 8. Create release archive
echo
echo "--- 8. Creating release archive ---"
ARCHIVE_TAR="$DIST_DIR/${STAGE_NAME}.tar.gz"
tar -czf "$ARCHIVE_TAR" -C "$DIST_DIR" "$STAGE_NAME"
sha256sum "$ARCHIVE_TAR" | awk '{print $1}' > "${ARCHIVE_TAR}.sha256"
TAR_SIZE="$(ls -lh "$ARCHIVE_TAR" | awk '{print $5}')"
echo "✔ Release archive: $ARCHIVE_TAR ($TAR_SIZE)"
echo "  SHA-256: $(cat "${ARCHIVE_TAR}.sha256")"

# 8b. Verify packaged archive ground truth (ADR-024)
echo
echo "--- 8b. Verifying packaged archive ground truth ---"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT
tar -xzf "$ARCHIVE_TAR" -C "$SCRATCH"
echo "   Checking release-wide SHA256SUMS inside packaged tar.gz..."
(cd "$SCRATCH/$STAGE_NAME" && sha256sum --quiet -c SHA256SUMS)
if [[ -f "$SCRATCH/$STAGE_NAME/data/SHA256SUMS" ]]; then
  echo "   Checking sidecar data/SHA256SUMS inside packaged tar.gz..."
  (cd "$SCRATCH/$STAGE_NAME/data" && sha256sum --quiet -c SHA256SUMS)
fi
if [[ -f "$SCRATCH/$STAGE_NAME/data/INTEGRITY.json" ]]; then
  echo "   Checking SQLite content integrity inside packaged tar.gz..."
  "$PYTHON" -m search.validation.db_integrity --check \
    --bible-db "$SCRATCH/$STAGE_NAME/data/bible.db" \
    --macula-db "$SCRATCH/$STAGE_NAME/data/macula.db" \
    --manifest "$SCRATCH/$STAGE_NAME/data/INTEGRITY.json"
elif [[ -f "$SCRATCH/$STAGE_NAME/data/bible.db" || -f "$SCRATCH/$STAGE_NAME/data/macula.db" ]]; then
  echo "ERROR: package contains SQLite DBs but no INTEGRITY.json content manifest." >&2
  exit 1
fi
rm -rf "$SCRATCH"
trap - EXIT
echo "✔ Packaged archive verified against internal manifests."

if [[ "$CREATE_ZIP" = true ]]; then
  command -v zip >/dev/null 2>&1 || { echo "ERROR: 'zip' utility is required for --zip" >&2; exit 1; }
  ARCHIVE_ZIP="$DIST_DIR/${STAGE_NAME}.zip"
  (cd "$DIST_DIR" && zip -qr "${STAGE_NAME}.zip" "$STAGE_NAME")
  sha256sum "$ARCHIVE_ZIP" | awk '{print $1}' > "${ARCHIVE_ZIP}.sha256"
  ZIP_SIZE="$(ls -lh "$ARCHIVE_ZIP" | awk '{print $5}')"
  echo "✔ Zip archive:     $ARCHIVE_ZIP ($ZIP_SIZE)"
  echo "  SHA-256: $(cat "${ARCHIVE_ZIP}.sha256")"

  SCRATCH_ZIP="$(mktemp -d)"
  trap 'rm -rf "$SCRATCH_ZIP"' EXIT
  unzip -q "$ARCHIVE_ZIP" -d "$SCRATCH_ZIP"
  (cd "$SCRATCH_ZIP/$STAGE_NAME" && sha256sum --quiet -c SHA256SUMS)
  if [[ -f "$SCRATCH_ZIP/$STAGE_NAME/data/SHA256SUMS" ]]; then
    (cd "$SCRATCH_ZIP/$STAGE_NAME/data" && sha256sum --quiet -c SHA256SUMS)
  fi
  if [[ -f "$SCRATCH_ZIP/$STAGE_NAME/data/INTEGRITY.json" ]]; then
    "$PYTHON" -m search.validation.db_integrity --check \
      --bible-db "$SCRATCH_ZIP/$STAGE_NAME/data/bible.db" \
      --macula-db "$SCRATCH_ZIP/$STAGE_NAME/data/macula.db" \
      --manifest "$SCRATCH_ZIP/$STAGE_NAME/data/INTEGRITY.json"
  elif [[ -f "$SCRATCH_ZIP/$STAGE_NAME/data/bible.db" || -f "$SCRATCH_ZIP/$STAGE_NAME/data/macula.db" ]]; then
    echo "ERROR: zip package contains SQLite DBs but no INTEGRITY.json content manifest." >&2
    exit 1
  fi
  rm -rf "$SCRATCH_ZIP"
  trap - EXIT
  echo "✔ Packaged zip archive verified against internal manifests."
fi

# 9. Extract release notes
echo
echo "--- 9. Extracting release notes ---"
"$PYTHON" "$REPO_ROOT/scripts/extract_release_notes.py" "$ARCHIVE_TAG" --out "$DIST_DIR/RELEASE_NOTES.md"

echo
echo "=============================================================="
echo "Release build complete for $STAGE_NAME"
echo "=============================================================="
