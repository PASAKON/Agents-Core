"""Tests for the TopView Wan 3.0 runner's pure helpers (tools/topview_wan3.py).

The money gate reads a number off a button and a balance off a sidebar, and the prompt box turns only one
token spelling into a reference chip; those parsers are what these tests pin. TopViewBrowser (the only
class that touches Chrome) is not exercised here.

Run via:  pytest tests/test_topview_wan3.py
"""
from __future__ import annotations

import struct
from pathlib import Path

import pytest

from tools import topview_wan3 as tv


def test_tokens_are_rewritten_to_the_form_the_box_chips():
    # measured 2026-09-26: a pasted "@Image1" and "<<<Image1>>>" become chips, "@Image 1" stays plain text
    p = tv.normalize_tokens("@Image 1: THE MOUNT. <<<Image2>>> the village. @Image 10 and @Video 1.")
    assert p == "@Image1: THE MOUNT. @Image2 the village. @Image10 and @Video1."
    assert tv.chip_tags(p) == ["@Image1", "@Image2", "@Image10", "@Video1"]


def test_cost_is_read_only_from_a_generate_button_with_a_number():
    assert tv.parse_cost("Generate 0.6") == 0.6
    assert tv.parse_cost("Generate 15") == 15.0
    assert tv.parse_cost("Generate") is None           # no number read -> no click
    assert tv.parse_cost("Get Free Unlimited Generations") is None


def test_menus_compare_by_last_token_not_suffix():
    assert tv._last("SD 480p") == "480p"
    assert tv._last("12s") == "12s" and tv._last("12s") != "2s"


def test_lowest_resolution():
    assert tv.lowest_resolution(["720p", "1080p", "480p"]) == "480p"


def test_hazards_stop_money_and_failure_text_but_not_the_upsell_button():
    assert tv.classify_hazard("Insufficient credits. Top up to continue")
    assert tv.classify_hazard("Generation failed, credits refunded")
    assert tv.classify_hazard("Get Free Unlimited Generations Generate 0.6") is None


def test_ledger_key_keeps_rehearsal_apart_from_the_shot():
    assert tv.job_key(Path("n01-rehearsal.wan3.json")) == "n01-rehearsal"
    assert tv.job_key(Path("n01.wan3.json")) == "n01"


def test_images_resolve_by_basename_in_order(tmp_path):
    for n in ("ref-Manta.png", "loc_village_above_A_v2.png"):
        (tmp_path / n).write_bytes(b"x")
    job = {"images": ["Character/ref-Manta.png", "Location/loc_village_above_A_v2.png"]}
    assert [p.name for p in tv.resolve_images(job, tmp_path)] == ["ref-Manta.png", "loc_village_above_A_v2.png"]
    with pytest.raises(FileNotFoundError):
        tv.resolve_images({"images": ["Character/missing.png"]}, tmp_path)


def _mvhd(version: int, scale: int, dur: int) -> bytes:
    if version == 1:
        body = bytes([1, 0, 0, 0]) + struct.pack(">QQIQ", 0, 0, scale, dur)
    else:
        body = bytes([0, 0, 0, 0]) + struct.pack(">IIII", 0, 0, scale, dur)
    return b"\x00\x00\x00\x00ftypisom" + struct.pack(">I", 8 + len(body) + 40) + b"mvhd" + body + b"\x00" * 40


def test_mp4_duration_from_the_header():
    assert tv.mp4_duration(_mvhd(0, 1000, 2042)) == pytest.approx(2.042)
    assert tv.mp4_duration(_mvhd(1, 90000, 180000)) == pytest.approx(2.0)
    assert tv.mp4_duration(b"not a video") is None


def test_mp4_urls_are_pulled_out_of_json():
    body = '{"a":"https://cdn.x.com/v/abc.mp4?sig=1\\u0026t=2","b":"https://cdn.x.com/v/abc.mp4?sig=1\\u0026t=2"}'
    assert tv.mp4_urls(body) == ["https://cdn.x.com/v/abc.mp4?sig=1&t=2"]
    assert tv.mp4_urls('{"u":"https:\\/\\/cdn.x.com\\/v\\/c.mp4"}') == ["https://cdn.x.com/v/c.mp4"]


class _Page:
    def wait_for_timeout(self, ms):
        pass


class _FreePlanBrowser:
    """A stub that reads like the live page on 2026-09-26: Free plan, 5 credits, button 'Generate 0.6'."""
    def __init__(self):
        self.page, self.clicks = _Page(), 0

    def state(self):
        return {"genText": "Generate 0.6", "balanceText": "5", "genDisabled": False, "dialogs": [],
                "pricingModal": "", "plan": "Free"}

    def click_generate(self, cost):
        self.clicks += 1

    def log(self, *a):
        pass


def test_free_plan_stops_before_the_click(tmp_path, monkeypatch):
    refs = tmp_path / "refs"
    refs.mkdir()
    (refs / "a.png").write_bytes(b"x")
    job = tmp_path / "n01-rehearsal.wan3.json"
    job.write_text('{"key": "n01", "title": "t", "seconds": 2, "images": ["C/a.png"], "prompt": "@Image 1 x"}')
    monkeypatch.setattr(tv, "prepare", lambda *a, **k: {
        "gen_text": "Generate 0.6", "balance_text": "5", "model": "Wan 3.0", "aspect": "16:9", "seconds": "2s",
        "resolution": "SD 480p", "chips": ["@Image1"], "plan": "Free"})
    args = type("A", (), dict(refs=None, out=str(tmp_path / "out"), dry_run=False, resolution=None,
                              probe_costs=False, max_credits=3, allow_free_plan=False, timeout_s=5))()
    b, ledger = _FreePlanBrowser(), {}
    row = tv.run_job(b, job, args, ledger, tmp_path / "out" / "ledger.json")
    assert row["status"] == "stopped" and row["hazard_kind"] == "plan_required"
    assert b.clicks == 0
    assert ledger["n01-rehearsal"]["status"] not in tv.FIRED  # a later run, after the plan is bought, may fire
