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
    task_id = os.environ.get("DEV_TASK_ID")
    if task_id:
        role = os.environ.get("DEV_ROLE", "dev")
        return f"Dev:{role}:{task_id[:10]}"
    if os.environ.get("CTO_SESSION") == "1":
        sid = os.environ.get("CTO_SESSION_ID")
        tag = f"[{sid}]" if sid else ""
        return f"CTO-event[{level.upper()}]{tag}"
    return None


def _per_session_log() -> Path | None:
    """Per-CTO log file (state/logs/cto-<id>.log) for the owning session.

    CTO processes use their own id; DEV processes use the spawning CTO's
    id (DEV_CTO_ID). This is the file `spawn-cto.sh --with-logs` tails."""
    sid = None
    if os.environ.get("CTO_SESSION") == "1":
        sid = os.environ.get("CTO_SESSION_ID")
    elif os.environ.get("DEV_TASK_ID"):
        sid = os.environ.get("DEV_CTO_ID")
    if not sid:
        return None
    return _ROOT / "state" / "logs" / f"cto-{sid}.log"


def _append_cto_log(level: str, msg: str) -> None:
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
