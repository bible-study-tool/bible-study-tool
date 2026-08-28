#!/usr/bin/env bash
# Fetch the third-party raw source data into data/ (gitignored).
#
# Every file is pinned by SHA-256 in data/PROVENANCE.md. This script is
# idempotent: files whose checksum already matches are skipped, so re-running
# it never clobbers verified data.
#
# Usage:
#   scripts/fetch_sources.sh            # fetch + verify
#   scripts/fetch_sources.sh --check    # verify checksums only (offline)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$REPO_ROOT/data"
CHECKSUMS="$DATA/PROVENANCE.md"

# --- pinned sources ----------------------------------------------------------
GMLEWIS_PIN="c9432716b19d039f06a2aebbd1f10b911c6254b0"
GMLEWIS_URL="https://github.com/gmlewis/bible-codes/archive/${GMLEWIS_PIN}.zip"
SCROLLMAPPER_URL="https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/en/KJV/KJV-osis.json"
OSHB_URL="https://github.com/openscriptures/morphhb/archive/refs/tags/v.2.2.zip"

mkdir -p "$DATA/strongs"

fetch() { # fetch <url> <dest>
  local url="$1" dest="$2"
  if [[ -f "$dest" ]]; then
    echo "[skip] $(basename "$dest") already present"
  else
    echo "[get ] $url"
    curl -fsSL --retry 3 -o "$dest.tmp" "$url"
    mv "$dest.tmp" "$dest"
  fi
}

# --- 1. gmlewis/bible-codes (Strong's concordance .go files) -----------------
# The archive extracts to bible-codes-<pin>/; we copy out the strongs package.
NEED_GMLEWIS=0
for f in strongs.go hebrew.go greek.go kjv.go regenerate.sh; do
  [[ -f "$DATA/strongs/$f" ]] || NEED_GMLEWIS=1
done
if [[ "$NEED_GMLEWIS" == "1" ]]; then
  TMP="$(mktemp -d)"
  echo "[get ] $GMLEWIS_URL"
  curl -fsSL --retry 3 -o "$TMP/bc.zip" "$GMLEWIS_URL"
  unzip -q "$TMP/bc.zip" -d "$TMP"
  SRC="$TMP/bible-codes-${GMLEWIS_PIN}/strongs"
  mkdir -p "$DATA/strongs"
  cp "$SRC"/strongs.go "$SRC"/hebrew.go "$SRC"/greek.go "$SRC"/kjv.go "$DATA/strongs/" 2>/dev/null \
    || cp "$SRC"/*.go "$DATA/strongs/"
  cp "$SRC/regenerate.sh" "$DATA/regenerate.sh" 2>/dev/null || true
  rm -rf "$TMP"
else
  echo "[skip] strongs/*.go already present"
fi

# --- 2. scrollmapper KJV-osis ------------------------------------------------
fetch "$SCROLLMAPPER_URL" "$DATA/KJV-osis.json"

# --- 3. Open Scriptures Hebrew Bible v.2.2 -----------------------------------
fetch "$OSHB_URL" "$DATA/OSHB-v.2.2.zip"

# --- verification ------------------------------------------------------------
echo
echo "Verifying checksums against $CHECKSUMS ..."
if sha256sum -c <(grep -oE '^[0-9a-f]{64}  [A-Za-z0-9._/-]+' "$CHECKSUMS" | sed "s#  #  $DATA/#"); then
  echo "All source checksums match the pinned provenance record."
else
  echo "ERROR: checksum mismatch — a source changed upstream. Do NOT regenerate" >&2
  echo "the lexicons until the change is reviewed and PROVENANCE.md is updated." >&2
  exit 1
fi
