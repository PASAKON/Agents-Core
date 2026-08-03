"""Main Tab (window titlebar) — the strategic half of the two-layer tab.

iTerm exposes two independent title surfaces on one session, written by two
different escape codes (verified live 2026-08-03):

    OSC 1  -> terminalIconName   -> the TAB strip        (colorable, tab-title.sh)
    OSC 2  -> terminalWindowName -> the WINDOW titlebar  (this module)

So the org uses them for two different jobs:

    Main Tab (here) : 🎯 <session goal> ▓▓▓▓▓▓░░░░ 62% · ⏱ 2h14m
    Sub Tab  (there): CTO #bafbda08 ⏳ <what I'm doing right now>   [colored]

Slow/strategic above, fast/tactical below. The window titlebar is also what
macOS shows in Mission Control and the Window menu, which is exactly where a
goal + progress reading earns its space.

## Why a daemon

`session.creationTime` / `startTime` are both None — iTerm has no built-in
elapsed-time variable, so the clock needs an external driver. One shared
daemon on a 60s tick refreshes every live session from a single loop (CEO
choice 2026-08-03, option B): ~1 wakeup/minute total, versus a per-session
per-second loop that would wake 6 processes 60x more often and make iTerm
repaint 6 titlebars every second for information nobody reads at second
precision.

The periodic re-write is also self-healing: anything that clobbers the
window title (a profile write, a stray OSC 0) is repaired on the next tick.

## Ownership rule

This module writes **OSC 2 only** and never touches OSC 1. `tab-title.sh`
writes **OSC 1 only**. Crossing that line makes one surface eat the other —
note OSC 0 sets BOTH, which is why the status path had to stop using it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

try:  # POSIX only; the daemon degrades to a pidfile-only guard without it.
    import fcntl
except ImportError:  # pragma: no cover - not reachable on mac/linux
    fcntl = None  # type: ignore[assignment]

from tools.itermtab import sync_dev_tab_colors

_ROOT = Path(__file__).resolve().parent.parent
_TITLE_DIR = _ROOT / "state" / "tab-titles"
_LOCKS = _ROOT / "state" / "locks"
_PIDFILE = _LOCKS / "maintab-daemon.pid"
# The pidfile a daemon started with no --pidfile is understood to own. Used to
# recognise legacy / hand-started daemons in the process table.
_DEFAULT_PIDFILE = _PIDFILE
_DAEMON_LOG = _LOCKS / "maintab-daemon.log"

DEFAULT_INTERVAL = 60.0
# Exit after this many consecutive ticks with nothing to update, so a
# forgotten daemon doesn't outlive the org by days.
_IDLE_TICKS_BEFORE_EXIT = 10

_BAR_WIDTH = 10
_BAR_FULL = "▓"
_BAR_EMPTY = "░"
# Titlebars have room, but an unbounded goal turns one into a paragraph.
# Cap the goal; the bar/percent/clock tail is always kept.
_GOAL_MAX = 60


# ---------------------------------------------------------------------------
# session identity
# ---------------------------------------------------------------------------
def session_key(role: str | None = None, sid: str | None = None) -> tuple[str, str]:
    """(role, session_id) from args or env. Exits 2 when the session is unknown."""
    role = role or os.environ.get("CXO_ROLE") or "cto"
    sid = sid or os.environ.get("CXO_SESSION_ID") or os.environ.get("CTO_SESSION_ID")
    if not sid:
        print("maintab: no CXO_SESSION_ID / CTO_SESSION_ID in env", file=sys.stderr)
        raise SystemExit(2)
    return role, sid


def _state_path(role: str, sid: str) -> Path:
    return _TITLE_DIR / f"{role}-{sid}.main.json"


def _tty_path(role: str, sid: str) -> Path:
    return _LOCKS / f"{role}-{sid}.tty"


def _base_name(role: str, sid: str) -> str:
    """The stable '<ROLE> #<sid>' prefix, used as the goal fallback."""
    try:
        line = (_TITLE_DIR / f"{role}-{sid}.base").read_text().splitlines()[0].strip()
        if line:
            return line
    except (OSError, IndexError):
        pass
    return f"{role.upper()} #{sid}"


def _session_started(role: str, sid: str) -> datetime:
    """Best-effort session start: the spawn-time lock file's mtime.

    The launcher writes state/locks/<role>-<sid>.tty when the session is
    created, so its mtime is the closest thing to a real start timestamp.
    Falls back to now() when the lock is missing — elapsed then reads 0m and
    grows from first sight, which beats raising.
    """
    try:
        return datetime.fromtimestamp(_tty_path(role, sid).stat().st_mtime,
                                      tz=timezone.utc)
    except OSError:
        return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------
def read_state(role: str, sid: str) -> dict:
    try:
        data = json.loads(_state_path(role, sid).read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(role: str, sid: str, state: dict) -> None:
    _TITLE_DIR.mkdir(parents=True, exist_ok=True)
    _state_path(role, sid).write_text(json.dumps(state, ensure_ascii=False))


def set_main(role: str, sid: str, goal: str | None = None,
             done: int | None = None, total: int | None = None,
             percent: int | None = None) -> dict:
    """Update goal and/or progress, preserving whatever isn't passed."""
    state = read_state(role, sid)
    if goal is not None:
        state["goal"] = goal
    if done is not None and total is not None:
        state["done"], state["total"] = done, total
        state.pop("percent", None)  # done/total wins over a stale raw percent
    if percent is not None:
        state["percent"] = max(0, min(100, percent))
        state.pop("done", None)
        state.pop("total", None)
    state.setdefault("started", _session_started(role, sid).isoformat())
    write_state(role, sid, state)
    return state


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def progress_percent(state: dict) -> int | None:
    """Percent from explicit `percent`, else from done/total. None if unset."""
    if isinstance(state.get("percent"), int):
        return max(0, min(100, state["percent"]))
    done, total = state.get("done"), state.get("total")
    if isinstance(done, int) and isinstance(total, int) and total > 0:
        return max(0, min(100, round(done / total * 100)))
    return None


