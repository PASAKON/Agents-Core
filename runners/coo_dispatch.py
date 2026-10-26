#!/usr/bin/env python3
"""Root dispatcher for SomPong's workers: acts on the requests the COO gate files (CEO card
Q-20261013-1948-4a33; workers run as root, CEO card Q-20261013-2010-091c).

The gate (runners/coo_gate.py, user org-coo-gate, hub role org_coo) can only INSERT pending coo
tasks and two kinds of request events. Everything with consequences happens here, as root, with
the hub owner's ORG_DB_URL (deploy/coo-gate/org-coo-dispatch.service starts this through
scripts/hub/with-org-db-env.sh):

  coo_delegate_request  on a pending coo task -> start its worker, one at a time, only while
                        MemAvailable >= MIN_FREE_MB (CEO brief: at most one worker, >= 1 GB free)
                          researcher                  runners/coo_worker.py in tmux `coo-<id8>`
                          data_analyst, browser_operator  tools/delegate.delegate_task, and only
                                                      when COO_DISPATCH_ROOT_ROLES=1 (CEO card
                                                      Q-20261013-2111-5ff5: wait for a box; until then
                                                      the task waits, with one event saying why)
  coo_close_request     on a coo task in review/failed/stalled -> status done, worker stopped
  a researcher whose tmux session is gone, or that ran past RUN_LIMIT_S -> failed
  every coo task that ended without a runner_fit event -> one runner_fit event (tools/runner_fit)

The role is checked again here (lib/coo_policy.check_role) before any worker starts. It never
starts a tmux server: with no server running it waits, because a server started from this unit
would live in its cgroup and die with it (CLAUDE.md "Contabo -- one tmux server").
"""
from __future__ import annotations

import asyncio
import errno
import fcntl
import json
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import coo_policy, db, session_names  # noqa: E402

POLL_S = 10
MIN_FREE_MB = 1024
MAX_WORKERS = 1
RUN_LIMIT_S = 45 * 60            # coo_worker's own limit is 30 min per runner attempt
GONE_GRACE_S = 120
ROOT_ROLES = ("data_analyst", "browser_operator")
CLOSABLE = ("review", "failed", "stalled", "blocked_human")
ENDED = ("done", "failed", "cancelled")
JOB_TYPE = {"researcher": "research", "data_analyst": "research", "browser_operator": "browse"}
TMUX = os.environ.get("COO_TMUX") or "tmux"
LOCKS_DIR = ROOT / "state" / "locks"
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

log = logging.getLogger("coo_dispatch")


# ---------------------------------------------------------------------------------- host checks

def mem_available_mb(meminfo: str | None = None) -> int:
    text = meminfo if meminfo is not None else Path("/proc/meminfo").read_text()
    for line in text.splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return 0


def tmux_server_up() -> bool:
    return subprocess.run([TMUX, "list-sessions"], capture_output=True).returncode == 0


def tmux_alive(name: str | None) -> bool:
    return bool(name) and subprocess.run([TMUX, "has-session", "-t", f"={name}"],
                                         capture_output=True).returncode == 0


def tmux_kill(name: str | None) -> None:
    if name and tmux_alive(name):
        subprocess.run([TMUX, "kill-session", "-t", f"={name}"], capture_output=True)


def tmux_sessions() -> list[str] | None:
    """Return session names in the shared tmux server, or None when unreachable/down."""
    try:
        r = subprocess.run(
            [TMUX, "list-sessions", "-F", "#{session_name}"],
            capture_output=True, text=True,
        )
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return [line.strip() for line in (r.stdout or "").splitlines() if line.strip()]


def single_role_flock_held(role: str, locks_dir: Path | None = None) -> bool:
    """Return True if state/locks/.single-<role>.flock is held or cannot be checked (fail-closed)."""
    target_dir = locks_dir if locks_dir is not None else LOCKS_DIR
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(target_dir / f".single-{role}.flock"), os.O_CREAT | os.O_RDWR, 0o644)
    except OSError:
        return True
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
            return True
        return True
    else:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        return False
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def root_roles_on(environ=None) -> bool:
    return (environ if environ is not None else os.environ).get("COO_DISPATCH_ROOT_ROLES") == "1"


# ---------------------------------------------------------------------------------- hub reads

