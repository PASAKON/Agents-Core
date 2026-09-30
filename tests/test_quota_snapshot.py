"""Tests for quota snapshot precomputation (PLAN-auto-dispatch.md §3).

Covers:
(a) write_snapshot then read_snapshot round-trips 4 buckets
(b) read_snapshot returns None for missing file, invalid JSON, missing keys, and ts older than max_age_s
(c) cached_quotas returns snapshot without calling fetch_all_quotas when fresh and error-free
(d) cached_quotas falls back to fetch_all_quotas when a snapshot bucket has an error
(e) CLI --snapshot flag writes snapshot, appends history, prints expected output, exits 0 even on bucket error
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.quota as quota_mod
from tools.quota import (
    DEFAULT_HISTORY,
    SNAPSHOT_PATH,
    Quota,
    read_snapshot,
    record_snapshot,
    write_snapshot,
)
import tools.route as route
from tools.route import cached_quotas


@pytest.fixture
def four_buckets() -> dict[str, Quota]:
    return {
        "claude": Quota(
            provider="claude",
            weekly_remaining=0.5,
            daily_remaining=0.8,
            weekly_resets_at="2026-10-06T00:00:00+00:00",
            daily_resets_at="2026-09-30T00:00:00+00:00",
            source="vps",
            error=None,
        ),
        "codex": Quota(
            provider="codex",
            weekly_remaining=0.7,
            daily_remaining=0.9,
            weekly_resets_at="2026-10-05T00:00:00+00:00",
            daily_resets_at=None,
            source="session",
            error=None,
        ),
        "agy-gemini": Quota(
            provider="agy-gemini",
            weekly_remaining=1.0,
            daily_remaining=0.75,
            weekly_resets_at="2026-10-06T00:05:38Z",
            daily_resets_at="2026-09-29T12:00:00Z",
            source="cli",
            error=None,
        ),
        "agy-claude": Quota(
            provider="agy-claude",
            weekly_remaining=0.95,
            daily_remaining=0.85,
            weekly_resets_at="2026-10-06T00:05:38Z",
            daily_resets_at="2026-09-29T12:00:00Z",
            source="cli",
            error=None,
        ),
    }


def test_write_read_snapshot_roundtrip(tmp_path: Path, four_buckets: dict[str, Quota]):
    path = tmp_path / "quota-snapshot.json"
    fixed_now = datetime(2026, 9, 30, 5, 10, 0, tzinfo=timezone.utc)

    out_path = write_snapshot(four_buckets, path=path, now=fixed_now)
    assert out_path == path
    assert path.is_file()

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    assert raw_data["ts"] == "2026-09-30T05:10:00+00:00"
    assert set(raw_data["buckets"].keys()) == {"claude", "codex", "agy-gemini", "agy-claude"}

    loaded = read_snapshot(path, now=fixed_now)
    assert loaded is not None
    assert set(loaded.keys()) == set(four_buckets.keys())

    for name, expected in four_buckets.items():
        actual = loaded[name]
        assert actual.provider == expected.provider
        assert actual.weekly_remaining == expected.weekly_remaining
        assert actual.daily_remaining == expected.daily_remaining
        assert actual.weekly_resets_at == expected.weekly_resets_at
        assert actual.daily_resets_at == expected.daily_resets_at
        assert actual.source == expected.source
        assert actual.error == expected.error


def test_read_snapshot_invalid_or_stale(tmp_path: Path, four_buckets: dict[str, Quota]):
    # 1. Missing file returns None
    missing_path = tmp_path / "missing-snapshot.json"
    assert read_snapshot(missing_path) is None

    # 2. Invalid JSON returns None
    bad_json_path = tmp_path / "broken.json"
    bad_json_path.write_text("{invalid json structure", encoding="utf-8")
    assert read_snapshot(bad_json_path) is None

    # 3. JSON not a dict returns None
    not_dict_path = tmp_path / "list.json"
    not_dict_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    assert read_snapshot(not_dict_path) is None

    # 4. Missing "ts" or "buckets" returns None
    no_ts_path = tmp_path / "no-ts.json"
    no_ts_path.write_text(json.dumps({"buckets": {}}), encoding="utf-8")
    assert read_snapshot(no_ts_path) is None

    no_buckets_path = tmp_path / "no-buckets.json"
    no_buckets_path.write_text(json.dumps({"ts": "2026-09-30T05:10:00+00:00"}), encoding="utf-8")
    assert read_snapshot(no_buckets_path) is None

    # 5. Timestamp older than max_age_s returns None
    snap_path = tmp_path / "stale.json"
    write_time = datetime(2026, 9, 30, 5, 0, 0, tzinfo=timezone.utc)
    write_snapshot(four_buckets, path=snap_path, now=write_time)

    # 901 seconds later (> 900s) -> None
    stale_time = datetime(2026, 9, 30, 5, 15, 1, tzinfo=timezone.utc)
    assert read_snapshot(snap_path, max_age_s=900, now=stale_time) is None

    # 900 seconds later (<= 900s) -> valid dict
    fresh_time = datetime(2026, 9, 30, 5, 15, 0, tzinfo=timezone.utc)
    res_fresh = read_snapshot(snap_path, max_age_s=900, now=fresh_time)
    assert res_fresh is not None
    assert len(res_fresh) == 4


def test_cached_quotas_uses_fresh_snapshot_without_live_fetch(
    tmp_path: Path,
    four_buckets: dict[str, Quota],
    monkeypatch: pytest.MonkeyPatch,
):
    snap_path = tmp_path / "quota-snapshot.json"
    write_snapshot(four_buckets, path=snap_path, now=datetime.now(timezone.utc))

    monkeypatch.setattr(quota_mod, "SNAPSHOT_PATH", snap_path)
    route._quota_cache.clear()

    def fail_fetch(cfg):
        raise RuntimeError("fetch_all_quotas must not be called when snapshot is fresh")

    monkeypatch.setattr(route, "fetch_all_quotas", fail_fetch)

    res = cached_quotas({}, now=100.0)
    assert set(res.keys()) == set(four_buckets.keys())
    assert res["claude"].weekly_remaining == 0.5
    assert route._quota_cache["quotas"] is res


def test_cached_quotas_falls_back_when_snapshot_has_error(
    tmp_path: Path,
    four_buckets: dict[str, Quota],
    monkeypatch: pytest.MonkeyPatch,
):
    snap_path = tmp_path / "quota-snapshot.json"
    four_buckets["agy-gemini"].error = "ssh command timed out"
    write_snapshot(four_buckets, path=snap_path, now=datetime.now(timezone.utc))

    monkeypatch.setattr(quota_mod, "SNAPSHOT_PATH", snap_path)
    route._quota_cache.clear()

    live_quotas = {
        name: Quota(provider=name, weekly_remaining=0.99, error=None)
        for name in four_buckets
    }
    fetch_called = False

    def mock_fetch(cfg):
        nonlocal fetch_called
        fetch_called = True
        return live_quotas

    monkeypatch.setattr(route, "fetch_all_quotas", mock_fetch)

    res = cached_quotas({}, now=100.0)
    assert fetch_called is True
    assert res is live_quotas
    assert res["agy-gemini"].error is None


def test_cli_snapshot_flag(
    tmp_path: Path,
    four_buckets: dict[str, Quota],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    snap_file = tmp_path / "custom-snap.json"
    history_file = tmp_path / "custom-hist.jsonl"

    monkeypatch.setattr(quota_mod, "SNAPSHOT_PATH", snap_file)
    monkeypatch.setattr(quota_mod, "DEFAULT_HISTORY", history_file)
    monkeypatch.setattr(quota_mod, "load_plans", lambda path=None: {})
    monkeypatch.setattr(quota_mod, "fetch_all_quotas", lambda cfg, now=None: four_buckets)
    monkeypatch.setattr(sys, "argv", ["quota.py", "--snapshot"])

    quota_mod.main()

    captured = capsys.readouterr()
    expected_prefix = f"snapshot: {snap_file} 4 buckets "
    assert captured.out.startswith(expected_prefix)
    assert snap_file.is_file()
    assert history_file.is_file()

    snap_data = json.loads(snap_file.read_text(encoding="utf-8"))
    assert set(snap_data["buckets"].keys()) == set(four_buckets.keys())

    history_lines = history_file.read_text(encoding="utf-8").splitlines()
    assert len(history_lines) == 4


def test_cli_snapshot_flag_exits_0_on_bucket_error(
    tmp_path: Path,
    four_buckets: dict[str, Quota],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    four_buckets["agy-claude"].error = "failed to parse /usage"
    snap_file = tmp_path / "custom-snap.json"
    history_file = tmp_path / "custom-hist.jsonl"

    monkeypatch.setattr(quota_mod, "SNAPSHOT_PATH", snap_file)
    monkeypatch.setattr(quota_mod, "DEFAULT_HISTORY", history_file)
    monkeypatch.setattr(quota_mod, "load_plans", lambda path=None: {})
    monkeypatch.setattr(quota_mod, "fetch_all_quotas", lambda cfg, now=None: four_buckets)
    monkeypatch.setattr(sys, "argv", ["quota.py", "--snapshot"])

    quota_mod.main()

    captured = capsys.readouterr()
    assert f"snapshot: {snap_file} 4 buckets " in captured.out
    snap_data = json.loads(snap_file.read_text(encoding="utf-8"))
    assert snap_data["buckets"]["agy-claude"]["error"] == "failed to parse /usage"
