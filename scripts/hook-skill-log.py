#!/usr/bin/env python3
"""PostToolUse hook — log every Skill tool invocation to a TSV file
so we can later audit which skills actually fire vs. dead weight.

Reads JSON event from stdin (Claude Code hook contract):
  {"tool_name": "Skill", "tool_input": {"skill": "...", ...}, ...}

Appends one line to state/skill-usage.log per Skill call:
  <ISO timestamp>\t<skill name>\t<session id>

Silent for non-Skill tool calls. Never fails — wrapped in try/except.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "state" / "skill-usage.log"


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = event.get("tool_name") or event.get("tool") or ""
    if tool_name != "Skill":
        return 0

    tool_input = event.get("tool_input") or event.get("input") or {}
    skill = (
        tool_input.get("skill")
        or tool_input.get("name")
        or "<unknown>"
    )
    session_id = event.get("session_id") or "-"

    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{ts}\t{skill}\t{session_id}\n")
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
