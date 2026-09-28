"""Tests for the FB Reels composer poster (task-c6bd5ba6; permalink/comment
work task-cfdc75a8).

Covers everything that needs no browser: caption paragraph-level compare
(the field-note fix for ProseMirror's doubled blank lines), the three-state
permalink classifier and its logged-out HTML content check, the comment
identity/idempotency helpers, the double-publish Thai-date guard, and CLI
argument parsing (including the per-mode required-argument gate). FBReelBrowser
(the only class with real Playwright/CDP calls) is never instantiated here —
its docstring in tools/fb_reel_post.py explains why (verified live via scratch
exploration, exercised for real via --dry-run/--resolve-permalink/--comment-only,
not unit-tested). `resolve_permalink`'s polling loop IS unit-tested here, via a
fake browser stub and injected fetch_html/now/sleep — no real network or CDP.

Run via:  pytest tests/test_fb_reel_post.py
"""
from __future__ import annotations

from datetime import datetime

import pytest

from tools import fb_reel_post as frp


def test_captions_match_identical():
    ok, diff = frp.captions_match("line one\nline two", "line one\nline two")
    assert ok
    assert diff == []


def test_captions_match_ignores_doubled_blank_lines():
    # ProseMirror/contenteditable readback is known to double blank lines
    # between paragraphs — this must NOT be treated as a mismatch.
    expected = "para one\n\npara two\n\npara three"
    actual_doubled = "para one\n\n\n\npara two\n\n\n\npara three"
    ok, diff = frp.captions_match(expected, actual_doubled)
    assert ok, diff


def test_captions_match_detects_real_difference():
    ok, diff = frp.captions_match("expected line", "actual line")
    assert not ok
    assert diff == ["line 0: expected='expected line' actual='actual line'"]


def test_captions_match_detects_missing_trailing_line():
    ok, diff = frp.captions_match("line one\nline two", "line one")
    assert not ok
    assert diff == ["line 1: expected='line two' actual='<MISSING>'"]


def test_captions_match_strips_leading_trailing_blank_lines():
    ok, diff = frp.captions_match("\n\ncontent\n\n", "content")
    assert ok, diff


def test_normalize_caption_collapses_blank_runs():
    assert frp.normalize_caption("a\n\n\n\nb") == ["a", "", "b"]


def test_build_parser_required_args():
    ap = frp.build_parser()
    args = ap.parse_args([
        "--asset-id", "123",
        "--video", "/tmp/v.mp4",
        "--cover", "/tmp/c.png",
        "--caption-file", "/tmp/cap.txt",
    ])
    assert args.asset_id == "123"
    assert args.video == "/tmp/v.mp4"
    assert args.cover == "/tmp/c.png"
    assert args.caption_file == "/tmp/cap.txt"
    assert args.dry_run is False
    assert args.cdp == "http://127.0.0.1:9230"


def test_build_parser_dry_run_flag():
    ap = frp.build_parser()
    args = ap.parse_args([
        "--asset-id", "123", "--video", "v.mp4", "--cover", "c.png",
        "--caption-file", "cap.txt", "--dry-run",
    ])
    assert args.dry_run is True


def test_build_parser_missing_required_arg_exits():
    ap = frp.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args(["--video", "v.mp4"])


def test_build_parser_custom_cdp():
    ap = frp.build_parser()
    args = ap.parse_args([
        "--cdp", "http://127.0.0.1:9999",
        "--asset-id", "123", "--video", "v.mp4", "--cover", "c.png",
        "--caption-file", "cap.txt",
    ])
    assert args.cdp == "http://127.0.0.1:9999"


# -- new modes: --resolve-permalink / --comment-only / --delete-test-post ---

def test_build_parser_resolve_permalink_mode_minimal_args():
    ap = frp.build_parser()
    args = ap.parse_args(["--resolve-permalink", "--caption-file", "cap.txt"])
    assert args.resolve_permalink is True
    assert args.caption_file == "cap.txt"
    assert args.page_id == frp.DEFAULT_PAGE_ID


def test_build_parser_resolve_permalink_missing_caption_file_exits():
    ap = frp.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args(["--resolve-permalink"])


def test_build_parser_comment_only_mode_minimal_args():
    ap = frp.build_parser()
    args = ap.parse_args([
        "--comment-only", "--permalink", "https://x", "--first-comment-file", "c.txt",
    ])
    assert args.comment_only is True
    assert args.permalink == "https://x"
    assert args.page_name == frp.DEFAULT_PAGE_NAME


