#!/usr/bin/env python3
"""COO gate -- the only process that holds SomPong's hub credential (CEO card Q-20261013-1948-4a33).

SomPong (the COO, unix user `sompong`) may create and delegate its own research workers --
researcher, data_analyst, browser_operator -- and never a code role. Its "org" MCP server
(runners/coo_mcp_server.py) holds no secret; it sends one JSON line per call to this gate over a
unix socket, and the gate does the hub work as the Postgres role `org_coo`.

Three properties, each enforced here and again below it:
  1. Who: SO_PEERCRED on every connection. Only the uids in COO_GATE_ALLOWED_UIDS (sompong's,
     resolved by deploy/coo-gate/install.sh) and root get an answer.
  2. What: a fixed table of ops (OPS below). No op takes SQL, a shell string, a project, an owner
     or a runner: the gate stamps owner_role='coo', the project from its own config, and refuses a
     role outside lib/coo_policy.COO_WORKER_ROLES before anything is written. lib.db.create_task
     checks the role again, and the hub's org_coo_guard trigger a third time
     (deploy/coo-gate/org_coo_role.sql).
  3. Which rows: every task op checks owner_role='coo'. The gate never changes a task's status and
     never starts a worker: `delegate_task` and `close_task` file an event the root dispatcher
     (runners/coo_dispatch.py) acts on, through its own hub connection. So the socket-facing
     process can do no more than org_coo can, and org_coo can do no more than this file.

Protocol: one JSON object per line in, one per line out, then the connection closes.
    {"op": "create_task", "session_id": "...", "role": "researcher", "title": "...", "description": "..."}
    -> {"ok": true, "task_id": "task-..."}      or      {"ok": false, "error": "..."}

Requests are handled one at a time (the ops are a few short statements each); a slow client is cut
off after COO_GATE_SOCKET_TIMEOUT seconds. Waiting for a task to finish is the client's poll loop,
never a blocking op here. Logs name the op, the peer uid and the task id, never a description.
"""
from __future__ import annotations

import json
import logging
import os
import re
import socket
import struct
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import coo_policy, db  # noqa: E402
from tools import ask_run  # noqa: E402  (secret shapes only: one list of them, not a second copy)

DEFAULT_SOCKET = "/run/org-coo-gate/gate.sock"
DEFAULT_PROJECT = "mooniex-agents"
MAX_REQUEST_BYTES = 64 * 1024
MAX_TITLE = 200
MAX_DESCRIPTION = 20_000
MAX_CHARTER = 500
LIST_LIMIT = 50
# Statuses a coo task can be closed from. Closing is the dispatcher's write (status 'done').
CLOSABLE = ("review", "failed", "stalled", "blocked_human")
TASK_FIELDS = ("id", "role", "title", "status", "runner", "runner_model", "report",
               "delegate_log", "created_at", "updated_at", "owner_cto")
RESPAWN_FIELDS = frozenset({"op", "session_id", "role", "host"})
RESPAWN_STATUS_FIELDS = frozenset({"op", "session_id", "request_id"})
# Audit log (#38) and field notes (#24b). The caps here are mirrored in org_coo_role.sql, which
# checks the same shapes again; tests/test_coo_gate.py reads both and keeps them equal.
AUDIT_FIELDS = frozenset({"op", "session_id", "tool", "input", "ok"})
FIELD_NOTE_FIELDS = frozenset({"op", "session_id", "skill", "tag", "text"})
MAX_AUDIT_TOOL = 100
MAX_AUDIT_INPUT = 2000
MAX_FIELD_NOTE = 600
FIELD_NOTE_TAGS = ("MISSING", "WRONG", "COSTLY", "CONFIRMED")
SKILL_NAME = re.compile(r"[A-Za-z0-9_.\-]{3,80}")        # fullmatch: `$` would let a newline through
SKILLS_DIR = ROOT / ".claude" / "skills"
RATE_WINDOW_S = 3600
AUDIT_MAX_PER_HOUR = 600
FIELD_NOTE_MAX_PER_HOUR = 30

log = logging.getLogger("coo_gate")


class Refused(Exception):
    """A request this gate will not carry out; the message goes back to the caller."""


# --------------------------------------------------------------------------- config

