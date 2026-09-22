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

WAKER_LOG="$ROOT/state/secretary-waker.out"
ENV_FILE="${CLAUDEFLOW_ENV:-/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env}"

if [[ "${1:-start}" == "stop" ]]; then
  pkill -f "runners.secretary_telegram_poll" 2>/dev/null || true
  pkill -f "runners.secretary_waker" 2>/dev/null || true
  pkill -f "runners.secretary_server" 2>/dev/null || true
  echo "stopped"
  exit 0
fi

# The waker carries replies the other way: report_to_ceo writes a letter into
# state/inbox/secretary-sompong/, the waker has SomPong read it, think, and
# message the CEO. Without it the inbound half works and every answer sits on
# disk — which is exactly what happened to four orders on 2026-08-16.
#
# lib/telegram_out reads TELEGRAM_BOT_TOKEN, and claudeflow's .env points that
# name at @MoonieXBot: nine bots share that file. Sending SomPong's replies
# with it returns ok:true and delivers them into a different bot's chat, so map
# the names explicitly here rather than inheriting.
_env_from_file() { grep -hE "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"' \r'; }
export TELEGRAM_BOT_TOKEN="${SECRETARY_BOT_TOKEN:-$(_env_from_file SECRETARY_BOT_TOKEN)}"
export TELEGRAM_CEO_CHAT_ID="${TELEGRAM_CEO_CHAT_ID:-$(_env_from_file SECRETARY_ADMIN_CHAT_ID)}"
[[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CEO_CHAT_ID" ]] \
  || { echo "SECRETARY_BOT_TOKEN / SECRETARY_ADMIN_CHAT_ID missing from $ENV_FILE"; exit 1; }

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

if pgrep -f "runners.secretary_waker" >/dev/null 2>&1; then
  echo "reply waker:    already running"
else
  nohup "$PY" -m runners.secretary_waker >> "$WAKER_LOG" 2>&1 &
  echo "reply waker:    started (pid $!)"
  sleep 3
fi

echo
tail -3 "$POLL_LOG"
echo
echo "logs: $SERVER_LOG"
echo "      $POLL_LOG"
