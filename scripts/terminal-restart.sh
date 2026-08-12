#!/usr/bin/env bash
# terminal-restart.sh — replace a stuck/stale/confused claude in place.
#
# The common case (see TASK.md task-b0b3f602 / .claude/skills/terminal-restart):
# claude runs stale code, is stuck, or is confused, but tmux itself is fine.
# `tmux respawn-pane -k` replaces ONLY the process inside the pane — same
# pane, same window, same tmux session — so the iTerm tab never closes, the
# tmux session never dies, and state/locks/<name>.winid stays correct because
# the window never changed.
#
# If tmux itself is the broken layer (wedged, wrong name, or gone while the
# process lingers), this is the WRONG tool — use scripts/session-restart.sh.
#
# Usage:
#   bash scripts/terminal-restart.sh                    # this session (from env)
#   bash scripts/terminal-restart.sh cto-a1b2c3d4        # some other session, by name
#   bash scripts/terminal-restart.sh --force cto-a1b2c3d4
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKS_DIR="$ROOT/state/locks"

FORCE=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) ARGS+=("$a") ;;
  esac
done

NAME="${ARGS[0]:-}"
if [ -z "$NAME" ]; then
  ROLE="${CXO_ROLE:-cto}"
  SID="${CXO_SESSION_ID:-${CTO_SESSION_ID:-}}"
  if [ -z "$SID" ]; then
    echo "terminal-restart: no session name given and no CXO_SESSION_ID/CTO_SESSION_ID in env" >&2
    exit 2
  fi
  NAME="$ROLE-$SID"
fi

if ! tmux has-session -t "$NAME" 2>/dev/null; then
  echo "terminal-restart: no tmux session '$NAME' — tmux itself may be the" >&2
  echo "  broken layer here, which this script cannot fix. Try session-restart instead:" >&2
  echo "  bash scripts/session-restart.sh $NAME" >&2
  exit 1
fi

FORCE_ARGS=()
[ "$FORCE" = "1" ] && FORCE_ARGS=(--force)
CHECK_RC=0
CHECK_MSG="$(cd "$ROOT" && python3 -m tools.terminal_restart check \
    --name "$NAME" --locks-dir "$LOCKS_DIR" "${FORCE_ARGS[@]}")" || CHECK_RC=$?
if [ -n "$CHECK_MSG" ]; then
  echo "terminal-restart: $CHECK_MSG" >&2
fi
if [ "$CHECK_RC" -ne 0 ]; then
  exit 1
fi

UUID_FILE="$LOCKS_DIR/$NAME.uuid"
UUID="$(tr -d '[:space:]' <"$UUID_FILE")"
SID_PART="${NAME#*-}"

# Resume is not free: it reads the whole prior transcript back in. The
# per-session log is a rough (not exact) proxy for how much that is — real
# transcript size lives in ~/.claude/projects, not here, but this is enough
# to let the operator gauge "small" vs "this has been running for days."
LOG_FILE="$ROOT/state/logs/$NAME.log"
LOG_SIZE="unknown"
if [ -f "$LOG_FILE" ]; then
  LOG_SIZE="$(du -h "$LOG_FILE" 2>/dev/null | cut -f1 | tr -d '[:space:]')"
fi
echo "terminal-restart: resume is NOT free — claude re-reads the whole prior" >&2
echo "  transcript on '-r'. Rough size proxy ($LOG_FILE): ${LOG_SIZE:-unknown}." >&2
echo "terminal-restart: the in-flight turn (if any) is lost — anything the" >&2
echo "  pane was mid-tool-call on does not come back. Files on disk / worktrees" >&2
echo "  are untouched." >&2

RUN_FILE="$(cd "$ROOT" && python3 -m tools.terminal_restart build-run-file \
    --name "$NAME" --locks-dir "$LOCKS_DIR")"
echo "terminal-restart: resume run-file ready ($RUN_FILE), target uuid=$UUID"

VERIFY_DELAY=25
DELAY=4

CURRENT=""
[ -n "${TMUX:-}" ] && CURRENT="$(tmux display-message -p '#S' 2>/dev/null || true)"

if [ "$CURRENT" = "$NAME" ]; then
  # The command issuing `respawn-pane -k` is itself running inside the pane
  # about to be killed — defer it (same shape as session-kill.sh) so this
  # message flushes before the pane dies. Everything after the kill runs in
  # a detached, SIGHUP-proof subshell with nowhere left to print to but the
  # per-session log file.
  echo "terminal-restart: restarting THIS session — pane will end in ${DELAY}s, then verify against $LOG_FILE"
  nohup bash -c "
    sleep $DELAY
    tmux respawn-pane -k -t '$NAME' 'bash $RUN_FILE'
    sleep $VERIFY_DELAY
    cd '$ROOT'
    if ! python3 -m tools.terminal_restart verify --name '$NAME' --locks-dir '$LOCKS_DIR' --delay 0 >>'$LOG_FILE' 2>&1; then
      {
        echo \"\$(date -u +%FT%TZ) terminal-restart: VERIFY FAILED after respawn of '$NAME'\"
        echo \"\$(date -u +%FT%TZ) terminal-restart: resume by hand: bash scripts/spawn-cto.sh --resume $SID_PART  (uuid: $UUID)\"
      } >>'$LOG_FILE' 2>&1
    fi
  " >/dev/null 2>&1 &
  disown 2>/dev/null || true
  exit 0
fi

# Restarting a DIFFERENT session — no self-kill risk, run synchronously so
# the caller gets a real result instead of having to go check a log file.
RESPAWN_OUT="$(cd "$ROOT" && python3 -m tools.terminal_restart respawn \
    --name "$NAME" --locks-dir "$LOCKS_DIR" --run-file "$RUN_FILE" 2>&1)" \
  || { echo "terminal-restart: respawn-pane failed: $RESPAWN_OUT" >&2; exit 1; }
[ -n "$RESPAWN_OUT" ] && echo "terminal-restart: $RESPAWN_OUT"

echo "terminal-restart: waiting ${VERIFY_DELAY}s to verify..."
VERIFY_RC=0
VERIFY_OUT="$(cd "$ROOT" && python3 -m tools.terminal_restart verify \
    --name "$NAME" --locks-dir "$LOCKS_DIR" --delay "$VERIFY_DELAY")" || VERIFY_RC=$?
echo "$VERIFY_OUT"
if [ "$VERIFY_RC" -ne 0 ]; then
  echo "terminal-restart: VERIFY FAILED for '$NAME' — resume by hand:" >&2
  echo "  bash scripts/spawn-cto.sh --resume $SID_PART  (uuid: $UUID)" >&2
  exit 1
fi
echo "terminal-restart: '$NAME' restarted OK — tab/tmux session unchanged, claude replaced."
