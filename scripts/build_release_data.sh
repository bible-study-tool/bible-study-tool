#!/usr/bin/env bash
# build_release_data.sh — Deterministic release data bundler (WP-029 Phase 2, ADR-006, ADR-024).
#
# Packages the sidecar data bundle for zero-Python standalone distribution:
# - Vacuumed SQLite databases (data/bible.db, data/macula.db)
# - Canonical derived lexicons (lexicons/*.json)
# - Cryptographic SHA256SUMS manifest for bundle verification
# - Compressed distribution archive (dist/data.tar.gz)
#
# NOTE: data/egw.db is STRICTLY EXCLUDED from release bundles (copyright clean, ADR-002, ADR-023).
#
# Usage:
#   scripts/build_release_data.sh                 # full build + tar.gz archive
#   scripts/build_release_data.sh --no-archive    # build dist/data/ and SHA256SUMS only
#   scripts/build_release_data.sh --zip           # also create dist/data.zip
#   scripts/build_release_data.sh --check [dir]   # verify existing data bundle against SHA256SUMS
#   scripts/build_release_data.sh --out-dir <dir> # specify custom output directory

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"
OUT_DIR="$DIST_DIR/data"
DATA_SRC="$REPO_ROOT/data"
LEXICONS_SRC="$REPO_ROOT/lexicons"

