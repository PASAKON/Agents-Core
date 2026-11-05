"""Is the Claude subscription spent right now?

One question for the code that decides whether a Project Head's letter can wake its
Haiku shell (which needs Claude) or must be answered by the AGY brain instead
(tools/claude_out_fallback.py, CEO 4 Nov 2026, Q-20261104-0251-39de).

The answer comes from the newest `"provider": "claude"` row of
`state/reports/quota-history.jsonl`, which the quota poll appends every few minutes
(tools/quota.py). Spent = its `daily_remaining` or `weekly_remaining` is at or under
the threshold. Three ways it is never spent:

  * the row is older than STALE_AFTER_S (2 h): a poll that stopped is no evidence;
  * there is no readable row, or the figures are missing or not numbers;
  * the kill switch file `state/claude_out_fallback.off` exists.

It never raises: any trouble reads as "not spent", so the caller falls back to the
wake it always did.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Same hub-root rule as lib/mailbox.py: ORG_ROOT (set on every worker) wins, so a
# process running from a worktree still reads the hub's state/.
ROOT = Path((os.environ.get("ORG_ROOT") or "").strip() or Path(__file__).resolve().parent.parent)
HISTORY = ROOT / "state" / "reports" / "quota-history.jsonl"
OFF_SWITCH = ROOT / "state" / "claude_out_fallback.off"

DEFAULT_THRESHOLD = 0.10
STALE_AFTER_S = 2 * 3600
# A claude row is written on every poll, so the newest one is within the last few KB;
# the history file itself grows without bound and is never read whole.
TAIL_BYTES = 256 * 1024


def _ts(value) -> float | None:
    """Epoch seconds of an ISO-8601 timestamp (a bare one counts as UTC), else None."""
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()


def _newest_claude_row(path: Path) -> dict | None:
    """The last `provider == "claude"` row in the file's tail, or None."""
    with open(path, "rb") as fh:
        size = fh.seek(0, os.SEEK_END)
        fh.seek(max(0, size - TAIL_BYTES))
        raw = fh.read()
    lines = raw.split(b"\n")
    if size > TAIL_BYTES:
        lines = lines[1:]               # the first line is cut mid-row
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("provider") == "claude":
            return row
    return None


def _fraction(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def claude_spent(threshold: float = DEFAULT_THRESHOLD, *, now: float | None = None) -> bool:
    """True when the newest fresh claude quota row shows a window at or under `threshold`."""
    try:
        if os.path.lexists(OFF_SWITCH):
            return False
        row = _newest_claude_row(HISTORY)
        if row is None:
            return False
        stamp = _ts(row.get("ts"))
        if stamp is None or (now if now is not None else datetime.now(timezone.utc).timestamp()) - stamp > STALE_AFTER_S:
            return False
        left = [f for f in (_fraction(row.get("daily_remaining")), _fraction(row.get("weekly_remaining")))
                if f is not None]
        return any(f <= threshold for f in left)
    except Exception:
        return False