def render_bar(percent: int, width: int = _BAR_WIDTH) -> str:
    filled = round(percent / 100 * width)
    return _BAR_FULL * filled + _BAR_EMPTY * (width - filled)


def format_elapsed(seconds: float) -> str:
    """Coarse elapsed: 42m / 2h14m / 1d3h.

    Minute precision is deliberate — second precision would be pure churn on
    a session measured in hours.
    """
    seconds = max(0, int(seconds))
    minutes, hours = seconds // 60, seconds // 3600
    if hours >= 24:
        return f"{hours // 24}d{hours % 24}h"
    if hours >= 1:
        return f"{hours}h{minutes % 60:02d}m"
    return f"{minutes}m"


def render(role: str, sid: str, now: datetime | None = None) -> str:
    """The full Main Tab line for one session."""
    state = read_state(role, sid)
    now = now or datetime.now(timezone.utc)

    goal = " ".join(((state.get("goal") or "").strip()
                     or _base_name(role, sid)).split())
    if len(goal) > _GOAL_MAX:
        goal = goal[: _GOAL_MAX - 1] + "…"

    try:
        started = datetime.fromisoformat(state["started"])
    except (KeyError, TypeError, ValueError):
        started = _session_started(role, sid)
    elapsed = format_elapsed((now - started).total_seconds())

    pct = progress_percent(state)
    if pct is None:
        return f"🎯 {goal} · ⏱ {elapsed}"
    return f"🎯 {goal} {render_bar(pct)} {pct}% · ⏱ {elapsed}"


