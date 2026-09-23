#!/usr/bin/env python3
"""PreToolUse hook — stop a C-level session from running a browser loop.

IRON-RULES §42: browser work belongs to the `browser_operator` role, not to a
C-level tab. The rule is prose, and prose does not stop a `/loop` at 3am. This
is the part that actually stops it.

What it does NOT do: block the first browser call. A C-level legitimately opens
a page to verify a DEV's work, and blocking that would make the rule hated and
disabled. The harm is *accumulation* — screenshots never leave a context and
are re-sent on every later turn — so the guard counts, stays silent while the
count is small, and blocks once the session has clearly stopped verifying and
started working.

Discriminator: a DEV process carries WORKER_ROLE in its environment (set by
runners/worker_init.py before exec). Anything without it is a C-level or a plain
session, and is subject to the caps.

Reads the Claude Code hook event from stdin:
  {"session_id": "...", "tool_name": "mcp__claude-in-chrome__computer",
   "tool_input": {"action": "screenshot", ...}, ...}

Exit 0 = allow (silent). Exit 2 = block, stderr goes back to the model.

Escape hatch for a genuine long C-level browser task: BROWSER_GUARD=off.
Counters live in state/browser-guard/<session>.json and reset per session; to
clear one by hand, delete that file.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

STATE_DIR_ENV = os.environ.get("BROWSER_GUARD_STATE_DIR")
if STATE_DIR_ENV:
    STATE_DIR = Path(STATE_DIR_ENV)
else:
    STATE_DIR = Path(__file__).resolve().parent.parent / "state" / "browser-guard"

# Chosen from the first real browser_operator run (2026-08-10): verifying a
# DEV's work took the CTO 3 chrome calls and 1 screenshot. A DEV doing the
# actual job took 29 calls and 8 screenshots. The caps sit between the two.
MAX_CALLS = 12
MAX_SCREENSHOTS = 5

DEV_MAX_CALLS = 60
DEV_MAX_SCREENSHOTS = 15

_SCREENSHOT_ACTIONS = {"screenshot", "zoom"}


def _message(kind: str, calls: int, shots: int) -> str:
    return (
        f"BLOCKED by IRON-RULES §42 — this session has made {calls} browser "
        f"calls ({shots} of them screenshots), which is past the {kind} cap for "
        "a C-level session.\n\n"
        "That volume is not verification any more, it is the work itself, and "
        "browser work belongs to the `browser_operator` role. Screenshots never "
        "leave a context: every one you have taken is re-sent on every "
        "remaining turn of this session, so continuing here costs more with "
        "each step.\n\n"
        "Do this instead: create a task with `role: browser_operator`, put the "
        "remaining browser steps in its description, and delegate. If the work "
        "repeats, require a replay script so run two onward needs no model.\n\n"
        "If you genuinely must continue in this tab (the task is nearly done, "
        "or delegating costs more than finishing), re-run with BROWSER_GUARD=off "
        "in the environment, and say in your next message to the CEO that you "
        "overrode the guard and why."
    )


def main() -> int:
    if os.environ.get("BROWSER_GUARD", "").lower() in {"off", "0", "false"}:
        return 0

    is_dev = bool(os.environ.get("WORKER_ROLE"))

    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    tool = event.get("tool_name") or event.get("tool") or ""
    if not tool.startswith("mcp__claude-in-chrome__"):
        return 0

    session = str(event.get("session_id") or "unknown").replace("/", "_")
    path = STATE_DIR / f"{session}.json"

    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            counts = json.loads(path.read_text())
        except Exception:
            counts = {}
        calls = int(counts.get("chrome_calls", 0)) + 1
        shots = int(counts.get("screenshots", 0))
        action = (event.get("tool_input") or {}).get("action")
        if tool.endswith("__computer") and action in _SCREENSHOT_ACTIONS:
            shots += 1
        path.write_text(json.dumps({"chrome_calls": calls, "screenshots": shots}))
    except Exception:
        # A guard that breaks the session is worse than no guard.
        return 0

    if is_dev:
        if shots > DEV_MAX_SCREENSHOTS:
            print(f"WARNING: {_message('screenshot', calls, shots)}", file=sys.stderr)
            return 0
        if calls > DEV_MAX_CALLS:
            print(f"WARNING: {_message('browser-call', calls, shots)}", file=sys.stderr)
            return 0
        return 0
    else:
        if shots > MAX_SCREENSHOTS:
            print(_message("screenshot", calls, shots), file=sys.stderr)
            return 2
        if calls > MAX_CALLS:
            print(_message("browser-call", calls, shots), file=sys.stderr)
            return 2
        return 0


if __name__ == "__main__":
    sys.exit(main())
