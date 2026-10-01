"""tools/disk_watch.py: ADR 0030's yellow letter and orange reclaim, on a
schedule (every watchdog tick) instead of only at spawn time."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import disk_watch  # noqa: E402

T0 = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)


@pytest.fixture()
def run(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_DISK_WATCH", "on")
    letters: list[str] = []
    reclaims: list[int] = []

    def _run(free, now=T0):
        def reclaim():
            reclaims.append(1)
            return (2 * 1024 ** 3, 3)
        return disk_watch.check(now=now, free_gb=free, state_path=tmp_path / "s.json",
                                notify=letters.append, reclaim=reclaim, host="contabo")
    _run.letters, _run.reclaims = letters, reclaims
    return _run


def test_green_does_nothing(run):
    r = run(50.0)
    assert r["band"] == "green" and not r["notified"] and run.letters == [] and run.reclaims == []


def test_yellow_writes_once_a_day(run):
    assert run(15.0)["notified"] is True
    assert run(15.0, T0 + timedelta(hours=5))["notified"] is False
    assert run(15.0, T0 + timedelta(hours=25))["notified"] is True
    assert len(run.letters) == 2 and run.reclaims == []
    assert "contabo: 15.0 GB free (yellow" in run.letters[0]


def test_getting_worse_writes_straight_away_and_orange_reclaims(run):
    run(15.0)
    r = run(8.0, T0 + timedelta(minutes=10))
    assert r["band"] == "orange" and r["notified"] and r["reclaimed_bytes"] == 2 * 1024 ** 3
    assert "freed 2.0 GB" in run.letters[-1]
    run(8.0, T0 + timedelta(minutes=20))
    assert len(run.reclaims) == 1  # once an hour
    run(8.0, T0 + timedelta(minutes=80))
    assert len(run.reclaims) == 2


def test_back_to_green_rearms(run):
    run(15.0)
    run(50.0, T0 + timedelta(hours=1))
    assert run(15.0, T0 + timedelta(hours=2))["notified"] is True


def test_switched_off_is_a_no_op(tmp_path, monkeypatch):
    monkeypatch.setenv("ORG_DISK_WATCH", "off")
    assert disk_watch.check(free_gb=1.0, state_path=tmp_path / "s.json",
                            notify=lambda b: pytest.fail("notified"),
                            reclaim=lambda: pytest.fail("reclaimed")) == {"skipped": "ORG_DISK_WATCH=off"}
