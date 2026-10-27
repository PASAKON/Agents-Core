#!/usr/bin/env python3
"""SomPong's "org" MCP server: delegate research workers through the COO gate, holding no secret.

CEO card Q-20261013-1948-4a33 (option 1, 2026-10-13): SomPong (the COO) may create and delegate
its own research workers -- researcher, data_analyst, browser_operator -- and never a code role
("CTO ไว้ดูแลเรื่อง Coding ในองค์กรอย่างเดียว"). Code work still goes to a CTO.

This server runs as the unix user `sompong`, as a child of SomPong's Claude session
(scripts/lib/cxo_mcp_config.py wires it as the "org" server for role coo). It has no hub
credential and never reads one: worker tools send one JSON line to the COO gate
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
  ask_run / ask_ceo / ask_run_wait              Run Inbox command and question cards for the CEO's
                                                tap (root work goes through ask_run, CEO 2026-10-01)
  email_ceo(kind, title, ...)                   action / alert / done / deadline to the CEO only
  quota()                                      read the local runner quota snapshot
  field_note(skill, tag, text)                 one line about an org skill: MISSING | WRONG | COSTLY |
                                                CONFIRMED. A CTO or PH reads it and folds it in by hand.

The three Run Inbox tools do not go through the gate and touch no hub database: they are
tools/ask_run.py (the same code as every other C-level's org server), plain HTTPS to the Run Inbox
with SomPong's own token, ~/.config/mooniex/run-inbox.token (0600, owned by sompong). The COO is a
C-level (policies/agents.yaml c_level), so the hub lets it raise command and question cards.
email_ceo uses the same token through tools/email_ceo.py; quota reads no credentials.

CLI for tests and for SomPong's own Bash (no MCP needed):
  .venv/bin/python -m runners.coo_mcp_server --cli create_task '{"role": "researcher", ...}'
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SOCKET_PATH = os.environ.get("COO_GATE_SOCKET") or "/run/org-coo-gate/gate.sock"
TIMEOUT_S = 15.0
POLL_S = 10.0
MAX_WAIT_S = 1800
QUOTA_PATH = Path(__file__).resolve().parent.parent / "state" / "quota-snapshot.json"
# Statuses that mean "the worker is still going": wait_task keeps polling through these.
RUNNING = ("pending", "in_progress", "rate_limited", "conflict", "queued_remote")
# The tool names this server serves, in order. cxo_mcp_config builds the coo session's
# --allowed-tools from this tuple (mcp__org__<name>), so the two never drift.
TOOL_NAMES = ("set_charter", "create_task", "delegate_task", "get_task", "list_tasks",
              "wait_task", "close_task", "live_sessions", "ask_run", "ask_ceo", "ask_run_wait",
              "email_ceo", "quota", "field_note", "respawn_clevel")


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


def field_note(skill: str, tag: str, text: str) -> dict:
    return _with_session("field_note", skill=skill, tag=tag, text=text)


def respawn_status(request_id: int) -> dict:
    return call("respawn_status", request_id=request_id)


def respawn_clevel(role: str = "", host: str = "contabo", request_id: int | None = None) -> dict:
    if request_id is not None:
        return respawn_status(request_id)
    return _with_session("respawn_clevel", role=role, host=host)


# Run Inbox. tools.ask_run is imported here, not at the top: cxo_mcp_config loads this module under
# the launcher's system python3 to read TOOL_NAMES, so nothing outside the stdlib may load with it.
# A refusal or a hub error comes back as ok:false like every other tool here; ask_run's messages
# name the field and the kind of value, never the value.

def _run_inbox(fn_name: str, *args, **kwargs) -> dict:
    from tools import ask_run as ask_run_tool
    try:
        out = getattr(ask_run_tool, fn_name)(*args, **kwargs)
    except (ask_run_tool.Refused, ask_run_tool.HubError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, **out}


def ask_run(**arguments) -> dict:
    return _run_inbox("mcp_ask", arguments)


def ask_ceo(**arguments) -> dict:
    return _run_inbox("mcp_ask_ceo", arguments)


def email_ceo(**arguments) -> dict:
    from tools import email_ceo as email_ceo_tool
    if not (os.environ.get("CXO_SESSION_ID") or "").strip():
        return {"ok": False, "error": "CXO_SESSION_ID is not set in this session's environment"}
    arguments.update(role="coo", session=session_id())
    try:
        out = email_ceo_tool.mcp_send(arguments)
    except (email_ceo_tool.Refused, email_ceo_tool.HubError, ValueError) as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, **out}


def quota() -> dict:
    """Read the public snapshot only; never fetch live quota or expose source paths."""
    fields = ("weekly_remaining", "daily_remaining", "weekly_resets_at", "daily_resets_at",
              "limit_hit", "limit_until", "error")
    try:
        snapshot = json.loads(QUOTA_PATH.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(snapshot["ts"].replace("Z", "+00:00"))
        if ts.tzinfo is None:
            raise ValueError("snapshot timestamp has no timezone")
        buckets = {name: {field: bucket.get(field) for field in fields}
                   for name, bucket in snapshot["buckets"].items()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        return {"ok": False, "error": f"quota snapshot: {type(e).__name__}: {e}"}
    out = {"ok": True, "ts": snapshot["ts"], "buckets": buckets}
    if (datetime.now(timezone.utc) - ts).total_seconds() > 2 * 60 * 60:
        out["stale"] = True
    return out


def ask_run_wait(id: str, max_wait_s: float = 600.0, interval_s: float = 5.0,
                 tail_lines: int = 40) -> dict:
    return _run_inbox("wait_result", id, max_wait_s=max_wait_s, interval_s=interval_s,
                      tail_lines_n=tail_lines)


def _serve() -> None:
    import asyncio
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

    @mcp.tool(name="ask_run")
    async def _ask_run(host: str, why: str, command: str = "", script: str = "",
                       args: list[str] | None = None, expected: str = "", risk: str = "amber",
                       timeout_s: int = 300, expects_input: bool = False, shell: str = "",
                       cwd: str = "", env_keys: list[str] | None = None, session: str = "",
                       role: str = "", task: str = "", dry_run: bool = False,
                       spend: dict | None = None, no_spend: str = "") -> str:
        """Ask the CEO to run one command on a host via the Run Inbox (a card on his phone, Face
        ID). This is how root work happens (CEO 2026-10-01). The CEO's tap is the only authority.
        Raise it at once when a blocker needs his tap; never ask in chat first. A secret-shaped
        value is refused before anything is sent: name an env var instead (env_keys). Returns
        {id, url, risk, expires_at} at once; read the result with ask_run_wait on the id. `why`
        stays short (about 500 chars). dry_run=True sends nothing. A command that spends credit
        carries spend={provider, billing, unit, estimate, cap, how, balance_after?, budget?} and
        --max-usd/--max-credits equal to the cap in the command; a spend-looking command that is
        not spend sends no_spend='<reason>' (CEO 2026-10-14)."""
        out = await asyncio.to_thread(ask_run, host=host, why=why, command=command, script=script,
                                      args=args, expected=expected, risk=risk, timeout_s=timeout_s,
                                      expects_input=expects_input, shell=shell, cwd=cwd,
                                      env_keys=env_keys, session=session, role=role, task=task,
                                      dry_run=dry_run, spend=spend, no_spend=no_spend)
        return json.dumps(out, indent=2, ensure_ascii=False)

    @mcp.tool(name="ask_ceo")
    async def _ask_ceo(question: str = "", options: list[str] | None = None, why: str = "",
                       recommended: int = 0, free_text: bool = True, expires_h: float = 24.0,
                       session: str = "", role: str = "", host: str = "", task: str = "",
                       dry_run: bool = False, questions: list[dict] | None = None) -> str:
        """Ask the CEO a question with 2-4 answers he taps on /run (a question card). Never for a
        command, money or a secret (that is ask_run). options: 2-4 one-line labels; recommended:
        1-based, 0 = none; expires_h 24 by default. Several at once: questions=[{question, why,
        options, recommended, free_text}, ...] (1-6). Returns {id, url, expires_at} (or a QG-
        group id); read the answer with ask_run_wait: that hub record is his decision. Not the
        same tool as mcp__sompong__ask_ceo (Telegram/LINE)."""
        out = await asyncio.to_thread(ask_ceo, question=question, options=options, why=why,
                                      recommended=recommended, free_text=free_text,
                                      expires_h=expires_h, session=session, role=role, host=host,
                                      task=task, dry_run=dry_run, questions=questions)
        return json.dumps(out, indent=2, ensure_ascii=False)

    @mcp.tool(name="ask_run_wait")
    async def _ask_run_wait(id: str, max_wait_s: float = 600.0, interval_s: float = 5.0,
                            tail_lines: int = 40) -> str:
        """Wait for a RUN-..., Q-... or QG-... id to end (polls every 5 s) and return its record:
        terminal=true once it is done/failed/denied/expired/cancelled or answered; terminal=false
        when max_wait_s ran out first (default 600, keep it at or under 1500): call again."""
        out = await asyncio.to_thread(ask_run_wait, id, max_wait_s, interval_s, tail_lines)
        return json.dumps(out, indent=2, ensure_ascii=False)

    @mcp.tool(name="email_ceo")
    async def _email_ceo(kind: str, title: str, need: str = "", why: str = "",
                         if_not: str = "", link: str = "", due: str = "", ref: str = "",
                         dry_run: bool = False) -> str:
        """Send action/alert/done/deadline notifications to the CEO only. The hub enforces caps
        and deduplication; dry_run previews without sending. Uses this COO session's identity."""
        out = await asyncio.to_thread(email_ceo, kind=kind, title=title, need=need, why=why,
                                      if_not=if_not, link=link, due=due, ref=ref, dry_run=dry_run)
        return json.dumps(out, indent=2, ensure_ascii=False)

    @mcp.tool(name="quota")
    def _quota() -> str:
        """Read runner quota remaining and resets; stale=true means the snapshot is over 2 h old."""
        return json.dumps(quota(), ensure_ascii=False)

    @mcp.tool(name="field_note")
    def _field_note(skill: str, tag: str, text: str) -> str:
        """File one field note about an org skill you used (the directory name under .claude/skills/).
        tag: MISSING (it should have told you X), WRONG (a rule it states proved false), COSTLY (the
        step that ate the most time) or CONFIRMED (a rule that held). text: one line, at most 600
        characters, no secrets. A CTO or PH reads the notes and edits the skill by hand; you cannot
        change a skill from here."""
        return json.dumps(field_note(skill, tag, text), ensure_ascii=False)

    @mcp.tool(name="respawn_clevel")
    def _respawn_clevel(role: str = "", host: str = "contabo",
                        request_id: int | None = None) -> str:
        """Start or resume a missing peer C-level on Contabo (role: cto, cmo, cgo, or cfo;
        host must be 'contabo'). Returns {request_id, queued}; pass request_id to read the
        dispatcher's coo_respawn_done result."""
        return json.dumps(respawn_clevel(role=role, host=host, request_id=request_id),
                          ensure_ascii=False)

    mcp.run()


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] not in TOOL_NAMES + ("ping", "respawn_status"):
        print(f"usage: --cli <{'|'.join(TOOL_NAMES + ('ping', 'respawn_status'))}> ['<json args>']",
              file=sys.stderr)
        return 2
    args = json.loads(argv[1]) if len(argv) > 1 else {}
    if argv[0] == "ping":
        out = call("ping")
    else:
        out = globals()[argv[0]](**args)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # tools.ask_run
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        sys.exit(_cli(sys.argv[2:]))
    _serve()