def allowed_uids(environ: dict[str, str] | None = None) -> frozenset[int]:
    raw = (environ if environ is not None else os.environ).get("COO_GATE_ALLOWED_UIDS", "")
    try:
        uids = frozenset(int(u) for u in raw.split(",") if u.strip())
    except ValueError as e:
        raise SystemExit(f"COO_GATE_ALLOWED_UIDS must be comma-separated integers: {e}") from e
    return uids | {0}


def project(environ: dict[str, str] | None = None) -> str:
    return (environ if environ is not None else os.environ).get("COO_GATE_PROJECT") or DEFAULT_PROJECT


# --------------------------------------------------------------------------- field checks

def _text(req: dict, key: str, limit: int) -> str:
    value = req.get(key)
    if not isinstance(value, str) or not value.strip():
        raise Refused(f"{key} is required (a non-empty string)")
    if len(value) > limit:
        raise Refused(f"{key} is longer than {limit} characters")
    return value.strip()


def _task_id(req: dict) -> str:
    tid = _text(req, "task_id", 64)
    if not tid.startswith("task-") or not tid[5:].replace("-", "").isalnum():
        raise Refused("task_id must look like task-xxxxxxxx")
    return tid


def _coo_session(session_id: str) -> None:
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT session_id FROM c_level_sessions WHERE role=? AND session_id=?",
            (coo_policy.COO_ROLE, session_id)).fetchone()
    if row is None:
        raise Refused(f"session {session_id!r} is not a coo session in the hub")


def _coo_task(task_id: str) -> dict:
    task = db.get_task(task_id)
    if not task or task.get("owner_role") != coo_policy.COO_ROLE:
        # Same answer for "absent" and "not yours": the gate does not confirm other tasks exist.
        raise Refused(f"{task_id} is not a coo task")
    return task


def _slim(task: dict) -> dict:
    return {k: task.get(k) for k in TASK_FIELDS}


# --------------------------------------------------------------------------- redaction + rate cap

_REDACTED = "<redacted>"
# One list of token shapes (tools/ask_run.py, tested against scripts/contabo_blueprint.sh), plus the
# two it lacks: a Google OAuth access token and an HTTP Basic credential.
_TOKEN_SHAPES = tuple(rx for _label, rx in ask_run._TOKEN_SHAPES) + (
    re.compile(r"\bya29\.[A-Za-z0-9_.\-]{20,}"),
    re.compile(r"\bBasic\s+[A-Za-z0-9+/]{8,}=*", re.IGNORECASE),
)
_PRIVATE_KEY = re.compile(ask_run.PRIVATE_KEY_MARKER + r".*?(?:END [A-Z ]*PRIVATE KEY|\Z)", re.DOTALL)
_SECRET_KEY = re.compile(ask_run.SECRET_KEY_WORDS, re.IGNORECASE)
# `name=` / `name:` / `"name":` with the name starting at a word boundary, so each run of name
# characters is scanned once (a keyword inside the name is tested in Python, not by backtracking).
_KEY_SEP = re.compile(r"(?<![A-Za-z0-9_.\-])([A-Za-z0-9_.\-]+)[\\\"']*[ \t]*[:=][ \t]*")
# A literal value; a bare reference to an env var ($NAME) is how a secret should be named, so it stays.
_VALUE = re.compile(
    r"""\\?(["'])(?!\$\{?[A-Za-z_])(?:(?!\1).)*|(?!\$\{?[A-Za-z_])[^\s"'\\,;&}\]]+""", re.DOTALL)
# A long unbroken run of key-like characters that mixes letters and digits. Paths are left alone
# (a run right after `/` is not tested) and so is a UUID.
_LONG_RUN = re.compile(r"(?<![A-Za-z0-9_\-/])[A-Za-z0-9_\-]{32,}")
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _mask_run(m: re.Match) -> str:
    run = m.group(0)
    if _UUID.fullmatch(run) or not (re.search(r"\d", run) and re.search(r"[A-Za-z]", run)):
        return run
    return _REDACTED


def _redact(text: str) -> str:
    """`text` with what looks like a credential masked. Best effort by shape, not a guarantee: a
    secret in a form none of these match (a bare short password, `curl -u user:pass`) passes.
    Linear time: this runs inside the gate's one request loop on text the COO's tools wrote."""
    text = _PRIVATE_KEY.sub(_REDACTED, text)
    for rx in _TOKEN_SHAPES:
        text = rx.sub(_REDACTED, text)
    text = db.redact_url(text) or ""
    out, pos = [], 0
    for m in _KEY_SEP.finditer(text):
        if m.start() < pos or not _SECRET_KEY.search(m.group(1)):
            continue         # inside a value already masked, or not a secret's name
        v = _VALUE.match(text, m.end())
        if v:
            out += [text[pos:v.start()], _REDACTED]
            pos = v.end()
    out.append(text[pos:])
    return _LONG_RUN.sub(_mask_run, "".join(out))


