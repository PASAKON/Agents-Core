"""Publish quota resets from the existing snapshot timer; no model calls."""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from datetime import timedelta
import fcntl
import inspect
import json
import logging
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db
from tools import email_ceo
from tools.quota import DEFAULT_HISTORY, _as_utc, _parse_bonus_time

RESETS = ROOT / "state/reports/quota-resets.jsonl"
BUCKETS = {"claude", "codex", "agy-gemini", "agy-claude"}
MAIL_BUCKETS = {"codex": "Codex", "agy-gemini": "AGY Argon/Gemini", "agy-claude": "AGY Claude"}
LOGGER = logging.getLogger(__name__)


def mail_fields(event):
    """Reuse the CEO mail format and a stable bucket + reset deadline reference."""
    try:
        deadline = _parse_bonus_time(event["resets_at"])
        when = deadline.astimezone(ZoneInfo("Asia/Bangkok")).strftime("%d/%m/%Y %H:%M น.") if deadline else "ไม่ทราบ"
    except (ValueError, TypeError, OverflowError):
        when = "ไม่ทราบ"
    def pct(value):
        return f"{value:g}%" if value is not None else "ไม่ทราบ"
    reason = {"utilization_drop": "รีเซ็ตด้วยตนเอง / ได้โควต้าใหม่",
              "reset_extended": "โบนัส", "plan_changed": "เปลี่ยนแผน"}[event["reason"]]
    return {"title": f"🎉 {MAIL_BUCKETS[event['bucket']]} รีเซ็ตแล้ว — โควต้าก้อนใหม่",
            "why": f"ใช้ไป: {pct(event['from_pct'])} -> {pct(event['to_pct'])}\n"
                   f"เหตุผล: {reason}\nรีเซ็ตถัดไป: {when} (เวลาไทย)",
            "ref": f"{event['bucket']}:{event['resets_at']}"}


def mail_reset(event):
    if event["bucket"] not in MAIL_BUCKETS:
        return
    try:
        email_ceo.send(mail_fields(event), kind="quota_reset", session="cto-quota-reset", role="cto")
    except Exception as exc:
        # Delivery must never prevent snapshot advancement; don't log response secrets.
        LOGGER.warning("quota reset mail failed for %s (%s)", event["bucket"], type(exc).__name__)


def rows(path):
    if not Path(path).exists():
        return
    with Path(path).open() as stream:
        for line in stream:
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    yield row
            except ValueError:
                continue


def reset_event(bucket, old, new, now):
    if old.get("error") or new.get("error"):
        return None
    for slot in ("weekly", "daily"):
        def pct(row):
            remaining = row.get("weekly_raw") if slot == "weekly" else None
            if remaining is None:
                remaining = row.get(f"{slot}_remaining")
            return round(100 * (1 - remaining), 4) if remaining is not None else None

        before, after = pct(old), pct(new)
        reset = new.get(f"{slot}_resets_at")
        reason = None
        if before is not None and after is not None and before - after >= 20:
            reason = "utilization_drop"
        try:
            old_reset = _parse_bonus_time(old.get(f"{slot}_resets_at"))
            new_reset = _parse_bonus_time(reset)
            if old_reset and new_reset and now < old_reset and new_reset - old_reset > timedelta(days=1):
                reason = reason or "reset_extended"
        except (ValueError, TypeError, OverflowError):
            pass
        if old.get("plan_type") and new.get("plan_type") and old["plan_type"] != new["plan_type"]:
            reason = reason or "plan_changed"
        if reason:
            return {"bucket": bucket, "from_pct": before, "to_pct": after,
                    "plan_type": new.get("plan_type"), "resets_at": reset, "reason": reason}
    return None


def drain_waiting():
    from tools import host_queue, budget_queue, route
    route._quota_cache.clear()
    for module in (host_queue, budget_queue):
        drain = getattr(module, "drain", None)
        if drain:
            result = drain()
            if inspect.isawaitable(result):
                asyncio.run(result)


def process(quotas, *, history=DEFAULT_HISTORY, resets=None, now=None):
    """Compare before history append. Fail before advancing history if publication fails."""
    now = _as_utc(now)
    previous = {r.get("provider"): r for r in rows(history)}
    events = []
    for bucket, quota in quotas.items():
        if bucket in BUCKETS and bucket in previous:
            event = reset_event(bucket, previous[bucket], asdict(quota), now)
            if event:
                events.append(event)
    if not events:
        return []
    path = Path(resets) if resets is not None else Path(history).with_name("quota-resets.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    published = []
    with path.open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        seen = {(r.get("bucket"), r.get("resets_at")) for r in rows(path)}
        for event in events:
            key = (event["bucket"], event["resets_at"])
            if key in seen:
                continue
            with db.get_conn() as conn:
                # Serialize hub publication across snapshot processes/hosts too.
                conn.execute("SELECT pg_advisory_xact_lock(716316301)")
                existing = conn.execute(
                    "SELECT id FROM events WHERE kind='quota_reset' "
                    "AND payload::jsonb->>'bucket' = ? "
                    "AND (payload::jsonb->>'resets_at') IS NOT DISTINCT FROM ? LIMIT 1", key,
                ).fetchone()
                if not existing:
                    db.log_event(conn, None, "quota_reset", "quota_reset", event)
            stream.write(json.dumps(event, sort_keys=True) + "\n")
            stream.flush()
            seen.add(key)
            published.append(event)
            if not existing:
                mail_reset(event)
    if published:
        drain_waiting()
    return published


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["last"])
    parser.add_argument("--bucket", choices=sorted(BUCKETS))
    args = parser.parse_args()
    latest = {}
    for event in rows(RESETS):
        if not args.bucket or event.get("bucket") == args.bucket:
            latest[event["bucket"]] = event
    for event in latest.values():
        print(json.dumps(event, sort_keys=True))


if __name__ == "__main__":
    main()
