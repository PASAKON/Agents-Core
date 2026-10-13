#!/usr/bin/env python3
"""SomPong's "org" MCP server: delegate research workers through the COO gate, holding no secret.

CEO card Q-20261013-1948-4a33 (option 1, 2026-10-13): SomPong (the COO) may create and delegate
its own research workers -- researcher, data_analyst, browser_operator -- and never a code role
("CTO ไว้ดูแลเรื่อง Coding ในองค์กรอย่างเดียว"). Code work still goes to a CTO.

This server runs as the unix user `sompong`, as a child of SomPong's Claude session
(scripts/lib/cxo_mcp_config.py wires it as the "org" server for role coo). It has no hub
credential and never reads one: every tool is one JSON line to the COO gate
(runners/coo_gate.py) over /run/org-coo-gate/gate.sock, which checks the caller's uid and does the
hub work as the narrow Postgres role org_coo. The session id comes from CXO_SESSION_ID, which the
COO launcher sets; the gate checks that it is a coo session.

Tools (mcp__org__<name> inside the session):
  set_charter(charter)                          one line: what this session is doing (required
                                                before the first create_task, IRON §35)
  create_task(role, title, description)         researcher | data_analyst | browser_operator
  delegate_task(task_id)                        queue it; the root dispatcher starts the worker
  get_task(task_id) / list_tasks(limit)         status and, once in review, the report
  wait_task(task_id, timeout_s)                 poll until the worker reports (or the timeout)
  close_task(task_id, result, why)              done; result pass|fail scores the runner
  live_sessions(all)                            who is live on every host: run before SendMessage

CLI for tests and for SomPong's own Bash (no MCP needed):
  .venv/bin/python -m runners.coo_mcp_server --cli create_task '{"role": "researcher", ...}'
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
from pathlib import Path

SOCKET_PATH = os.environ.get("COO_GATE_SOCKET") or "/run/org-coo-gate/gate.sock"
TIMEOUT_S = 15.0
POLL_S = 10.0
MAX_WAIT_S = 1800
# Statuses that mean "the worker is still going": wait_task keeps polling through these.
RUNNING = ("pending", "in_progress", "rate_limited", "conflict", "queued_remote")
# The tool names this server serves, in order. cxo_mcp_config builds the coo session's
# --allowed-tools from this tuple (mcp__org__<name>), so the two never drift.
TOOL_NAMES = ("set_charter", "create_task", "delegate_task", "get_task", "list_tasks",
              "wait_task", "close_task", "live_sessions")


def session_id() -> str:
    return (os.environ.get("CXO_SESSION_ID") or os.environ.get("COO_SESSION_ID") or "").strip()


def call(op: str, **fields) -> dict:
    """One request to the gate. Never raises: a transport problem comes back as ok:false."""
    req = {"op": op, **fields}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT_S)
            s.connect(SOCKET_PATH)
            s.sendall((json.dumps(req, ensure_ascii=False) + "\n").encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
    except FileNotFoundError:
        return {"ok": False, "error": f"the COO gate is not running ({SOCKET_PATH} missing): "
                                      "tell the CTO (org-coo-gate.service)"}
    except OSError as e:
        return {"ok": False, "error": f"COO gate unreachable: {type(e).__name__}: {e}"}
    try:
        return json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "error": "the COO gate sent no valid answer"}


def _with_session(op: str, **fields) -> dict:
    sid = session_id()
    if not sid:
        return {"ok": False, "error": "CXO_SESSION_ID is not set in this session's environment"}
    return call(op, session_id=sid, **fields)


# Plain functions first (the CLI and the tests call these); MCP wrappers below.

def set_charter(charter: str) -> dict:
    return _with_session("set_charter", charter=charter)


def create_task(role: str, title: str, description: str) -> dict:
    return _with_session("create_task", role=role, title=title, description=description)


def delegate_task(task_id: str) -> dict:
    return call("delegate_task", task_id=task_id)


def get_task(task_id: str) -> dict:
    return call("get_task", task_id=task_id)


def list_tasks(limit: int = 20) -> dict:
    return call("list_tasks", limit=limit)


def wait_task(task_id: str, timeout_s: int = 600, *, sleep=time.sleep, clock=time.monotonic) -> dict:
    deadline = clock() + max(0, min(int(timeout_s), MAX_WAIT_S))
    while True:
        out = get_task(task_id)
        status = ((out.get("task") or {}).get("status")) if out.get("ok") else None
        if not out.get("ok") or status not in RUNNING or clock() >= deadline:
            if out.get("ok") and status in RUNNING:
                out["note"] = f"still {status} after {timeout_s}s; call wait_task again"
            return out
        sleep(POLL_S)


def close_task(task_id: str, result: str = "pass", why: str = "") -> dict:
    return call("close_task", task_id=task_id, result=result, why=why)


def live_sessions(all: bool = False) -> dict:
    return call("live_sessions", all=bool(all))


def _serve() -> None:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("org")

    @mcp.tool(name="set_charter")
    def _set_charter(charter: str) -> str:
        """Set this COO session's one-line charter (what it is working on). Needed once per
        session before create_task."""
        return json.dumps(set_charter(charter), ensure_ascii=False)

    @mcp.tool(name="create_task")
    def _create_task(role: str, title: str, description: str) -> str:
        """Create a worker task. role: researcher (web research + reading repos, report only),
        data_analyst, or browser_operator. Any other role is refused: code work goes to a CTO via
        SendMessage to a CTO. description is the full brief the worker gets."""
        return json.dumps(create_task(role, title, description), ensure_ascii=False)

    @mcp.tool(name="delegate_task")
    def _delegate_task(task_id: str) -> str:
        """Start the worker for a pending task you created. Returns at once; use wait_task."""
        return json.dumps(delegate_task(task_id), ensure_ascii=False)

    @mcp.tool(name="get_task")
    def _get_task(task_id: str) -> str:
        """Status of one of your tasks; once it is in review, `report` holds the worker's report."""
        return json.dumps(get_task(task_id), ensure_ascii=False)

    @mcp.tool(name="list_tasks")
    def _list_tasks(limit: int = 20) -> str:
        """Your most recent tasks (1-50), newest first."""
        return json.dumps(list_tasks(limit), ensure_ascii=False)

    @mcp.tool(name="wait_task")
    def _wait_task(task_id: str, timeout_s: int = 600) -> str:
        """Wait until the worker reports (status leaves pending/in_progress) or timeout_s passes
        (max 1800). Returns the task, with the report when there is one."""
        return json.dumps(wait_task(task_id, timeout_s), ensure_ascii=False)

    @mcp.tool(name="close_task")
    def _close_task(task_id: str, result: str = "pass", why: str = "") -> str:
        """Close a task after reading its report (from review, failed or stalled). result: pass
        (the report answered the brief) or fail (it did not; say why in one line). The verdict is
        recorded as the job's runner score."""
        return json.dumps(close_task(task_id, result, why), ensure_ascii=False)

    @mcp.tool(name="live_sessions")
    def _live_sessions(all: bool = False) -> str:
        """The C-level sessions live right now on every host. Run it before any SendMessage and
        send only to a name it prints, verbatim (CEO 2026-10-13). all=true lists workers too."""
        out = live_sessions(all)
        return out.get("text") if out.get("ok") and out.get("text") else json.dumps(out, ensure_ascii=False)

    mcp.run()


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] not in TOOL_NAMES + ("ping",):
        print(f"usage: --cli <{'|'.join(TOOL_NAMES + ('ping',))}> ['<json args>']", file=sys.stderr)
        return 2
    args = json.loads(argv[1]) if len(argv) > 1 else {}
    if argv[0] == "ping":
        out = call("ping")
    else:
        out = globals()[argv[0]](**args)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        sys.exit(_cli(sys.argv[2:]))
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    _serve()
