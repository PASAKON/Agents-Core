"""Regression tests for the task-e8086826 audit fixes (W3, W4, W8).

W3 — depends_on was invisible to delegate_task's pre-flight: only a touches
overlap with an ACTIVE task ever blocked a delegate, and that block silently
evaporates the moment the dependency reaches 'review' (locks release there)
even though it isn't merged yet. Fix: db.unmet_dependencies() gates
delegate_task independently of touches, refusing via delegate_log without
reusing the 'conflict' status (so it stays distinguishable from a real
touches-collision).

W4 — retry-before-claim double-spawn window: a second delegate_task call on
a task whose worktree exists, is still 'pending', and has no assigned_agent
fell through to _spawn_iterm_tab again. Fix: an updated_at-based grace-period
guard for that specific combo, plus a pid-liveness check before the
re-delegate branch resets (and potentially orphans) a genuinely running DEV.

W8 — claudesign_project_id: out-of-band column, zero code references, zero
non-null rows. Fix: idempotent DROP COLUMN in db.init().

Run via:  python scripts/test_depends_on_enforcement.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest.mock as mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db  # noqa: E402
import tools.delegate as delegate  # noqa: E402

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _insert(tid: str, status: str, *, depends_on=None, touches=None,
            worktree=None, branch=None, assigned_agent=None, pid=None,
            updated_at: str | None = None) -> None:
    ts = updated_at or db.now_iso()
    with db.get_conn() as c:
        c.execute(
            "INSERT INTO tasks(id,project,role,status,title,description,"
            "depends_on,touches,worktree,branch,assigned_agent,pid,"
            "created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, "mooniex-claudeflow", "developer", status, "seed", "d",
             json.dumps(depends_on or []), json.dumps(touches or []),
             worktree, branch, assigned_agent, pid, ts, ts),
        )


def _run(coro):
    return asyncio.run(coro)


def _fake_project(**overrides) -> dict:
    proj = {
        "key": "mooniex-claudeflow",
        "agents_allowed": ["developer"],
        "spawn_backend": "iterm",
        "web_ui": "off",
        "default_branch": "main",
    }
    proj.update(overrides)
    return proj


def _dead_pid() -> int:
    """Find a pid that definitely does not name a live process."""
    candidate = 999_999
    while candidate < 2_000_000:
        try:
            os.kill(candidate, 0)
            candidate += 1
        except ProcessLookupError:
            return candidate
        except OSError:
            candidate += 1
    raise RuntimeError("could not find a dead pid for the test")


def _patched():
    """Common patch set: no real git worktree, no real osascript, no real
    background kickoff/watchdog tasks (they only fire once we already
    returned, but asyncio.run() would otherwise complain about destroyed
    pending tasks)."""
    spawn_calls: list[str] = []

    def fake_spawn(role, task_id, **kw):
        spawn_calls.append(task_id)
        return "spawned"

    async def fake_noop(*a, **kw):
        return None

    return spawn_calls, [
        mock.patch("tools.delegate.create_worktree",
                   return_value={"worktree": "/fake/wt", "branch": "agent/x"}),
        mock.patch("tools.delegate._spawn_iterm_tab", side_effect=fake_spawn),
        mock.patch("tools.delegate.get_project", return_value=_fake_project()),
        mock.patch("tools.delegate._auto_kickoff", side_effect=fake_noop),
        mock.patch("tools.delegate._verify_claimed", side_effect=fake_noop),
    ]


# ---------------------------------------------------------------------------
# W3 — depends_on enforcement
# ---------------------------------------------------------------------------

def test_unmet_dependency_blocks_delegate() -> bool:
    dep = db.new_task_id()
    child = db.new_task_id()
    _insert(dep, "in_progress")
    _insert(child, "pending", depends_on=[dep])

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        result = _run(delegate.delegate_task(child))

    return (
        len(spawn_calls) == 0
        and result["status"] == "pending"          # unchanged, NOT 'conflict'
        and "blocked by unfinished dependency" in (result["delegate_log"] or "")
        and dep in (result["delegate_log"] or "")
    )


def test_unmet_dependency_distinguishable_from_touches_collision() -> bool:
    """Same refusal-shape check as above, but proves the two failure modes
    are told apart both by status AND by delegate_log text."""
    dep = db.new_task_id()
    dep_child = db.new_task_id()
    _insert(dep, "review")  # NOT terminal-merged — review is not done/merged
    _insert(dep_child, "pending", depends_on=[dep])

    blocker = db.new_task_id()
    collide_child = db.new_task_id()
    paths = ["shared/path.py"]
    _insert(blocker, "in_progress", touches=paths)
    _insert(collide_child, "pending", touches=paths)

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        dep_result = _run(delegate.delegate_task(dep_child))
        collide_result = _run(delegate.delegate_task(collide_child))

    dep_log = dep_result["delegate_log"] or ""
    collide_log = collide_result["delegate_log"] or ""
    return (
        dep_result["status"] == "pending"
        and collide_result["status"] == "conflict"
        and "blocked by unfinished dependency" in dep_log
        and "path collision" in collide_log
        and "blocked by unfinished dependency" not in collide_log
        and "path collision" not in dep_log
    )


def test_dependency_merged_allows_delegate() -> bool:
    dep = db.new_task_id()
    child = db.new_task_id()
    _insert(dep, "merged")
    _insert(child, "pending", depends_on=[dep])

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        result = _run(delegate.delegate_task(child))

    return (
        len(spawn_calls) == 1
        and result["worktree"] == "/fake/wt"
        and "blocked by unfinished dependency" not in (result["delegate_log"] or "")
    )


def test_dependency_done_allows_delegate() -> bool:
    dep = db.new_task_id()
    child = db.new_task_id()
    _insert(dep, "done")
    _insert(child, "pending", depends_on=[dep])

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        result = _run(delegate.delegate_task(child))

    return len(spawn_calls) == 1 and result["worktree"] == "/fake/wt"


def test_no_depends_on_unchanged() -> bool:
    """Regression guard: a task with no depends_on behaves exactly as
    before this fix — no dependency gate interference."""
    child = db.new_task_id()
    _insert(child, "pending", depends_on=[])

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        result = _run(delegate.delegate_task(child))

    return (
        len(spawn_calls) == 1
        and result["worktree"] == "/fake/wt"
        and not (result["delegate_log"] or "")
    )


def test_missing_dependency_treated_as_unmet() -> bool:
    """A depends_on id that no longer resolves to a row must block, not
    silently pass — a typo'd/deleted dependency id is not "satisfied"."""
    child = db.new_task_id()
    _insert(child, "pending", depends_on=["task-doesnotexist"])

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        result = _run(delegate.delegate_task(child))

    return (
        len(spawn_calls) == 0
        and "missing" in (result["delegate_log"] or "")
    )


