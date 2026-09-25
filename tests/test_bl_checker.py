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


def _video_with_single_frame_dip(path: Path, content_frames: int = 16, rate: int = 30) -> None:
    """testsrc -> EXACTLY one black frame -> testsrc, frame-accurate (trim by
    frame count, not by duration, so the dip is guaranteed to be one frame
    long regardless of `rate`). `content_frames` is deliberately NOT a
    multiple of the old 4fps grid's sample spacing (rate/4 frames) so the
    regression this reproduces -- EP57 76.37s, a single dropped frame the old
    4fps sampling never landed on -- is faithfully modelled at 30fps too."""
    W, H = ck.EMPTY_FRAME_W, ck.EMPTY_FRAME_H
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=size={W}x{H}:rate={rate}",
        "-f", "lavfi", "-i", f"color=black:size={W}x{H}:rate={rate}",
        "-f", "lavfi", "-i", f"testsrc=size={W}x{H}:rate={rate}",
        "-filter_complex",
        f"[0:v]trim=start_frame=0:end_frame={content_frames},setpts=PTS-STARTPTS[a];"
        f"[1:v]trim=start_frame=0:end_frame=1,setpts=PTS-STARTPTS[b];"
        f"[2:v]trim=start_frame=0:end_frame={content_frames},setpts=PTS-STARTPTS[c];"
        "[a][b][c]concat=n=3:v=1:a=0[v]",
        "-map", "[v]", "-r", str(rate), "-pix_fmt", "yuv420p", str(path),
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


def test_detect_empty_frames_catches_single_frame_dip_at_30fps_but_not_4fps(tmp_path):
    # Reproduces the exact field note: EP57 76.37s, a single dropped/black
    # frame between two normal ones, sitting at a time the old 4fps sample
    # grid (0, 0.25, 0.5, 0.75s...) never lands on.
    video = tmp_path / "dip.mp4"
    _video_with_single_frame_dip(video, content_frames=16, rate=30)
    at_30 = ck.detect_empty_frames(video, fps=30)
    assert at_30, "expected the single black frame to be caught sampling at 30fps"
    assert all(0.5 <= t <= 0.6 for t in at_30)

    at_4 = ck.detect_empty_frames(video, fps=4)
    assert at_4 == [], "a coarse 4fps grid should miss a single 1/30s-long dip -- this is the bug being fixed"


def test_detect_empty_frames_dip_caught_even_when_frame_is_not_flat(monkeypatch, tmp_path):
    # Isolates the MEAN-dip logic from the std<12 flat/black test: a frame
    # whose own std stays well above 12 (it isn't a uniform black frame) but
    # whose mean drops far below both neighbours must still be flagged --
    # "whole-frame mean drops far below both neighbours", not "is flat".
    import numpy as np

    means = np.array([140.0, 142.0, 20.0, 141.0, 139.0])
    stds = np.array([50.0, 48.0, 30.0, 49.0, 47.0])
    monkeypatch.setattr(ck, "_frame_stats", lambda *a, **kw: (means, stds))
    video = tmp_path / "irrelevant.mp4"
    video.write_bytes(b"")
    flagged = ck.detect_empty_frames(video, ignore_before=0.0, fps=30)
    assert flagged == [round(2 / 30, 3)]


def test_detect_empty_frames_no_dip_when_only_one_neighbour_is_darker(monkeypatch, tmp_path):
    # A real cut from a bright plate to a dark one differs from only ONE
    # neighbour, not both -- must not be flagged as a dip.
    import numpy as np

    means = np.array([140.0, 138.0, 30.0, 28.0, 25.0])
    stds = np.array([50.0, 48.0, 40.0, 38.0, 35.0])
    monkeypatch.setattr(ck, "_frame_stats", lambda *a, **kw: (means, stds))
    video = tmp_path / "irrelevant.mp4"
    video.write_bytes(b"")
    assert ck.detect_empty_frames(video, ignore_before=0.0, fps=30) == []


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


# ─────────────────────── 4. one caption style per episode ────────────────

def test_caption_style_signatures_new_generator_is_always_one_style():
    html = 'caption(0.1, 1.08, "hi"); caption(1.15, 4.32, "another line");'
    assert ck.caption_style_signatures(html) == {"caption"}
    assert ck.check_one_caption_style(html) == []


def test_caption_style_signatures_flags_the_ep57_three_kind_bug():
    # Exactly the EP57 defect: assemble.py's addCap() branching its inline
    # look on a `kind` argument -- three different caption looks in one
    # episode, the CEO's own complaint 2026-09-25.
    html = (
        'addCap(0.10, 1.08, "hi", "chip-ff", null);'
        'addCap(1.15, 4.32, "another", "chip-comp", 700);'
        'addCap(4.40, 9.46, "third", "rail", null);'
    )
    assert ck.caption_style_signatures(html) == {"chip-ff", "chip-comp", "rail"}
    assert ck.check_one_caption_style(html) == ["chip-ff", "rail"]


def test_caption_style_signatures_single_addcap_kind_passes():
    html = 'addCap(0.1, 1.0, "a", "rail", null); addCap(1.2, 2.0, "b", "rail", null);'
    assert ck.caption_style_signatures(html) == {"rail"}
    assert ck.check_one_caption_style(html) == []


def test_caption_style_signatures_fallback_to_hand_rolled_inline_style():
    html = ('<div class="cap" id="c1" style="background:red">hi</div>'
            '<div class="cap" id="c2" style="background:blue">yo</div>')
    assert ck.caption_style_signatures(html) == {"background:red", "background:blue"}
    assert ck.check_one_caption_style(html) != []


def test_check_one_caption_style_none_when_no_composition_given():
    assert ck.check_one_caption_style(None) == []
    assert ck.check_one_caption_style("") == []