def _rows(sql: str, params: tuple = ()) -> list[dict]:
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def delegate_requests() -> list[dict]:
    """Pending coo tasks that carry a delegate request, oldest request first."""
    return _rows(
        "SELECT t.id, t.role, t.title, MIN(e.id) AS req FROM tasks t JOIN events e ON e.task_id = t.id "
        "WHERE t.owner_role = ? AND t.status = 'pending' AND e.kind = 'coo_delegate_request' "
        "GROUP BY t.id, t.role, t.title ORDER BY req", (coo_policy.COO_ROLE,))


def close_requests() -> list[dict]:
    return _rows(
        "SELECT t.id, t.role, t.status, t.tmux_session, e.payload FROM tasks t "
        "JOIN events e ON e.task_id = t.id WHERE t.owner_role = ? AND e.kind = 'coo_close_request' "
        "AND t.status IN (" + ",".join("?" * len(CLOSABLE)) + ") ORDER BY e.id",
        (coo_policy.COO_ROLE, *CLOSABLE))


def running() -> list[dict]:
    return _rows("SELECT id, role, tmux_session, spawned_at, updated_at FROM tasks "
                 "WHERE owner_role = ? AND status = 'in_progress'", (coo_policy.COO_ROLE,))


def has_event(task_id: str, kind: str) -> bool:
    return bool(_rows("SELECT 1 FROM events WHERE task_id = ? AND kind = ? LIMIT 1", (task_id, kind)))


def _event(task_id: str, kind: str, payload: dict) -> None:
    with db.get_conn() as conn:
        db.log_event(conn, task_id, "coo_dispatch", kind, payload)


# ---------------------------------------------------------------------------------- actions

def start_researcher(tid: str) -> bool:
    if not db.claim_task(tid, "coo_dispatch"):
        return False
    name = f"coo-{tid.removeprefix('task-')[:8]}"
    cmd = [str(ROOT / "scripts" / "hub" / "with-org-db-env.sh"), str(ROOT / ".venv" / "bin" / "python"),
           "-m", "runners.coo_worker", tid]
    done = subprocess.run([TMUX, "new-session", "-d", "-s", name, "-c", str(ROOT),
                           " ".join(cmd) + f" 2>&1 | tee -a {ROOT}/state/coo-work/{tid}.tmux.log"],
                          capture_output=True, text=True)
    if done.returncode != 0:
        db.update_status(tid, "failed", actor="coo_dispatch",
                         report=f"tmux could not start the worker: {done.stderr.strip()[:300]}")
        return False
    db.update_status(tid, "in_progress", actor="coo_dispatch", tmux_session=name,
                     spawned_at=db.now_iso(), runner="coo_worker")
    _event(tid, "coo_dispatched", {"via": "coo_worker", "tmux": name})
    return True


def start_root_role(tid: str) -> bool:
    from tools import delegate
    result = asyncio.run(delegate.delegate_task(tid))
    _event(tid, "coo_dispatched", {"via": "delegate", "status": (result or {}).get("status")})
    return True


def dispatch_once(environ=None) -> None:
    reqs = delegate_requests()
    if not reqs:
        return
    if len(running()) >= MAX_WORKERS:
        return
    free = mem_available_mb()
    if free < MIN_FREE_MB:
        log.info("waiting: MemAvailable %s MB < %s MB", free, MIN_FREE_MB)
        return
    for req in reqs:
        tid, role = req["id"], req["role"]
        try:
            coo_policy.check_role(coo_policy.COO_ROLE, role)
        except coo_policy.CooRoleRefused as e:      # the gate and the hub refuse this first
            db.update_status(tid, "cancelled", actor="coo_dispatch", report=str(e))
            continue
        if role in ROOT_ROLES and not root_roles_on(environ):
            if not has_event(tid, "coo_dispatch_held"):
                _event(tid, "coo_dispatch_held", {
                    "why": f"{role} runs as root with a shell; it waits for its own box (CEO card "
                           "Q-20261013-2111-5ff5, COO_DISPATCH_ROOT_ROLES=1 overrides)"})
            continue
        if not tmux_server_up():
            log.warning("waiting: no tmux server; this unit must never start one")
            return
        started = start_researcher(tid) if role == "researcher" else start_root_role(tid)
        log.info("dispatch %s %s -> %s", tid, role, "started" if started else "not started")
        return                                       # one per tick; MAX_WORKERS is checked again


def close_once() -> None:
    for req in close_requests():
        try:
            payload = json.loads(req["payload"]) if isinstance(req["payload"], str) else (req["payload"] or {})
        except ValueError:
            payload = {}
        tmux_kill(req.get("tmux_session"))
        db.update_status(req["id"], "done", actor="coo_dispatch")
        record_fit(req["id"], result=payload.get("result") or "pass", why=payload.get("why") or "")


