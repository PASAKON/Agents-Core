"""One live session per C-level role, on Contabo only (org restructure P2, plan §3.1).

CTO's Contabo-only guard is unconditional. The remaining policy is off unless
the host flag ORG_SINGLE_CLEVEL is on (`/etc/org-flags/ORG_SINGLE_CLEVEL`,
or `ORG_SINGLE_CLEVEL=1` in the env; lib/org_flags.py): `refusal()` then returns
None without reading anything else, so a host that has not opted in launches
exactly as before. On:

- A C-level (cto, cmo, cgo, cfo, coo) starts only on Contabo. The one exception
  is the plan's emergency: Contabo down for more than 30 minutes and the CEO
  typed the order himself, which the launching shell states with
  `ORG_CLEVEL_EMERGENCY=1`. A host that cannot be resolved counts as "not
  Contabo" (fails closed).
- A second live session of the same role on this host is refused. Live = a lock
  `state/locks/<role>-<id>.lock` whose pid is alive and (from /proc, or `ps` on the Mac) is
  still that role's launcher: argv[0] or argv[1] is cxo-claude.sh started with
  `--role <role>`, or cto-claude.sh for the CTO (a recycled pid, or a process
  that only mentions the launcher in its arguments, is not a session). A resume
  of the same id is not "another" session: the launcher's own per-id lock
  handles it. A resume under a new id is: spawn paths pass no session id.

Project Heads and workers are not C-levels and never reach this gate.

The launchers (`scripts/cxo-claude.sh`, `scripts/cto-claude.sh`) run the CLI
under a flock on `state/locks/.single-<role>.flock` and write their own lock
before releasing it, so two launchers started in the same second cannot both
pass. The spawn paths (relay `spawn_c_level`, `node_dispatch` start_clevel,
`send_to_cxo --spawn`) call `refusal()` first only to answer early with the
reason; the launcher is the check that holds.

CLI:
    python -m tools.clevel_gate check --role cto [--session <id>] [--host contabo]
    # exit 0 = may start, 1 = refused (reason on stderr)
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import org_flags  # noqa: E402

LOCKS_DIR = ROOT / "state" / "locks"
HOME_HOST = "contabo"
LAUNCHERS = ("cxo-claude", "cto-claude")
PROC = Path("/proc")


def single_on() -> bool:
    return org_flags.on("ORG_SINGLE_CLEVEL")


def emergency() -> bool:
    return os.environ.get("ORG_CLEVEL_EMERGENCY", "").strip() == "1"


def _is_c_level(role: str) -> bool:
    from lib.roles import c_level_roles
    return role in c_level_roles()


def _self_host() -> str | None:
    try:
        from lib.config import self_host
        return self_host()
    except Exception:  # noqa: BLE001 — unresolved host fails closed below
        return None


def _launcher_role(argv: list[str]) -> str | None:
    """The role a launcher argv runs, or None when argv is not a launcher.
    Only argv[0] and argv[1] may name the script (`bash …/cxo-claude.sh` or the
    script itself); a launcher name further down is some other process's text."""
    for i, arg in enumerate(argv[:2]):
        base = os.path.basename(arg)
        if base.endswith(".sh"):
            base = base[:-3]
        if base == "cto-claude":
            return "cto"
        if base == "cxo-claude":
            rest = argv[i + 1:]
            for j, a in enumerate(rest[:-1]):
                if a == "--role":
                    return rest[j + 1].strip().lower()
            return None
    return None


def _ps_argv(pid: int) -> list[str] | None:
    """argv of `pid` from `ps` where there is no /proc (the Mac, M13a), or None
    when ps cannot say: ps missing, ps exiting non-zero, no output, or only the
    `(name)` macOS prints when this user may not read another user's argv. The
    caller has already seen the pid alive, so None means "count it live" (fail
    closed, as before M13a). ps joins argv with spaces, so an argument holding a
    space splits; the launcher paths hold none. Without this a pid the OS reused
    after a Project Head ended kept its project held."""
    try:
        out = subprocess.run(["ps", "-ww", "-o", "command=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    argv = out.stdout.split()
    if out.returncode != 0 or not argv or re.fullmatch(r"\(.*\)", " ".join(argv)):
        return None
    return argv


def _pid_is_launcher(pid: int, role: str | None = None) -> bool:
    """`pid` is alive and is a launcher (of `role`, when given), read from /proc or ps."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass  # alive, owned by another user
    if PROC.is_dir():
        try:
            raw = (PROC / str(pid) / "cmdline").read_bytes()
        except OSError:
            return False  # gone between the kill and the read
        argv = [a.decode("utf-8", "replace") for a in raw.split(b"\0") if a]
    else:
        argv = _ps_argv(pid)
        if argv is None:
            return True  # ps cannot read it (or no ps: Windows): an alive pid counts
    found = _launcher_role(argv)
    if found is None:
        return False
    return role is None or found == role


def live_lock(role: str, session_id: str, locks_dir: Path | None = None) -> int | None:
    """Launcher pid of the live `role` session `session_id` on this host, else None.
    The one liveness test for C-level and Project Head locks (send_to_cxo and
    spawn_ph use it too): the lock file alone outlives a killed session."""
    lock = Path(locks_dir or LOCKS_DIR) / f"{role}-{session_id}.lock"
    try:
        pid = int(lock.read_text(encoding="ascii", errors="replace").strip())
    except (OSError, ValueError):
        return None
    return pid if pid > 1 and _pid_is_launcher(pid, role) else None


def live_sessions(role: str, locks_dir: Path | None = None,
                  exclude: str | None = None) -> list[tuple[str, int]]:
    """(session id, launcher pid) of every live `role` session on this host."""
    found = []
    prefix = f"{role}-"
    locks_dir = Path(locks_dir or LOCKS_DIR)
    for lock in sorted(locks_dir.glob(f"{role}-*.lock")):
        sid = lock.name[len(prefix):-len(".lock")]
        if not sid or sid == exclude:
            continue
        pid = live_lock(role, sid, locks_dir)
        if pid:
            found.append((sid, pid))
    return found


def refusal(role: str, session_id: str | None = None, host: str | None = None,
            locks_dir: Path | None = None) -> str | None:
    """None when `role` may start a session here (or the gate is off), else why not."""
    role = (role or "").strip().lower()
    host = (host or _self_host() or "").strip().lower()
    if role == "cto" and host != HOME_HOST:
        return "CTO runs on Contabo only. Open it on Contabo."
    if not single_on():
        return None
    if not _is_c_level(role):
        return None
    host = host or _self_host()
    if host != HOME_HOST and not emergency():
        return (f"{role.upper()} runs on Contabo only (plan §3.1); this host is "
                f"{host or 'unresolved'}. Open it on Contabo. Emergency only (Contabo down "
                f"> 30 min and the CEO typed the order): ORG_CLEVEL_EMERGENCY=1.")
    live = live_sessions(role, locks_dir, exclude=session_id)
    if live:
        sid, pid = live[0]
        return (f"{role.upper()} is already live on this host as #{sid} (launcher pid "
                f"{pid}); one session per C-level (plan §3.1). Write to it instead: "
                f"bash scripts/live-sessions.sh, then SendMessage.")
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.clevel_gate")
    ap.add_argument("verb", choices=("check",))
    ap.add_argument("--role", required=True)
    ap.add_argument("--session", default=None)
    ap.add_argument("--host", default=None)
    ap.add_argument("--locks-dir", default=str(LOCKS_DIR))
    args = ap.parse_args(argv)
    why = refusal(args.role, args.session, args.host, Path(args.locks_dir))
    if why:
        print(why, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
