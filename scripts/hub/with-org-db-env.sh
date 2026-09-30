#!/usr/bin/env bash
# Puts ORG_DB_URL into the environment of the given command, then execs it.
# Single indirection point so the secret is read at spawn time everywhere a
# process needs it -- MCP servers via config/cto.mcp.json + config/worker.mcp.json,
# launchd daemons via their plists -- without the value ever landing in a
# git-tracked file or a plist (docs/design/tasks-db-hub.md §3.3 step 4).
#
# Usage: with-org-db-env.sh <real command> [args...]
#
# Order (docs/design/org-mesh-w18-contabo-consumers.md):
#   (a) the hub env file exists: source it. The Mac's file carries ORG_DB_URL.
#       Contabo's file carries only POSTGRES_* and no ORG_DB_URL.
#   (b) ORG_DB_URL is still unset and this host's Infisical identity file exists
#       (/etc/infisical/<host>.env): run the command through
#       `tools/infisical_setup.py run Agents-Core prod`, which puts the project's
#       secrets, ORG_DB_URL among them, into its environment. Without this leg a
#       Contabo MCP server would stay on state/tasks.db after the cutover (split
#       brain), because no .env may be extended (CLAUDE.md §Secrets).
#   (c) neither: plain exec, nothing added.
# The identity file is only tested for existence, never opened. No value is printed.
#
# Overrides, used by the tests so they never reach a real file:
#   MOONIEX_ORG_DB_ENV         env file path (default ~/.config/mooniex/org-db.env)
#   MOONIEX_NODE_YAML          node file, for its `host:` line (default ~/.config/mooniex/node.yaml)
#   ORG_HOST                   host name, wins over the node file
#   INFISICAL_CRED_DIR         identity file directory (default /etc/infisical), the
#                              same override tools/infisical_setup.py reads
#   MOONIEX_INFISICAL_ID_FILE  identity file path, wins over the two lines above
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ENV_FILE="${MOONIEX_ORG_DB_ENV:-$HOME/.config/mooniex/org-db.env}"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [ -z "${ORG_DB_URL:-}" ]; then
  ID_FILE="${MOONIEX_INFISICAL_ID_FILE:-}"
  if [ -z "$ID_FILE" ]; then
    HOST="$(printf '%s' "${ORG_HOST:-}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
      | tr '[:upper:]' '[:lower:]')"
    NODE_FILE="${MOONIEX_NODE_YAML:-$HOME/.config/mooniex/node.yaml}"
    if [ -z "$HOST" ] && [ -f "$NODE_FILE" ]; then
      # last top-level `host:` line wins; drop a ` # comment`, edge quotes, edge space and CR
      HOST="$(sed -n 's/^host[[:space:]]*:[[:space:]]*//p' "$NODE_FILE" | tail -n 1 \
        | sed -e 's/[[:space:]]*#.*$//' -e 's/^[[:space:]"'"'"']*//' -e 's/[[:space:]"'"'"']*$//' \
        | tr '[:upper:]' '[:lower:]')"
    fi
    # a host name is a bare word; anything else must not build a path
    case "$HOST" in
      ""|*[!a-z0-9_-]*) HOST="" ;;
    esac
    if [ -n "$HOST" ]; then ID_FILE="${INFISICAL_CRED_DIR:-/etc/infisical}/$HOST.env"; fi
  fi
  if [ -n "$ID_FILE" ] && [ -f "$ID_FILE" ]; then
    exec python3 "$ROOT/tools/infisical_setup.py" run Agents-Core prod -- "$@"
  fi
fi
exec "$@"