def _clean(text: str) -> str:
    """No NUL and no lone surrogate: Postgres refuses both in a jsonb string, which would drop the
    row (an audit gap anyone could open by putting one in a command)."""
    return text.replace("\x00", "").encode("utf-8", "replace").decode("utf-8")


# kind:session -> times of the rows written in the last hour. The gate is one process and the hub
# trigger cannot count rows (org_coo may not read audit rows back), so the cap lives here and starts
# again from zero if the gate restarts.
_recent: dict[str, list[float]] = {}


def _over_cap(kind: str, session_id: str, limit: int, now: float) -> bool:
    key = f"{kind}:{session_id}"
    recent = [t for t in _recent.get(key, ()) if now - t < RATE_WINDOW_S]
    _recent[key] = recent
    return len(recent) >= limit


def _count_row(kind: str, session_id: str, now: float) -> None:
    _recent.setdefault(f"{kind}:{session_id}", []).append(now)


# --------------------------------------------------------------------------- ops

def op_ping(req: dict, uid: int) -> dict:
    return {"uid": uid, "roles": list(coo_policy.COO_WORKER_ROLES), "project": project()}


def op_set_charter(req: dict, uid: int) -> dict:
    session_id = _text(req, "session_id", 64)
    charter = _text(req, "charter", MAX_CHARTER)
    _coo_session(session_id)
    with db.get_conn() as conn:
        conn.execute("UPDATE c_level_sessions SET charter=? WHERE role=? AND session_id=?",
                     (charter, coo_policy.COO_ROLE, session_id))
    return {"session_id": session_id}


def op_create_task(req: dict, uid: int) -> dict:
    session_id = _text(req, "session_id", 64)
    role = _text(req, "role", 40)
    title = _text(req, "title", MAX_TITLE)
    description = _text(req, "description", MAX_DESCRIPTION)
    try:
        coo_policy.check_role(coo_policy.COO_ROLE, role)
    except coo_policy.CooRoleRefused as e:
        raise Refused(str(e)) from e
    _coo_session(session_id)
    # researcher runs through runners/coo_worker.py, which routes outside runners first
    # (config/plans.yaml role class `research`); the other two go through tools/delegate.py
    # pinned to claude, so no launcher pushes a branch for them.
    runner = None if role == "researcher" else "claude"
    tid = db.create_task(project(), role, title, description, touches=[],
                         owner_cto=session_id, owner_role=coo_policy.COO_ROLE, runner=runner)
    return {"task_id": tid}


def op_delegate_task(req: dict, uid: int) -> dict:
    tid = _task_id(req)
    task = _coo_task(tid)
    try:
        coo_policy.check_role(task.get("owner_role"), task.get("role") or "")
    except coo_policy.CooRoleRefused as e:
        raise Refused(str(e)) from e
    if task.get("status") != "pending":
        raise Refused(f"{tid} is {task.get('status')}, only a pending task can be delegated")
    with db.get_conn() as conn:
        db.log_event(conn, tid, "coo_gate", "coo_delegate_request", {"uid": uid})
    return {"task_id": tid, "queued": True,
            "note": "the dispatcher starts it within ~30 s; poll get_task"}


def op_get_task(req: dict, uid: int) -> dict:
    return {"task": _slim(_coo_task(_task_id(req)))}


def op_list_tasks(req: dict, uid: int) -> dict:
    limit = req.get("limit", 20)
    if not isinstance(limit, int) or not 1 <= limit <= LIST_LIMIT:
        raise Refused(f"limit must be an integer from 1 to {LIST_LIMIT}")
    cols = ("id", "role", "title", "status", "runner", "created_at", "updated_at")
    with db.get_conn() as conn:
        rows = conn.execute(
            f"SELECT {', '.join(cols)} FROM tasks "
            "WHERE owner_role=? ORDER BY created_at DESC LIMIT ?",
            (coo_policy.COO_ROLE, limit)).fetchall()
    return {"tasks": [{c: r[c] for c in cols} for r in rows]}


