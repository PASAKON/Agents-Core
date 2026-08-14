"""Terminal + optional macOS notifications."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

COLORS = {
    "info": "\033[36m",
    "success": "\033[32m",
    "warn": "\033[33m",
    "error": "\033[31m",
    "ceo": "\033[35m",
    "cto": "\033[34m",
}
RESET = "\033[0m"

_ROOT = Path(__file__).resolve().parent.parent
_CTO_LOG = _ROOT / "state" / "logs" / "cto.log"


def _detect_source(level: str) -> str | None:
    """Pick the prefix that identifies who is logging.

    Returns the prefix string when the calling process is part of the org
    (CTO MCP server or DEV session). Returns None otherwise — caller skips
    the cto.log write so unrelated processes don't pollute the shared log.

    CTO-event lines carry the session id (`CTO-event[INFO][a1b2c3d4]`) so
    hook-log-prompt can drop other sessions' events in multi-CTO setups.
    """
    task_id = os.environ.get("WORKER_TASK_ID")
    if task_id:
        role = os.environ.get("WORKER_ROLE", "dev")
        return f"Dev:{role}:{task_id[:10]}"
    if os.environ.get("CTO_SESSION") == "1":
        sid = os.environ.get("CTO_SESSION_ID")
        tag = f"[{sid}]" if sid else ""
        return f"CTO-event[{level.upper()}]{tag}"
    return None


def _per_session_log() -> Path | None:
    """Per-CTO log file (state/logs/cto-<id>.log) for the owning session.

    CTO processes use their own id; DEV processes use the spawning CTO's
    id (WORKER_CTO_ID). This is the file `spawn-cto.sh --with-logs` tails."""
    sid = None
    if os.environ.get("CTO_SESSION") == "1":
        sid = os.environ.get("CTO_SESSION_ID")
    elif os.environ.get("WORKER_TASK_ID"):
        sid = os.environ.get("WORKER_CTO_ID")
    if not sid:
        return None
    return _ROOT / "state" / "logs" / f"cto-{sid}.log"


def _under_test() -> bool:
    """True when this process is a test run rather than real org work.

    The suites drive real production code — `test_watchdog_reap.py` calls
    `worker_reap`, which calls `warn()` — so without this guard their synthetic
    values land in the same `state/logs/cto.log` a C-level reads for live
    status. Observed 2026-08-13: lines like
    `worker_reap: task-7d6fe27d pid=99999 did not match` and
    `REAPED task-d0a9b673 ... pid=22222` surfaced in the CTO event feed
    mid-session, for tasks that do not exist.

    Keyed on the entry script's name rather than an env var so it covers
    every existing `scripts/test_*.py` and every future one with nothing to
    remember. `ORG_NOTIFY_SILENT=1` is the explicit override for a test
    driven some other way.
    """
    if os.environ.get("ORG_NOTIFY_SILENT") == "1":
        return True
    entry = os.path.basename(sys.argv[0] or "")
    return entry.startswith("test_") or entry == "pytest"


def _append_cto_log(level: str, msg: str) -> None:
    # stderr still prints, so a test's own output is unaffected. Only the
    # shared, human-watched log files are protected.
    if _under_test():
        return
    source = _detect_source(level)
    if source is None:
        return
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] {source}: {msg}\n"
    targets = [_CTO_LOG]
    per = _per_session_log()
    if per is not None:
        targets.append(per)
    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass


def notify(level: str, msg: str, *, mac: bool = False, title: str = "Org") -> None:
    color = COLORS.get(level, "")
    line = f"{color}● [{level.upper()}] {msg}{RESET}"
    print(line, file=sys.stderr)
    sys.stderr.flush()
    _append_cto_log(level, msg)
    if mac:
        try:
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "{msg}" with title "{title}"'],
                check=False, capture_output=True, timeout=2,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass


def info(msg, **kw): notify("info", msg, **kw)
def success(msg, **kw): notify("success", msg, mac=True, **kw)
def warn(msg, **kw): notify("warn", msg, **kw)
def error(msg, **kw): notify("error", msg, mac=True, **kw)
