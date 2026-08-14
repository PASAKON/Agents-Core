"""Stdio MCP server exposing the secretary's proxy actions (task-b293ef6c).

The secretary (`runners/secretary_server.py`) is reachable from Telegram, so
it must never get `Bash` or any general-purpose escape hatch. This server
is the alternative: four named, typed actions instead of a shell.

  mac_status()                          -- is the Mac up, via Tailscale?
  org_snapshot()                        -- what's running, Contabo-only view
  relay_to_session(target_role, message) -- queue/deliver an order to a C-level
  spawn_c_level(role, host)             -- start a C-level session

Design points this server exists to enforce (see TASK.md task-b293ef6c):
  1. Enumerated actions, never raw keystrokes -- no tool here takes a
     free-form command/shell/keys argument (see the guard test in
     scripts/test_relay_mcp_server.py).
  2. Proxy with attribution, never impersonation -- every message
     `relay_to_session` hands off is prefixed "[CEO via SomPong] "
     server-side; the caller cannot omit or spoof that marker.
  3. Read-only actions (mac_status, org_snapshot) execute immediately.
     Write actions that would reach the Mac (relay_to_session,
     spawn_c_level when their target has no live Contabo session) are
     queued for a separate, not-yet-built Mac-side draining agent -- see
     the queue helpers below for the contract that agent must honour.

Registered in config/secretary.mcp.json as server "relay" -- tools become
mcp__relay__<tool_name> inside the secretary's Claude Code CLI invocation.
Modelled on runners/dev_mcp_server.py and runners/cto_mcp_server.py (read
those first): thin @mcp.tool() functions, explicit error shaping, no
free-form escape hatch anywhere in this file.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests
from mcp.server.fastmcp import FastMCP

from lib.logger import get_logger
from tools import tmux_session

log = get_logger("relay", stdout=False)
mcp = FastMCP("relay")

# ---------------------------------------------------------------------------
# Known targets. Never derived from caller input -- an unknown role/host is
# always rejected, never guessed or passed through.
# ---------------------------------------------------------------------------
C_LEVEL_ROLES = ("cto", "cmo", "cgo", "cfo")
HOSTS = ("contabo", "mac")

# Design point 2 -- applied here, unconditionally, so the caller can never
# omit or spoof it (see relay_to_session).
RELAY_PREFIX = "[CEO via SomPong] "

# state/locks/<role>-active is the same pointer scripts/cxo-claude.sh writes
# for a live primary C-level session (also read by tools/send_to_cxo.py's
# iTerm path) -- reused here, not duplicated, just checked against tmux
# liveness instead of an iTerm tab (Contabo has no iTerm).
LOCKS_DIR = ROOT / "state" / "locks"

TAILSCALE_BIN = os.environ.get("RELAY_TAILSCALE_BIN", "tailscale")
# Verified live from Contabo 2026-08-13 (TASK.md): the Mac's tailscale
# HostName. Matched by substring, not a hardcoded peer index -- the tailnet
# also carries iPhones and a Windows box, and peer order is not stable.
MAC_HOSTNAME_MATCH = os.environ.get("RELAY_MAC_HOSTNAME", "MacBook Pro ของ GoB")

SUPABASE_TABLE = "claudeflow_agent_runs"
AGENT_RUNS_WINDOW_HOURS = 24
AGENT_RUNS_LIMIT = 20

# Deliverable 3 -- the Mac-bound work queue. Same SECRETARY_* env-override
# pattern as runners/secretary_server.py's SESSION_DB_PATH: default lives
# under this checkout, but a service user with no write access to a
# root-owned checkout (Contabo) must be able to point it elsewhere.
QUEUE_DB_PATH = Path(
    os.environ.get("SECRETARY_RELAY_QUEUE_DB") or ROOT / "state" / "relay_queue.db"
)


# ---------------------------------------------------------------------------
# Audit trail -- "Every call to every tool appends an audit line (who, what,
# when, delivered-or-queued). The CEO must be able to reconstruct what the
# bot did on their behalf." (TASK.md Deliverable 1). One line per call,
# state/logs/relay.log (get_logger already timestamps + rotates).
# ---------------------------------------------------------------------------

def _audit(tool: str, target: str, outcome: str, detail: str = "") -> None:
    log.info("AUDIT actor=secretary tool=%s target=%s outcome=%s detail=%s",
              tool, target, outcome, detail)


# ---------------------------------------------------------------------------
# Deliverable 3 -- the queue. Append / list-pending / mark-done only; this
# server never drains it. See the module docstring above and the contract
# comment on `_queue_enqueue` below for what the future Mac-side draining
# agent (a separate task) must do with what it finds here. Not exposed as
# MCP tools themselves -- the four tools above are the only surface; these
# are plumbing `relay_to_session`/`spawn_c_level` call into.
# ---------------------------------------------------------------------------

def _queue_conn() -> sqlite3.Connection:
    QUEUE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(QUEUE_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS relay_queue (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            kind        TEXT NOT NULL,
            target_role TEXT NOT NULL,
            payload     TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            created_at  TEXT NOT NULL,
            done_at     TEXT,
            result      TEXT
        )"""
    )
    return conn


