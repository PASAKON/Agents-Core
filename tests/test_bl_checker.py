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


# ═══════════════════════════════════════════════════════════════════════════
# Arm A -- the headline plate (task-406c21f3). Schema, per-arm mask, plate checks.
# A bare list of beats (arm B) is covered by every test above, untouched.
# ═══════════════════════════════════════════════════════════════════════════

import json  # noqa: E402

LINE_1 = "โบรกเกอร์ไม่อยากให้คุณรู้"          # 25 characters, 19 visual
LINE_2 = "Weltrade เปิดบัญชีง่ายจริงไหม"      # 29 characters, 24 visual
RED = "ไม่อยากให้คุณรู้"


def _headline(**over):
    h = {"lines": [LINE_1, LINE_2], "red": RED, "bug_side": "left",
         "backdrop": [{"t0": 0.0, "src": "real/a.png"}, {"t0": 1.0, "src": "real/b.png"},
                      {"t0": 2.0, "src": "real/c.png"}]}
    h.update(over)
    return h


def _parsed(**over):
    return ck.parse_headline(_headline(**over))


# ── schema: list vs object ──

def test_split_beats_doc_bare_list_is_arm_b():
    beats = [_beat("A", "KIN", {})]
    assert ck.split_beats_doc(beats) == (beats, None)


def test_split_beats_doc_object_is_arm_a():
    beats = [_beat("A", "COMP", {"cap": "x"})]
    got_beats, headline = ck.split_beats_doc({"headline": _headline(), "beats": beats})
    assert got_beats == beats
    assert headline["lines"] == [LINE_1, LINE_2] and headline["bug_side"] == "left"


@pytest.mark.parametrize("doc", [
    {"headline": _headline()},                                   # no beats
    {"beats": []},                                               # no headline
    {"headline": _headline(), "beats": {}},                      # beats not a list
    {"headline": _headline(), "beats": [], "extra": 1},          # unknown key
    "beats.json", 7, None,
])
def test_split_beats_doc_refuses_anything_else(doc):
    with pytest.raises(ck.ArmAError):
        ck.split_beats_doc(doc)


def test_bug_side_defaults_to_right():
    raw = _headline()
    del raw["bug_side"]
    assert ck.parse_headline(raw)["bug_side"] == "right"


def test_backdrop_is_sorted_by_t0():
    b = _headline()["backdrop"]
    assert [e["t0"] for e in _parsed(backdrop=[b[2], b[0], b[1]])["backdrop"]] == [0.0, 1.0, 2.0]


# ── schema: two lines, 30 characters, counted the way _visual_len counts ──

@pytest.mark.parametrize("lines", [[LINE_1], [LINE_1, LINE_2, LINE_1], [LINE_1, ""], [LINE_1, 7], "ab"])
def test_headline_needs_exactly_two_non_empty_string_lines(lines):
    with pytest.raises(ck.ArmAError, match="exactly 2 non-empty strings"):
        _parsed(lines=lines, red="ก")


def test_line_limit_counts_visual_characters_not_code_points():
    thirty = "ก" * 30
    with_marks = "ก" * 30 + "ิ"                    # 31 code points, 30 visual (ิ is category Mn)
    assert len(with_marks) == 31 and ck._visual_len(with_marks) == 30
    assert _parsed(lines=[with_marks, LINE_2], red=RED.replace(RED, "ไหม"))["lines"][0] == with_marks
    assert _parsed(lines=[thirty, LINE_2], red="ไหม")["lines"][0] == thirty


def test_line_of_31_visual_characters_is_refused():
    with pytest.raises(ck.ArmAError, match=r"line 1 is 31 characters.*limit is 30"):
        _parsed(lines=["ก" * 31, LINE_2], red="ไหม")


def test_second_line_over_the_limit_is_refused_and_named():
    with pytest.raises(ck.ArmAError, match="line 2 is 31 characters"):
        _parsed(lines=[LINE_1, "ข" * 31], red="ไม่อยาก")


def test_a_line_holding_a_line_break_is_refused():
    with pytest.raises(ck.ArmAError, match="line break"):
        _parsed(lines=["ab\ncd", LINE_2], red="ไหม")


# ── schema: `red` is an exact substring, occurring exactly once ──

def test_red_is_found_once_across_both_lines():
    assert _parsed(red="Weltrade")["red"] == "Weltrade"
    assert _parsed()["red"] == RED


