#!/usr/bin/env python3
"""Register tab_guard.py as a PreToolUse hook in ~/.claude/settings.json.

A session cannot edit its own hook config, so this is the CEO-run path. It is
deliberately conservative about somebody else's settings file:

  - backs up to settings.json.bak-<timestamp> before touching anything
  - MERGES into hooks.PreToolUse, never replaces the array
  - idempotent: running it twice changes nothing the second time
  - validates the JSON round-trips before writing, so a crash cannot leave a
    half-written settings file behind

Run it, then start one new session for the hook to take effect:

    python3 /Users/gob/Projects/Agents/scripts/browser/install_tab_guard_hook.py
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

SETTINGS = Path.home() / ".claude" / "settings.json"
GUARD = Path(__file__).resolve().parent / "tab_guard.py"
MATCHER = "mcp__claude-in-chrome__tabs_(close|create)_mcp"
ENTRY = {
    "matcher": MATCHER,
    "hooks": [{"type": "command", "command": f"python3 {GUARD}"}],
}


def main() -> int:
    if not GUARD.exists():
        print(f"guard script missing: {GUARD}")
        return 1
    if not SETTINGS.exists():
        print(f"no settings file at {SETTINGS}")
        return 1

    data = json.loads(SETTINGS.read_text())
    pre = data.setdefault("hooks", {}).setdefault("PreToolUse", [])

    if any("tab_guard.py" in json.dumps(e) for e in pre):
        print("already registered — nothing to do")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = SETTINGS.with_suffix(f".json.bak-{stamp}")
    shutil.copy2(SETTINGS, backup)

    pre.append(ENTRY)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    json.loads(text)                      # prove it parses before it lands
    SETTINGS.write_text(text)

    print(f"backup   {backup}")
    print(f"added    PreToolUse matcher {MATCHER}")
    print(f"command  python3 {GUARD}")
    print(f"total PreToolUse entries now {len(pre)}")
    print("\nStart ONE new session for it to take effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
