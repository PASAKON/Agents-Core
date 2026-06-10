#!/usr/bin/env bash
# Spawn an iTerm2 window with a C-level chat tab (cto/cmo/cgo/cfo).
# Generalization of spawn-cto.sh — all C-levels share the same spawn
# machinery and only differ in role doc + tab title + lock prefix.
#
# Usage:
#   bash scripts/spawn-cxo.sh --role cfo                    # fresh session
#   bash scripts/spawn-cxo.sh --role cmo --last             # claude -c
#   bash scripts/spawn-cxo.sh --role cgo --resume <id>      # claude -r <id>
#   bash scripts/spawn-cxo.sh --role cto --with-logs        # also open log tabs
#   bash scripts/spawn-cxo.sh --role cfo --id <id>          # force a specific id
#
# Phase 2 flag passthrough note:
#   Unknown flags fall into ARGS and are forwarded to cxo-claude.sh via
#   $CLAUDE_ARGS. Simple single-word flags pass through; multi-word values
#   (e.g. --tab-title "CFO <- CTO: topic") are not reliably forwarded due to
#   word-splitting. For ephemeral spawns from tools/send_to_cxo.py --spawn,
#   use the _spawn_new_ephemeral() temp-script path — it calls cxo-claude.sh
#   directly with no shell-in-shell quoting issues.
#
# Inherited CXO_SESSION_ID is intentionally ignored — re-running this
# from inside an existing C-level chat would otherwise duplicate the id.
set -euo pipefail

ROOT="/Users/gob/Projects/Agents"

ROLE=""
WITH_LOGS=0
EXPLICIT_ID=""
ARGS=()
prev=""
for a in "$@"; do
  if [ "$prev" = "--role" ]; then
    ROLE="$a"; prev=""; continue
  fi
  if [ "$prev" = "--id" ]; then
    EXPLICIT_ID="$a"; prev=""; continue
  fi
  case "$a" in
    --role) prev="--role" ;;
    --id)   prev="--id" ;;
    --with-logs) WITH_LOGS=1 ;;
    *) ARGS+=("$a") ;;
  esac
done

if [ -z "$ROLE" ]; then
  echo "usage: spawn-cxo.sh --role <cto|cmo|cgo|cfo> [--new|--last|--resume <id>|--with-logs|--id <id>]" >&2
  exit 2
fi

# Validate role early so we fail before any AppleScript work.
if [ ! -f "$ROOT/roles/$ROLE.md" ]; then
  echo "role doc not found: $ROOT/roles/$ROLE.md" >&2
  exit 2
fi

# Never inherit a session id from the parent shell.
unset CXO_SESSION_ID CTO_SESSION_ID
if [ -n "$EXPLICIT_ID" ]; then
  CXO_SESSION_ID="$EXPLICIT_ID"
fi

# Translate session args → claude CLI args (identical to spawn-cto.sh).
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

# Resolve display name (CTO / CMO / CGO / CFO) for tab title + log file.
DISPLAY="$(cd "$ROOT" && source .venv/bin/activate && python3 -c "
from lib.config import display_for, is_c_level
import sys
if not is_c_level('$ROLE'):
    print('role $ROLE is not a C-level role', file=sys.stderr); sys.exit(2)
print(display_for('$ROLE'))
")"
[ -n "$DISPLAY" ] || exit 2

LOCKS_DIR="$ROOT/state/locks"
mkdir -p "$LOCKS_DIR"

is_id_live() {
  local lock="$LOCKS_DIR/$ROLE-$1.lock"
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

if [ -n "${CXO_SESSION_ID:-}" ]; then
  if is_id_live "$CXO_SESSION_ID"; then
    echo "$DISPLAY id $CXO_SESSION_ID already running (see $LOCKS_DIR/$ROLE-$CXO_SESSION_ID.lock)" >&2
    exit 1
  fi
else
  for _try in 1 2 3 4 5 6 7 8 9 10; do
    candidate="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
    if ! is_id_live "$candidate"; then
      CXO_SESSION_ID="$candidate"
      break
    fi
  done
  if [ -z "${CXO_SESSION_ID:-}" ]; then
    echo "could not pick an unused $DISPLAY id after 10 tries" >&2
    exit 1
  fi
fi

TAB_TITLE="$DISPLAY #$CXO_SESSION_ID"
LOG_FILE="$ROOT/state/logs/$ROLE-$CXO_SESSION_ID.log"
mkdir -p "$ROOT/state/logs"
touch "$LOG_FILE"

CHAT_CMD="export CXO_SESSION_ID='$CXO_SESSION_ID' && bash '$ROOT/scripts/cxo-claude.sh' --role $ROLE $CLAUDE_ARGS"
LOG_CMD="cd '$ROOT' && tail -F state/logs/$ROLE-$CXO_SESSION_ID.log"
DEV_CMD="cd '$ROOT' && bash scripts/tail-dev-logs.sh"

EXTRA_TABS=""
if [ "$WITH_LOGS" = "1" ]; then
  EXTRA_TABS=$(cat <<APPLESCRIPT_EXTRA

    set logTab to (create tab with default profile)
    tell current session of logTab
      set name to "$DISPLAY Log #$CXO_SESSION_ID"
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
      set name to "$TAB_TITLE"
      write text "$CHAT_CMD"
    end tell
$EXTRA_TABS
  end tell
end tell
APPLESCRIPT

if [ "$WITH_LOGS" = "1" ]; then
  echo "spawned iTerm window id=$CXO_SESSION_ID ($DISPLAY chat + log + dev logs)."
else
  echo "spawned iTerm window id=$CXO_SESSION_ID (logs at state/logs/$ROLE-$CXO_SESSION_ID.log)"
fi
