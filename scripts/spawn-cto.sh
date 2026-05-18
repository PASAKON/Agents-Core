#!/usr/bin/env bash
# Spawn an iTerm2 window with 3 tabs for CTO chat + log streams.
#   tab 1: interactive CTO chat REPL (python -m runners.cto_chat)
#   tab 2: tail -F state/logs/cto.log
#   tab 3: tail -F state/logs/*_latest.log  (auto-refreshing)
#
# Usage:
#   bash scripts/spawn-cto.sh           # picker if prior sessions exist
#   bash scripts/spawn-cto.sh --new     # always fresh
#   bash scripts/spawn-cto.sh --last    # resume most recent
#   bash scripts/spawn-cto.sh --resume <id>
set -euo pipefail

ROOT="/Users/gob/Projects/Agents"
CHAT_ARGS="${*:-}"

if ! [ -d "$ROOT/.venv" ]; then
  echo "venv not found at $ROOT/.venv — run scripts/setup.sh first" >&2
  exit 1
fi

mkdir -p "$ROOT/state/logs"
touch "$ROOT/state/logs/cto.log"

CHAT_CMD="cd '$ROOT' && source .venv/bin/activate && python -m runners.cto_chat $CHAT_ARGS"
LOG_CMD="cd '$ROOT' && tail -F state/logs/cto.log"
DEV_CMD="cd '$ROOT' && bash scripts/tail-dev-logs.sh"

osascript <<APPLESCRIPT
tell application "iTerm"
  activate
  set newWindow to (create window with default profile)
  tell newWindow
    tell current session of current tab
      set name to "CTO Chat"
      write text "$CHAT_CMD"
    end tell

    set logTab to (create tab with default profile)
    tell current session of logTab
      set name to "CTO Log"
      write text "$LOG_CMD"
    end tell

    set devTab to (create tab with default profile)
    tell current session of devTab
      set name to "Dev Logs"
      write text "$DEV_CMD"
    end tell

    select first tab
  end tell
end tell
APPLESCRIPT

echo "spawned iTerm window with 3 tabs."
echo "  tab 1: CTO chat"
echo "  tab 2: CTO log"
echo "  tab 3: Dev logs"
