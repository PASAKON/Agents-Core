#!/usr/bin/env bash
# Tail all *_latest.log dev logs. Restarts tail when new log files appear.
set -uo pipefail

cd "$(dirname "$0")/.."
LOGS="state/logs"

mkdir -p "$LOGS"

echo "watching $LOGS/*_latest.log ..."
echo "(re-execs when new dev sessions create new symlinks)"
echo

while :; do
  shopt -s nullglob
  files=( "$LOGS"/*_latest.log )
  shopt -u nullglob

  if (( ${#files[@]} > 0 )); then
    tail -F "${files[@]}" &
    TAIL_PID=$!

    BEFORE=$(ls -1 "$LOGS"/*_latest.log 2>/dev/null | sort | tr '\n' ' ')
    while :; do
      sleep 3
      AFTER=$(ls -1 "$LOGS"/*_latest.log 2>/dev/null | sort | tr '\n' ' ')
      if [[ "$BEFORE" != "$AFTER" ]]; then
        echo
        echo "[tail-dev-logs] log set changed — restarting tail"
        kill "$TAIL_PID" 2>/dev/null || true
        wait "$TAIL_PID" 2>/dev/null || true
        break
      fi
    done
  else
    sleep 2
  fi
done
