#!/usr/bin/env python3
"""PreToolUse hook on `Agent`: log every in-session subagent call a C-level
makes (tool-value plan 2026-10-13 §4.3 M2, week 1 = log only).

Why: a C-level's own Agent calls never reach delegate_task, so the router, the
override gate and the Monday report cannot see them. Last week's override lines
said "in-session Agent run by CTO …" 13 times, and nobody counted the rest.
This hook counts them. It never blocks: it prints nothing and returns 0 on
every path. Whether a dev-shaped call without `route:` / `override:` gets
refused from 26 Oct is the CEO's call after he sees week 1.

Where the line goes: one JSON line per call, appended to
state/reports/agent-calls.jsonl (gitignored by state/reports/*). It does not
write a hub event inline, because the hook runs under the system python3 of
the session, and a C-level session has neither ORG_DB_URL nor psycopg (measured
on Contabo 2026-10-13). tools/tool_value.py collect, which runs with the hub
env, reads the spool. A Mac session's spool reaches the report only through
the Mac collector (plan T5).

What a line holds: ts, the Claude session id, role, org session id, host, cwd,
entrypoint, subagent_type, model, the description (≤80 chars), prompt length
in characters, whether the agent type is read-only, and the `route:` or
`override:` marker on the prompt's first line. Never the prompt text.

Who is logged: C-level sessions (CXO_SESSION=1 or CTO_SESSION=1, set by
cto-claude.sh / cxo-claude.sh). Silent for:
  - SomPong (CXO_ROLE=coo): his Agent calls are his own loop, not dev work;
  - workers: WORKER_TASK_ID set (runners/worker_init.py) or cwd under /worktrees/.
A headless `claude -p` started from a C-level shell inherits CXO_SESSION=1 and
is logged, labelled by its entrypoint: it spends the same quota.
"""
from __future__ import annotations

import json
import os
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL_NAMES = {"Agent", "Task"}  # "Task" is the tool's name in older Claude Code builds.
# Agent types that cannot edit files: plan M2 never blocks these.
READ_ONLY_TYPES = {"Explore", "Plan", "claude-code-guide", "statusline-setup"}
ROUTE_RE = re.compile(r"^\s*route:\s*(task-[0-9a-f]{8})\b", re.IGNORECASE)
OVERRIDE_RE = re.compile(r"^\s*override:\s*([A-Za-z][\w-]*)", re.IGNORECASE)
SCHEMA = 1


def _spool() -> Path:
    # Tests point this at tmp_path, never the real state/.
    return Path(os.environ.get("AGENT_ROUTE_LOG_PATH")
                or ROOT / "state" / "reports" / "agent-calls.jsonl")


def _exempt(payload: dict) -> bool:
    env = os.environ
    if env.get("CXO_SESSION") != "1" and env.get("CTO_SESSION") != "1":
        return True
    if env.get("CXO_ROLE") == "coo":
        return True
    return bool(env.get("WORKER_TASK_ID")) or "/worktrees/" in str(payload.get("cwd") or "")


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line
    return ""


def record(payload: dict) -> dict:
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    prompt = tool_input.get("prompt") if isinstance(tool_input.get("prompt"), str) else ""
    subagent = str(tool_input.get("subagent_type") or "general-purpose")
    first = _first_line(prompt)
    route = ROUTE_RE.match(first)
    override = OVERRIDE_RE.match(first)
    env = os.environ
    return {
        "schema": SCHEMA,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_id": str(payload.get("session_id") or payload.get("sessionId") or ""),
        "role": env.get("CXO_ROLE") or "cto",
        "org_session": env.get("CTO_SESSION_ID") or env.get("CXO_SESSION_ID") or "",
        "host": socket.gethostname(),
        "cwd": str(payload.get("cwd") or ""),
        "entrypoint": env.get("CLAUDE_CODE_ENTRYPOINT") or "",
        "tool": str(payload.get("tool_name") or ""),
        "subagent_type": subagent,
        "model": str(tool_input.get("model") or ""),
        "description": str(tool_input.get("description") or "")[:80],
        "prompt_chars": len(prompt),
        "read_only": subagent in READ_ONLY_TYPES,
        "background": bool(tool_input.get("run_in_background")),
        "route": route.group(1).lower() if route else "",
        "override": override.group(1).lower() if override else "",
    }


def _append(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # One write on an O_APPEND fd: two sessions logging at the same instant
    # cannot interleave inside a line this short.
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict) or payload.get("tool_name") not in TOOL_NAMES:
            return 0
        if _exempt(payload):
            return 0
        _append(_spool(), json.dumps(record(payload), ensure_ascii=False) + "\n")
    except Exception:
        # A lost log line is harmless; a blocked Agent call is not.
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
