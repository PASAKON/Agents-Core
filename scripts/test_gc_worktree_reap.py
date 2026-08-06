"""Tests for the --reap worktree-reclaim logic in tools/gc_stale_tasks.py.

Context: gc_stale_tasks.py used to cancel stale tasks but never removed their
worktree dirs, and nothing ever revisited terminal-status tasks whose
worktree already existed before this code shipped — see wiki
org:reference/2026-08-06-agents-system-audit.md. reap_worktrees() cross-
references every tasks.db row that has a worktree against its current
status.

Tests:
  1. Terminal status (done) + clean worktree exists -> removed (dir gone).
  2. Terminal status (failed) + dirty worktree -> skipped + logged, dir
     survives (never force-removed).
  3. Non-terminal status (in_progress) -> untouched entirely (not even
     considered — not in removed/skipped/flagged).
  4. review status + worktree mtime >21 days -> flagged in output, dir
     survives (never removed).
  5. review status + fresh mtime -> NOT flagged.
  6. dry_run=True (the default) touches nothing on disk, even for an
     otherwise-removable candidate.

Run via: python scripts/test_gc_worktree_reap.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod
import tools.worktree as worktree_mod
from tools.gc_stale_tasks import reap_worktrees

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True, check=True)


def _make_worktree(path: Path, *, dirty: bool = False) -> None:
    """A real git working dir at `path` — enough for `git status --porcelain`
    and `git log -1` (what reap_worktrees actually shells out to) to work."""
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], path)
    _git(["config", "user.email", "test@test.local"], path)
    _git(["config", "user.name", "test"], path)
    (path / "README.md").write_text("seed\n")
    _git(["add", "-A"], path)
    _git(["commit", "-q", "-m", "seed"], path)
    if dirty:
        (path / "README.md").write_text("uncommitted change\n")


def _insert_task(conn, *, tid: str, project: str, role: str, status: str,
                 worktree: str) -> None:
    ts = db_mod.now_iso()
    conn.execute(
        """INSERT INTO tasks
           (id, project, role, status, title, description, worktree,
            touches, depends_on, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, project, role, status, "test", "test", worktree,
         "[]", "[]", ts, ts),
    )
    conn.commit()


