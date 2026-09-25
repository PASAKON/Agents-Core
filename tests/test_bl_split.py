"""Unit tests for tools/bl_split.py (task-1678d38e, docs/ops/bl-split-ab-2026-09-25).

Pure-Python tests exercise the dead-air walk/selection logic directly
against synthetic pause lists (fast, deterministic). One end-to-end test
runs real ffmpeg silencedetect against a synthetic audio fixture, same
convention as tests/test_bl_checker.py.

Run via: pytest tests/test_bl_split.py -q
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools import bl_split as sp


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


# ─────────────────────────── parse_silencedetect ─────────────────────────

def test_parse_silencedetect_pairs_start_and_end():
    text = (
        "[silencedetect @ 0x1] silence_start: 2.65773\n"
        "[silencedetect @ 0x1] silence_end: 3.21993 | silence_duration: 0.5622\n"
        "[silencedetect @ 0x1] silence_start: 5.07955\n"
        "[silencedetect @ 0x1] silence_end: 5.68125 | silence_duration: 0.6017\n"
    )
    assert sp.parse_silencedetect(text) == [(2.65773, 3.21993), (5.07955, 5.68125)]


def test_parse_silencedetect_drops_unmatched_trailing_start():
    text = (
        "[silencedetect @ 0x1] silence_start: 2.0\n"
        "[silencedetect @ 0x1] silence_end: 2.6 | silence_duration: 0.6\n"
        "[silencedetect @ 0x1] silence_start: 9.0\n"  # runs to EOF, no matching end
    )
    assert sp.parse_silencedetect(text) == [(2.0, 2.6)]


def test_parse_silencedetect_empty_text():
    assert sp.parse_silencedetect("") == []


# ─────────────────────────── frame_floor ──────────────────────────────────

def test_frame_floor_snaps_down_to_grid():
    assert sp.frame_floor(30.3, 30) == 30.3
    assert sp.frame_floor(30.31, 30) == pytest.approx(30.3)
    assert sp.frame_floor(30.3666, 30) == pytest.approx(30.3333333, abs=1e-4)


def test_frame_floor_epsilon_guards_float_error():
    # 30.3 stored as 30.299999999999997 must still floor to 30.3, not 30.2666...
    assert sp.frame_floor(30.3 - 1e-9, 30) == pytest.approx(30.3)


# ─────────────────────────── candidates / forbidden ───────────────────────

def test_candidate_pauses_filters_below_threshold():
    pauses = [(0.0, 0.3), (1.0, 1.44), (2.0, 2.45), (3.0, 4.0)]
    cands = sp.candidate_pauses(pauses, min_dur=0.45)
    assert cands == [(2.0, 2.45), (3.0, 4.0)]


def test_is_forbidden_overlap():
    blocks = [(129.38, 141.48)]
    assert sp.is_forbidden((135.0, 135.5), blocks) is True   # fully inside
    assert sp.is_forbidden((128.0, 130.0), blocks) is True   # straddles the start
    assert sp.is_forbidden((141.0, 142.0), blocks) is True   # straddles the end
    assert sp.is_forbidden((10.0, 10.5), blocks) is False    # nowhere near


def test_load_blocks_accepts_pairs_and_dicts(tmp_path):
    p1 = tmp_path / "pairs.json"
    p1.write_text(json.dumps([[1.0, 2.0], [3.0, 4.0]]))
    assert sp.load_blocks(p1) == [(1.0, 2.0), (3.0, 4.0)]

    p2 = tmp_path / "dicts.json"
    p2.write_text(json.dumps([{"t0": 129.38, "t1": 141.48, "note": "x"}]))
    assert sp.load_blocks(p2) == [(129.38, 141.48)]

    assert sp.load_blocks(None) == []


# ─────────────────────────── select_cut_points (the walk) ────────────────

def test_select_cut_points_picks_longest_in_25_50_window():
    # two candidates in [25,50]: a shorter pause at 30.2 and a longer one at
    # 40.1 -- must pick the LONGER one even though it's further away.
    candidates = [(29.9, 30.5), (39.5, 40.7)]  # durations 0.6 / 1.2
    cuts = sp.select_cut_points(candidates, [])
    assert len(cuts) == 1
    assert cuts[0] == sp.frame_floor((39.5 + 40.7) / 2)


def test_select_cut_points_falls_back_past_50s_when_window_empty():
    # nothing in [25,50], but a candidate exists further out (60s) -- fallback
    # must still pick it rather than stopping.
    candidates = [(59.5, 60.3)]
    cuts = sp.select_cut_points(candidates, [])
    assert cuts == [sp.frame_floor((59.5 + 60.3) / 2)]


def test_select_cut_points_skips_forbidden_pause_for_next_longest_allowed():
    # the longest candidate in-window sits inside a forbidden block; the
    # walk must fall through to the next-longest ALLOWED one, not skip the
    # window/give up.
    candidates = [(35.0, 37.0), (40.0, 40.6)]  # durations 2.0 (forbidden) / 0.6 (allowed)
    blocks = [(34.0, 38.0)]
    cuts = sp.select_cut_points(candidates, blocks)
    assert cuts == [sp.frame_floor((40.0 + 40.6) / 2)]


def test_select_cut_points_walks_multiple_segments():
    # three well-separated candidates ~30s apart -> three cuts, each measured
    # from the PREVIOUS cut, not from t=0.
    candidates = [(29.5, 30.5), (60.0, 61.0), (91.0, 92.0)]
    cuts = sp.select_cut_points(candidates, [])
    assert len(cuts) == 3
    assert cuts[0] == sp.frame_floor(30.0)
    assert cuts[1] == sp.frame_floor(60.5)
    assert cuts[2] == sp.frame_floor(91.5)


def test_select_cut_points_no_candidates_returns_empty():
    assert sp.select_cut_points([], []) == []


def test_select_cut_points_stops_when_nothing_past_min_gap():
    # a single candidate sits BEFORE the +25s floor from t=0 -- never usable.
    candidates = [(10.0, 10.6)]
    assert sp.select_cut_points(candidates, []) == []


# ─────────────────────────── enforce_min_tail (task-99f3d2e8) ─────────────

def test_enforce_min_tail_drops_a_short_final_cut():
    # cuts at 39.3/65.83/104.53/145.9, episode ends 153.0333 -- the last
    # segment (145.9-153.0333 = 7.13s) is short of the 20s default and must
    # merge into the one before it (104.53-153.0333).
    cuts = [39.3, 65.8333, 104.5333, 145.9]
    out = sp.enforce_min_tail(cuts, 153.0514, min_seg=20.0)
    assert out == [39.3, 65.8333, 104.5333]


def test_enforce_min_tail_keeps_cuts_when_tail_already_long_enough():
    cuts = [30.0, 60.0]
    out = sp.enforce_min_tail(cuts, 90.0, min_seg=20.0)
    assert out == [30.0, 60.0]  # tail is 30.0s, well over 20s


def test_enforce_min_tail_can_cascade_past_multiple_cuts():
    # a pathological case: every cut sits within min_seg of the end -- must
    # keep popping until the tail clears the bar or no cuts remain.
    cuts = [10.0, 15.0, 18.0]
    out = sp.enforce_min_tail(cuts, 20.0, min_seg=20.0)
    assert out == []  # even the first cut leaves only a 10.0s tail


def test_enforce_min_tail_no_cuts_is_a_noop():
    assert sp.enforce_min_tail([], 15.0, min_seg=20.0) == []


def test_enforce_min_tail_default_matches_plan_min_seg_constant():
    assert sp.MIN_SEG_TAIL == 20.0


def test_split_episode_merges_short_tail_end_to_end(tmp_path):
    # same synthetic shape as test_split_episode_end_to_end_with_real_audio
    # but with a SECOND, later silence placed so the walk would otherwise
    # produce a short final segment -- split_episode() must merge it away
    # by default (min_seg=20.0).
    audio = tmp_path / "audio.mp3"
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=0.6",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=25",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=0.6",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
        "-filter_complex", "[0:a][1:a][2:a][3:a][4:a]concat=n=5:v=0:a=1[a]", "-map", "[a]",
        str(audio),
    ])
    # silences at ~30.0s and ~55.6s -- the second one is only 10s from the
    # episode's own end (~66.2s), well short of the 20s default tail.
    timings = {"L1": (5.0, 6.0), "L2": (50.0, 51.0), "L3": (60.0, 61.0)}
    plan = sp.split_episode(audio, timings)
    assert len(plan["cuts"]) == 1  # the second candidate's cut was dropped
    assert len(plan["segments"]) == 2
    assert plan["min_seg_tail_s"] == 20.0


# ─────────────────────────── SCRIPT.tsv / timings.tsv ─────────────────────

def test_load_timings_parses_header_and_rows(tmp_path):
    p = tmp_path / "timings.tsv"
    p.write_text("tag\tt0\tt1\nHOOK-1\t0.18\t2.64\nHOOK-2\t3.08\t5.54\n", encoding="utf-8")
    timings = sp.load_timings(p)
    assert timings == {"HOOK-1": (0.18, 2.64), "HOOK-2": (3.08, 5.54)}


def test_load_script_five_columns_no_header(tmp_path):
    p = tmp_path / "SCRIPT.tsv"
    p.write_text("HOOK-1\tข้อความ\tshot-a\tshow\tnote here\nHOOK-2\ttext2\t\tavatar\t\n", encoding="utf-8")
    script = sp.load_script(p)
    assert script["HOOK-1"] == {"text": "ข้อความ", "shot": "shot-a", "verb": "show", "note": "note here"}
    assert script["HOOK-2"]["shot"] == ""


# ─────────────────────────── build_segments ────────────────────────────────

def test_build_segments_assigns_tags_by_own_t0_and_computes_frames():
    timings = {"A": (0.0, 1.0), "B": (5.0, 6.0), "C": (32.0, 33.0), "D": (40.0, 41.0)}
    cuts = [30.0]
    segs = sp.build_segments(cuts, 45.0, timings, fps=30)
    assert [s["id"] for s in segs] == ["seg01", "seg02"]
    assert [l["tag"] for l in segs[0]["lines"]] == ["A", "B"]
    assert [l["tag"] for l in segs[1]["lines"]] == ["C", "D"]
    assert segs[0]["t0"] == 0.0 and segs[0]["t1"] == 30.0
    assert segs[0]["frame_count"] == 900
    assert segs[1]["t0"] == 30.0 and segs[1]["t1"] == 45.0
    assert segs[1]["frame_count"] == 450


def test_build_segments_includes_script_text_when_given():
    timings = {"A": (0.0, 1.0)}
    script = {"A": {"text": "hi", "shot": "", "verb": "show", "note": ""}}
    segs = sp.build_segments([], 10.0, timings, script, fps=30)
    assert segs[0]["lines"][0]["text"] == "hi"


def test_build_segments_no_cuts_single_segment():
    timings = {"A": (0.0, 1.0), "B": (5.0, 6.0)}
    segs = sp.build_segments([], 10.0, timings, fps=30)
    assert len(segs) == 1
    assert segs[0]["t0"] == 0.0
    assert segs[0]["t1"] == 10.0


# ─────────────────────────── end-to-end (real ffmpeg) ─────────────────────

def test_split_episode_end_to_end_with_real_audio(tmp_path):
    # ~62s of tone with one deliberate 0.6s silence near t=30s -- exercises
    # the real default WALK_MIN_GAP/WALK_MAX_GAP window (25-50s) with real
    # ffmpeg silencedetect + ffprobe, not just the pure-python walk logic.
    audio = tmp_path / "audio.mp3"
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=0.6",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=31",
        "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]", "-map", "[a]",
        str(audio),
    ])
    timings = {"L1": (5.0, 6.0), "L2": (50.0, 51.0)}
    plan = sp.split_episode(audio, timings)
    assert plan["total_duration"] == pytest.approx(61.6, abs=0.2)
    assert len(plan["cuts"]) == 1
    # the silence sits at [30.0, 30.6) -- midpoint ~30.3s
    assert plan["cuts"][0] == pytest.approx(30.3, abs=0.05)
    assert len(plan["segments"]) == 2
    assert [l["tag"] for l in plan["segments"][0]["lines"]] == ["L1"]
    assert [l["tag"] for l in plan["segments"][1]["lines"]] == ["L2"]


# ─────────────────────────── CLI ───────────────────────────────────────────

def test_main_writes_segments_json(tmp_path):
    script_p = tmp_path / "SCRIPT.tsv"
    script_p.write_text("A\ttext a\t\tshow\t\nB\ttext b\t\tshow\t\n", encoding="utf-8")
    timings_p = tmp_path / "timings.tsv"
    timings_p.write_text("tag\tt0\tt1\nA\t0.0\t1.0\nB\t40.0\t41.0\n", encoding="utf-8")

    audio = tmp_path / "audio.mp3"
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=0.6",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=15",
        "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]", "-map", "[a]",
        str(audio),
    ])
    out_p = tmp_path / "segments.json"
    # --min-seg 0 disables the short-tail merge (its own default behaviour
    # is covered by the enforce_min_tail tests above) -- this test is only
    # about the CLI plumbing, and the ~15.3s tail here is deliberately
    # shorter than the 20s default so it stays a useful regression case.
    rc = sp.main([str(audio), "--script", str(script_p), "--timings", str(timings_p),
                  "-o", str(out_p), "--min-seg", "0"])
    assert rc == 0
    data = json.loads(out_p.read_text(encoding="utf-8"))
    assert len(data["segments"]) == 2
    assert data["segments"][0]["lines"][0]["text"] == "text a"