def test_red_missing_key_is_refused():
    raw = _headline()
    del raw["red"]
    with pytest.raises(ck.ArmAError, match="headline.red is required"):
        ck.parse_headline(raw)


@pytest.mark.parametrize("red", ["", "   ", None, 3])
def test_red_blank_or_not_a_string_is_refused(red):
    with pytest.raises(ck.ArmAError, match="headline.red is required"):
        _parsed(red=red)


def test_red_occurring_in_neither_line_is_refused():
    with pytest.raises(ck.ArmAError, match="occurs in neither line"):
        _parsed(red="ไม่มีคำนี้")


def test_red_occurring_twice_in_one_line_is_refused_as_ambiguous():
    with pytest.raises(ck.ArmAError, match="ambiguous: it occurs 2 times"):
        _parsed(lines=["คนเทรดคนเทรด", LINE_2], red="คนเทรด")


def test_red_occurring_once_in_each_line_is_refused_as_ambiguous():
    with pytest.raises(ck.ArmAError, match="ambiguous: it occurs 2 times"):
        _parsed(lines=["ผลลัพธ์จริง", "ผลลัพธ์ปลอม"], red="ผลลัพธ์")


def test_overlapping_matches_count_as_ambiguous():
    with pytest.raises(ck.ArmAError, match="ambiguous"):
        _parsed(lines=["aaa", "bcd"], red="aa")


def test_red_that_cuts_a_thai_syllable_is_refused():
    with pytest.raises(ck.ArmAError, match="cuts a Thai syllable"):
        _parsed(red="ไม")                         # leaves the tone mark ่ outside the span
    with pytest.raises(ck.ArmAError, match="cuts a Thai syllable"):
        _parsed(red="่อยาก")                       # starts on a tone mark


# ── schema: bug_side, backdrop, unknown keys ──

def test_bug_side_must_be_left_or_right():
    with pytest.raises(ck.ArmAError, match="bug_side"):
        _parsed(bug_side="top")


def test_unknown_headline_key_is_refused():
    with pytest.raises(ck.ArmAError, match="unknown key"):
        _parsed(red_word=3)


@pytest.mark.parametrize("backdrop", [
    [],
    [{"t0": 0.0, "src": "real/a.png"}, {"t0": 1.0, "src": "real/b.png"}],                         # two
    [{"t0": 0.0, "src": "real/a.png"}] * 4,                                                       # four
    [{"t0": 0.0, "src": "real/a.png"}, {"t0": 1.0, "src": "real/b.png"}, {"t0": 2.5, "src": "real/c.png"}],
    [{"t0": 0.0, "src": "real/a.png"}, {"t0": 1.0, "src": "real/b.png"}, {"t0": 1.0, "src": "real/c.png"}],
    [{"t0": 0.0, "src": "real/a.png"}, {"t0": 1.0, "src": "real/b.png"}, {"t0": 2.0}],           # no src
    [{"t0": 0.0, "src": "real/a.png"}, {"t0": 1.0, "src": "real/b.png"}, {"t0": "2", "src": "real/c.png"}],
    "real/a.png",
])
def test_backdrop_must_be_three_entries_at_0_1_2(backdrop):
    with pytest.raises(ck.ArmAError, match="backdrop"):
        _parsed(backdrop=backdrop)


@pytest.mark.parametrize("src", ["", "real/", "a.png", "media/real/a.png", "/real/a.png", "real/../x.png",
                                  "real\\a.png", "broll/S01.mp4", 5])
def test_backdrop_src_must_sit_under_real(src):
    b = _headline()["backdrop"]
    with pytest.raises(ck.ArmAError, match="backdrop"):
        _parsed(backdrop=[b[0], b[1], {"t0": 2.0, "src": src}])


# ── geometry ──

def test_layout_font_shrinks_with_the_widest_line_and_caps_at_88():
    short = ck.headline_layout(_parsed(lines=["รู้ก่อนเสียเงิน", "เปิดบัญชีง่าย"], red="เสียเงิน"))
    assert short["font_px"] == 88 and short["box"] == (120, 276, 840, 220)
    assert short["text"][0] > 120 and short["text"][0] + short["text"][2] < 960          # centred, narrower than the box
    assert abs((short["text"][0] + short["text"][2] / 2) - 540) < 0.01
    full = ck.headline_layout(_parsed(lines=["ก" * 30, LINE_2], red="ไหม"))
    assert full["font_px"] == 48
    assert full["text"][2] <= 840 + 0.01


