"""Auto-resume scheduler for rate-limited DEV tasks.

Long-running poller that wakes every POLL_INTERVAL_S, looks for tasks
that are stuck in `rate_limited` with `retry_after_ts` already in the
past, and re-opens each one via tools.resume_worker. Every action is
logged through lib.notify so it surfaces in the CTO chat via the
existing UserPromptSubmit hook.

Usage:
    python -m runners.auto_resume

Recommended: spawn in its own iTerm tab when the CTO starts, e.g. by
scripts/spawn-cto.sh. Safe to run multiple instances (resume is
idempotent — it sets status=in_progress before exec).
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.notify import info, warn
from tools.resume_worker import resume

POLL_INTERVAL_S = 60


def _due_tasks() -> list[dict]:
    """Return tasks ready for auto-resume right now."""
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, retry_after_ts FROM tasks "
            "WHERE status='rate_limited' "
            "AND retry_after_ts IS NOT NULL "
            "AND retry_after_ts <= ? "
            "ORDER BY retry_after_ts ASC",
            (now_iso,),
        ).fetchall()
    return [dict(r) for r in rows]


def tick() -> int:
    """One scheduler pass. Returns number of tasks resumed."""
    due = _due_tasks()
    resumed = 0
    for t in due:
        tid = t["id"]
        try:
            msg = resume(tid)
            info(f"auto-resume {tid}: {msg}")
            resumed += 1
        except Exception as e:
            warn(f"auto-resume failed for {tid}: {e}")
    return resumed


def main() -> None:
    db.init()
    info(f"auto_resume started (interval={POLL_INTERVAL_S}s)")
    try:
        while True:
            try:
                tick()
            except Exception as e:
                warn(f"auto_resume tick error: {e}")
            time.sleep(POLL_INTERVAL_S)
    except KeyboardInterrupt:
        info("auto_resume stopped (KeyboardInterrupt)")


if __name__ == "__main__":
    main()
