#!/usr/bin/env bash
# Run SomPong entirely on the Mac — failover for when Contabo is unreachable.
#
# The normal home for SomPong is the Contabo box: Telegram webhook -> claudeflow
# Express route -> secretary_server -> relay queue -> mac_agent. On 2026-08-16
# that box was off for 2h24m (a host-level cut: the journal stops mid-line with
# no shutdown sequence, and it came back on a newer kernel), which took SomPong
# and terminal.mooniex.com down together — both are that one host.
#
# This script stands the whole thing up here instead, using Telegram long
# polling so the Mac needs no inbound address. Cost of switching: a webhook and
# getUpdates are mutually exclusive, so this DELETES the webhook. Put it back
# with scripts/sompong-restore-webhook.sh when Contabo is healthy again.
#
# Usage:  bash scripts/sompong-mac.sh          # start (idempotent)
#         bash scripts/sompong-mac.sh stop     # stop both processes
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
KEY_FILE="$ROOT/state/secretary-api-key"
SERVER_LOG="$ROOT/state/secretary-server.out"
POLL_LOG="$ROOT/state/secretary-telegram.out"

if [[ "${1:-start}" == "stop" ]]; then
  pkill -f "runners.secretary_telegram_poll" 2>/dev/null || true
  pkill -f "runners.secretary_server" 2>/dev/null || true
  echo "stopped"
  exit 0
fi

# The API key only ever guards 127.0.0.1:8643, but secretary_server refuses to
# start without one. Generate once and keep it, so a restart does not orphan a
# poller still holding the old value.
if [[ ! -f "$KEY_FILE" ]]; then
  mkdir -p "$(dirname "$KEY_FILE")"
  "$PY" -c "import secrets; print(secrets.token_hex(24))" > "$KEY_FILE"
  chmod 600 "$KEY_FILE"
fi
export SECRETARY_API_KEY="$(cat "$KEY_FILE")"
export SECRETARY_CLAUDE_BIN="${SECRETARY_CLAUDE_BIN:-$(command -v claude)}"

if lsof -nP -iTCP:8643 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "secretary_server: already listening on 8643"
else
  nohup "$PY" -m runners.secretary_server >> "$SERVER_LOG" 2>&1 &
  echo "secretary_server: started (pid $!)"
  sleep 5
  lsof -nP -iTCP:8643 -sTCP:LISTEN >/dev/null 2>&1 \
    || { echo "FAILED to bind 8643 — see $SERVER_LOG"; tail -5 "$SERVER_LOG"; exit 1; }
fi

if pgrep -f "runners.secretary_telegram_poll" >/dev/null 2>&1; then
  echo "telegram poller: already running"
else
  nohup "$PY" -m runners.secretary_telegram_poll >> "$POLL_LOG" 2>&1 &
  echo "telegram poller: started (pid $!)"
  sleep 4
fi

echo
tail -3 "$POLL_LOG"
echo
echo "logs: $SERVER_LOG"
echo "      $POLL_LOG"
