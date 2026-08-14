"""report_to_ceo -- the reply half of the CEO-orders obligation ledger
(task-df6de4d4 D3).

`runners/relay_mcp_server.py::relay_to_session` (Contabo, the secretary's
own MCP server) opens a `ceo_orders` row per delivered order and hands the
recipient an order id in the letter's footer. This module is how ANY
C-level (cto/cmo/cgo/cfo) closes that row -- from wherever it happens to be
running, Contabo or the Mac -- and gets the reply's own wording into
SomPong's mailbox (the ledger row alone would lose it; see
`report_to_ceo`'s docstring).

Business logic only: `lib/org_tools_registry.py`'s own module docstring
says handler stubs stay thin ("No business logic lives here"), so this is
where report_to_ceo's actually lives. Wired in as that tool's ToolSpec
handler -- `_h_report_to_ceo` there is a one-line pass-through.

This module runs inside a C-level session process -- an entirely separate
process from the secretary's relay MCP server that owns the ceo_orders
table. It therefore resolves its OWN copy of the DB path / SSH target
constants from the same env vars, rather than importing a `runners.*`
module from `lib.*` (wrong layering direction -- runners depends on lib,
never the reverse). Same duplication-for-independence reasoning already
used in this codebase for C_LEVEL_ROLES/HISTORY_MODES between
runners/mac_agent.py and runners/relay_mcp_server.py.
"""
from __future__ import annotations

import json
import os
import shlex
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import mailbox  # noqa: E402
from tools.agent_transport import current_identity  # noqa: E402
from tools.org_inspector import detect_host  # noqa: E402

# The three outcomes a C-level may close an order with. 'awaiting_reply' is
# insert-only (relay_to_session sets it; never a valid target status here).
REPLY_STATUSES = ("done", "failed", "blocked")

# Same DB file runners/relay_mcp_server.py's _orders_conn()/_queue_conn()
# use -- see the module docstring for why this is a second copy of the path
# resolution rather than an import.
QUEUE_DB_PATH = Path(
    os.environ.get("SECRETARY_RELAY_QUEUE_DB") or ROOT / "state" / "relay_queue.db"
)

# Same SSH target runners/mac_agent.py drains the relay queue through --
# same env var names on purpose, one Mac-side SSH config serves both
# directions (mac_agent.py only ever reads orders out; this module writes
# a reply in). Mirrors runners/mac_agent.py::_ssh_sqlite's invocation
# exactly, per the task brief.
SSH_HOST = os.environ.get("MAC_AGENT_SSH_HOST", "mooniex-vps")
REMOTE_DB = os.environ.get(
    "MAC_AGENT_REMOTE_DB", "/home/secretary/runtime/relay_queue.db"
)
REMOTE_SQLITE_USER = os.environ.get("MAC_AGENT_REMOTE_USER", "secretary")
SSH_TIMEOUT = int(os.environ.get("MAC_AGENT_SSH_TIMEOUT", "20"))
# Contabo's own checkout root -- needed only for the Mac branch of the
# mailbox write below (SomPong's inbox is a real path under it, not a DB
# row). Same default this repo's own CLAUDE.md documents.
REMOTE_ROOT = os.environ.get("MAC_AGENT_REMOTE_ROOT", "/opt/mooniex-agents")

# Cap on the reply_detail text shipped over SSH in one SQL statement --
# mirrors runners/mac_agent.py's MAX_RESULT_CHARS discipline (bound what
# leaves the machine in one call).
MAX_DETAIL_CHARS = 4000

# SomPong's own mailbox identity -- the reply's `to`, matching the `from`
# runners/relay_mcp_server.py stamps on the original order.
SECRETARY_TO_ROLE = "secretary"
SECRETARY_TO_SESSION_ID = "sompong"


# ---------------------------------------------------------------------------
# Transport -- local (Contabo) vs over SSH (Mac). Mirrors
# tools/org_inspector.py's own host-aware pattern: detect via detect_host()
# (ORG_INSPECTOR_HOST overridable, never guessed), branch, never assume.
# ---------------------------------------------------------------------------

