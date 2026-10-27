"""Tests for the --reap worktree-reclaim logic in tools/gc_stale_tasks.py.

Context: gc_stale_tasks.py used to cancel stale tasks but never removed their
worktree dirs, and nothing ever revisited terminal-status tasks whose
worktree already existed before this code shipped — see wiki
org:reference/2026-08-06-agents-system-audit.md. reap_worktrees() cross-
references every tasks.db row that has a worktree against its current
status.

2026-10-27 (task-3a803be1): the reap became a standing op on Contabo
(deploy/systemd/org-worktree-reap.timer), so it needs no CEO card per run. Two
faults made it skip nearly everything, and a wrong removal deletes another
session's work, so the conditions are tested one by one.

Every test builds its own temp world: a bare "origin", the project's clone of
it, and real `git worktree add` worktrees under a folder whose name has
spaces, Thai script, parentheses and a `#` — nothing touches a real checkout.

Original scenarios (kept, now on real worktrees with a remote):
  1. Terminal status (done) + clean worktree exists -> removed (dir gone).
  2. Terminal status (failed) + dirty worktree -> skipped + logged, dir
     survives (never force-removed).
  3. Non-terminal status (in_progress) -> untouched entirely (not even
     considered — not in removed/skipped/flagged).
  4. review status + worktree mtime >21 days, branch NOT merged -> flagged in
     output, dir survives (never removed).
  5. review status + fresh mtime, branch NOT merged -> NOT flagged.
  6. dry_run=True (the default) touches nothing on disk, even for an
     otherwise-removable candidate.
  7. Terminal status (merged) + clean worktree exists -> removed (dir gone).
     Regression guard for W6 (org:reference/2026-08-06-agents-system-audit.md).

Added 2026-10-27:
  fault 1  runner-only untracked files count as clean (and are hashed, not copied)
  fault 2  a `review` row whose HEAD is in origin/<base> is removed
  and: a foreign untracked file blocks; an unmerged review row is flag-only;
  pending/in_progress/rate_limited/conflict rows are kept whatever git says; a
  commit on no remote blocks; a live cwd blocks; a path mismatch (or symlink)
  blocks; a folder with no task row is never touched; the second look before
  removal aborts on change; a failed fetch turns the ancestry rule off.

Run via: python -m pytest scripts/test_gc_worktree_reap.py
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod
import tools.gc_stale_tasks as gc_mod
import tools.worktree as worktree_mod
from tools.gc_stale_tasks import reap_worktrees

PROJECT = "test-proj"
ROLE = "developer"


def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(args)} in {cwd}: {r.stderr}"
    return r.stdout.strip()


class ReapEnv:
    """A bare origin, the project's clone of it, and a worktrees/ folder."""

    def __init__(self, base: Path):
        self.base = base
        self.origin = base / "origin.git"
        self.repo = base / "repo"
        self.worktrees = base / "worktrees"
        self.worktrees.mkdir()
        _git(base, "init", "-q", "--bare", "-b", "main", str(self.origin))
        _git(base, "clone", "-q", str(self.origin), str(self.repo))
        _git(self.repo, "checkout", "-q", "-B", "main")
        (self.repo / "README.md").write_text("seed\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "seed")
        _git(self.repo, "push", "-q", "-u", "origin", "main")

    def worktree(self, tid: str, state: str = "at_main", *, role: str = ROLE) -> Path:
        """A real linked worktree of the project on branch agent/<role>-<tid>.

        at_main    HEAD == origin/main
        pushed     one commit, pushed to origin as its own branch, NOT in main
        merged     as pushed, then main on origin moves past it (the project
                   clone's origin/main stays stale until the reaper fetches)
        local      one commit that is on no remote
        """
        wt = worktree_mod.worktree_path(PROJECT, role, tid)
        branch = worktree_mod.branch_name(role, tid)
        _git(self.repo, "worktree", "add", "-q", "-b", branch, str(wt), "origin/main")
        if state != "at_main":
            (wt / f"{tid}.txt").write_text("work\n")
            _git(wt, "add", "-A")
            _git(wt, "commit", "-q", "-m", f"work {tid}")
        if state in ("pushed", "merged"):
            _git(wt, "push", "-q", "origin", f"HEAD:refs/heads/{branch}")
        if state == "merged":
            sha = _git(wt, "rev-parse", "HEAD")
            tree = _git(self.origin, "rev-parse", f"{sha}^{{tree}}")
            later = _git(self.origin, "commit-tree", tree, "-p", sha, "-m", "main moves on")
            _git(self.origin, "update-ref", "refs/heads/main", later)
        return wt

    def row(self, tid: str, status: str, *, worktree: Path | str | None = None,
            role: str = ROLE) -> None:
        wt = worktree if worktree is not None else worktree_mod.worktree_path(PROJECT, role, tid)
        ts = db_mod.now_iso()
        with db_mod.get_conn() as conn:
            conn.execute(
                """INSERT INTO tasks
                   (id, project, role, status, title, description, worktree,
                    touches, depends_on, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (tid, PROJECT, role, status, "test", "test", str(wt), "[]", "[]", ts, ts),
            )
            conn.commit()


def ids(entries) -> set[str]:
    return {e["task_id"] for e in entries}


def entry(result: dict, key: str, tid: str) -> dict | None:
    return next((e for e in result[key] if e["task_id"] == tid), None)


@pytest.fixture
def env(tmp_path, monkeypatch):
    base = tmp_path / "คลัง งาน (test) #1"      # hostile name: spaces, Thai, (), #
    base.mkdir()
    monkeypatch.delenv("ORG_DB_URL", raising=False)     # never the hub
    for k, v in {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                 "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@test.local",
                 "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@test.local",
                 "GIT_TERMINAL_PROMPT": "0"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setattr(db_mod, "DB_PATH", base / "test_tasks.db")
    e = ReapEnv(base)
    # remove_worktree() and the reaper look the project up through tools.worktree
    monkeypatch.setattr(worktree_mod, "WORKTREE_DIR", e.worktrees)
    monkeypatch.setattr(worktree_mod, "get_project",
                        lambda key: {"key": key, "path": str(e.repo), "default_branch": "main"})
    monkeypatch.setattr(worktree_mod, "project_path_for_host", lambda key, host: str(e.repo))
    # a non-root CI user cannot read other users' /proc/<pid>/cwd
    monkeypatch.setattr(gc_mod, "CWD_UNREADABLE_BLOCKS", os.geteuid() == 0, raising=False)
    db_mod.init()
    return e


# --- the original scenarios -------------------------------------------------

def test_terminal_clean_worktree_removed(env):
    wt = env.worktree("task-reap0001")
    env.row("task-reap0001", "done")
    res = reap_worktrees(dry_run=False)
    assert "task-reap0001" in ids(res["removed"])                       # [1]
    assert not wt.exists()                                              # [1b]
    rem = entry(res, "removed", "task-reap0001")
    assert "size_human" in rem and "last_commit" in rem                 # [7]
    # the branch is never deleted, and the row stops pointing at the dead path
    assert _git(env.repo, "branch", "--list", "agent/developer-task-reap0001")
    assert db_mod.get_task("task-reap0001")["worktree"] is None


def test_terminal_dirty_worktree_skipped(env):
    wt = env.worktree("task-reap0002")
    (wt / "README.md").write_text("uncommitted change\n")
    env.row("task-reap0002", "failed")
    res = reap_worktrees(dry_run=False)
    assert "task-reap0002" in ids(res["skipped"])                       # [2]
    assert entry(res, "skipped", "task-reap0002")["action"] == "skipped_dirty"   # [2b]
    assert wt.exists()                                                  # [2c]


def test_review_stale_unmerged_is_flagged_never_removed(env):
    wt = env.worktree("task-reap0004", "pushed")
    stale = time.time() - 30 * 86400
    os.utime(wt, (stale, stale))
    env.row("task-reap0004", "review")
    res = reap_worktrees(dry_run=False)
    assert "task-reap0004" in ids(res["flagged_review"])                # [4]
    assert "task-reap0004" not in ids(res["removed"]) | ids(res["skipped"])   # [4b]
    assert wt.exists()                                                  # [4c]


def test_review_fresh_unmerged_not_flagged(env):
    wt = env.worktree("task-reap0005", "pushed")
    env.row("task-reap0005", "review")
    res = reap_worktrees(dry_run=False)
    assert "task-reap0005" not in ids(res["flagged_review"])            # [5]
    assert wt.exists()                                                  # [5b]


def test_dry_run_default_removes_nothing(env, capsys):
    wt_done = env.worktree("task-reap0006")
    wt_merged = env.worktree("task-reap0007")
    wt_dirty = env.worktree("task-reap0002")
    (wt_dirty / "README.md").write_text("uncommitted change\n")
    env.row("task-reap0006", "cancelled")
    env.row("task-reap0007", "merged")
    env.row("task-reap0002", "failed")
    before = {w: sorted(p.name for p in w.iterdir()) for w in (wt_done, wt_merged, wt_dirty)}
    listed = _git(env.repo, "worktree", "list", "--porcelain")

    res = reap_worktrees()                                              # the default
    assert ids(res["removed"]) == {"task-reap0006", "task-reap0007"}    # [6a][7a]
    assert {e["action"] for e in res["removed"]} == {"would_remove"}
    assert "task-reap0002" in ids(res["skipped"])
    assert wt_done.exists() and wt_merged.exists() and wt_dirty.exists()  # [6b][7b]
    assert before == {w: sorted(p.name for p in w.iterdir()) for w in before}
    assert _git(env.repo, "worktree", "list", "--porcelain") == listed
    assert db_mod.get_task("task-reap0006")["worktree"] == str(wt_done)
    assert "would remove" in capsys.readouterr().out


def test_merged_status_removed_then_idempotent(env):
    wt = env.worktree("task-reap0007")
    env.row("task-reap0007", "merged")
    res = reap_worktrees(dry_run=False)
    assert "task-reap0007" in ids(res["removed"])                       # [9]
    assert not wt.exists()                                              # [9b]
    assert entry(res, "removed", "task-reap0007")["status"] == "merged"   # [9c]
    assert "task-reap0007" not in ids(reap_worktrees(dry_run=False)["removed"])   # [8]


@pytest.mark.parametrize("status", ["pending", "in_progress", "rate_limited", "conflict"])
def test_live_statuses_keep_their_worktree_whatever_git_says(env, status):
    # the strongest bait: clean, pushed, and already merged into origin/main
    wt = env.worktree("task-reap0003", "merged")
    env.row("task-reap0003", status)
    res = reap_worktrees(dry_run=False)
    assert "task-reap0003" not in (ids(res["removed"]) | ids(res["skipped"])
                                   | ids(res["flagged_review"]))        # [3]
    assert wt.exists()                                                  # [3b]


def test_in_progress_with_head_equal_to_origin_main_is_kept(env):
    wt = env.worktree("task-reap0003", "at_main")
    env.row("task-reap0003", "in_progress")
    res = reap_worktrees(dry_run=False)
    assert ids(res["removed"]) == set() and wt.exists()


# --- fault 1: runner-only files count as clean ------------------------------

RUNNER_NAMES = ["REPORT.md", "BLOCKER.md", "PR_BODY.md", "WORKER.md", "TASK.md",
                "CTO-FEEDBACK.md", ".org-task.json", ".media_blockers"]


def test_runner_only_untracked_files_count_as_clean(env, capsys):
    tid = "task-runner01"
    wt = env.worktree(tid)
    for name in RUNNER_NAMES:
        (wt / name).write_text(f"content of {name}\n")
    reports = wt / "docs" / "reports" / tid
    reports.mkdir(parents=True)
    (reports / ".media_allow_raw").write_text("")
    (reports / "รายงาน (final) #2 REPORT.md.bak").write_text("hostile name\n")
    (reports / "sub").mkdir()
    (reports / "sub" / "shot.png").write_bytes(b"\x89PNG")
    env.row(tid, "done")

    res = reap_worktrees(dry_run=False)
    assert tid in ids(res["removed"]), res["skipped"]
    assert not wt.exists()
    out = capsys.readouterr().out
    # one line per runner file: name, size, sha256 — printed before the removal line
    for name in RUNNER_NAMES:
        body = f"content of {name}\n".encode()
        assert f"{name!r} {len(body)} B sha256={hashlib.sha256(body).hexdigest()}" in out
    assert out.count("runner-file") == len(RUNNER_NAMES) + 3
    assert out.index("runner-file") < out.index("removed ")
    # "do not copy them anywhere"
    assert list(env.base.rglob("REPORT.md")) == []


def test_runner_file_hash_covers_at_most_one_mb(env, capsys):
    tid = "task-runner02"
    wt = env.worktree(tid)
    big = os.urandom(1024 * 1024) + b"tail that must not be hashed"
    (wt / "REPORT.md").write_bytes(big)
    env.row(tid, "done")
    assert tid in ids(reap_worktrees(dry_run=False)["removed"])
    out = capsys.readouterr().out
    assert f"{len(big)} B sha256={hashlib.sha256(big[:1024 * 1024]).hexdigest()}" in out
    assert "first 1048576 B hashed" in out


@pytest.mark.parametrize("name", [
    "notes.txt",
    "สมุด (draft) #1.txt",
    "two\nlines.txt",                       # a newline in a name must not forge a record
    "sub/REPORT.md",                        # the fixed names count at the root only
    "docs/reports/task-other/REPORT.md",    # another task's report folder
    "docs/reports/REPORT.md",
    "REPORT.md.bak",
    "REPORT.md~",
])
def test_foreign_untracked_file_blocks_removal(env, name):
    tid = "task-foreign1"
    wt = env.worktree(tid)
    (wt / "REPORT.md").write_text("this one is fine\n")
    target = wt / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("not the runner's\n")
    env.row(tid, "done")
    res = reap_worktrees(dry_run=False)
    assert tid not in ids(res["removed"])
    skipped = entry(res, "skipped", tid)
    assert skipped["action"] == "skipped_dirty"
    assert "\n" not in skipped["reason"]                # printed with repr(), one line
    assert wt.exists() and target.exists()


def test_tracked_change_to_a_runner_named_file_blocks(env):
    tid = "task-foreign2"
    wt = env.worktree(tid)
    (wt / "TASK.md").write_text("tracked on this branch\n")
    _git(wt, "add", "TASK.md")
    _git(wt, "commit", "-q", "-m", "track TASK.md")
    _git(wt, "push", "-q", "origin", f"HEAD:refs/heads/agent/developer-{tid}")
    (wt / "TASK.md").write_text("edited after the commit\n")     # ' M', not '??'
    env.row(tid, "done")
    res = reap_worktrees(dry_run=False)
    assert entry(res, "skipped", tid)["action"] == "skipped_dirty"
    assert wt.exists()


def test_runner_file_that_is_a_symlink_is_not_followed(env):
    tid = "task-foreign3"
    wt = env.worktree(tid)
    secret = env.base / "secret.txt"
    secret.write_text("do not open me\n")
    (wt / "REPORT.md").symlink_to(secret)
    env.row(tid, "done")
    res = reap_worktrees(dry_run=False)
    skipped = entry(res, "skipped", tid)
    assert skipped["action"] == "skipped_dirty" and "regular file" in skipped["reason"]
    assert wt.exists() and secret.exists()


def test_runner_file_below_a_symlinked_directory_is_not_followed(env):
    tid = "task-foreign4"
    wt = env.worktree(tid)
    outside = env.base / "outside"
    outside.mkdir()
    (outside / "REPORT.md").write_text("elsewhere\n")
    (wt / "docs" / "reports").mkdir(parents=True)
    (wt / "docs" / "reports" / tid).symlink_to(outside)
    env.row(tid, "done")
    res = reap_worktrees(dry_run=False)
    # git lists the symlink itself, which is not "under" docs/reports/<tid>/
    assert entry(res, "skipped", tid)["action"] == "skipped_dirty"
    assert wt.exists() and (outside / "REPORT.md").exists()


@pytest.mark.parametrize("path,task_id,expect", [
    ("REPORT.md", "task-a", True),
    (".media_blockers", "task-a", True),
    ("docs/reports/task-a/REPORT.md", "task-a", True),
    ("docs/reports/task-a/deep/er/x.bin", "task-a", True),
    ("docs/reports/task-a/", "task-a", False),
    ("docs/reports/task-a/../x", "task-a", False),
    ("docs/reports/task-a/./x", "task-a", False),
    ("docs/reports/task-b/REPORT.md", "task-a", False),
    ("docs/reports/task-ab/REPORT.md", "task-a", False),
    ("a/REPORT.md", "task-a", False),
    ("REPORT.md ", "task-a", False),
    ("src/app.py", "task-a", False),
])
def test_is_runner_file(path, task_id, expect):
    assert gc_mod._is_runner_file(path, task_id) is expect


# --- fault 2: a merged `review` row is removed ------------------------------

def test_merged_review_row_qualifies(env, capsys):
    tid = "task-review01"
    wt = env.worktree(tid, "merged")
    (wt / "REPORT.md").write_text("report\n")
    env.row(tid, "review")
    assert "task-review01" not in _git(env.repo, "branch", "--merged", "origin/main"), \
        "fixture: the project clone's origin/main must be stale until the reaper fetches"
    res = reap_worktrees(dry_run=False)
    assert tid in ids(res["removed"]), res["skipped"]
    assert not wt.exists()
    assert entry(res, "removed", tid)["status"] == "review"
    assert "fetch origin" in capsys.readouterr().out
    # the row is still `review`, and keeps its path: a reopen restores a worktree there
    assert db_mod.get_task(tid)["status"] == "review"
    assert db_mod.get_task(tid)["worktree"] == str(wt)
    assert _git(env.repo, "branch", "--list", f"agent/developer-{tid}")


def test_unmerged_review_row_is_flag_only(env):
    old = env.worktree("task-review02", "pushed")
    new = env.worktree("task-review03", "pushed")
    stale = time.time() - 30 * 86400
    os.utime(old, (stale, stale))
    env.row("task-review02", "review")
    env.row("task-review03", "review")
    res = reap_worktrees(dry_run=False)
    assert ids(res["flagged_review"]) == {"task-review02"}
    assert ids(res["kept_review"]) == {"task-review03"}
    assert ids(res["removed"]) == set() and ids(res["skipped"]) == set()
    assert old.exists() and new.exists()


def test_failed_fetch_turns_ancestry_off_but_terminal_rows_still_qualify(env, capsys):
    merged = env.worktree("task-review04", "merged")
    done = env.worktree("task-fetch01")
    env.row("task-review04", "review")
    env.row("task-fetch01", "done")
    _git(env.repo, "remote", "set-url", "origin", str(env.base / "no-such-origin.git"))
    res = reap_worktrees(dry_run=False)
    assert "task-fetch01" in ids(res["removed"]) and not done.exists()
    assert "task-review04" not in ids(res["removed"]) and merged.exists()
    assert "FAILED" in capsys.readouterr().out


def test_origin_is_fetched_once_per_run(env, monkeypatch):
    calls = []
    real = gc_mod._fetch_origin
    monkeypatch.setattr(gc_mod, "_fetch_origin", lambda repo: calls.append(repo) or real(repo))
    for n in range(3):
        env.worktree(f"task-fetch1{n}")
        env.row(f"task-fetch1{n}", "done")
    reap_worktrees(dry_run=False)
    assert len(calls) == 1


# --- every other condition --------------------------------------------------

def test_commit_on_no_remote_blocks(env):
    wt = env.worktree("task-local01", "local")
    env.row("task-local01", "done")
    res = reap_worktrees(dry_run=False)
    skipped = entry(res, "skipped", "task-local01")
    assert skipped["action"] == "skipped_unpushed" and "1 commit" in skipped["reason"]
    assert wt.exists()


def test_live_cwd_blocks_and_releases(env):
    wt = env.worktree("task-cwd001")
    (wt / "sub").mkdir()
    env.row("task-cwd001", "done")
    proc = subprocess.Popen(["sleep", "60"], cwd=str(wt / "sub"))     # a subdirectory counts
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not gc_mod._cwd_holders(wt):
            time.sleep(0.05)
        res = reap_worktrees(dry_run=False)
        skipped = entry(res, "skipped", "task-cwd001")
        assert skipped["action"] == "skipped_in_use" and f"pid {proc.pid}" in skipped["reason"]
        assert wt.exists()
    finally:
        proc.kill()
        proc.wait()
    assert "task-cwd001" in ids(reap_worktrees(dry_run=False)["removed"])   # it was the only blocker
    assert not wt.exists()


def test_cwd_scan_reads_a_proc_tree_and_fails_closed(env, tmp_path, monkeypatch):
    wt = env.worktree("task-cwd002")
    proc = tmp_path / "proc"
    for pid, target in (("101", wt / "deep"), ("102", env.base), ("103", wt.with_name(wt.name + "-sibling"))):
        target.mkdir(exist_ok=True)
        (proc / pid).mkdir(parents=True)
        (proc / pid / "cwd").symlink_to(target)
    (proc / "self").mkdir()
    (proc / "101" / "comm").write_text("worker\n")
    held = gc_mod._cwd_holders(wt, str(proc))
    assert held == ["pid 101 (worker)"]            # not 102 (elsewhere), not 103 (name prefix only)
    (proc / "104" / "cwd").mkdir(parents=True)     # readlink() fails: cannot say who is in there
    monkeypatch.setattr(gc_mod, "CWD_UNREADABLE_BLOCKS", True)
    assert gc_mod._cwd_holders(wt, str(proc)) is None
    monkeypatch.setattr(gc_mod, "CWD_UNREADABLE_BLOCKS", False)
    assert gc_mod._cwd_holders(wt, str(proc)) == ["pid 101 (worker)"]
    assert gc_mod._cwd_holders(wt, str(tmp_path / "no-proc-here")) is None


def test_path_mismatch_blocks(env):
    # a row that points at another clean, pushed worktree — here a live service deploy tree
    deploy = worktree_mod.WORKTREE_DIR / "spend-guard-deploy"
    _git(env.repo, "worktree", "add", "-q", "--detach", str(deploy), "origin/main")
    wt = env.worktree("task-path001")
    env.row("task-path001", "done", worktree=deploy)
    env.row("task-path002", "done", worktree=env.repo)                 # the repo itself
    env.row("task-path003", "done",     # same directory, spelled with a detour
            worktree=os.path.join(str(env.worktrees), "..", env.worktrees.name, deploy.name))
    res = reap_worktrees(dry_run=False)
    for tid in ("task-path001", "task-path002", "task-path003"):
        assert entry(res, "skipped", tid)["action"] == "skipped_path_mismatch", tid
        assert entry(res, "skipped", tid)["size_bytes"] is None        # not even walked
    assert deploy.exists() and env.repo.exists() and wt.exists()


def test_row_path_clean_but_computed_path_holds_unpushed_work(env):
    # remove_worktree() deletes the path IT computes, not the row's. The row
    # points at a clean, pushed tree; the computed path holds unpushed work.
    # Checking the first and deleting the second would lose that work.
    clean = env.worktrees / "some-clean-tree"
    _git(env.repo, "worktree", "add", "-q", "--detach", str(clean), "origin/main")
    victim = env.worktree("task-path004", "local")
    env.row("task-path004", "done", worktree=clean)
    res = reap_worktrees(dry_run=False)
    assert entry(res, "skipped", "task-path004")["action"] == "skipped_path_mismatch"
    assert victim.exists() and (victim / "task-path004.txt").exists() and clean.exists()


def test_symlinked_worktree_path_blocks(env):
    real = env.worktree("task-path010")
    link = worktree_mod.worktree_path(PROJECT, ROLE, "task-path011")
    link.symlink_to(real, target_is_directory=True)
    env.row("task-path011", "done")
    res = reap_worktrees(dry_run=False)
    assert entry(res, "skipped", "task-path011")["action"] == "skipped_path_mismatch"
    assert real.exists() and link.is_symlink()


def test_worktree_of_another_repo_blocks(env):
    # right path, wrong repo: `git worktree remove` from this repo would fail and
    # remove_worktree() would fall back to rmtree
    other = env.base / "other-repo"
    _git(env.base, "clone", "-q", str(env.origin), str(other))
    wt = worktree_mod.worktree_path(PROJECT, ROLE, "task-repo001")
    _git(other, "worktree", "add", "-q", "-b", "agent/developer-task-repo001", str(wt), "origin/main")
    env.row("task-repo001", "done")
    res = reap_worktrees(dry_run=False)
    skipped = entry(res, "skipped", "task-repo001")
    assert skipped["action"] == "skipped_unverifiable" and "belongs to git dir" in skipped["reason"]
    assert wt.exists()


def test_folder_with_no_task_row_is_never_touched(env):
    for name in ("spend-guard-deploy", "tool-value-deploy"):
        _git(env.repo, "worktree", "add", "-q", "--detach", str(env.worktrees / name), "origin/main")
    stray = env.worktree("task-norow01")                     # a real worktree, but no row
    (env.worktrees / "plain-folder").mkdir()
    (env.worktrees / "plain-folder" / "data.bin").write_bytes(b"x")
    env.row("task-withrow", "done", worktree=env.worktrees / "nowhere")   # a row whose dir is gone
    res = reap_worktrees(dry_run=False)
    assert ids(res["removed"]) == set() and ids(res["skipped"]) == set()
    for p in (env.worktrees / "spend-guard-deploy", env.worktrees / "tool-value-deploy",
              stray, env.worktrees / "plain-folder" / "data.bin"):
        assert p.exists(), p


def test_second_look_before_removal_aborts_on_change(env, monkeypatch):
    wt = env.worktree("task-twice01")
    env.row("task-twice01", "done")
    calls = []

    def holders(w, *a, **kw):
        calls.append(w)
        return [] if len(calls) == 1 else ["pid 4242 (late-arrival)"]
    monkeypatch.setattr(gc_mod, "_cwd_holders", holders)
    res = reap_worktrees(dry_run=False)
    assert len(calls) == 2
    skipped = entry(res, "skipped", "task-twice01")
    assert skipped["action"] == "skipped_changed" and "late-arrival" in skipped["reason"]
    assert wt.exists()


def test_second_look_aborts_when_a_file_appears_between_checks(env, monkeypatch):
    wt = env.worktree("task-twice02")
    env.row("task-twice02", "done")
    real = gc_mod._cwd_holders
    calls = []

    def holders(w, *a, **kw):
        calls.append(w)
        if len(calls) == 1:                      # after the first look, before the second
            (wt / "REPORT.md").write_text("a runner file, but new\n")
        return real(w, *a, **kw)
    monkeypatch.setattr(gc_mod, "_cwd_holders", holders)
    res = reap_worktrees(dry_run=False)
    assert entry(res, "skipped", "task-twice02")["action"] == "skipped_changed"
    assert wt.exists()


# --- the command line -------------------------------------------------------

def test_main_prints_df_before_and_after(env, monkeypatch, capsys):
    wt = env.worktree("task-main001")
    env.row("task-main001", "done")
    monkeypatch.setattr(sys, "argv", ["gc_stale_tasks.py", "--reap"])
    assert gc_mod.main() == 0
    out = capsys.readouterr().out
    assert out.index("df before:") < out.index("would remove") < out.index("df after:")
    assert wt.exists()                                      # dry run by default

    monkeypatch.setattr(sys, "argv", ["gc_stale_tasks.py", "--reap", "--go"])
    assert gc_mod.main() == 0
    out = capsys.readouterr().out
    assert out.index("df before:") < out.index("removed ") < out.index("df after:")
    assert "MB" in out and not wt.exists()


# --- scripts/install-org-worktree-reap.sh -----------------------------------

def _fake_checkout(parent: Path) -> Path:
    root = parent / "hq"
    for d in ("scripts/hub", "deploy/systemd", "tools", "lib", "runners", ".venv/bin"):
        (root / d).mkdir(parents=True)
    for rel in ("scripts/install-org-worktree-reap.sh",
                "deploy/systemd/org-worktree-reap.service",
                "deploy/systemd/org-worktree-reap.timer"):
        shutil.copy(ROOT / rel, root / rel)
    for rel in ("tools/gc_stale_tasks.py", "scripts/hub/with-org-db-env.sh", ".venv/bin/python"):
        (root / rel).write_text("#!/bin/sh\n")
        (root / rel).chmod(0o755)
    for d in root.rglob("*"):
        if d.is_dir():
            d.chmod(0o755)
    root.chmod(0o755)
    return root


def _run_installer(root: Path, units: Path, log: Path, action: str):
    fake = root.parent / "fake-systemctl"
    fake.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n')
    fake.chmod(0o755)
    env = dict(os.environ, ORG_REAP_UNIT_DIR=str(units), ORG_REAP_SYSTEMCTL=str(fake))
    return subprocess.run(["bash", str(root / "scripts/install-org-worktree-reap.sh"), action],
                          capture_output=True, text=True, env=env)


def test_installer_is_idempotent_and_fills_in_the_checkout(tmp_path):
    root = _fake_checkout(tmp_path)
    units, log = tmp_path / "units", tmp_path / "systemctl.log"
    first = _run_installer(root, units, log, "install")
    assert first.returncode == 0, first.stderr
    service = (units / "org-worktree-reap.service").read_text()
    timer = (units / "org-worktree-reap.timer").read_text()
    assert "@ROOT@" not in service + timer
    assert f"ExecStart=/bin/bash {root}/scripts/hub/with-org-db-env.sh {root}/.venv/bin/python " \
           f"{root}/tools/gc_stale_tasks.py --reap --go" in service
    assert "User=root" in service and "OnCalendar=*-*-* 00/6:30:00 Asia/Bangkok" in timer
    assert sorted(p.name for p in units.iterdir()) == ["org-worktree-reap.service", "org-worktree-reap.timer"]

    second = _run_installer(root, units, log, "install")
    assert second.returncode == 0, second.stderr
    assert (units / "org-worktree-reap.service").read_text() == service
    assert (units / "org-worktree-reap.timer").read_text() == timer
    calls = log.read_text().splitlines()
    assert calls == ["daemon-reload", "enable org-worktree-reap.timer",
                     "restart org-worktree-reap.timer"] * 2

    gone = _run_installer(root, units, log, "uninstall")
    assert gone.returncode == 0 and list(units.iterdir()) == []


def test_installer_refuses_a_checkout_inside_worktrees(tmp_path):
    parent = tmp_path / "worktrees" / "a-task"
    parent.mkdir(parents=True)
    root = _fake_checkout(parent)
    units, log = tmp_path / "units", tmp_path / "systemctl.log"
    res = _run_installer(root, units, log, "install")
    assert res.returncode != 0 and "worktrees/" in res.stderr
    assert not units.exists() and not log.exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-p", "no:cacheprovider"]))