def test_build_parser_comment_only_missing_args_exits():
    ap = frp.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args(["--comment-only", "--permalink", "https://x"])


def test_build_parser_delete_test_post_minimal_args():
    ap = frp.build_parser()
    args = ap.parse_args(["--delete-test-post", "https://x"])
    assert args.delete_test_post == "https://x"


def test_build_parser_mutually_exclusive_modes_exits():
    ap = frp.build_parser()
    with pytest.raises(SystemExit):
        ap.parse_args([
            "--resolve-permalink", "--comment-only",
            "--caption-file", "c.txt", "--permalink", "https://x",
            "--first-comment-file", "f.txt",
        ])


# -- extract_page_description / verify_permalink_content --------------------

def test_extract_page_description_prefers_og():
    html_text = (
        '<meta property="og:description" content="og text">'
        '<meta name="description" content="name text">'
    )
    assert frp.extract_page_description(html_text) == "og text"


def test_extract_page_description_falls_back_to_name_meta_and_unescapes_entities():
    # &#xe22; is U+0E22 (Thai ย), numeric-entity-encoded the way film 2's
    # real permalink HTML was measured to encode it (task-cfdc75a8, 2026-09-26).
    html_text = '<meta name="description" content="test &#xe22;ok">'
    assert frp.extract_page_description(html_text) == "test ยok"


def test_extract_page_description_absent_returns_empty():
    assert frp.extract_page_description("<title>Facebook</title>") == ""


def test_verify_permalink_content_positive():
    caption = "ยายเก็บขวดขายทุกวัน… แต่ตาชั่งร้านเสี่ยชั่งให้ขาดทุกเที่ยว\nnext line"
    html_text = (
        '<meta name="description" content="ยายเก็บขวดขายทุกวัน… '
        'แต่ตาชั่งร้านเสี่ยชั่งให้ขาดทุกเที่ยว - more text">'
    )
    assert frp.verify_permalink_content(html_text, caption) is True


def test_verify_permalink_content_negative_dead_page():
    # Mirrors film 1's dead reel (1104791208680559): no description meta at
    # all, bare "Facebook" title — must NOT verify.
    caption = "ยายเก็บขวดขายทุกวัน… แต่ตาชั่งร้านเสี่ยชั่งให้ขาดทุกเที่ยว"
    html_text = "<title>Facebook</title>"
    assert frp.verify_permalink_content(html_text, caption) is False


def test_verify_permalink_content_negative_caption_mismatch():
    caption = "caption that was actually published"
    html_text = '<meta name="description" content="a completely different caption">'
    assert frp.verify_permalink_content(html_text, caption) is False


# -- is_failure_evidence / classify_permalink_state / outcome_to_exit_code --

def test_is_failure_evidence_true():
    assert frp.is_failure_evidence("โพสต์นี้ไม่ได้บันทึกไว้อย่างถูกต้อง")


def test_is_failure_evidence_false():
    assert not frp.is_failure_evidence("กำลังประมวลผล")


def test_classify_permalink_state_verified():
    outcome, evidence = frp.classify_permalink_state("https://x", "", True, False)
    assert outcome == "verified"
    assert evidence == "https://x"


def test_classify_permalink_state_failed_on_marker():
    outcome, evidence = frp.classify_permalink_state(None, "ไม่สำเร็จ", True, False)
    assert outcome == "failed"
    assert evidence == "ไม่สำเร็จ"


def test_classify_permalink_state_pending_before_timeout():
    outcome, _ = frp.classify_permalink_state(None, "", True, False)
    assert outcome == "pending"


def test_classify_permalink_state_published_unverified_at_timeout():
    outcome, evidence = frp.classify_permalink_state(None, "some row text", True, True)
    assert outcome == "published_unverified"
    assert evidence == "some row text"


def test_classify_permalink_state_failed_no_evidence_at_timeout():
    outcome, _ = frp.classify_permalink_state(None, "", False, True)
    assert outcome == "failed"


def test_outcome_to_exit_code():
    assert frp.outcome_to_exit_code("verified") == 0
    assert frp.outcome_to_exit_code("published_unverified") == 6
    assert frp.outcome_to_exit_code("failed") == 8


# -- find_activity_row_for_caption / parse_thai_datetime / is_recent_duplicate

def test_find_activity_row_for_caption_found():
    body = "line a\nline b\ncaption first line here\nrow detail 1\nrow detail 2"
    row = frp.find_activity_row_for_caption(body, "caption first line here\nsecond")
    assert "caption first line here" in row
    assert "row detail 1" in row


