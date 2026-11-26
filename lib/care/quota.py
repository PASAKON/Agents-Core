"""Push quota gate (design §3.2). Pure decision + one injected HTTP read."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

CONSUMPTION_URL = "https://api.line.me/v2/bot/message/quota/consumption"

# http(method, url, headers, json_body) -> (status:int, body:dict)
Http = Callable[[str, str, dict, Optional[dict]], tuple]


@dataclass(frozen=True)
class QuotaConfig:
    monthly_limit: int = 300
    alert_at: int = 240
    critical_reserve: Optional[int] = None  # TBD -> treated as 0, reported as reserve_unset
    channel_id: str = "@587kfqpt"

    @classmethod
    def from_dict(cls, d: dict) -> "QuotaConfig":
        p = d.get("push", {})
        return cls(monthly_limit=p.get("monthly_limit", 300), alert_at=p.get("alert_at", 240),
                   critical_reserve=p.get("critical_reserve"),
                   channel_id=d.get("channel_basic_id", "@587kfqpt"))


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str
    used: Optional[int] = None
    alert: bool = False  # caller should fire the (deduped) 240 alert


def month_key(now: datetime) -> str:
    # TBD reset timezone: UTC placeholder (config quota_reset.timezone).
    n = now.astimezone(timezone.utc)
    return f"{n.year}_{n.month:02d}"


def read_consumption(http: Http, token: str) -> int:
    status, body = http("GET", CONSUMPTION_URL, {"Authorization": f"Bearer {token}"}, None)
    if status != 200:
        raise RuntimeError(f"consumption_http_{status}")
    return int(body["totalUsage"])


def decide_push(cfg: QuotaConfig, used: int, batch: int = 1, critical: bool = False,
                halted: bool = False) -> GateDecision:
    if halted:
        return GateDecision(False, "monthly_halt", used)
    projected = used + batch
    alert = projected >= cfg.alert_at
    if projected > cfg.monthly_limit:
        return GateDecision(False, "hard_stop", used, alert)
    if not critical:
        reserve = cfg.critical_reserve or 0
        if projected > cfg.monthly_limit - reserve:
            return GateDecision(False, "critical_reserve", used, alert)
    return GateDecision(True, "ok" if cfg.critical_reserve is not None else "ok_reserve_unset",
                        used, alert)