def run_tests(tmp_db: Path, tmp_worktrees: Path, fake_repo: Path) -> None:
    original_db_path = db_mod.DB_PATH
    original_wt_dir = worktree_mod.WORKTREE_DIR
    original_get_project = worktree_mod.get_project
    db_mod.DB_PATH = tmp_db

    # remove_worktree() looks up the project via get_project() to find the
    # canonical repo (only used for `git worktree remove`'s cwd — the actual
    # target path is recomputed from project_key/role/task_id against
    # WORKTREE_DIR). Stub both so the reap logic never touches a real project
    # or the real worktrees/ dir.
    def _fake_get_project(key: str) -> dict:
        return {"key": key, "path": str(fake_repo), "default_branch": "main"}

    worktree_mod.WORKTREE_DIR = tmp_worktrees
    worktree_mod.get_project = _fake_get_project

    try:
        db_mod.init()

        # --- Test 1: terminal (done) + clean worktree -> removed ---
        role1, tid1 = "developer", "task-reap0001"
        wt1 = worktree_mod.worktree_path("test-proj", role1, tid1)
        _make_worktree(wt1, dirty=False)
        with db_mod.get_conn() as conn:
            _insert_task(conn, tid=tid1, project="test-proj", role=role1,
                        status="done", worktree=str(wt1))

        # --- Test 2: terminal (failed) + dirty worktree -> skipped ---
        role2, tid2 = "developer", "task-reap0002"
        wt2 = worktree_mod.worktree_path("test-proj", role2, tid2)
        _make_worktree(wt2, dirty=True)
        with db_mod.get_conn() as conn:
            _insert_task(conn, tid=tid2, project="test-proj", role=role2,
                        status="failed", worktree=str(wt2))

        # --- Test 3: non-terminal (in_progress) -> untouched ---
        role3, tid3 = "developer", "task-reap0003"
        wt3 = worktree_mod.worktree_path("test-proj", role3, tid3)
        _make_worktree(wt3, dirty=False)
        with db_mod.get_conn() as conn:
            _insert_task(conn, tid=tid3, project="test-proj", role=role3,
                        status="in_progress", worktree=str(wt3))

        # --- Test 4: review + stale mtime (>21d) -> flagged only ---
        role4, tid4 = "developer", "task-reap0004"
        wt4 = worktree_mod.worktree_path("test-proj", role4, tid4)
        _make_worktree(wt4, dirty=False)
        stale_time = time.time() - 30 * 86400  # 30 days ago
        os.utime(wt4, (stale_time, stale_time))
        with db_mod.get_conn() as conn:
            _insert_task(conn, tid=tid4, project="test-proj", role=role4,
                        status="review", worktree=str(wt4))

        # --- Test 5: review + fresh mtime -> NOT flagged ---
        role5, tid5 = "developer", "task-reap0005"
        wt5 = worktree_mod.worktree_path("test-proj", role5, tid5)
        _make_worktree(wt5, dirty=False)
        with db_mod.get_conn() as conn:
            _insert_task(conn, tid=tid5, project="test-proj", role=role5,
                        status="review", worktree=str(wt5))

        # --- Test 6 setup: another clean 'done' candidate, probed under
        # dry_run=True first to prove dry-run touches nothing ---
        role6, tid6 = "developer", "task-reap0006"
        wt6 = worktree_mod.worktree_path("test-proj", role6, tid6)
        _make_worktree(wt6, dirty=False)
        with db_mod.get_conn() as conn:
            _insert_task(conn, tid=tid6, project="test-proj", role=role6,
                        status="cancelled", worktree=str(wt6))

        # ---- Run 1: dry_run=True (the default) ----
        dry = reap_worktrees(dry_run=True)
        removed_ids_dry = {r["task_id"] for r in dry["removed"]}
        skipped_ids_dry = {r["task_id"] for r in dry["skipped"]}
        flagged_ids_dry = {r["task_id"] for r in dry["flagged_review"]}

        _mark(tid1 in removed_ids_dry and tid6 in removed_ids_dry,
              f"[6a] dry-run reports clean terminal worktrees as candidates — got {removed_ids_dry}")
        _mark(wt1.exists() and wt6.exists(),
              "[6b] dry-run (default) did NOT delete anything on disk")
        _mark(tid2 in skipped_ids_dry,
              f"[dry] dirty terminal worktree reported as skip candidate — got {skipped_ids_dry}")
        _mark(tid4 in flagged_ids_dry,
              f"[dry] stale review worktree flagged under dry-run too — got {flagged_ids_dry}")

        # ---- Run 2: dry_run=False (--go) — the real assertions ----
        result = reap_worktrees(dry_run=False)
        removed_ids = {r["task_id"] for r in result["removed"]}
        skipped_ids = {r["task_id"] for r in result["skipped"]}
        flagged_ids = {r["task_id"] for r in result["flagged_review"]}

        # [1] terminal + clean -> removed
        _mark(tid1 in removed_ids, f"[1] terminal(done)+clean worktree removed — got {removed_ids}")
        _mark(not wt1.exists(), "[1b] worktree dir for tid1 is gone from disk")

        # [2] terminal + dirty -> skipped, not force-removed
        _mark(tid2 in skipped_ids, f"[2] terminal(failed)+dirty worktree skipped — got {skipped_ids}")
        skip2 = next((r for r in result["skipped"] if r["task_id"] == tid2), None)
        _mark(skip2 is not None and skip2["action"] == "skipped_dirty",
              f"[2b] skip reason is 'skipped_dirty' — got {skip2 and skip2['action']}")
        _mark(wt2.exists(), "[2c] dirty worktree dir for tid2 SURVIVES (never force-removed)")

        # [3] non-terminal -> completely untouched
        _mark(tid3 not in removed_ids and tid3 not in skipped_ids and tid3 not in flagged_ids,
              "[3] non-terminal (in_progress) task not considered at all")
        _mark(wt3.exists(), "[3b] in_progress worktree dir untouched")

        # [4] review + stale mtime -> flagged, never removed
        _mark(tid4 in flagged_ids, f"[4] stale review (>21d) worktree flagged — got {flagged_ids}")
        _mark(tid4 not in removed_ids and tid4 not in skipped_ids,
              "[4b] flagged review task never appears in removed/skipped")
        _mark(wt4.exists(), "[4c] stale review worktree dir survives (flag-only, never removed)")

        # [5] review + fresh mtime -> NOT flagged
        _mark(tid5 not in flagged_ids, f"[5] fresh review worktree NOT flagged — got {flagged_ids}")
        _mark(wt5.exists(), "[5b] fresh review worktree dir untouched")

        # [6] real removal happened only after --go, and reports size/last_commit
        _mark(tid6 in removed_ids, f"[6c] terminal(cancelled)+clean worktree removed on --go — got {removed_ids}")
        _mark(not wt6.exists(), "[6d] worktree dir for tid6 is gone from disk after --go")
        rem1 = next((r for r in result["removed"] if r["task_id"] == tid1), None)
        _mark(rem1 is not None and "size_human" in rem1 and "last_commit" in rem1,
              f"[7] removed entries carry size_human + last_commit — got {rem1}")

        # Idempotent: running again finds nothing left to remove for tid1/tid6
        result2 = reap_worktrees(dry_run=False)
        removed_ids2 = {r["task_id"] for r in result2["removed"]}
        _mark(tid1 not in removed_ids2 and tid6 not in removed_ids2,
              "[8] idempotent: already-removed worktrees not re-reported")

    finally:
        db_mod.DB_PATH = original_db_path
        worktree_mod.WORKTREE_DIR = original_wt_dir
        worktree_mod.get_project = original_get_project


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp_db = Path(td) / "test_tasks.db"
        tmp_worktrees = Path(td) / "worktrees"
        fake_repo = Path(td) / "fake_repo"
        fake_repo.mkdir(parents=True, exist_ok=True)
        run_tests(tmp_db, tmp_worktrees, fake_repo)

    count = _failures
    print(f"\n{'ALL PASS' if count == 0 else str(count) + ' FAILED'}")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())