# ---------------------------------------------------------------------------
# W4 — double-spawn window
# ---------------------------------------------------------------------------

def test_double_spawn_within_grace_period_refused() -> bool:
    task_id = db.new_task_id()
    _insert(task_id, "pending")

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        first = _run(delegate.delegate_task(task_id))
        second = _run(delegate.delegate_task(task_id))

    return (
        len(spawn_calls) == 1
        and first["worktree"] == "/fake/wt"
        and second["worktree"] == "/fake/wt"
        and "duplicate delegate refused" in (second["delegate_log"] or "")
        and "grace period" in (second["delegate_log"] or "")
    )


def test_redelegate_after_grace_period_proceeds() -> bool:
    """Past the grace window (watchdog already gave up, or never ran), a
    manual re-delegate on a still-unclaimed task must still work."""
    task_id = db.new_task_id()
    _insert(task_id, "pending")

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        _run(delegate.delegate_task(task_id))  # spawn #1, sets worktree

        # Age the SPAWN clock, and deliberately leave `updated_at` fresh.
        # The guard used to read `updated_at`, which meant any unrelated
        # write — reopen_task, a watchdog ping, or the refusal's own
        # delegate_log — looked like a spawn and blocked the retry (GH #51,
        # #53). Backdating only `spawned_at` asserts both halves: the real
        # spawn clock is what opens the window, and a fresh `updated_at`
        # no longer holds it shut.
        stale_ts = (datetime.now(timezone.utc)
                    - timedelta(seconds=delegate.CLAIM_VERIFY_DELAY_S + 5)
                    ).isoformat(timespec="seconds")
        fresh_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with db.get_conn() as c:
            c.execute("UPDATE tasks SET spawned_at=?, updated_at=? WHERE id=?",
                      (stale_ts, fresh_ts, task_id))

        second = _run(delegate.delegate_task(task_id))  # spawn #2, allowed

    return len(spawn_calls) == 2 and "duplicate delegate refused" not in (
        second["delegate_log"] or "")


