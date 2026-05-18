#!/usr/bin/env bash
# Launch Claude Code CLI with CTO role + org MCP server.
# Same UI as plain Claude Code — only difference is system prompt + tools.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROLE_PROMPT="$(cat "$ROOT/roles/cto.md")"
MCP_CONFIG="$ROOT/config/cto.mcp.json"

# CTO-only tool whitelist. mcp__org__* covers every tool from the stdio server.
ALLOWED="mcp__org__wiki_read mcp__org__wiki_list mcp__org__wiki_search mcp__org__wiki_write mcp__org__create_task mcp__org__delegate_task mcp__org__delegate_parallel_tasks mcp__org__get_task mcp__org__review_diff mcp__org__merge_task mcp__org__reopen_task mcp__org__list_projects mcp__org__stats Read Grep Glob Bash"

cd "$ROOT"
export CTO_SESSION=1
exec claude \
  -n "CTO" \
  --model opus \
  --permission-mode auto \
  --append-system-prompt "$ROLE_PROMPT" \
  --mcp-config "$MCP_CONFIG" \
  --allowed-tools $ALLOWED \
  "$@"
