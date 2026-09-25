"""Tests for the FB group-feed poster (task-708dd145).

Covers everything that needs no browser: caption paragraph-level compare
(same ProseMirror doubled-blank-line fix as tools/fb_reel_post.py) and the
link-presence check. FBGroupBrowser (the only class with real
Playwright/CDP calls) is never instantiated here — exercised live via
--dry-run instead.

Run via:  pytest tests/test_fb_group_share.py
"""
from __future__ import annotations

from tools import fb_group_share as fgs


def test_captions_match_identical():
    ok, diff = fgs.captions_match("line one\nline two", "line one\nline two")
    assert ok
    assert diff == []


def test_captions_match_ignores_doubled_blank_lines():
    expected = "para one\n\npara two\n\npara three"
    actual_doubled = "para one\n\n\n\npara two\n\n\n\npara three"
    ok, diff = fgs.captions_match(expected, actual_doubled)
    assert ok, diff


def test_captions_match_detects_real_difference():
    ok, diff = fgs.captions_match("expected line", "actual line")
    assert not ok
    assert diff == ["line 0: expected='expected line' actual='actual line'"]


def test_captions_match_detects_missing_trailing_line():
    ok, diff = fgs.captions_match("line one\nline two", "line one")
    assert not ok
    assert diff == ["line 1: expected='line two' actual='<MISSING>'"]


def test_link_in_text_true():
    text = "hello\nhttps://www.facebook.com/reel/4560927164226012\n"
    assert fgs.link_in_text(text, "https://www.facebook.com/reel/4560927164226012")


def test_link_in_text_false():
    text = "hello\nno link here\n"
    assert not fgs.link_in_text(text, "https://www.facebook.com/reel/4560927164226012")


def test_build_parser_defaults():
    ap = fgs.build_parser()
    args = ap.parse_args([
        "--group-url", "https://www.facebook.com/groups/123/",
        "--text-file", "caption.txt",
        "--link", "https://www.facebook.com/reel/1/",
    ])
    assert args.cdp == "http://127.0.0.1:9230"
    assert args.group_url == "https://www.facebook.com/groups/123/"
    assert args.dry_run is False
    assert args.page_name == "ละครสั้นคุณธรรม by ILAG Studio"
