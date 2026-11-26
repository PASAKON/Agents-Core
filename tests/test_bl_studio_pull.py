"""Unit tests for tools/bl_studio_pull.py (task-f19ca94b).

Exercises the pure raw-JSON adapters against the saved samples in
state/cgo/bl/raw-schema/, alternate TikTok Studio response shapes, 30-day window
flagging, URL query-token stripping, >= 3 s pacing enforcement, /login
(SIGNED_OUT exit 4) and captcha/verify (exit 3) handling, home_lock acquire +
release in finally, and JSON + flat CSV writing.

Run via:  pytest tests/test_bl_studio_pull.py
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools import bl_studio_pull as pull

RAW_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "state" / "cgo" / "bl" / "raw-schema"
REF_UTC = datetime(2026, 11, 26, 0, 0, 0, tzinfo=timezone.utc)


def _load_raw_sample(name: str) -> dict:
    return json.loads((RAW_SCHEMA_DIR / name).read_text(encoding="utf-8"))


# ── saved raw-schema sample validation ──────────────────────────────────────


def test_saved_raw_schema_samples_strip_all_query_tokens():
    sample_files = sorted(RAW_SCHEMA_DIR.glob("*.json"))
    assert len(sample_files) >= 3
    for path in sample_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        endpoint_path = data.get("_meta", {}).get("endpoint_path", "")
        assert endpoint_path.startswith("https://www.tiktok.com/")
        assert "?" not in endpoint_path
        assert "#" not in endpoint_path
        assert "msToken" not in endpoint_path
        assert "verifyFp" not in endpoint_path


def test_extract_content_list_from_saved_raw_sample():
    rows = pull.extract_content_list_from_raw(_load_raw_sample("content_list.json"))
    assert len(rows) == 3

    first = rows[0]
    assert first["video_id"] == "7440100000000000001"
    assert first["post_time_utc"] == "2025-11-24T04:00:00Z"
    assert len(first["caption_80"]) <= 80
    assert first["caption_80"].startswith("โบรกเกอร์เถื่อนอ้างใบอนุญาต ASIC ปลอม")
    assert first["duration_s"] == 58.0
    assert first["views"] == 28450
    assert first["likes"] == 1920
    assert first["comments"] == 64
    assert first["shares"] == 310
    assert first["saves"] == 485


def test_extract_video_analytics_from_saved_raw_sample():
    detail = pull.extract_video_analytics_from_raw(_load_raw_sample("video_analytics.json"))
    assert detail["video_id"] == "7440100000000000001"
    assert detail["avg_watch_time_s"] == 24.6
    assert detail["watched_full_video_pct"] == 21.8
    assert detail["new_followers"] == 134
    assert len(detail["retention_curve"]) == 7
    assert detail["retention_curve"][0] == {"t_s": 0, "pct": 100.0}
    assert detail["retention_curve"][-1] == {"t_s": 58, "pct": 21.8}
    assert detail["traffic_sources"] == {
        "for_you": 74.2,
        "search": 12.8,
        "profile": 6.5,
        "following": 4.1,
        "other": 2.4,
    }


def test_extract_account_overview_from_saved_raw_sample():
    acc = pull.extract_account_overview_from_raw(_load_raw_sample("account_overview.json"))
    assert acc == {
        "followers_start": 14210,
        "followers_end": 14685,
        "total_views": 43750,
    }


# ── alternate TikTok Studio JSON shapes & error handling ────────────────────


def test_extract_content_list_handles_nested_data_and_truncates_caption_to_80_chars():
    long_caption = "A" * 120
    raw = {
        "data": {
            "item_list": [
                {
                    "id": "7449990000000000009",
                    "createTime": "1764043200",
                    "title": long_caption,
                    "video_meta": {"duration_ms": 64500},
                    "item_stat": {
                        "playCount": "31,200",
                        "diggCount": 1400,
                        "commentCount": 52,
                        "shareCount": 180,
                        "collectCount": 290,
                    },
                }
            ]
        }
    }
    rows = pull.extract_content_list_from_raw(raw)
    assert len(rows) == 1
    r = rows[0]
    assert r["video_id"] == "7449990000000000009"
    assert r["post_time_utc"] == "2025-11-25T04:00:00Z"
    assert r["caption_80"] == "A" * 80
    assert len(r["caption_80"]) == 80
    assert r["duration_s"] == 64.5
    assert r["views"] == 31200
    assert r["likes"] == 1400
    assert r["saves"] == 290


def test_extract_video_analytics_handles_dict_traffic_sources_and_ratio_retention():
    raw = {
        "data": {
            "item_id": "7449990000000000009",
            "average_watch_time": 19.25,
            "completion_rate": 0.165,
            "followers_gained": 42,
            "video_retention": [
                {"timestamp": 0, "rate": 1.0},
                {"timestamp": 5, "rate": 0.625},
                {"timestamp": 15, "rate": 0.165},
            ],
            "impression_sources": {
                "fyp": 70.0,
                "search": 15.0,
                "profile": 8.0,
                "following": 5.0,
                "sound": 1.2,
                "hashtag": 0.8,
            },
        }
    }
    parsed = pull.extract_video_analytics_from_raw(raw)
    assert parsed["video_id"] == "7449990000000000009"
    assert parsed["avg_watch_time_s"] == 19.25
    assert parsed["watched_full_video_pct"] == 16.5
    assert parsed["new_followers"] == 42
    assert parsed["retention_curve"] == [
        {"t_s": 0, "pct": 100.0},
        {"t_s": 5, "pct": 62.5},
        {"t_s": 15, "pct": 16.5},
    ]
    assert parsed["traffic_sources"] == {
        "for_you": 70.0,
        "search": 15.0,
        "profile": 8.0,
        "following": 5.0,
        "other": 2.0,
    }


def test_extract_account_overview_derives_start_and_end_from_follower_series():
    raw = {
        "data": {
            "follower_history": [
                {"date": "2026-10-28", "followers": 10100},
                {"date": "2026-11-10", "followers": 10350},
                {"date": "2026-11-26", "followers": 10890},
            ],
            "video_views": 95400,
        }
    }
    acc = pull.extract_account_overview_from_raw(raw)
    assert acc == {
        "followers_start": 10100,
        "followers_end": 10890,
        "total_views": 95400,
    }


def test_adapters_raise_on_unrecognized_shape():
    bad = {"unexpected": "shape", "code": 0}
    with pytest.raises(pull.UnrecognizedResponseShape):
        pull.extract_content_list_from_raw(bad)
    with pytest.raises(pull.UnrecognizedResponseShape):
        pull.extract_video_analytics_from_raw(bad)
    with pytest.raises(pull.UnrecognizedResponseShape):
        pull.extract_account_overview_from_raw(bad)


# ── 30-day window flagging, merging & unexposed fields ──────────────────────


def test_merge_and_flag_30d_window_flags_older_videos():
    # Reference time: 2025-11-26T00:00:00Z (matches epoch dates in content_list.json)
    ref = datetime(2025, 11, 26, 0, 0, 0, tzinfo=timezone.utc)
    content_rows = pull.extract_content_list_from_raw(_load_raw_sample("content_list.json"))
    va = pull.extract_video_analytics_from_raw(_load_raw_sample("video_analytics.json"))
    merged = pull.merge_video_records(content_rows, {va["video_id"]: va}, reference_utc=ref)

    assert len(merged) == 3
    assert merged[0]["within_30d"] is True
    assert merged[0]["older_than_30d"] is False
    assert merged[0]["avg_watch_time_s"] == 24.6
    assert merged[0]["traffic_sources"]["for_you"] == 74.2

    assert merged[1]["within_30d"] is True
    assert merged[1]["older_than_30d"] is False
    # Video 2 had no detail sample -> deep fields remain None
    assert merged[1]["avg_watch_time_s"] is None

    # Video 3 was posted 2025-10-05 (>30 days before 2025-11-26) -> flagged older_than_30d
    assert merged[2]["video_id"] == "7420500000000000003"
    assert merged[2]["within_30d"] is False
    assert merged[2]["older_than_30d"] is True


def test_detect_unexposed_fields_identifies_missing_studio_metrics():
    content_rows = pull.extract_content_list_from_raw(_load_raw_sample("content_list.json"))
    ref = datetime(2025, 11, 26, 0, 0, 0, tzinfo=timezone.utc)
    # Without per-video analytics or account follower counts, those fields are reported unexposed
    merged = pull.merge_video_records(content_rows, {}, reference_utc=ref)
    payload = pull.build_pull_payload(merged, account_overview=None, pulled_at_utc=ref)

    assert set(payload["unexposed_fields"]["per_video"]) == {
        "avg_watch_time_s",
        "watched_full_video_pct",
        "retention_curve",
        "traffic_sources",
        "new_followers",
    }
    assert set(payload["unexposed_fields"]["account_window"]) == {
        "followers_start",
        "followers_end",
    }
    # total_views falls back to sum of 30d video views when account_overview is absent
    assert payload["account_window"]["total_views"] == 28450 + 15300


# ── URL sanitization, pacing, guards & lock lifecycle ───────────────────────


def test_sanitize_url_strips_query_and_fragment_tokens():
    dirty = (
        "https://www.tiktok.com/aweme/v2/data/insight/video/detail/"
        "?msToken=abc123SECRET&verifyFp=verify_999&_signature=_02B4Z6wo00f01#section"
    )
    clean = pull.sanitize_url(dirty)
    assert clean == "https://www.tiktok.com/aweme/v2/data/insight/video/detail/"
    assert "msToken" not in clean
    assert "SECRET" not in clean


def test_enforce_pacing_sleeps_when_interval_is_under_3_seconds():
    slept: list[float] = []
    now = [100.0]

    def fake_clock() -> float:
        return now[0]

    def fake_sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    t1 = pull.enforce_pacing(None, 3.0, sleep_fn=fake_sleep, clock_fn=fake_clock)
    assert t1 == 100.0
    assert slept == []

    now[0] = 101.2  # only 1.2s elapsed
    t2 = pull.enforce_pacing(t1, 2.0, sleep_fn=fake_sleep, clock_fn=fake_clock)  # even if caller passes 2.0, min is 3.0
    assert len(slept) == 1
    assert pytest.approx(slept[0], rel=1e-3) == 1.8
    assert pytest.approx(t2, rel=1e-3) == 103.0


def test_login_and_verification_detection():
    assert pull.is_login_url("https://www.tiktok.com/login") is True
    assert pull.is_login_url("https://www.tiktok.com/login/qrcode?redirect_url=...") is True
    assert pull.is_login_url("https://www.tiktok.com/tiktokstudio/content") is False

    assert pull.has_verification_marker("Please slide to verify to continue") is True
    assert pull.has_verification_marker("กรุณายืนยันตัวตนเพื่อดำเนินการต่อ") is True
    assert pull.has_verification_marker("TikTok Studio Content Analytics") is False


def test_main_exits_4_on_signed_out_and_always_releases_lock(monkeypatch, capsys):
    events: list[tuple[str, str]] = []

    def fake_acquire(key: str, owner: str | None = None, ttl: int = 1800, purpose: str = "") -> dict:
        events.append(("acquire", f"{key}:{purpose}"))
        return {"key": key, "owner": owner}

    def fake_release(key: str, owner: str | None = None) -> bool:
        events.append(("release", key))
        return True

    def fake_run_live_pull(**kwargs):
        events.append(("run_live_pull", "called"))
        raise pull.SignedOut("SIGNED_OUT")

    monkeypatch.setattr(pull.home_lock, "acquire", fake_acquire)
    monkeypatch.setattr(pull.home_lock, "release", fake_release)
    monkeypatch.setattr(pull, "run_live_pull", fake_run_live_pull)

    code = pull.main(["--owner", "task-f19ca94b"])
    captured = capsys.readouterr()

    assert code == pull.EXIT_SIGNED_OUT == 4
    assert captured.out.strip() == "SIGNED_OUT"
    assert events == [
        ("acquire", "home:contabo:9282:CGO studio pull"),
        ("run_live_pull", "called"),
        ("release", "home:contabo:9282"),
    ]


def test_main_exits_3_on_captcha_and_always_releases_lock(monkeypatch):
    events: list[str] = []

    monkeypatch.setattr(pull.home_lock, "acquire", lambda key, **kw: events.append(f"acquire:{key}") or {})
    monkeypatch.setattr(pull.home_lock, "release", lambda key, **kw: events.append(f"release:{key}") or True)

    def fake_run_live_pull(**kwargs):
        raise pull.VerificationWall("captcha detected")

    monkeypatch.setattr(pull, "run_live_pull", fake_run_live_pull)

    code = pull.main(["--owner", "task-f19ca94b"])
    assert code == pull.EXIT_CAPTCHA == 3
    assert events == ["acquire:home:contabo:9282", "release:home:contabo:9282"]


# ── JSON + flat CSV output & offline replay from raw-schema ─────────────────


def test_pull_from_raw_schema_dir_and_write_outputs(tmp_path):
    ref = datetime(2025, 11, 26, 0, 0, 0, tzinfo=timezone.utc)
    payload = pull.pull_from_raw_schema_dir(RAW_SCHEMA_DIR, reference_utc=ref)
    json_path, csv_path = pull.write_pull_outputs(payload, out_dir=tmp_path, date_str="2026-11-26")

    assert json_path.exists()
    assert csv_path.exists()
    assert not json_path.with_suffix(".json.tmp").exists()
    assert not csv_path.with_suffix(".csv.tmp").exists()

    saved_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved_json["account"] == "@black_liquidity"
    assert saved_json["account_window"]["followers_start"] == 14210
    assert saved_json["account_window"]["followers_end"] == 14685
    assert saved_json["account_window"]["total_views"] == 43750
    assert saved_json["account_window"]["videos_in_30d_count"] == 2
    assert saved_json["account_window"]["videos_older_than_30d_count"] == 1

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert tuple(rows[0].keys()) == pull.CSV_COLUMNS
    assert rows[0]["video_id"] == "7440100000000000001"
    assert rows[0]["within_30d"] == "True"
    assert rows[0]["older_than_30d"] == "False"
    assert rows[0]["views"] == "28450"
    assert rows[0]["avg_watch_time_s"] == "24.6"
    assert rows[0]["watched_full_video_pct"] == "21.8"
    assert rows[0]["retention_points_count"] == "7"
    assert rows[0]["traffic_for_you_pct"] == "74.2"
    assert rows[0]["new_followers"] == "134"
    assert rows[2]["older_than_30d"] == "True"

    md_table = pull.format_30d_markdown_table(payload)
    assert "7440100000000000001" in md_table
    assert "28,450" in md_table
    assert "74.2%" in md_table
    assert "older (>30d)" in md_table
