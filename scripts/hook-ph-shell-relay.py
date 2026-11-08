#!/usr/bin/env python3
"""Stop hook: a PH shell may answer only after relaying the current user turn."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys

TAIL_BYTES = 2 * 1024 * 1024
RELAY = re.compile(r"(?:^|[\s/])(?:tools/)?ph_brain\.py\s+(?:turn|delegate)\b|(?:^|[\s/])(?:tools/)?ask_run\.py\s+ask\b")
# Read-only lookups the shell may answer from itself (CEO 2026-11-08: facts yes,
# judgement no). The reply must quote what the command printed.
READONLY = re.compile(r"(?:^|[\s/])(?:tools/)?ph_brain\.py\s+status\b"
                      r"|(?:^|[\s/])scripts/live-sessions\.sh\b"
                      r"|^\s*(?:cat|head|tail|sed -n|grep)\b[^|;&]*docs/plans/[\w.-]+-STATUS\.md\s*$")
REASON = ('PH shell: relay this to your brain: bash scripts/hub/org-python.sh '
          'tools/ph_brain.py turn --ph "$CXO_SESSION_ID" --project "$ORG_PH_PROJECT" '
          '--lane "$ORG_PH_LANE" --message "<the prompt>"')


def _real_user(record):
    if record.get('type') != 'user':
        return False
    content = record.get('message', {}).get('content')
    if isinstance(content, str):
        return bool(content.strip())
    return isinstance(content, list) and any(
        isinstance(part, dict) and part.get('type') == 'text' and part.get('text', '').strip()
        for part in content)


def _tail(path):
    with open(path, 'rb') as stream:
        size = stream.seek(0, os.SEEK_END)
        stream.seek(max(0, size - TAIL_BYTES))
        data = stream.read(TAIL_BYTES)
    if size > TAIL_BYTES:
        data = data.partition(b'\n')[2]
    return data.decode('utf-8').splitlines()


def decide(payload, env=os.environ):
    if env.get('ORG_PH_SHELL') != '1' or payload.get('stop_hook_active'):
        return None
    path = payload.get('transcript_path')
    if not path:
        return None
    records = [json.loads(line) for line in _tail(Path(path)) if line.strip()]
    last_user = next((i for i in range(len(records) - 1, -1, -1)
                      if _real_user(records[i])), None)
    if last_user is None:
        return None
    for record in records[last_user + 1:]:
        if record.get('type') != 'assistant':
            continue
        for part in record.get('message', {}).get('content', []):
            if (isinstance(part, dict) and part.get('type') == 'tool_use'
                    and part.get('name') == 'Bash'
                    and (RELAY.search(cmd := str(part.get('input', {}).get('command', '')))
                         or READONLY.search(cmd))):
                return None
    return {'decision': 'block', 'reason': REASON}


def main():
    try:
        result = decide(json.load(sys.stdin))
        if result:
            print(json.dumps(result))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeError):
        pass  # A malformed or truncated transcript must never trap the session.
    return 0


if __name__ == '__main__':
    sys.exit(main())
