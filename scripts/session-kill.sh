#!/usr/bin/env bash
# session-kill.sh — actually end a C-level session, not just its iTerm tab.
#
# Since the tmux migration (2026-08-07) an iTerm tab is only a *viewer* of a
# tmux session, so closing the tab detaches and leaves the Claude process
# running: it keeps burning quota, keeps counting against the 5-session cap,
# and keeps showing up on the phone console. This is the other half — it ends
# the session itself.
#
#   bash scripts/session-kill.sh                        # this session, status=closed
#   bash scripts/session-kill.sh --status saved          # park it (resumable)
#   bash scripts/session-kill.sh cto-a1b2c3d4            # some other session, by name
#   bash scripts/session-kill.sh --delay 0 <name>
#   bash scripts/session-kill.sh --status force_saved --note "tests red" cto-a1b2c3d4
#
# --status records WHY the session ended in c_level_sessions (closed|saved|
# force_saved, default closed) via tools/session_status.record_close, BEFORE
# the kill, so the row exists even if the process dies mid-teardown. The resume
# UUID is copied out of <name>.uuid at that moment — that file is deliberately
# preserved on close (tools/session_name.KEEP_SUFFIXES), so this never competes
# with the reaper.
#
# Killing the session you are *inside* also kills the process running this
# script, which would truncate whatever the agent is still printing. So a
# self-kill is deferred: nohup'd (SIGHUP-proof, since the pane's children are
# HUPed on teardown) and delayed long enough for the final report to flush.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKS_DIR="$ROOT/state/locks"

# The launcher's EXIT trap normally removes these, but the trap never fires
# when the process was orphaned — the Aug-10 case ran for 9h with no tmux to
# attach to, its trap never reached. Killing the tmux session is what finally
# ends that process, so sweeping the lock family here is the backstop that
# leaves state/locks/<name>.* behind for nobody. The extension list mirrors
# tools/session_name.LOCK_SUFFIXES; keep them in sync.
reap_locks() {
  # .uuid is deliberately NOT here — see tools/session_name.KEEP_SUFFIXES. It
  # holds the full Claude UUID that `spawn-cto.sh --resume <id>` needs; the org's
  # short id is only its last 8 hex. Reaping it on close would leave the session
  # permanently unresumable, which is the opposite of what closing should mean.
  rm -f "$LOCKS_DIR/$NAME".lock "$LOCKS_DIR/$NAME".run \
        "$LOCKS_DIR/$NAME".tty \
        "$LOCKS_DIR/$NAME".winid "$LOCKS_DIR/$NAME".watcher-pid \
        "$LOCKS_DIR/$NAME".topic 2>/dev/null || true
}

# Record WHY this session ended in c_level_sessions, BEFORE the teardown that
# follows. Run synchronously (not in the deferred self-kill) so the row lands
# even if the process dies mid-teardown. Best-effort: a failure here must not
# block the kill — the record is recoverable, a zombie session is not — so the
# python traceback is let through to stderr and a one-line WARNING follows.
# Skipped when NAME is not <role>-<id> shaped (nothing to key the row on).
record_status() {
  case "$NAME" in
    *-*) : ;;
    *) return 0 ;;
  esac
  local role="${NAME%%-*}"          # split on the FIRST hyphen only — the id
  local sid="${NAME#*-}"            # may itself hold one (console fallback slug)
  local -a note=()
  [ -n "${NOTE:-}" ] && note=(--note "$NOTE")
  ( cd "$ROOT" && python3 -m tools.session_status close \
      --role "$role" --session-id "$sid" \
      --status "$STATUS" --locks-dir "$LOCKS_DIR" "${note[@]}" ) >/dev/null \
    || echo "session-kill: WARNING: could not record status='$STATUS' for '$NAME' (see traceback above) — kill still proceeds" >&2
}

DELAY=4
STATUS="closed"   # why the session ended — closed|saved|force_saved (task-728e4741)
NOTE=""
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --delay) DELAY="${2:?--delay needs a number}"; shift 2 ;;
    --status) STATUS="${2:?--status needs closed|saved|force_saved}"; shift 2 ;;
    --note) NOTE="${2:?--note needs text}"; shift 2 ;;
    -h|--help) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
case "$STATUS" in
  closed|saved|force_saved) : ;;
  *) echo "session-kill: invalid --status '$STATUS' (want closed|saved|force_saved)" >&2; exit 2 ;;
esac

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
  # No tmux to kill, but the lock family may have outlived it (the launcher's
  # EXIT trap does not always fire). Reap it so state/locks/<name>.* is not
  # left behind — but only when the lock's pid is dead. A LIVE pid here is the
  # orphan (a process burning quota with no tmux); deleting its lock would
  # hide it from the cap, so surface it instead and leave the deciding to a
  # human (or `python3 -m tools.session_gc --reap`).
  _LOCK="$LOCKS_DIR/$NAME.lock"
  if [ -e "$_LOCK" ]; then
    _PID="$(tr -d '[:space:]' <"$_LOCK" 2>/dev/null || true)"
    if [ -n "$_PID" ] && kill -0 "$_PID" 2>/dev/null; then
      echo "session-kill: no tmux session '$NAME', but pid $_PID still alive — ORPHAN, lock left in place" >&2
    else
      record_status
      reap_locks
    fi
  fi
  echo "session-kill: no tmux session '$NAME' (already gone)"
  exit 0
fi

# Are we inside the session we're about to kill?
CURRENT=""
[ -n "${TMUX:-}" ] && CURRENT="$(tmux display-message -p '#S' 2>/dev/null || true)"

if [ "$CURRENT" = "$NAME" ]; then
  echo "session-kill: ending '$NAME' (this session) in ${DELAY}s"
  record_status   # before the deferred kill — the row must land even if this
                  # process dies the instant `tmux kill-session` runs
  # Kill first, then sweep the lock family — after kill-session the process is
  # gone and the sweep is just catching whatever the EXIT trap missed. The rm
  # is inlined (not reap_locks) because the detached bash -c is a fresh shell
  # with no access to this function; keep its extension list in sync with
  # reap_locks / tools/session_name.LOCK_SUFFIXES.
  nohup bash -c "sleep $DELAY; tmux kill-session -t '$NAME'; rm -f '$LOCKS_DIR/$NAME'.lock '$LOCKS_DIR/$NAME'.run '$LOCKS_DIR/$NAME'.tty '$LOCKS_DIR/$NAME'.winid '$LOCKS_DIR/$NAME'.watcher-pid '$LOCKS_DIR/$NAME'.topic" >/dev/null 2>&1 &
  disown 2>/dev/null || true
else
  record_status
  tmux kill-session -t "$NAME"
  reap_locks
  echo "session-kill: ended '$NAME'"
fi
