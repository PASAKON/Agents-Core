"""Quota usage forecasting and size estimation tool.

Calculates estimated task quota costs based on seeds or learned tables,
determines dispatch verdicts against bucket reserve thresholds,
computes 24h burn rates across resets, and generates exhaustion projections.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import quota

SEED_COSTS: dict[str, dict[str, float | int]] = {
    "claude": {"S": 3, "M": 8, "L": 20, "plan_usd": 20},
    "codex": {"S": 1, "M": 3, "L": 8, "plan_usd": 20},
    "agy-gemini": {"S": 0.3, "M": 1, "L": 3, "plan_usd": 100},
    "agy-claude": {"S": 1, "M": 3, "L": 8, "plan_usd": 100},
}

COST_TABLE_PATH = ROOT / "state" / "cost-table.json"


def infer_size(touches: list | tuple | None = None, brief: str | None = None) -> str:
    """Infer task size S, M, or L based on touch count and brief length.

    S: len(touches) <= 2 and len(brief) < 1500
    L: len(touches) > 6 or len(brief) > 6000
    Else: M
    None counts as empty.
    """
    t_len = len(touches) if touches is not None else 0
    b_len = len(brief) if brief is not None else 0
    if t_len <= 2 and b_len < 1500:
        return "S"
    if t_len > 6 or b_len > 6000:
        return "L"
    return "M"


def cost_for(
    bucket: str,
    size: str,
    *,
    limits: dict[str, dict],
    table: dict | None = None,
) -> tuple[float | None, str]:
    """Calculate expected quota cost fraction and source for bucket and size.

    Scaled by: (pct / 100) * (ref plan_usd / limits[bucket]["plan_usd"]).
    Returns (fraction, source) e.g. (0.008, "seed") or (0.012, "learned n=7").
    Unknown bucket -> (None, "no cost data").
    """
    if not isinstance(limits, dict) or bucket not in limits:
        return None, "no cost data"

    limit_row = limits[bucket]
    limit_plan_usd = limit_row.get("plan_usd")
    if not limit_plan_usd or limit_plan_usd <= 0:
        return None, "no cost data"

    learned_cell = None
    if table is None:
        if COST_TABLE_PATH.is_file():
            try:
                raw = json.loads(COST_TABLE_PATH.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    learned_cell = raw.get(bucket, {}).get(size)
            except Exception:
                learned_cell = None
    else:
        learned_cell = table.get(bucket, {}).get(size)

    if (
        isinstance(learned_cell, dict)
        and learned_cell.get("n", 0) >= 5
        and "pct" in learned_cell
        and "plan_usd" in learned_cell
        and learned_cell["plan_usd"] > 0
    ):
        pct = float(learned_cell["pct"])
        ref_plan_usd = float(learned_cell["plan_usd"])
        source = f"learned n={learned_cell['n']}"
    elif bucket in SEED_COSTS and size in SEED_COSTS[bucket]:
        seed = SEED_COSTS[bucket]
        pct = float(seed[size])
        ref_plan_usd = float(seed["plan_usd"])
        source = "seed"
    else:
        return None, "no cost data"

    fraction = (pct / 100.0) * (ref_plan_usd / limit_plan_usd)
    return fraction, source


def fmt_pct(val: float | int | None) -> str:
    """Format percentage with no decimals when whole, else one decimal."""
    if val is None:
        return "None"
    r = round(float(val), 1)
    if r.is_integer():
        return f"{int(r)}%"
    return f"{r:.1f}%"


def verdict(
    q: quota.Quota | None,
    cost: float | None,
    limit_row: dict | None,
) -> tuple[str, float | None, str]:
    """Determine dispatch verdict for quota and cost against bucket limits.

    Returns: (verdict, after, why)
    verdict in {"ok", "will_hit", "unknown"}
    """
    if q is None:
        return "unknown", None, "no quota data"
    if q.error:
        return "unknown", None, q.error
    if q.weekly_remaining is None:
        return "unknown", None, "weekly quota unknown"
    if cost is None:
        return "unknown", None, "no cost data"

    after = q.weekly_remaining - cost
    row = limit_row or {}
    min_5h_pct = row.get("min_5h_pct", 0)
    reserve_pct = row.get("reserve_pct", 0)

    if q.daily_remaining is not None and round(q.daily_remaining * 100, 4) < min_5h_pct:
        return "will_hit", after, f"5h {fmt_pct(q.daily_remaining * 100)} < min {fmt_pct(min_5h_pct)}"

    if round(after * 100, 4) < reserve_pct:
        return "will_hit", after, f"after {fmt_pct(after * 100)} < reserve {fmt_pct(reserve_pct)}"

    return "ok", after, f"reserve {fmt_pct(reserve_pct)} ok"


def burn_rate(
    bucket: str,
    history_path: Path | str | None = None,
    now: datetime | None = None,
    window_h: int | float = 24,
) -> float | None:
    """Calculate quota burn rate as weekly fraction per day.

    Reads quota history, filters points in last window_h for bucket with valid weekly_remaining,
    slices after the last rise > 0.02 (reset). Requires >= 2 points spanning >= 1 h.
    """
    p = Path(history_path) if history_path is not None else quota.DEFAULT_HISTORY
    if not p.is_file():
        return None

    if now is None:
        now_dt = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now_dt = now.replace(tzinfo=timezone.utc)
    else:
        now_dt = now.astimezone(timezone.utc)

    window_start = now_dt - timedelta(hours=window_h)
    points: list[tuple[datetime, float]] = []

    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                if obj.get("provider") != bucket:
                    continue
                if obj.get("error") is not None:
                    continue
                w = obj.get("weekly_remaining")
                if w is None:
                    continue
                ts_str = obj.get("ts")
                if not ts_str or not isinstance(ts_str, str):
                    continue
                try:
                    ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts_dt.tzinfo is None:
                        ts_dt = ts_dt.replace(tzinfo=timezone.utc)
                    else:
                        ts_dt = ts_dt.astimezone(timezone.utc)
                except Exception:
                    continue

                if window_start <= ts_dt <= now_dt:
                    points.append((ts_dt, float(w)))
    except Exception:
        return None

    if not points:
        return None

    points.sort(key=lambda pt: pt[0])

    # Keep only the points after the last rise > 0.02 (a reset)
    last_reset_idx = 0
    for i in range(1, len(points)):
        if points[i][1] - points[i - 1][1] > 0.02:
            last_reset_idx = i

    points = points[last_reset_idx:]

    if len(points) < 2:
        return None

    span_s = (points[-1][0] - points[0][0]).total_seconds()
    hours = span_s / 3600.0
    if hours < 1.0:
        return None

    rate = (points[0][1] - points[-1][1]) / hours * 24.0
    return max(0.0, rate)


def projection(
    bucket: str,
    q: quota.Quota | None,
    rate: float | None,
    reserve_pct: float | int,
    now: datetime | None = None,
) -> str | None:
    """Project when bucket quota reaches reserve or holds past reset.

    None if rate is None or <= 0, or quota is unavailable.
    """
    if rate is None or rate <= 0:
        return None
    if q is None or q.weekly_remaining is None:
        return None

    if now is None:
        now_dt = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now_dt = now.replace(tzinfo=timezone.utc)
    else:
        now_dt = now.astimezone(timezone.utc)

    weekly = q.weekly_remaining
    reserve = reserve_pct / 100.0
    days = (weekly - reserve) / rate

    reach_dt = now_dt + timedelta(days=max(0.0, days))
    reach_str = reach_dt.strftime("%Y-%m-%d")

    reset_str = q.weekly_resets_at
    reset_dt = None
    if reset_str:
        try:
            reset_dt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
            if reset_dt.tzinfo is None:
                reset_dt = reset_dt.replace(tzinfo=timezone.utc)
            else:
                reset_dt = reset_dt.astimezone(timezone.utc)
        except Exception:
            reset_dt = None

    if reset_dt is not None:
        reset_md = reset_dt.strftime("%m-%d")
        if reach_dt < reset_dt and days > 0:
            return f"reaches reserve {reach_str}, before reset {reset_md}"
        elif reach_dt < reset_dt and days <= 0:
            return f"reaches reserve {reach_str}, before reset {reset_md}"
        else:
            return f"holds past reset {reset_md}"
    else:
        return f"reaches reserve {reach_str}"
