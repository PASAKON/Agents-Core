#!/bin/bash
cd /tmp/claude-0/-opt-MoonieXHQ-Agents-Core/381826cd-bc49-487d-a946-08e0d1a121af/scratchpad/harness
for r in argon sonnet; do python3 test.py --job D3 --runner $r > /opt/MoonieXHQ/Agents/Core/state/argon-trial-2026-10/runs/D3/$r.checks.txt 2>&1; echo "D3 $r checks: $(python3 -c "import json;d=json.load(open('/opt/MoonieXHQ/Agents/Core/state/argon-trial-2026-10/runs/D3/'+'$r'+'.checks.json'));print([c['exit'] for c in d['checks']], d['checks'][0]['tail'][-300:].replace(chr(10),' / ') if d['checks'] else d.get('apply_error'))")"; done
until [ "$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)" -ge 1024 ]; do sleep 30; done
python3 judge.py --job D3 2>&1 | tail -1
