#!/usr/bin/env bash
# Spawn an iTerm2 window with the CTO chat tab (default).
#   tab 1: Claude Code CLI w/ CTO role (scripts/cto-claude.sh)
#
# CTO + Dev log tabs are NOT opened by default — CEO does not watch them;
# the AI consumes logs via hooks. Pass --with-logs to also open them, or
# tail on demand: `tail -F state/logs/cto.log`.
#
# Usage:
#   bash scripts/spawn-cto.sh                # fresh Claude Code session
#   bash scripts/spawn-cto.sh --new          # fresh (alias)
#   bash scripts/spawn-cto.sh --last         # resume most recent (claude -c)
#   bash scripts/spawn-cto.sh --resume <id>  # claude -r <id>
#   bash scripts/spawn-cto.sh --with-logs    # also open cto.log + dev logs tabs
set -euo pipefail

ROOT="/Users/gob/Projects/Agents"

WITH_LOGS=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --with-logs) WITH_LOGS=1 ;;
    *) ARGS+=("$a") ;;
  esac
done

# Translate legacy cto_chat args → claude CLI args
CLAUDE_ARGS=""
case "${ARGS[0]:-}" in
  --last) CLAUDE_ARGS="-c" ;;
  --resume) CLAUDE_ARGS="-r ${ARGS[1]:-}" ;;
  --new|"") CLAUDE_ARGS="" ;;
  *) CLAUDE_ARGS="${ARGS[*]}" ;;
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

EXTRA_TABS=""
if [ "$WITH_LOGS" = "1" ]; then
  EXTRA_TABS=$(cat <<APPLESCRIPT_EXTRA

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
APPLESCRIPT_EXTRA
)
fi

osascript <<APPLESCRIPT
tell application "iTerm"
  activate
  set newWindow to (create window with default profile)
  tell newWindow
    tell current session of current tab
      set name to "CTO Chat"
      write text "$CHAT_CMD"
    end tell
$EXTRA_TABS
  end tell
end tell
APPLESCRIPT

if [ "$WITH_LOGS" = "1" ]; then
  echo "spawned iTerm window with 3 tabs (CTO chat + cto.log + dev logs)."
else
  echo "spawned iTerm window with CTO chat tab. (logs on disk; --with-logs to tail)"
fi
