#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BL TikTok Studio Analytics Pull — zero-model, read-only XHR collector (task-f19ca94b).

Reads TikTok Studio analytics for @black_liquidity through Browser Home `tiktok-bl`
(CDP http://127.0.0.1:9282 on Contabo) and writes:
  - state/cgo/bl/pull-<YYYY-MM-DD>.json
  - state/cgo/bl/pull-<YYYY-MM-DD>.csv
  - state/cgo/bl/raw-schema/<endpoint>.json (1 sample per endpoint, query tokens stripped)

Rules & safety invariants:
  1. READ ONLY on the account: no post, edit, reply, like, follow, or UI clicking.
  2. Lock first: acquires `home:contabo:9282` via `tools/home_lock.py` with
     `--purpose "CGO studio pull"` and always releases in a `finally:` block.
  3. Captures JSON XHR responses Studio itself loads via CDP `Network.responseReceived`
     + `Network.getResponseBody` without clicking UI controls.
  4. Never prints or persists URLs with query tokens (`sanitize_url` strips query
     and fragment components and redacts token patterns).
  5. Enforces pacing >= 3.0 s between page loads.
  6. Stops immediately at any captcha or verification marker and exits 3 (never solves one).
  7. If the browser lands on `/login`, prints `SIGNED_OUT`, exits 4, and does nothing else.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import home_lock  # noqa: E402

DEFAULT_CDP_URL = "http://127.0.0.1:9282"
DEFAULT_LOCK_KEY = "home:contabo:9282"
DEFAULT_LOCK_PURPOSE = "CGO studio pull"
DEFAULT_OUT_DIR = Path("state/cgo/bl")
DEFAULT_RAW_SCHEMA_DIR = Path("state/cgo/bl/raw-schema")

STUDIO_CONTENT_URL = "https://www.tiktok.com/tiktokstudio/content"
STUDIO_ANALYTICS_URL = "https://www.tiktok.com/tiktokstudio/analytics"
STUDIO_VIDEO_ANALYTICS_URL_TMPL = "https://www.tiktok.com/tiktokstudio/analytics/{video_id}"

MIN_PACING_S = 3.0
DEFAULT_PACING_S = 3.5
WINDOW_DAYS = 30

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_LOCK_ERROR = 2
EXIT_CAPTCHA = 3
EXIT_SIGNED_OUT = 4

_VERIFICATION_MARKERS = (
    "verify to continue",
    "captcha",
    "ยืนยันตัวตน",
    "security check",
    "slide to verify",
    "เลื่อนเพื่อยืนยัน",
    "unusual activity",
    "confirm it's you",
    "confirm you're not a robot",
    "drag the slider",
    "fit the puzzle",
    "เลือกภาพเพื่อยืนยัน",
)

_CAPTCHA_DOM_SELECTORS = (
    "#captcha_container",
    ".captcha-verify-container",
    ".secsdk-captcha-drag-icon",
    "[id*='captcha-verify']",
    "iframe[src*='captcha']",
)

_TOKEN_PATH_RE = re.compile(
    r"(msToken|verifyFp|_signature|X-Bogus|odin_tt|sessionid|tt_webid)=[^/&\s]+",
    re.IGNORECASE,
)

CSV_COLUMNS = (
    "video_id",
    "post_time_utc",
    "within_30d",
    "older_than_30d",
    "caption_80",
    "duration_s",
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "avg_watch_time_s",
    "watched_full_video_pct",
    "retention_points_count",
    "traffic_for_you_pct",
    "traffic_search_pct",
    "traffic_profile_pct",
    "traffic_following_pct",
    "traffic_other_pct",
    "new_followers",
)

PER_VIDEO_REQUIRED_FIELDS = (
    "video_id",
    "post_time_utc",
    "caption_80",
    "duration_s",
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "avg_watch_time_s",
    "watched_full_video_pct",
    "retention_curve",
    "traffic_sources",
    "new_followers",
)

ACCOUNT_REQUIRED_FIELDS = (
    "followers_start",
    "followers_end",
    "total_views",
)


# ── exceptions ───────────────────────────────────────────────────────────────


class VerificationWall(RuntimeError):
    """Captcha or verification wall encountered. Exit 3 immediately; never solve."""


class SignedOut(RuntimeError):
    """Browser Home landed on /login or is not authenticated. Exit 4 immediately."""


class UnrecognizedResponseShape(RuntimeError):
    """Raw JSON response did not match any known TikTok Studio field shape."""


# ── URL & security helpers ───────────────────────────────────────────────────


def sanitize_url(url: str) -> str:
    """Strip query string and fragment completely so query tokens are never printed or saved."""
    if not url:
        return ""
    try:
        parts = urlsplit(str(url).strip())
    except ValueError:
        return "<invalid-url>"
    base = f"{parts.scheme}://{parts.netloc}{parts.path}" if parts.scheme and parts.netloc else parts.path
    return _TOKEN_PATH_RE.sub(r"\1=<redacted>", base)


def is_login_url(url: str) -> bool:
    """Return True if the URL path indicates a TikTok login redirect."""
    if not url:
        return False
    try:
        path = (urlsplit(url).path or "").lower()
    except ValueError:
        return "/login" in url.lower()
    return path == "/login" or path.startswith("/login/") or "/login" in path.split("/")


def has_verification_marker(text: str) -> bool:
    """Return True if page text contains any captcha or verification wall marker."""
    body = (text or "").lower()
    return any(marker.lower() in body for marker in _VERIFICATION_MARKERS)


def enforce_pacing(last_load_monotonic: float | None, pacing_s: float,
                   sleep_fn: Callable[[float], None] = time.sleep,
                   clock_fn: Callable[[], float] = time.monotonic) -> float:
    """Ensure at least max(MIN_PACING_S, pacing_s) seconds elapse between page loads."""
    effective_pacing = max(MIN_PACING_S, float(pacing_s))
    now = clock_fn()
    if last_load_monotonic is not None:
        elapsed = now - last_load_monotonic
        if elapsed < effective_pacing:
            sleep_fn(effective_pacing - elapsed)
            now = clock_fn()
    return now


# ── pure extraction helpers ──────────────────────────────────────────────────


def _first_present(d: dict, keys: tuple[str, ...]) -> Any:
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _to_int(val: Any) -> int | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        if isinstance(val, str):
            cleaned = val.strip().replace(",", "")
            if not cleaned:
                return None
            return int(float(cleaned))
        return int(val)
    except (ValueError, TypeError):
        return None


def _to_float(val: Any) -> float | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        if isinstance(val, str):
            cleaned = val.strip().replace(",", "").rstrip("%")
            if not cleaned:
                return None
            return float(cleaned)
        return float(val)
    except (ValueError, TypeError):
        return None


def _normalize_rate_to_pct(val: Any, *, key_hint: str = "") -> float | None:
    """Normalize a percentage or 0..1 ratio to a 0..100 percentage rounded to 2 decimals.

    TikTok Studio endpoints return rates either as a 0..1 ratio (e.g. `full_video_watched_rate: 0.218`)
    or as a 0..100 percentage (`watched_full_video_pct: 21.8`). If the field name indicates a rate/ratio
    and 0 < abs(num) <= 1.0, scale by 100.
    """
    num = _to_float(val)
    if num is None:
        return None
    hint = key_hint.lower()
    is_ratio_key = ("rate" in hint or "ratio" in hint) and "pct" not in hint and "percent" not in hint
    if is_ratio_key and 0.0 <= num <= 1.0:
        num = num * 100.0
    return round(num, 2)


def _parse_post_time_utc(raw_ts: Any) -> str | None:
    """Convert a UNIX epoch (seconds or ms) or ISO timestamp to UTC ISO-8601 `YYYY-MM-DDTHH:MM:SSZ`."""
    if raw_ts is None or isinstance(raw_ts, bool):
        return None
    if isinstance(raw_ts, (int, float)) or (isinstance(raw_ts, str) and raw_ts.strip().isdigit()):
        ts = float(raw_ts)
        if ts <= 0:
            return None
        if ts > 1e12:  # milliseconds epoch
            ts = ts / 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(raw_ts, str):
        text = raw_ts.strip()
        if not text:
            return None
        try:
            if text.endswith("Z"):
                dt = datetime.fromisoformat(text[:-1]).replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromisoformat(text)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return None
    return None


def _normalize_caption_80(raw_caption: Any) -> str:
    if raw_caption is None:
        return ""
    collapsed = re.sub(r"\s+", " ", str(raw_caption)).strip()
    return collapsed[:80]


def _parse_duration_s(item: dict) -> float | None:
    video_obj = item.get("video") if isinstance(item.get("video"), dict) else {}
    video_meta = item.get("video_meta") if isinstance(item.get("video_meta"), dict) else {}

    ms_val = _first_present(item, ("duration_ms", "video_duration_ms"))
    if ms_val is None:
        ms_val = _first_present(video_obj, ("duration_ms", "durationMs"))
    if ms_val is None:
        ms_val = _first_present(video_meta, ("duration_ms", "durationMs"))
    if ms_val is not None:
        f_ms = _to_float(ms_val)
        return round(f_ms / 1000.0, 2) if f_ms is not None else None

    for src in (item, video_obj, video_meta):
        sec_val = _first_present(src, ("duration_s", "duration", "video_duration", "videoDuration"))
        if sec_val is not None:
            f_sec = _to_float(sec_val)
            if f_sec is None:
                continue
            # TikTok sometimes puts milliseconds inside `video.duration` when > 36000 for short clips
            if f_sec > 36000:
                return round(f_sec / 1000.0, 2)
            return round(f_sec, 2)
    return None


def _extract_retention_curve(src: dict) -> list[dict]:
    """Extract retention curve points as `[{'t_s': float|int, 'pct': float}, ...]`."""
    raw_curve = _first_present(
        src,
        (
            "retention_curve",
            "video_retention",
            "retention_list",
            "audience_retention",
            "retention_points",
            "retention",
        ),
    )
    if isinstance(raw_curve, dict):
        raw_curve = _first_present(raw_curve, ("points", "list", "items", "data", "curve"))
    if not isinstance(raw_curve, list):
        return []

    points: list[dict] = []
    for idx, pt in enumerate(raw_curve):
        if isinstance(pt, dict):
            t_raw = _first_present(pt, ("t_s", "second", "time", "timestamp", "t", "x", "offset_s"))
            t_s = _to_float(t_raw)
            if t_s is None:
                t_s = float(idx)
            elif t_s.is_integer():
                t_s = int(t_s)

            pct = None
            for k in ("pct", "percent", "percentage", "rate", "ratio", "value", "y", "retention"):
                if k in pt and pt[k] is not None:
                    pct = _normalize_rate_to_pct(pt[k], key_hint=k)
                    break
            if pct is not None:
                points.append({"t_s": t_s, "pct": pct})
        elif isinstance(pt, (int, float)):
            points.append({"t_s": idx, "pct": round(float(pt), 2)})
    return points


_TRAFFIC_SOURCE_ALIASES = {
    "for_you": "for_you",
    "foryou": "for_you",
    "for you": "for_you",
    "fyp": "for_you",
    "for_you_page": "for_you",
    "recommend": "for_you",
    "search": "search",
    "tiktok_search": "search",
    "profile": "profile",
    "personal_profile": "profile",
    "creator_profile": "profile",
    "other_profile": "profile",
    "following": "following",
    "follow": "following",
    "following_feed": "following",
    "other": "other",
    "others": "other",
    "sound": "other",
    "music": "other",
    "hashtag": "other",
    "share": "other",
    "external": "other",
}


def _empty_traffic_sources() -> dict[str, float | None]:
    return {
        "for_you": None,
        "search": None,
        "profile": None,
        "following": None,
        "other": None,
    }


def _extract_traffic_sources(src: dict) -> dict[str, float | None]:
    """Extract traffic source split into `{for_you, search, profile, following, other}` percentages."""
    raw_ts = _first_present(
        src,
        (
            "traffic_sources",
            "traffic_source",
            "impression_sources",
            "video_traffic_source",
            "traffic_source_list",
        ),
    )
    out = _empty_traffic_sources()
    if raw_ts is None:
        return out

    if isinstance(raw_ts, dict):
        # Check if wrapped in a list container
        nested_list = _first_present(raw_ts, ("list", "items", "sources", "data"))
        if isinstance(nested_list, list):
            raw_ts = nested_list
        else:
            for k, v in raw_ts.items():
                norm_key = _TRAFFIC_SOURCE_ALIASES.get(str(k).strip().lower().replace("-", "_"))
                if not norm_key:
                    continue
                pct = _normalize_rate_to_pct(v, key_hint=str(k))
                if pct is None:
                    continue
                out[norm_key] = round((out[norm_key] or 0.0) + pct, 2)
            return out

    if isinstance(raw_ts, list):
        for entry in raw_ts:
            if not isinstance(entry, dict):
                continue
            name = _first_present(entry, ("source", "name", "type", "key", "label", "traffic_source"))
            if name is None:
                continue
            norm_key = _TRAFFIC_SOURCE_ALIASES.get(str(name).strip().lower().replace("-", "_"), "other")
            pct = None
            for k in ("pct", "percent", "percentage", "rate", "ratio", "value", "share"):
                if k in entry and entry[k] is not None:
                    pct = _normalize_rate_to_pct(entry[k], key_hint=k)
                    break
            if pct is not None:
                out[norm_key] = round((out[norm_key] or 0.0) + pct, 2)
    return out


def _extract_single_video_analytics_fields(src: dict) -> dict[str, Any]:
    """Extract deep analytics fields from a video item or per-video analytics dict."""
    analytics_sub = src.get("analytics") if isinstance(src.get("analytics"), dict) else {}
    metrics_sub = src.get("metrics") if isinstance(src.get("metrics"), dict) else {}
    stats_sub = src.get("stats") if isinstance(src.get("stats"), dict) else {}
    item_stat = src.get("item_stat") if isinstance(src.get("item_stat"), dict) else {}

    def lookup(keys: tuple[str, ...]) -> tuple[Any, str]:
        for container in (src, analytics_sub, metrics_sub, stats_sub, item_stat):
            if isinstance(container, dict):
                for k in keys:
                    if k in container and container[k] is not None:
                        return container[k], k
        return None, ""

    avg_watch_raw, _ = lookup(
        (
            "avg_watch_time_s",
            "avg_watch_time",
            "average_watch_time",
            "avg_play_duration",
            "play_duration_avg",
            "watch_time_avg",
        )
    )
    avg_watch_time_s = _to_float(avg_watch_raw)
    if avg_watch_time_s is not None:
        avg_watch_time_s = round(avg_watch_time_s, 2)

    full_raw, full_key = lookup(
        (
            "watched_full_video_pct",
            "watched_full_pct",
            "full_video_watched_rate",
            "completion_rate",
            "finish_rate",
            "full_watch_rate",
        )
    )
    watched_full_video_pct = _normalize_rate_to_pct(full_raw, key_hint=full_key)

    new_followers_raw, _ = lookup(
        (
            "new_followers",
            "new_follower_count",
            "followers_gained",
            "net_new_followers",
            "video_new_followers",
        )
    )
    new_followers = _to_int(new_followers_raw)

    retention_curve: list[dict] = []
    for container in (src, analytics_sub, metrics_sub):
        if isinstance(container, dict):
            retention_curve = _extract_retention_curve(container)
            if retention_curve:
                break

    traffic_sources = _empty_traffic_sources()
    for container in (src, analytics_sub, metrics_sub):
        if isinstance(container, dict):
            candidate = _extract_traffic_sources(container)
            if any(v is not None for v in candidate.values()):
                traffic_sources = candidate
                break

    return {
        "avg_watch_time_s": avg_watch_time_s,
        "watched_full_video_pct": watched_full_video_pct,
        "retention_curve": retention_curve,
        "traffic_sources": traffic_sources,
        "new_followers": new_followers,
    }


# ── public pure adapters (unit-tested against state/cgo/bl/raw-schema/) ──────


def extract_content_list_from_raw(raw: dict | list) -> list[dict]:
    """Parse a TikTok Studio content list response into normalized video rows."""
    items = None
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        for key in ("items", "item_list", "aweme_list", "videos", "list", "content_list"):
            v = raw.get(key)
            if isinstance(v, list):
                items = v
                break
        if items is None and isinstance(raw.get("data"), dict):
            data_obj = raw["data"]
            for key in ("items", "item_list", "aweme_list", "videos", "list"):
                v = data_obj.get(key)
                if isinstance(v, list):
                    items = v
                    break
        elif items is None and isinstance(raw.get("data"), list):
            items = raw["data"]

    if items is None:
        raise UnrecognizedResponseShape(
            f"no video list found under known container keys; top-level={list(raw)[:20] if isinstance(raw, dict) else type(raw)!r}"
        )

    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            raise UnrecognizedResponseShape(f"expected dict item in content list, got {type(item)!r}")
        vid = _first_present(item, ("video_id", "item_id", "aweme_id", "id"))
        if vid is None:
            raise UnrecognizedResponseShape(f"no video id in item keys={list(item)[:20]}")

        stats_src = (
            item.get("stats")
            if isinstance(item.get("stats"), dict)
            else (item.get("item_stat") if isinstance(item.get("item_stat"), dict) else item)
        )

        def pick_metric(candidates: tuple[str, ...]) -> int | None:
            v = _first_present(stats_src, candidates)
            if v is None:
                v = _first_present(item, candidates)
            return _to_int(v)

        post_time_utc = _parse_post_time_utc(
            _first_present(item, ("create_time", "createTime", "post_time", "publish_time", "posted_at"))
        )
        caption_raw = _first_present(item, ("desc", "title", "caption", "description", "text"))
        caption_80 = _normalize_caption_80(caption_raw)
        duration_s = _parse_duration_s(item)

        deep = _extract_single_video_analytics_fields(item)

        out.append(
            {
                "video_id": str(vid),
                "post_time_utc": post_time_utc,
                "caption_80": caption_80,
                "duration_s": duration_s,
                "views": pick_metric(("views", "view_count", "play_count", "playCount", "video_views")),
                "likes": pick_metric(("likes", "like_count", "digg_count", "diggCount")),
                "comments": pick_metric(("comments", "comment_count", "commentCount")),
                "shares": pick_metric(("shares", "share_count", "shareCount")),
                "saves": pick_metric(
                    ("saves", "save_count", "collect_count", "collectCount", "favorite_count", "bookmark_count")
                ),
                **deep,
            }
        )
    return out


def extract_video_analytics_from_raw(raw: dict, default_video_id: str | None = None) -> dict:
    """Parse a per-video TikTok Studio analytics response into normalized analytics fields."""
    if not isinstance(raw, dict):
        raise UnrecognizedResponseShape(f"expected dict for video analytics, got {type(raw)!r}")

    container = None
    for key in ("video_analytics", "analytics", "insight", "video_insight", "item_analytics"):
        if isinstance(raw.get(key), dict):
            container = raw[key]
            break
    if container is None and isinstance(raw.get("data"), dict):
        data_obj = raw["data"]
        container = (
            data_obj.get("video_analytics")
            if isinstance(data_obj.get("video_analytics"), dict)
            else data_obj
        )
    if container is None:
        container = raw

    vid = _first_present(container, ("video_id", "item_id", "aweme_id", "id")) or _first_present(
        raw, ("video_id", "item_id", "aweme_id", "id")
    ) or default_video_id

    deep = _extract_single_video_analytics_fields(container)
    has_any_signal = (
        vid is not None
        or deep["avg_watch_time_s"] is not None
        or deep["watched_full_video_pct"] is not None
        or bool(deep["retention_curve"])
        or any(v is not None for v in deep["traffic_sources"].values())
        or deep["new_followers"] is not None
    )
    if not has_any_signal:
        raise UnrecognizedResponseShape(
            f"no recognizable video analytics fields in top-level keys={list(raw)[:20]}"
        )

    duration_s = _parse_duration_s(container)
    return {
        "video_id": str(vid) if vid is not None else None,
        "duration_s": duration_s,
        **deep,
    }


def extract_account_overview_from_raw(raw: dict) -> dict:
    """Parse an account-level TikTok Studio analytics overview response for the 30d window."""
    if not isinstance(raw, dict):
        raise UnrecognizedResponseShape(f"expected dict for account overview, got {type(raw)!r}")

    container = None
    for key in ("account_overview", "overview", "account_analytics", "creator_overview", "data"):
        if isinstance(raw.get(key), dict):
            container = raw[key]
            break
    if container is None:
        container = raw

    followers_start = _to_int(
        _first_present(container, ("followers_start", "follower_count_start", "start_followers", "followers_begin"))
    )
    followers_end = _to_int(
        _first_present(
            container,
            ("followers_end", "follower_count_end", "end_followers", "follower_count", "current_followers"),
        )
    )

    series = _first_present(container, ("follower_history", "followers_series", "follower_trend", "followers_daily"))
    if isinstance(series, list) and series:
        vals: list[int] = []
        for entry in series:
            if isinstance(entry, dict):
                v = _to_int(_first_present(entry, ("followers", "count", "value", "follower_count")))
                if v is not None:
                    vals.append(v)
            else:
                v = _to_int(entry)
                if v is not None:
                    vals.append(v)
        if vals:
            if followers_start is None:
                followers_start = vals[0]
            if followers_end is None:
                followers_end = vals[-1]

    total_views = _to_int(
        _first_present(container, ("total_views", "video_views", "views_total", "play_count_total", "views"))
    )

    if followers_start is None and followers_end is None and total_views is None:
        raise UnrecognizedResponseShape(
            f"no recognizable account overview fields in top-level keys={list(raw)[:20]}"
        )

    return {
        "followers_start": followers_start,
        "followers_end": followers_end,
        "total_views": total_views,
    }


def flag_30d_window(row: dict, reference_utc: datetime) -> dict:
    """Attach `within_30d` and `older_than_30d` flags relative to `reference_utc` (30-day window)."""
    ref = reference_utc.astimezone(timezone.utc) if reference_utc.tzinfo else reference_utc.replace(tzinfo=timezone.utc)
    cutoff = ref - timedelta(days=WINDOW_DAYS)
    post_time_str = row.get("post_time_utc")
    older_than_30d = False
    within_30d = True
    if post_time_str:
        try:
            dt = datetime.fromisoformat(post_time_str.replace("Z", "+00:00"))
            older_than_30d = dt < cutoff
            within_30d = not older_than_30d
        except ValueError:
            older_than_30d = False
            within_30d = False
    else:
        within_30d = False
    return {
        **row,
        "within_30d": within_30d,
        "older_than_30d": older_than_30d,
    }


def merge_video_records(
    content_rows: list[dict],
    analytics_by_video_id: dict[str, dict],
    reference_utc: datetime | None = None,
) -> list[dict]:
    """Merge per-video analytics detail into the content list rows and flag the 30-day window."""
    ref = reference_utc or datetime.now(timezone.utc)
    merged: list[dict] = []
    for base in content_rows:
        vid = str(base["video_id"])
        detail = analytics_by_video_id.get(vid) or {}
        row = dict(base)

        if row.get("duration_s") is None and detail.get("duration_s") is not None:
            row["duration_s"] = detail["duration_s"]

        for field in ("avg_watch_time_s", "watched_full_video_pct", "new_followers"):
            if detail.get(field) is not None:
                row[field] = detail[field]

        if detail.get("retention_curve"):
            row["retention_curve"] = detail["retention_curve"]
        elif "retention_curve" not in row or row["retention_curve"] is None:
            row["retention_curve"] = []

        detail_ts = detail.get("traffic_sources") or {}
        base_ts = row.get("traffic_sources") or _empty_traffic_sources()
        if any(v is not None for v in detail_ts.values()):
            row["traffic_sources"] = {**_empty_traffic_sources(), **detail_ts}
        else:
            row["traffic_sources"] = {**_empty_traffic_sources(), **base_ts}

        merged.append(flag_30d_window(row, ref))
    return merged


def detect_unexposed_fields(video_rows: list[dict], account_window: dict) -> dict[str, list[str]]:
    """Determine which per-video and account-level fields were NOT exposed by TikTok Studio."""
    video_unexposed: list[str] = []
    target_rows = [r for r in video_rows if r.get("within_30d")] or video_rows

    for field in PER_VIDEO_REQUIRED_FIELDS:
        if not target_rows:
            video_unexposed.append(field)
            continue
        if field == "retention_curve":
            if all(not r.get("retention_curve") for r in target_rows):
                video_unexposed.append(field)
        elif field == "traffic_sources":
            if all(
                not isinstance(r.get("traffic_sources"), dict)
                or all(v is None for v in r["traffic_sources"].values())
                for r in target_rows
            ):
                video_unexposed.append(field)
        elif field == "caption_80":
            if all(not r.get("caption_80") for r in target_rows):
                video_unexposed.append(field)
        else:
            if all(r.get(field) is None for r in target_rows):
                video_unexposed.append(field)

    account_unexposed = [
        field for field in ACCOUNT_REQUIRED_FIELDS if account_window.get(field) is None
    ]
    return {
        "per_video": video_unexposed,
        "account_window": account_unexposed,
    }


def build_pull_payload(
    video_rows: list[dict],
    account_overview: dict | None = None,
    *,
    pulled_at_utc: datetime | None = None,
    account_handle: str = "@black_liquidity",
    source_mode: str = "live_cdp",
) -> dict:
    """Assemble the complete JSON payload for `state/cgo/bl/pull-<YYYY-MM-DD>.json`."""
    now_utc = (pulled_at_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff_utc = now_utc - timedelta(days=WINDOW_DAYS)

    within_30d_rows = [r for r in video_rows if r.get("within_30d")]
    older_rows = [r for r in video_rows if r.get("older_than_30d")]

    computed_30d_views = sum((r.get("views") or 0) for r in within_30d_rows)
    acc = dict(account_overview or {})
    account_window = {
        "window_days": WINDOW_DAYS,
        "window_start_utc": cutoff_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_end_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "followers_start": acc.get("followers_start"),
        "followers_end": acc.get("followers_end"),
        "total_views": acc.get("total_views") if acc.get("total_views") is not None else (
            computed_30d_views if within_30d_rows else None
        ),
        "total_views_from_30d_videos": computed_30d_views,
        "videos_in_30d_count": len(within_30d_rows),
        "videos_older_than_30d_count": len(older_rows),
    }

    unexposed = detect_unexposed_fields(video_rows, account_window)

    return {
        "schema_version": 1,
        "account": account_handle,
        "pulled_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pull_date": now_utc.strftime("%Y-%m-%d"),
        "source_mode": source_mode,
        "account_window": account_window,
        "videos": video_rows,
        "unexposed_fields": unexposed,
    }


def video_row_to_csv_dict(row: dict) -> dict[str, Any]:
    """Flatten a single normalized video dict into a flat CSV row dict."""
    ts = row.get("traffic_sources") if isinstance(row.get("traffic_sources"), dict) else {}
    curve = row.get("retention_curve") if isinstance(row.get("retention_curve"), list) else []
    return {
        "video_id": row.get("video_id", ""),
        "post_time_utc": row.get("post_time_utc") or "",
        "within_30d": bool(row.get("within_30d", False)),
        "older_than_30d": bool(row.get("older_than_30d", False)),
        "caption_80": row.get("caption_80") or "",
        "duration_s": "" if row.get("duration_s") is None else row["duration_s"],
        "views": "" if row.get("views") is None else row["views"],
        "likes": "" if row.get("likes") is None else row["likes"],
        "comments": "" if row.get("comments") is None else row["comments"],
        "shares": "" if row.get("shares") is None else row["shares"],
        "saves": "" if row.get("saves") is None else row["saves"],
        "avg_watch_time_s": "" if row.get("avg_watch_time_s") is None else row["avg_watch_time_s"],
        "watched_full_video_pct": (
            "" if row.get("watched_full_video_pct") is None else row["watched_full_video_pct"]
        ),
        "retention_points_count": len(curve),
        "traffic_for_you_pct": "" if ts.get("for_you") is None else ts["for_you"],
        "traffic_search_pct": "" if ts.get("search") is None else ts["search"],
        "traffic_profile_pct": "" if ts.get("profile") is None else ts["profile"],
        "traffic_following_pct": "" if ts.get("following") is None else ts["following"],
        "traffic_other_pct": "" if ts.get("other") is None else ts["other"],
        "new_followers": "" if row.get("new_followers") is None else row["new_followers"],
    }


def write_pull_outputs(payload: dict, out_dir: Path = DEFAULT_OUT_DIR, date_str: str | None = None) -> tuple[Path, Path]:
    """Atomically write `pull-<YYYY-MM-DD>.json` and flat `pull-<YYYY-MM-DD>.csv` under `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    day = date_str or payload.get("pull_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_path = out_dir / f"pull-{day}.json"
    csv_path = out_dir / f"pull-{day}.csv"

    tmp_json = json_path.with_suffix(".json.tmp")
    tmp_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp_json, json_path)

    tmp_csv = csv_path.with_suffix(".csv.tmp")
    with tmp_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in payload.get("videos", []):
            writer.writerow(video_row_to_csv_dict(row))
    os.replace(tmp_csv, csv_path)

    return json_path, csv_path


def save_raw_schema_sample(
    raw_dir: Path,
    endpoint_slug: str,
    endpoint_url: str,
    body: dict | list,
    *,
    schema_status: str = "captured_live_cdp",
) -> Path:
    """Save 1 raw sample per endpoint under `state/cgo/bl/raw-schema/` with query tokens stripped."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", endpoint_slug).strip("_") or "endpoint"
    out_path = raw_dir / f"{safe_slug}.json"
    clean_url = sanitize_url(endpoint_url)

    if isinstance(body, dict):
        wrapped = {
            "_meta": {
                "endpoint_path": clean_url,
                "schema_status": schema_status,
                "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            **{k: v for k, v in body.items() if k != "_meta"},
        }
    else:
        wrapped = {
            "_meta": {
                "endpoint_path": clean_url,
                "schema_status": schema_status,
                "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "items": body,
        }

    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(wrapped, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, out_path)
    return out_path


def format_30d_markdown_table(payload: dict) -> str:
    """Render a Markdown 30-day summary table (views, avg watch s, completion %, FYP %)."""
    lines = [
        "| Video ID | Post Time (UTC) | Window | Views | Avg Watch (s) | Completion (%) | FYP (%) | New Followers | Caption (first 80 chars) |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload.get("videos", []):
        vid = row.get("video_id", "")
        post_t = row.get("post_time_utc") or "n/a"
        win_flag = "30d" if row.get("within_30d") else "older (>30d)"
        views = f"{row['views']:,}" if row.get("views") is not None else "n/a"
        avg_w = f"{row['avg_watch_time_s']:.1f}" if row.get("avg_watch_time_s") is not None else "n/a"
        comp = f"{row['watched_full_video_pct']:.1f}%" if row.get("watched_full_video_pct") is not None else "n/a"
        ts = row.get("traffic_sources") or {}
        fyp = f"{ts['for_you']:.1f}%" if ts.get("for_you") is not None else "n/a"
        nf = str(row["new_followers"]) if row.get("new_followers") is not None else "n/a"
        cap = (row.get("caption_80") or "").replace("|", "\\|")
        lines.append(f"| `{vid}` | {post_t} | {win_flag} | {views} | {avg_w} | {comp} | {fyp} | {nf} | {cap} |")
    return "\n".join(lines)


# ── CDP XHR classification & browser layer ───────────────────────────────────


def classify_xhr_payload(clean_url: str, body: Any) -> str | None:
    """Classify an intercepted JSON payload into `content_list`, `video_analytics`, or `account_overview`."""
    path_lower = clean_url.lower()
    if not isinstance(body, (dict, list)):
        return None

    # Try content list first if path or payload has an items list of videos
    if any(tok in path_lower for tok in ("item_list", "item/list", "content/list", "post_list", "creator/item")):
        try:
            rows = extract_content_list_from_raw(body)
            if rows:
                return "content_list"
        except UnrecognizedResponseShape:
            pass

    if any(tok in path_lower for tok in ("video/detail", "analytics/video", "item_analytics", "video_insight")):
        if isinstance(body, dict):
            try:
                extract_video_analytics_from_raw(body)
                return "video_analytics"
            except UnrecognizedResponseShape:
                pass

    if any(tok in path_lower for tok in ("insight/overview", "analytics/overview", "account_overview", "creator/overview")):
        if isinstance(body, dict):
            try:
                extract_account_overview_from_raw(body)
                return "account_overview"
            except UnrecognizedResponseShape:
                pass

    # Structural fallback regardless of path naming
    if isinstance(body, dict):
        if any(k in body for k in ("video_analytics", "retention_curve", "traffic_sources")):
            try:
                extract_video_analytics_from_raw(body)
                return "video_analytics"
            except UnrecognizedResponseShape:
                pass
        if any(k in body for k in ("account_overview", "followers_start", "followers_end", "follower_history")):
            try:
                extract_account_overview_from_raw(body)
                return "account_overview"
            except UnrecognizedResponseShape:
                pass
    try:
        rows = extract_content_list_from_raw(body)
        if rows:
            return "content_list"
    except UnrecognizedResponseShape:
        pass

    return None


class StudioCDPBrowser:
    """Read-only CDP session over Browser Home `tiktok-bl` (127.0.0.1:9282).

    Opens its own temporary tab so existing Browser Home tabs are never disturbed,
    intercepts XHR JSON via CDP `Network.responseReceived` + `Network.getResponseBody`,
    never clicks any UI element, enforces >= 3s pacing between navigations, and
    closes only its own tab on exit.
    """

    def __init__(self, cdp_url: str = DEFAULT_CDP_URL, pacing_s: float = DEFAULT_PACING_S):
        self.cdp_url = cdp_url
        self.pacing_s = max(MIN_PACING_S, float(pacing_s))
        self._pw = None
        self._browser = None
        self.page = None
        self.cdp = None
        self._last_nav_ts: float | None = None
        self._pending_requests: dict[str, str] = {}
        self.captured_blobs: list[tuple[str, Any]] = []

    def attach(self) -> None:
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url, timeout=15_000)
            if not self._browser.contexts:
                raise RuntimeError(f"no browser context found on CDP {self.cdp_url}")
            ctx = self._browser.contexts[0]
            self.page = ctx.new_page()
            self.cdp = ctx.new_cdp_session(self.page)
            self.cdp.send("Network.enable")
            self.cdp.on("Network.responseReceived", self._on_response_received)
            self.cdp.on("Network.loadingFinished", self._on_loading_finished)
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self.cdp is not None:
            try:
                self.cdp.detach()
            except Exception:
                pass
            self.cdp = None
        if self.page is not None:
            try:
                self.page.close()
            except Exception:
                pass
            self.page = None
        # Never call self._browser.close() on a shared Browser Home; stop Playwright driver only.
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None
            self._browser = None

    def _on_response_received(self, event: dict) -> None:
        try:
            req_id = event.get("requestId")
            resp = event.get("response") or {}
            raw_url = resp.get("url") or ""
            mime = (resp.get("mimeType") or "").lower()
            res_type = (event.get("type") or "").lower()
            if not req_id or not raw_url:
                return
            if "json" in mime or res_type in ("xhr", "fetch"):
                if "tiktok.com" in raw_url:
                    self._pending_requests[req_id] = sanitize_url(raw_url)
        except Exception:
            pass

    def _on_loading_finished(self, event: dict) -> None:
        req_id = event.get("requestId")
        if not req_id or req_id not in self._pending_requests or self.cdp is None:
            return
        clean_url = self._pending_requests.pop(req_id, "")
        self._fetch_body(req_id, clean_url)

    def _fetch_body(self, req_id: str, clean_url: str) -> None:
        if self.cdp is None:
            return
        try:
            res = self.cdp.send("Network.getResponseBody", {"requestId": req_id})
            body_str = res.get("body") or ""
            if res.get("base64Encoded"):
                body_str = base64.b64decode(body_str).decode("utf-8", errors="replace")
            if not body_str.strip().startswith(("{", "[")):
                return
            parsed = json.loads(body_str)
            self.captured_blobs.append((clean_url, parsed))
        except Exception:
            pass

    def _drain_pending_bodies(self) -> None:
        for req_id, clean_url in list(self._pending_requests.items()):
            self._pending_requests.pop(req_id, None)
            self._fetch_body(req_id, clean_url)

    def check_guards(self) -> None:
        """Raise VerificationWall (exit 3) or SignedOut (exit 4) if detected on the current page."""
        if self.page is None:
            return
        curr_url = self.page.url or ""
        if is_login_url(curr_url):
            raise SignedOut("SIGNED_OUT")

        try:
            body_text = self.page.evaluate("() => document.body ? document.body.innerText : ''") or ""
        except Exception:
            body_text = ""

        if has_verification_marker(body_text):
            raise VerificationWall(f"verification marker on {sanitize_url(curr_url)}")

        for sel in _CAPTCHA_DOM_SELECTORS:
            try:
                if self.page.locator(sel).count() > 0:
                    raise VerificationWall(f"captcha selector {sel} present on {sanitize_url(curr_url)}")
            except VerificationWall:
                raise
            except Exception:
                pass

        # Also check if an unauthenticated login channel picker is rendered in-place
        try:
            if self.page.locator('div[data-e2e="channel-item"]').count() > 0:
                raise SignedOut("SIGNED_OUT")
        except SignedOut:
            raise
        except Exception:
            pass

    def navigate_and_collect(self, target_url: str, wait_ms: int = 4000) -> list[tuple[str, Any]]:
        """Navigate to `target_url` with >= 3 s pacing, verify guards, and return captured (clean_url, json_body) pairs."""
        if self.page is None:
            raise RuntimeError("StudioCDPBrowser is not attached")
        self._last_nav_ts = enforce_pacing(self._last_nav_ts, self.pacing_s)
        self.captured_blobs.clear()
        self._pending_requests.clear()

        self.page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
        self.check_guards()
        self.page.wait_for_timeout(wait_ms)
        self._drain_pending_bodies()
        self.check_guards()
        return list(self.captured_blobs)


# ── orchestration ────────────────────────────────────────────────────────────


def pull_from_raw_schema_dir(
    raw_dir: Path,
    *,
    reference_utc: datetime | None = None,
) -> dict:
    """Build a complete pull payload from saved raw schema files in `raw_dir` (offline/fixture mode)."""
    ref = reference_utc or datetime.now(timezone.utc)
    content_path = raw_dir / "content_list.json"
    if not content_path.exists():
        raise FileNotFoundError(f"missing content_list.json in {raw_dir}")

    content_raw = json.loads(content_path.read_text(encoding="utf-8"))
    content_rows = extract_content_list_from_raw(content_raw)

    analytics_by_vid: dict[str, dict] = {}
    va_path = raw_dir / "video_analytics.json"
    if va_path.exists():
        va_raw = json.loads(va_path.read_text(encoding="utf-8"))
        va_parsed = extract_video_analytics_from_raw(va_raw)
        if va_parsed.get("video_id"):
            analytics_by_vid[str(va_parsed["video_id"])] = va_parsed

    account_overview = None
    ao_path = raw_dir / "account_overview.json"
    if ao_path.exists():
        ao_raw = json.loads(ao_path.read_text(encoding="utf-8"))
        account_overview = extract_account_overview_from_raw(ao_raw)

    merged_rows = merge_video_records(content_rows, analytics_by_vid, reference_utc=ref)
    return build_pull_payload(
        merged_rows,
        account_overview,
        pulled_at_utc=ref,
        source_mode="raw_schema_replay",
    )


def run_live_pull(
    *,
    cdp_url: str = DEFAULT_CDP_URL,
    out_dir: Path = DEFAULT_OUT_DIR,
    raw_schema_dir: Path = DEFAULT_RAW_SCHEMA_DIR,
    pacing_s: float = DEFAULT_PACING_S,
    max_videos: int = 50,
    browser_factory: Callable[[], StudioCDPBrowser] | None = None,
    reference_utc: datetime | None = None,
) -> tuple[dict, Path, Path]:
    """Execute the live CDP TikTok Studio pull (caller must hold the home lock)."""
    ref = reference_utc or datetime.now(timezone.utc)
    browser = browser_factory() if browser_factory is not None else StudioCDPBrowser(cdp_url=cdp_url, pacing_s=pacing_s)
    saved_samples: set[str] = set()

    content_rows: list[dict] = []
    analytics_by_vid: dict[str, dict] = {}
    account_overview: dict | None = None

    try:
        browser.attach()

        # 1. Load Studio Content list page
        for clean_url, blob in browser.navigate_and_collect(STUDIO_CONTENT_URL):
            kind = classify_xhr_payload(clean_url, blob)
            if kind == "content_list":
                rows = extract_content_list_from_raw(blob)
                content_rows.extend(rows)
                if "content_list" not in saved_samples:
                    save_raw_schema_sample(raw_schema_dir, "content_list", clean_url, blob)
                    saved_samples.add("content_list")
            elif kind == "account_overview" and account_overview is None:
                account_overview = extract_account_overview_from_raw(blob)
                if "account_overview" not in saved_samples:
                    save_raw_schema_sample(raw_schema_dir, "account_overview", clean_url, blob)
                    saved_samples.add("account_overview")

        # 2. Load Studio Analytics overview page
        for clean_url, blob in browser.navigate_and_collect(STUDIO_ANALYTICS_URL):
            kind = classify_xhr_payload(clean_url, blob)
            if kind == "account_overview" and account_overview is None:
                account_overview = extract_account_overview_from_raw(blob)
                if "account_overview" not in saved_samples:
                    save_raw_schema_sample(raw_schema_dir, "account_overview", clean_url, blob)
                    saved_samples.add("account_overview")
            elif kind == "content_list" and not content_rows:
                content_rows.extend(extract_content_list_from_raw(blob))
                if "content_list" not in saved_samples:
                    save_raw_schema_sample(raw_schema_dir, "content_list", clean_url, blob)
                    saved_samples.add("content_list")

        # Deduplicate content_rows preserving order
        deduped_rows: list[dict] = []
        seen_vids: set[str] = set()
        for r in content_rows:
            vid = str(r["video_id"])
            if vid not in seen_vids:
                seen_vids.add(vid)
                deduped_rows.append(flag_30d_window(r, ref))
        content_rows = deduped_rows

        # 3. For each video posted in the last 30 days (up to max_videos), open its per-video analytics URL
        for row in content_rows[:max_videos]:
            if row.get("older_than_30d"):
                continue
            vid = str(row["video_id"])
            target = STUDIO_VIDEO_ANALYTICS_URL_TMPL.format(video_id=vid)
            for clean_url, blob in browser.navigate_and_collect(target):
                kind = classify_xhr_payload(clean_url, blob)
                if kind == "video_analytics" and isinstance(blob, dict):
                    parsed = extract_video_analytics_from_raw(blob, default_video_id=vid)
                    analytics_by_vid[vid] = parsed
                    if "video_analytics" not in saved_samples:
                        save_raw_schema_sample(raw_schema_dir, "video_analytics", clean_url, blob)
                        saved_samples.add("video_analytics")
    finally:
        browser.close()

    merged_rows = merge_video_records(content_rows, analytics_by_vid, reference_utc=ref)
    payload = build_pull_payload(
        merged_rows,
        account_overview,
        pulled_at_utc=ref,
        source_mode="live_cdp",
    )
    json_path, csv_path = write_pull_outputs(payload, out_dir=out_dir, date_str=payload["pull_date"])
    return payload, json_path, csv_path


# ── CLI entry point ──────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="bl_studio_pull.py",
        description=__doc__.split("\n\n")[0],
    )
    ap.add_argument("--cdp", default=DEFAULT_CDP_URL, help="CDP endpoint URL (default: http://127.0.0.1:9282)")
    ap.add_argument("--lock-key", default=DEFAULT_LOCK_KEY, help="Browser Home lock key (default: home:contabo:9282)")
    ap.add_argument("--purpose", default=DEFAULT_LOCK_PURPOSE, help="Lock purpose string")
    ap.add_argument("--owner", default="", help="Lock owner session/task id (defaults to env session/task id)")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory (default: state/cgo/bl)")
    ap.add_argument(
        "--raw-schema-dir",
        type=Path,
        default=DEFAULT_RAW_SCHEMA_DIR,
        help="Directory for 1 raw sample per endpoint (default: state/cgo/bl/raw-schema)",
    )
    ap.add_argument(
        "--pacing",
        type=float,
        default=DEFAULT_PACING_S,
        help="Minimum seconds between page loads (enforced >= 3.0s)",
    )
    ap.add_argument("--max-videos", type=int, default=50, help="Max 30-day videos to query per-video analytics for")
    ap.add_argument(
        "--from-raw-dir",
        type=Path,
        default=None,
        help="Offline replay: build pull JSON + CSV from saved raw-schema JSON files without touching CDP",
    )
    ap.add_argument("--date", default=None, help="Override pull-<YYYY-MM-DD> date stamp")
    ap.add_argument("--print-table", action="store_true", help="Print the 30-day Markdown table to stdout")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.from_raw_dir is not None:
        payload = pull_from_raw_schema_dir(args.from_raw_dir)
        json_path, csv_path = write_pull_outputs(payload, out_dir=args.out_dir, date_str=args.date)
        print(f"Wrote {json_path} and {csv_path} ({len(payload['videos'])} videos)")
        if args.print_table:
            print(format_30d_markdown_table(payload))
        return EXIT_OK

    owner = (args.owner or home_lock.default_owner() or "cgo-studio-pull").strip()
    try:
        home_lock.acquire(args.lock_key, owner=owner, purpose=args.purpose)
    except home_lock.HomeLockHeld as e:
        print(f"LOCK_HELD: {e}", file=sys.stderr)
        return EXIT_LOCK_ERROR
    except Exception as e:
        print(f"LOCK_ERROR: {e}", file=sys.stderr)
        return EXIT_LOCK_ERROR

    try:
        payload, json_path, csv_path = run_live_pull(
            cdp_url=args.cdp,
            out_dir=args.out_dir,
            raw_schema_dir=args.raw_schema_dir,
            pacing_s=max(MIN_PACING_S, args.pacing),
            max_videos=args.max_videos,
        )
        if args.date:
            json_path, csv_path = write_pull_outputs(payload, out_dir=args.out_dir, date_str=args.date)
        print(f"Wrote {json_path} and {csv_path} ({len(payload['videos'])} videos)")
        if args.print_table:
            print(format_30d_markdown_table(payload))
        return EXIT_OK
    except SignedOut:
        print("SIGNED_OUT")
        return EXIT_SIGNED_OUT
    except VerificationWall as e:
        print(f"CAPTCHA_OR_VERIFY_WALL: {e}", file=sys.stderr)
        return EXIT_CAPTCHA
    finally:
        try:
            home_lock.release(args.lock_key, owner=owner)
        except Exception as e:
            print(f"home_lock: release of {args.lock_key} failed ({e})", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
