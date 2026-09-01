#!/usr/bin/env python3
"""PostToolUse hook — log every Skill tool invocation to a TSV file
so we can later audit which skills actually fire vs. dead weight.

Reads JSON event from stdin (Claude Code hook contract):
  {"tool_name": "Skill", "tool_input": {"skill": "...", ...}, ...}

Appends one line to state/skill-usage.log per Skill call:
  <ISO timestamp>\t<skill name>\t<session id>\t<role>

Role comes from the WORKER_ROLE env var (set by runners/worker_init.py for
every worker). Falls back to CXO_ROLE (already set by scripts/cto-claude.sh
and scripts/cxo-claude.sh for every C-level session) rather than exporting a
second, redundant role var from those launchers. "-" when neither is set.

Log destination: the ORG_SKILL_LOG env var, when set, is used verbatim as an
absolute path — this is how the user-level ~/.claude/settings.json hook
registration points every worktree of every repo at one shared log (see
docs/WAVE0-SKILL-TELEMETRY.md). Falls back to state/skill-usage.log next to
this script's own repo root, which is WRONG whenever __file__ resolves inside
a git worktree's copy of this script rather than the main checkout — same doc.

Silent for non-Skill tool calls. Never fails — wrapped in try/except.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _default_log_path() -> Path:
    return Path(__file__).resolve().parent.parent / "state" / "skill-usage.log"


def _log_path() -> Path:
    override = os.environ.get("ORG_SKILL_LOG")
    if override:
        return Path(override)
    return _default_log_path()


def _role() -> str:
    return os.environ.get("WORKER_ROLE") or os.environ.get("CXO_ROLE") or "-"


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
    role = _role()

    try:
        log_path = _log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{ts}\t{skill}\t{session_id}\t{role}\n")
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