def test_find_activity_row_for_caption_not_found():
    assert frp.find_activity_row_for_caption("unrelated text", "caption first line") == ""


def test_parse_thai_datetime_valid():
    dt = frp.parse_thai_datetime("โพสต์เมื่อ 26 ก.ย. 2026, 12:07 น.")
    assert dt == datetime(2026, 9, 26, 12, 7)


def test_parse_thai_datetime_invalid():
    assert frp.parse_thai_datetime("no date here") is None


def test_is_recent_duplicate_within_window():
    assert frp.is_recent_duplicate("26 ก.ย. 2026, 12:07", datetime(2026, 9, 26, 20, 0)) is True


def test_is_recent_duplicate_outside_window():
    assert frp.is_recent_duplicate("24 ก.ย. 2026, 12:07", datetime(2026, 9, 26, 20, 0)) is False


def test_is_recent_duplicate_no_timestamp():
    assert frp.is_recent_duplicate("no date", datetime(2026, 9, 26, 20, 0)) is False


# -- comment identity / idempotency / body_contains_text / test marker ------

def test_parse_comment_identity_chue_phrasing():
    label = "แสดงความคิดเห็นในชื่อ ละครสั้นคุณธรรม by ILAG Studio"
    assert frp.parse_comment_identity(label) == "ละครสั้นคุณธรรม by ILAG Studio"


def test_parse_comment_identity_naam_phrasing():
    assert frp.parse_comment_identity("แสดงความคิดเห็นในนาม Some Page") == "Some Page"


def test_parse_comment_identity_no_match():
    assert frp.parse_comment_identity("unrelated label") is None


def test_is_duplicate_comment_true():
    # Real ProseMirror-doubling scenario: same paragraph break, doubled blank
    # lines on readback — must still be recognised as the same comment.
    assert frp.is_duplicate_comment("para one\n\npara two", ["other", "para one\n\n\n\npara two"])


def test_is_duplicate_comment_false():
    assert not frp.is_duplicate_comment("hello\nworld", ["something else"])


def test_body_contains_text_true():
    body = "noise\nline one\nline two\nmore noise"
    assert frp.body_contains_text(body, "line one\nline two")


def test_body_contains_text_false_wrong_order():
    body = "line one\nunrelated\nline two"
    assert not frp.body_contains_text(body, "line one\nline two")


# -- collapsed-comment fixture (CEO/CTO addendum 2026-09-29, EP4 live bug: ---
# -- Facebook collapses a long comment to "<prefix>... ดูเพิ่มเติม" in its ---
# -- own innerText, which broke the strict multi-line body_contains_text ----
# -- match and would have let is_duplicate_comment double-post a re-run ----

def test_body_contains_text_true_for_facebook_collapsed_comment():
    comment = "ดูละครสั้น «ขายฝากนาแม่» เต็มเรื่องได้ที่นี่เลยครับ 👇 https://www.facebook.com/61594116376333/videos/1973008630041783/"
    collapsed_body = "noise\nดูละครสั้น «ขายฝากนาแม่» เต็มเรื่องได้ที่... ดูเพิ่มเติม\nmore noise"
    assert frp.body_contains_text(collapsed_body, comment)


def test_body_contains_text_false_when_collapsed_prefix_does_not_match():
    comment = "ดูละครสั้น «ขายฝากนาแม่» เต็มเรื่องได้ที่นี่เลยครับ"
    collapsed_body = "noise\nข้อความอื่นที่ไม่เกี่ยวข้อง... ดูเพิ่มเติม\nmore noise"
    assert not frp.body_contains_text(collapsed_body, comment)


def test_is_duplicate_comment_true_for_facebook_collapsed_existing_comment():
    comment = "ดูละครสั้น «ขายฝากนาแม่» เต็มเรื่องได้ที่นี่เลยครับ 👇 https://www.facebook.com/61594116376333/videos/1973008630041783/"
    existing = ["other comment", "ดูละครสั้น «ขายฝากนาแม่» เต็มเรื่องได้ที่... ดูเพิ่มเติม"]
    assert frp.is_duplicate_comment(comment, existing)


def test_extract_test_marker_found():
    assert frp.extract_test_marker("ทดสอบระบบ [TEST-a1b2c3d4]") == "a1b2c3d4"


def test_extract_test_marker_absent():
    assert frp.extract_test_marker("no marker here") is None


def test_has_test_marker():
    assert frp.has_test_marker("[TEST-deadbeef]")
    assert not frp.has_test_marker("plain caption")


