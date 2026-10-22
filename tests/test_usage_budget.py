"""Daily budget calculations, history tail, and cache boundaries."""
import json
from datetime import datetime

import pytest

from tools import usage_budget as budget
from tools.quota import Quota, apply_bonuses, record_snapshot

NOW = datetime.fromisoformat("2026-10-22T12:00:00+07:00")


def row(at, value, **extra):
    return {"ts": at, "provider": "codex", "weekly_remaining": value,
            "weekly_resets_at": "2026-10-24T12:00:00+07:00", **extra}


def calc(rows, now=NOW):
    return budget.calculate(rows, now)["rows"]["chatgpt"]


def test_day_start_and_inclusive_reset():
    rows = [row("2026-10-21T23:50:00+07:00", .9), row("2026-10-22T00:00:00+07:00", .8),
            row(NOW.isoformat(), .7)]
    result = calc(rows)
    assert result["start_remaining"] == .8
    assert result["days_left"] == 3
    assert result["used"] == pytest.approx(.1)
    assert result["pace"] == pytest.approx(.8 / 6)
    assert result["headroom"] == pytest.approx(.8 / 3 - .1)


def test_first_today_and_reset_today():
    result = calc([row(NOW.isoformat(), .4, weekly_resets_at="2026-10-22T23:00:00+07:00")])
    assert result["days_left"] == 1
    assert result["target"] == .4
    assert result["used"] == 0


def test_midday_reset_positive_drops_only():
    rows = [row("2026-10-21T23:59:00+07:00", .2), row("2026-10-22T09:00:00+07:00", .1),
            row("2026-10-22T10:00:00+07:00", 1), row(NOW.isoformat(), .8)]
    result = calc(rows)
    assert result["used"] == pytest.approx(.3)
    assert result["state"] == "over"
    assert result["headroom"] < 0


def test_raw_bonus_and_old_history(tmp_path):
    q = apply_bonuses(Quota("codex", weekly_remaining=.4), [{"provider": "codex"}], NOW)
    assert q.weekly_remaining == 1
    assert q.weekly_raw == .4
    path = tmp_path / "history"
    record_snapshot({"codex": q}, path, NOW)
    assert json.loads(path.read_text())["weekly_raw"] == .4
    result = calc([row(NOW.isoformat(), 1, weekly_raw=.4, source="quota (bonus: active)")])
    assert result["now_remaining"] == .4
    assert result["bonus"] is True
    assert calc([row(NOW.isoformat(), .6)])["now_remaining"] == .6
    assert calc([row(NOW.isoformat(), .6, weekly_raw=None)])["now_remaining"] == .6


@pytest.mark.parametrize("rows", [[], [row("2026-10-22T11:29:59+07:00", .5)],
                                  [row(NOW.isoformat(), .5, error="unavailable")]])
def test_unknown(rows):
    assert calc(rows)["state"] == "unknown"


def test_tail_keeps_preceding_for_each_bucket(tmp_path):
    path = tmp_path / "history"
    rows = [row("2026-10-21T20:00:00+07:00", .9, provider=b) for b in budget.BUCKETS.values()]
    rows += [row(NOW.isoformat(), .7)]
    path.write_text("x" * 70000 + "\n" + "\n".join(json.dumps(r) for r in rows))
    assert budget.read_history(path, NOW) == rows


def test_write_cache_and_thai_midnight(tmp_path):
    history, snapshot = tmp_path / "history", tmp_path / "budget.json"
    history.write_text(json.dumps(row(NOW.isoformat(), .7)) + "\n")
    data = budget.write(snapshot, history, NOW)
    assert json.loads(snapshot.read_text()) == data
    assert budget.load_rows(snapshot, history, NOW) == data["rows"]
    snapshot.write_text("broken")
    assert budget.load_rows(snapshot, history, NOW) == data["rows"]
    old = {**data, "ts": "2026-10-21T23:59:00+07:00", "day": "2026-10-21"}
    snapshot.write_text(json.dumps(old))
    midnight = datetime.fromisoformat("2026-10-22T00:01:00+07:00")
    assert budget.load_rows(snapshot, history, midnight)["chatgpt"]["state"] == "unknown"