def op_close_task(req: dict, uid: int) -> dict:
    tid = _task_id(req)
    task = _coo_task(tid)
    if task.get("status") not in CLOSABLE:
        raise Refused(f"{tid} is {task.get('status')}; close works from {', '.join(CLOSABLE)}")
    # The COO's verdict on the report becomes the job's runner_fit (tools/runner_fit.py).
    result = req.get("result", "pass")
    if result not in ("pass", "fail"):
        raise Refused("result must be pass or fail")
    why = req.get("why", "")
    if not isinstance(why, str) or len(why) > 300:
        raise Refused("why must be a string of at most 300 characters")
    with db.get_conn() as conn:
        db.log_event(conn, tid, "coo_gate", "coo_close_request",
                     {"uid": uid, "result": result, "why": why.strip()})
    return {"task_id": tid, "queued": True}


def op_live_sessions(req: dict, uid: int) -> dict:
    """The live-session list SomPong must check before any SendMessage (CEO 2026-10-13). Read-only:
    org_coo holds SELECT on live_hosts and live_sessions columns and nothing else there."""
    from tools import live_sessions
    with db.get_conn() as conn:
        return {"text": live_sessions.render(conn, all_roles=bool(req.get("all")))}


def op_respawn_clevel(req: dict, uid: int, *, now=None) -> dict:
    """Queue a C-level respawn request on Contabo (CEO pick #18, 2026-10-26).

    Accepts ONLY {op, session_id, role, host}: no prompt, brief, argv, id or uuid from the COO may
    reach the new session. Rate-limited here and again in runners/coo_dispatch.py."""
    extra = sorted(set(req) - RESPAWN_FIELDS)
    if extra:
        raise Refused(
            f"respawn_clevel accepts only role, host, session_id (unexpected: {', '.join(extra)})"
        )
    session_id = _text(req, "session_id", 64)
    role = _text(req, "role", 40)
    host = _text(req, "host", 40)
    try:
        coo_policy.check_respawn(role, host)
    except coo_policy.CooRoleRefused as e:
        raise Refused(str(e)) from e
    _coo_session(session_id)
    with db.get_conn() as conn:
        rows = [
            dict(r) for r in conn.execute(
                "SELECT id, kind, payload, ts FROM coo_respawn_events",
            ).fetchall()
        ]
        reason = coo_policy.respawn_rate_limit_reason(rows, role, now=now)
        if reason:
            raise Refused(reason)
        payload = {"role": role, "host": host, "by_session": session_id}
        db.log_event(conn, None, "coo_gate", "coo_respawn_request", payload)
        # events.payload is text: match by_session and role in Python, so the
        # same SQL runs on Postgres and the SQLite tests.
        request_id = 0
        for ev in conn.execute(
            "SELECT id, payload FROM coo_respawn_events WHERE kind=? ORDER BY id DESC LIMIT 20",
            ("coo_respawn_request",),
        ).fetchall():
            raw = ev["payload"]
            p = json.loads(raw) if isinstance(raw, str) else (raw or {})
            if isinstance(p, dict) and p.get("by_session") == session_id and p.get("role") == role:
                request_id = int(ev["id"])
                break
    return {"request_id": request_id, "role": role, "host": host, "queued": True}


def op_respawn_status(req: dict, uid: int) -> dict:
    """Read the dispatcher's coo_respawn_done event for a prior coo_respawn_request id."""
    extra = sorted(set(req) - RESPAWN_STATUS_FIELDS)
    if extra:
        raise Refused(
            f"respawn_status accepts only request_id, session_id (unexpected: {', '.join(extra)})"
        )
    if req.get("session_id") is not None:
        _coo_session(_text(req, "session_id", 64))
    request_id = req.get("request_id")
    if isinstance(request_id, bool) or not isinstance(request_id, int) or request_id < 1:
        raise Refused("request_id must be a positive integer")
    with db.get_conn() as conn:
        req_row = conn.execute(
            "SELECT id, payload, ts FROM coo_respawn_events WHERE id=? AND kind=?",
            (request_id, "coo_respawn_request"),
        ).fetchone()
        if req_row is None:
            raise Refused(f"respawn request {request_id} not found")
        raw_req = req_row["payload"]
        req_payload = json.loads(raw_req) if isinstance(raw_req, str) else (raw_req or {})
        done_rows = conn.execute(
            "SELECT id, payload, ts FROM coo_respawn_events WHERE kind=? AND id>? ORDER BY id ASC",
            ("coo_respawn_done", request_id),
        ).fetchall()
    for row in done_rows:
        raw_done = row["payload"]
        try:
            done_payload = json.loads(raw_done) if isinstance(raw_done, str) else (raw_done or {})
        except ValueError:
            continue
        if not isinstance(done_payload, dict):
            continue
        rid = done_payload.get("request_id")
        if rid == request_id:
            return {
                "request_id": request_id,
                "done": True,
                "respawn_ok": bool(done_payload.get("ok")),
                "role": done_payload.get("role"),
                "host": done_payload.get("host"),
                "mode": done_payload.get("mode"),
                "sid": done_payload.get("sid"),
                "uuid": done_payload.get("uuid"),
                "reason": done_payload.get("reason"),
                "event": done_payload,
            }
    return {
        "request_id": request_id,
        "done": False,
        "role": req_payload.get("role"),
        "host": req_payload.get("host"),
    }


