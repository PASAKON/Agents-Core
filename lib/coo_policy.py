"""What a COO (SomPong) may hand to a worker -- one list, enforced in code.

CEO card Q-20261013-1948-4a33 (option 1, 2026-10-13 20:01Z): SomPong may create and
delegate its own research workers -- researcher, data_analyst, browser_operator --
and never a code role ("CTO ไว้ดูแลเรื่อง Coding ในองค์กรอย่างเดียว").

Enforced at three places, each of which refuses on its own:
  1. runners/coo_gate.py -- the only process that holds the COO's hub credential; its
     create_task and delegate_task ops call check_role() before touching the hub, and the
     root dispatcher (runners/coo_dispatch.py) checks again before it starts a worker.
  2. lib.db.create_task -- every Python path that inserts a task row (the org MCP
     registry, runners/cto.py, the COO gate) calls check_role() first.
  3. deploy/coo-gate/org_coo_role.sql -- the org_coo_guard trigger refuses any tasks row
     the Postgres role org_coo writes unless owner_role='coo' and role is in this list.
Keep this tuple and the SQL list identical (tests/test_coo_gate.py checks it).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import Iterable, Mapping
from zoneinfo import ZoneInfo

COO_ROLE = "coo"
COO_WORKER_ROLES = ("researcher", "data_analyst", "browser_operator")
# SomPong may start or resume a missing peer C-level on Contabo (CEO pick #18, 2026-10-26),
# never itself (mooniex-sompong.service supervises coo). Built from the full 5-role C-level
# roster minus COO_ROLE so runtime code never carries a partial roster literal.
COO_RESPAWN_ROLES = tuple(r for r in ("cto", "cmo", "cgo", "cfo", "coo") if r != COO_ROLE)
COO_RESPAWN_HOST = "contabo"
RESPAWN_WINDOW_S = 10 * 60
RESPAWN_MAX_PER_WINDOW = 1
RESPAWN_MAX_PER_THAI_DAY = 3
THAI_TZ = ZoneInfo("Asia/Bangkok")


class CooRoleRefused(PermissionError):
    """A COO-owned task asked for a role outside COO_WORKER_ROLES."""


class CooRespawnRefused(CooRoleRefused):
    """A COO respawn request named a role outside COO_RESPAWN_ROLES or a non-Contabo host."""


def check_role(owner_role: str | None, role: str) -> None:
    """Raise CooRoleRefused when a coo-owned task names any other role.

    Other owners pass untouched: this guard narrows the COO, nobody else."""
    if (owner_role or "").strip().lower() != COO_ROLE:
        return
    if role not in COO_WORKER_ROLES:
        raise CooRoleRefused(
            f"role {role!r} refused for a coo task: SomPong may delegate only "
            f"{', '.join(COO_WORKER_ROLES)} (CEO card Q-20261013-1948-4a33). "
            f"Code work goes to a CTO: SendMessage it the brief.")


def check_respawn(role: str, host: str = COO_RESPAWN_HOST) -> None:
    """Raise CooRespawnRefused unless role is in COO_RESPAWN_ROLES and host is contabo."""
    if role not in COO_RESPAWN_ROLES:
        raise CooRespawnRefused(
            f"role {role!r} refused for respawn_clevel: SomPong may respawn only "
            f"{', '.join(COO_RESPAWN_ROLES)}")
    if host != COO_RESPAWN_HOST:
        raise CooRespawnRefused(
            f"host {host!r} refused for respawn_clevel: other hosts wait for Run Inbox P2")


def _parse_ts(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def respawn_rate_limit_reason(
    events: Iterable[Mapping[str, object]],
    role: str,
    *,
    now: float | datetime | str | None = None,
    exclude_id: int | None = None,
) -> str | None:
    """Return a refusal reason if `role` exceeds <=1 per 10 min or <=3 per Thai day."""
    now_dt = _parse_ts(now) if now is not None else datetime.now(timezone.utc)
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)
    now_thai_date = now_dt.astimezone(THAI_TZ).date()
    in_window = 0
    in_thai_day = 0
    for ev in events:
        if exclude_id is not None and ev.get("id") == exclude_id:
            continue
        raw_payload = ev.get("payload")
        if isinstance(raw_payload, str):
            try:
                payload = json.loads(raw_payload)
            except ValueError:
                continue
        elif isinstance(raw_payload, Mapping):
            payload = raw_payload
        else:
            continue
        if not isinstance(payload, Mapping) or payload.get("role") != role:
            continue
        ev_dt = _parse_ts(ev.get("ts"))
        if ev_dt is None:
            continue
        age_s = (now_dt - ev_dt).total_seconds()
        if -60 <= age_s < RESPAWN_WINDOW_S:
            in_window += 1
        if ev_dt.astimezone(THAI_TZ).date() == now_thai_date and ev_dt <= now_dt + timedelta(seconds=60):
            in_thai_day += 1
    if in_window >= RESPAWN_MAX_PER_WINDOW:
        return (f"rate limit: role {role!r} already has {in_window} respawn request(s) in the last "
                f"10 minutes (max {RESPAWN_MAX_PER_WINDOW} per 10 min)")
    if in_thai_day >= RESPAWN_MAX_PER_THAI_DAY:
        return (f"rate limit: role {role!r} already has {in_thai_day} respawn requests today in "
                f"Asia/Bangkok (max {RESPAWN_MAX_PER_THAI_DAY} per Thai day)")
    return None