def reap_once(now: float | None = None) -> None:
    now = time.time() if now is None else now
    for t in running():
        if t["role"] != "researcher":
            continue                                 # delegate.py's own watchdog covers those
        started = _epoch(t.get("spawned_at") or t.get("updated_at"))
        age = now - started if started else 0
        if age > RUN_LIMIT_S:
            tmux_kill(t.get("tmux_session"))
            db.update_status(t["id"], "failed", actor="coo_dispatch",
                             report=f"timed out after {int(age // 60)} min")
            record_fit(t["id"], result="fail", fail_reason="timeout", why="ran past the limit")
        elif age > GONE_GRACE_S and not tmux_alive(t.get("tmux_session")):
            db.update_status(t["id"], "failed", actor="coo_dispatch",
                             report="the worker's tmux session ended without a report")
            record_fit(t["id"], result="fail", fail_reason="crash", why="worker exited without a report")


def fit_once() -> None:
    """A runner_fit for every coo task that ended without one (one per job, CEO brief)."""
    for t in _rows("SELECT t.id, t.status FROM tasks t WHERE t.owner_role = ? AND t.status IN ("
                   + ",".join("?" * len(ENDED)) + ") AND NOT EXISTS (SELECT 1 FROM events e "
                   "WHERE e.task_id = t.id AND e.kind = 'runner_fit')", (coo_policy.COO_ROLE, *ENDED)):
        if t["status"] == "done":
            record_fit(t["id"], result="pass", why="closed by the COO")
        else:
            record_fit(t["id"], result="fail", fail_reason="other", why=f"ended {t['status']}")


def record_fit(tid: str, *, result: str, fail_reason: str | None = None, why: str = "") -> None:
    from tools import runner_fit
    if result not in ("pass", "fail"):
        result = "pass"
    if result == "fail" and not fail_reason:
        fail_reason = "wrong"
    task = db.get_task(tid) or {}
    with db.get_conn() as conn:
        if conn.execute("SELECT 1 FROM events WHERE task_id = ? AND kind = 'runner_fit' LIMIT 1",
                        (tid,)).fetchone():
            return
        events = [dict(e) for e in runner_fit.status_events(conn, tid)]
        for e in events:
            if not isinstance(e["ts"], str):
                e["ts"] = e["ts"].isoformat()
        payload = runner_fit.from_task(task, events, job_type=JOB_TYPE.get(task.get("role"), "other"),
                                       result=result, fail_reason=fail_reason, why=why[:300],
                                       reviewer=coo_policy.COO_ROLE)
        runner_fit.record(conn, tid, "coo_dispatch", payload)


def _epoch(ts) -> float | None:
    if ts is None:
        return None
    if hasattr(ts, "timestamp"):
        return ts.timestamp()
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# ---------------------------------------------------------------------------------- C-level respawn

def live_hub_rows(host: str = coo_policy.COO_RESPAWN_HOST) -> list[dict]:
    """Return all live_sessions rows on `host` (both verified=1 and verified=0 name-only rows)."""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT host, uuid, sid, role, name, address, status, pid, seen_at, verified "
            "FROM live_sessions WHERE host = ?",
            (host,),
        ).fetchall()
    return [dict(r) for r in rows]


def live_row_claims_role(row: dict, role: str, host: str = coo_policy.COO_RESPAWN_HOST) -> str | None:
    """Return a refusal reason if a live_sessions row claims `role` by role, name, or tmux/sid."""
    if not isinstance(row, dict):
        return "unsure: malformed live_sessions row"
    row_host = str(row.get("host") or host).strip().lower()
    if row_host and row_host != host:
        return None
    row_role = str(row.get("role") or "").strip().lower()
    if row_role == role:
        return (f"live hub row already exists for role {role!r} on {host} "
                f"(name={row.get('name')!r}, verified={row.get('verified')})")
    name = str(row.get("name") or "").strip()
    if name:
        parsed = session_names.parse_short(name)
        if parsed and parsed[0] == role:
            return f"live hub row name {name!r} claims role {role!r}"
        role_up = role.upper()
        if f"{role_up} (" in name or re.search(
            rf"(?:^|[\s🟢🍎🪟]){re.escape(role_up)}(?:\s*\(|\s+#|\s+-|$)", name
        ):
            return f"live hub row name {name!r} claims role {role!r}"
    for key in ("address", "tmux_session", "sid"):
        val = str(row.get(key) or "").strip().lower()
        if not val:
            continue
        short = session_names.parse_short(val)
        if (short and short[0] == role) or val == role or val.startswith(f"{role}-"):
            return f"live hub row {key}={row.get(key)!r} claims role {role!r}"
    return None


