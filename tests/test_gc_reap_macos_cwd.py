"""gc reap on macOS: no /proc, so cwd holders come from lsof (4 Nov 2026: the Mac
reap skipped all 26 worktrees with 'cannot read /proc/*/cwd')."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import gc_stale_tasks as gc  # noqa: E402


def _fake_lsof(stdout, rc=0):
    def run(argv, **kw):
        assert argv[:2] == ["lsof", "-a"]
        return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr="")
    return run


def test_darwin_uses_lsof_and_finds_holder(tmp_path, monkeypatch):
    wt = tmp_path / "wt"
    (wt / "sub").mkdir(parents=True)
    real = str(wt.resolve())
    monkeypatch.setattr(gc.sys, "platform", "darwin")
    monkeypatch.setattr(gc.os.path, "isdir", lambda p: False if p == "/proc" else True)
    out = f"p11\nczsh\nn{real}/sub\np12\ncnode\nn/Users/gob\np13\ncvim\nn{real}2\n"
    monkeypatch.setattr(gc.subprocess, "run", _fake_lsof(out, rc=1))
    assert gc._cwd_holders(wt) == ["pid 11 (zsh)"]


def test_darwin_empty_list_when_nobody_inside(tmp_path, monkeypatch):
    wt = tmp_path / "wt"
    wt.mkdir()
    monkeypatch.setattr(gc.sys, "platform", "darwin")
    monkeypatch.setattr(gc.os.path, "isdir", lambda p: False if p == "/proc" else True)
    monkeypatch.setattr(gc.subprocess, "run", _fake_lsof("p1\nclaunchd\nn/\n"))
    assert gc._cwd_holders(wt) == []


def test_darwin_lsof_failure_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(gc.sys, "platform", "darwin")
    monkeypatch.setattr(gc.os.path, "isdir", lambda p: False if p == "/proc" else True)

    def boom(*a, **k):
        raise FileNotFoundError("lsof")
    monkeypatch.setattr(gc.subprocess, "run", boom)
    assert gc._cwd_holders(tmp_path) is None
    monkeypatch.setattr(gc.subprocess, "run", _fake_lsof("", rc=2))
    assert gc._cwd_holders(tmp_path) is None


def test_linux_never_calls_lsof(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("lsof must not run on Linux")
    monkeypatch.setattr(gc.subprocess, "run", boom)
    proc = tmp_path / "proc"
    proc.mkdir()
    assert gc._cwd_holders(tmp_path / "wt", proc_dir=str(proc)) == []
