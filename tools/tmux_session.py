"""tmux session helper for agent ptys with optional ttyd web bridge.

A tmux session is the single pty source-of-truth. Any number of clients
(iTerm tab via `tmux attach`, browser via `ttyd tmux attach`) can attach
simultaneously and see/type the exact same stream — true two-way realtime
sync, not a log mirror.

API:
    create(session, cwd, cmd)                 — start detached tmux session
    send_keys(session, text)                  — type text + Enter
    has_session(session) -> bool
    kill(session)                             — kill tmux session
    start_ttyd(session, port, writable=True)  — wrap session in web terminal
    stop_ttyd(port)
    pick_free_port(start=8700) -> int

Designed for the web_designer role on mooniex-claudesign but works for any
project whose config sets `spawn_backend: tmux`.
"""
from __future__ import annotations

import socket
import subprocess
from pathlib import Path

DEFAULT_TTYD_BIND = "127.0.0.1"
DEFAULT_TTYD_PORT_BASE = 8700


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def has_session(session: str) -> bool:
    r = subprocess.run(
        ["tmux", "has-session", "-t", session],
        capture_output=True, text=True, check=False,
    )
    return r.returncode == 0


def create(session: str, cwd: str | Path, cmd: str) -> None:
    """Start a detached tmux session that runs `cmd` in `cwd`.

    Idempotent: if session already exists, returns without error.
    """
    if has_session(session):
        return
    cwd = str(Path(cwd).expanduser())
    _run([
        "tmux", "new-session", "-d", "-s", session, "-c", cwd,
        # Wrap cmd in a login shell so user PATH (claude, pnpm, etc.) resolves.
        "/bin/zsh", "-l", "-c", cmd,
    ])


def send_keys(session: str, text: str, *, press_enter: bool = True) -> None:
    """Type `text` into the session. By default appends Enter (C-m).

    Uses tmux -l literal mode so user content containing `C-c` etc. is not
    interpreted as a keybinding. Enter is sent separately as a key.
    """
    if not has_session(session):
        raise RuntimeError(f"tmux session not found: {session}")
    _run(["tmux", "send-keys", "-t", session, "-l", text])
    if press_enter:
        _run(["tmux", "send-keys", "-t", session, "C-m"])


def kill(session: str) -> bool:
    """Kill tmux session. Returns True iff a session was killed."""
    if not has_session(session):
        return False
    subprocess.run(
        ["tmux", "kill-session", "-t", session],
        capture_output=True, text=True, check=False,
    )
    return True


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((DEFAULT_TTYD_BIND, port))
            return True
        except OSError:
            return False


def pick_free_port(start: int = DEFAULT_TTYD_PORT_BASE, span: int = 100) -> int:
    """Return the first free TCP port in [start, start+span) on loopback."""
    for p in range(start, start + span):
        if _port_free(p):
            return p
    raise RuntimeError(f"no free port in [{start},{start+span})")


def start_ttyd(session: str, port: int, *, writable: bool = True,
               bind: str = DEFAULT_TTYD_BIND) -> int:
    """Spawn ttyd in background, attaching to the tmux session.

    Returns the ttyd PID. Caller persists the PID for later kill.

    Safety: binds to loopback by default — never reachable on LAN.
    """
    if not has_session(session):
        raise RuntimeError(f"tmux session not found: {session}")
    args = ["ttyd", "-p", str(port), "-i", bind]
    if writable:
        args.append("--writable")
    args += ["tmux", "attach", "-t", session]
    p = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return p.pid


def stop_ttyd(pid: int) -> bool:
    """Best-effort SIGTERM to ttyd by PID. Returns True iff signal sent."""
    if not pid or pid <= 0:
        return False
    try:
        import os
        os.kill(pid, 15)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def url_for(port: int, bind: str = DEFAULT_TTYD_BIND) -> str:
    return f"http://{bind}:{port}"


def session_name_for(task_id: str, prefix: str = "wd") -> str:
    """Stable tmux session name for a task. Strips `task-` so `tmux ls`
    stays readable: `wd-161dbcf7` not `wd-task-161dbcf7`."""
    stripped = task_id.removeprefix("task-")
    return f"{prefix}-{stripped}"


if __name__ == "__main__":  # pragma: no cover — smoke entry
    import sys
    if len(sys.argv) < 2:
        print("usage: python -m tools.tmux_session "
              "[create SESSION CWD CMD | send SESSION TEXT | kill SESSION | "
              "ttyd SESSION PORT | port]", file=sys.stderr)
        raise SystemExit(2)
    op = sys.argv[1]
    if op == "create":
        create(sys.argv[2], sys.argv[3], sys.argv[4])
    elif op == "send":
        send_keys(sys.argv[2], sys.argv[3])
    elif op == "kill":
        print("killed" if kill(sys.argv[2]) else "no session")
    elif op == "ttyd":
        pid = start_ttyd(sys.argv[2], int(sys.argv[3]))
        print(f"ttyd pid={pid} url={url_for(int(sys.argv[3]))}")
    elif op == "port":
        print(pick_free_port())
    else:
        print(f"unknown op: {op}", file=sys.stderr)
        raise SystemExit(2)