def _done_respawn_request_ids() -> set[int]:
    done_ids: set[int] = set()
    for r in _rows("SELECT id, payload FROM events WHERE kind = ? ORDER BY id ASC", ("coo_respawn_done",)):
        raw = r.get("payload")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except ValueError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("request_id"), int):
            done_ids.add(int(payload["request_id"]))
    return done_ids


def respawn_requests() -> list[dict]:
    """Unprocessed coo_respawn_request events, oldest first."""
    done_ids = _done_respawn_request_ids()
    reqs = _rows("SELECT id, payload, ts FROM events WHERE kind = ? ORDER BY id ASC", ("coo_respawn_request",))
    return [r for r in reqs if int(r["id"]) not in done_ids]


def _respawn_done(
    request_id: int,
    *,
    role: str | None,
    host: str | None,
    ok: bool,
    mode: str | None = None,
    sid: str | None = None,
    uuid: str | None = None,
    reason: str = "",
) -> dict:
    payload = {
        "request_id": request_id,
        "role": role,
        "host": host,
        "ok": bool(ok),
        "started": bool(ok),
        "mode": mode,
        "sid": sid,
        "uuid": uuid,
        "reason": reason,
    }
    _event(None, "coo_respawn_done", payload)
    return payload


def latest_session_id(role: str, host: str = coo_policy.COO_RESPAWN_HOST) -> str | None:
    """Most recent session_id for `role` on `host` in c_level_sessions (ordered by spawned_at DESC)."""
    rows = _rows(
        "SELECT session_id FROM c_level_sessions "
        "WHERE role = ? AND (host = ? OR host IS NULL OR host = '') "
        "ORDER BY spawned_at DESC, session_id DESC LIMIT 1",
        (role, host),
    )
    if not rows:
        return None
    sid = str(rows[0].get("session_id") or "").strip()
    return sid or None


def resolve_resume_uuid(role: str, session_id: str) -> str | None:
    """Resolve `session_id` to a full Claude UUID via scripts/resolve-resume-id.sh as root."""
    try:
        r = subprocess.run(
            ["bash", str(ROOT / "scripts" / "resolve-resume-id.sh"), role, session_id],
            capture_output=True, text=True, cwd=str(ROOT),
        )
    except OSError:
        return None
    if r.returncode != 0:
        return None
    candidate = (r.stdout or "").strip()
    if UUID_RE.fullmatch(candidate):
        return candidate
    return None


def start_clevel(role: str, *, mode: str, sid: str, resume_uuid: str | None = None) -> tuple[bool, str]:
    """Start `scripts/cxo-claude.sh` in a detached tmux session `<role>-<sid>` on the shared server."""
    tmux_name = f"{role}-{sid}"
    launcher = f"bash {ROOT}/scripts/cxo-claude.sh --role {role}"
    if mode == "resume" and resume_uuid:
        launcher += f" -r {resume_uuid}"
    try:
        done = subprocess.run(
            [TMUX, "new-session", "-d", "-s", tmux_name, "-c", str(ROOT), launcher],
            capture_output=True, text=True,
        )
    except OSError as e:
        log.error("tmux start failed: %s", e)
        return False, f"tmux_start_error:{type(e).__name__}"
    if done.returncode != 0:
        log.error("tmux start failed: %s", done.stderr)
        return False, "tmux_start_failed"
    return True, f"{mode} session started in tmux {tmux_name}"


def respawn_once(*, now=None) -> list[dict]:
    """Consume unprocessed coo_respawn_request events and record coo_respawn_done for each."""
    reqs = respawn_requests()
    if not reqs:
        return []
    results: list[dict] = []
    for req in reqs:
        req_id = int(req["id"])
        raw_payload = req.get("payload")
        try:
            payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
        except ValueError:
            payload = None
        if not isinstance(payload, dict) or set(payload.keys()) != {"role", "host", "by_session"}:
            role_val = payload.get("role") if isinstance(payload, dict) else None
            host_val = payload.get("host") if isinstance(payload, dict) else None
            results.append(_respawn_done(
                req_id, role=role_val, host=host_val, ok=False,
                reason="invalid coo_respawn_request payload keys",
            ))
            continue
        role = str(payload.get("role") or "").strip()
        host = str(payload.get("host") or "").strip()
        try:
            coo_policy.check_respawn(role, host)
        except coo_policy.CooRoleRefused as e:
            results.append(_respawn_done(req_id, role=role, host=host, ok=False, reason=str(e)))
            continue

        results.append(_reserved_respawn(req_id, role, host, now=now))
    return results