def test_a_default_headline_sits_inside_the_cmo_band_of_12_to_26_percent():
    for lines, red in ((["รู้ก่อนเสียเงิน", "เปิดบัญชีง่าย"], "เสียเงิน"), ([LINE_1, LINE_2], RED),
                       (["ก" * 30, "ข" * 30], "ก" * 30)):
        _, y, _, h = ck.headline_layout(_parsed(lines=lines, red=red))["box"]
        assert 0.12 * ck.CANVAS_H <= y and (y + h) <= 0.26 * ck.CANVAS_H


def test_bug_zone_right_is_the_zone_the_mask_has_always_used():
    x, y, w, h = ck.bug_zone("right")
    assert (x, y) == (pytest.approx(1080 * .55), pytest.approx(1920 * .12))
    assert (x + w, y + h) == (pytest.approx(1080), pytest.approx(1920 * .24))


# ── the per-arm empty-frame mask ──

def _box_on_black(path, x, y, w, h, dur=1.0):
    """A black clip with one white box standing on every frame (frame px at EMPTY_FRAME_W x EMPTY_FRAME_H)."""
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
          "-i", f"color=black:size={ck.EMPTY_FRAME_W}x{ck.EMPTY_FRAME_H}:rate={ck.EMPTY_FRAME_FPS}:duration={dur}",
          "-vf", f"drawbox=x={x}:y={y}:w={w}:h={h}:color=white:t=fill", "-pix_fmt", "yuv420p", str(path)])


# frame px = canvas px / 4. Inside bug_zone("left") = canvas (100,176,400,86); inside the right bug zone = canvas
# x >= 594, y 230-461; the plate box of an 88 px headline = canvas (120,276,840,220).
LEFT_BUG_BOX = (30, 48, 80, 14)
RIGHT_BUG_BOX = (170, 70, 80, 30)
PLATE_BOX = (60, 80, 120, 30)


def test_arm_b_mask_hides_a_standing_box_in_the_top_right_only(tmp_path):
    right, left = tmp_path / "right.mp4", tmp_path / "left.mp4"
    _box_on_black(right, *RIGHT_BUG_BOX)
    _box_on_black(left, *LEFT_BUG_BOX)
    assert ck.detect_empty_frames(right, ignore_before=0.0), "arm B masks the right bug: the frame is empty"
    assert ck.detect_empty_frames(left, ignore_before=0.0) == [], "arm B does not mask the left: not empty to it"


def test_arm_a_mask_follows_the_bug_to_the_top_left(tmp_path):
    right, left = tmp_path / "right.mp4", tmp_path / "left.mp4"
    _box_on_black(right, *RIGHT_BUG_BOX)
    _box_on_black(left, *LEFT_BUG_BOX)
    assert ck.detect_empty_frames(left, ignore_before=0.0, bug_side="left"), "arm A masks the left bug"
    assert ck.detect_empty_frames(right, ignore_before=0.0, bug_side="left") == [], \
        "the right zone is not masked in arm A: a bright box there is real content"


def test_arm_a_mask_hides_the_headline_plate_from_the_empty_frame_gate(tmp_path):
    video = tmp_path / "plate.mp4"
    _box_on_black(video, *PLATE_BOX)
    assert ck.detect_empty_frames(video, ignore_before=0.0, bug_side="left") == [], "unmasked, white text on black looks busy"
    h = _parsed(lines=["รู้ก่อนเสียเงิน", "เปิดบัญชีง่าย"], red="เสียเงิน")
    assert ck.detect_empty_frames(video, ignore_before=0.0, **ck.arm_mask_kwargs(h)), \
        "masked, the frame is empty and is flagged"


def test_arm_mask_kwargs_is_empty_for_arm_b():
    assert ck.arm_mask_kwargs(None) == {}
    kw = ck.arm_mask_kwargs(_parsed())
    assert kw["bug_side"] == "left" and kw["extra_zones"] == (ck.headline_layout(_parsed())["box"],)


