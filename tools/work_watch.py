"""Work/ watcher — Work/RULES.md rules 7-8, ADR 0030 §D (task-dbe47b9b).

Runs once per `runners/watchdog.py`'s `scan_once` tick (the launchd job
`com.mooniex.agents-watchdog` drives that loop). For every Work/<task-id>/
folder that is either:

  (a) an orphan per `tools.workdir.orphans()` — task done/merged/cancelled/
      failed, or absent from tasks.db entirely ("unknown"), OR
  (b) `in_progress` but its recorded worker pid is no longer alive — never
      caught by (a), since `tools.workdir._ORPHAN_STATUSES`
      (tools/workdir.py:52) never includes "in_progress",

`watch()` does exactly one of:

  - the owning CTO/CXO session is alive — `tools.session_cap.live_sessions()`
    (tools/session_cap.py:76-103): a lock file under `state/locks/
    <role>-<id>.lock` whose recorded pid still answers `kill(pid, 0)`. The
    lock basename is `tools.session_name.lock_basename(role, id)`
    (tools/session_name.py:56), the single derivation both the lock file and
    the tmux session name share. → `tools.send_to_cto.send()` one line:
    folder, bytes, what is unfiled.
  - the owner is gone (or the task was never owned) → ONE LungNote to-do at
    Critical priority, due today, created the same way
    `tools/skill_objection.py:64-75` already writes one: a subprocess JSON-RPC
    call to the LungNote MCP server via `scripts/lib/mcp_call.py --server
    lungnote --tool add_todo` — never importing LungNote's own code (IRON
    §54: projects talk only through APIs). That server is `node
    /Users/gob/MoonieXHQ/Projects/LungNote/Mcp/index.js`
    (config/cto.mcp.json:11-15, scripts/lib/cxo_mcp_config.py's `_build()`
    "lungnote" branch) — its credential lives in that checkout's own
    `/Users/gob/MoonieXHQ/Projects/LungNote/Mcp/.env`, never passed through
    `cxo_mcp_config` (whose lungnote entry carries `env: {}`) and never read
    or printed by this file. `mcp__lungnote__add_todo`'s schema is
    `{text, due_at, due_text, note_id, note_title}` — no priority field — so
    "Critical" is encoded as a `[CRITICAL]` prefix in `text`, the same
    bracket-tag idiom `tools/skill_objection.py:89` already uses
    (`[skill objection -> {author}] ...`).

Rate-limited to once per folder per 24h (`state/work_watch_state.json`) so a
5-minute watchdog tick doesn't re-alert or re-file constantly. The LungNote
to-do is deduped by folder for good — `lungnote_todo` in that state file is
set once and never triggers a second `add_todo` call for the same folder,
even after the 24h window reopens (dedupe is permanent, alerts are not).

Green listing (rule 8 / `work_dir.abandon_days`, default 14 days) is
`tools.workdir.orphans()`'s own `green` field (added alongside this file,
task-dbe47b9b): a folder whose task ended `abandon_days` days ago has been
`flagged` (the >24h test) for far longer than one alert cycle, so by
construction this watcher has already alerted or filed for it at least once
by the time it turns Green. `watch()` only logs the candidate — never
deletes anything; deletion stays a human/CTO act via
`workdir.py close --archive`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db  # noqa: E402
from lib.notify import info, warn  # noqa: E402
from tools import send_to_cto  # noqa: E402
from tools import session_cap  # noqa: E402
from tools import session_name  # noqa: E402
from tools import workdir  # noqa: E402
from tools.gc_stale_tasks import _alive_for_gc  # noqa: E402
from tools.worker_reap import _pid_alive  # noqa: E402

STATE_PATH = ROOT / "state" / "work_watch_state.json"
MCP_CALL = ROOT / "scripts" / "lib" / "mcp_call.py"
ALERT_INTERVAL_S = 24 * 3600


def _load_state(path: Path | None = None) -> dict:
    p = path or STATE_PATH
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict, path: Path | None = None) -> None:
    p = path or STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _owner_alive(owner_cto: str | None, owner_role: str | None,
                  live_sessions: list[str]) -> bool:
    """tools/session_cap.py:76 `live_sessions()` is the org's existing
    C-level liveness check. An ownerless task (`owner_cto` falsy) has nobody
    to alert and falls straight to the LungNote branch."""
    if not owner_cto:
        return False
    basename = session_name.lock_basename(owner_role or "cto", owner_cto)
    return basename in live_sessions


def _add_lungnote_todo(text: str, due_at: str, *,
                       mcp_call: Path | None = None) -> bool:
    """Fail-open, same contract as tools/skill_objection.py:64-75 — a
    LungNote outage must never crash the watchdog's scan_once tick."""
    try:
        r = subprocess.run(
            [sys.executable, str(mcp_call or MCP_CALL),
             "--server", "lungnote", "--root", str(ROOT),
             "--tool", "add_todo",
             "--args", json.dumps({"text": text, "due_at": due_at})],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0
    except Exception as e:
        warn(f"work_watch: lungnote add_todo failed: {e}")
        return False


def _pid_dead_in_progress(task: dict) -> bool:
    """True only when `task` is provably dead: a recorded pid that no longer
    answers on its host. No pid, or an unreachable remote host
    (`_alive_for_gc` returns None), must never read as dead."""
    pid = task.get("pid")
    if not pid:
        return False
    host = task.get("host") or "mac"
    if host == "mac":
        return not _pid_alive(pid)
    return _alive_for_gc(task) is False


def _folder_stats(task_id: str, root=None) -> tuple[int, list[str]]:
    """(total bytes, unfiled relative paths) for Work/<task_id>/. Reuses
    `tools.workdir.close(dry_run=True)` for the unfiled list rather than
    re-walking SOURCES.txt coverage a second time."""
    folder = workdir.folder_path(task_id, root=root)
    total = sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())
    try:
        dry = workdir.close(task_id, dry_run=True, root=root)
        unfiled = dry.get("unfiled", [])
    except FileNotFoundError:
        unfiled = []
    return total, unfiled