def _local_conn() -> sqlite3.Connection:
    QUEUE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(QUEUE_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS ceo_orders (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            target_role       TEXT NOT NULL,
            target_session_id TEXT,
            host              TEXT NOT NULL,
            order_text        TEXT NOT NULL,
            sent_at           TEXT NOT NULL,
            status            TEXT NOT NULL DEFAULT 'awaiting_reply'
                              CHECK(status IN ('awaiting_reply','done','failed','blocked')),
            replied_at        TEXT,
            reply_detail      TEXT
        )"""
    )
    return conn


def _ssh_exec(remote_cmd: str, input_text: str | None = None) -> tuple[bool, str]:
    """Run one remote command over SSH. Returns (ok, output). Never raises
    -- an unreachable VPS is an expected, not exceptional, outcome here
    (see report_to_ceo's docstring: "if it cannot, return an explicit
    failure" -- not a crash). `input_text`, when given, travels over stdin
    rather than being shell-interpolated -- the ONE thing this function
    lets a caller pass arbitrary text through safely (see
    `_deliver_reply_letter`'s Mac branch, which ships a whole JSON letter
    body this way instead of quoting it onto the command line)."""
    try:
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={SSH_TIMEOUT}",
             SSH_HOST, remote_cmd],
            input=input_text, capture_output=True, text=True,
            timeout=SSH_TIMEOUT + 15,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"ssh failed: {e}"
    if r.returncode != 0:
        return False, (r.stderr or "").strip()[:400]
    return True, r.stdout


def _ssh_sqlite(sql: str) -> tuple[bool, str]:
    """Run one SQL statement against Contabo's queue DB over SSH. Same
    invocation as runners/mac_agent.py::_ssh_sqlite (same env vars, same
    `sudo -u secretary sqlite3 <db> <sql>` shape) -- duplicated rather than
    imported because that function lives in a runners.* module (see module
    docstring)."""
    remote = (
        f"sudo -u {shlex.quote(REMOTE_SQLITE_USER)} "
        f"sqlite3 {shlex.quote(REMOTE_DB)} {shlex.quote(sql)}"
    )
    return _ssh_exec(remote)


# ---------------------------------------------------------------------------
# Lookup -- host-aware, three-way result: found-and-open / found-and-closed
# / not-found, PLUS an explicit "couldn't even ask" for an unreachable Mac
# link. Never conflate "not found" with "couldn't check" -- report_to_ceo
# must never claim success for an order it couldn't actually verify.
# ---------------------------------------------------------------------------

def _lookup_order(order_id: int, host: str) -> dict:
    if host == "contabo":
        with _local_conn() as conn:
            row = conn.execute(
                "SELECT status, replied_at FROM ceo_orders WHERE id = ?",
                (order_id,),
            ).fetchone()
        if row is None:
            return {"ok": True, "found": False}
        return {"ok": True, "found": True, "status": row[0], "replied_at": row[1]}

    sql = f"SELECT status, replied_at FROM ceo_orders WHERE id = {int(order_id)};"
    ok, out = _ssh_sqlite(sql)
    if not ok:
        return {"ok": False, "reason": f"cannot reach Contabo over SSH: {out}"}
    line = out.strip()
    if not line:
        return {"ok": True, "found": False}
    parts = line.split("|", 1)
    return {
        "ok": True, "found": True,
        "status": parts[0],
        "replied_at": parts[1] if len(parts) > 1 and parts[1] else None,
    }


def _close_order(order_id: int, status: str, detail: str, now: str, host: str) -> dict:
    """Conditional UPDATE (WHERE status = 'awaiting_reply') doubles as a
    race guard: if the row was closed by someone else between the lookup
    above and this call, zero rows change and that is reported as a
    failure, not silently treated as success."""
    if host == "contabo":
        with _local_conn() as conn:
            cur = conn.execute(
                "UPDATE ceo_orders SET status = ?, replied_at = ?, reply_detail = ? "
                "WHERE id = ? AND status = 'awaiting_reply'",
                (status, now, detail, order_id),
            )
            conn.commit()
            changed = cur.rowcount
        if changed > 0:
            return {"ok": True}
        return {"ok": False, "reason": "row no longer awaiting_reply"}

    safe_detail = detail.replace("'", "''")[:MAX_DETAIL_CHARS]
    sql = (
        f"UPDATE ceo_orders SET status = '{status}', replied_at = '{now}', "
        f"reply_detail = '{safe_detail}' "
        f"WHERE id = {int(order_id)} AND status = 'awaiting_reply'; "
        "SELECT changes();"
    )
    ok, out = _ssh_sqlite(sql)
    if not ok:
        return {"ok": False, "reason": f"cannot reach Contabo over SSH: {out}"}
    try:
        changed = int(out.strip() or "0")
    except ValueError:
        changed = 0
    if changed > 0:
        return {"ok": True}
    return {"ok": False, "reason": "row no longer awaiting_reply"}


def _deliver_reply_letter(host: str, body: str, from_role: str,
                           from_session_id: str) -> dict:
    """Write the reply into SomPong's mailbox. On Contabo that is a plain
    `lib.mailbox.send()` -- this process's own filesystem IS Contabo's
    checkout. On the Mac, a local `mailbox.send()` call would write into
    THIS machine's own state/inbox/ tree, which SomPong (Contabo-only, no
    live process anywhere else) will never read -- "sitting nowhere" is
    exactly the failure mode the task brief calls out. So the Mac branch
    ships the identical letter shape over SSH instead, landing it in
    Contabo's real inbox directory. The JSON body travels over stdin
    (`_ssh_exec`'s `input_text`), never shell-interpolated -- arbitrary
    reply text can never break out of the remote command line.
    """
    if host == "contabo":
        try:
            mailbox.send(
                SECRETARY_TO_ROLE, SECRETARY_TO_SESSION_ID, body,
                from_role, from_session_id,
            )
        except Exception as e:
            return {"ok": False, "reason": f"mailbox write failed: {e}"}
        return {"ok": True}

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    letter = {
        "from": {"role": from_role, "session_id": from_session_id},
        "to": {"role": SECRETARY_TO_ROLE, "session_id": SECRETARY_TO_SESSION_ID},
        "chain": [f"{from_role}:{from_session_id}"],
        "sent_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "body": body,
    }
    payload = json.dumps(letter, ensure_ascii=False, indent=2)
    remote_dir = f"{REMOTE_ROOT}/state/inbox/{SECRETARY_TO_ROLE}-{SECRETARY_TO_SESSION_ID}"
    remote_path = f"{remote_dir}/{ts}-{from_role}-{from_session_id}.json"
    remote_cmd = (
        f"sudo -u {shlex.quote(REMOTE_SQLITE_USER)} mkdir -p {shlex.quote(remote_dir)} && "
        f"sudo -u {shlex.quote(REMOTE_SQLITE_USER)} tee {shlex.quote(remote_path)} > /dev/null"
    )
    ok, out = _ssh_exec(remote_cmd, input_text=payload)
    if not ok:
        return {"ok": False, "reason": f"cannot reach Contabo over SSH: {out}"}
    return {"ok": True}


# ---------------------------------------------------------------------------
# report_to_ceo -- the tool
# ---------------------------------------------------------------------------

def report_to_ceo(order_id: int, status: str, detail: str) -> str:
    """Close out a CEO order relayed via SomPong. Called by the C-level
    session the order was addressed to, using the order id from the
    letter's footer (task-df6de4d4 D2).

    Order of operations, and why:
      1. Validate `status`. Anything outside REPLY_STATUSES writes
         NOTHING -- not a partial ledger update, not a letter.
      2. Look up the row (host-aware). Unknown id, already-closed id, or
         an unreachable Contabo (Mac branch, VPS down) all short-circuit
         here -- reported honestly, nothing written. A C-level that thinks
         it reported when it did not is exactly the failure this task
         exists to remove.
      3. Write the reply letter into SomPong's mailbox -- lib.mailbox.send
         on Contabo, the SSH-shipped equivalent on the Mac. SomPong has no
         live process today, so nothing drains this box yet (the
         follow-up task's job); write it anyway, because the ledger row
         alone would lose the C-level's own wording.
      4. Close the ledger row (status/replied_at/reply_detail), guarded by
         the same WHERE status='awaiting_reply' the lookup already
         confirmed, closing a benign race (closed by someone else between
         steps 2 and 4) instead of silently double-applying.

    The identity on the letter is always the CALLING session's own
    (tools.agent_transport.current_identity(), the same resolver
    tools/send_to_cxo.py uses) -- never the CEO, never the secretary. A
    non-C-level caller (no CXO_ROLE/CXO_SESSION_ID in this process's env)
    is refused before anything is looked up.
    """
    if status not in REPLY_STATUSES:
        return (
            f"rejected: status must be one of {'/'.join(REPLY_STATUSES)}, "
            f"got {status!r} -- nothing written"
        )

    identity = current_identity()
    if identity.kind != "cxo":
        return (
            "rejected: report_to_ceo must be called from a C-level session "
            f"(current identity: {identity.label()}) -- nothing written"
        )

    host = detect_host()

    lookup = _lookup_order(order_id, host)
    if not lookup["ok"]:
        return f"order #{order_id}: {lookup['reason']} -- reply NOT sent, nothing written"
    if not lookup["found"]:
        return f"order #{order_id} not found"
    if lookup["status"] != "awaiting_reply":
        return (
            f"order #{order_id} already closed as {lookup['status']} "
            f"at {lookup['replied_at']}"
        )

    from_role = identity.role
    from_session_id = identity.session_id or ""
    body = f"[report_to_ceo] order #{order_id} -- {status}\n{detail}"

    sent = _deliver_reply_letter(host, body, from_role, from_session_id)
    if not sent["ok"]:
        return f"order #{order_id}: {sent['reason']} -- reply NOT sent, ledger untouched"

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    closed = _close_order(order_id, status, detail, now, host)
    if not closed["ok"]:
        return (
            f"order #{order_id}: reply letter sent, but the ledger could not "
            f"be closed ({closed['reason']}) -- check list_ceo_orders"
        )
    return f"order #{order_id} closed as {status}"
