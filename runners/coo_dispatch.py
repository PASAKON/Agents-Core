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
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import coo_policy, db  # noqa: E402

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


def tick(environ=None) -> None:
    for step in (close_once, reap_once, fit_once, lambda: dispatch_once(environ)):
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