def test_redelegate_refused_while_pid_alive() -> bool:
    """W4 guard B: an in_progress task with a live pid must not be reset
    (which would orphan the running DEV) or spawned a second time."""
    task_id = db.new_task_id()
    _insert(task_id, "in_progress", worktree="/fake/wt", branch="agent/x",
            assigned_agent="developer", pid=os.getpid())

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        result = _run(delegate.delegate_task(task_id))

    return (
        len(spawn_calls) == 0
        and result["status"] == "in_progress"
        and result["assigned_agent"] == "developer"
        and result["pid"] == os.getpid()
        and "already running under live pid" in (result["delegate_log"] or "")
    )


def test_redelegate_proceeds_when_pid_dead() -> bool:
    """Regression guard: a dead pid must not block the existing recovery
    path — reset + respawn still happens exactly as before this fix."""
    task_id = db.new_task_id()
    dead = _dead_pid()
    _insert(task_id, "in_progress", worktree="/fake/wt", branch="agent/x",
            assigned_agent="developer", pid=dead)

    spawn_calls, patches = _patched()
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        result = _run(delegate.delegate_task(task_id))

    return (
        len(spawn_calls) == 1
        and result["status"] == "pending"
        and result["assigned_agent"] is None
        and result["pid"] is None
    )


# ---------------------------------------------------------------------------
# W8 — dead column migration
# ---------------------------------------------------------------------------

def _cols() -> set[str]:
    with db.get_conn() as c:
        return {r["name"] for r in c.execute("PRAGMA table_info(tasks)").fetchall()}


def test_fresh_init_has_no_dead_column() -> bool:
    cols = _cols()
    migration_cols = {c for c, _ in db._MIGRATION_COLUMNS}
    return "claudesign_project_id" not in cols and migration_cols <= cols


def test_migration_drops_existing_column_idempotently() -> bool:
    with db.get_conn() as c:
        c.execute("ALTER TABLE tasks ADD COLUMN claudesign_project_id TEXT")
    if "claudesign_project_id" not in _cols():
        return False

    db.init()  # first pass: should drop it
    ok1 = "claudesign_project_id" not in _cols()

    db.init()  # second pass: must be a no-op, not an error
    ok2 = "claudesign_project_id" not in _cols()

    return ok1 and ok2


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="depends-on-")
    db.DB_PATH = Path(tmp) / "tasks.db"
    db.init()

    print("=== W3: depends_on enforcement ===")
    r = test_unmet_dependency_blocks_delegate()
    _mark(r, "unmet dependency (in_progress) blocks delegate, status unchanged")
    r = test_unmet_dependency_distinguishable_from_touches_collision()
    _mark(r, "dependency-block vs touches-collision are distinguishable "
             "(status + delegate_log)")
    r = test_dependency_merged_allows_delegate()
    _mark(r, "dependency status='merged' -> delegate proceeds")
    r = test_dependency_done_allows_delegate()
    _mark(r, "dependency status='done' -> delegate proceeds")
    r = test_no_depends_on_unchanged()
    _mark(r, "no depends_on -> unchanged behavior (regression guard)")
    r = test_missing_dependency_treated_as_unmet()
    _mark(r, "missing/deleted dependency id treated as unmet, not satisfied")

    print("=== W4: double-spawn window ===")
    r = test_double_spawn_within_grace_period_refused()
    _mark(r, "second delegate within grace period does not spawn again")
    r = test_redelegate_after_grace_period_proceeds()
    _mark(r, "manual re-delegate past grace period still spawns")
    r = test_redelegate_refused_while_pid_alive()
    _mark(r, "re-delegate refused while pid is alive (no orphaned DEV)")
    r = test_redelegate_proceeds_when_pid_dead()
    _mark(r, "re-delegate still resets+respawns when pid is dead (regression guard)")

    print("=== W8: dead column migration ===")
    r = test_fresh_init_has_no_dead_column()
    _mark(r, "fresh db.init() has no claudesign_project_id, has all migration cols")
    r = test_migration_drops_existing_column_idempotently()
    _mark(r, "db.init() drops claudesign_project_id and is idempotent")

    print(f"\n{'ALL PASS' if _failures == 0 else f'{_failures} FAILURE(S)'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
