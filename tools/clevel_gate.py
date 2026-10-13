"""One live session per C-level role, on Contabo only (org restructure P2, plan §3.1).

Off unless `ORG_SINGLE_CLEVEL=1` on the host: `refusal()` then returns None
without reading anything, so a host that has not opted in launches exactly as
before. On:

- A C-level (cto, cmo, cgo, cfo, coo) starts only on Contabo. The one exception
  is the plan's emergency: Contabo down for more than 30 minutes and the CEO
  typed the order himself, which the launching shell states with
  `ORG_CLEVEL_EMERGENCY=1`. A host that cannot be resolved counts as "not
  Contabo" (fails closed).
- A second live session of the same role on this host is refused. Live = a lock
  `state/locks/<role>-<id>.lock` whose pid is alive and, where /proc exists, is
  still a C-level launcher (a recycled pid is not a session). A resume of the
  same id is not "another" session: the launcher's own per-id lock handles it.

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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCKS_DIR = ROOT / "state" / "locks"
HOME_HOST = "contabo"
LAUNCHERS = ("cxo-claude", "cto-claude")


def single_on() -> bool:
    return os.environ.get("ORG_SINGLE_CLEVEL", "").strip() == "1"


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


def _pid_is_launcher(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass  # alive, owned by another user
    cmdline = Path(f"/proc/{pid}/cmdline")
    if not cmdline.parent.exists():
        return True  # no /proc (the Mac): an alive pid counts
    try:
        argv = cmdline.read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
    except OSError:
        return False
    return any(name in argv for name in LAUNCHERS)


def live_sessions(role: str, locks_dir: Path = LOCKS_DIR,
                  exclude: str | None = None) -> list[tuple[str, int]]:
    """(session id, launcher pid) of every live `role` session on this host."""
    found = []
    prefix = f"{role}-"
    for lock in sorted(Path(locks_dir).glob(f"{role}-*.lock")):
        sid = lock.name[len(prefix):-len(".lock")]
        if not sid or sid == exclude:
            continue
        try:
            pid = int(lock.read_text(encoding="ascii", errors="replace").strip())
        except (OSError, ValueError):
            continue
        if pid > 1 and _pid_is_launcher(pid):
            found.append((sid, pid))
    return found


def refusal(role: str, session_id: str | None = None, host: str | None = None,
            locks_dir: Path = LOCKS_DIR) -> str | None:
    """None when `role` may start a session here (or the gate is off), else why not."""
    if not single_on():
        return None
    role = (role or "").strip().lower()
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
