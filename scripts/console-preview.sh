#!/usr/bin/env bash
# console-preview.sh — P0.5 preview of MoonieX Console on this Mac.
# iPhone (Tailscale) -> ttyd (bound to tailnet IP only) -> tmux -> runners.cto_chat
# Real console (P1) lands on Contabo per wiki projects/mooniex-console.md;
# this is throwaway preview infra, zero prod risk (nothing touches Hostinger).
#
# Usage: console-preview.sh {start|stop|status|url}
set -euo pipefail

AGENTS_DIR="/Users/gob/Projects/Agents"
TMUX_SESSION="cto-main"
TTYD_PORT=7681
PIDFILE="/tmp/mooniex-console-preview.pid"

ts_bin() {
  if command -v tailscale >/dev/null 2>&1; then command -v tailscale
  elif [ -x "/Applications/Tailscale.app/Contents/MacOS/Tailscale" ]; then echo "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
  else echo ""; fi
}
ts_ip() { local b; b="$(ts_bin)"; [ -n "$b" ] || { echo ""; return; }; "$b" ip -4 2>/dev/null | head -1 || true; }

cmd_url() {
  local ip; ip="$(ts_ip)"
  [ -n "$ip" ] || { echo "Tailscale not up. Install Tailscale.app + sign in first." >&2; exit 1; }
  echo "http://${ip}:${TTYD_PORT}"
}

cmd_start() {
  local ip; ip="$(ts_ip)"
  [ -n "$ip" ] || { echo "ERROR: no Tailscale IP. Open Tailscale.app, sign in, toggle ON, retry." >&2; exit 1; }
  command -v ttyd >/dev/null 2>&1 || { echo "ERROR: ttyd not installed (brew install ttyd)" >&2; exit 1; }

  # Preview runs the `claude` CLI (Claude Code) in the Agents repo. NOTE: the
  # org `runners.cto_chat` is single-instance-locked, so a 2nd copy can't run
  # while a CTO session is live — the real Contabo console runs cto_chat fine
  # (own box, own lock). For this Mac preview, `claude` proves the full
  # iPhone->Tailscale->ttyd->tmux->agent path.
  if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    tmux new-session -d -s "$TMUX_SESSION" -c "$AGENTS_DIR" \
      "/Users/gob/.local/bin/claude"
    echo "tmux '$TMUX_SESSION' started (claude CLI)"
  else
    echo "tmux '$TMUX_SESSION' already running — reusing"
  fi

  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "ttyd already running (pid $(cat "$PIDFILE"))"
  else
    nohup caffeinate -i ttyd \
      --port "$TTYD_PORT" --interface "$ip" --writable \
      -t titleFixed="mooniex console — cto" \
      -t 'theme={"background":"#000000","foreground":"#c7c7c7","cursor":"#c7c7c7"}' \
      -t fontFamily="Menlo, Monaco, monospace" -t fontSize=13 \
      tmux attach -t "$TMUX_SESSION" \
      >/tmp/mooniex-console-preview.log 2>&1 &
    echo $! > "$PIDFILE"; sleep 1
    if ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "ERROR: ttyd failed — /tmp/mooniex-console-preview.log:" >&2
      tail -5 /tmp/mooniex-console-preview.log >&2; rm -f "$PIDFILE"; exit 1
    fi
    echo "ttyd up (pid $(cat "$PIDFILE")) — bound to ${ip} only"
  fi
  echo ""; echo "BOOKMARK THIS ON BOTH iPHONES:"; cmd_url
}

cmd_stop() {
  if [ -f "$PIDFILE" ]; then kill "$(cat "$PIDFILE")" 2>/dev/null || true; rm -f "$PIDFILE"; echo "ttyd stopped"
  else pkill -f "ttyd --port ${TTYD_PORT}" 2>/dev/null && echo "ttyd stopped (no pidfile)" || echo "ttyd not running"; fi
  echo "tmux '$TMUX_SESSION' left alive (CTO keeps state). Kill: tmux kill-session -t $TMUX_SESSION"
}

cmd_status() {
  local ip; ip="$(ts_ip)"
  echo "tailscale ip : ${ip:-DOWN}"
  tmux has-session -t "$TMUX_SESSION" 2>/dev/null && echo "tmux         : $TMUX_SESSION running" || echo "tmux         : not running"
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "ttyd         : pid $(cat "$PIDFILE") on $TTYD_PORT"; [ -n "$ip" ] && echo "url          : http://${ip}:${TTYD_PORT}"
  else echo "ttyd         : not running"; fi
}

case "${1:-}" in
  start) cmd_start ;; stop) cmd_stop ;; status) cmd_status ;; url) cmd_url ;;
  *) echo "usage: $0 {start|stop|status|url}" >&2; exit 1 ;;
esac
