"""Watchdog reload on code change (task-c767f98a).

`runners/watchdog.py --loop` records HEAD at startup (`_code_rev`) and, at the
top of each subsequent loop iteration (after `time.sleep`, before `scan_once`),
exits 0 for a service manager restart once HEAD moves and the git dir is not
mid-operation (`_git_busy`).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import runners.watchdog as watchdog

REV_A = "aaaaaaaaaaaa" + "0" * 28
REV_B = "bbbbbbbbbbbb" + "1" * 28


class _LoopStop(Exception):
    """Raised by the time.sleep stub after N calls to stop an infinite loop."""


@pytest.fixture
def drive(monkeypatch, capsys):
    """Stub db.init, scan_once, time.sleep, _code_rev and _git_busy; drive watchdog.main()."""
    monkeypatch.delenv("WATCHDOG_RELOAD_ON_CODE_CHANGE", raising=False)
    monkeypatch.setattr(watchdog.db, "init", lambda: None)

    def run(
        revs: list[str | None] | None = None,
        busy: list[bool] | None = None,
        max_sleeps: int = 5,
        argv: list[str] | None = None,
    ):
        scans = 0
        sleeps = 0
        rev_calls: list[str | None] = []
        busy_calls: list[bool] = []
        rev_seq = list(revs if revs is not None else [REV_A])
        busy_seq = list(busy if busy is not None else [False])

        def fake_scan_once():
            nonlocal scans
            scans += 1
            return {
                "pinged": [],
                "stalled": [],
                "reaped": [],
                "surface_reaped": [],
                "scanned": 0,
                "gc_cancelled": 0,
                "disk_queue_spawned": None,
                "mesh_probe": {},
                "work_watch": {"alerted": [], "lungnote_filed": [], "green": []},
            }

        def fake_sleep(_seconds):
            nonlocal sleeps
            sleeps += 1
            if sleeps >= max_sleeps:
                raise _LoopStop(sleeps)

        def fake_code_rev(root=watchdog.REPO_ROOT):
            val = rev_seq.pop(0) if len(rev_seq) > 1 else rev_seq[0]
            rev_calls.append(val)
            return val

        def fake_git_busy(root=watchdog.REPO_ROOT):
            val = busy_seq.pop(0) if len(busy_seq) > 1 else busy_seq[0]
            busy_calls.append(val)
            return val

        monkeypatch.setattr(watchdog, "scan_once", fake_scan_once)
        monkeypatch.setattr(watchdog.time, "sleep", fake_sleep)
        monkeypatch.setattr(watchdog, "_code_rev", fake_code_rev)
        monkeypatch.setattr(watchdog, "_git_busy", fake_git_busy)
        monkeypatch.setattr(
            sys, "argv", argv if argv is not None else ["watchdog", "--loop", "--interval", "1"]
        )

        stopped = False
        rc = None
        try:
            rc = watchdog.main()
        except _LoopStop:
            stopped = True
        out = capsys.readouterr().out
        return {
            "rc": rc,
            "stopped": stopped,
            "scans": scans,
            "sleeps": sleeps,
            "rev_calls": rev_calls,
            "busy_calls": busy_calls,
            "out": out,
        }

    return run


def test_a_head_changes_after_first_scan_exits_zero(drive):
    res = drive(revs=[REV_A, REV_B], max_sleeps=5)
    assert res["stopped"] is False
    assert res["rc"] == 0
    assert res["scans"] == 1
    assert f"watchdog: code changed {REV_A[:12]}..{REV_B[:12]}; exiting for a restart" in res["out"]


def test_b_head_unchanged_still_looping_after_five_scans(drive):
    res = drive(revs=[REV_A], max_sleeps=5)
    assert res["stopped"] is True
    assert res["rc"] is None
    assert res["scans"] == 5
    assert len(res["rev_calls"]) == 5


def test_c_code_rev_none_at_start_never_exits(drive):
    res = drive(revs=[None, REV_B], max_sleeps=5)
    assert res["stopped"] is True
    assert res["rc"] is None
    assert res["scans"] == 5
    assert res["rev_calls"] == [None]
    assert "watchdog: code reload off (" in res["out"]


def test_d_git_busy_defers_exit_until_clear(drive):
    res = drive(revs=[REV_A, REV_B], busy=[True, False], max_sleeps=5)
    assert res["stopped"] is False
    assert res["rc"] == 0
    assert res["scans"] == 2
    assert res["busy_calls"] == [True, False]
    assert f"watchdog: code changed {REV_A[:12]}..{REV_B[:12]}; exiting for a restart" in res["out"]


def test_e_env_opt_out_disables_reload(drive, monkeypatch):
    monkeypatch.setenv("WATCHDOG_RELOAD_ON_CODE_CHANGE", "0")
    res = drive(revs=[REV_A, REV_B], max_sleeps=5)
    assert res["stopped"] is True
    assert res["rc"] is None
    assert res["scans"] == 5
    assert "watchdog: code reload off (WATCHDOG_RELOAD_ON_CODE_CHANGE=0)" in res["out"]


def test_f_oneshot_mode_never_calls_code_rev(drive):
    res = drive(revs=[REV_A, REV_B], argv=["watchdog"])
    assert res["stopped"] is False
    assert res["rc"] == 0
    assert res["scans"] == 1
    assert res["rev_calls"] == []


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=10
    )
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr}")
    return r.stdout.strip()


def test_g_code_rev_and_git_busy_on_tmp_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")

    (repo / "file.txt").write_text("one\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-q", "-m", "first")

    rev1 = watchdog._code_rev(repo)
    assert rev1 is not None and len(rev1) == 40
    assert rev1 == _git(repo, "rev-parse", "HEAD")
    assert watchdog._git_busy(repo) is False

    (repo / "file.txt").write_text("two\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-q", "-m", "second")

    rev2 = watchdog._code_rev(repo)
    assert rev2 is not None and len(rev2) == 40
    assert rev2 != rev1

    index_lock = repo / ".git" / "index.lock"
    index_lock.write_text("", encoding="utf-8")
    assert watchdog._git_busy(repo) is True

    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / ".git").write_text(f"gitdir: {repo / '.git'}\n", encoding="utf-8")
    assert watchdog._git_busy(linked) is True

    index_lock.unlink()
    assert watchdog._git_busy(repo) is False
    assert watchdog._git_busy(linked) is False
    assert watchdog._code_rev(tmp_path / "not-a-repo") is None