def op_audit_append(req: dict, uid: int, *, now: float | None = None) -> dict:
    """Append one row to the COO's audit log (#38): which tool it ran, with what input, and whether it
    worked. Fed by scripts/coo-audit-hook.py from the COO's own Claude Code settings. Accepts ONLY
    {op, session_id, tool, input, ok}. The input is redacted, cut to MAX_AUDIT_INPUT, and kept as text."""
    extra = sorted(set(req) - AUDIT_FIELDS)
    if extra:
        raise Refused(f"audit_append accepts only session_id, tool, input, ok (unexpected: {', '.join(extra)})")
    session_id = _text(req, "session_id", 64)
    tool = _clean(req["tool"]).strip()[:MAX_AUDIT_TOOL] if isinstance(req.get("tool"), str) else ""
    if not tool:
        raise Refused("tool is required (a non-empty string)")
    if not isinstance(req.get("input"), str):
        raise Refused("input must be a string (the tool input as JSON text)")
    if not isinstance(req.get("ok"), bool):
        raise Refused("ok must be true or false")
    _coo_session(session_id)
    now = time.time() if now is None else now
    if _over_cap("audit", session_id, AUDIT_MAX_PER_HOUR, now):
        raise Refused(f"audit rate cap: at most {AUDIT_MAX_PER_HOUR} rows per session per hour")
    # Redact the whole text and cut after: cutting first could leave half a key at the edge, short
    # enough to slip under the length rule in _redact.
    payload = {"session_id": session_id, "tool": tool,
               "input": _redact(_clean(req["input"]))[:MAX_AUDIT_INPUT], "ok": req["ok"]}
    with db.get_conn() as conn:
        db.log_event(conn, None, "coo_gate", "coo_audit", payload)
    _count_row("audit", session_id, now)
    return {"recorded": True}


def op_field_note(req: dict, uid: int, *, now: float | None = None) -> dict:
    """File one field note (#24b) about an org skill: what it got wrong, lacked, cost, or got right.
    The gate writes the event and nothing else; a CTO or PH reads it with tools/coo_field_notes.py
    and folds it into the skill by hand. Accepts ONLY {op, session_id, skill, tag, text}."""
    extra = sorted(set(req) - FIELD_NOTE_FIELDS)
    if extra:
        raise Refused(f"field_note accepts only session_id, skill, tag, text (unexpected: {', '.join(extra)})")
    session_id = _text(req, "session_id", 64)
    skill = req.get("skill")
    if not isinstance(skill, str) or not SKILL_NAME.fullmatch(skill) or skill.startswith("."):
        raise Refused("skill must match ^[A-Za-z0-9_.-]{3,80}$")
    if not (SKILLS_DIR / skill).is_dir():
        raise Refused(f"skill {skill!r} is not a directory under .claude/skills/")
    tag = req.get("tag")
    if tag not in FIELD_NOTE_TAGS:
        raise Refused(f"tag must be one of {', '.join(FIELD_NOTE_TAGS)}")
    text = _clean(_text(req, "text", MAX_FIELD_NOTE))
    if len(text.splitlines()) != 1:
        raise Refused("text must be a single line")
    _coo_session(session_id)
    now = time.time() if now is None else now
    if _over_cap("field_note", session_id, FIELD_NOTE_MAX_PER_HOUR, now):
        raise Refused(f"field note rate cap: at most {FIELD_NOTE_MAX_PER_HOUR} per session per hour")
    # A note ends up in a skill file in a public repo: mask anything credential-shaped first.
    payload = {"session_id": session_id, "skill": skill, "tag": tag,
               "text": _redact(text)[:MAX_FIELD_NOTE]}
    with db.get_conn() as conn:
        db.log_event(conn, None, "coo_gate", "coo_field_note", payload)
    _count_row("field_note", session_id, now)
    return {"recorded": True, "skill": skill, "tag": tag}


