#!/usr/bin/env bash
# bootstrap.sh — Repository-root entrypoint delegating to scripts/bootstrap.sh.
#
# Usage:
#   ./bootstrap.sh                  # install virtualenv and core dependencies
#   ./bootstrap.sh --data           # install deps + fetch pinned data + hydrate SQLite DBs
#   ./bootstrap.sh --data --verify  # full setup + verify_all.sh (one command from fresh clone)
#   ./bootstrap.sh --all-in-one     # all optional groups (ml, dist, data, verify)
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$REPO_ROOT/scripts/bootstrap.sh" "$@"
