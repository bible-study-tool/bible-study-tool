#!/usr/bin/env bash
# verify_all.sh — ONE command to run every integrity gate locally.
#
# Contributors: run this before every Merge Request. It runs the exact checks
# CI runs, with a human-readable remedy for each failure. CI fails on the
# same things; if this passes locally, the robot gatekeeper passes too.
#
# What is gated (and why):
#   1. Test suite (pytest)         — includes the byte-regeneration tripwires
#                                    and the PROVENANCE checksum gate.
#   2. F1-F4 data validators       — schema, Strong's, cross-refs, dead links.
#   3. Source checksums (--check)  — only when the raw sources are present
#                                    locally (data/ is gitignored; on a fresh
#                                    clone the PROVENANCE gate in pytest
#                                    already covers the committed artifacts).
#
# Rules of thumb:
#   * Entry/curated Markdown (materials/) is HAND content — validators give
#     you specific errors; fix the entry.
#   * lexicons/*.json, correlations/agreement-ledger.json and generated
#     corpus entries are GENERATED — never hand-edit; regenerate with the
#     command printed in the failure message.
#   * A failed ledger/corpus tripwire after a SOURCE re-pin is the review
#     gate working: inspect the diff, then regenerate and commit together
#     with the updated data/PROVENANCE.md checksum.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FAILURES=()

# Determine python interpreter (prefer .venv if present, fallback to active python/PATH)
PYTHON="${PYTHON:-}"
check_deps() { "$1" -c "import pytest, yaml, numpy" >/dev/null 2>&1; }

if [[ -z "$PYTHON" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]] && check_deps "$REPO_ROOT/.venv/bin/python"; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
  elif command -v python >/dev/null 2>&1 && check_deps python; then
    PYTHON="python"
  elif command -v python3 >/dev/null 2>&1 && check_deps python3; then
    PYTHON="python3"
  else
    echo "ERROR: Python test dependencies not found (pytest, PyYAML, numpy)." >&2
    echo "Please initialize your environment with:" >&2
    echo "    ./bootstrap.sh" >&2
    echo "Or activate your virtual environment:" >&2
    echo "    source .venv/bin/activate" >&2
    exit 1
  fi
fi

# Pre-flight: Check for stale editable install / unresolvable search namespace modules
check_search_modules() {
  "$1" -c "import search, search.resource, search.linking, search.validation, search.corpus, search.ui" >/dev/null 2>&1
}

if ! check_search_modules "$PYTHON"; then
  echo "Notice: Core 'search' namespace modules could not be imported cleanly." >&2
  echo "Your editable installation may be stale. Attempting auto-refresh..." >&2
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$PYTHON" --no-deps -q -e . >/dev/null 2>&1 || true
  else
    "$PYTHON" -m pip install --no-deps -q -e . >/dev/null 2>&1 || true
  fi
  if ! check_search_modules "$PYTHON"; then
    echo "ERROR: Unable to import core search modules." >&2
    echo "Please refresh your environment with:" >&2
    echo "    ./bootstrap.sh" >&2
    exit 1
  fi
  echo "✔ Editable install refreshed successfully."
fi

run_step() { # run_step <label> <command...>
  local label="$1"; shift
  echo
  echo "━━━ $label ━━━"
  if "$@"; then
    echo "✔ $label: OK"
  else
    echo "✘ $label: FAILED — see above"
    FAILURES+=("$label")
  fi
}

echo "Bible Study Tool — full local verification"
echo "repo: $REPO_ROOT"
echo "python: $("$PYTHON" --version 2>&1) ($PYTHON)"

# --- 1. full test suite (includes all tripwires + checksum gates) -----------
run_step "Test suite (pytest, includes regeneration tripwires + checksum gate)" \
  "$PYTHON" -m pytest

# --- 2. F1-F4 data-integrity validators --------------------------------------
run_step "F1 schema validator"   "$PYTHON" -m search.validation.schema  --repo .
run_step "F2 Strong's validator" "$PYTHON" -m search.validation.strongs --repo .
run_step "F3 cross-ref validator" "$PYTHON" -m search.validation.xrefs  --repo .
run_step "F4 dead-ref audit"     "$PYTHON" -m search.validation.audit   --repo .

# --- 3. raw-source checksums (only when the sources are present) -------------
if [[ -f data/KJV-osis.json ]]; then
  run_step "Raw source checksums (fetch_sources.sh --check)" \
    bash scripts/fetch_sources.sh --check
else
  echo
  echo "━━━ Raw source checksums ━━━"
  echo "– SKIP: raw sources not present (data/ is gitignored). The committed"
  echo "  artifacts were still checksum-verified by the PROVENANCE gate in"
  echo "  pytest. To fetch sources locally: bash scripts/fetch_sources.sh"
fi

# --- summary -----------------------------------------------------------------
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ ${#FAILURES[@]} -eq 0 ]]; then
  echo "ALL CHECKS PASSED ✔"
  exit 0
fi
echo "FAILED: ${#FAILURES[@]} check(s): ${FAILURES[*]}"
echo
echo "Remedies:"
echo "  * Validator failures name the entry and the rule — fix the Markdown."
echo "  * GENERATED artifacts are never hand-edited: regenerate with the"
echo "    command in the failure message (lexicons: build_strongs_lexicon /"
echo "    build_stepbible_lexicon / build_morphology; ledger:"
echo "    search.agreement.compare.write_ledger; corpus:"
echo "    build_genesis1), then commit with the updated"
echo "    data/PROVENANCE.md checksums."
echo "  * If a SOURCE was re-pinned, the agreement-ledger tripwire is the"
echo "    review gate: inspect the ledger diff before regenerating."
exit 1
