#!/usr/bin/env bash
# The live C-level session list (tools/live_sessions.py) with the hub env, on a POSIX host.
#
#   bash scripts/live-sessions.sh [--all] [--id <sid>] [--json] [--local]
#
# org-python.sh puts ORG_DB_URL in the environment (never echoed). infisical prints a
# "[infisical run] ... secret NAMES ... -> python" banner on stderr; that one line is dropped,
# every other stderr line stays. The exit code is the python's.
# Windows has no such wrapper: docs/ops/live-sessions.md has the equivalent line.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ERR="$(mktemp)"
trap 'rm -f "$ERR"' EXIT
rc=0
bash "$ROOT/scripts/hub/org-python.sh" -m tools.live_sessions "$@" 2>"$ERR" || rc=$?
grep -v '^\[infisical run\] ' "$ERR" >&2 || true
exit "$rc"
