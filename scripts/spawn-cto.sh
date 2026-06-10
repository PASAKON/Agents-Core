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
#   bash scripts/spawn-cto.sh --id <id>      # force a specific CTO id (collision-checked)
#
# Inherited CTO_SESSION_ID from the parent shell is intentionally
# ignored — running this script from inside an existing CTO chat would
# otherwise duplicate that chat's id into the new tab.
set -euo pipefail

ROOT="/Users/gob/Projects/Agents"

WITH_LOGS=0
EXPLICIT_ID=""
ARGS=()
prev=""
for a in "$@"; do
  if [ "$prev" = "--id" ]; then
    EXPLICIT_ID="$a"
    prev=""
    continue
  fi
  case "$a" in
    --with-logs) WITH_LOGS=1 ;;
    --id) prev="--id" ;;
    *) ARGS+=("$a") ;;
  esac
done

# Never inherit CTO_SESSION_ID from the parent shell. Running spawn-cto.sh
# from inside an existing CTO chat would otherwise clone the running id
# into the new tab. Explicit `--id <id>` is the only supported override.
unset CTO_SESSION_ID
if [ -n "$EXPLICIT_ID" ]; then
  CTO_SESSION_ID="$EXPLICIT_ID"
fi

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

# Generate a short CTO session ID so DEV reports route only to this CTO.
# Injected as CTO_SESSION_ID env into cto-claude.sh + MCP server.
#
# Collision avoidance: a lock file at state/locks/cto-<ID>.lock means a
# CTO chat is currently using that ID. If the PID inside is live, pick
# a different ID — reusing it would mis-route DEV replies. Stale locks
# (dead PID) are reaped. An explicit CTO_SESSION_ID from the parent env
# is honored but rejected outright if it collides with a live process.
LOCKS_DIR="$ROOT/state/locks"
mkdir -p "$LOCKS_DIR"

is_id_live() {
  local lock="$LOCKS_DIR/cto-$1.lock"
  [ -e "$lock" ] || return 1
  local pid
  pid="$(tr -d '[:space:]' <"$lock" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  if kill -0 "$pid" 2>/dev/null; then
    return 0
  fi
  rm -f "$lock"
  return 1
}

if [ -n "${CTO_SESSION_ID:-}" ]; then
  if is_id_live "$CTO_SESSION_ID"; then
    echo "CTO id $CTO_SESSION_ID already running (see $LOCKS_DIR/cto-$CTO_SESSION_ID.lock) — refuse to spawn duplicate" >&2
    exit 1
  fi
else
  for _try in 1 2 3 4 5 6 7 8 9 10; do
    candidate="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
    if ! is_id_live "$candidate"; then
      CTO_SESSION_ID="$candidate"
      break
    fi
  done
  if [ -z "${CTO_SESSION_ID:-}" ]; then
    echo "could not pick an unused CTO id after 10 tries" >&2
    exit 1
  fi
fi

CTO_TAB_TITLE="CTO #$CTO_SESSION_ID"
CTO_LOG="$ROOT/state/logs/cto-$CTO_SESSION_ID.log"

mkdir -p "$ROOT/state/logs"
touch "$CTO_LOG"

CHAT_CMD="export CTO_SESSION_ID='$CTO_SESSION_ID' && bash '$ROOT/scripts/cto-claude.sh' $CLAUDE_ARGS"
LOG_CMD="cd '$ROOT' && tail -F state/logs/cto-$CTO_SESSION_ID.log"
DEV_CMD="cd '$ROOT' && bash scripts/tail-dev-logs.sh"

EXTRA_TABS=""
if [ "$WITH_LOGS" = "1" ]; then
  EXTRA_TABS=$(cat <<APPLESCRIPT_EXTRA

    set logTab to (create tab with default profile)
    tell current session of logTab
      set name to "CTO Log #$CTO_SESSION_ID"
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
  set newWindow to (create window with default profile)
  tell newWindow
    tell current session of current tab
      set name to "$CTO_TAB_TITLE"
      write text "$CHAT_CMD"
    end tell
$EXTRA_TABS
  end tell
end tell
APPLESCRIPT

if [ "$WITH_LOGS" = "1" ]; then
  echo "spawned iTerm window id=$CTO_SESSION_ID (CTO chat + log + dev logs)."
else
  echo "spawned iTerm window id=$CTO_SESSION_ID (logs at state/logs/cto-$CTO_SESSION_ID.log)"
fi
