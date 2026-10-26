"""Daily Thai-time usage targets derived solely from quota history."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "state/reports/quota-history.jsonl"
# Its own directory: the widget endpoint container mounts only this dir, read-only.
SNAPSHOT = ROOT / "state/usage-budget/usage-budget.json"
THAI = timezone(timedelta(hours=7))
BUCKETS = {"agy": "agy-gemini", "chatgpt": "codex", "claude": "claude", "agy-claude": "agy-claude"}


def timestamp(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def reverse_lines(path):
    """Stream complete lines backwards with bounded memory."""
    with Path(path).open("rb") as stream:
        stream.seek(0, 2)
        position, pending = stream.tell(), b""
        while position:
            size = min(position, 65536)
            position -= size
            stream.seek(position)
            parts = (stream.read(size) + pending).split(b"\n")
            pending = parts[0]
            yield from reversed(parts[1:])
        if pending:
            yield pending


def read_history(path, now):
    """Read today's tail plus the last preceding observation for each bucket."""
    start = timestamp(now).astimezone(THAI).replace(hour=0, minute=0, second=0, microsecond=0)
    rows, preceding = [], set()
    if not Path(path).exists():
        return rows
    for line in reverse_lines(path):
        try:
            row = json.loads(line)
            ts = timestamp(row["ts"])
            bucket = row["provider"]
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
        if bucket not in BUCKETS.values() or ts > now:
            continue
        if ts <= start:
            if bucket in preceding:
                continue
            preceding.add(bucket)
        rows.append(row)
        if len(preceding) == len(BUCKETS):
            break
    return list(reversed(rows))


def weekly(row):
    value = row.get("weekly_raw")
    if value is None:
        value = row.get("weekly_remaining")
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return max(0.0, min(1.0, value))


def calculate(history, now):
    now = timestamp(now)
    start = now.astimezone(THAI).replace(hour=0, minute=0, second=0, microsecond=0)
    result = {"ts": now.isoformat(), "day": start.date().isoformat(), "rows": {}}
    for label, bucket in BUCKETS.items():
        records = sorted((r for r in history if r.get("provider") == bucket and timestamp(r["ts"]) <= now),
                         key=lambda r: timestamp(r["ts"]))
        # A failed read is a gap, not a fact: skip it, and let staleness decide unknown.
        records = [r for r in records if not r.get("error") and weekly(r) is not None]
        before = [r for r in records if timestamp(r["ts"]) <= start]
        today = [r for r in records if timestamp(r["ts"]) > start]
        records = before[-1:] + today
        latest = records[-1] if records else {}
        initial = weekly(records[0]) if records else None
        reset = latest.get("weekly_resets_at")
        try:
            days = max(1, (timestamp(reset).astimezone(THAI).date() - start.date()).days + 1)
        except (ValueError, TypeError, AttributeError):
            days = None
        target = initial / days if initial is not None and days else None
        values = [weekly(r) for r in records]
        used = sum(max(0.0, a - b) for a, b in zip(values, values[1:]) if a is not None and b is not None)
        unknown = (not records or target is None
                   or (now - timestamp(latest["ts"])).total_seconds() > 1800)
        result["rows"][label] = {
            "bucket": bucket, "start_remaining": initial, "days_left": days, "target": target,
            "used": used if records else None,
            "pace": target * (now - start).total_seconds() / 86400 if target is not None else None,
            "headroom": target - used if target is not None else None,
            "state": "unknown" if unknown else "over" if used > target else "under",
            "now_remaining": weekly(latest), "weekly_resets_at": reset,
            "bonus": "(bonus:" in latest.get("source", ""),
        }
    return result


def today(history=HISTORY, now=None):
    now = timestamp(now) if now is not None else datetime.now(timezone.utc)
    return calculate(read_history(history, now), now)


def write(path=None, history=HISTORY, now=None):
    data = today(history, now)
    path = Path(path) if path is not None else SNAPSHOT
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
            name = stream.name
            json.dump(data, stream)
            stream.write("\n")
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)
    return data


def load_gate_rows(path=None, now=None):
    """Only a fresh snapshot can close the tier gate; never reconstruct stale data."""
    try:
        now = timestamp(now) if now is not None else datetime.now(timezone.utc)
        data = json.loads(Path(path if path is not None else SNAPSHOT).read_text())
        age = (now - timestamp(data["ts"])).total_seconds()
        if not 0 <= age <= 1800 or data["day"] != now.astimezone(THAI).date().isoformat():
            return None
        rows = data["rows"]
        if not isinstance(rows, dict):
            return None
        return {r.get("bucket", key): r for key, r in rows.items()
                if isinstance(r, dict) and r.get("state") in ("under", "over")}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def load_rows(path=None, history=HISTORY, now=None):
    """Routing is fail-open; cached budgets must also belong to today's Thai day."""
    try:
        now = timestamp(now) if now is not None else datetime.now(timezone.utc)
        try:
            data = json.loads(Path(path if path is not None else SNAPSHOT).read_text())
            age = (now - timestamp(data["ts"])).total_seconds()
            if 0 <= age <= 1800 and data["day"] == now.astimezone(THAI).date().isoformat():
                rows = data["rows"]
                if not isinstance(rows, dict) or any(not isinstance(r, dict) for r in rows.values()):
                    raise ValueError("invalid budget rows")
                return rows
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass
        return today(history, now)["rows"]
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["today", "write"])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--history", type=Path, default=HISTORY)
    parser.add_argument("--now")
    args = parser.parse_args()
    data = write(history=args.history, now=args.now) if args.command == "write" else today(args.history, args.now)
    if args.json:
        print(json.dumps(data))
        return
    def pct(value, signed=False):
        return "?" if value is None else format(value, "+.1%" if signed else ".1%")
    for label, row in data["rows"].items():
        try:
            reset = timestamp(row["weekly_resets_at"]).astimezone(THAI).strftime("%d %b")
        except (ValueError, TypeError, AttributeError):
            reset = "unknown"
        print(f"{label:10} used {pct(row['used'])} / target {pct(row['target'])}  "
              f"pace {pct(row['pace'])}  headroom {pct(row['headroom'], True)}  {row['state']}  (resets {reset})")


if __name__ == "__main__":
    main()
