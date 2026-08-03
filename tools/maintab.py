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
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TITLE_DIR = _ROOT / "state" / "tab-titles"
_LOCKS = _ROOT / "state" / "locks"
_PIDFILE = _LOCKS / "maintab-daemon.pid"
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
def _daemon_alive() -> int | None:
    """Pid of the running daemon, or None."""
    try:
        pid = int(_PIDFILE.read_text().strip())
    except (OSError, ValueError):
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


def ensure_daemon(interval: float = DEFAULT_INTERVAL) -> int | None:
    """Start the daemon if it isn't already running. Returns its pid."""
    pid = _daemon_alive()
    if pid:
        return pid
    _LOCKS.mkdir(parents=True, exist_ok=True)
    try:
        log = open(_DAEMON_LOG, "a")
    except OSError:
        log = subprocess.DEVNULL
    proc = subprocess.Popen(
        [sys.executable, "-m", "tools.maintab", "daemon",
         "--interval", str(interval)],
        cwd=str(_ROOT), stdout=log, stderr=log,
        stdin=subprocess.DEVNULL, start_new_session=True,
    )
    return proc.pid


def stop_daemon() -> bool:
    pid = _daemon_alive()
    if not pid:
        return False
    try:
        os.kill(pid, 15)
    except OSError:
        return False
    _PIDFILE.unlink(missing_ok=True)
    return True


def run_daemon(interval: float = DEFAULT_INTERVAL) -> int:
    """Tick every `interval` seconds, refreshing every live session."""
    if _daemon_alive():
        print("maintab: daemon already running", file=sys.stderr)
        return 1
    _LOCKS.mkdir(parents=True, exist_ok=True)
    _PIDFILE.write_text(str(os.getpid()))
    idle = 0
    try:
        while True:
            pushed = sum(push(role, sid) for role, sid in live_sessions())
            idle = 0 if pushed else idle + 1
            if idle >= _IDLE_TICKS_BEFORE_EXIT:
                return 0  # nothing left to update; don't linger
            time.sleep(interval)
    except KeyboardInterrupt:
        return 0
    finally:
        try:
            if _PIDFILE.read_text().strip() == str(os.getpid()):
                _PIDFILE.unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
_USAGE = """usage: python -m tools.maintab <command>

  set [--goal TEXT] [--progress DONE/TOTAL | --percent N]
                        update this session's goal and/or progress, then push
  push                  redraw this session's Main Tab once
  render                print the line without writing it (debug/tests)
  daemon [--interval S] run the refresh loop in the foreground
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
        return run_daemon(float(interval) if interval else DEFAULT_INTERVAL)

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