OPS: dict[str, Callable[[dict, int], dict]] = {
    "ping": op_ping,
    "set_charter": op_set_charter,
    "create_task": op_create_task,
    "delegate_task": op_delegate_task,
    "get_task": op_get_task,
    "list_tasks": op_list_tasks,
    "close_task": op_close_task,
    "live_sessions": op_live_sessions,
    "respawn_clevel": op_respawn_clevel,
    "respawn_status": op_respawn_status,
    "audit_append": op_audit_append,
    "field_note": op_field_note,
}


def handle(req: Any, uid: int) -> dict:
    """One request -> one response dict. Never raises."""
    if not isinstance(req, dict) or not isinstance(req.get("op"), str):
        return {"ok": False, "error": "request must be a JSON object with an 'op'"}
    fn = OPS.get(req["op"])
    if fn is None:
        return {"ok": False, "error": f"unknown op {req['op']!r}; ops: {', '.join(OPS)}"}
    try:
        out = fn(req, uid)
    except Refused as e:
        log.info("refused op=%s uid=%s task=%s: %s", req["op"], uid, req.get("task_id"), e)
        return {"ok": False, "error": str(e)}
    except Exception as e:  # a hub error, a trigger refusal: report the class, keep serving
        log.warning("error op=%s uid=%s task=%s: %s: %s", req["op"], uid, req.get("task_id"),
                    type(e).__name__, str(e).splitlines()[0] if str(e) else "")
        return {"ok": False, "error": f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}"}
    log.info("ok op=%s uid=%s task=%s", req["op"], uid, out.get("task_id") or req.get("task_id"))
    return {"ok": True, **out}


# --------------------------------------------------------------------------- socket

def peer_uid(conn: socket.socket) -> int:
    creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", creds)
    return uid


def _read_line(conn: socket.socket) -> bytes:
    buf = b""
    while b"\n" not in buf:
        chunk = conn.recv(4096)
        if not chunk:
            break
        buf += chunk
        if len(buf) > MAX_REQUEST_BYTES:
            raise Refused(f"request is longer than {MAX_REQUEST_BYTES} bytes")
    return buf.split(b"\n", 1)[0]


def serve_one(conn: socket.socket, uids: frozenset[int]) -> None:
    uid = peer_uid(conn)
    if uid not in uids:
        log.warning("refused connection from uid %s", uid)
        conn.sendall(b'{"ok": false, "error": "this uid may not use the COO gate"}\n')
        return
    try:
        line = _read_line(conn)
        req = json.loads(line.decode("utf-8"))
    except Refused as e:
        resp = {"ok": False, "error": str(e)}
    except (UnicodeDecodeError, json.JSONDecodeError):
        resp = {"ok": False, "error": "request is not one line of JSON"}
    else:
        resp = handle(req, uid)
    conn.sendall((json.dumps(resp, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


def bind(path: str) -> socket.socket:
    p = Path(path)
    if p.exists() or p.is_symlink():
        p.unlink()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(path)
    # Anyone may connect; serve_one answers only the allowed uids (SO_PEERCRED cannot be faked).
    os.chmod(path, 0o666)
    sock.listen(16)
    return sock


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s coo_gate %(levelname)s %(message)s")
    if not os.environ.get("ORG_DB_URL"):
        log.error("ORG_DB_URL is not set: start through deploy/coo-gate/org-coo-gate.service")
        return 2
    if os.geteuid() == 0:
        log.error("refusing to run as root: the unit drops to org-coo-gate with setpriv")
        return 2
    uids = allowed_uids()
    timeout = float(os.environ.get("COO_GATE_SOCKET_TIMEOUT") or 10)
    path = os.environ.get("COO_GATE_SOCKET") or DEFAULT_SOCKET
    server = bind(path)
    log.info("listening on %s for uids %s, project %s", path, sorted(uids), project())
    while True:
        conn, _ = server.accept()
        with conn:
            conn.settimeout(timeout)
            try:
                serve_one(conn, uids)
            except (OSError, TimeoutError) as e:
                log.warning("connection dropped: %s", type(e).__name__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