def _queue_enqueue(kind: str, target_role: str, payload: dict) -> int:
    """Append a pending entry. Returns its id.

    Contract for the future Mac-side draining agent (not built here — see
    TASK.md "Out of scope"):
      - Poll `_queue_list_pending()`-equivalent reads periodically, oldest
        id first (the query already orders that way).
      - kind="relay": payload["message"] already carries the
        "[CEO via SomPong] " prefix -- do NOT re-prefix it. Deliver with
        the Mac's own tools/send_to_cxo.py send(target_role, message),
        the Mac-only iTerm-tab path this queue exists because Contabo
        cannot reach.
      - kind="spawn": payload is {}. Reaching this queue at all implies
        host="mac" (a Contabo target is delivered immediately and never
        queued). Deliver with the Mac's scripts/spawn-cxo.sh --role
        <target_role> (the Mac original, with its iTerm/osascript window
        creation -- safe there, unlike on Contabo).
      - After acting, success or failure, call mark-done exactly once with
        a short human-readable outcome string. Never leave an entry
        pending after it has actually been attempted.
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _queue_conn() as conn:
        cur = conn.execute(
            "INSERT INTO relay_queue (kind, target_role, payload, status, created_at) "
            "VALUES (?, ?, ?, 'pending', ?)",
            (kind, target_role, json.dumps(payload), now),
        )
        conn.commit()
        return cur.lastrowid


def _queue_list_pending() -> list[dict]:
    with _queue_conn() as conn:
        rows = conn.execute(
            "SELECT id, kind, target_role, payload, created_at "
            "FROM relay_queue WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
    return [
        {
            "id": r[0], "kind": r[1], "target_role": r[2],
            "payload": json.loads(r[3]), "created_at": r[4],
        }
        for r in rows
    ]


def _queue_mark_done(entry_id: int, result: str) -> bool:
    """Idempotent: returns False (no-op) for an unknown id or one already
    marked done, so a duplicate call can never double-apply a result."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _queue_conn() as conn:
        cur = conn.execute(
            "UPDATE relay_queue SET status = 'done', done_at = ?, result = ? "
            "WHERE id = ? AND status = 'pending'",
            (now, result, entry_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# mac_status
# ---------------------------------------------------------------------------

def _tailscale_status_json() -> dict | None:
    """Fixed command, no caller-supplied argument ever reaches subprocess.
    Returns the parsed dict, or None for ANY failure (missing binary,
    non-zero exit, unparseable JSON) -- callers turn None into an explicit
    "unknown" state, never a guess."""
    try:
        result = subprocess.run(
            [TAILSCALE_BIN, "status", "--json"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _find_mac_peer(data: dict) -> dict | None:
    """Identify the Mac by HostName match, never a hardcoded peer index --
    the tailnet also carries iPhones and a Windows box, and peer order in
    the JSON is not stable."""
    peers = (data or {}).get("Peer") or {}
    needle = MAC_HOSTNAME_MATCH.lower()
    for peer in peers.values():
        hostname = str(peer.get("HostName") or "")
        if needle in hostname.lower():
            return peer
    return None


def _mac_status_dict() -> dict:
    data = _tailscale_status_json()
    if data is None:
        return {
            "reachable": None, "state": "unknown",
            "last_seen": None, "hostname": None,
            "summary_th": "เช็คสถานะ Mac ไม่ได้ตอนนี้ครับ (tailscale ใช้งานไม่ได้)",
        }
    peer = _find_mac_peer(data)
    if peer is None:
        return {
            "reachable": None, "state": "unknown",
            "last_seen": None, "hostname": None,
            "summary_th": "หา Mac ใน tailnet ไม่เจอครับ",
        }
    online = bool(peer.get("Online"))
    last_seen = peer.get("LastSeen")
    hostname = peer.get("HostName")
    if online:
        summary = "Mac ออนไลน์อยู่ครับ"
    else:
        summary = (
            f"Mac หลับอยู่ครับ (เห็นล่าสุด {last_seen or 'ไม่ทราบ'}) "
            "ย้ายไปทำที่ Contabo แทนไหมครับ"
        )
    return {
        "reachable": online, "state": "up" if online else "down",
        "last_seen": last_seen, "hostname": hostname,
        "summary_th": summary,
    }


@mcp.tool()
def mac_status() -> str:
    """Is the Mac reachable right now, via Tailscale? No arguments.

    Fixed `tailscale status --json` call -- no caller-supplied argument
    ever reaches the subprocess. Identifies the Mac by hostname match, not
    a hardcoded peer index. If tailscale is missing, errors, or returns
    unparseable JSON, returns an explicit "unknown" state -- never
    guesses "asleep", never raises. `summary_th` is a ready-to-repeat
    Thai sentence for the secretary to hand back verbatim.
    """
    result = _mac_status_dict()
    _audit("mac_status", "mac", result["state"], result["summary_th"])
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# org_snapshot
# ---------------------------------------------------------------------------

def _tmux_sessions() -> list[str]:
    """Live tmux sessions on Contabo. Fixed `tmux ls` -- no argument. Empty
    list, not an error, both when tmux has no sessions and when the
    binary/server is unavailable -- "no sessions" is the normal shape here
    (Contabo currently has zero C-level tmux sessions, per TASK.md)."""
    try:
        result = subprocess.run(
            ["tmux", "ls"], capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _recent_agent_runs() -> dict:
    """Best-effort read of claudeflow_agent_runs (last 24h, capped rows).
    Never raises -- a missing credential or network failure becomes
    available=False so org_snapshot can say plainly this part is missing
    rather than presenting a partial picture as complete."""
    base_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not base_url or not service_key:
        return {
            "available": False,
            "reason": "missing SUPABASE_URL/SUPABASE_SERVICE_KEY",
            "rows": [],
        }
    since = (datetime.now(timezone.utc) - timedelta(hours=AGENT_RUNS_WINDOW_HOURS)).isoformat()
    try:
        r = requests.get(
            f"{base_url}/rest/v1/{SUPABASE_TABLE}",
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
            params={
                "select": "agent_name,status,created_at",
                "created_at": f"gte.{since}",
                "order": "created_at.desc",
                "limit": str(AGENT_RUNS_LIMIT),
            },
            timeout=15,
        )
        r.raise_for_status()
        rows = r.json()
    except (requests.RequestException, ValueError) as e:
        return {"available": False, "reason": str(e), "rows": []}
    return {
        "available": True, "rows": rows,
        "window_hours": AGENT_RUNS_WINDOW_HOURS, "capped_at": AGENT_RUNS_LIMIT,
    }


@mcp.tool()
def org_snapshot() -> str:
    """What the org is doing right now, from Contabo-reachable sources
    only. No arguments.

    Does NOT include LungNote to-do counts -- the secretary's own LungNote
    tools already cover that; duplicating it here would risk two
    disagreeing answers. Covers: live tmux sessions on Contabo, and
    recent (last 24h, capped) claudeflow_agent_runs rows from Supabase.
    Always states which parts are Contabo-only so the secretary never
    presents a partial picture as complete.
    """
    tmux_sessions = _tmux_sessions()
    agent_runs = _recent_agent_runs()
    result = {
        "scope_note": (
            "Contabo-only snapshot -- excludes anything only visible from "
            "the Mac. LungNote to-dos are not duplicated here; use the "
            "secretary's own LungNote tools for those."
        ),
        "tmux_sessions": tmux_sessions,
        "recent_agent_runs": agent_runs,
    }
    _audit("org_snapshot", "-", "ok",
           f"tmux_sessions={len(tmux_sessions)} agent_runs_available={agent_runs['available']}")
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# relay_to_session
# ---------------------------------------------------------------------------

def _active_contabo_tmux_session(role: str) -> str | None:
    """Live Contabo tmux session name for `role`, or None.

    Reads the same state/locks/<role>-active pointer scripts/cxo-claude.sh
    writes for a live primary session, then checks tmux liveness (not an
    iTerm tab -- Contabo has none). A stale pointer (file present, tmux
    session gone) is treated the same as no pointer: not found, not a
    crash (Deliverable 2)."""
    pointer = LOCKS_DIR / f"{role}-active"
    if not pointer.exists():
        return None
    session_id = pointer.read_text().strip()
    if not session_id:
        return None
    tmux_name = f"{role}-{session_id}"
    return tmux_name if tmux_session.has_session(tmux_name) else None


@mcp.tool()
def relay_to_session(target_role: str, message: str) -> str:
    """Queue or deliver an order to a C-level session, on the CEO's behalf.

    `target_role` must be one of cto/cmo/cgo/cfo -- anything else is
    rejected. `message` is free text (a message, never a shell command or
    key sequence) and is ALWAYS stored/delivered with the
    "[CEO via SomPong] " attribution prefix applied here, server-side --
    the caller cannot omit or spoof it (a receiving session must be able
    to tell a bot-relayed order from something the CEO typed directly).

    If a live Contabo tmux session for `target_role` exists, delivers now
    via tmux send-keys and reports delivered. Otherwise the target is
    assumed to live on the Mac: the message is enqueued for the separate,
    not-yet-built Mac-side draining agent, and the response reports
    queued together with whether the Mac is currently reachable -- so the
    secretary can offer moving the request to Contabo instead of silently
    parking it.
    """
    if target_role not in C_LEVEL_ROLES:
        _audit("relay_to_session", target_role, "rejected", "unknown target_role")
        return json.dumps({
            "status": "rejected",
            "reason": f"unknown role {target_role!r}. Known: {', '.join(C_LEVEL_ROLES)}",
        }, ensure_ascii=False)

    full_message = f"{RELAY_PREFIX}{message}"

    tmux_name = _active_contabo_tmux_session(target_role)
    if tmux_name:
        try:
            tmux_session.send_keys(tmux_name, full_message)
        except RuntimeError as e:
            _audit("relay_to_session", target_role, "delivery_failed", str(e))
            return json.dumps({
                "status": "error", "target_role": target_role, "detail": str(e),
            }, ensure_ascii=False)
        _audit("relay_to_session", target_role, "delivered",
               f"tmux={tmux_name} message={full_message!r}")
        return json.dumps({
            "status": "delivered", "target_role": target_role,
            "tmux_session": tmux_name, "message": full_message,
        }, ensure_ascii=False)

    queue_id = _queue_enqueue("relay", target_role, {"message": full_message})
    mac = _mac_status_dict()
    _audit("relay_to_session", target_role, "queued",
           f"queue_id={queue_id} mac_state={mac['state']} message={full_message!r}")
    return json.dumps({
        "status": "queued", "target_role": target_role, "queue_id": queue_id,
        "message": full_message,
        "mac_reachable": mac["reachable"], "mac_state": mac["state"],
        "mac_summary_th": mac["summary_th"],
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# spawn_c_level
# ---------------------------------------------------------------------------

@mcp.tool()
def spawn_c_level(role: str, host: str) -> str:
    """Start a C-level session, on the CEO's behalf -- equivalent in
    effect to the CEO running `/spawn-cto` (or the cmo/cgo/cfo
    equivalent) themselves, so every call is audited prominently.

    `role` must be one of cto/cmo/cgo/cfo. `host` must be "contabo" or
    "mac" -- anything else is rejected.

    host="contabo": starts a live tmux session running
    scripts/cxo-claude.sh for `role` right now (tmux, not iTerm --
    Contabo is headless; MoonieX Console already attaches to C-level
    sessions this same way).
    host="mac": enqueued for the separate, not-yet-built Mac-side
    draining agent (same queue relay_to_session uses).
    """
    if role not in C_LEVEL_ROLES:
        _audit("spawn_c_level", role, "rejected", f"unknown role, host={host}")
        return json.dumps({
            "status": "rejected",
            "reason": f"unknown role {role!r}. Known: {', '.join(C_LEVEL_ROLES)}",
        }, ensure_ascii=False)
    if host not in HOSTS:
        _audit("spawn_c_level", role, "rejected", f"unknown host {host!r}")
        return json.dumps({
            "status": "rejected",
            "reason": f"unknown host {host!r}. Known: {', '.join(HOSTS)}",
        }, ensure_ascii=False)

    if host == "mac":
        queue_id = _queue_enqueue("spawn", role, {})
        mac = _mac_status_dict()
        _audit("spawn_c_level", role, "queued",
               f"queue_id={queue_id} mac_state={mac['state']}")
        return json.dumps({
            "status": "queued", "role": role, "host": "mac", "queue_id": queue_id,
            "mac_reachable": mac["reachable"], "mac_state": mac["state"],
            "mac_summary_th": mac["summary_th"],
        }, ensure_ascii=False)

    # host == "contabo"
    session_id = uuid.uuid4().hex[:8]
    tmux_name = f"{role}-{session_id}"
    cmd = (
        f"export CXO_SESSION_ID={session_id} && "
        f"exec bash '{ROOT / 'scripts' / 'cxo-claude.sh'}' --role {role}"
    )
    try:
        tmux_session.create(tmux_name, ROOT, cmd)
    except Exception as e:
        _audit("spawn_c_level", role, "spawn_failed", f"host=contabo error={e}")
        return json.dumps({
            "status": "error", "role": role, "host": "contabo", "detail": str(e),
        }, ensure_ascii=False)
    _audit("spawn_c_level", role, "spawned", f"host=contabo tmux={tmux_name}")
    return json.dumps({
        "status": "spawned", "role": role, "host": "contabo",
        "tmux_session": tmux_name, "session_id": session_id,
    }, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