def live_host_refusal(host, *, now=None):
    rows = _rows("SELECT published_at, error FROM live_hosts WHERE host = ?", (host,))
    if len(rows) != 1:
        return "live_host_missing"
    row = rows[0]
    stamp = coo_policy._parse_ts(row.get("published_at"))
    clock = coo_policy._parse_ts(now) if now is not None else coo_policy.datetime.now(coo_policy.timezone.utc)
    if row.get("error"):
        return "live_host_error"
    if stamp is None or clock is None or not 0 <= (clock - stamp).total_seconds() <= 180:
        return "live_host_stale"
    return None


_UUID_BYTES = re.compile(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def process_role_refusal(role, proc_root=Path("/proc"), locks_dir=None):
    """Refuse while any process of `role` runs. Two argv shapes count:
    - the launcher: the item `cxo-claude.sh` (any path) followed by `--role <role>`;
    - a claude that outlived its launcher: `--session-id <uuid>` where <uuid> is in a
      state/locks/<role>-*.uuid file (the launcher writes one per session).
    Reads cmdline only, never environ (secrets), and skips tmux processes: the shared server's
    own argv names the command it was started with."""
    locks_dir = LOCKS_DIR if locks_dir is None else locks_dir
    try:
        role_uuids = {p.read_bytes().strip().lower() for p in locks_dir.glob(f"{role}-*.uuid")}
        if any(not _UUID_BYTES.fullmatch(u) for u in role_uuids):
            return "lock_uuid_invalid"  # an empty or garbled lock could hide a live claude
        for pid in proc_root.iterdir():
            if not pid.name.isdigit():
                continue
            try:
                comm = (pid / "comm").read_bytes().strip()
                argv = (pid / "cmdline").read_bytes().split(b"\0")
            except OSError:
                if not pid.exists():
                    continue
                raise
            if comm.startswith(b"tmux"):
                continue
            if role_uuids and any(argv[i] == b"--session-id" and argv[i + 1].lower() in role_uuids
                                  for i in range(len(argv) - 1)):
                return "process_role_alive"
            launcher = [i for i, a in enumerate(argv) if a.rsplit(b"/", 1)[-1] == b"cxo-claude.sh"]
            if not launcher:
                continue
            rest = argv[launcher[0] + 1:]
            if any(rest[i] == b"--role" and rest[i + 1] == role.encode() for i in range(len(rest) - 1)):
                return "process_role_alive"
    except OSError as exc:
        log.exception("Cannot inspect process environment")
        return f"proc_read_error:{type(exc).__name__}"
    return None


def _reserved_respawn(req_id, role, host, *, now=None):
    try:
        LOCKS_DIR.mkdir(parents=True, exist_ok=True)
        reservation = (LOCKS_DIR / f"coo-respawn-{role}.lock").open("a")
    except OSError as exc:
        return _respawn_done(req_id, role=role, host=host, ok=False,
                             reason=f"reservation_error:{type(exc).__name__}")
    with reservation:
        try:
            fcntl.flock(reservation, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            return _respawn_done(req_id, role=role, host=host, ok=False,
                                 reason=f"reservation_busy:{type(exc).__name__}")
        # Serialize across roles as well, so concurrent dispatchers cannot exceed the global cap.
        try:
            daily_lock = (LOCKS_DIR / "coo-respawn-global.lock").open("a")
        except OSError as exc:
            return _respawn_done(req_id, role=role, host=host, ok=False,
                                 reason=f"reservation_error:{type(exc).__name__}")
        with daily_lock:
            try:
                fcntl.flock(daily_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                return _respawn_done(req_id, role=role, host=host, ok=False,
                                     reason=f"reservation_busy:{type(exc).__name__}")
            # Another dispatcher may have handled this request while we waited to run.
            if req_id in _done_respawn_request_ids():
                return {"request_id": req_id, "ok": False, "reason": "already_processed"}
            try:
                reason = live_host_refusal(host, now=now) or process_role_refusal(role)
                if reason:
                    return _respawn_done(req_id, role=role, host=host, ok=False, reason=reason)
                return _respawn_checked(req_id, role, host, now=now)
            except Exception as exc:
                log.exception("C-level respawn check failed")
                return _respawn_done(req_id, role=role, host=host, ok=False,
                                     reason=f"respawn_error:{type(exc).__name__}")


def _respawn_checked(req_id, role, host, *, now=None):
    # Rate limits: one per role per 10 min and three globally per Bangkok day.
    all_reqs = _rows(
        "SELECT id, kind, payload, ts FROM events WHERE kind IN (?, ?) ORDER BY id ASC",
        ("coo_respawn_request", "coo_respawn_done"),
    )
    prior_reqs = [
        r for r in all_reqs
        if r["kind"] == "coo_respawn_done" or int(r["id"]) < req_id
    ]
    rate_reason = coo_policy.respawn_rate_limit_reason(prior_reqs, role, now=now)
    if rate_reason:
        return _respawn_done(req_id, role=role, host=host, ok=False, reason=rate_reason)


    # (a) No live hub row (verified OR name-only) whose role is `role` on contabo, and no live
    #     row's name or tmux session claims `role`. When unsure, refuse.
    try:
        hub_rows = live_hub_rows(host)
    except Exception as e:
        log.exception("Could not read live_sessions")
        return _respawn_done(
            req_id, role=role, host=host, ok=False,
            reason=f"live_sessions_read_error:{type(e).__name__}",
        )

    if not isinstance(hub_rows, list):
        return _respawn_done(
            req_id, role=role, host=host, ok=False,
            reason="unsure: live_sessions returned non-list data",
        )

    claim_reason = None
    for row in hub_rows:
        claim_reason = live_row_claims_role(row, role, host)
        if claim_reason:
            break
    if claim_reason:
        return _respawn_done(req_id, role=role, host=host, ok=False, reason=claim_reason)


    # (b) Launcher's single-role flock state/locks/.single-<role>.flock is NOT held.
    if single_role_flock_held(role):
        return _respawn_done(
            req_id, role=role, host=host, ok=False,
            reason=f"single-role flock state/locks/.single-{role}.flock is held",
        )


    # (c) Shared tmux server is up and no tmux session `<role>-*` exists in it.
    sessions = tmux_sessions()
    if sessions is None:
        return _respawn_done(
            req_id, role=role, host=host, ok=False,
            reason="unsure: shared tmux server is not running or unreachable",
        )

    existing_tmux = next(
        (s for s in sessions if s == role or s.startswith(f"{role}-")),
        None,
    )
    if existing_tmux is not None:
        return _respawn_done(
            req_id, role=role, host=host, ok=False,
            reason=f"tmux session {existing_tmux!r} already exists in the shared server",
        )


    # Resolve resume UUID for the role's most recent c_level_sessions row, or mint fresh id8.
    prev_sid = latest_session_id(role, host)
    resolved_uuid = resolve_resume_uuid(role, prev_sid) if prev_sid else None
    if resolved_uuid:
        mode = "resume"
        sid = resolved_uuid.replace("-", "")[-8:].lower()
    else:
        mode = "fresh"
        sid = uuid.uuid4().hex[:8]
    ok, reason = start_clevel(role, mode=mode, sid=sid, resume_uuid=resolved_uuid)
    return _respawn_done(
        req_id,
        role=role,
        host=host,
        ok=ok,
        mode=mode if ok else None,
        sid=sid if ok else None,
        uuid=resolved_uuid if ok else None,
        reason=reason,
    )


def tick(environ=None) -> None:
    for step in (close_once, reap_once, fit_once, respawn_once, lambda: dispatch_once(environ)):
        try:
            step()
        except Exception:
            log.exception("step failed")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s coo_dispatch %(levelname)s %(message)s")
    if os.geteuid() != 0:
        log.error("runs as root (it starts workers as root, CEO card Q-20261013-2010-091c)")
        return 2
    if not os.environ.get("ORG_DB_URL"):
        log.error("ORG_DB_URL is not set: start through scripts/hub/with-org-db-env.sh")
        return 2
    (ROOT / "state" / "coo-work").mkdir(parents=True, exist_ok=True)
    once = argv == ["--once"]
    log.info("started: root roles %s", "on" if root_roles_on() else "held")
    while True:
        tick()
        if once:
            return 0
        time.sleep(POLL_S)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