def _candidates(db_path, root=None) -> list[dict]:
    """Work/ folders needing a watcher decision this tick: `workdir.orphans()`
    (done/merged/cancelled/failed/unknown) plus `in_progress` folders whose
    recorded pid is dead — never covered by `orphans()`, whose
    `_ORPHAN_STATUSES` (tools/workdir.py:52) never includes "in_progress"."""
    out = list(workdir.orphans(db_path, root=root))
    seen = {c["task"] for c in out}
    for t in db.list_tasks(status="in_progress", limit=500):
        if t["id"] in seen:
            continue
        if not (workdir.folder_path(t["id"], root=root)).is_dir():
            continue
        if _pid_dead_in_progress(t):
            out.append({"task": t["id"], "status": "in_progress",
                       "updated_at": t.get("updated_at"), "age_hours": None,
                       "flagged": True, "green": False})
    return out


def watch(*, root=None, db_path=None, state_path: Path | None = None,
          now: datetime | None = None, mcp_call: Path | None = None) -> dict:
    """One watcher pass. Returns `{"alerted": [...], "lungnote_filed": [...],
    "green": [...]}` — task ids, for the caller's log line."""
    now = now or datetime.now(timezone.utc)
    db_path = db_path or str(db.DB_PATH)
    state = _load_state(state_path)
    alerted: list[str] = []
    filed: list[str] = []
    green: list[str] = []

    live = session_cap.live_sessions()

    for cand in _candidates(db_path, root=root):
        task_id = cand["task"]
        if not cand.get("flagged"):
            continue

        if cand.get("green"):
            info(f"work_watch: Work/{task_id} is a disk-hygiene Green "
                 f"candidate (work_dir.abandon_days elapsed) — archive via "
                 f"`workdir.py close --archive`, never auto-deleted")
            green.append(task_id)

        entry = state.get(task_id, {})
        last = entry.get("last_checked_at")
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
            except ValueError:
                last_dt = None
            if last_dt is not None and (now - last_dt).total_seconds() < ALERT_INTERVAL_S:
                continue  # rate-limited: already checked this folder <24h ago

        task = db.get_task(task_id) or {}
        owner_cto = task.get("owner_cto")
        owner_role = task.get("owner_role")
        total_bytes, unfiled = _folder_stats(task_id, root=root)

        if _owner_alive(owner_cto, owner_role, live):
            msg = (f"Work/{task_id} orphaned (status={cand['status']}) — "
                   f"{total_bytes} bytes, {len(unfiled)} unfiled file(s)")
            try:
                ok = send_to_cto.send(
                    task_id, msg, role=task.get("role"),
                    cto_id=owner_cto, owner_role=owner_role or "cto",
                )
            except Exception as e:
                warn(f"work_watch: send_to_cto failed for {task_id}: {e}")
                ok = False
            if ok:
                alerted.append(task_id)
        elif not entry.get("lungnote_todo"):
            due_at = now.date().isoformat() + "T00:00:00+00:00"
            text = (f"[CRITICAL] Work/{task_id} orphaned, owner session "
                    f"gone — {total_bytes} bytes, {len(unfiled)} unfiled "
                    f"file(s), status={cand['status']}. Reclaim via "
                    f"`workdir.py close --archive` or hand off the task.")
            if _add_lungnote_todo(text, due_at, mcp_call=mcp_call):
                entry["lungnote_todo"] = True
                filed.append(task_id)

        entry["last_checked_at"] = now.isoformat(timespec="seconds")
        state[task_id] = entry

    _save_state(state, state_path)
    return {"alerted": alerted, "lungnote_filed": filed, "green": green}


def main() -> int:
    db.init()
    result = watch()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
