#!/usr/bin/env bash
# Start 9Router bound to localhost ONLY, and refuse to start it any other way.
#
# Why this script exists: `9router` with no flags binds 0.0.0.0 and prints its
# own warning — "Network-exposed: reachable at http://192.168.1.149:20128".
# That is every device on the house WiFi able to send prompts through the CEO's
# configured providers, on his quota, with no authentication. The warning is
# easy to read past at the end of an install, so the safe form lives here
# instead of in someone's memory.
#
#   bash scripts/ninerouter-up.sh          # foreground, logs visible
#   bash scripts/ninerouter-up.sh --tray   # background, system tray
set -euo pipefail
PORT=20128
HOST=127.0.0.1

if ! command -v 9router >/dev/null 2>&1; then
  echo "9router is not installed. The CEO installs it by hand:" >&2
  echo "    npm install -g 9router" >&2
  exit 1
fi

if curl -s --max-time 2 "http://$HOST:$PORT/" >/dev/null 2>&1; then
  echo ">> already running on $HOST:$PORT"
  exit 0
fi

echo ">> starting 9Router on $HOST:$PORT (local-only, never 0.0.0.0)"
exec 9router --host "$HOST" --port "$PORT" --no-browser ${1:+"$1"}
