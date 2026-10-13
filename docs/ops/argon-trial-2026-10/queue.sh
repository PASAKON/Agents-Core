#!/bin/bash
# One run at a time; waits for >=1 GB available before each.
cd "$(dirname "$0")"
for job in "$@"; do
  for r in argon sonnet; do
    [ -f /opt/MoonieXHQ/Agents/Core/state/argon-trial-2026-10/runs/$job/$r.json ] && continue
    for i in $(seq 1 30); do
      a=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); [ "$a" -ge 1024 ] && break; sleep 60
    done
    echo "$(date -u +%T) start $job $r"
    python3 run.py --job "$job" --runner "$r" 2>&1 | tail -2
  done
done
echo "$(date -u +%T) queue done"
