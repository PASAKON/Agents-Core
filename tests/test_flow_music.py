"""Tests for the Google Flow Music runner's pure helpers (tools/flow_music.py).

The UI shows no price on Generate, so the money gate is the balance read and the charge afterwards; the song
match decides which files are ours. Those are what these tests pin. FlowMusicBrowser (the only class that
touches Chrome) is not exercised here.

Run via:  pytest tests/test_flow_music.py
"""
from __future__ import annotations

import json
import struct

import pytest

from tools import flow_music as fm


def test_balance_is_read_from_the_account_menu_text():
    assert fm.parse_credits("30610 credits") == 30610.0
    assert fm.parse_credits("30,610 credits") == 30610.0
    assert fm.parse_credits("Credits 30610 available") == 30610.0
    assert fm.parse_credits("Buy Credits") is None


def test_length_is_refused_where_the_ui_would_clamp_it():
    assert fm.check_length("1:00") == "1:00"
    assert fm.check_length("2:07") == "2:07"
    for bad in ("0:30", "3:01", "60", "1:5"):
        with pytest.raises(ValueError):
            fm.check_length(bad)


def test_a_song_is_ours_only_if_new_and_from_our_prompt_or_session():
    prompt = "A slow,  spacious piece.\nNo vocals."
    clip = {"id": "new", "operation": {"sound_prompt": "A slow, spacious piece. No vocals.", "conversation_id": "s1"}}
    assert fm.ours(clip, set(), prompt, None)
    assert not fm.ours(clip, {"new"}, prompt, None)                        # existed before the click
    other = {"id": "x", "operation": {"sound_prompt": "disco", "conversation_id": "s2"}}
    assert not fm.ours(other, set(), prompt, "s1")
    assert fm.ours(dict(other, operation={"sound_prompt": "rewritten", "conversation_id": "s1"}), set(), prompt, "s1")


def test_clip_status_from_the_library_json():
    done = {"duration": {"status": "completed", "value": "60.2"}, "wav_url": "https://x/a.wav"}
    assert fm.clip_status(done) == "completed"
    assert fm.clip_seconds(done) == 60.2
    assert fm.clip_status({"duration": {"status": "pending"}}) == "pending"
    assert fm.clip_status({"duration": {"status": "completed"}}) == "pending"      # no file URL yet
    assert fm.clip_status({"duration": {"status": "failed"}, "wav_url": "u"}) == "failed"


def test_money_text_is_a_hazard_and_plain_text_is_not():
    assert fm.classify_hazard("You are out of credits. Buy Credits to continue")
    assert fm.classify_hazard("Upgrade your plan to generate more")
    assert fm.classify_hazard("Generate Ctrl Enter") is None


def test_gate_refuses_without_a_plain_generate_button_or_balance():
    st = {"genCount": 1, "genText": "Generate", "genDisabled": False, "dialogs": []}
    fm.gate(st, 30610, 20)
    with pytest.raises(fm.HazardStop):
        fm.gate(dict(st, genText="Upgrade"), 30610, 20)
    with pytest.raises(fm.HazardStop):
        fm.gate(st, 10, 20)
    with pytest.raises(fm.HazardStop):
        fm.gate(st, None, 20)
    with pytest.raises(fm.HazardStop):
        fm.gate(dict(st, dialogs=["Not enough credits"]), 30610, 20)


def _wav(seconds: float, rate: int = 48000, channels: int = 2) -> bytes:
    byte_rate = rate * channels * 2
    data_len = int(seconds * byte_rate)
    fmt = struct.pack("<HHIIHH", 1, channels, rate, byte_rate, channels * 2, 16)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"LIST" + struct.pack("<I", 4) + b"INFO" \
        + b"data" + struct.pack("<I", data_len) + b"\0" * data_len
    return b"RIFF" + struct.pack("<I", len(body)) + body


def test_wav_duration_walks_the_chunks():
    assert fm.wav_duration(_wav(1.5)) == pytest.approx(1.5)
    assert fm.wav_duration(b"not a wav at all" * 4) is None


def test_prompts_file_is_validated(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps([{"id": "A1", "title": "T", "prompt": "x"}]), encoding="utf-8")
    assert fm.load_prompts(p)[0]["id"] == "A1"
    p.write_text(json.dumps([{"id": "A1", "prompt": "x"}, {"id": "A1", "prompt": "y"}]), encoding="utf-8")
    with pytest.raises(ValueError):
        fm.load_prompts(p)
    p.write_text(json.dumps([{"id": "A1", "prompt": "x" * 3001}]), encoding="utf-8")
    with pytest.raises(ValueError):
        fm.load_prompts(p)
    assert fm.song_title({"id": "A1", "title": "Glass Bloom"}) == "ILAG A1 Glass Bloom"


def test_refire_expects_later_charges_to_be_subtracted():
    c3 = {"status": "failed-after-submit", "fired_at": "2026-09-26T11:15:54+00:00", "balance_before": 30565.0}
    c4 = {"status": "done", "fired_at": "2026-09-26T11:33:00+00:00", "charged": 5.0}
    old = {"status": "done", "fired_at": "2026-09-26T10:54:26+00:00", "charged": 5.0}
    assert fm.expected_balance(c3, {"C3": c3, "C4": c4, "C2": old}) == 30560.0
    unknown = {"status": "submitted", "fired_at": "2026-09-26T11:40:00+00:00"}
    assert fm.expected_balance(c3, {"C3": c3, "X": unknown}) is None


def test_tokens_never_reach_the_ledger():
    body = '{"data":{"access_token":"ya29.a0AX07Cmt-abc_def"}} Bearer eyJhbGciOi.eyJzdWIi.sig ya29.zzz'
    out = fm.redact(body)
    assert "ya29." not in out and "eyJ" not in out and "access_token\":\"ya" not in out
