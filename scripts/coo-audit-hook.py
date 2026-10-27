#!/usr/bin/env python3
"""PostToolUse hook for SomPong's Claude Code session: one audit row per tool call (#38).

Reads the hook JSON on stdin and sends {op: audit_append, session_id, tool, input, ok} to the COO
gate (runners/coo_gate.py) over its unix socket. The gate redacts and cuts the input, checks that the
session is a coo session, and writes a `coo_audit` event the COO's own Postgres role can append to but
never read, change or delete (deploy/coo-gate/org_coo_role.sql).

Fail open, always: it prints nothing, exits 0 on every path, and gives up after 2 s in total
(stdin, connect, send and answer together). A gate that is down, slow, full (the hourly cap) or
unreachable costs one missing audit row and never blocks the COO.

The session id is CXO_SESSION_ID, else the hook's own session_id. This file is not registered in any
settings file by the repo: the PH wires it into SomPong's settings. Which means SomPong's settings
decide whether it runs (README, "Audit log").

Stdlib only: it runs under the system python3, once per tool call, so it must start fast.
Keep the two constants below equal to runners/coo_gate.py (tests/test_coo_gate.py checks).
"""
from __future__ import annotations

import json
import os
import signal
import socket
import sys
import time

DEFAULT_SOCKET = "/run/org-coo-gate/gate.sock"
BUDGET_S = 2.0
# The gate keeps MAX_AUDIT_INPUT (2000) characters after redacting the whole text. Sending more than
# that lets it redact before it cuts; the request line is capped at 64 KB, so 8000 is plenty.
SEND_INPUT_CHARS = 8000
MAX_AUDIT_TOOL = 100


def _tool_ok(payload: dict) -> bool:
    """False when the call failed: the failure event, or a response that says so."""
    if payload.get("hook_event_name") == "PostToolUseFailure":
        return False
    resp = payload.get("tool_response")
    if isinstance(resp, dict):
        if resp.get("is_error") or resp.get("error") or resp.get("success") is False:
            return False
    return True


def request_from(payload: object, environ: dict[str, str]) -> dict | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("tool_name"), str):
        return None
    session_id = (environ.get("CXO_SESSION_ID") or "").strip() or str(payload.get("session_id") or "").strip()
    if not session_id:
        return None
    text = json.dumps(payload.get("tool_input"), ensure_ascii=False, default=str)
    return {"op": "audit_append", "session_id": session_id, "tool": payload["tool_name"][:MAX_AUDIT_TOOL],
            "input": text[:SEND_INPUT_CHARS], "ok": _tool_ok(payload)}


def send(req: dict, path: str, deadline: float) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        for step in ("connect", "send", "recv"):
            s.settimeout(max(0.05, deadline - time.monotonic()))
            if step == "connect":
                s.connect(path)
            elif step == "send":
                s.sendall((json.dumps(req, ensure_ascii=False) + "\n").encode("utf-8"))
            else:
                s.recv(4096)       # wait for the answer so the gate has written before we exit


def main() -> int:
    # SIGALRM is the backstop for the one thing the socket timeouts do not cover: a stdin that never closes.
    signal.signal(signal.SIGALRM, lambda *_: os._exit(0))
    signal.setitimer(signal.ITIMER_REAL, BUDGET_S)
    deadline = time.monotonic() + BUDGET_S
    try:
        req = request_from(json.loads(sys.stdin.read()), dict(os.environ))
        if req:
            send(req, os.environ.get("COO_GATE_SOCKET") or DEFAULT_SOCKET, deadline)
    except BaseException:   # fail open: nothing here may reach the COO
        pass
    return 0


if __name__ == "__main__":
    os._exit(main())
