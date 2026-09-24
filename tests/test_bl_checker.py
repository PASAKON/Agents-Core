"""Unit tests for tools/bl_checker.py (task-67bb7a11).

Synthetic ffmpeg fixtures only (testsrc/color lavfi sources) -- no real
episode media, no model calls. ffmpeg itself is exercised for real, same
convention as tests/test_bl_scripter.py.

Run via: pytest tests/test_bl_checker.py -q
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools import bl_checker as ck


# ─────────────────────────── fixture builders ────────────────────────────

def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _continuous_video(path: Path, dur: float = 2.0) -> None:
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
          "-i", f"testsrc=size={ck.EMPTY_FRAME_W}x{ck.EMPTY_FRAME_H}:rate={ck.EMPTY_FRAME_FPS}:duration={dur}",
          "-pix_fmt", "yuv420p", str(path)])


def _video_with_black_gap(path: Path, seg: float = 0.6) -> None:
    """testsrc -> black -> testsrc, each `seg` seconds -- a mid-clip gap."""
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=size={ck.EMPTY_FRAME_W}x{ck.EMPTY_FRAME_H}:rate={ck.EMPTY_FRAME_FPS}:duration={seg}",
        "-f", "lavfi", "-i", f"color=black:size={ck.EMPTY_FRAME_W}x{ck.EMPTY_FRAME_H}:rate={ck.EMPTY_FRAME_FPS}:duration={seg}",
        "-f", "lavfi", "-i", f"testsrc=size={ck.EMPTY_FRAME_W}x{ck.EMPTY_FRAME_H}:rate={ck.EMPTY_FRAME_FPS}:duration={seg}",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]", "-map", "[v]",
        "-pix_fmt", "yuv420p", str(path),
    ])


# ─────────────────────────── 1. empty frames ─────────────────────────────

def test_detect_empty_frames_continuous_video_passes(tmp_path):
    video = tmp_path / "continuous.mp4"
    _continuous_video(video)
    assert ck.detect_empty_frames(video) == []


def test_detect_empty_frames_flags_the_black_gap(tmp_path):
    video = tmp_path / "gap.mp4"
    _video_with_black_gap(video, seg=0.6)
    empty = ck.detect_empty_frames(video)
    assert empty, "expected the 0.6s black gap to be detected"
    # the gap sits at t in [0.6, 1.2) -- well past the 0.25s grace window
    assert all(t >= 0.5 for t in empty)
    assert all(t <= 1.3 for t in empty)


def test_detect_empty_frames_ignores_before_grace_window(tmp_path):
    # a black clip whose only "empty" content is inside the first 0.25s
    # grace window should report nothing.
    video = tmp_path / "brief_black_then_content.mp4"
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=black:size={ck.EMPTY_FRAME_W}x{ck.EMPTY_FRAME_H}:rate={ck.EMPTY_FRAME_FPS}:duration=0.2",
        "-f", "lavfi", "-i", f"testsrc=size={ck.EMPTY_FRAME_W}x{ck.EMPTY_FRAME_H}:rate={ck.EMPTY_FRAME_FPS}:duration=1.0",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]",
        "-pix_fmt", "yuv420p", str(video),
    ])
    assert ck.detect_empty_frames(video) == []


# ─────────────────────────── 2. safe area / credit ───────────────────────

def _beat(tag, mode, extra):
    return {"tag": tag, "t0": 0.0, "t1": 1.0, "mode": mode, "extra": extra}


def test_check_out_of_safe_area_box_inside_passes():
    beats = [_beat("EVID-1", "EVID", {"img": "real/x.png", "box": [200, 300, 400, 500]})]
    assert ck.check_out_of_safe_area(beats) == []


def test_check_out_of_safe_area_box_near_edge_fails():
    # x=950..1070 pokes past the right safe margin (canvas right-safe=1026
    # at the default 5% side margin) -- the task's own "caption box outside
    # the safe area -> fails" scenario.
    beats = [_beat("COMP-1", "COMP", {"img": "real/x.png", "box": [950, 200, 120, 100]})]
    assert ck.check_out_of_safe_area(beats) == ["COMP-1"]


def test_check_out_of_safe_area_ignores_modes_without_a_box():
    beats = [_beat("KIN-1", "KIN", {"lines": [["bl-lg", "hi"]]}),
             _beat("FF-1", "FF", {"cap": "hi"})]
    assert ck.check_out_of_safe_area(beats) == []


def test_check_out_of_safe_area_landscape_source_uses_placement_transform():
    # native 1374x868 (landscape) -> scaled to canvas width 1080, scale~0.786,
    # centered vertically. A box already safely inside the scaled/centered
    # placement should pass.
    beats = [_beat("EVID-2", "EVID", {"img": "real/x.jpg", "native_w": 1374, "native_h": 868,
                                       "box": [100, 100, 800, 300]})]
    assert ck.check_out_of_safe_area(beats) == []


def test_check_credit_missing_passes_with_room_above_evidence():
    beats = [_beat("HOOK-4", "COMP", {"img": "third-party/x.jpg", "box": [100, 260, 870, 140],
                                       "native_h": 1350, "credit": "crédit"})]
    assert ck.check_credit_missing(beats) == []


def test_check_credit_missing_fails_when_evidence_starts_near_the_top():
    beats = [_beat("BAD-1", "COMP", {"img": "third-party/x.jpg", "box": [50, 10, 500, 100],
                                      "credit": "credit"})]
    assert ck.check_credit_missing(beats) == ["BAD-1"]


def test_check_credit_missing_ignores_beats_without_credit():
    beats = [_beat("EVID-1", "EVID", {"img": "real/x.png", "box": [50, 10, 500, 100]})]
    assert ck.check_credit_missing(beats) == []


# ─────────────────────────── 3. text over face ───────────────────────────

def test_check_text_over_face_skips_when_no_face_box_given():
    beats = [_beat("FF-1", "FF", {"cap": "hi"})]
    assert ck.check_text_over_face(beats, None) == []


def test_check_text_over_face_flags_ff_caption_intersecting_face_box():
    beats = [_beat("FF-1", "FF", {"cap": "hi"})]
    band = ck.caption_band("FF")
    face_box = (300, band[0] + 5, 400, 50)  # sits inside the FF caption band
    assert ck.check_text_over_face(beats, face_box) == ["FF-1"]


def test_check_text_over_face_no_overlap_when_face_box_elsewhere():
    beats = [_beat("FF-1", "FF", {"cap": "hi"})]
    face_box = (300, 50, 400, 50)  # near the top, far from the FF chest band
    assert ck.check_text_over_face(beats, face_box) == []


# ─────────────────────────── runner / CLI ────────────────────────────────

def test_run_checker_pass_true_when_everything_clean(tmp_path):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    beats = [_beat("EVID-1", "EVID", {"img": "real/x.png", "box": [200, 300, 400, 500]})]
    result = ck.run_checker(video, beats)
    assert result["pass"] is True
    assert result == {"pass": True, "empty_frames": [], "out_of_safe_area": [], "text_over_face": [], "credit_missing": []}


def test_run_checker_pass_false_when_safe_area_fails(tmp_path):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    beats = [_beat("COMP-1", "COMP", {"img": "real/x.png", "box": [950, 200, 120, 100]})]
    result = ck.run_checker(video, beats)
    assert result["pass"] is False
    assert result["out_of_safe_area"] == ["COMP-1"]
    assert result["empty_frames"] == []


def test_main_exit_code_matches_pass(tmp_path, capsys):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    beats_path = tmp_path / "beats.json"
    import json
    beats_path.write_text(json.dumps([_beat("EVID-1", "EVID", {"img": "real/x.png", "box": [200, 300, 400, 500]})]))
    rc = ck.main(["--video", str(video), "--beats", str(beats_path)])
    assert rc == 0

    bad_beats_path = tmp_path / "bad_beats.json"
    bad_beats_path.write_text(json.dumps([_beat("COMP-1", "COMP", {"img": "real/x.png", "box": [950, 200, 120, 100]})]))
    rc = ck.main(["--video", str(video), "--beats", str(bad_beats_path)])
    assert rc == 1
