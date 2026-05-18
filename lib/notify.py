"""Terminal + optional macOS notifications."""
from __future__ import annotations

import subprocess
import sys

COLORS = {
    "info": "\033[36m",
    "success": "\033[32m",
    "warn": "\033[33m",
    "error": "\033[31m",
    "ceo": "\033[35m",
    "cto": "\033[34m",
}
RESET = "\033[0m"


def notify(level: str, msg: str, *, mac: bool = False, title: str = "Org") -> None:
    color = COLORS.get(level, "")
    line = f"{color}● [{level.upper()}] {msg}{RESET}"
    print(line, file=sys.stderr)
    sys.stderr.flush()
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
