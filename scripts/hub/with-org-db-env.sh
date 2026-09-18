#!/usr/bin/env bash
# Sources the hub's env file (ORG_DB_URL etc.) into this process, then execs
# the given command. Single indirection point so the secret is read at
# spawn time everywhere a process needs it -- MCP servers via
# config/cto.mcp.json + config/worker.mcp.json, launchd daemons via their
# plists -- without the value ever landing in a git-tracked file or a plist
# (docs/design/tasks-db-hub.md §3.3 step 4). Rotating the password later
# means editing the one env file, not every consumer.
#
# Usage: with-org-db-env.sh <real command> [args...]
#
# MOONIEX_ORG_DB_ENV overrides the env file path -- used by
# scripts/hub/cutover-mac.sh's own dry-run tests so they never touch the
# real ~/.config/mooniex/org-db.env.
set -eo pipefail

ENV_FILE="${MOONIEX_ORG_DB_ENV:-$HOME/.config/mooniex/org-db.env}"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
exec "$@"
