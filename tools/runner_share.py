"""One-line Bangkok-day worker and in-session activity report."""
import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TH = ZoneInfo("Asia/Bangkok")


def on_day(value, day):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp.replace(tzinfo=stamp.tzinfo or timezone.utc).astimezone(TH).date() == day
    except (ValueError, TypeError):
        return False


def summary(conn, day, reports=ROOT / "state/reports"):
    counts = Counter()
    for row in conn.execute("SELECT runner, created_at FROM tasks").fetchall():
        if on_day(row["created_at"], day):
            runner = row["runner"]
            counts[runner if runner in {"claude", "codex", "agy"} else "other"] += 1
    sessions = defaultdict(lambda: [0, 0, 0])
    for name in ("agent-route", "ph-handson"):
        path = reports / (name + ".jsonl")
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
                if not on_day(row["ts"], day):
                    continue
                if name == "agent-route" and row.get("decision") == "error_allow":
                    continue
                sessions[str(row.get("session_id") or "?")][
                    2 if name == "ph-handson" else 0 if row.get("has_reason") else 1] += 1
            except (ValueError, TypeError, KeyError):
                continue
    outside = 100 * (counts["codex"] + counts["agy"]) / max(1, sum(counts.values()))
    text = f"{day} TH workers " + " ".join(f"{r}={counts[r]}" for r in ("claude", "codex", "agy", "other"))
    text += f" outside={outside:.1f}%; sessions Agent+/-/PH:"
    items = [f" {sid}={a}/{b}/{c}" for sid, (a, b, c) in sorted(sessions.items())]
    for i, item in enumerate(items):
        if len(text + item) > 275:
            text += f" +{len(items)-i} sessions"
            break
        text += item
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", type=date.fromisoformat,
                        default=datetime.now(TH).date() - timedelta(days=1))
    args = parser.parse_args()
    from lib.db import get_conn
    with get_conn(readonly=True) as conn:
        print(summary(conn, args.day))


if __name__ == "__main__":
    main()