def test_run_checker_fails_when_composition_has_multiple_caption_styles(tmp_path):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    beats = [_beat("EVID-1", "EVID", {"img": "real/x.png", "box": [200, 300, 400, 500]})]
    html = 'addCap(0.1,1.0,"a","chip-ff",null); addCap(1.2,2.0,"b","rail",null);'
    result = ck.run_checker(video, beats, composition_html=html)
    assert result["pass"] is False
    assert result["extra_caption_styles"] == ["rail"]
    assert result["empty_frames"] == []


# ────────────────────── 5. kinetic text overflow (task-9a4f1029) ─────────

def _kinetic_call(text, css_class="bl-lg", tag=None):
    import json as _json
    call = 'kinetic(760, 0.05, 3.0, [{c:"%s", h:%s}], 0);' % (css_class, _json.dumps(text, ensure_ascii=False))
    return call + f" // {tag}" if tag else call


def test_check_kinetic_overflow_passes_a_short_single_line():
    # measured off final-arm1.mp4 itself (see this check's own header
    # comment): "สรุปแบบไม่โลกสวย" rendered at 660px, well under the 720px
    # safe box, at 82px (.bl-lg).
    html = _kinetic_call("สรุปแบบไม่โลกสวย")
    assert ck.check_kinetic_overflow(html) == []


def test_check_kinetic_overflow_flags_a_long_unsplit_sentence():
    # the exact MAIN-4 line from the pilot (task-1a5eb073): fed as ONE
    # lines[] entry instead of being split, Chrome wrapped it mid-word
    # ("เช็"/"ก") -- this is the defect the gate exists to catch before a
    # render ever runs.
    html = _kinetic_call("เช็กต่อว่ามีใบอนุญาตซื้อขายฟอเร็กซ์ไหม", tag="MAIN-4")
    bad = ck.check_kinetic_overflow(html)
    assert len(bad) == 1
    assert "MAIN-4" in bad[0]


def test_check_kinetic_overflow_ignores_html_tags_when_measuring():
    # the highlighted-word wrapper (<span class="n">...</span>) adds no
    # visible characters -- only the text inside it should count.
    short = ck.check_kinetic_overflow(_kinetic_call('<span class="n">สั้น</span>'))
    assert short == []


def test_check_kinetic_overflow_prefers_the_trailing_tag_comment():
    html = _kinetic_call("เช็กต่อว่ามีใบอนุญาตซื้อขายฟอเร็กซ์ไหม", tag="CURIOSITY-3")
    bad = ck.check_kinetic_overflow(html)
    assert bad == [b for b in bad if b.startswith("CURIOSITY-3:")]


def test_check_kinetic_overflow_falls_back_to_the_line_text_with_no_tag_comment():
    html = _kinetic_call("เช็กต่อว่ามีใบอนุญาตซื้อขายฟอเร็กซ์ไหม")  # no // TAG
    bad = ck.check_kinetic_overflow(html)
    assert len(bad) == 1 and "เช็กต่อ" in bad[0]


def test_check_kinetic_overflow_none_when_no_composition_given():
    assert ck.check_kinetic_overflow(None) == []
    assert ck.check_kinetic_overflow("") == []


def test_check_kinetic_overflow_multiple_lines_in_one_call_each_checked():
    import json as _json
    html = ('kinetic(760, 0.05, 3.0, ['
            '{c:"bl-lg", h:%s}, {c:"bl-lg", h:%s}], 0); // SPLIT-OK'
            % (_json.dumps("สรุปแบบไม่โลกสวย", ensure_ascii=False),
               _json.dumps("เช็กต่อว่ามีใบอนุญาตซื้อขายฟอเร็กซ์ไหม", ensure_ascii=False)))
    bad = ck.check_kinetic_overflow(html)
    assert len(bad) == 1  # only the second (long) entry overflows


def test_run_checker_fails_when_kinetic_line_overflows(tmp_path):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    beats = [_beat("SUMMARY-1", "KIN", {"lines": [["bl-lg", "hi"]]})]
    html = _kinetic_call("เช็กต่อว่ามีใบอนุญาตซื้อขายฟอเร็กซ์ไหม", tag="SUMMARY-1")
    result = ck.run_checker(video, beats, composition_html=html)
    assert result["pass"] is False
    assert result["kinetic_overflow"]


def test_check_kinetic_overflow_flags_the_real_pilot_composition():
    # task-9a4f1029's own gate criterion, verbatim: this exact file (task-
    # 1a5eb073's Arm 1 pilot render) must fail. Skips outside Contabo,
    # where this box-specific media fixture (never in git) doesn't exist.
    pilot = Path("/opt/MoonieXHQ/Work/bl-split-ep57/arm1/build/index.html")
    if not pilot.is_file():
        pytest.skip(f"pilot composition not staged on this box: {pilot}")
    html = pilot.read_text(encoding="utf-8")
    bad = ck.check_kinetic_overflow(html)
    assert bad, "expected the pilot's unsplit kinetic lines to overflow the safe box"
    assert len(bad) >= 10  # 14 of its 15 kinetic lines measure over -- see RUNLOG.md


# ─────────────────────────── runner / CLI ────────────────────────────────

def test_run_checker_pass_true_when_everything_clean(tmp_path):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    beats = [_beat("EVID-1", "EVID", {"img": "real/x.png", "box": [200, 300, 400, 500]})]
    result = ck.run_checker(video, beats)
    assert result["pass"] is True
    assert result == {"pass": True, "empty_frames": [], "out_of_safe_area": [], "text_over_face": [],
                       "credit_missing": [], "extra_caption_styles": [], "kinetic_overflow": []}


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