# ---------------------------------------------------------------------------
# writing to the terminal
# ---------------------------------------------------------------------------
def push(role: str, sid: str, now: datetime | None = None) -> bool:
    """Write this session's Main Tab via OSC 2. False if the tty is gone."""
    try:
        tty = _tty_path(role, sid).read_text().strip()
    except OSError:
        return False
    if not tty:
        return False
    try:
        with open(tty, "w") as fh:
            fh.write(f"\033]2;{render(role, sid, now)}\007")
        return True
    except OSError:
        # Session closed, or its pty is no longer writable — not an error.
        return False


def live_sessions() -> list[tuple[str, str]]:
    """Every (role, sid) with Main Tab state and a still-present tty lock."""
    out = []
    for path in sorted(_TITLE_DIR.glob("*.main.json")):
        stem = path.name[: -len(".main.json")]
        role, _, sid = stem.partition("-")
        if sid and _tty_path(role, sid).exists():
            out.append((role, sid))
    return out


# ---------------------------------------------------------------------------
# daemon
# ---------------------------------------------------------------------------
# `ensure-daemon` fires on every status update of every C-level session, so two
# callers racing each other is the NORMAL case, not an exotic one. Two locks,
# two jobs (2026-08-03, fixing a double-daemon TOCTOU):
#
#   <pidfile>.spawnlock  held for milliseconds by ensure_daemon() while it
#                        decides whether to spawn, so two concurrent callers
#                        cannot both read "not running" and both spawn.
#   <pidfile>.lock       held for its whole life by the daemon that won
#                        run_daemon(). The kernel drops it on exit — including
#                        kill -9 — so unlike a pidfile it can never go stale.
#
# flock rather than an O_EXCL pidfile precisely because of that: an O_EXCL
# claim outlives the process that made it, so one hard-killed daemon would
# lock out every future one until someone deleted the file by hand.
_DAEMON_MARKER = "tools.maintab"
# The exact argv[1:4] of a daemon: `python -m tools.maintab daemon ...`.
_DAEMON_ARGV = ("-m", _DAEMON_MARKER, "daemon")


def _run_lock_path() -> Path:
    return _PIDFILE.with_name(_PIDFILE.name + ".lock")


def _spawn_lock_path() -> Path:
    return _PIDFILE.with_name(_PIDFILE.name + ".spawnlock")


def _try_lock(path: Path) -> tuple[str, int | None]:
    """Non-blocking exclusive flock. ('won', fd) | ('busy', None) | ('unsupported', None)."""
    if fcntl is None:
        return "unsupported", None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    except OSError:
        return "unsupported", None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        _close(fd)
        return "busy", None
    return "won", fd


def _close(fd: int | None) -> None:
    if fd is None:
        return
    try:
        os.close(fd)  # also releases the flock
    except OSError:
        pass


