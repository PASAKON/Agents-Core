#!/usr/bin/env bash
# scripts/idle-ping-watcher.sh — Background idle-ping daemon for CXO ephemeral tabs.
# Spawned by cxo-claude.sh immediately after tab is up; one process per <role>-<sid>.
#
# Usage: bash scripts/idle-ping-watcher.sh --role <role> --session <sid>
#
# Lifecycle:
#   1. Poll tab contents every 60s.
#   2. After 5 min of no activity → send ping.
#   3. Wait up to 5 more min for reply:
#      - New activity + "เสร็จแล้ว"/"done" in last 200 chars → close immediately.
#      - New activity (any other text) → cancel close, reset idle timer.
#      - No activity within 5 min → close.
#   4. Exit cleanly when lock file disappears or SIGTERM received.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKS="$ROOT/state/locks"

ROLE=""
SID=""

prev=""
for a in "$@"; do
  case "$prev" in
    --role)    ROLE="$a"; prev="" ;;
    --session) SID="$a";  prev="" ;;
    *)
      case "$a" in
        --role|--session) prev="$a" ;;
      esac ;;
  esac
done

if [ -z "$ROLE" ] || [ -z "$SID" ]; then
  echo "usage: idle-ping-watcher.sh --role <role> --session <sid>" >&2
  exit 1
fi

WINID_FILE="$LOCKS/$ROLE-$SID.winid"
PID_FILE="$LOCKS/$ROLE-$SID.watcher-pid"

echo "$$" > "$PID_FILE"

# Re-export so gate 3 of close_session passes when we invoke itermtab_close
export CXO_ROLE="$ROLE"
export CXO_SESSION_ID="$SID"

cleanup() { rm -f "$PID_FILE"; }
trap cleanup EXIT INT TERM

IDLE_SECS=300   # 5 min idle before ping
PING_SECS=300   # 5 min wait after ping before auto-close
POLL=60         # poll interval

_get_winid() {
  [ -f "$WINID_FILE" ] || return 1
  tr -d '[:space:]' < "$WINID_FILE"
}

_get_len() {
  local wid
  wid="$(_get_winid)" || { echo -1; return; }
  osascript 2>/dev/null <<EOASLEN || echo -1
tell application "iTerm2"
  repeat with w in windows
    if id of w is $wid then
      return length of (contents of current session of current tab of w)
    end if
  end repeat
  return -1
end tell
EOASLEN
}

_get_tail() {
  local wid
  wid="$(_get_winid)" || { echo ""; return; }
  osascript 2>/dev/null <<EOASTAIL || echo ""
tell application "iTerm2"
  repeat with w in windows
    if id of w is $wid then
      set c to contents of current session of current tab of w
      set L to length of c
      if L > 200 then
        return text (L - 199) thru L of c
      else
        return c
      end if
    end if
  end repeat
  return ""
end tell
EOASTAIL
}

_send_ping() {
  local wid sender
  wid="$(_get_winid)" || return 1
  sender="${CXO_ROLE:-system}"
  osascript 2>/dev/null <<EOASPING || return 1
tell application "iTerm2"
  repeat with w in windows
    if id of w is $wid then
      tell current session of current tab of w
        write text "[from $sender]: ยังทำงานต่ออยู่ไหม? ไม่ตอบใน 5 นาที = close session." newline NO
        write text (ASCII character 13) newline NO
      end tell
      return
    end if
  end repeat
end tell
EOASPING
}

_do_close() {
  cd "$ROOT"
  source .venv/bin/activate 2>/dev/null || true
  python3 -m tools.itermtab_close --role "$ROLE" --session "$SID" 2>/dev/null || true
}

_contains_done() {
  # Return 0 (success) if text contains เสร็จแล้ว or done (case-insensitive)
  printf '%s' "$1" | python3 -c '
import sys
c = sys.stdin.read().lower()
exit(0 if "เสร็จแล้ว" in c or "done" in c else 1)
' 2>/dev/null
}

baseline="$(_get_len)"
idle_ts=$SECONDS

while true; do
  sleep $POLL

  # Lock gone — someone else closed the tab
  if [ ! -f "$WINID_FILE" ]; then exit 0; fi

  cur="$(_get_len)"
  if [ "$cur" = "-1" ]; then exit 0; fi  # window gone

  if [ "$cur" != "$baseline" ]; then
    # Activity: reset idle timer
    baseline="$cur"
    idle_ts=$SECONDS
    continue
  fi

  elapsed=$((SECONDS - idle_ts))
  [ $elapsed -ge $IDLE_SECS ] || continue

  # ---- Idle threshold reached: send ping ----
  _send_ping || true
  sleep 2  # let ping text appear before snapshotting
  ping_baseline="$(_get_len)"
  ping_ts=$SECONDS

  # ---- Ping-wait loop ----
  while true; do
    sleep $POLL

    if [ ! -f "$WINID_FILE" ]; then exit 0; fi

    post="$(_get_len)"
    if [ "$post" = "-1" ]; then exit 0; fi

    if [ "$post" != "$ping_baseline" ]; then
      tail="$(_get_tail)"
      if _contains_done "$tail"; then
        _do_close
        exit 0
      fi
      # Activity but not done — cancel close, resume main loop
      baseline="$post"
      idle_ts=$SECONDS
      break
    fi

    ping_elapsed=$((SECONDS - ping_ts))
    if [ $ping_elapsed -ge $PING_SECS ]; then
      _do_close
      exit 0
    fi
  done
done
