#!/usr/bin/env bash
# spawn-ph.sh — start a Project Head for one project (org restructure P2, plan §3.2).
#
#   bash scripts/spawn-ph.sh --project <Name> [--brief-file <path> | --brief <text>] [--dry-run]
#
# Run it from inside a C-level session. The Project Head's lane is your role and
# its owner is your session; it reports to you and to no one else. Refused unless
# ORG_PH_ROLES=1, roles/project_head.md exists (the COO writes it) and the
# resource gate passes. Prints one JSON line: session id, tmux session, brief path.
# The logic and every refusal live in tools/spawn_ph.py.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY=python3
cd "$ROOT"
exec "$PY" -m tools.spawn_ph "$@"
