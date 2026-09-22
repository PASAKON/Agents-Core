#!/usr/bin/env python3
"""PreToolUse hook: make "never close another operator's tab" mechanically true.

A rule written in a skill informs; it does not enforce. This does. It sits in
front of the Chrome MCP's tab tools and answers two questions the operator
cannot be trusted to answer under load:

  tabs_close_mcp  — is this tab mine?      Deny if a DIFFERENT live task owns it.
  tabs_create_mcp — do I already have one? Deny if this task already holds a tab
                    it never released, which is how twenty-five of them piled up.

Ownership comes from scripts/browser/tab_registry.py, i.e. from disk, not from
anybody's memory. The calling task is derived from the worktree path, which is
the one thing a worker cannot get wrong about itself.

Wire it in ~/.claude/settings.json so every session on this machine gets it, not
just this repo:

  "hooks": {
    "PreToolUse": [
      { "matcher": "mcp__claude-in-chrome__tabs_(close|create)_mcp",
        "hooks": [{ "type": "command",
                    "command": "python3 /Users/gob/MoonieXHQ/Agents/Core/scripts/browser/tab_guard.py" }] }
    ]
  }

Fails OPEN on any internal error: a broken guard must never be able to stop the
render queue. Every decision goes to stderr so the refusal is visible.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MAX_TABS_PER_TASK = 1          # one working tab at a time
TASK_RE = re.compile(r"task-[0-9a-f]{8}")


def caller_task() -> str | None:
    """Which task is running this. The worktree path carries it; env is a fallback."""
    for candidate in (os.environ.get("ORG_TASK_ID"), os.getcwd()):
        if not candidate:
            continue
        m = TASK_RE.search(candidate)
        if m:
            return m.group(0)
    return None


def deny(reason: str) -> None:
    """Block the call and tell the operator what to do instead."""
    print(reason, file=sys.stderr)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0                                   # fail open

    try:
        import tab_registry as reg
    except Exception:
        return 0                                   # fail open

    tool = str(payload.get("tool_name", ""))
    args = payload.get("tool_input") or {}
    me = caller_task()

    if tool.endswith("tabs_close_mcp"):
        ids = args.get("tab_ids") or args.get("tabIds") or args.get("tab_id") or []
        if isinstance(ids, (str, int)):
            ids = [ids]
        claims = reg._claims()
        for tid in ids:
            owner = claims.get(str(tid))
            if not owner or owner == me:
                continue                           # orphan, or mine
            alive, why = reg._task_alive(owner)
            if alive:
                sess = "wd-" + owner.replace("task-", "")
                deny(
                    f"REFUSED: tab {tid} belongs to {owner}, which is still running ({why}). "
                    f"Closing it would destroy another operator's staged composer — that can be "
                    f"half an hour of someone else's work. If you genuinely need Chrome refreshed, "
                    f"warn the owner first and wait for a reply in its own pane:\n"
                    f'  tmux send-keys -t {sess} C-u; tmux send-keys -t {sess} '
                    f'"[CTO] need to refresh Chrome, safe?"; tmux send-keys -t {sess} Enter'
                )
        return 0

    if tool.endswith("tabs_create_mcp"):
        if not me:
            return 0                               # not a worker; leave it alone
        held = reg._load(me).get("tabs", [])
        if len(held) >= MAX_TABS_PER_TASK:
            ids = ", ".join(str(t["tab_id"]) for t in held)
            deny(
                f"REFUSED: {me} already holds {len(held)} tab(s) ({ids}) and the limit is "
                f"{MAX_TABS_PER_TASK}. Twenty-five Higgsfield tabs accumulated this way, and a tab "
                f"that has touched more than one video asset is where the stale @Video binding bug "
                f"comes from. Reuse the tab you have, or finish with it first:\n"
                f"  python3 scripts/browser/tab_registry.py release {me} <tab-id>"
            )
        return 0

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:                        # fail open, loudly
        print(f"tab_guard internal error, allowing: {exc}", file=sys.stderr)
        raise SystemExit(0)
