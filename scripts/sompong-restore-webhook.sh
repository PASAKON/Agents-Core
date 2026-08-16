#!/usr/bin/env bash
# Hand SomPong back to the Contabo webhook after a Mac failover.
#
# Undoes scripts/sompong-mac.sh. A webhook and getUpdates cannot both be
# active, so this stops the Mac poller FIRST and only then re-registers the
# webhook — the other order leaves a poller quietly stealing updates that
# Telegram believes it has delivered to the webhook.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${CLAUDEFLOW_ENV:-/Users/gob/Projects/mooniex-claudeflow/.env}"
WEBHOOK_URL="${SOMPONG_WEBHOOK_URL:-https://webhook.mooniex.com/telegram/@sompong}"

TOKEN="$(grep -hE '^SECRETARY_BOT_TOKEN=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"'"'"' \r')"
[[ -n "$TOKEN" ]] || { echo "SECRETARY_BOT_TOKEN not found in $ENV_FILE"; exit 1; }

echo "1/3 stopping the Mac poller"
pkill -f "runners.secretary_telegram_poll" 2>/dev/null || true
sleep 2

echo "2/3 checking the webhook host is up before handing over"
code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${WEBHOOK_URL%/telegram/*}/" || true)"
if [[ "$code" == "000" ]]; then
  echo "   host is not answering (curl got 000) — refusing to hand over."
  echo "   Restart the Mac path with: bash scripts/sompong-mac.sh"
  exit 1
fi
echo "   host answered HTTP $code"

echo "3/3 setting the webhook"
curl -s --max-time 20 "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"${WEBHOOK_URL}\"}" \
  | python3 -c 'import sys,json; r=json.load(sys.stdin); print("  ok:", r.get("ok"), r.get("description",""))'

curl -s --max-time 20 "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" \
  | python3 -c 'import sys,json; r=json.load(sys.stdin)["result"]; print("  url:", r.get("url")); print("  pending:", r.get("pending_update_count"))'
