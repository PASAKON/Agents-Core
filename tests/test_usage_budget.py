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
    assert result["start_remaining"] == 1
    assert result["used"] == pytest.approx(.2)


def test_midday_reset_after_empty_midnight():
    result = calc([row("2026-10-22T00:00:00+07:00", 0),
                   row("2026-10-22T11:00:00+07:00", .93), row(NOW.isoformat(), .93)])
    assert result["start_remaining"] == .93
    assert result["target"] > 0
    assert result["state"] == "under"


def test_empty_midnight_without_reset_stays_over():
    result = calc([row("2026-10-22T00:00:00+07:00", 0),
                   row("2026-10-22T11:00:00+07:00", .01), row(NOW.isoformat(), 0)])
    assert result["start_remaining"] == 0
    assert result["used"] == pytest.approx(.01)
    assert result["state"] == "over"


def test_claude_reset_timestamp_jitter_preserves_drops():
    rows = [row(at, value, provider="claude", weekly_resets_at=reset) for at, value, reset in [
        ("2026-10-22T00:00:00+07:00", .9, "2026-10-24T12:00:00.500000+07:00"),
        ("2026-10-22T09:00:00+07:00", .7, "2026-10-24T12:00:00.520000+07:00"),
        ("2026-10-22T10:00:00+07:00", .5, "2026-10-24T12:00:00.480000+07:00"),
        (NOW.isoformat(), .4, "2026-10-24T12:00:00.510000+07:00"),
    ]]
    result = budget.calculate(rows, NOW)["rows"]["claude"]
    assert result["start_remaining"] == .9
    assert result["used"] == pytest.approx(.2 + .2 + .1)
    assert result["used"] > result["target"]
    assert result["state"] == "over"


@pytest.mark.parametrize("previous_reset,current_reset,expected_start,expected_used", [
    ("2026-10-24T12:00:00+07:00", "2026-10-24T12:59:59+07:00", .9, .5),
    ("2026-10-24T12:00:00+07:00", "2026-10-24T13:00:00+07:00", .5, .1),
    (None, "2026-10-24T12:00:00+07:00", .9, .5),
    ("2026-10-24T12:00:00+07:00", None, .9, .5),
])
def test_reset_timestamp_threshold_and_missing(previous_reset, current_reset, expected_start, expected_used):
    result = calc([row("2026-10-22T00:00:00+07:00", .9, weekly_resets_at=previous_reset),
                   row("2026-10-22T11:00:00+07:00", .5, weekly_resets_at=current_reset),
                   row(NOW.isoformat(), .4, weekly_resets_at=current_reset)])
    assert result["start_remaining"] == expected_start
    assert result["used"] == pytest.approx(expected_used)


def test_last_reset_sets_baseline_and_latest_reset_sets_days():
    result = calc([row("2026-10-22T00:00:00+07:00", .2),
                   row("2026-10-22T09:00:00+07:00", 1),
                   row("2026-10-22T10:00:00+07:00", .5),
                   row("2026-10-22T11:00:00+07:00", .9,
                       weekly_resets_at="2026-10-28T12:00:00+07:00"),
                   row(NOW.isoformat(), .8, weekly_resets_at="2026-10-28T12:00:00+07:00")])
    assert result["start_remaining"] == .9
    assert result["used"] == pytest.approx(.1)
    assert result["days_left"] == 7


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


def test_error_row_today_is_skipped_not_unknown():
    from datetime import datetime, timezone
    from tools import usage_budget as ub
    now = datetime(2026, 10, 22, 5, 0, tzinfo=timezone.utc)
    rs = "2026-10-24T00:00:00Z"
    hist = [
        {"ts": "2026-10-21T16:50:00+00:00", "provider": "claude", "weekly_remaining": 0.9, "weekly_resets_at": rs},
        {"ts": "2026-10-22T03:00:00+00:00", "provider": "claude", "weekly_remaining": None, "error": "ssh timeout", "weekly_resets_at": rs},
        {"ts": "2026-10-22T04:50:00+00:00", "provider": "claude", "weekly_remaining": 0.8, "weekly_resets_at": rs},
    ]
    row = ub.calculate(hist, now)["rows"]["claude"]
    assert row["state"] == "under"
    assert abs(row["used"] - 0.1) < 1e-9
    assert abs(row["target"] - 0.3) < 1e-9
