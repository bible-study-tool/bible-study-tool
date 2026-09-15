#!/usr/bin/env bash
# Fetch the third-party raw source data into data/ (gitignored).
#
# Every file is pinned by SHA-256 in data/PROVENANCE.md. Files already present
# are skipped, so re-running never re-downloads verified data. Verification
# fails closed: a checksum mismatch (or a missing/empty checksum list) aborts
# with a non-zero exit.
#
# Usage:
#   scripts/fetch_sources.sh            # fetch + verify (network required)
#   scripts/fetch_sources.sh --check    # verify checksums only (offline)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$REPO_ROOT/data"
CHECKSUMS="$DATA/PROVENANCE.md"
MODE="${1:-}"

# --- pinned sources ----------------------------------------------------------
GMLEWIS_PIN="c9432716b19d039f06a2aebbd1f10b911c6254b0"
GMLEWIS_URL="https://github.com/gmlewis/bible-codes/archive/${GMLEWIS_PIN}.zip"
SCROLLMAPPER_PIN="e1b254cef86d0e65b1a5d1a94b8b112d0f296a2c"
SCROLLMAPPER_URL="https://raw.githubusercontent.com/scrollmapper/bible_databases/${SCROLLMAPPER_PIN}/sources/en/KJV/KJV-osis.json"
SCROLLMAPPER_ASV_URL="https://raw.githubusercontent.com/scrollmapper/bible_databases/${SCROLLMAPPER_PIN}/sources/en/ASV/ASV.json"
SCROLLMAPPER_BSB_URL="https://raw.githubusercontent.com/scrollmapper/bible_databases/${SCROLLMAPPER_PIN}/sources/en/BSB/BSB.json"
SCROLLMAPPER_YLT_URL="https://raw.githubusercontent.com/scrollmapper/bible_databases/${SCROLLMAPPER_PIN}/sources/en/YLT/YLT.json"
OSHB_PIN="v.2.2"
OSHB_URL="https://github.com/openscriptures/morphhb/releases/download/${OSHB_PIN}/OSHB-${OSHB_PIN}.zip"
STEPBIBLE_PIN="efe428a0047bf7b9c3ce2624f60c252c6e435945"
TBESH_URL="https://raw.githubusercontent.com/STEPBible/STEPBible-Data/${STEPBIBLE_PIN}/Lexicons/TBESH%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Hebrew%20-%20STEPBible.org%20CC%20BY.txt"
TBESG_URL="https://raw.githubusercontent.com/STEPBible/STEPBible-Data/${STEPBIBLE_PIN}/Lexicons/TBESG%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Greek%20-%20STEPBible.org%20CC%20BY.txt"
TSK_URL="https://a.openbible.info/data/cross-references.zip"

# --- verification (shared by both modes) -------------------------------------
verify() {
  echo
  echo "Verifying checksums against $CHECKSUMS ..."
  local list
  # Grep failures (e.g. missing file, format drift) must not pass vacuously.
  list="$(grep -oE '^[0-9a-f]{64}  [A-Za-z0-9._/-]+' "$CHECKSUMS" | sed "s#  #  $DATA/#")"
  if [[ -z "$list" ]]; then
    echo "ERROR: no checksums found in $CHECKSUMS — the record format changed." >&2
    echo "Fix: restore the 'SHA-256' blocks (64-hex + two spaces + path), then re-run." >&2
    exit 1
  fi
  if sha256sum -c <<< "$list"; then
    echo "All source checksums match the pinned provenance record."
  else
    echo "ERROR: checksum mismatch — a source changed (upstream or local edit)." >&2
    echo "Fix: re-verify the upstream source, update the pin + SHA-256 in" >&2
    echo "data/PROVENANCE.md (see its Policy section), then MR the change." >&2
    echo "Note: Release assets (releases/download/) are immutable, but GitHub repo" >&2
    echo "archive zips (/archive/) are generated dynamically and may drift." >&2
    exit 1
  fi
}

if [[ "$MODE" == "--check" ]]; then
  verify
  exit 0
fi
if [[ -n "$MODE" ]]; then
  echo "Usage: $0 [--check]" >&2
  exit 2
fi

command -v curl >/dev/null || {
  echo "ERROR: 'curl' is required." >&2
  exit 1
}

fetch() { # fetch <url> <dest>
  local url="$1" dest="$2"
  if [[ -f "$dest" ]]; then
    echo "[skip] ${dest#"$REPO_ROOT"/} already present"
  else
    echo "[get ] $url"
    curl -fsSL --retry 3 --connect-timeout 15 --max-time 600 -o "$dest.tmp" "$url"
    mv "$dest.tmp" "$dest"
  fi
}

# --- 1. gmlewis/bible-codes (Strong's concordance .go files) -----------------
# The archive extracts to bible-codes-<pin>/; we copy out the strongs package.
# Uses Python stdlib zipfile (no system unzip required).
NEED_GMLEWIS=0
for f in strongs.go hebrew.go greek.go; do
  [[ -f "$DATA/strongs/$f" ]] || NEED_GMLEWIS=1
done
if [[ "$NEED_GMLEWIS" == "1" ]]; then
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  echo "[get ] $GMLEWIS_URL"
  curl -fsSL --retry 3 --connect-timeout 15 --max-time 600 -o "$TMP/bc.zip" "$GMLEWIS_URL"
  python3 - "$TMP" "$GMLEWIS_PIN" <<'PYEOF'
