"""Tests for tools/maintab.py — the Main Tab (window titlebar) layer.

The two-layer tab only works while each layer stays in its own lane:

    OSC 1 -> tab strip       (tab-title.sh, colored, carries "<ROLE> #<sid>")
    OSC 2 -> window titlebar (maintab.py, goal + progress + clock)

OSC 0 writes BOTH, so any accidental use of it makes one layer eat the other.
test_push_uses_osc2_only covers that from this side; scripts/test_tab_title.py
asserts the OSC 1 half.

Run via:   python3 scripts/test_maintab.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import maintab  # noqa: E402


def _mark(ok: bool, msg: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


class _FakeRoot:
    """Point maintab at a throwaway state dir holding one fake session."""

    def __init__(self, tmp: Path, role: str = "cto", sid: str = "testsid1"):
        self.role, self.sid = role, sid
        self.titles = tmp / "tab-titles"
        self.locks = tmp / "locks"
        self.titles.mkdir(parents=True, exist_ok=True)
        self.locks.mkdir(parents=True, exist_ok=True)
        self.faketty = tmp / "faketty"
        self.faketty.write_text("")
        (self.locks / f"{role}-{sid}.tty").write_text(str(self.faketty) + "\n")
        (self.titles / f"{role}-{sid}.base").write_text(f"CTO #{sid}\n")
        self._saved = (maintab._TITLE_DIR, maintab._LOCKS, maintab._PIDFILE)

    def __enter__(self):
        maintab._TITLE_DIR = self.titles
        maintab._LOCKS = self.locks
        maintab._PIDFILE = self.locks / "maintab-daemon.pid"
        return self

    def __exit__(self, *exc):
        maintab._TITLE_DIR, maintab._LOCKS, maintab._PIDFILE = self._saved
        return False

    def tty_text(self) -> str:
        return self.faketty.read_text()


def test_bar_endpoints() -> bool:
    return (
        maintab.render_bar(0) == "░" * 10
        and maintab.render_bar(100) == "▓" * 10
        and len(maintab.render_bar(37)) == 10
    )


def test_percent_from_done_total() -> bool:
    return (
        maintab.progress_percent({"done": 12, "total": 13}) == 92
        and maintab.progress_percent({"done": 0, "total": 13}) == 0
        and maintab.progress_percent({}) is None
        # total=0 must not raise ZeroDivisionError
        and maintab.progress_percent({"done": 1, "total": 0}) is None
    )


def test_explicit_percent_wins_and_clamps() -> bool:
    return (
        maintab.progress_percent({"percent": 62, "done": 1, "total": 13}) == 62
        and maintab.progress_percent({"percent": 150}) == 100
        and maintab.progress_percent({"percent": -5}) == 0
    )


def test_elapsed_format() -> bool:
    f = maintab.format_elapsed
    return (
        f(0) == "0m"
        and f(59) == "0m"
        and f(42 * 60) == "42m"
        and f(2 * 3600 + 14 * 60) == "2h14m"
        and f(3600) == "1h00m"
        and f(26 * 3600) == "1d2h"
        and f(-5) == "0m"  # clock skew must not produce a negative
    )


def test_render_has_goal_bar_and_clock(tmp: Path) -> bool:
    with _FakeRoot(tmp / "a") as fr:
        maintab.set_main(fr.role, fr.sid, goal="ทำแท็บ 2 ชั้น", done=12, total=13)
        started = datetime.now(timezone.utc) - timedelta(hours=2, minutes=14)
        maintab.write_state(fr.role, fr.sid,
                            {**maintab.read_state(fr.role, fr.sid),
                             "started": started.isoformat()})
        line = maintab.render(fr.role, fr.sid)
    return (
        line.startswith("🎯 ทำแท็บ 2 ชั้น")
        and "92%" in line
        and "▓" in line
        and "⏱ 2h14m" in line
    )


def test_render_without_progress_omits_bar(tmp: Path) -> bool:
    with _FakeRoot(tmp / "b") as fr:
        maintab.set_main(fr.role, fr.sid, goal="แค่เป้า")
        line = maintab.render(fr.role, fr.sid)
    return "🎯 แค่เป้า" in line and "▓" not in line and "%" not in line


def test_render_falls_back_to_base_name(tmp: Path) -> bool:
    """No goal set yet -> use '<ROLE> #<sid>' rather than an empty target."""
    with _FakeRoot(tmp / "c") as fr:
        line = maintab.render(fr.role, fr.sid)
    return "CTO #testsid1" in line


def test_long_goal_truncated(tmp: Path) -> bool:
    with _FakeRoot(tmp / "d") as fr:
        maintab.set_main(fr.role, fr.sid, goal="x" * 200)
        line = maintab.render(fr.role, fr.sid)
    return "…" in line and len(line) < 120


def test_set_preserves_unpassed_fields(tmp: Path) -> bool:
    """Updating progress alone must not clear the goal, and vice versa."""
    with _FakeRoot(tmp / "e") as fr:
        maintab.set_main(fr.role, fr.sid, goal="เป้าเดิม", done=1, total=10)
        maintab.set_main(fr.role, fr.sid, done=7, total=10)   # progress only
        s1 = maintab.read_state(fr.role, fr.sid)
        maintab.set_main(fr.role, fr.sid, goal="เป้าใหม่")     # goal only
        s2 = maintab.read_state(fr.role, fr.sid)
    return (
        s1.get("goal") == "เป้าเดิม" and s1.get("done") == 7
        and s2.get("goal") == "เป้าใหม่" and s2.get("done") == 7
    )


def test_push_uses_osc2_only(tmp: Path) -> bool:
    """The whole two-layer design rests on this: OSC 2, never OSC 0 or 1."""
    with _FakeRoot(tmp / "f") as fr:
        maintab.set_main(fr.role, fr.sid, goal="เป้า", done=1, total=2)
        ok = maintab.push(fr.role, fr.sid)
        written = fr.tty_text()
    return (
        ok
        and written.startswith("\x1b]2;")
        and written.endswith("\x07")
        and "\x1b]0;" not in written
        and "\x1b]1;" not in written
    )


def test_push_false_when_tty_gone(tmp: Path) -> bool:
    """A closed session must be skipped quietly, not raise in the daemon."""
    with _FakeRoot(tmp / "g") as fr:
        maintab.set_main(fr.role, fr.sid, goal="เป้า")
        (fr.locks / f"{fr.role}-{fr.sid}.tty").unlink()
        return maintab.push(fr.role, fr.sid) is False


def test_live_sessions_lists_only_sessions_with_tty(tmp: Path) -> bool:
    with _FakeRoot(tmp / "h") as fr:
        maintab.set_main(fr.role, fr.sid, goal="เป้า")
        alive = maintab.live_sessions()
        # a second session with state but no tty lock (already closed)
        maintab.write_state("cmo", "deadsid1", {"goal": "ตายแล้ว"})
        after = maintab.live_sessions()
    return alive == [("cto", "testsid1")] and after == [("cto", "testsid1")]


# ---------------------------------------------------------------------------
# daemon single-instance (TOCTOU race, orphan duplicates, stale pidfile)
# ---------------------------------------------------------------------------
# Every fake daemon below carries `--pidfile <tmp>` on its command line, which
# is what maintab._is_our_daemon() matches on. That keeps these tests off the
# CEO's real daemon (default pidfile) even though stop_daemon scans the whole
# process table.
class _FakeSubprocess:
    """Stands in for maintab.subprocess: Popen stubbed, the rest real.

    Only spawning is faked — the `ps` identity checks go through
    subprocess.run and must stay real for these tests to mean anything.
    """

    DEVNULL = subprocess.DEVNULL
    SubprocessError = subprocess.SubprocessError
    run = staticmethod(subprocess.run)

    def __init__(self, pid: int, delay: float = 0.0):
        self.pid, self.delay, self.calls = pid, delay, []
        self._lock = threading.Lock()

    def Popen(self, argv, **kw):  # noqa: N802 - mirrors subprocess.Popen
        with self._lock:
            self.calls.append(argv)
        time.sleep(self.delay)  # exec latency: the old code's race window
        return SimpleNamespace(pid=self.pid)


def _stub_pkg(tmp: Path) -> Path:
    """A `tools.maintab` stand-in that only sleeps.

    A daemon is recognised by the exact argv shape `python -m tools.maintab
    daemon ...`, so a fake has to be launched that way too — but running the
    real module would push OSC 2 to the CEO's live ttys. Importing this stub
    instead gives the right command line and does nothing else.
    """
    pkg = tmp / "stubpkg" / "tools"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "maintab.py").write_text("import time\ntime.sleep(300)\n")
    return pkg.parent


def _fake_daemon(pidfile: Path, stub: Path) -> subprocess.Popen:
    """A harmless sleeper whose command line reads as a maintab daemon."""
    return subprocess.Popen(
        [sys.executable, "-m", "tools.maintab", "daemon",
         "--interval", "3600", "--pidfile", str(pidfile)],
        cwd=str(stub), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _reap(*procs: subprocess.Popen) -> None:
    for p in procs:
        if p.poll() is None:
            p.kill()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def _await_daemon(p: subprocess.Popen, timeout: float = 10.0) -> bool:
    """Wait until the fake has exec'd and ps reports it as our daemon."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        cmd = maintab._ps(["-p", str(p.pid), "-ww", "-o", "command="]).strip()
        if maintab._is_our_daemon(cmd):
            return True
        time.sleep(0.05)
    return False


