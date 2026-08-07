#!/usr/bin/env bash
# session-kill.sh — actually end a C-level session, not just its iTerm tab.
#
# Since the tmux migration (2026-08-07) an iTerm tab is only a *viewer* of a
# tmux session, so closing the tab detaches and leaves the Claude process
# running: it keeps burning quota, keeps counting against the 5-session cap,
# and keeps showing up on the phone console. This is the other half — it ends
# the session itself.
#
#   bash scripts/session-kill.sh                 # this session (from its env)
#   bash scripts/session-kill.sh cto-a1b2c3d4    # some other session, by name
#   bash scripts/session-kill.sh --delay 0 <name>
#
# Killing the session you are *inside* also kills the process running this
# script, which would truncate whatever the agent is still printing. So a
# self-kill is deferred: nohup'd (SIGHUP-proof, since the pane's children are
# HUPed on teardown) and delayed long enough for the final report to flush.
set -euo pipefail

DELAY=4
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --delay) DELAY="${2:?--delay needs a number}"; shift 2 ;;
    -h|--help) sed -n '2,18p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done

NAME="${ARGS[0]:-}"
if [ -z "$NAME" ]; then
  ROLE="${CXO_ROLE:-cto}"
  SID="${CXO_SESSION_ID:-${CTO_SESSION_ID:-}}"
  if [ -z "$SID" ]; then
    echo "session-kill: no session name given and no CXO_SESSION_ID/CTO_SESSION_ID in env" >&2
    exit 2
  fi
  NAME="$ROLE-$SID"
fi

if ! tmux has-session -t "$NAME" 2>/dev/null; then
  echo "session-kill: no tmux session '$NAME' (already gone)"
  exit 0
fi

# Are we inside the session we're about to kill?
CURRENT=""
[ -n "${TMUX:-}" ] && CURRENT="$(tmux display-message -p '#S' 2>/dev/null || true)"

if [ "$CURRENT" = "$NAME" ]; then
  echo "session-kill: ending '$NAME' (this session) in ${DELAY}s"
  nohup bash -c "sleep $DELAY; tmux kill-session -t '$NAME'" >/dev/null 2>&1 &
  disown 2>/dev/null || true
else
  tmux kill-session -t "$NAME"
  echo "session-kill: ended '$NAME'"
fi
