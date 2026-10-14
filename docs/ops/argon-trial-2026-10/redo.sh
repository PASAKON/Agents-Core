#!/bin/bash
# Redo rounds after the main queue: wait for queue1 to finish, then run each "<job> <tag> <from-run>" one at a
# time with that job's feedback file, then the CTO checks on the new output.
cd "$(dirname "$0")"
R=/opt/MoonieXHQ/Agents/Core/state/argon-trial-2026-10
until grep -q "queue done" ../queue1.log; do sleep 30; done
while read -r job tag from; do
  [ -z "$job" ] && continue
  until [ "$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)" -ge 1024 ]; do sleep 30; done
  echo "$(date -u +%T) start $job argon-$tag (from $from)"
  python3 run.py --job "$job" --runner argon --tag "$tag" --from-run "$from" --extra "$R/runs/$job/$tag-feedback.md" 2>&1 | tail -2
  python3 test.py --job "$job" --runner "argon-$tag" > "$R/runs/$job/argon-$tag.checks.txt" 2>&1
  echo "$(date -u +%T) checked $job argon-$tag: $(python3 -c "import json;d=json.load(open('$R/runs/$job/argon-$tag.checks.json'));print('applied' if d['applied'] else 'NOT APPLIED', [c['exit'] for c in d['checks']])")"
done < "$1"
echo "$(date -u +%T) redo done"