def _exited(p: subprocess.Popen, timeout: float = 5.0) -> bool:
    try:
        p.wait(timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        return False


def test_concurrent_ensure_spawns_one_daemon(tmp: Path) -> bool:
    """The whole point: ensure-daemon fires on EVERY status update of EVERY
    session, so simultaneous callers must still produce exactly one daemon."""
    with _FakeRoot(tmp / "i"):
        fake = _fake_daemon(maintab._PIDFILE, _stub_pkg(tmp / "i"))
        ready = _await_daemon(fake)
        shim = _FakeSubprocess(fake.pid, delay=0.05)
        real, maintab.subprocess = maintab.subprocess, shim
        try:
            threads = [threading.Thread(target=maintab.ensure_daemon)
                       for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(30)
        finally:
            maintab.subprocess = real
            _reap(fake)
        recorded = maintab._PIDFILE.read_text().strip()
    return ready and len(shim.calls) == 1 and recorded == str(fake.pid)


_CLAIM = """
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from tools import maintab
maintab._PIDFILE = Path(sys.argv[2])
status, fd = maintab._try_lock(maintab._run_lock_path())
Path(sys.argv[3]).write_text(status)
while not Path(sys.argv[4]).exists():   # hold the claim until every sibling tried
    time.sleep(0.02)
raise SystemExit(0 if status == "won" else 7)
"""


def test_run_lock_admits_one_process(tmp: Path) -> bool:
    """The claim itself, across real processes — not just one interpreter."""
    with _FakeRoot(tmp / "j"):
        results = tmp / "j" / "claims"
        results.mkdir(parents=True, exist_ok=True)
        go = results / "go"
        procs = [
            subprocess.Popen(
                [sys.executable, "-c", _CLAIM, str(ROOT),
                 str(maintab._PIDFILE), str(results / f"r{i}"), str(go)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for i in range(8)
        ]
        deadline = time.monotonic() + 30
        while (time.monotonic() < deadline
               and len(list(results.glob("r*"))) < len(procs)):
            time.sleep(0.05)
        go.write_text("go")
        codes = []
        for p in procs:
            try:
                codes.append(p.wait(timeout=15))
            except subprocess.TimeoutExpired:
                codes.append(None)
        _reap(*procs)
    return codes.count(0) == 1 and codes.count(7) == len(procs) - 1


def test_stop_clears_untracked_duplicate(tmp: Path) -> bool:
    """An orphan daemon keeps writing titlebars forever with nothing tracking
    it, so stop must clear every daemon, not just the recorded pid."""
    with _FakeRoot(tmp / "k"):
        stub = _stub_pkg(tmp / "k")
        tracked = _fake_daemon(maintab._PIDFILE, stub)
        orphan = _fake_daemon(maintab._PIDFILE, stub)
        ready = _await_daemon(tracked) and _await_daemon(orphan)
        maintab._PIDFILE.write_text(str(tracked.pid))  # only one is recorded
        try:
            stopped = maintab.stop_daemon()
            gone = _exited(tracked) and _exited(orphan)
            cleared = not maintab._PIDFILE.exists()
        finally:
            _reap(tracked, orphan)
    return ready and stopped and gone and cleared


def test_foreign_pidfile_does_not_block_start(tmp: Path) -> bool:
    """A recycled pid owned by an unrelated process must not look like a live
    daemon — otherwise startup is blocked until someone deletes the file."""
    with _FakeRoot(tmp / "l"):
        foreign = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(120)"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        maintab._PIDFILE.write_text(str(foreign.pid))
        alive = maintab._daemon_alive()

        fake = _fake_daemon(maintab._PIDFILE, _stub_pkg(tmp / "l"))
        ready = _await_daemon(fake)
        shim = _FakeSubprocess(fake.pid)
        real, maintab.subprocess = maintab.subprocess, shim
        try:
            started = maintab.ensure_daemon()
        finally:
            maintab.subprocess = real
            _reap(foreign, fake)
    return (alive is None and ready and len(shim.calls) == 1
            and started == fake.pid)


def test_daemon_match_is_argv_anchored(tmp: Path) -> bool:
    """stop_daemon kills what it matches, so the matcher must not fire on a
    command line that merely *quotes* the daemon command — an agent session
    carrying this task's text in its argv did exactly that (2026-08-03).
    """
    with _FakeRoot(tmp / "n"):
        pidfile = str(maintab._PIDFILE)
        ours = ("/usr/bin/python3 -m tools.maintab daemon "
                f"--interval 60 --pidfile {pidfile}")
        agent = ("claude -n 'DevOps Engineer' --append-system-prompt "
                 f"run python3 -m tools.maintab daemon --pidfile {pidfile}")
        other_statedir = "/usr/bin/python3 -m tools.maintab daemon --interval 60"
        ensure = "/usr/bin/python3 -m tools.maintab ensure-daemon"
        unrelated = "/bin/sleep 300"
        return (maintab._is_our_daemon(ours)
                and not maintab._is_our_daemon(agent)
                and not maintab._is_our_daemon(other_statedir)
                and not maintab._is_our_daemon(ensure)
                and not maintab._is_our_daemon(unrelated))


def test_run_daemon_loses_lock_quietly(tmp: Path) -> bool:
    """Losing the race is the expected outcome, so the loser exits 0 and
    leaves the winner's pidfile alone."""
    with _FakeRoot(tmp / "m"):
        held, fd = maintab._try_lock(maintab._run_lock_path())
        maintab._PIDFILE.write_text("999999")
        try:
            rc = maintab.run_daemon(interval=0.01)
        finally:
            maintab._close(fd)
        untouched = maintab._PIDFILE.read_text().strip() == "999999"
    return held == "won" and rc == 0 and untouched


def main() -> int:
    fails = 0
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        cases = [
            (test_bar_endpoints, (),
             "progress bar renders 0%/100%/partial at fixed width"),
            (test_percent_from_done_total, (),
             "percent from done/total, total=0 is safe"),
            (test_explicit_percent_wins_and_clamps, (),
             "explicit percent wins and clamps 0-100"),
            (test_elapsed_format, (),
             "elapsed formats m / h / d and never goes negative"),
            (test_render_has_goal_bar_and_clock, (tmp,),
             "render shows goal + bar + percent + clock"),
            (test_render_without_progress_omits_bar, (tmp,),
             "no progress set -> no bar, no percent"),
            (test_render_falls_back_to_base_name, (tmp,),
             "no goal set -> falls back to '<ROLE> #<sid>'"),
            (test_long_goal_truncated, (tmp,),
             "over-long goal truncated with ellipsis"),
            (test_set_preserves_unpassed_fields, (tmp,),
             "set() preserves fields it wasn't given"),
            (test_push_uses_osc2_only, (tmp,),
             "push writes OSC 2 only (never OSC 0/1)"),
            (test_push_false_when_tty_gone, (tmp,),
             "push returns False when the tty is gone"),
            (test_live_sessions_lists_only_sessions_with_tty, (tmp,),
             "live_sessions skips sessions with no tty"),
            (test_concurrent_ensure_spawns_one_daemon, (tmp,),
             "8 concurrent ensure_daemon calls spawn exactly one daemon"),
            (test_run_lock_admits_one_process, (tmp,),
             "run lock admits exactly one process, losers exit quietly"),
            (test_stop_clears_untracked_duplicate, (tmp,),
             "stop clears an untracked duplicate daemon, not just the pidfile pid"),
            (test_foreign_pidfile_does_not_block_start, (tmp,),
             "stale/foreign pidfile is ignored and startup still happens"),
            (test_daemon_match_is_argv_anchored, (tmp,),
             "daemon match is argv-anchored + pidfile-scoped, not text search"),
            (test_run_daemon_loses_lock_quietly, (tmp,),
             "run_daemon that loses the claim returns 0 and leaves the pidfile"),
        ]
        for fn, args, desc in cases:
            try:
                ok = fn(*args)
            except Exception as e:
                ok, desc = False, f"{desc} — raised {e!r}"
            fails += not ok
            _mark(ok, desc)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
