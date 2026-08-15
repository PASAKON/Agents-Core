"""tmux session helper for agent ptys with optional ttyd web bridge.

A tmux session is the single pty source-of-truth. Any number of clients
(iTerm tab via `tmux attach`, browser via `ttyd tmux attach`) can attach
simultaneously and see/type the exact same stream — true two-way realtime
sync, not a log mirror.

API:
    tmux_bin() -> str                         — resolve the tmux binary path
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

import os
import shutil
import socket
import subprocess
from pathlib import Path

DEFAULT_TTYD_BIND = "127.0.0.1"
DEFAULT_TTYD_PORT_BASE = 8700

_TMUX_BIN: str | None = None


def _reset_tmux_bin_cache() -> None:
    """Test-only: clear the cached resolution so the next tmux_bin() call
    re-resolves. Production code never calls this -- the answer cannot
    change inside one process."""
    global _TMUX_BIN
    _TMUX_BIN = None


def tmux_bin() -> str:
    """Absolute path to the tmux binary, resolved once per process.

    launchd hands a process a bare PATH (/usr/bin:/bin:/usr/sbin:/sbin) -- it
    does NOT inherit the login shell's. Homebrew installs tmux in
    /opt/homebrew/bin, so a plain "tmux" argv[0] resolves to nothing under
    launchd and every tmux call fails. The dangerous part is what that
    failure looked like in practice: sessions that plainly existed were
    reported as "no live session" -- a confident, wrong, plausible-looking
    answer, not a clean "command not found".

    Resolution order:
      1. TMUX_BIN env override -- operator escape hatch, also what tests use.
      2. shutil.which("tmux") -- correct whenever PATH is sane, and picks up
         non-standard installs the hardcoded candidates below would miss.
      3. /opt/homebrew/bin/tmux, /usr/local/bin/tmux, /usr/bin/tmux, by
         existence -- covers the launchd case, where `which` finds nothing
         because PATH was stripped, but the binary is still on disk.
      4. bare "tmux" as the last resort. This keeps today's behaviour on any
         box not accounted for above, and lets a truly missing tmux surface
         as a real OSError from the caller's subprocess call instead of
         silently pretending nothing is running.

    Cached in a module global -- this runs on every tmux operation and the
    answer cannot change mid-process -- but the cache is resettable via
    `_reset_tmux_bin_cache()` so tests can exercise more than one resolution
    path in a single run.
    """
    global _TMUX_BIN
    if _TMUX_BIN is not None:
        return _TMUX_BIN
    override = os.environ.get("TMUX_BIN")
    if override:
        _TMUX_BIN = override
        return _TMUX_BIN
    found = shutil.which("tmux")
    if found:
        _TMUX_BIN = found
        return _TMUX_BIN
    for candidate in ("/opt/homebrew/bin/tmux", "/usr/local/bin/tmux", "/usr/bin/tmux"):
        if Path(candidate).exists():
            _TMUX_BIN = candidate
            return _TMUX_BIN
    _TMUX_BIN = "tmux"  # last resort; surfaces as a real error, not a silent miss
    return _TMUX_BIN


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def has_session(session: str) -> bool:
    r = subprocess.run(
        [tmux_bin(), "has-session", "-t", session],
        capture_output=True, text=True, check=False,
    )
    return r.returncode == 0


def login_shell() -> str:
    """Absolute path to a login shell that exists on THIS machine.

    `/bin/zsh` used to be hardcoded here. That is right on the Mac and absent
    on Contabo (Debian), and the failure was silent in the worst possible way:
    `tmux new-session -d ... /bin/zsh -l -c '...'` exits **0** even when the
    shell does not exist. tmux creates the session, the command dies
    instantly, the session dies with it, the server shuts down -- and
    `create()` returns cleanly, so `spawn_c_level` told the CEO "spawned" for
    a session that never existed.

    $SHELL first (honours whatever the invoking user actually runs), then the
    old candidate order, so the Mac resolves to zsh exactly as before.
    """
    for candidate in (os.environ.get("SHELL"), "/bin/zsh", "/bin/bash", "/bin/sh"):
        if candidate and Path(candidate).exists():
            return candidate
    return "/bin/sh"  # POSIX guarantees this one


def create(session: str, cwd: str | Path, cmd: str) -> None:
    """Start a detached tmux session that runs `cmd` in `cwd`.

    Idempotent: if session already exists, returns without error.

    Raises RuntimeError when the session is not alive afterwards. tmux reports
    success for a command it could not run (see `login_shell`), so its exit
    code proves nothing -- only the session existing does.
    """
    if has_session(session):
        return
    cwd = str(Path(cwd).expanduser())
    shell = login_shell()
    _run([
        tmux_bin(), "new-session", "-d", "-s", session, "-c", cwd,
        # Wrap cmd in a login shell so user PATH (claude, pnpm, etc.) resolves.
        shell, "-l", "-c", cmd,
    ])
    if not has_session(session):
        raise RuntimeError(
            f"tmux session {session!r} was not alive after new-session — its "
            f"command exited immediately (shell={shell}, cwd={cwd})"
        )


def send_keys(session: str, text: str, *, press_enter: bool = True) -> None:
    """Type `text` into the session. By default appends Enter (C-m).

    Uses tmux -l literal mode so user content containing `C-c` etc. is not
    interpreted as a keybinding. Enter is sent separately as a key.
    """
    if not has_session(session):
        raise RuntimeError(f"tmux session not found: {session}")
    _run([tmux_bin(), "send-keys", "-t", session, "-l", text])
    if press_enter:
        _run([tmux_bin(), "send-keys", "-t", session, "C-m"])


def capture(session: str, lines: int = 200) -> str:
    """Best-effort text of a session's pane, including scrollback.

    Exists so a spawn that dies can still say why. A tmux session whose only
    command exits is torn down immediately, taking the error message with it
    -- which is exactly how a 100%-reproducible spawn failure once looked
    like total silence for an hour (2026-08-15). Callers use this on the
    failure path to put the real stderr into `tasks.delegate_log` instead of
    guessing.

    Returns "" when the session is already gone or tmux errors; the caller is
    reporting a failure either way and must not fail again on the report.
    """
    r = subprocess.run(
        [tmux_bin(), "capture-pane", "-t", session, "-p", "-S", f"-{lines}"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        return ""
    return "\n".join(ln for ln in (r.stdout or "").splitlines() if ln.strip())


def kill(session: str) -> bool:
    """Kill tmux session. Returns True iff a session was killed."""
    if not has_session(session):
        return False
    subprocess.run(
        [tmux_bin(), "kill-session", "-t", session],
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
    args += [tmux_bin(), "attach", "-t", session]
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
