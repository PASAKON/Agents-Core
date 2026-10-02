#!/usr/bin/env bash
# Run the Agents venv python with the task ledger reachable.
#
#   bash scripts/hub/org-python.sh -m tools.session_charter get
#
# After the hub cutover (G1, 2026-10-02) lib.db reads the ledger from Postgres:
# it needs ORG_DB_URL in the environment and psycopg in the interpreter. A
# shell script's bare `python3` is the system interpreter (no psycopg), and a
# tmux pane or launcher started before the cutover has no ORG_DB_URL, so the
# CLI died on the archived state/tasks.db (task-1b8ef857).
#
# This picks the venv interpreter and, when this host is on the hub, starts it
# through scripts/hub/with-org-db-env.sh. "On the hub" is decided by
# cxo_mcp_config.org_db_wrapper(), the rule that already wraps every org MCP
# server, so a CLI call and the MCP server never land on different ledgers.
# A host that is not on the hub gets the plain venv interpreter.
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

if [ -n "${ORG_DB_URL:-}" ]; then
  exec "$PY" "$@"
fi

WRAPPER="$("$PY" -c '
import sys
sys.path.insert(0, sys.argv[1] + "/scripts/lib")
import cxo_mcp_config
print(cxo_mcp_config.org_db_wrapper(sys.argv[1]) or "")
' "$ROOT" 2>/dev/null || true)"

if [ -n "$WRAPPER" ]; then
  exec bash "$WRAPPER" "$PY" "$@"
fi
exec "$PY" "$@"
