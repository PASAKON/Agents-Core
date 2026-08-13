#!/usr/bin/env bash
# Spawn the mooniex-claudesign Web Designer surface.
#
# Headless by default: starts open-design daemon (port 7456) + web UI
# (Next.js, port 3000) as background processes, waits for the web port
# to accept connections, then opens the browser to http://localhost:3000.
#
# CEO uses this for private design work and CEO-supervised issue fixes.
# CTO `delegate_task` for `mooniex-claudesign` still works separately —
# that path spawns a Web Designer *agent* in tmux+ttyd; this script
# only boots the open-design app surface.
#
# Usage:
#   bash scripts/spawn-web-designer.sh             # start + open browser
#   bash scripts/spawn-web-designer.sh --with-iterm  # also open iTerm tabs (debug)
#   bash scripts/spawn-web-designer.sh --status    # show running state
#   bash scripts/spawn-web-designer.sh --stop      # kill daemon + web
#   bash scripts/spawn-web-designer.sh --restart   # stop then start
#   bash scripts/spawn-web-designer.sh --no-open   # start but don't open browser
set -euo pipefail

PROJECT_DIR="/Users/gob/Projects/mooniex-claudesign"
STATE_DIR="/Users/gob/Projects/Agents/state/web-designer"
LOG_DAEMON="$STATE_DIR/daemon.log"
LOG_WEB="$STATE_DIR/web.log"
PID_DAEMON="$STATE_DIR/daemon.pid"
PID_WEB="$STATE_DIR/web.pid"
DAEMON_PORT="${OD_PORT:-7456}"
WEB_PORT="${OD_WEB_PORT:-3000}"
WEB_URL="http://localhost:${WEB_PORT}"

MODE="start"
WITH_ITERM=0
OPEN_BROWSER=1
for a in "$@"; do
  case "$a" in
    --with-iterm) WITH_ITERM=1 ;;
    --status)     MODE="status" ;;
    --stop)       MODE="stop" ;;
    --restart)    MODE="restart" ;;
    --no-open)    OPEN_BROWSER=0 ;;
    -h|--help)
      sed -n '2,20p' "$0"; exit 0 ;;
    *)
      echo "unknown flag: $a" >&2; exit 2 ;;
  esac
done

mkdir -p "$STATE_DIR"

is_alive() {
  local pidfile="$1"
  [ -f "$pidfile" ] || return 1
  local pid
  pid=$(cat "$pidfile" 2>/dev/null || true)
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null
}

port_open() {
  local port="$1"
  nc -z 127.0.0.1 "$port" >/dev/null 2>&1
}

stop_proc() {
  local pidfile="$1" label="$2"
  if is_alive "$pidfile"; then
    local pid
    pid=$(cat "$pidfile")
    echo "stopping $label (pid $pid)"
    kill "$pid" 2>/dev/null || true
    sleep 1
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$pidfile"
}

show_status() {
  local d_state w_state
  if is_alive "$PID_DAEMON"; then d_state="alive (pid $(cat "$PID_DAEMON"))"; else d_state="down"; fi
  if is_alive "$PID_WEB";    then w_state="alive (pid $(cat "$PID_WEB"))";    else w_state="down"; fi
  echo "daemon : $d_state  port $DAEMON_PORT $(port_open "$DAEMON_PORT" && echo OPEN || echo closed)"
  echo "web    : $w_state  port $WEB_PORT $(port_open "$WEB_PORT" && echo OPEN || echo closed)"
  echo "url    : $WEB_URL"
  echo "logs   : $LOG_DAEMON"
  echo "         $LOG_WEB"
}

start_daemon() {
  if is_alive "$PID_DAEMON" || port_open "$DAEMON_PORT"; then
    echo "daemon already running on port $DAEMON_PORT"
    return 0
  fi
  echo "starting daemon → $LOG_DAEMON"
  (
    cd "$PROJECT_DIR"
    OD_PORT="$DAEMON_PORT" OD_WEB_PORT="$WEB_PORT" nohup pnpm --filter @open-design/daemon dev \
      >>"$LOG_DAEMON" 2>&1 &
    echo $! > "$PID_DAEMON"
  )
}

start_web() {
  if is_alive "$PID_WEB" || port_open "$WEB_PORT"; then
    echo "web already running on port $WEB_PORT"
    return 0
  fi
  echo "starting web   → $LOG_WEB"
  (
    cd "$PROJECT_DIR"
    OD_PORT="$DAEMON_PORT" PORT="$WEB_PORT" nohup pnpm --filter @open-design/web dev \
      >>"$LOG_WEB" 2>&1 &
    echo $! > "$PID_WEB"
  )
}

wait_for_web() {
  local tries=60
  echo -n "waiting for $WEB_URL "
  while [ $tries -gt 0 ]; do
    if port_open "$WEB_PORT"; then echo " ready"; return 0; fi
    echo -n "."
    sleep 1
    tries=$((tries - 1))
  done
  echo
  echo "web did not open port $WEB_PORT within 60s — tail $LOG_WEB" >&2
  return 1
}

spawn_iterm_tabs() {
  local daemon_cmd web_cmd
  daemon_cmd="cd '$PROJECT_DIR' && tail -F '$LOG_DAEMON'"
  web_cmd="cd '$PROJECT_DIR' && tail -F '$LOG_WEB'"
  osascript <<APPLESCRIPT
tell application "iTerm"
  set newWindow to (create window with default profile)
  tell newWindow
    tell current session of current tab
      set name to "claudesign daemon"
      write text "$daemon_cmd"
    end tell
    set webTab to (create tab with default profile)
    tell current session of webTab
      set name to "claudesign web"
      write text "$web_cmd"
    end tell
    select first tab
  end tell
end tell
APPLESCRIPT
}

case "$MODE" in
  status)
    show_status
    ;;
  stop)
    stop_proc "$PID_WEB"    "web"
    stop_proc "$PID_DAEMON" "daemon"
    echo "stopped."
    ;;
  restart)
    stop_proc "$PID_WEB"    "web"
    stop_proc "$PID_DAEMON" "daemon"
    sleep 1
    start_daemon
    start_web
    wait_for_web || true
    [ "$OPEN_BROWSER" = "1" ] && open "$WEB_URL"
    [ "$WITH_ITERM" = "1" ] && spawn_iterm_tabs
    show_status
    ;;
  start)
    if [ ! -d "$PROJECT_DIR" ]; then
      echo "project dir not found: $PROJECT_DIR" >&2; exit 1
    fi
    if ! command -v pnpm >/dev/null 2>&1; then
      echo "pnpm not found on PATH — install pnpm first" >&2; exit 1
    fi
    start_daemon
    start_web
    wait_for_web || true
    [ "$OPEN_BROWSER" = "1" ] && open "$WEB_URL"
    [ "$WITH_ITERM" = "1" ] && spawn_iterm_tabs
    show_status
    ;;
esac
