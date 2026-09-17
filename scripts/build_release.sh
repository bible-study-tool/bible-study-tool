#!/usr/bin/env bash
# build_release.sh — Unified release packaging pipeline (WP-029 Phase 3, ADR-024).
# Delegates to the cross-platform Python implementation scripts/build_release.py.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
export PYTHON

exec "$PYTHON" "$REPO_ROOT/scripts/build_release.py" "$@"
