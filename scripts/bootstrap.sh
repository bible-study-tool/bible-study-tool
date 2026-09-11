#!/usr/bin/env bash
# bootstrap.sh — One-command environment setup for the Adventist Bible Study Tool.
#
# Detects or creates a Python virtual environment (.venv), installs the package
# in editable mode with development/test dependencies, validates imports, and
# runs basic health checks.
#
# Usage:
#   ./scripts/bootstrap.sh          # standard bootstrap (editable install with test extras)
#   ./scripts/bootstrap.sh --ml     # include sentence-transformers (for ML embeddings)
#   ./scripts/bootstrap.sh --verify # run verify_all.sh after bootstrapping
#
# Adheres to ADR-011 (Automated Bootstrapping & Developer Experience).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WANT_ML=false
WANT_DIST=false
RUN_VERIFY=false

for arg in "$@"; do
  case "$arg" in
    --ml)
      WANT_ML=true
      ;;
    --dist)
      WANT_DIST=true
      ;;
    --all)
      WANT_ML=true
      WANT_DIST=true
      ;;
    --verify)
      RUN_VERIFY=true
      ;;
    -h|--help)
      echo "Usage: $0 [--ml] [--dist] [--all] [--verify]"
      echo
      echo "Options:"
      echo "  --ml       Install optional machine-learning dependencies (sentence-transformers)"
      echo "  --dist     Install standalone packaging tools (pyinstaller)"
      echo "  --all      Install all optional dependency groups (ml + dist)"
      echo "  --verify   Run full verification suite (scripts/verify_all.sh) after bootstrap"
      echo "  -h, --help Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      echo "Usage: $0 [--ml] [--dist] [--all] [--verify]" >&2
      exit 2
      ;;
  esac
done

EXTRAS="test"
if [[ "$WANT_ML" == true ]]; then
  EXTRAS="$EXTRAS,ml"
fi
if [[ "$WANT_DIST" == true ]]; then
  EXTRAS="$EXTRAS,dist"
fi
INSTALL_EXTRAS=".[${EXTRAS}]"

echo "=============================================================="
echo "Adventist Bible Study Tool — Environment Bootstrap"
echo "=============================================================="

find_python() {
  for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
      if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

SYSTEM_PYTHON="$(find_python || true)"
if [[ -z "$SYSTEM_PYTHON" ]]; then
  echo "ERROR: Python 3.10 or higher is required but was not found on PATH." >&2
  exit 1
fi

PY_VERSION="$("$SYSTEM_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")"
echo "Detected Python: $SYSTEM_PYTHON (v$PY_VERSION)"

VENV_DIR="$REPO_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment at $VENV_DIR ..."
  if command -v uv >/dev/null 2>&1; then
    uv venv --python "$SYSTEM_PYTHON" "$VENV_DIR"
  else
    "$SYSTEM_PYTHON" -m venv "$VENV_DIR"
  fi
else
  echo "Existing virtual environment found at $VENV_DIR."
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "ERROR: Virtual environment Python not found at $VENV_PYTHON" >&2
  exit 1
fi

echo "Installing package in editable mode ($INSTALL_EXTRAS) ..."
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$VENV_PYTHON" -e "$INSTALL_EXTRAS"
else
  "$VENV_PYTHON" -m pip install --upgrade pip 2>/dev/null || true
  "$VENV_PYTHON" -m pip install -e "$INSTALL_EXTRAS"
fi

echo "Verifying environment..."
"$VENV_PYTHON" -c "import yaml, numpy, pytest, search; print('✔ Core dependencies and namespace packages successfully verified.')"

if [[ "$RUN_VERIFY" == true ]]; then
  echo
  echo "Running full verification suite..."
  PYTHON="$VENV_PYTHON" bash "$REPO_ROOT/scripts/verify_all.sh"
fi

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Bootstrap complete! Environment is ready."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "To activate your virtual environment:"
echo "  source .venv/bin/activate"
echo
echo "To check project status:"
echo "  python scripts/status.py"
echo
echo "To run the full test & verification suite:"
echo "  bash scripts/verify_all.sh"
echo