@contextmanager
def _spawn_gate(timeout: float = 5.0):
    """Serialise the check-then-spawn decision. Proceeds ungated on timeout.

    A status update must never hang on a wedged lock holder, so waiting past
    `timeout` degrades to the old racy path rather than blocking — the run lock
    is what actually guarantees one daemon.
    """
    deadline = time.monotonic() + timeout
    fd = None
    while True:
        status, fd = _try_lock(_spawn_lock_path())
        if status != "busy" or time.monotonic() >= deadline:
            break
        time.sleep(0.02)
    try:
        yield
    finally:
        _close(fd)


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _ps(args: list[str]) -> str:
    try:
        out = subprocess.run(["ps", *args], capture_output=True, text=True,
                             timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout


def _is_our_daemon(cmd: str) -> bool:
    """Does this command line belong to a maintab daemon owning OUR pidfile?

    Two independent guards: the argv shape (a recycled pid held by an
    unrelated process won't have it) and the pidfile it owns (a daemon of a
    different state dir points elsewhere — which is also what keeps the tests
    off the CEO's real daemon).

    The argv match is anchored at argv[1:4] deliberately. A loose "contains
    tools.maintab and daemon" match also hits any agent session whose prompt
    quotes the command — observed live 2026-08-03, where a DEV agent's own
    argv carried this task's text — and stop_daemon kills what it matches.
    """
    tokens = cmd.split()
    if tuple(tokens[1:4]) != _DAEMON_ARGV:
        return False
    return _pidfile_of(tokens) == _resolve(_PIDFILE)


def _pidfile_of(tokens: list[str]) -> Path | None:
    if "--pidfile" in tokens:
        idx = tokens.index("--pidfile")
        return _resolve(Path(tokens[idx + 1])) if idx + 1 < len(tokens) else None
    return _resolve(_DEFAULT_PIDFILE)  # no flag -> the default pidfile


def _resolve(path: Path) -> Path | None:
    try:
        return Path(path).resolve()
    except OSError:
        return None


def _daemon_alive() -> int | None:
    """Pid of the running daemon, or None.

    A pidfile alone proves nothing: the pid may be dead, or recycled by an
    unrelated process, which would otherwise block startup forever. The pid
    must still be running AND still look like our daemon.
    """
    try:
        pid = int(_PIDFILE.read_text().strip())
    except (OSError, ValueError):
        return None
    if pid <= 0 or not _pid_running(pid):
        return None
    if not _is_our_daemon(_ps(["-p", str(pid), "-ww", "-o", "command="]).strip()):
        return None  # stale / foreign pidfile — treat as not running
    return pid


def _daemon_pids() -> list[int]:
    """Every maintab daemon owning our pidfile, tracked or not."""
    pids = []
    me = os.getpid()
    for line in _ps(["-A", "-ww", "-o", "pid=,command="]).splitlines():
        pid_s, _, cmd = line.strip().partition(" ")
        try:
            pid = int(pid_s)
        except ValueError:
            continue
        if pid != me and _is_our_daemon(cmd):
            pids.append(pid)
    return pids


def _write_pidfile(pid: int) -> None:
    try:
        _PIDFILE.parent.mkdir(parents=True, exist_ok=True)
        _PIDFILE.write_text(str(pid))
    except OSError:
        pass


def ensure_daemon(interval: float = DEFAULT_INTERVAL) -> int | None:
    """Start the daemon if it isn't already running. Returns its pid."""
    try:
        _LOCKS.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    with _spawn_gate():
        pid = _daemon_alive()
        if pid:
            return pid
        try:
            log = open(_LOCKS / _DAEMON_LOG.name, "a")
        except OSError:
            log = subprocess.DEVNULL
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "tools.maintab", "daemon",
                 "--interval", str(interval), "--pidfile", str(_PIDFILE)],
                cwd=str(_ROOT), stdout=log, stderr=log,
                stdin=subprocess.DEVNULL, start_new_session=True,
            )
        except OSError:
            return None
        # Record the pid here, inside the gate: the child needs a moment to
        # exec and claim the run lock, and until then the next ensure-daemon
        # call would otherwise see an empty pidfile and spawn a second one.
        _write_pidfile(proc.pid)
        return proc.pid


def stop_daemon() -> bool:
    """Stop every running daemon, tracked by the pidfile or not.

    Signalling only the recorded pid orphans any duplicate — from an old race
    or a hand-started `tools.maintab daemon` — and an orphan keeps writing
    titlebars with nothing tracking it.
    """
    targets = set(_daemon_pids())
    try:
        pid = int(_PIDFILE.read_text().strip())
    except (OSError, ValueError):
        pid = 0
    if pid > 0 and pid != os.getpid() and _pid_running(pid):
        targets.add(pid)
    targets.discard(os.getpid())
    if not targets:
        _unlink_pidfile()
        return False

    for pid in targets:
        _signal(pid, 15)
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        targets = {pid for pid in targets if _pid_running(pid)}
        if not targets:
            break
        time.sleep(0.05)
    for pid in targets:  # ignored SIGTERM / wedged in a syscall
        _signal(pid, 9)
    _unlink_pidfile()
    return True


def _signal(pid: int, sig: int) -> None:
    try:
        os.kill(pid, sig)
    except OSError:
        pass


