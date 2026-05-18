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
    """
    task_id = os.environ.get("DEV_TASK_ID")
    if task_id:
        role = os.environ.get("DEV_ROLE", "dev")
        return f"Dev:{role}:{task_id[:10]}"
    if os.environ.get("CTO_SESSION") == "1":
        return f"CTO-event[{level.upper()}]"
    return None


def _append_cto_log(level: str, msg: str) -> None:
    source = _detect_source(level)
    if source is None:
        return
    try:
        _CTO_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with _CTO_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {source}: {msg}\n")
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
