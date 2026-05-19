#!/usr/bin/env bash
# Launch Claude Code CLI with CTO role + org MCP server.
# Same UI as plain Claude Code — only difference is system prompt + tools.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE_PROMPT="$(cat "$ROOT/roles/cto.md")"
MCP_CONFIG="$ROOT/config/cto.mcp.json"

# CTO-only tool whitelist. mcp__org__* covers every tool from the stdio server.
ALLOWED="mcp__org__wiki_read mcp__org__wiki_list mcp__org__wiki_search mcp__org__wiki_write mcp__org__create_task mcp__org__check_collisions mcp__org__delegate_task mcp__org__delegate_parallel_tasks mcp__org__get_task mcp__org__list_my_tasks mcp__org__review_diff mcp__org__merge_task mcp__org__reopen_task mcp__org__list_projects mcp__org__stats Read Grep Glob Bash"

cd "$ROOT"
export CTO_SESSION=1
# Generate CTO ID if not inherited from spawn-cto.sh (e.g. when running
# cto-claude.sh standalone). Re-emit tab title in case the parent shell
# precmd reset it.
if [ -z "${CTO_SESSION_ID:-}" ]; then
  CTO_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
  export CTO_SESSION_ID
fi
printf '\033]0;CTO Chat #%s\007' "$CTO_SESSION_ID"
exec claude \
  -n "CTO Chat #$CTO_SESSION_ID" \
  --model opus \
  --permission-mode auto \
  --append-system-prompt "$ROLE_PROMPT" \
  --mcp-config "$MCP_CONFIG" \
  --allowed-tools $ALLOWED \
  "$@"
