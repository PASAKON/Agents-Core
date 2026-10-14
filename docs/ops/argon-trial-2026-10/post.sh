#!/bin/bash
# For each job: wait for both runs, run the CTO checks on both, then the blind judge.
cd "$(dirname "$0")"
R=/opt/MoonieXHQ/Agents/Core/state/argon-trial-2026-10
for job in "$@"; do
  until [ -f $R/runs/$job/argon.json ] && [ -f $R/runs/$job/sonnet.json ]; do sleep 20; done
  for r in argon sonnet; do
    [ -f $R/runs/$job/$r.checks.json ] || python3 test.py --job $job --runner $r > $R/runs/$job/$r.checks.txt 2>&1
  done
  until [ "$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)" -ge 1024 ]; do sleep 30; done
  [ -f $R/judge/$job.json ] || python3 judge.py --job $job 2>&1 | tail -1
done
echo "$(date -u +%T) post done"
