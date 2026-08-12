#!/usr/bin/env bash
# session-restart.sh — LAST RESORT: tmux itself is the broken layer.
#
# See TASK.md task-b0b3f602 / .claude/skills/session-restart. Use this only
# when tmux is wedged, wrongly named, or gone while the process lingers —
# i.e. when scripts/terminal-restart.sh's `respawn-pane` cannot even be
# delivered. If claude is merely stuck/stale/confused but tmux is fine, that
# script is the right (much cheaper) tool, not this one.
#
# Tears the whole stack down (session-kill.sh --status saved) and rebuilds
# it (spawn-cto.sh / spawn-cxo.sh --resume) with the SAME session id and the
# SAME resume UUID — a new tmux session + a new iTerm window, but the same
# identity, so DEV reports and CEO history still route to it.
#
# Usage:
#   bash scripts/session-restart.sh                # this session (from env)
#   bash scripts/session-restart.sh cfo-a1b2c3d4    # some other session, by name
#   bash scripts/session-restart.sh --force cfo-a1b2c3d4
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKS_DIR="$ROOT/state/locks"

FORCE=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) ARGS+=("$a") ;;
  esac
done

NAME="${ARGS[0]:-}"
if [ -z "$NAME" ]; then
  ROLE="${CXO_ROLE:-cto}"
  SID="${CXO_SESSION_ID:-${CTO_SESSION_ID:-}}"
  if [ -z "$SID" ]; then
    echo "session-restart: no session name given and no CXO_SESSION_ID/CTO_SESSION_ID in env" >&2
    exit 2
  fi
  NAME="$ROLE-$SID"
fi
ROLE="${NAME%%-*}"
SID="${NAME#*-}"

FORCE_ARGS=()
[ "$FORCE" = "1" ] && FORCE_ARGS=(--force)
CHECK_RC=0
CHECK_MSG="$(cd "$ROOT" && python3 -m tools.terminal_restart check \
    --name "$NAME" --locks-dir "$LOCKS_DIR" ${FORCE_ARGS[@]+"${FORCE_ARGS[@]}"})" || CHECK_RC=$?
if [ -n "$CHECK_MSG" ]; then
  echo "session-restart: $CHECK_MSG" >&2
fi
if [ "$CHECK_RC" -ne 0 ]; then
  exit 1
fi

# Capture id+uuid FIRST, to a temp file OUTSIDE state/locks/ — session-kill.sh's
# reap_locks deletes the .lock/.run/.tty/.winid/.watcher-pid/.topic family
# (deliberately keeping .uuid — tools.session_name.KEEP_SUFFIXES) and this
# capture must survive that regardless.
CAPTURE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/session-restart-XXXXXX")"
CAPTURE_FILE="$CAPTURE_DIR/$NAME.json"
( cd "$ROOT" && python3 -m tools.terminal_restart capture \
    --name "$NAME" --locks-dir "$LOCKS_DIR" --dest "$CAPTURE_FILE" ) >/dev/null
UUID="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['uuid'])" "$CAPTURE_FILE")"
echo "session-restart: captured identity for '$NAME' -> $CAPTURE_FILE (uuid=$UUID)"

LOG_FILE="$ROOT/state/logs/$NAME.log"
LOG_SIZE="unknown"
[ -f "$LOG_FILE" ] && LOG_SIZE="$(du -h "$LOG_FILE" 2>/dev/null | cut -f1 | tr -d '[:space:]')"
echo "session-restart: resume is NOT free — claude re-reads the whole prior" >&2
echo "  transcript on '-r'. Rough size proxy ($LOG_FILE): ${LOG_SIZE:-unknown}." >&2
echo "session-restart: the in-flight turn (if any) is lost. Files on disk /" >&2
echo "  worktrees are untouched — only the tmux+claude stack is torn down." >&2

VERIFY_DELAY=25
DELAY=4

# Resume by the FULL uuid the capture resolved, never by the short id.
# `--resume <sid>` makes spawn-cto.sh re-read state/locks/<name>.uuid itself —
# exactly the unverified value this script just went to the trouble of
# resolving — and by this point the old session is already torn down, so a
# resume into a missing transcript has nothing left to fall back to.
if [ "$ROLE" = "cto" ]; then
  SPAWN_CMD="bash '$ROOT/scripts/spawn-cto.sh' --id '$SID' --resume '$UUID'"
else
  SPAWN_CMD="bash '$ROOT/scripts/spawn-cxo.sh' --role '$ROLE' --id '$SID' --resume '$UUID'"
fi

CURRENT=""
[ -n "${TMUX:-}" ] && CURRENT="$(tmux display-message -p '#S' 2>/dev/null || true)"

if [ "$CURRENT" = "$NAME" ]; then
  # We are running inside the very session about to be torn down. Defer the
  # whole sequence (kill, respawn, verify) — same shape as session-kill.sh —
  # so this message flushes first. `session-kill.sh --delay 0` inside our
  # own already-deferred block skips ITS internal defer (which would only
  # re-detect the same self-match and wait again); ours is the one delay
  # that matters here.
  echo "session-restart: rebuilding THIS session — pane will end in ${DELAY}s, then verify against $LOG_FILE"
  nohup bash -c "
    sleep $DELAY
    bash '$ROOT/scripts/session-kill.sh' --status saved --delay 0 '$NAME'
    sleep 2
    $SPAWN_CMD
    sleep $VERIFY_DELAY
    cd '$ROOT'
    if ! python3 -m tools.terminal_restart verify --name '$NAME' --locks-dir '$LOCKS_DIR' --delay 0 >>'$LOG_FILE' 2>&1; then
      {
        echo \"\$(date -u +%FT%TZ) session-restart: VERIFY FAILED after rebuild of '$NAME'\"
        echo \"\$(date -u +%FT%TZ) session-restart: resume by hand: bash scripts/spawn-cto.sh --resume $SID  (uuid: $UUID)\"
      } >>'$LOG_FILE' 2>&1
    fi
  " >/dev/null 2>&1 &
  disown 2>/dev/null || true
  exit 0
fi

# Rebuilding a DIFFERENT session — no self-kill risk, run synchronously.
bash "$ROOT/scripts/session-kill.sh" --status saved "$NAME"
sleep 2
eval "$SPAWN_CMD"

echo "session-restart: waiting ${VERIFY_DELAY}s to verify..."
VERIFY_RC=0
VERIFY_OUT="$(cd "$ROOT" && python3 -m tools.terminal_restart verify \
    --name "$NAME" --locks-dir "$LOCKS_DIR" --delay "$VERIFY_DELAY")" || VERIFY_RC=$?
echo "$VERIFY_OUT"
if [ "$VERIFY_RC" -ne 0 ]; then
  echo "session-restart: VERIFY FAILED for '$NAME' — resume by hand:" >&2
  echo "  bash scripts/spawn-cto.sh --resume $SID  (uuid: $UUID)" >&2
  exit 1
fi
echo "session-restart: '$NAME' rebuilt OK — same id + uuid, new tmux session + iTerm window."
