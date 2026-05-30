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

# Per-CTO lock so the claude-CLI path has the same collision defense
# that runners/cto_chat.py provides for the Python REPL. spawn-cto.sh's
# is_id_live() check relies on this file existing while a CTO chat is
# alive.
LOCKS_DIR="$ROOT/state/locks"
mkdir -p "$LOCKS_DIR"
LOCKFILE="$LOCKS_DIR/cto-$CTO_SESSION_ID.lock"
if [ -e "$LOCKFILE" ]; then
  existing_pid="$(tr -d '[:space:]' <"$LOCKFILE" 2>/dev/null || true)"
  if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "CTO id $CTO_SESSION_ID already running as pid $existing_pid — refuse to start a second one." >&2
    exit 1
  fi
  rm -f "$LOCKFILE"
fi
echo "$$" >"$LOCKFILE"

# Find the iTerm window id whose session shares our TTY, then record it
# so tools/delegate.py can target this exact window when spawning DEV
# tabs. Matching by window id is immune to the session-name flicker
# that causes name-based lookups to misroute DEVs to the wrong CTO.
WINID_FILE="$LOCKS_DIR/cto-$CTO_SESSION_ID.winid"
MY_TTY="$(tty 2>/dev/null || true)"
if [ -n "$MY_TTY" ]; then
  WINID="$(osascript 2>/dev/null <<APPLE || true
tell application "iTerm"
  repeat with w in windows
    repeat with t in tabs of w
      repeat with s in sessions of t
        try
          if tty of s is "$MY_TTY" then
            return (id of w) as string
          end if
        end try
      end repeat
    end repeat
  end repeat
  return ""
end tell
APPLE
)"
  WINID="$(printf '%s' "$WINID" | tr -d '[:space:]')"
  if [ -n "$WINID" ]; then
    echo "$WINID" >"$WINID_FILE"
  fi
fi

trap 'rm -f "$LOCKFILE" "$WINID_FILE"' EXIT INT TERM

printf '\033]0;CTO Chat #%s\007' "$CTO_SESSION_ID"
# `exec` would replace the shell and skip the EXIT trap, leaving a
# stale lock. Run claude as a child instead and propagate its exit code.
claude \
  -n "CTO Chat #$CTO_SESSION_ID" \
  --model claude-opus-4-8 \
  --effort max \
  --permission-mode auto \
  --append-system-prompt "$ROLE_PROMPT" \
  --mcp-config "$MCP_CONFIG" \
  --allowed-tools $ALLOWED \
  "$@"
exit $?