import sys, zipfile, pathlib
tmp, pin = pathlib.Path(sys.argv[1]), sys.argv[2]
with zipfile.ZipFile(tmp / "bc.zip") as zf:
    zf.extractall(tmp)
PYEOF
  SRC="$TMP/bible-codes-${GMLEWIS_PIN}/strongs"
  [[ -d "$SRC" ]] || { echo "ERROR: pinned archive layout changed — '$SRC' missing." >&2; exit 1; }
  mkdir -p "$DATA/strongs"
  cp "$SRC"/*.go "$DATA/strongs/"
  [[ -f "$SRC/regenerate.sh" ]] || {
    echo "ERROR: regenerate.sh not found in the pinned archive (upstream layout change)." >&2
    exit 1
  }
  cp "$SRC/regenerate.sh" "$DATA/regenerate.sh"
  rm -rf "$TMP"
  trap - EXIT
else
  echo "[skip] strongs/*.go already present"
fi

# --- 2. scrollmapper KJV-osis & parallel translations ------------------------
fetch "$SCROLLMAPPER_URL" "$DATA/KJV-osis.json"
fetch "$SCROLLMAPPER_ASV_URL" "$DATA/ASV.json"
fetch "$SCROLLMAPPER_BSB_URL" "$DATA/BSB.json"
fetch "$SCROLLMAPPER_YLT_URL" "$DATA/YLT.json"

# --- 3. Open Scriptures Hebrew Bible v.2.2 -----------------------------------
fetch "$OSHB_URL" "$DATA/OSHB-v.2.2.zip"
# The OSHB generator reads per-book XML; extract them from the zip (idempotent).
if [[ ! -f "$DATA/oshb/Gen.xml" ]]; then
  echo "[xtr ] OSHB-v.2.2.zip -> data/oshb/"
  python3 - "$DATA" <<'PYEOF'
import os, sys, zipfile
data = sys.argv[1]
z = zipfile.ZipFile(os.path.join(data, "OSHB-v.2.2.zip"))
os.makedirs(os.path.join(data, "oshb"), exist_ok=True)
count = 0
for n in z.namelist():
    if n.startswith("__MACOSX") or n.endswith("/"):
        continue
    dest = os.path.join(data, "oshb", os.path.basename(n))
    with z.open(n) as src, open(dest, "wb") as out:
        out.write(src.read())
    count += 1
print(f"[xtr ] extracted {count} files")
PYEOF
else
  echo "[skip] oshb/*.xml already extracted"
fi

# --- 4. STEPBible TBESH/TBESG brief lexicons ---------------------------------
mkdir -p "$DATA/stepbible"
fetch "$TBESH_URL" "$DATA/stepbible/TBESH.txt"
fetch "$TBESG_URL" "$DATA/stepbible/TBESG.txt"

# --- 5. Clear-Bible Macula Hebrew Lowfat XML (Whole Old Testament: 39 books, 929 chapters) ---
MACULA_PIN="47db250bd55d0d8577f2a94fba114ef16c35b23c"
mkdir -p "$DATA/macula-hebrew"
if [[ ! -f "$DATA/macula-hebrew/39-Mal-003-lowfat.xml" ]]; then
  echo "[get ] Macula Hebrew Lowfat XML (39 books, 929 chapters) from Clear-Bible/macula-hebrew ..."
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  git clone --filter=blob:none --no-checkout https://github.com/Clear-Bible/macula-hebrew.git "$TMP/macula"
  git -C "$TMP/macula" sparse-checkout set WLC/lowfat
  git -C "$TMP/macula" checkout "$MACULA_PIN"
  cp "$TMP/macula/WLC/lowfat"/*.xml "$DATA/macula-hebrew/"
  rm -rf "$TMP"
  trap - EXIT
else
  echo "[skip] macula-hebrew/*.xml (all 39 OT books) already present"
fi

# --- 6. Clear-Bible Macula Greek Lowfat XML (Whole New Testament: 27 books, 260 chapters) ---
MACULA_GREEK_PIN="8423afe47b9e8f24b7772e808af45c7159a6fe7e"
mkdir -p "$DATA/macula-greek"
if [[ ! -f "$DATA/macula-greek/27-revelation.xml" ]]; then
  echo "[get ] Macula Greek Lowfat XML (27 books, 260 chapters) from Clear-Bible/macula-greek ..."
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  git clone --filter=blob:none --no-checkout https://github.com/Clear-Bible/macula-greek.git "$TMP/macula_greek"
  git -C "$TMP/macula_greek" sparse-checkout set Nestle1904/lowfat
  git -C "$TMP/macula_greek" checkout "$MACULA_GREEK_PIN"
  cp "$TMP/macula_greek/Nestle1904/lowfat"/[0-9]*.xml "$DATA/macula-greek/"
  rm -rf "$TMP"
  trap - EXIT
else
  echo "[skip] macula-greek/*.xml (all 27 NT books) already present"
fi

# --- 7. OpenBible / Treasury of Scripture Knowledge (TSK) Cross References ---
fetch "$TSK_URL" "$DATA/cross-references.zip"

# --- verification ------------------------------------------------------------
verify


