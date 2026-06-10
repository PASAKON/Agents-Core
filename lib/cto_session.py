"""CTO session identity. Each running CTO chat owns a short ID so DEV
reports route back to the spawning CTO instead of broadcasting to every
open CTO tab.

The ID is exported as CTO_SESSION_ID in the CTO process env. DEV
processes inherit DEV_CTO_ID at spawn time (via tools/delegate.py).
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "state" / "logs"
SHARED_LOG = LOGS_DIR / "cto.log"  # legacy fallback when no ID is set


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def current_id() -> str | None:
    """Return the CTO id this process is associated with.

    Resolution order:
      1. CTO_SESSION_ID  — set by cto_chat at startup
      2. DEV_CTO_ID      — set by delegate_task on DEV spawn
    """
    sid = os.environ.get("CTO_SESSION_ID") or os.environ.get("DEV_CTO_ID")
    return sid or None


def ensure_cto_id() -> str:
    sid = os.environ.get("CTO_SESSION_ID")
    if not sid:
        sid = new_id()
        os.environ["CTO_SESSION_ID"] = sid
    return sid


def tab_title(sid: str) -> str:
    # Base prefix only — scripts/tab-title.sh appends a live status glyph +
    # summary after it (IRON-RULES §32). Routing tools match this prefix.
    return f"CTO #{sid}"


def log_path(sid: str | None) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not sid:
        return SHARED_LOG
    return LOGS_DIR / f"cto-{sid}.log"


def current_log_path() -> Path:
    return log_path(current_id())