def test_looks_like_login_wall_true():
    assert frp.looks_like_login_wall("โปรดเข้าสู่ระบบ Facebook เพื่อดำเนินการต่อ")


def test_looks_like_login_wall_false():
    assert not frp.looks_like_login_wall("normal page content")


# -- resolve_permalink polling loop (fake browser, injected fetch/now/sleep) -

class _FakeBrowser:
    """Stands in for FBReelBrowser: only the methods resolve_permalink calls."""

    def __init__(self, candidates_sequence, activity_sequence):
        self.candidates_sequence = candidates_sequence
        self.activity_sequence = activity_sequence
        self._round = 0

    def list_public_video_candidates(self, page_id):
        idx = min(self._round, len(self.candidates_sequence) - 1)
        return self.candidates_sequence[idx]

    def read_activity_feed_text(self, asset_id):
        idx = min(self._round, len(self.activity_sequence) - 1)
        text = self.activity_sequence[idx]
        self._round += 1
        return text

    def log(self, msg):
        pass


def test_resolve_permalink_verified_on_first_round():
    fb = _FakeBrowser(
        candidates_sequence=[[("1", "https://www.facebook.com/x/videos/1/")]],
        activity_sequence=[""],
    )
    result = frp.resolve_permalink(
        fb, "pid", "aid", "caption first line\nmore",
        fetch_html=lambda url: '<meta name="description" content="caption first line">',
        now=lambda: 1000.0, sleep=lambda s: None, timeout_s=1800,
    )
    assert result == {
        "outcome": "verified",
        "url": "https://www.facebook.com/x/videos/1/",
        "evidence": "https://www.facebook.com/x/videos/1/",
    }


def test_resolve_permalink_published_unverified_after_timeout():
    fb = _FakeBrowser(
        candidates_sequence=[[("1", "https://www.facebook.com/x/videos/1/")]],
        activity_sequence=["some row text without a failure marker"],
    )
    calls = {"n": 0}

    def now():
        calls["n"] += 1
        return 1000.0 if calls["n"] == 1 else 999999.0

    result = frp.resolve_permalink(
        fb, "pid", "aid", "caption line",
        fetch_html=lambda url: "",  # never verifies
        now=now, sleep=lambda s: None, timeout_s=1800,
    )
    assert result["outcome"] == "published_unverified"


def test_resolve_permalink_failed_on_marker_immediately():
    # The feed row must carry the caption's own first line for
    # find_activity_row_for_caption to anchor on it — a row with only the
    # failure text and no caption match returns "" and the poll keeps
    # going (correct: a real run's clock advances until the 30 min
    # timeout). This fixture puts both in the same row, as the real
    # Business Suite feed does.
    fb = _FakeBrowser(
        candidates_sequence=[[]],
        activity_sequence=["caption line\nโพสต์นี้ไม่ได้บันทึกไว้อย่างถูกต้อง"],
    )
    result = frp.resolve_permalink(
        fb, "pid", "aid", "caption line",
        fetch_html=lambda url: "",
        now=lambda: 1000.0, sleep=lambda s: None, timeout_s=1800,
    )
    assert result["outcome"] == "failed"


def test_resolve_permalink_failed_when_nothing_seen_at_all_after_timeout():
    fb = _FakeBrowser(candidates_sequence=[[]], activity_sequence=[""])
    calls = {"n": 0}

    def now():
        calls["n"] += 1
        return 1000.0 if calls["n"] == 1 else 999999.0

    result = frp.resolve_permalink(
        fb, "pid", "aid", "caption line",
        fetch_html=lambda url: "",
        now=now, sleep=lambda s: None, timeout_s=1800,
    )
    assert result["outcome"] == "failed"


def test_resolve_permalink_polls_then_verifies():
    fb = _FakeBrowser(
        candidates_sequence=[
            [("1", "https://www.facebook.com/x/videos/1/")],
            [("1", "https://www.facebook.com/x/videos/1/")],
        ],
        activity_sequence=["", ""],
    )
    fetch_calls = {"n": 0}

    def fetch_html(url):
        fetch_calls["n"] += 1
        if fetch_calls["n"] == 1:
            return ""  # first round: not indexed yet
        return '<meta name="description" content="caption first line">'

    sleeps = []
    result = frp.resolve_permalink(
        fb, "pid", "aid", "caption first line",
        fetch_html=fetch_html, now=lambda: 1000.0,
        sleep=lambda s: sleeps.append(s), timeout_s=1800, poll_interval_s=120,
    )
    assert result["outcome"] == "verified"
    assert sleeps == [120]