def test_arm_b_detect_empty_frames_still_calls_frame_stats_with_four_arguments(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(ck, "_frame_stats", lambda *a, **kw: seen.append((a[1:], kw)) or None)
    ck.detect_empty_frames(tmp_path / "x.mp4")
    assert seen == [((ck.EMPTY_FRAME_FPS, ck.EMPTY_FRAME_W, ck.EMPTY_FRAME_H), {})]


# ── plate geometry checks ──

def _evid(tag, box, **extra):
    return _beat(tag, "EVID", {"img": "real/x.png", "native_w": 1080, "native_h": 1920, "box": box, **extra})


def test_headline_clear_of_everything_passes():
    beats = [_evid("EVID-1", [100, 800, 600, 500])]
    assert ck.check_headline(_parsed(), beats) == []


def test_headline_with_the_bug_on_the_right_overlaps_it():
    assert ck.check_headline(_parsed(bug_side="right"), []) == ["overlaps_bug_right"]


def test_headline_outside_the_safe_area_is_flagged(monkeypatch):
    monkeypatch.setattr(ck, "HEADLINE_BOX_LEFT", 20)           # text now starts left of the 54 px margin
    assert "outside_safe_area" in ck.check_headline(_parsed(lines=["ก" * 30, LINE_2], red="ไหม"), [])


def test_headline_on_top_of_an_evid_content_box_is_flagged_by_tag():
    beats = [_evid("EVID-1", [100, 800, 600, 500]), _evid("EVID-2", [100, 300, 400, 100])]
    assert ck.check_headline(_parsed(), beats) == ["overlaps_evidence:EVID-2"]


def test_headline_on_top_of_a_comp_content_box_is_flagged_too():
    beats = [_beat("COMP-1", "COMP", {"img": "real/x.png", "native_w": 1080, "native_h": 1920, "box": [100, 300, 400, 100]})]
    assert ck.check_headline(_parsed(), beats) == ["overlaps_evidence:COMP-1"]


def test_a_beat_with_no_box_declares_no_content_area():
    beats = [_beat("EVID-1", "EVID", {"img": "real/x.png"}), _beat("KIN-1", "KIN", {"lines": []})]
    assert ck.check_headline(_parsed(), beats) == []


def test_touching_edges_do_not_overlap():
    text = ck.headline_layout(_parsed())["text"]
    bottom = text[1] + text[3]
    beats = [_evid("EVID-1", [100, bottom, 600, 100])]
    assert ck.check_headline(_parsed(), beats) == []
    assert ck.check_headline(_parsed(), [_evid("EVID-1", [100, bottom - 1, 600, 100])]) == ["overlaps_evidence:EVID-1"]


def test_headline_on_top_of_a_credit_chip_is_flagged(monkeypatch):
    beats = [_evid("EVID-1", [100, 800, 600, 500], credit="WikiFX")]
    assert ck.check_headline(_parsed(), beats) == []           # the chip sits at y 40, the plate at 276
    monkeypatch.setattr(ck, "HEADLINE_TOP", 50)
    assert "overlaps_credit:EVID-1" in ck.check_headline(_parsed(), beats)


# ── text over face: the plate is text on every frame ──

FACE_UNDER_PLATE = (300.0, 300.0, 200.0, 150.0)


def test_text_over_face_arm_a_flags_every_face_beat_when_the_plate_meets_the_face():
    beats = [_beat("COMP-1", "COMP", {"img": "real/x.png"}), _beat("FF-1", "FF", {}), _beat("KIN-1", "KIN", {})]
    assert ck.check_text_over_face(beats, FACE_UNDER_PLATE) == []                      # arm B: no caption, no hit
    assert ck.check_text_over_face(beats, FACE_UNDER_PLATE, _parsed()) == ["COMP-1", "FF-1"]


def test_text_over_face_arm_a_leaves_a_face_below_the_plate_alone():
    beats = [_beat("COMP-1", "COMP", {"img": "real/x.png"})]
    assert ck.check_text_over_face(beats, (300.0, 900.0, 200.0, 300.0), _parsed()) == []


def test_text_over_face_arm_a_still_applies_the_caption_rule():
    beats = [_beat("COMP-1", "COMP", {"img": "real/x.png", "cap": "x"})]
    face_at_caption = (300.0, 1250.0, 200.0, 100.0)
    assert ck.check_text_over_face(beats, face_at_caption) == ["COMP-1"]
    assert ck.check_text_over_face(beats, face_at_caption, _parsed()) == ["COMP-1"]


# ── the composed HTML carries the plate where the layout says ──

def _plate_html(h, **over):
    lay = ck.headline_layout(h)
    left, top, width, height = lay["box"]
    style = {"left": f"{left}px", "top": f"{top}px", "width": f"{width}px", "height": f"{height}px",
             "font-size": f"{lay['font_px']}px", "line-height": f"{lay['line_h']}px", **over}
    css = ";".join(f"{k}:{v}" for k, v in style.items())
    bug = ('<style id="arm-a-bug">#bug{left:120px;right:auto;top:190px}</style>' if h["bug_side"] == "left" else "")
    return f'<html>{bug}<div id="hl" class="hl" style="{css}">x</div></html>'


def test_check_headline_plate_clean_when_the_html_matches():
    h = _parsed()
    assert ck.check_headline_plate(h, _plate_html(h)) == []


def test_check_headline_plate_flags_a_missing_or_duplicated_plate():
    h = _parsed()
    assert ck.check_headline_plate(h, "<html></html>") == ["plate_count=0"]
    assert ck.check_headline_plate(h, _plate_html(h) + _plate_html(h)) == ["plate_count=2"]


def test_check_headline_plate_flags_a_plate_that_moved():
    h = _parsed()
    problems = ck.check_headline_plate(h, _plate_html(h, top="500px"))
    assert problems == ["plate_top=500px!=276px"]


def test_check_headline_plate_flags_a_missing_or_misplaced_bug_override():
    h = _parsed()
    bug_style = '<style id="arm-a-bug">#bug{left:120px;right:auto;top:190px}</style>'
    assert bug_style in _plate_html(h)
    assert ck.check_headline_plate(h, _plate_html(h).replace(bug_style, "")) == ["bug_override_missing"]
    assert ck.check_headline_plate(h, _plate_html(h).replace(bug_style, bug_style.replace("left:120px", "left:900px"))) \
        == ["bug_override_not_at_120,190"]


# ── run_checker + main ──

def test_run_checker_arm_a_clean_video_and_html_passes(tmp_path):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    h = _parsed()
    result = ck.run_checker(video, [_evid("EVID-1", [100, 800, 600, 500])], composition_html=_plate_html(h), headline=h)
    assert result["pass"] is True and result["headline"] == []
    assert set(result) == {"pass", "empty_frames", "out_of_safe_area", "text_over_face", "credit_missing",
                           "extra_caption_styles", "kinetic_overflow", "headline"}


def test_run_checker_arm_a_fails_on_a_plate_geometry_problem(tmp_path):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    h = _parsed(bug_side="right")
    result = ck.run_checker(video, [], headline=h)
    assert result["pass"] is False and result["headline"] == ["overlaps_bug_right"]


def test_run_checker_arm_a_fails_when_the_composed_html_has_no_plate(tmp_path):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    result = ck.run_checker(video, [], composition_html="<html></html>", headline=_parsed())
    assert result["pass"] is False and result["headline"] == ["plate_count=0"]


def test_run_checker_arm_a_empty_frame_is_still_caught_under_the_plate(tmp_path):
    video = tmp_path / "plate-only.mp4"
    _box_on_black(video, *PLATE_BOX)
    h = _parsed(lines=["รู้ก่อนเสียเงิน", "เปิดบัญชีง่าย"], red="เสียเงิน")
    result = ck.run_checker(video, [], headline=h)
    assert result["empty_frames"] and result["pass"] is False


def test_main_reads_an_arm_a_object_and_an_arm_b_list(tmp_path):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    beats = [_evid("EVID-1", [100, 800, 600, 500])]
    arm_b = tmp_path / "b.json"
    arm_b.write_text(json.dumps(beats))
    assert ck.main(["--video", str(video), "--beats", str(arm_b)]) == 0
    arm_a = tmp_path / "a.json"
    arm_a.write_text(json.dumps({"headline": _headline(), "beats": beats}))
    assert ck.main(["--video", str(video), "--beats", str(arm_a)]) == 0
    arm_a_right = tmp_path / "a-right.json"
    arm_a_right.write_text(json.dumps({"headline": _headline(bug_side="right"), "beats": beats}))
    assert ck.main(["--video", str(video), "--beats", str(arm_a_right)]) == 1


def test_main_exits_2_with_the_reason_when_red_is_ambiguous(tmp_path, capsys):
    video = tmp_path / "clean.mp4"
    _continuous_video(video, dur=1.0)
    doc = tmp_path / "a.json"
    doc.write_text(json.dumps({"headline": _headline(lines=["ผลลัพธ์จริง", "ผลลัพธ์ปลอม"], red="ผลลัพธ์"), "beats": []}))
    assert ck.main(["--video", str(video), "--beats", str(doc)]) == 2
    assert "ambiguous" in capsys.readouterr().err
