"""GC stale tasks.

Run periodically (suggest 10 min interval). Marks tasks as 'cancelled' if:

  1. status='pending' AND created_at older than STALE_PENDING_MINUTES
     AND assigned_agent IS NULL  (never delegated successfully)
  1b. status='pending' AND assigned_agent IS NOT NULL AND
     spawned_at/created_at older than STALE_SPAWNED_PENDING_MINUTES AND
     the DEV process is provably dead (never flipped to in_progress —
     W3 Bug B: category 1's `assigned_agent is not None` guard used to
     skip these forever)
  2. status='conflict' AND updated_at older than STALE_CONFLICT_MINUTES
     (caller hasn't retried — lock is dead weight)
  3. status='rate_limited' AND retry_after_ts in the past by >
     STALE_RATELIMIT_MINUTES (caller gave up)

Releases path locks held by cancelled tasks. Also runs
release_terminal_task_locks(), a separate pass that releases locks for
any task that reached a terminal status (or 'review') outside
db.update_status — e.g. a status written directly to the row, which never
fires lib/db.py's RELEASING_STATUSES release (W3 Bug A) — and deletes any
lock row whose owner isn't a task at all.

Idempotent. Safe to run concurrently with other CTOs (uses a single UPDATE
with a WHERE clause that re-checks the same predicates).

W1.5 (shared ledger): each category acts only on rows this box owns. 1 (the
disk_queue exemption and the pid check read THIS box's queue file and process
table) takes `is_local_row` rows; 1b and 3 take local rows plus remote rows
this box dispatched (`_alive_for_gc` asks over ssh, and reads None -- never
act -- for any other row); 2 takes rows this box dispatched. A row that is
not ours is skipped, never cancelled.

`--reap` is a separate mode (dry run unless `--go`): it removes the worktrees
of finished tasks. It is the standing op behind deploy/systemd/
org-worktree-reap.timer on Contabo, so every condition it needs before it
removes anything is listed in reap_worktrees().
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.config import host as get_host, self_host
from runners.branch_poller import remote_pid_alive
from tools import disk_queue, budget_queue
from tools import worktree as worktree_mod
from tools.worker_reap import (_pid_alive, is_dispatched_here, is_local_row,
                               is_remote_row, row_host)
from tools.worktree import remove_worktree

STALE_PENDING_MINUTES         = 30
STALE_CONFLICT_MINUTES        = 60
STALE_RATELIMIT_MINUTES       = 30
STALE_SPAWNED_PENDING_MINUTES = 120

# Statuses whose worktree is dead weight and can be reclaimed. Includes
# 'merged': audited 2026-08-07 (W6, org:reference/2026-08-06-agents-system-
# audit.md) — merge_task()'s success path has only ever written 'done'
# (tools/git_ops.py:342-347, true since the original commit), and no other
# call site in the repo or its full git history writes status='merged' via
# update_status(). It is a legacy value declared in db.VALID_STATUS and
# treated as done-equivalent by several read-only checks (lib/reflect.py,
# lib/recall.py, tools/delegate.py, tools/revert_task.py) but produced by no
# code path — the one live example (task-df93e0ed) has no status_* event for
# the transition, meaning it was hand-set directly in the DB outside any
# tool, not written by the app. Safe to treat as terminal like 'done'.
# Still excludes 'reverted'/'blocked_human' (still needs a human look).
TERMINAL_STATUSES = {"done", "cancelled", "stalled", "failed", "merged"}

# Statuses whose owning task is done touching its paths — used by
# release_terminal_task_locks. TERMINAL_STATUSES plus 'review': a task in
# review is out of the DEV's hands even though it isn't terminal yet, same
# rationale as lib/db.py's RELEASING_STATUSES (which this file doesn't
# import — lib/db.py is out of scope for this task, so the set is
# duplicated here rather than reused).
LOCK_RELEASE_STATUSES = TERMINAL_STATUSES | {"review"}

# 'review' worktrees older than this are flagged (print-only) unless their
# HEAD is already in origin/<base> (--reap then removes them: the PR is merged
# and only the row is stale) — an unmerged one is never auto-removed, since a
# human may still be about to look at it.
REVIEW_STALE_DAYS = 21

# --reap (CEO 2026-10-27, task-3a803be1). Untracked files the runner itself
# leaves in a finished worktree: at the worktree root, plus anything under
# docs/reports/<task-id>/. They do not make a worktree dirty. Anything else,
# tracked or untracked, does.
RUNNER_ROOT_FILES = frozenset({
    "REPORT.md", "BLOCKER.md", "PR_BODY.md", "WORKER.md", "TASK.md",
    "CTO-FEEDBACK.md", ".org-task.json", ".media_blockers",
})
RUNNER_HASH_LIMIT = 1024 * 1024     # bytes of each runner file that get hashed
GIT_TIMEOUT_S = 120
FETCH_TIMEOUT_S = 180
# A /proc/<pid>/cwd this process may not read (another uid, so not root) means
# "cannot say nobody is in there": fail closed. Only the tests relax it, for a
# non-root CI user.
CWD_UNREADABLE_BLOCKS = True
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MB = 1024 * 1024


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _age_minutes(ts: str | None) -> float | None:
    dt = _parse_ts(ts)
    if dt is None:
        return None
    return (_now() - dt).total_seconds() / 60


def _worktree_git_status(wt: Path) -> str | None:
    """`git status --porcelain` output for wt, or None if it can't be
    determined (missing dir, not a git worktree, git error). Callers must
    treat None as 'unknown — do not remove'."""
    if not wt.exists():
        return None
    r = subprocess.run(["git", "status", "--porcelain"], cwd=str(wt),
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return r.stdout


def _reclaim_worktree(task: dict, *, dry_run: bool) -> dict | None:
    """Remove a terminal-status task's worktree unless it's dirty or missing.

    Reuses tools.worktree.remove_worktree — never reimplements the git
    plumbing. Returns None when there's nothing to reclaim (no worktree
    recorded, or the path is already gone). Otherwise a dict with an
    `action` of 'removed' / 'would_remove' / 'skipped_dirty' /
    'skipped_unverifiable' / 'error'.
    """
    wt_str = task.get("worktree")
    if not wt_str:
        return None
    wt = Path(wt_str)
    if not wt.exists():
        return None

    status = _worktree_git_status(wt)
    if status is None:
        print(f"[gc] skip worktree reclaim for {task['id']}: "
              f"can't verify git status at {wt}", file=sys.stderr)
        return {"task_id": task["id"], "worktree": wt_str,
                "action": "skipped_unverifiable"}
    if status.strip():
        print(f"[gc] skip worktree reclaim for {task['id']}: "
              f"uncommitted changes at {wt}", file=sys.stderr)
        return {"task_id": task["id"], "worktree": wt_str,
                "action": "skipped_dirty"}

    if dry_run:
        return {"task_id": task["id"], "worktree": wt_str,
                "action": "would_remove"}

    try:
        remove_worktree(task["project"], task["role"], task["id"])
        if wt.exists():
            raise RuntimeError(f"worktree still exists after removal: {wt}")
        db.set_fields(task["id"], worktree=None, actor="gc_stale_tasks")
        print(f"[gc] removed worktree for {task['id']}: {wt}", file=sys.stderr)
        return {"task_id": task["id"], "worktree": wt_str, "action": "removed"}
    except Exception as e:
        print(f"[gc] failed to remove worktree for {task['id']}: {e}",
              file=sys.stderr)
        return {"task_id": task["id"], "worktree": wt_str,
                "action": "error", "error": str(e)}


def _alive_for_gc(t: dict) -> bool | None:
    """True/False/None liveness for the process behind task `t`, dispatched
    by ownership (W1.5): a local row (host == self) is checked with kill(pid,
    0); a remote row this box dispatched is asked over ssh; a row that is
    neither is another box's business and reads None. None means "couldn't
    determine — do not act", matching remote_pid_alive's own contract; a local
    check never returns None since kill(pid, 0) is always answerable (no pid
    included — _pid_alive(None) is False).
    """
    if is_local_row(t):
        return _pid_alive(t.get("pid"))
    if not is_remote_row(t):
        return None
    pid = t.get("pid")
    if not pid:
        return False
    try:
        host_cfg = get_host(row_host(t))
    except ValueError:
        return None
    return remote_pid_alive(host_cfg, pid)


def gc_stale_tasks(
    *,
    pending_minutes: int = STALE_PENDING_MINUTES,
    conflict_minutes: int = STALE_CONFLICT_MINUTES,
    ratelimit_minutes: int = STALE_RATELIMIT_MINUTES,
    dry_run: bool = False,
) -> list[dict]:
    """Sweep for stale tasks and cancel them. Returns list of affected entries."""
    cancelled: list[dict] = []

    # Category 1: pending tasks never delegated (no assigned_agent)
    for t in db.list_tasks(status="pending", limit=500):
        if t.get("assigned_agent") is not None:
            continue
        # W1.5: the pid check below reads THIS box's process table, and the
        # disk_queue exemption reads THIS box's queue file -- so only a row
        # that belongs here (an unspawned row belongs to its dispatcher).
        if not is_local_row(t):
            continue
        # ADR 0030 §D (task-dbe47b9b): a task sitting in tools/disk_queue.py's
        # FIFO queue (tools/delegate.py's disk_floor refusal path) is
        # deliberately pending with no assigned_agent for as long as the
        # disk stays below the floor — runners/watchdog.py's scan_once drain
        # is what eventually spawns it, not this GC. Without this exemption
        # the 30-minute floor below would cancel it long before space
        # returns; disk_queue.pop() is what actually drops a queued entry
        # once its task is cancelled/closed elsewhere.
        if disk_queue.is_queued(t["id"]) or budget_queue.is_queued(t["id"]):
            continue
        # Never reap a task whose DEV is still running. A task stays
        # 'pending' for the whole spawn window — dev_init flips it to
        # in_progress only once it claims — so a live spawn sits squarely
        # inside this sweep's kill zone. Cancelling it is bad enough;
        # _reclaim_worktree below then deletes the worktree out from under
        # a process still working in it, and its only guard is `git status`
        # being non-empty, which a DEV that has not committed yet fails.
        #
        # Measured 2026-08-13 00:26: task-7d4b567b, pid 47128 observed in
        # state R+ (running, consuming CPU), cancelled ~30s after delegate.
        # See GH #52.
        if _pid_alive(t.get("pid")):
            continue
        # Measure from the spawn, not from row creation. `created_at` is
        # when create_task ran, which says nothing about how long the task
        # has been abandoned: a task created at 23:50 and delegated at
        # 00:25 was already 35 minutes "stale" the instant its DEV started.
        #
        # spawned_at is NULL for a task that genuinely was never delegated
        # — exactly what this category exists to catch — so fall back to
        # created_at only in that case.
        age = _age_minutes(t.get("spawned_at") or t.get("created_at"))
        if age is None or age <= pending_minutes:
            continue
        print(f"[gc] cancelled {t['id']} (stale pending >{pending_minutes}min)",
              file=sys.stderr)
        entry: dict = {
            "task_id": t["id"], "project": t["project"],
            "kind": "pending", "age_min": round(age, 1),
        }
        if not dry_run:
            db.update_status(
                t["id"], "cancelled", actor="gc_stale_tasks",
                report=f"gc: stale pending >{pending_minutes}min without assignment",
            )
            entry["locks_released"] = db.release_task_locks(t["id"], t["project"])
        entry["worktree_reclaim"] = _reclaim_worktree(t, dry_run=dry_run)
        cancelled.append(entry)

    # Category 1b: pending tasks that WERE delegated (assigned_agent set)
    # but whose DEV process is provably dead — W3 Bug B. Category 1 above
    # skips these forever via its `assigned_agent is not None` guard, so a
    # spawn that died before ever reaching in_progress held its locks for
    # good (measured: task-8b6625ff, 26 days, 17 locks).
    #
    # 120-minute floor, not 30: this sits on top of Category 1's own spawn-
    # window protection (the _pid_alive live-process check), so the extra
    # margin is purely about giving a slow-to-report spawn room, not about
    # racing a delegate that hasn't started yet.
    for t in db.list_tasks(status="pending", limit=500):
        if t.get("assigned_agent") is None:
            continue
        age = _age_minutes(t.get("spawned_at") or t.get("created_at"))
        if age is None or age <= STALE_SPAWNED_PENDING_MINUTES:
            continue
        alive = _alive_for_gc(t)
        if alive is not False:  # True (running) or None (unknown) — never act
            continue
        print(f"[gc] cancelled {t['id']} (stale spawned pending "
              f">{STALE_SPAWNED_PENDING_MINUTES}min, no live process)",
              file=sys.stderr)
        # Read-only count up front so --dry-run reports the lock count too
        # (not just which tasks would be cancelled) — the whole point of a
        # dry-run for a bug about locks is seeing the lock numbers before
        # committing to releasing them.
        with db.get_conn() as conn:
            lock_n = conn.execute(
                "SELECT COUNT(*) c FROM locks WHERE owner=? AND key LIKE ?",
                (t["id"], f"proj:{t['project']}:path:%"),
            ).fetchone()["c"]
        entry = {
            "task_id": t["id"], "project": t["project"],
            "kind": "spawned_pending", "age_min": round(age, 1),
            "locks_released": lock_n,
        }
        if not dry_run:
            db.update_status(
                t["id"], "cancelled", actor="gc_stale_tasks",
                report=(f"gc: stale spawned pending "
                        f">{STALE_SPAWNED_PENDING_MINUTES}min, no live "
                        f"process (host={t.get('host') or self_host()})"),
            )
            # update_status already released these locks — 'cancelled' is
            # in lib/db.py's RELEASING_STATUSES. This call is a no-op safety
            # net (always returns 0 here), so entry keeps the pre-release
            # lock_n above rather than being overwritten with that 0.
            db.release_task_locks(t["id"], t["project"])
        entry["worktree_reclaim"] = _reclaim_worktree(t, dry_run=dry_run)
        cancelled.append(entry)

    # Category 2: conflict tasks whose caller gave up retrying
    for t in db.list_tasks(status="conflict", limit=500):
        # W1.5: no process to probe, only a status flip -- the dispatcher, whose
        # caller gave up retrying, is the one owner.
        if not is_dispatched_here(t):
            continue
        age = _age_minutes(t.get("updated_at"))
        if age is None or age <= conflict_minutes:
            continue
        print(f"[gc] cancelled {t['id']} (stale conflict >{conflict_minutes}min)",
              file=sys.stderr)
        entry = {
            "task_id": t["id"], "project": t["project"],
            "kind": "conflict", "age_min": round(age, 1),
        }
        if not dry_run:
            db.update_status(
                t["id"], "cancelled", actor="gc_stale_tasks",
                report=f"gc: stale conflict >{conflict_minutes}min, caller gave up",
            )
            entry["locks_released"] = db.release_task_locks(t["id"], t["project"])
        entry["worktree_reclaim"] = _reclaim_worktree(t, dry_run=dry_run)
        cancelled.append(entry)

    # Category 3: rate_limited tasks whose retry_after_ts is overdue
    for t in db.list_tasks(status="rate_limited", limit=500):
        rev = t.get("review")
        if rev:
            if isinstance(rev, dict) and rev.get("quota_stop"):
                continue
            if isinstance(rev, str):
                try:
                    parsed_rev = json.loads(rev)
                    if isinstance(parsed_rev, dict) and parsed_rev.get("quota_stop"):
                        continue
                except ValueError:
                    pass
        # W1.5: _alive_for_gc reads None ("not ours") and this branch cancels on
        # anything but a definite True, so a row that is neither local nor
        # dispatched here must be skipped before the liveness call.
        if not (is_local_row(t) or is_remote_row(t)):
            continue
        rat = _parse_ts(t.get("retry_after_ts"))
        if rat is not None:
            overdue_min = (_now() - rat).total_seconds() / 60
            if overdue_min <= ratelimit_minutes:
                continue
        else:
            # No retry_after_ts recorded — fall back to updated_at age
            age = _age_minutes(t.get("updated_at"))
            if age is None or age <= ratelimit_minutes:
                continue
        # A rate limit is not a death. `retry_after` is what the API says it
        # will accept next, not when the underlying allowance clears: a WEEKLY
        # Claude quota reports retry_after=300s and then keeps refusing, so
        # this branch fires on a worker that is alive and correctly waiting.
        # On 2026-09-19 it cancelled task-2e5cd54e mid-episode and reclaimed
        # its worktree; four commits survived only because git had them.
        # Every other category here already checks liveness before acting.
        alive = _alive_for_gc(t)
        if alive is True:
            print(f"[gc] keeping {t['id']} — rate_limited but its process is alive "
                  f"(pid {t.get('pid')}); a waiting worker is not a stale one",
                  file=sys.stderr)
            continue
        print(f"[gc] cancelled {t['id']} (stale rate_limited >{ratelimit_minutes}min, process not alive)",
              file=sys.stderr)
        entry = {
            "task_id": t["id"], "project": t["project"],
            "kind": "rate_limited",
            "retry_after_ts": t.get("retry_after_ts"),
        }
        if not dry_run:
            db.update_status(
                t["id"], "cancelled", actor="gc_stale_tasks",
                report=(f"gc: rate_limited overdue >{ratelimit_minutes}min, "
                        f"retry_after_ts={t.get('retry_after_ts')}"),
            )
            entry["locks_released"] = db.release_task_locks(t["id"], t["project"])
        entry["worktree_reclaim"] = _reclaim_worktree(t, dry_run=dry_run)
        cancelled.append(entry)

    # W3 Bug A: locks held by a task whose status went terminal (or
    # 'review') outside db.update_status never got released. Same returned
    # list — runners/watchdog.py:620 already calls gc_stale_tasks() and
    # logs len(result), so this rides along with no watchdog edit.
    cancelled.extend(release_terminal_task_locks(dry_run=dry_run))

    return cancelled


def release_terminal_task_locks(dry_run: bool = False) -> list[dict]:
    """Release path locks whose owning task is done touching its paths, and
    delete lock rows that belong to no task row at all.

    Bug A (W3): lib/db.py's update_status releases locks via
    RELEASING_STATUSES, but only when the status transition goes through
    that function. A status written directly to the row (measured: 8 'done'
    owners, 24 lock rows, zero status_done event in their history) never
    fires that release, and nothing else in the codebase cleans it up.

    Uses raw SQL against db.get_conn() (the same inline-SQL idiom
    _all_tasks_with_worktree already uses above) rather than a new
    lib/db.py helper — lib/db.py is out of scope for this task.
    """
    released: list[dict] = []
    with db.get_conn() as conn:
        owners = [r["owner"] for r in conn.execute(
            "SELECT DISTINCT owner FROM locks WHERE key LIKE 'proj:%:path:%'"
        ).fetchall()]

    for owner in owners:
        t = db.get_task(owner)

        if t is None:
            with db.get_conn() as conn:
                n = conn.execute(
                    "SELECT COUNT(*) c FROM locks WHERE owner=?", (owner,)
                ).fetchone()["c"]
            if n == 0:
                continue
            print(f"[gc] deleted {n} orphan lock(s) for owner={owner} "
                  f"(no task row)", file=sys.stderr)
            entry = {"task_id": owner, "kind": "orphan_lock",
                     "locks_released": n}
            if not dry_run:
                with db.get_conn() as conn:
                    conn.execute("DELETE FROM locks WHERE owner=?", (owner,))
            released.append(entry)
            continue

        if t["status"] not in LOCK_RELEASE_STATUSES:
            continue

        with db.get_conn() as conn:
            n = conn.execute(
                "SELECT COUNT(*) c FROM locks WHERE owner=? AND key LIKE ?",
                (owner, f"proj:{t['project']}:path:%"),
            ).fetchone()["c"]
        if n == 0:
            continue
        print(f"[gc] released {n} lock(s) for {owner} "
              f"(terminal status={t['status']})", file=sys.stderr)
        entry = {
            "task_id": owner, "project": t["project"], "status": t["status"],
            "kind": "terminal_locks",
            "locks_released": n if dry_run else db.release_task_locks(
                owner, t["project"]),
        }
        released.append(entry)

    return released


@contextmanager
def _read_tasks():
    if db.pg_url():
        with db.get_conn(readonly=True) as conn:
            yield conn
    else:
        # Quote '#' and '?' in paths (hostile filenames in the reaper tests).
        conn = sqlite3.connect(db.DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def _all_tasks_with_worktree() -> list[dict]:
    """Every tasks.db row that has a worktree path recorded, regardless of
    status — the raw input to the --reap cross-reference sweep."""
    with _read_tasks() as conn:
        rows = conn.execute(
            "SELECT id, project, role, status, worktree, updated_at "
            "FROM tasks WHERE worktree IS NOT NULL AND worktree <> ''"
        ).fetchall()
    return [dict(r) for r in rows]


def _dir_size_bytes(path: Path) -> int:
    """Recursive size of path, skipping symlinks (worktrees symlink in
    node_modules/.env from the canonical repo — those must not be counted,
    they aren't this worktree's disk cost and aren't removed with it)."""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path, followlinks=False):
        for fn in filenames:
            fp = Path(dirpath) / fn
            try:
                if not fp.is_symlink():
                    total += fp.stat().st_size
            except OSError:
                pass
    return total


def _human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _last_commit_date(wt: Path) -> str:
    r = subprocess.run(["git", "log", "-1", "--format=%cI"], cwd=str(wt),
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return "unknown"


def _git(cwd: str | Path, *args: str, timeout: int = GIT_TIMEOUT_S) -> tuple[int, bytes]:
    """Run git in `cwd`: (returncode, stdout). (-1, b"") when git cannot be
    run or does not finish in time — callers treat that as 'cannot verify'."""
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                           timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return -1, b""
    return r.returncode, r.stdout


def _is_runner_file(path: str, task_id: str) -> bool:
    """True for a path (as `git status` prints it) the runner itself leaves
    behind: the fixed names at the worktree root, or anything under
    docs/reports/<task-id>/ (never a `..` or empty component)."""
    if path in RUNNER_ROOT_FILES:
        return True
    prefix = f"docs/reports/{task_id}/"
    if not path.startswith(prefix):
        return False
    return all(part not in ("", ".", "..") for part in path[len(prefix):].split("/"))


def _status_entries(wt: Path) -> list[tuple[str, str]] | None:
    """[(XY, path)] from `git status`, one per untracked FILE (not per
    directory), or None when git cannot say. --no-optional-locks: reading a
    worktree must not write its index, a dry run included."""
    rc, out = _git(wt, "--no-optional-locks", "status", "--porcelain=v1", "-z",
                   "--untracked-files=all")
    if rc != 0:
        return None
    entries: list[tuple[str, str]] = []
    records = iter(out.split(b"\0"))
    for rec in records:
        if not rec:
            continue
        xy = rec[:2].decode("ascii", "replace")
        entries.append((xy, os.fsdecode(rec[3:])))
        if "R" in xy or "C" in xy:
            next(records, None)     # a rename/copy source follows as its own record
    return entries


def _open_runner_file(wt: Path, rel: str):
    """Open wt/rel as a binary regular file without following symlinks.

    Root-run code over a tree another account may write (CTO_Gate_MergeChecklist
    §2b): every component is opened with O_NOFOLLOW relative to the parent's
    dir_fd, the file with O_NONBLOCK too (a planted FIFO cannot hang the open),
    and fstat must say regular file. Raises OSError / ValueError otherwise."""
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    parts = rel.split("/")
    fd = os.open(str(wt), dir_flags)
    try:
        for name in parts[:-1]:
            nfd = os.open(name, dir_flags, dir_fd=fd)
            os.close(fd)
            fd = nfd
        ffd = os.open(parts[-1], file_flags, dir_fd=fd)
    finally:
        os.close(fd)
    try:
        st = os.fstat(ffd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("not a regular file")
        return os.fdopen(ffd, "rb")
    except Exception:
        os.close(ffd)
        raise


def _runner_file_digest(wt: Path, rel: str) -> tuple[int, str]:
    """Return size and SHA-256 of the first RUNNER_HASH_LIMIT bytes."""
    with _open_runner_file(wt, rel) as source:
        st = os.fstat(source.fileno())
        h = hashlib.sha256()
        left = RUNNER_HASH_LIMIT
        while left > 0:
            chunk = source.read(min(65536, left))
            if not chunk:
                break
            h.update(chunk)
            left -= len(chunk)
        return st.st_size, h.hexdigest()


def _archive_runner_files(t: dict, wt: Path, files) -> dict:
    """P0 shape: task-named tgz of untracked runner files outside the checkout.

    Exclusive names retain previous attempts; 0600 archives may contain private
    reports. Opening each member uses the same no-symlink guard as inspection.
    """
    if not files:
        return {}
    root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    dest = root / "worktree-reap" / t["id"]
    dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix="runner-", suffix=".tgz", dir=dest)
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as output:
            with tarfile.open(fileobj=output, mode="w:gz") as archive:
                for rel, size, digest in files:
                    with _open_runner_file(wt, rel) as source:
                        before = os.fstat(source.fileno())
                        info = tarfile.TarInfo(rel)
                        info.size = before.st_size
                        info.mode = before.st_mode & 0o777
                        info.mtime = before.st_mtime
                        archive.addfile(info, source)
                        after = os.fstat(source.fileno())
                        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                            raise ValueError(f"runner file changed while archiving: {rel}")
                        if _runner_file_digest(wt, rel) != (size, digest):
                            raise ValueError(f"runner file changed before archive: {rel}")
            output.flush()
            os.fsync(output.fileno())
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        print(f"  runner-archive {t['id']} {path} sha256={digest}")
        return {"archive_path": str(path), "archive_sha256": digest}
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _cwd_holders(wt: Path, proc_dir: str = "/proc") -> list[str] | None:
    """'pid N (comm)' for every process whose cwd is `wt` or inside it, or
    None when that cannot be established (no /proc, or a cwd link this process
    may not read while CWD_UNREADABLE_BLOCKS is set)."""
    try:
        names = [n for n in os.listdir(proc_dir) if n.isdigit()]
        real = os.path.realpath(wt)
    except (OSError, ValueError):
        return None
    prefix = real.rstrip(os.sep) + os.sep
    holders: list[str] = []
    unreadable = 0
    for pid in names:
        try:
            cwd = os.readlink(os.path.join(proc_dir, pid, "cwd"))
        except FileNotFoundError:
            continue                    # the process exited meanwhile
        except OSError as e:
            if e.errno != errno.ESRCH:  # ESRCH: also gone
                unreadable += 1
            continue
        if cwd.endswith(" (deleted)"):
            cwd = cwd[:-len(" (deleted)")]
        if cwd == real or cwd.startswith(prefix):
            try:
                with open(os.path.join(proc_dir, pid, "comm"), "rb") as f:
                    comm = os.fsdecode(f.read(64)).strip()
            except OSError:
                comm = "?"
            holders.append(f"pid {pid} ({comm})")
    if unreadable and CWD_UNREADABLE_BLOCKS:
        return None
    return holders


def _verified_path(t: dict) -> tuple[Path | None, str | None]:
    """The directory remove_worktree() will act on, or why it must not.

    remove_worktree() recomputes its own path from (project, role, id) and,
    when `git worktree remove` fails, falls back to rmtree. So the row's
    recorded path has to be that very directory, reached without a symlink in
    the last component — otherwise we would delete a folder nobody checked."""
    if not _TASK_ID_RE.match(str(t["id"])):
        return None, f"unsafe task id {t['id']!r}"
    try:
        expected = worktree_mod.worktree_path(t["project"], t["role"], t["id"])
        if os.path.realpath(t["worktree"]) != os.path.realpath(expected):
            return None, f"row path is not the task's worktree {str(expected)!r}"
    except (OSError, ValueError, TypeError) as e:
        return None, f"cannot resolve the worktree path ({type(e).__name__})"
    if os.path.islink(expected):
        return None, f"{str(expected)!r} is a symlink"
    if not os.path.isdir(expected):
        return None, f"{str(expected)!r} is not a directory"
    return Path(expected), None


def _repo_problem(wt: Path, repo: Path) -> str | None:
    """Why `git worktree remove` run from `repo` would not be the one that
    removes `wt` (so remove_worktree()'s rmtree fallback would), or None."""
    rc, out = _git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if rc != 0:
        return "cannot read the worktree's git dir"
    common = os.path.realpath(os.fsdecode(out).rstrip("\n"))
    if common != os.path.realpath(repo / ".git"):
        return f"worktree belongs to git dir {common!r}, not to {str(repo)!r}"
    return None


def _inspect_worktree(wt: Path, task_id: str) -> tuple[str, str | None, dict]:
    """(action, reason, snapshot). action is 'ok' only when every removal
    condition on the worktree itself holds: clean (runner-only files aside),
    every commit on some remote, no process with its cwd inside."""
    entries = _status_entries(wt)
    if entries is None:
        return "skipped_unverifiable", "cannot read git status", {}
    runner: list[str] = []
    for xy, path in entries:
        if xy == "??" and _is_runner_file(path, task_id):
            runner.append(path)
            continue
        return "skipped_dirty", f"not clean: {xy!r} {path!r}", {}
    files = []
    for rel in runner:
        try:
            size, digest = _runner_file_digest(wt, rel)
        except (OSError, ValueError) as e:
            return "skipped_dirty", (f"runner file {rel!r} is not a plain regular "
                                     f"file ({type(e).__name__})"), {}
        files.append((rel, size, digest))
    rc, head = _git(wt, "rev-parse", "--verify", "HEAD")
    if rc != 0:
        return "skipped_unverifiable", "cannot read HEAD", {}
    rc, ahead = _git(wt, "rev-list", "--count", "HEAD", "--not", "--remotes")
    if rc != 0 or not ahead.strip().isdigit():
        return "skipped_unverifiable", "cannot count commits that are on no remote", {}
    if int(ahead) != 0:
        return "skipped_unpushed", f"{int(ahead)} commit(s) on no remote", {}
    holders = _cwd_holders(wt)
    if holders is None:
        return "skipped_unverifiable", "cannot read /proc/*/cwd for every process", {}
    if holders:
        return "skipped_in_use", f"cwd inside the worktree: {', '.join(holders)}", {}
    return "ok", None, {"status": tuple(entries), "head": head.strip(),
                        "runner": tuple(files)}


def _fetch_origin(repo: Path) -> bool:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    try:
        r = subprocess.run(["git", "fetch", "--quiet", "--prune", "origin"], cwd=str(repo),
                           env=env, capture_output=True, timeout=FETCH_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def _head_is_merged(wt: Path, base: str) -> bool:
    rc, _ = _git(wt, "merge-base", "--is-ancestor", "HEAD",
                 f"refs/remotes/origin/{base}")
    return rc == 0


def _print_runner_files(task_id: str, files) -> None:
    for rel, size, digest in files:
        note = f" (first {RUNNER_HASH_LIMIT} B hashed)" if size > RUNNER_HASH_LIMIT else ""
        print(f"  runner-file {task_id} {rel!r} {size} B sha256={digest}{note}")


def _reap_line(verb: str, entry: dict, note: str = "") -> None:
    size = entry.get("size_bytes")
    size_s = f"{size / _MB:9.1f} MB" if size is not None else "      n/a MB"
    tail = f"  -- {note}" if note else ""
    print(f"  {verb:<13} {entry['task_id']:<14} {entry['status']:<11} {size_s}  "
          f"{entry['worktree']!r}{tail}")


def _removal_check(t: dict, repo: Path) -> tuple[str, str | None, dict]:
    """Every condition on one worktree, from the path to the processes. Run
    once to decide and again right before removal."""
    wt, problem = _verified_path(t)
    if wt is None:
        return "skipped_path_mismatch", problem, {}
    problem = _repo_problem(wt, repo)
    if problem:
        return "skipped_unverifiable", problem, {}
    if t.get("_review_idle_days") is not None:
        with _read_tasks() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id=?", (t["id"],)).fetchone()
        fresh = dict(row) if row else None
        if not fresh or fresh.get("status") != "review":
            return "skipped_changed", "task is no longer in review", {}
        problem = _review_idle_problem(fresh, wt, t["_review_idle_days"])
        if problem:
            return "skipped_review", problem, {}
    return _inspect_worktree(wt, t["id"])


def _review_idle_problem(t: dict, wt: Path, days: float) -> str | None:
    age = _age_minutes(t.get("updated_at"))
    if age is None or age < days * 1440:
        return "review task is not idle long enough"
    # Include edits to nested files, not only the checkout directory's mtime.
    cutoff = time.time() - days * 86400
    for parent, dirs, files in os.walk(wt, followlinks=False):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            path = Path(parent) / name
            if name == ".git" or path.is_symlink():
                continue
            if path.stat().st_mtime > cutoff:
                return "worktree files are not idle long enough"
    if _status_entries(wt) != []:
        return "review worktree is not clean"
    rc, branch = _git(wt, "symbolic-ref", "--short", "HEAD")
    if rc:
        return "cannot read review branch"
    rc, remote = _git(wt, "rev-parse", "--verify",
                      "refs/remotes/origin/" + os.fsdecode(branch).strip())
    hc, head = _git(wt, "rev-parse", "--verify", "HEAD")
    if rc or hc or remote.strip() != head.strip():
        return "review branch HEAD does not equal origin HEAD"
    return None


def _reap_one(t: dict, wt: Path, repo: Path, entry: dict, *, dry_run: bool,
              why: str) -> dict:
    action, reason, snap = _removal_check(t, repo)
    if action != "ok":
        return {**entry, "action": action, "reason": reason}
    if dry_run:
        _print_runner_files(t["id"], snap["runner"])
        return {**entry, "action": "would_remove", "reason": why}

    # Second look right before removal: anything that moved since the first
    # one (a process started, a file written, HEAD advanced) aborts this one.
    action, reason, again = _removal_check(t, repo)
    if action != "ok":
        return {**entry, "action": "skipped_changed",
                "reason": f"changed before removal: {reason}"}
    if again != snap:
        return {**entry, "action": "skipped_changed",
                "reason": "status, HEAD or a runner file changed between the two checks"}
    _print_runner_files(t["id"], again["runner"])
    try:
        entry = {**entry, **_archive_runner_files(t, wt, again["runner"])}
        action, reason, final = _removal_check(t, repo)
        if action != "ok" or final != again:
            return {**entry, "action": "skipped_changed",
                    "reason": reason or "worktree changed during archive"}
        remove_worktree(t["project"], t["role"], t["id"], delete_branch=False)
        if wt.exists():
            raise RuntimeError(f"worktree still exists after removal: {wt}")
        if t["status"] in TERMINAL_STATUSES:
            db.set_fields(t["id"], worktree=None, actor="gc_stale_tasks")
    except Exception as e:  # noqa: BLE001 - one worktree must not stop the sweep
        return {**entry, "action": "error", "reason": f"{type(e).__name__}: {e}"}
    return {**entry, "action": "removed", "reason": why}


def reap_worktrees(*, dry_run: bool = True,
                   review_stale_days: int = REVIEW_STALE_DAYS,
                   review_idle: bool = False) -> dict:
    """Cross-reference every tasks.db row that has a worktree against its
    current status and remove the ones that are dead weight.

    A worktree is removed only when ALL of these hold:
      * the row is terminal (TERMINAL_STATUSES), or it is 'review' and its HEAD
        is an ancestor of origin/<base> (the PR merged, only the row is stale).
        pending / in_progress / rate_limited / conflict rows are never looked at.
      * it is clean — apart from the runner's own untracked files
        (RUNNER_ROOT_FILES, docs/reports/<task-id>/*), which are archived to
        $XDG_STATE_HOME/worktree-reap/<task-id>/ before removal;
      * `git rev-list --count HEAD --not --remotes` is 0;
      * no process has its cwd inside it;
      * the row's path IS tools.worktree.worktree_path(project, role, id);
      * the status and cwd checks still pass on a second look right before.
    The branch is never deleted. A folder with no task row is never touched.
    Each project's origin is fetched once per acting run; dry runs use cached
    refs without modifying any repository. If fetch fails, the 'review'
    ancestry rule is off for that repo and terminal rows still qualify.

    Unmerged 'review' worktrees older than review_stale_days are flagged only.
    review_idle=True selects review rows only, replacing the merge condition
    with idle task/files, a strictly clean tree, and exact origin branch equality.

    Returns {"removed", "skipped", "flagged_review", "kept_review"}; `removed`
    holds 'would_remove' entries under dry_run.
    """
    removed: list[dict] = []
    skipped: list[dict] = []
    flagged_review: list[dict] = []
    kept_review: list[dict] = []
    fetched: dict[str, bool] = {}
    idle_days = float((worktree_mod._load_storage_policy().get("review_worktree") or {}).get("idle_days", 3))

    def fetch_once(repo: Path) -> bool:
        key = os.path.realpath(repo)
        if key not in fetched:
            if dry_run:
                print(f"reap: cached origin refs in {str(repo)!r} (dry-run; no fetch)")
                fetched[key] = True
                return True
            fetched[key] = _fetch_origin(repo)
            print(f"reap: fetch origin in {str(repo)!r}: "
                  + ("ok" if fetched[key] else "FAILED, ancestry rule off for this repo"))
        return fetched[key]

    for t in _all_tasks_with_worktree():
        status = t["status"]
        if review_idle and status != "review":
            continue
        if status not in TERMINAL_STATUSES and status != "review":
            continue
        wt = Path(t["worktree"])
        if not wt.exists():
            continue
        entry = {"task_id": t["id"], "project": t["project"], "status": status,
                 "worktree": t["worktree"], "size_bytes": None}

        checked, problem = _verified_path(t)
        if checked is None:
            # Not sized, not opened: the recorded path is not a directory we own.
            skipped.append({**entry, "action": "skipped_path_mismatch", "reason": problem})
            _reap_line("skipped", skipped[-1], problem)
            continue
        try:
            repo = worktree_mod._repo_path(t["project"])
        except Exception as e:  # noqa: BLE001 - a project not cloned on this host
            skipped.append({**entry, "action": "skipped_unverifiable",
                            "reason": f"no checkout of {t['project']!r} on this host "
                                      f"({type(e).__name__})"})
            _reap_line("skipped", skipped[-1], skipped[-1]["reason"])
            continue

        entry["size_bytes"] = _dir_size_bytes(checked)
        entry["size_human"] = _human_size(entry["size_bytes"])
        entry["last_commit"] = _last_commit_date(checked)
        fetch_ok = fetch_once(repo)

        why = status
        if review_idle:
            if not fetch_ok:
                skipped.append({**entry, "action": "skipped_unverifiable", "reason": "origin fetch failed"})
                _reap_line("skipped", entry, "origin fetch failed")
                continue
            t = {**t, "_review_idle_days": idle_days}
            why = f"review idle >= {idle_days:g} days, clean and pushed"
        elif status == "review":
            try:
                base = worktree_mod.get_project(t["project"])["default_branch"]
            except Exception:  # noqa: BLE001 - no base branch, no ancestry rule
                base = None
            if not (fetch_ok and base and _head_is_merged(checked, base)):
                try:
                    age_days = (time.time() - checked.stat().st_mtime) / 86400
                except OSError:
                    continue
                if age_days > review_stale_days:
                    flagged_review.append({"task_id": t["id"], "worktree": t["worktree"],
                                           "age_days": round(age_days, 1)})
                    _reap_line("flagged", entry, f"review, not merged, {age_days:.0f} days old")
                else:
                    kept_review.append(entry)
                    _reap_line("kept", entry, "review, HEAD not in origin/" + (base or "?"))
                continue
            why = f"review, HEAD merged into origin/{base}"

        result = _reap_one(t, checked, repo, entry, dry_run=dry_run, why=why)
        if result["action"] in ("removed", "would_remove"):
            removed.append(result)
            _reap_line("would remove" if dry_run else "removed", result, why)
        else:
            skipped.append(result)
            _reap_line("skipped", result, result["reason"])

    return {"removed": removed, "skipped": skipped,
            "flagged_review": flagged_review, "kept_review": kept_review}


def _print_reap_report(result: dict, *, dry_run: bool) -> None:
    tag = "[dry-run] " if dry_run else ""
    verb = "would remove" if dry_run else "removed"
    total = sum(r.get("size_bytes") or 0 for r in result["removed"])
    print(f"{tag}reap: {verb} {len(result['removed'])} worktree(s) "
          f"({total / _MB:.1f} MB), skipped {len(result['skipped'])}, "
          f"flagged {len(result['flagged_review'])} stale 'review' worktree(s) "
          f"(>{REVIEW_STALE_DAYS}d, not merged), "
          f"kept {len(result['kept_review'])} other 'review' worktree(s)")


def _print_df(label: str) -> None:
    target = worktree_mod.WORKTREE_DIR if worktree_mod.WORKTREE_DIR.exists() else Path("/")
    out = ""
    try:
        r = subprocess.run(["df", "-h", "-P", str(target)], capture_output=True,
                           text=True, timeout=30)
        out = r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    if not out:
        u = shutil.disk_usage(target)
        out = (f"{u.used / 2**30:.1f}G used of {u.total / 2**30:.1f}G, "
               f"{u.free / 2**30:.1f}G free")
    print(f"df {label}:\n{out}")


def main() -> int:
    ap = argparse.ArgumentParser(description="GC stale tasks / reap terminal-status worktrees")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be cancelled without writing to DB "
                         "(stale-task sweep mode; ignored under --reap, which "
                         "is dry-run by default — see --go)")
    ap.add_argument("--pending", type=int, default=STALE_PENDING_MINUTES,
                    help=f"pending threshold minutes (default {STALE_PENDING_MINUTES})")
    ap.add_argument("--conflict", type=int, default=STALE_CONFLICT_MINUTES,
                    help=f"conflict threshold minutes (default {STALE_CONFLICT_MINUTES})")
    ap.add_argument("--ratelimit", type=int, default=STALE_RATELIMIT_MINUTES,
                    help=f"rate_limited threshold minutes (default {STALE_RATELIMIT_MINUTES})")
    ap.add_argument("--reap", action="store_true",
                    help="switch modes: reap the worktrees of finished tasks "
                         "(terminal rows, and 'review' rows whose HEAD is in "
                         "origin/<base>) instead of running the stale-task "
                         "sweep; see reap_worktrees() for every condition")
    ap.add_argument("--go", action="store_true",
                    help="[--reap only] actually remove worktrees; default is dry-run")
    ap.add_argument("--review-stale-days", type=int, default=REVIEW_STALE_DAYS,
                    help=f"[--reap only] flag unmerged 'review' worktrees older "
                         f"than this many days (default {REVIEW_STALE_DAYS})")
    ap.add_argument("--review-idle", action="store_true",
                    help="reclaim idle, clean, pushed review checkouts; dry unless --go")
    args = ap.parse_args()

    if args.reap or args.review_idle:
        _print_df("before")
        result = reap_worktrees(dry_run=not args.go or args.dry_run,
                                review_stale_days=args.review_stale_days,
                                review_idle=args.review_idle)
        _print_reap_report(result, dry_run=not args.go or args.dry_run)
        _print_df("after")
        return 0

    db.init()
    cancelled = gc_stale_tasks(
        pending_minutes=args.pending,
        conflict_minutes=args.conflict,
        ratelimit_minutes=args.ratelimit,
        dry_run=args.dry_run,
    )
    tag = "[dry-run] " if args.dry_run else ""
    verb = "would cancel" if args.dry_run else "cancelled"
    print(f"{tag}gc: {verb} {len(cancelled)} task(s)")
    if cancelled:
        print(json.dumps(cancelled, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