CREATE_ARCHIVE=true
CREATE_ZIP=false
CHECK_ONLY=false
CHECK_DIR=""

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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-archive)
      CREATE_ARCHIVE=false
      shift
      ;;
    --zip)
      CREATE_ZIP=true
      shift
      ;;
    --check)
      CHECK_ONLY=true
      if [[ $# -gt 1 && ! "$2" =~ ^-- ]]; then
        CHECK_DIR="$2"
        shift 2
      else
        shift 1
      fi
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      echo "Adventist Bible Study Tool — Release Data Bundler (ADR-024)"
      echo
      echo "Usage: $0 [--no-archive] [--zip] [--check [dir]] [--out-dir <dir>]"
      echo
      echo "Options:"
      echo "  --no-archive    Assemble dist/data/ and compute SHA256SUMS without creating tar.gz"
      echo "  --zip           Create .zip archive alongside .tar.gz (for Windows)"
      echo "  --check [dir]   Verify data bundle directory against its SHA256SUMS"
      echo "  --out-dir <dir> Destination directory for sidecar data (default: dist/data)"
      echo "  -h, --help      Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

# --- Verification Mode --------------------------------------------------------
if [[ "$CHECK_ONLY" = true ]]; then
  TARGET="${CHECK_DIR:-$OUT_DIR}"
  echo "Verifying data bundle at: $TARGET"
  if [[ ! -f "$TARGET/SHA256SUMS" ]]; then
    echo "ERROR: $TARGET/SHA256SUMS not found." >&2
    exit 1
  fi
  (cd "$TARGET" && sha256sum --quiet -c SHA256SUMS)
  echo "✔ Data bundle integrity verified successfully."
  exit 0
fi

# --- Build Mode --------------------------------------------------------------
echo "=============================================================="
echo "Adventist Bible Study Tool — Release Data Bundler (ADR-024)"
echo "=============================================================="

# 1. Verify raw source provenance pins
echo "1. Checking source data provenance..."
"$REPO_ROOT/scripts/fetch_sources.sh" --check

# 2. Verify source databases exist (or build them)
if [[ ! -f "$DATA_SRC/bible.db" ]]; then
  echo "2. data/bible.db not found; compiling from pinned sources..."
  "$PYTHON" -m search.corpus.extract_kjv --compile
  "$PYTHON" -m search.corpus.extract_translations
else
  echo "2. Found data/bible.db."
fi

if [[ ! -f "$DATA_SRC/macula.db" ]]; then
  echo "   data/macula.db not found; compiling linguistic database..."
  "$PYTHON" -m search.macula.build_db --repo "$REPO_ROOT"
else
  echo "   Found data/macula.db."
fi

# 3. Clean and prepare output directory
echo "3. Preparing output directory: $OUT_DIR"
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/lexicons"

# 4. Compact and copy SQLite databases via VACUUM INTO
echo "4. Compacting and copying SQLite databases..."
"$PYTHON" - "$DATA_SRC" "$OUT_DIR" <<'PYEOF'
import os, sqlite3, sys
src_dir, dst_dir = sys.argv[1], sys.argv[2]
for db_name in ['bible.db', 'macula.db']:
    src = os.path.join(src_dir, db_name)
    dst = os.path.join(dst_dir, db_name)
    print(f"   Compacting {db_name} -> {dst}...")
    con = sqlite3.connect(src)
    dst_escaped = dst.replace("'", "''")
    con.execute(f"VACUUM INTO '{dst_escaped}'")
    con.close()

    # Verify compacted integrity
    chk_con = sqlite3.connect(dst)
    res = chk_con.execute('PRAGMA quick_check;').fetchall()
    assert res == [('ok',)], f'Integrity check failed for {dst}: {res}'
    chk_con.close()
print('   ✔ SQLite databases vacuumed and verified.')
PYEOF

# 5. Copy canonical derived lexicons
echo "5. Copying canonical lexicons..."
cp "$LEXICONS_SRC"/*.json "$OUT_DIR/lexicons/"
LEX_COUNT=$(ls -1 "$OUT_DIR/lexicons/"*.json | wc -l)
echo "   ✔ Copied $LEX_COUNT lexicon JSON artifacts."

# Enforce copyright boundary tripwire (ADR-002, ADR-023, ADR-024)
if [[ -e "$OUT_DIR/egw.db" ]]; then
  echo "FATAL: egw.db found in release bundle directory! Violates copyright boundary." >&2
  exit 1
fi

# 6. Compute cryptographic SHA256SUMS manifest
echo "6. Generating SHA256SUMS manifest..."
(
  cd "$OUT_DIR"
  export LC_ALL=C
  sha256sum bible.db macula.db lexicons/*.json > SHA256SUMS
)
echo "   ✔ Manifest created: $OUT_DIR/SHA256SUMS ($(wc -l < "$OUT_DIR/SHA256SUMS") entries)."

# 7. Internal verification of the generated manifest
echo "7. Self-verifying data bundle against manifest..."
(
  cd "$OUT_DIR"
  sha256sum --quiet -c SHA256SUMS
)
echo "   ✔ Self-verification passed."

ARCHIVE_PARENT="$(cd "$(dirname "$OUT_DIR")" && pwd)"
ARCHIVE_BASE="$(basename "$OUT_DIR")"

# 8. Create distribution archives if requested
if [[ "$CREATE_ARCHIVE" = true ]]; then
  echo "8. Creating compressed release archive: $ARCHIVE_PARENT/$ARCHIVE_BASE.tar.gz..."
  tar -czf "$ARCHIVE_PARENT/$ARCHIVE_BASE.tar.gz" -C "$ARCHIVE_PARENT" "$ARCHIVE_BASE"
  sha256sum "$ARCHIVE_PARENT/$ARCHIVE_BASE.tar.gz" | awk '{print $1}' > "$ARCHIVE_PARENT/$ARCHIVE_BASE.tar.gz.sha256"
  ARCHIVE_SHA=$(cat "$ARCHIVE_PARENT/$ARCHIVE_BASE.tar.gz.sha256")
  ARCHIVE_SIZE=$(ls -lh "$ARCHIVE_PARENT/$ARCHIVE_BASE.tar.gz" | awk '{print $5}')
  echo "   ✔ Archive created: $ARCHIVE_PARENT/$ARCHIVE_BASE.tar.gz ($ARCHIVE_SIZE)"
  echo "   SHA-256: $ARCHIVE_SHA"
fi

if [[ "$CREATE_ZIP" = true ]]; then
  command -v zip >/dev/null 2>&1 || { echo "ERROR: 'zip' utility is required for --zip" >&2; exit 1; }
  echo "   Creating zip archive: $ARCHIVE_PARENT/$ARCHIVE_BASE.zip..."
  (cd "$ARCHIVE_PARENT" && zip -qr "$ARCHIVE_BASE.zip" "$ARCHIVE_BASE")
  sha256sum "$ARCHIVE_PARENT/$ARCHIVE_BASE.zip" | awk '{print $1}' > "$ARCHIVE_PARENT/$ARCHIVE_BASE.zip.sha256"
  echo "   ✔ Zip archive created: $ARCHIVE_PARENT/$ARCHIVE_BASE.zip"
fi

echo
echo "=============================================================="
echo "Release data bundle ready in: $OUT_DIR"
du -sh "$OUT_DIR"
echo "=============================================================="
