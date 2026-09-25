#!/usr/bin/env bash
# Wait, detached, for the CEO's Infisical login in the Browser Home, then run after_login.sh.
#   setsid nohup bash scripts/infisical/watch_login.sh [cdp-url] [max-hours] >/dev/null 2>&1 &
# Polls wait_login.mjs --once every 20 s (URL host+path and the org UI's words; reads no values).
# A stopped Chrome home just means "not yet": the CEO's phone can relaunch it any time.
set -u
ROOT=/opt/MoonieXHQ/Agents/Core
NODE=/opt/node-v22/bin/node
CDP=${1:-http://127.0.0.1:9281}
MAX_H=${2:-12}
LOG=$ROOT/state/logs/infisical-p1.log
mkdir -p "$(dirname "$LOG")"
deadline=$(( $(date +%s) + MAX_H * 3600 ))
CONSOLE=/opt/MoonieXHQ/Projects/MoonieX/Console
HOME_ID=${HOME_ID:-infisical}
down=0
echo "$(date -u +%FT%TZ) watch: start, up to ${MAX_H}h, pid $$" >>"$LOG"
while [ "$(date +%s)" -lt "$deadline" ]; do
  if "$NODE" "$ROOT/scripts/infisical/wait_login.mjs" "$CDP" 15 1 --once >>"$LOG" 2>&1; then
    echo "$(date -u +%FT%TZ) watch: login detected" >>"$LOG"
    sleep 5   # let the relay finish its own success handling first
    exec bash "$ROOT/scripts/infisical/after_login.sh" "$CDP"
  fi
  # The Browser Home died twice on 2026-09-25/26 (a Console restart kills every home in its
  # cgroup; one death is unexplained). Two minutes down -> relaunch it in its own systemd scope,
  # outside the Console, with one tab on the start URL. The CEO's phone can also tap เปิด.
  if curl -s -m 3 -o /dev/null "$CDP/json/version"; then
    down=0
  else
    down=$((down + 1))
    if [ "$down" -ge 6 ]; then
      echo "$(date -u +%FT%TZ) watch: home down 2 min, relaunching $HOME_ID in a scope" >>"$LOG"
      (cd "$CONSOLE" && systemd-run --quiet --scope --unit="relay-home-$HOME_ID-$(date +%H%M%S)" node scripts/relay-home.mjs launch "$HOME_ID" >>"$LOG" 2>&1)
      down=0
    fi
  fi
  sleep 20
done
echo "$(date -u +%FT%TZ) watch: gave up after ${MAX_H}h" >>"$LOG"