def _unlink_pidfile() -> None:
    try:
        _PIDFILE.unlink(missing_ok=True)
    except OSError:
        pass


def run_daemon(interval: float = DEFAULT_INTERVAL,
               pidfile: str | None = None) -> int:
    """Tick every `interval` seconds, refreshing every live session.

    Exactly one daemon per pidfile survives: the run lock is claimed here, and
    losing that claim is the expected outcome of a concurrent ensure-daemon, so
    the loser exits 0 in silence rather than treating it as an error.
    """
    global _PIDFILE
    if pidfile:
        _PIDFILE = Path(pidfile)
    try:
        _LOCKS.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    status, lock_fd = _try_lock(_run_lock_path())
    if status == "busy":
        return 0  # another daemon owns the tick
    if status == "unsupported":
        # No flock available: fall back to the pidfile, ignoring an entry that
        # names us (ensure_daemon writes our pid before we get here).
        running = _daemon_alive()
        if running and running != os.getpid():
            return 0

    _write_pidfile(os.getpid())
    idle = 0
    try:
        while True:
            pushed = sum(push(role, sid) for role, sid in live_sessions())
            # DEV tab color sync (task-0942febc): one call, degrades to a
            # no-op internally on any failure — never counted in `idle`,
            # since the Main Tab exit condition above is unrelated to it.
            sync_dev_tab_colors()
            idle = 0 if pushed else idle + 1
            if idle >= _IDLE_TICKS_BEFORE_EXIT:
                return 0  # nothing left to update; don't linger
            time.sleep(interval)
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            if _PIDFILE.read_text().strip() == str(os.getpid()):
                _unlink_pidfile()
        except OSError:
            pass
        _close(lock_fd)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
_USAGE = """usage: python -m tools.maintab <command>

  set [--goal TEXT] [--progress DONE/TOTAL | --percent N]
                        update this session's goal and/or progress, then push
  push                  redraw this session's Main Tab once
  render                print the line without writing it (debug/tests)
  daemon [--interval S] [--pidfile PATH]
                        run the refresh loop in the foreground
  ensure-daemon         start the daemon if not already running
  stop-daemon           stop it
  status                show daemon pid + every live session's line
"""


def _parse_progress(value: str) -> tuple[int, int]:
    done, _, total = value.partition("/")
    return int(done), int(total)


def main(argv: list[str]) -> int:
    if not argv:
        print(_USAGE, file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]

    def opt(name: str) -> str | None:
        idx = rest.index(name) if name in rest else -1
        return rest[idx + 1] if 0 <= idx < len(rest) - 1 else None

    if cmd == "set":
        role, sid = session_key()
        progress, percent = opt("--progress"), opt("--percent")
        done = total = None
        if progress:
            try:
                done, total = _parse_progress(progress)
            except ValueError:
                print("maintab: --progress wants DONE/TOTAL, e.g. 12/13",
                      file=sys.stderr)
                return 2
        set_main(role, sid, goal=opt("--goal"), done=done, total=total,
                 percent=int(percent) if percent else None)
        push(role, sid)
        ensure_daemon()
        print(render(role, sid))
        return 0

    if cmd == "push":
        role, sid = session_key()
        return 0 if push(role, sid) else 1

    if cmd == "render":
        role, sid = session_key()
        print(render(role, sid))
        return 0

    if cmd == "daemon":
        interval = opt("--interval")
        return run_daemon(float(interval) if interval else DEFAULT_INTERVAL,
                          pidfile=opt("--pidfile"))

    if cmd == "ensure-daemon":
        print(f"daemon pid: {ensure_daemon()}")
        return 0

    if cmd == "stop-daemon":
        print("stopped" if stop_daemon() else "not running")
        return 0

    if cmd == "status":
        print(f"daemon pid: {_daemon_alive() or '(not running)'}")
        for role, sid in live_sessions():
            print(f"  {role}-{sid}: {render(role, sid)}")
        return 0

    print(_USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
