#!/usr/bin/env bash
# Quit Chrome fully, relaunch with --remote-debugging-port, verify port up.
# Port of scripts/higgsfield/launch-chrome-debug.sh for Google Flow.
# Port 9223 (Higgsfield owns 9222) so the two automations can never collide.
# Run: bash scripts/flow/launch-chrome-debug.sh
set -u
PORT=9223
PROFILE="$HOME/.flow-automation/chrome-profile"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Kill ONLY the automation-profile Chrome — never touches the CEO's main Chrome.
echo ">> Stop any existing Flow automation Chrome..."
pkill -f "flow-automation/chrome-profile" 2>/dev/null || true
sleep 1

mkdir -p "$PROFILE"

echo ">> Launch automation Chrome (debug port $PORT, dedicated profile)..."
# Launch binary directly so flags are honored (open -a --args drops them); backgrounded.
nohup "$CHROME" \
  --remote-debugging-port=$PORT \
  --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check \
  --mute-audio \
  > /tmp/flow-chrome.log 2>&1 &
disown

echo ">> Wait for debug port..."
for i in $(seq 1 40); do
  if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo ">> PORT UP (127.0.0.1:$PORT):"
    curl -s "http://127.0.0.1:$PORT/json/version"
    echo
    echo "OK_READY"
    echo ">> Profile: $PROFILE"
    echo ">> FIRST RUN: log into Google in THIS window once, open flow.google.com, then run the dry-run."
    exit 0
  fi
  sleep 0.5
done
echo "ERROR: port $PORT not responding after 20s"
echo "--- chrome log tail ---"
tail -20 /tmp/flow-chrome.log 2>/dev/null
exit 1
