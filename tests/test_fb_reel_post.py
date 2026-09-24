"""Tests for the FB Reels composer poster (task-c6bd5ba6).

Covers everything that needs no browser: caption paragraph-level compare
(the field-note fix for ProseMirror's doubled blank lines) and CLI argument
parsing. FBReelBrowser (the only class with real Playwright/CDP calls) is
never instantiated here — its docstring in tools/fb_reel_post.py explains
why (verified live via scratch exploration, exercised for real via
--dry-run, not unit-tested).

Run via:  pytest tests/test_fb_reel_post.py
"""
from __future__ import annotations

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
