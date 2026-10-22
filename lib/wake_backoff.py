"""Pure budget policy. No I/O; callers retain their immediate event path.

Input: P1's state/usage-budget/usage-budget.json, i.e. {"ts": ISO-8601 or Unix seconds,
"rows": {"agy": {"state": "under"}, "chatgpt": ..., "claude": ..., "agy-claude": ...}}.
Unknown rows are never over. x4 needs all three bar providers over; agy-claude is a side bucket.
"""
from datetime import datetime, timezone
import math

PROVIDERS = ("agy", "chatgpt", "claude")


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
