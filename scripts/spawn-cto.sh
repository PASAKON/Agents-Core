#!/usr/bin/env bash
# Spawn an iTerm2 window with 3 tabs for CTO chat + log streams.
#   tab 1: Claude Code CLI w/ CTO role (scripts/cto-claude.sh)
#   tab 2: tail -F state/logs/cto.log
#   tab 3: tail -F state/logs/*_latest.log  (auto-refreshing)
#
# Usage:
#   bash scripts/spawn-cto.sh           # fresh Claude Code session
#   bash scripts/spawn-cto.sh --new     # fresh (alias)
#   bash scripts/spawn-cto.sh --last    # resume most recent (claude -c)
#   bash scripts/spawn-cto.sh --resume <id>  # claude -r <id>
set -euo pipefail

ROOT="/Users/gob/Projects/Agents"

# Translate legacy cto_chat args → claude CLI args
CLAUDE_ARGS=""
case "${1:-}" in
  --last) CLAUDE_ARGS="-c" ;;
  --resume) CLAUDE_ARGS="-r ${2:-}" ;;
  --new|"") CLAUDE_ARGS="" ;;
  *) CLAUDE_ARGS="$*" ;;
esac

if ! [ -d "$ROOT/.venv" ]; then
  echo "venv not found at $ROOT/.venv — run scripts/setup.sh first" >&2
  exit 1
fi

mkdir -p "$ROOT/state/logs"
touch "$ROOT/state/logs/cto.log"

CHAT_CMD="bash '$ROOT/scripts/cto-claude.sh' $CLAUDE_ARGS"
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
