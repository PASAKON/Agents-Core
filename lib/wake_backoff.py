"""Pure budget policy. No I/O but `load_budget`; callers retain their immediate event path.

Input: P1's state/usage-budget/usage-budget.json, i.e. {"ts": ISO-8601 or Unix seconds,
"rows": {"agy": {"state": "under"}, "chatgpt": ..., "claude": ..., "agy-claude": ...}}.
Unknown rows are never over. x4 needs all three bar providers over; agy-claude is a side bucket.

A timed check multiplies its base interval by the budget factor and by its tier's factor
(`wake_interval`); a real event never passes through here (IRON-RULES section 64).
"""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import stat

PROVIDERS = ("agy", "chatgpt", "claude")
# Same file tools/usage_budget.SNAPSHOT writes (a test pins the two together).
BUDGET_PATH = Path(__file__).resolve().parents[1] / "state/usage-budget/usage-budget.json"
BUDGET_READ_MAX = 64 * 1024


def _seconds(value):
    if isinstance(value, bool):
        raise ValueError("boolean timestamp")
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.timestamp()
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("non-finite timestamp")
    return value


def backoff_factor(budget_json: dict | None, now) -> int:
    """Return 1/2/4. Invalid, missing, future or >30-minute data fails open."""
    if not isinstance(budget_json, dict):
        return 1
    try:
        age = _seconds(now) - _seconds(budget_json.get("ts"))
    except (TypeError, ValueError, OverflowError):
        return 1
    if not 0 <= age <= 1800:
        return 1
    rows = budget_json.get("rows")
    if not isinstance(rows, dict):
        return 1
    over = sum(isinstance(rows.get(p), dict) and rows[p].get("state") == "over"
               for p in PROVIDERS)
    return 4 if over == len(PROVIDERS) else 2 if over else 1


def tier_factor(tier, over: bool) -> int | None:
    """Tier multiplier for a timed check. critical 1; normal 1, or 2 while any provider is
    over; low None (no timed wake at all). Any other tier is read as normal."""
    if tier == "low":
        return None
    if tier == "critical":
        return 1
    return 2 if over else 1


def wake_interval(base_s: float, *, tier, budget_json: dict | None, now) -> float | None:
    """base_s x backoff_factor x tier_factor; None = no timed wake for this tier.

    `over` is backoff_factor > 1, so missing, stale or invalid budget data leaves every
    tier but low at its base interval (fail open)."""
    factor = backoff_factor(budget_json, now)
    tiered = tier_factor(tier, factor > 1)
    return None if tiered is None else float(base_s) * factor * tiered


def load_budget(path=None) -> dict | None:
    """P1's budget json, or None when it is missing, not a regular file, too large or not a
    json object. Never raises: no data means no slowdown. state/ has no sticky bit, so a
    link is not followed and a FIFO cannot hang the caller."""
    fd = None
    try:
        fd = os.open(path if path is not None else BUDGET_PATH,
                     os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > BUDGET_READ_MAX:
            return None
        data = json.loads(os.read(fd, BUDGET_READ_MAX + 1))
    except (OSError, ValueError, RecursionError):
        return None
    finally:
        if fd is not None:
            os.close(fd)
    return data if isinstance(data, dict) else None
