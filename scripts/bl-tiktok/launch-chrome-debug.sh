#!/usr/bin/env bash
# Quit Chrome fully, relaunch with --remote-debugging-port, verify port up.
# Port of scripts/higgsfield/launch-chrome-debug.sh / scripts/flow/launch-chrome-debug.sh
# for the BLACK LIQUIDITY TikTok account.
# Port 9224 (Higgsfield owns 9222, Flow owns 9223) so no automation collides.
# Run: bash scripts/bl-tiktok/launch-chrome-debug.sh
set -u
PORT=9224
PROFILE="$HOME/.bl-tiktok-automation/chrome-profile"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Kill ONLY the automation-profile Chrome — never touches the CEO's main Chrome.
echo ">> Stop any existing BL TikTok automation Chrome..."
pkill -f "bl-tiktok-automation/chrome-profile" 2>/dev/null || true
sleep 1

mkdir -p "$PROFILE"

echo ">> Launch automation Chrome (debug port $PORT, dedicated profile)..."
# Launch binary directly so flags are honored (open -a --args drops them); backgrounded.
nohup "$CHROME" \
  --remote-debugging-port=$PORT \
  --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check \
  --mute-audio \
  > /tmp/bl-tiktok-chrome.log 2>&1 &
disown

echo ">> Wait for debug port..."
for i in $(seq 1 40); do
  if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo ">> PORT UP (127.0.0.1:$PORT):"
    curl -s "http://127.0.0.1:$PORT/json/version"
    echo
    echo "OK_READY"
    echo ">> Profile: $PROFILE"
    echo ">> FIRST RUN: python3 tools/bl_tiktok_login_qr.py to fetch the QR code image,"
    echo ">> then have the CEO scan it with the TikTok app on the black_liquidity account."
    exit 0
  fi
  sleep 0.5
done
echo "ERROR: port $PORT not responding after 20s"
echo "--- chrome log tail ---"
tail -20 /tmp/bl-tiktok-chrome.log 2>/dev/null
exit 1
