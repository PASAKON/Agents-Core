"""Unit tests for tools/bl_studio_pull.py (task-f19ca94b).

Exercises the pure raw-JSON adapters against the saved live-schema samples in
tests/fixtures/bl_studio/ (synthetic values) (`aweme/v2/data/insight/`, `/mod/v1/getPenaltyDetails/`,
`/tiktok/v1/creator/item_list/`), multi-call `aweme/v2/data/insight/` merging per
page, 30-day window flagging, URL query-token & ID stripping, >= 3 s pacing
enforcement, /login (SIGNED_OUT exit 4) and captcha/verify (exit 3) handling,
home_lock acquire + release in finally, and JSON + flat CSV writing.

Run via:  pytest tests/test_bl_studio_pull.py
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools import bl_studio_pull as pull

RAW_SCHEMA_DIR = Path(__file__).resolve().parent / "fixtures" / "bl_studio"
REF_UTC = datetime(2026, 11, 26, 16, 0, 0, tzinfo=timezone.utc)


def _load_raw_sample(name: str) -> dict:
    return json.loads((RAW_SCHEMA_DIR / name).read_text(encoding="utf-8"))


# ── saved raw-schema sample validation ──────────────────────────────────────


def test_saved_raw_schema_samples_have_live_tag_and_strip_all_tokens_and_ids():
    sample_files = sorted(RAW_SCHEMA_DIR.glob("*.json"))
    assert len(sample_files) >= 4
    for path in sample_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data.get("_meta", {})
        endpoint_path = meta.get("endpoint_path", "")
        assert meta.get("schema_status") == "live"
        assert endpoint_path.startswith("https://www.tiktok.com/")
        assert "?" not in endpoint_path
        assert "#" not in endpoint_path
        assert "msToken" not in endpoint_path
        assert "verifyFp" not in endpoint_path
        assert data.get("extra", {}).get("logid", "") == ""
        assert data.get("log_pb", {}).get("impr_id", "") == ""


def test_extract_content_list_from_saved_raw_sample():
    rows = pull.extract_content_list_from_raw(_load_raw_sample("content_list.json"))
    assert len(rows) == 3

    first = rows[0]
    assert first["video_id"] == "7400000000000000001"
    assert first["post_time_utc"] == "2026-11-19T04:48:32Z"
    assert len(first["caption_80"]) <= 80
    assert first["caption_80"].startswith("ตัวอย่างคลิปทดสอบ1")
    assert first["duration_s"] == 58.0
    assert first["views"] == 1201
    assert first["likes"] == 24
    assert first["comments"] == 2
    assert first["shares"] == 4
    assert first["saves"] == 9


def test_extract_video_analytics_from_saved_live_insight_sample():
    detail = pull.extract_video_analytics_from_raw(_load_raw_sample("video_analytics.json"))
    assert detail["video_id"] == "7400000000000000001"
    assert detail["duration_s"] == 58.0
    assert detail["avg_watch_time_s"] == 24.6
    assert detail["watched_full_video_pct"] == 21.8
    assert detail["new_followers"] == 3
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
    assert detail["search_terms"] == [
        {"keyword": "ราคาทองดิ่ง", "value": 14},
        {"keyword": "ข่าวทองคำ", "value": 8},
    ]
    assert len(detail["vv_48h"]) == 4
    assert detail["vv_48h"][0] == {"timestamp": 0, "value": 42}
    assert detail["vv_48h"][-1] == {"timestamp": 172800, "value": 312}


def test_extract_penalty_from_saved_raw_sample():
    pen = pull.extract_penalty_from_raw(_load_raw_sample("penalty_details.json"))
    assert pen == {
        "type": 0,
        "source": 0,
        "trigger": 0,
    }
    assert pull.format_penalty_cell(pen) == "none"


def test_extract_account_overview_from_saved_raw_sample():
    acc = pull.extract_account_overview_from_raw(_load_raw_sample("account_overview.json"))
    assert acc == {
        "followers_start": 49500,
        "followers_end": 50000,
        "follower_num": 50000,
        "unique_viewer_num": 38920,
        "total_views": None,
    }


# ── multi-call aweme/v2/data/insight/ merging & classification ──────────────


def test_merge_all_four_insight_calls_of_one_page_before_adapting():
    """Verify the 4 live `aweme/v2/data/insight/` calls per page (LIVE-insight-keys-2026-11-26.txt)
    merge without later calls clobbering earlier populated fields."""
    # Call 1: video_info + video_vv_history_48_hours populated
    call_1 = {
        "status_code": 0,
        "video_info": {
            "aweme_id": "7400000000000000001",
            "create_time": 1763527712,
            "desc": "ตัวอย่างคลิปทดสอบ9",
            "statistics": {
                "play_count": 1201,
                "digg_count": 24,
                "comment_count": 2,
                "share_count": 4,
                "collect_count": 9,
            },
            "video": {"duration": 58000},
        },
        "video_vv_history_48_hours": [
            {"timestamp": 0, "value": 42},
            {"timestamp": 3600, "value": 118},
        ],
        "vv_history": [],
    }
    # Call 2: realtime watch time, finish rate, retention, traffic sources, new followers, search terms
    call_2 = {
        "status_code": 0,
        "item_search_terms": {"status": 0, "value": [{"keyword": "ทองคำ", "value": 9}]},
        "realtime_new_followers": {
            "is_after_7d": False,
            "is_data_delay": False,
            "value": {"status": 0, "value": 4},
        },
        "video_new_followers": {"status": 0, "value": 0},
        "video_finish_rate_realtime": {
            "is_after_7d": False,
            "is_data_delay": False,
            "value": {"status": 0, "value": 0.195},
        },
        "video_per_duration_realtime": {
            "is_after_7d": False,
            "is_data_delay": False,
            "value": {"status": 0, "value": 18.4},
        },
        "video_retention_rate_realtime": {
            "is_after_7d": False,
            "is_data_delay": False,
            "value": {
                "status": 0,
                "peak_value": 1.0,
                "list": [
                    {"timestamp": 0, "value": 1.0},
                    {"timestamp": 15, "value": 0.52},
                    {"timestamp": 58, "value": 0.195},
                ],
            },
        },
        "video_traffic_source_percent_realtime": {
            "is_after_7d": False,
            "is_data_delay": False,
            "value": {
                "status": 0,
                "value": [
                    {"key": "for_you", "value": 0.81},
                    {"key": "search", "value": 0.11},
                    {"key": "personal_profile", "value": 0.05},
                    {"key": "following", "value": 0.02},
                    {"key": "other", "value": 0.01},
                ],
            },
        },
        "video_vv_history_48_hours": [],
    }
    # Call 3: video_rewards_data only, empty video_vv_history_48_hours
    call_3 = {
        "status_code": 0,
        "video_rewards_data": {"status": 0, "total": {"status": 2}},
        "video_vv_history_48_hours": [],
    }
    # Call 4: follower_num and unique_viewer_num + video_info, no realtime video fields
    call_4 = {
        "status_code": 0,
        "follower_num": {"status": 0, "value": 50000},
        "unique_viewer_num": {"status": 0, "value": 777},
        "video_info": {"aweme_id": "7400000000000000001"},
        "video_vv_history_48_hours": [],
    }

    url = "https://www.tiktok.com/aweme/v2/data/insight/"
    for c in (call_1, call_2, call_3, call_4):
        assert pull.classify_xhr_payload(url, c) == "video_analytics"

    merged = pull.merge_insight_blobs([call_1, call_2, call_3, call_4])
    parsed = pull.extract_video_analytics_from_raw(merged)

    assert parsed["video_id"] == "7400000000000000001"
    assert parsed["duration_s"] == 58.0
    assert parsed["watched_full_video_pct"] == 19.5
    assert parsed["avg_watch_time_s"] == 18.4
    # video_new_followers was 0 while realtime_new_followers was 4 -> picks 4
    assert parsed["new_followers"] == 4
    assert parsed["retention_curve"] == [
        {"t_s": 0, "pct": 100.0},
        {"t_s": 15, "pct": 52.0},
        {"t_s": 58, "pct": 19.5},
    ]
    assert parsed["traffic_sources"] == {
        "for_you": 81.0,
        "search": 11.0,
        "profile": 5.0,
        "following": 2.0,
        "other": 1.0,
    }
    assert parsed["search_terms"] == [{"keyword": "ทองคำ", "value": 9}]
    assert parsed["vv_48h"] == [
        {"timestamp": 0, "value": 42},
        {"timestamp": 3600, "value": 118},
    ]

    acc = pull.extract_account_overview_from_raw(merged)
    assert acc["follower_num"] == 50000
    assert acc["followers_end"] == 50000
    assert acc["unique_viewer_num"] == 777


def test_classify_and_extract_penalty_details_with_nonzero_penalty():
    url = "https://www.tiktok.com/mod/v1/getPenaltyDetails/"
    body = {
        "status_code": 0,
        "appeal_status": 1,
        "feedback_status": 0,
        "improve_views": True,
        "top_penalty_details": {
            "is_adult_group": False,
            "penalty_type": "unoriginal_content",
            "penalty_source": "system_audit",
            "penalty_trigger": "duplicate_frame_match",
        },
    }
    assert pull.classify_xhr_payload(url, body) == "penalty_details"
    pen = pull.extract_penalty_from_raw(body)
    assert pen == {
        "type": "unoriginal_content",
        "source": "system_audit",
        "trigger": "duplicate_frame_match",
    }
    assert pull.format_penalty_cell(pen) == "unoriginal_content/system_audit/duplicate_frame_match"


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
            "follower_num_history": [
                {"date": "2026-10-28", "value": 10100},
                {"date": "2026-11-10", "value": 10350},
                {"date": "2026-11-26", "value": 10890},
            ],
            "unique_viewer_num": {"status": 0, "value": 54200},
            "video_views": 95400,
        }
    }
    acc = pull.extract_account_overview_from_raw(raw)
    assert acc == {
        "followers_start": 10100,
        "followers_end": 10890,
        "follower_num": 10890,
        "unique_viewer_num": 54200,
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
    with pytest.raises(pull.UnrecognizedResponseShape):
        pull.extract_penalty_from_raw(bad)


# ── 30-day window flagging, merging & unexposed fields ──────────────────────


def test_merge_and_flag_30d_window_flags_older_videos():
    content_rows = pull.extract_content_list_from_raw(_load_raw_sample("content_list.json"))
    va = pull.extract_video_analytics_from_raw(_load_raw_sample("video_analytics.json"))
    pen = pull.extract_penalty_from_raw(_load_raw_sample("penalty_details.json"))
    merged = pull.merge_video_records(
        content_rows,
        {va["video_id"]: va},
        reference_utc=REF_UTC,
        penalties_by_video_id={va["video_id"]: pen},
    )

    assert len(merged) == 3
    assert merged[0]["within_30d"] is True
    assert merged[0]["older_than_30d"] is False
    assert merged[0]["avg_watch_time_s"] == 24.6
    assert merged[0]["traffic_sources"]["for_you"] == 74.2
    assert len(merged[0]["search_terms"]) == 2
    assert len(merged[0]["vv_48h"]) == 4
    assert merged[0]["penalty"] == {"type": 0, "source": 0, "trigger": 0}

    assert merged[1]["within_30d"] is True
    assert merged[1]["older_than_30d"] is False
    assert merged[1]["avg_watch_time_s"] is None
    assert merged[1]["penalty"] == {"type": None, "source": None, "trigger": None}

    # Video 3 was posted 2026-10-13 (>30 days before 2026-11-26) -> flagged older_than_30d
    assert merged[2]["video_id"] == "7400000000000000003"
    assert merged[2]["within_30d"] is False
    assert merged[2]["older_than_30d"] is True


def test_detect_unexposed_fields_identifies_missing_studio_metrics():
    content_rows = pull.extract_content_list_from_raw(_load_raw_sample("content_list.json"))
    merged = pull.merge_video_records(content_rows, {}, reference_utc=REF_UTC)
    payload = pull.build_pull_payload(merged, account_overview=None, pulled_at_utc=REF_UTC)

    assert set(payload["unexposed_fields"]["per_video"]) == {
        "avg_watch_time_s",
        "watched_full_video_pct",
        "retention_curve",
        "traffic_sources",
        "new_followers",
        "search_terms",
        "vv_48h",
        "penalty",
    }
    assert set(payload["unexposed_fields"]["account_window"]) == {
        "followers_start",
        "followers_end",
        "follower_num",
        "unique_viewer_num",
    }
    assert payload["account_window"]["total_views"] == 1201 + 1502


# ── URL sanitization, pacing, guards & lock lifecycle ───────────────────────


def test_sanitize_url_and_raw_sample_body_strip_tokens_and_ids():
    dirty = (
        "https://www.tiktok.com/aweme/v2/data/insight/"
        "?msToken=abc123SECRET&verifyFp=verify_999&_signature=_02B4Z6wo00f01#section"
    )
    clean = pull.sanitize_url(dirty)
    assert clean == "https://www.tiktok.com/aweme/v2/data/insight/"
    assert "msToken" not in clean
    assert "SECRET" not in clean

    raw_blob = {
        "extra": {"logid": "20261126155900ABC", "now": 1764169140000},
        "log_pb": {"impr_id": "20261126155900ABC"},
        "video_info": {
            "aweme_id": "7400000000000000001",
            "author": {"uid": "123456", "sec_uid": "MS4wLjABAAAAsecret", "unique_id": "black_liquidity"},
            "video": {"play_addr": {"url_list": ["https://v16.tiktokcdn.com/video/tos/?a=1&msToken=secret"]}},
        },
        "video_per_duration_realtime": {"value": {"status": 0, "value": 24.6}},
    }
    cleaned = pull.sanitize_raw_sample_body(raw_blob)
    assert cleaned["extra"]["logid"] == ""
    assert cleaned["extra"]["now"] == 1764169140000
    assert cleaned["log_pb"]["impr_id"] == ""
    assert cleaned["video_info"]["author"]["uid"] == ""
    assert cleaned["video_info"]["author"]["sec_uid"] == ""
    assert cleaned["video_info"]["video"]["play_addr"]["url_list"] == ["https://v16.tiktokcdn.com/video/tos/"]
    assert cleaned["video_per_duration_realtime"]["value"]["value"] == 24.6


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

    now[0] = 101.2
    t2 = pull.enforce_pacing(t1, 2.0, sleep_fn=fake_sleep, clock_fn=fake_clock)
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


# ── live orchestration with multi-blob page merging & 30d-only filter ───────


def test_run_live_pull_merges_multiple_insight_calls_and_queries_30d_videos_only(tmp_path):
    navigated_urls: list[str] = []

    class FakeBrowser:
        def attach(self):
            pass

        def close(self):
            pass

        def navigate_and_collect(self, target_url: str):
            navigated_urls.append(target_url)
            if target_url == pull.STUDIO_CONTENT_URL:
                return [
                    (
                        "https://www.tiktok.com/tiktok/v1/creator/item_list/",
                        _load_raw_sample("content_list.json"),
                    )
                ]
            if target_url.endswith("/7400000000000000001"):
                # Return split insight calls + penalty details on one page load
                va_full = _load_raw_sample("video_analytics.json")
                blob_a = {
                    "status_code": 0,
                    "video_info": va_full["video_info"],
                    "video_vv_history_48_hours": va_full["video_vv_history_48_hours"],
                }
                blob_b = {
                    "status_code": 0,
                    "video_finish_rate_realtime": va_full["video_finish_rate_realtime"],
                    "video_per_duration_realtime": va_full["video_per_duration_realtime"],
                    "video_retention_rate_realtime": va_full["video_retention_rate_realtime"],
                    "video_traffic_source_percent_realtime": va_full["video_traffic_source_percent_realtime"],
                    "video_new_followers": va_full["video_new_followers"],
                    "item_search_terms": va_full["item_search_terms"],
                    "video_vv_history_48_hours": [],
                }
                blob_c = {
                    "status_code": 0,
                    "follower_num": va_full["follower_num"],
                    "unique_viewer_num": va_full["unique_viewer_num"],
                    "video_vv_history_48_hours": [],
                }
                return [
                    ("https://www.tiktok.com/aweme/v2/data/insight/", blob_a),
                    ("https://www.tiktok.com/aweme/v2/data/insight/", blob_b),
                    ("https://www.tiktok.com/mod/v1/getPenaltyDetails/", _load_raw_sample("penalty_details.json")),
                    ("https://www.tiktok.com/aweme/v2/data/insight/", blob_c),
                ]
            return []

    out_dir = tmp_path / "out"
    raw_dir = tmp_path / "raw-schema"
    payload, json_path, csv_path = pull.run_live_pull(
        out_dir=out_dir,
        raw_schema_dir=raw_dir,
        browser_factory=FakeBrowser,
        reference_utc=REF_UTC,
    )

    # Only the 2 within-30d videos should have their per-video analytics URLs loaded (older 7400000000000000003 skipped)
    assert navigated_urls == [
        "https://www.tiktok.com/tiktokstudio/content",
        "https://www.tiktok.com/tiktokstudio/analytics/7400000000000000001",
        "https://www.tiktok.com/tiktokstudio/analytics/7400000000000000002",
    ]
    v0 = payload["videos"][0]
    assert v0["video_id"] == "7400000000000000001"
    assert v0["avg_watch_time_s"] == 24.6
    assert v0["watched_full_video_pct"] == 21.8
    assert len(v0["vv_48h"]) == 4
    assert len(v0["search_terms"]) == 2
    assert v0["penalty"] == {"type": 0, "source": 0, "trigger": 0}
    assert payload["account_window"]["follower_num"] == 50000
    assert payload["account_window"]["unique_viewer_num"] == 777

    for slug in ("content_list", "video_analytics", "penalty_details", "account_overview"):
        saved_sample = json.loads((raw_dir / f"{slug}.json").read_text(encoding="utf-8"))
        assert saved_sample["_meta"]["schema_status"] == "live"


# ── JSON + flat CSV output & offline replay from raw-schema ─────────────────


def test_pull_from_raw_schema_dir_and_write_outputs(tmp_path):
    payload = pull.pull_from_raw_schema_dir(RAW_SCHEMA_DIR, reference_utc=REF_UTC)
    json_path, csv_path = pull.write_pull_outputs(payload, out_dir=tmp_path, date_str="2026-11-26")

    assert json_path.exists()
    assert csv_path.exists()
    assert not json_path.with_suffix(".json.tmp").exists()
    assert not csv_path.with_suffix(".csv.tmp").exists()

    saved_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved_json["account"] == "@black_liquidity"
    assert saved_json["account_window"]["followers_start"] == 49500
    assert saved_json["account_window"]["followers_end"] == 50000
    assert saved_json["account_window"]["follower_num"] == 50000
    assert saved_json["account_window"]["unique_viewer_num"] == 38920
    assert saved_json["account_window"]["total_views"] == 1201 + 1502
    assert saved_json["account_window"]["videos_in_30d_count"] == 2
    assert saved_json["account_window"]["videos_older_than_30d_count"] == 1

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert tuple(rows[0].keys()) == pull.CSV_COLUMNS
    assert rows[0]["video_id"] == "7400000000000000001"
    assert rows[0]["within_30d"] == "True"
    assert rows[0]["older_than_30d"] == "False"
    assert rows[0]["views"] == "1201"
    assert rows[0]["avg_watch_time_s"] == "24.6"
    assert rows[0]["watched_full_video_pct"] == "21.8"
    assert rows[0]["retention_points_count"] == "7"
    assert rows[0]["traffic_for_you_pct"] == "74.2"
    assert rows[0]["new_followers"] == "3"
    assert rows[0]["search_terms_count"] == "2"
    assert rows[0]["vv_48h_points_count"] == "4"
    assert rows[0]["penalty_type"] == "0"
    assert rows[2]["older_than_30d"] == "True"

    md_table = pull.format_30d_markdown_table(payload)
    assert "7400000000000000001" in md_table
    assert "1,201" in md_table
    assert "74.2%" in md_table
    assert "Penalty" in md_table
    assert "none" in md_table
    assert "older (>30d)" in md_table


def test_retention_curve_ms_axis_is_converted_to_seconds():
    import tools.bl_studio_pull as m
    src = {"video_retention_rate_realtime": {"value": {"list": [
        {"t_s": 0, "pct": 100.0}, {"t_s": 1000, "pct": 56.0}, {"t_s": 3000, "pct": 31.0}]}}}
    pts = m._extract_retention_curve(src)
    assert [p["t_s"] for p in pts] == [0, 1, 3]
    assert pts[2]["pct"] == 31.0
