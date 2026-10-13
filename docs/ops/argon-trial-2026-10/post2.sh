#!/bin/bash
# Argon-only jobs (CEO 14 Oct ~03:40): wait for the Argon run, run the CTO checks on it, then the reviewer
# (the CTO) gives pass/redo by hand. No Sonnet run, no blind judge.
cd "$(dirname "$0")"
R=/opt/MoonieXHQ/Agents/Core/state/argon-trial-2026-10
for job in "$@"; do
  until [ -f $R/runs/$job/argon.json ]; do sleep 20; done
  [ -f $R/runs/$job/argon.checks.json ] || python3 test.py --job $job --runner argon > $R/runs/$job/argon.checks.txt 2>&1
  echo "$(date -u +%T) checked $job argon: $(python3 -c "import json;d=json.load(open('$R/runs/$job/argon.checks.json'));print('applied' if d['applied'] else 'NOT APPLIED', [c['exit'] for c in d['checks']])")"
done
echo "$(date -u +%T) post2 done"
