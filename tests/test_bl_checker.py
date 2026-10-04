"""Unit tests for tools/bl_checker.py (task-67bb7a11).

Synthetic ffmpeg fixtures only (testsrc/color lavfi sources) -- no real
episode media, no model calls. ffmpeg itself is exercised for real, same
convention as tests/test_bl_scripter.py.

Run via: pytest tests/test_bl_checker.py -q
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import bl_mark_clips as mc
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


def test_check_out_of_safe_area_counts_a_comp_shift():
    # EP58 MAIN-10: evidence at native y 1595-1690 sits in TikTok's caption zone, but the COMP
    # still is drawn 780 px higher (bl_compose `top - shift`), so on screen it is at y 815-910.
    box = [80, 1595, 860, 95]
    assert ck.check_out_of_safe_area([_beat("MAIN-10", "COMP", {"img": "real/x.png", "box": box})]) == ["MAIN-10"]
    assert ck.check_out_of_safe_area([_beat("MAIN-10", "COMP", {"img": "real/x.png", "box": box,
                                                                "shift": 780})]) == []


def test_check_out_of_safe_area_evid_never_shifts():
    beats = [_beat("MAIN-13", "EVID", {"img": "real/x.png", "box": [80, 1595, 860, 95], "shift": 780})]
    assert ck.check_out_of_safe_area(beats) == ["MAIN-13"]


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


# ── COMP captions above the head: per-take face boxes, the beat's own cap_cy, the evidence region (task-f35f2935) ──

def _comp(tag, t0, box=None, shift=0, cap="Caption", cy=None):
    extra = {"cap": cap}
    if box is not None:
        extra.update({"img": "real/x.png", "box": box, "shift": shift})
    if cy is not None:
        extra["cap_cy"] = cy
    return {"tag": tag, "t0": t0, "t1": t0 + 2.0, "mode": "COMP", "extra": extra}


def test_lip_take_follows_the_generators_seat_thresholds():
    assert [ck.lip_take(t) for t in (0.0, 38.76, 38.77, 80.83, 80.84, 95.0)] == \
        ["lip_a", "lip_a", "lip_b", "lip_b", "lip_c", "lip_c"]


def test_comp_caption_centre_is_head_top_minus_the_gap_and_half_a_pill_for_all_three_takes():
    assert {t: ck.comp_caption_cy(t) for t in ck.COMP_TAKES} == {"lip_a": 797, "lip_b": 862, "lip_c": 893}
    for take, row in ck.COMP_TAKES.items():
        cy = ck.comp_caption_cy(take)
        assert cy + ck.CAP_PILL_HALF_H <= row["head_top"] - ck.CAP_HEAD_GAP          # the pill ends 24 px above the head
        assert cy + 1 + ck.CAP_PILL_HALF_H > row["head_top"] - ck.CAP_HEAD_GAP       # and not a pixel higher than it must


def test_caption_band_comp_with_a_centre_is_the_pill_there_and_without_one_is_the_old_band():
    assert ck.caption_band("COMP", cy=797) == (715, 879)
    assert ck.caption_band("COMP") == ck.caption_band("FF") == (0.62 * ck.CANVAS_H, 0.72 * ck.CANVAS_H)
    assert ck.caption_band("FF", cy=797) == ck.caption_band("FF")                       # only COMP moves
    assert ck.caption_band("EVID", cy=797) is None and ck.caption_band("KIN") is None


def test_text_over_face_per_take_passes_a_comp_pill_above_the_head_and_fails_the_one_on_the_face():
    boxes = ck.take_face_boxes()
    for t0, take in ((1.0, "lip_a"), (40.0, "lip_b"), (90.0, "lip_c")):
        above = [_comp("C", t0, cy=ck.comp_caption_cy(take))]
        assert ck.check_text_over_face(above, None, take_boxes=boxes) == [], take
        assert ck.check_text_over_face([_comp("C", t0)], None, take_boxes=boxes) == ["C"], take       # still at 1300
        slack = [_comp("C", t0, cy=ck.comp_caption_cy(take) + ck.CAP_HEAD_GAP - 1)]                   # 1 px short of the head
        assert ck.check_text_over_face(slack, None, take_boxes=boxes) == [], take
        touching = [_comp("C", t0, cy=ck.comp_caption_cy(take) + ck.CAP_HEAD_GAP)]                    # the pill meets the head
        assert ck.check_text_over_face(touching, None, take_boxes=boxes) == ["C"], take


def test_text_over_face_per_take_uses_the_beats_own_take_and_mode():
    boxes = ck.take_face_boxes()
    # lip_a's pill centre (797) is far above lip_c's head, but lip_c's own centre is 893: 797 is safe there too ...
    assert ck.check_text_over_face([_comp("C", 90.0, cy=797)], None, take_boxes=boxes) == []
    # ... and lip_c's centre (893) on a lip_a beat reaches 975, over lip_a's head (top 903)
    assert ck.check_text_over_face([_comp("C", 1.0, cy=893)], None, take_boxes=boxes) == ["C"]
    # an FF beat is judged against the FF box at 1:1 (head to y 1101), whose caption band is the standing one
    ff = {"tag": "F", "t0": 90.0, "t1": 92.0, "mode": "FF", "extra": {"cap": "x"}}
    assert ck.check_text_over_face([ff], None, take_boxes=boxes) == []
    assert ck.check_text_over_face([ff], None, take_boxes={"lip_c": {"FF": (0, 1000, 1080, 600), "COMP": (0, 0, 1, 1)}}) == ["F"]


def test_text_over_face_per_take_refuses_a_take_with_no_box():
    with pytest.raises(ValueError, match="no COMP face box for take 'lip_b'"):
        ck.check_text_over_face([_comp("C", 40.0, cy=862)], None, take_boxes={"lip_a": {"FF": (0, 0, 1, 1), "COMP": (0, 0, 1, 1)}})


def test_face_box_beats_lists_the_beats_each_take_box_was_judged_against():
    beats = [_comp("A1", 1.0), _comp("A2", 5.0), _comp("B1", 40.0),
             {"tag": "F1", "t0": 90.0, "t1": 92.0, "mode": "FF", "extra": {}}, _evid("E1", [0, 0, 10, 10])]
    got = ck.face_box_beats(beats, ck.take_face_boxes())
    assert got == {"lip_a": {"COMP": {"box": list(ck.COMP_TAKES["lip_a"]["comp_box"]), "beats": ["A1", "A2"]}},
                   "lip_b": {"COMP": {"box": list(ck.COMP_TAKES["lip_b"]["comp_box"]), "beats": ["B1"]}},
                   "lip_c": {"FF": {"box": list(ck.COMP_TAKES["lip_c"]["ff_box"]), "beats": ["F1"]}}}


def test_evidence_region_arm_b_runs_from_under_the_bug_to_above_the_pill_arm_a_starts_lower():
    assert ck.evidence_region("lip_a") == (pytest.approx(460.8), 797 - 82 - 12 - 10)       # 693
    assert ck.evidence_region("lip_b")[1] == 862 - 82 - 12 - 10
    assert ck.evidence_region("lip_c", _parsed())[0] == ck.ARM_A_EVIDENCE_TOP == 560
    assert ck.evidence_region("lip_a", cy=700)[1] == 700 - 82 - 12 - 10


def test_comp_evidence_landing_counts_the_shift_and_names_which_edge_missed():
    top, bottom = ck.evidence_region("lip_a")
    fits = _comp("FIT", 9.0, box=[54, 500, 972, 150], shift=0, cy=797)
    assert ck.check_comp_evidence_landing([fits]) == []
    # the same box shifted down 60 (negative shift lowers the still) reaches 650+60 = 710 > 693 -> in the pill
    low = _comp("LOW", 9.0, box=[54, 500, 972, 150], shift=-60, cy=797)
    assert ck.check_comp_evidence_landing([low]) == ["LOW:in_caption"]
    # lifted 100 it starts at 400, under the brand mark's 460.8
    high = _comp("HIGH", 9.0, box=[54, 500, 972, 150], shift=100, cy=797)
    assert ck.check_comp_evidence_landing([high]) == ["HIGH:above_region"]
    assert top < 500 and 500 + 150 <= bottom
    # exactly on the limits passes
    edge = _comp("EDGE", 9.0, box=[54, 461, 972, bottom - 461], cy=797)
    assert ck.check_comp_evidence_landing([edge]) == []


def test_comp_evidence_landing_arm_a_limit_is_below_the_stamp_and_scrim():
    beat = _comp("A", 9.0, box=[54, 520, 972, 100], cy=797)
    assert ck.check_comp_evidence_landing([beat]) == []                                   # arm B: starts under 460.8
    assert ck.check_comp_evidence_landing([beat], _parsed()) == ["A:above_region"]        # arm A: 520 < 560


def test_comp_evidence_landing_skips_evid_and_a_comp_with_no_box():
    beats = [_evid("EVID-1", [54, 100, 972, 1500]), _comp("NOBOX", 9.0, cy=797)]
    assert ck.check_comp_evidence_landing(beats) == []


def test_comp_evidence_landing_follows_a_pill_moved_up():
    beat = _comp("UP", 9.0, box=[54, 500, 972, 150], cy=700)      # pill top 618: 650 + 22 > 618
    assert ck.check_comp_evidence_landing([beat]) == ["UP:in_caption"]


def test_run_checker_per_take_boxes_fail_a_comp_pill_on_the_face_and_report_the_beats(tmp_path):
    video = _clean_video(tmp_path / "clean.mp4")
    ok = ck.run_checker(video, [_comp("C", 1.0, box=[54, 500, 972, 150], cy=797)], take_boxes=ck.take_face_boxes())
    assert ok["pass"] is True and ok["text_over_face"] == [] and ok["comp_evidence_landing"] == []
    assert ok["face_box_beats"]["lip_a"]["COMP"]["beats"] == ["C"]
    bad = ck.run_checker(video, [_comp("C", 1.0, box=[54, 500, 972, 150])], take_boxes=ck.take_face_boxes())
    assert bad["pass"] is False and bad["text_over_face"] == ["C"]
    assert "face_box_beats" not in ck.run_checker(video, [], face_box=None)


# ── --take-table: another episode's takes replace COMP_TAKES (task-2db3174c) ──

def _table_doc(**over):
    """Three takes at seats 0 / 31.5 / 62.0 with heads 40 px higher than lip_a/b/c of EP58 -- nothing like COMP_TAKES."""
    takes = {
        "lip_a": {"seat": 0.0, "head_top": 863.04, "cy": 757, "comp_box": [-25, 863, 573, 599], "ff_box": [21, 64, 1021, 1037]},
        "lip_b": {"seat": 31.5, "head_top": 928.56, "cy": 822, "comp_box": [-7, 928, 576, 534], "ff_box": [54, 181, 1026, 920]},
        "lip_c": {"seat": 62.0, "head_top": 959.92, "cy": 853, "comp_box": [48, 959, 416, 503], "ff_box": [151, 237, 742, 864]},
    }
    takes.update(over)
    return {"episode": 99, "takes": takes}


def test_load_take_table_reads_a_file_and_orders_the_seats(tmp_path):
    path = tmp_path / "take_table.json"
    doc = _table_doc()
    doc["takes"]["lip_c"]["note"] = "extra keys are the reader's"
    path.write_text(json.dumps(doc), encoding="utf-8")
    t = ck.load_take_table(path)
    assert t["seats"] == (("lip_a", 0.0), ("lip_b", 31.5), ("lip_c", 62.0))
    assert t["takes"]["lip_b"]["comp_box"] == (-7, 928, 576, 534) and t["takes"]["lip_a"]["cy"] == 757
    assert ck.load_take_table(doc) == t                                  # a parsed dict is taken too


def test_the_table_moves_the_seats_the_caption_centres_and_the_boxes():
    t = ck.load_take_table(_table_doc())
    assert [ck.lip_take(x, t) for x in (0.0, 31.49, 31.5, 61.99, 62.0, 90.0)] == \
        ["lip_a", "lip_a", "lip_b", "lip_b", "lip_c", "lip_c"]
    assert ck.lip_take(35.0) == "lip_a" and ck.lip_take(35.0, t) == "lip_b"       # EP58's seat 38.77 is not this table's
    assert {k: ck.comp_caption_cy(k, t) for k in t["takes"]} == {"lip_a": 757, "lip_b": 822, "lip_c": 853}
    assert ck.take_face_boxes(t)["lip_b"]["COMP"] == (-7, 928, 576, 534)
    assert ck.evidence_region("lip_a", table=t)[1] == 757 - 82 - 12 - 10
    # the no-table calls are untouched
    assert ck.comp_caption_cy("lip_a") == 797 and ck.take_face_boxes() == ck.take_face_boxes(None)


def test_the_table_judges_text_over_face_and_landing_with_its_own_numbers():
    t = ck.load_take_table(_table_doc())
    boxes = ck.take_face_boxes(t)
    # 797 clears EP58's lip_a head (903) but this table's lip_a head is 863: the pill 715..879 meets it
    on_face = [_comp("C", 1.0, cy=797)]
    assert ck.check_text_over_face(on_face, None, take_boxes=ck.take_face_boxes()) == []
    assert ck.check_text_over_face(on_face, None, take_boxes=boxes, table=t) == ["C"]
    ok = [_comp("C", 1.0, cy=757), _comp("D", 33.0, cy=822), _comp("E", 70.0, cy=853)]
    assert ck.check_text_over_face(ok, None, take_boxes=boxes, table=t) == []
    # a beat at 33 s is lip_b here (seat 31.5) -- it was lip_a under EP58's seats, where cy 822 would meet a head at 903
    assert ck.check_text_over_face([_comp("D", 33.0, cy=822)], None, take_boxes=ck.take_face_boxes()) == ["D"]
    assert ck.check_comp_evidence_landing([_comp("L", 1.0, box=[54, 500, 972, 150], cy=757)], table=t) == []
    assert ck.check_comp_evidence_landing([_comp("L", 1.0, box=[54, 500, 972, 150], cy=757)]) == []
    assert ck.check_comp_evidence_landing([_comp("L", 1.0, box=[54, 560, 972, 150], cy=757)], table=t) == ["L:in_caption"]
    got = ck.face_box_beats(ok, boxes, t)
    assert got["lip_b"]["COMP"] == {"box": [-7, 928, 576, 534], "beats": ["D"]}


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d.update(takes={}), "at least one take"),
    (lambda d: d["takes"]["lip_a"].pop("ff_box"), "'lip_a' has no 'ff_box'"),
    (lambda d: d["takes"]["lip_a"].update(cy=790), "cy 790 is not floor"),
    (lambda d: d["takes"]["lip_b"].update(comp_box=[0, 0, 0, 5]), "comp_box must be"),
    (lambda d: d["takes"]["lip_b"].update(seat="31.5"), "must be numbers"),
    (lambda d: d["takes"]["lip_b"].update(seat=0.0), "share one seat"),
])
def test_load_take_table_refuses_a_table_that_disagrees_with_itself(mutate, message):
    doc = _table_doc()
    mutate(doc)
    with pytest.raises(ValueError, match=message):
        ck.load_take_table(doc)


def test_main_take_table_judges_per_take_and_a_bad_table_is_exit_2(tmp_path, capsys):
    video = _clean_video(tmp_path / "clean.mp4")
    table = tmp_path / "take_table.json"
    table.write_text(json.dumps(_table_doc()), encoding="utf-8")
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps([_comp("C", 1.0, box=[54, 500, 972, 150], cy=757)]), encoding="utf-8")
    bad.write_text(json.dumps([_comp("C", 1.0, cy=797)]), encoding="utf-8")                   # EP58's centre, this head is higher
    out = tmp_path / "result.json"
    assert ck.main(["--video", str(video), "--beats", str(good), "--take-table", str(table), "--out", str(out)]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["face_box_beats"]["lip_a"]["COMP"]["box"] == [-25, 863, 573, 599]            # the table's box, not COMP_TAKES'
    assert ck.main(["--video", str(video), "--beats", str(bad), "--take-table", str(table)]) == 1
    assert json.loads(capsys.readouterr().out.split("\n}\n")[-2] + "\n}")["text_over_face"] == ["C"]
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(_table_doc(lip_a={"seat": 0.0})), encoding="utf-8")
    assert ck.main(["--video", str(video), "--beats", str(good), "--take-table", str(broken)]) == 2
    assert ck.main(["--video", str(video), "--beats", str(good), "--take-table", str(tmp_path / "missing.json")]) == 2
    # without the option nothing changes: no per-take verdict, no face_box_beats
    assert ck.main(["--video", str(video), "--beats", str(good), "--out", str(out)]) == 0
    assert "face_box_beats" not in json.loads(out.read_text(encoding="utf-8"))


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

def _clean_video(path: Path, sides=("right",)) -> Path:
    """A clean 1 s clip: busy plate on every frame, the brand mark (and the legal pill) on, on the given side(s).
    The 270x480 `testsrc` clips this file used before passed the mark gate only because testsrc's red/yellow colour
    bars happen to sit under the mark's rule -- a clip a run_checker test calls clean must carry the mark on purpose."""
    return mc.marked_clip(path, frames=30, sides=sides)


def test_run_checker_pass_true_when_everything_clean(tmp_path):
    video = _clean_video(tmp_path / "clean.mp4")
    beats = [_beat("EVID-1", "EVID", {"img": "real/x.png", "box": [200, 300, 400, 500]})]
    result = ck.run_checker(video, beats)
    assert result["pass"] is True
    assert result["brand_mark"]["ok"] is True and result["brand_mark"]["failing_frames"] == 0
    assert {k: v for k, v in result.items() if k != "brand_mark"} == {
        "pass": True, "empty_frames": [], "empty_frames_excused": [], "out_of_safe_area": [], "text_over_face": [],
        "comp_evidence_landing": [], "credit_missing": [], "extra_caption_styles": [], "kinetic_overflow": []}


def test_run_checker_pass_false_when_safe_area_fails(tmp_path):
    video = _clean_video(tmp_path / "clean.mp4")
    beats = [_beat("COMP-1", "COMP", {"img": "real/x.png", "box": [950, 200, 120, 100]})]
    result = ck.run_checker(video, beats)
    assert result["pass"] is False
    assert result["out_of_safe_area"] == ["COMP-1"]
    assert result["empty_frames"] == []


def test_main_exit_code_matches_pass(tmp_path, capsys):
    video = _clean_video(tmp_path / "clean.mp4")
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


def test_layout_estimates_latin_capitals_wider_than_thai_text():
    # measured in Chromium on Kanit 800 (task-406c21f3): a 30-character all-caps line rendered 870 px at 48 px in an
    # 840 px box when it was estimated at the Thai 0.58 em per character; capitals are 0.70 em in the estimate now.
    caps = ck.headline_layout(_parsed(lines=["BROKER WITHDRAWAL SCAM EXPOSED", "WHAT THEY HIDE FROM TRADERS"], red="SCAM"))
    thai = ck.headline_layout(_parsed(lines=["ก" * 30, "ข" * 30], red="ก" * 30))
    assert thai["font_px"] == 48 and caps["font_px"] == 40
    assert caps["text"][2] <= 840 and caps["font_px"] * 30 * 0.688 * 0.97 < 840      # the measured 0.688 em mean fits
    assert ck._text_width_em("ก" * 30 + "ิ่") == pytest.approx(30 * 0.58)           # combining marks are zero width


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
    video = _clean_video(tmp_path / "clean.mp4", sides=("left",))
    h = _parsed()
    result = ck.run_checker(video, [_evid("EVID-1", [100, 800, 600, 500])], composition_html=_plate_html(h), headline=h)
    assert result["pass"] is True and result["headline"] == []
    assert result["brand_mark"]["side"] == "left"
    assert set(result) == {"pass", "empty_frames", "empty_frames_excused", "out_of_safe_area", "text_over_face",
                           "comp_evidence_landing", "credit_missing", "extra_caption_styles", "kinetic_overflow",
                           "brand_mark", "headline"}


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
    video = _clean_video(tmp_path / "clean.mp4", sides=("right", "left"))   # both marks: either arm's gate is satisfied
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


# ═══════════════════════════════════════════════════════════════════════════
# The brand mark on every frame, and the KIN-entry grace (task-c32c40e8, CMO ruling 2026-10-01)
# ═══════════════════════════════════════════════════════════════════════════

import re  # noqa: E402

TEMPLATE_HTML = Path(__file__).resolve().parent.parent / ".claude/skills/CMO_Procedure_BlackLiquidity_Cut/template/index.html"


def _segments_from(alphas):
    """Per-frame alphas -> the (first, last, alpha) runs mc.marked_clip draws."""
    out = []
    for i, a in enumerate(alphas):
        if out and out[-1][2] == a and out[-1][1] == i - 1:
            out[-1] = (out[-1][0], i, a)
        else:
            out.append((i, i, a))
    return out


def _seam_alphas(frames=90, seams=(0, 45)):
    """The EP58 defect: at the opening and at a seam the mark is absent for 8 frames, then fades in (alpha .1 ... .8
    over 8 frames), then it is steady. The real fade ended at ~.9; the fixture stops a step short because a thin
    4:2:0 rule reads about 3-4 points high near the top of a fade, so a .9 frame sits on the 95% line by chance."""
    alphas = [1.0] * frames
    for s in seams:
        for k in range(8):
            alphas[s + k] = 0
        for k in range(8):
            alphas[s + 8 + k] = round((k + 1) / 10, 1)
    return alphas


def test_mark_rect_is_the_template_rule_inside_the_zone_the_empty_frame_gate_masks():
    assert ck.bug_rule_rect("right") == (856, 380, 74, 5)    # the CMO's x860-930 y380-385, measured in Chromium
    assert ck.bug_rule_rect("left") == pytest.approx((297.59, 198, 5, 44))
    assert ck.mark_sample_rect("right") == (857, 381, 72, 3)
    assert ck.mark_sample_rect("left") == (299, 199, 2, 42)
    for side in ("right", "left"):
        zx, zy, zw, zh = ck.bug_zone(side)
        x, y, w, h = ck.mark_sample_rect(side)
        assert zx <= x and x + w <= zx + zw and zy <= y and y + h <= zy + zh
        rx, ry, rw, rh = ck.bug_rule_rect(side)
        assert rx <= x and x + w <= rx + rw and ry <= y and y + h <= ry + rh


def test_mark_geometry_constants_match_the_template_css():
    css = TEMPLATE_HTML.read_text(encoding="utf-8")
    bug = re.search(r"\.bug \{[^}]*?right: (\d+)px; top: (\d+)px;[^}]*?gap: (\d+)px", css, re.S)
    logo = re.search(r"\.bug \.logo \{ height: (\d+)px", css)
    rule = re.search(r"\.bug \.rl \{ width: (\d+)px; height: (\d+)px; background: var\(--neon\)", css)
    neon = re.search(r"--neon:\s*#([0-9A-Fa-f]{6})", css)
    assert bug and logo and rule and neon, "the template's .bug / .logo / .rl / --neon CSS changed shape"
    assert (int(bug[1]), int(bug[2]), int(bug[3])) == (ck.BUG_RIGHT_INSET, ck.BUG_RIGHT_TOP, ck.BUG_COLUMN_GAP)
    assert int(logo[1]) == ck.BUG_LOGO_SIZE[1]
    assert (int(rule[1]), int(rule[2])) == ck.BUG_RIGHT_RULE_SIZE
    assert tuple(int(neon[1][i:i + 2], 16) for i in (0, 2, 4)) == ck.BRAND_NEON


@pytest.mark.parametrize("side", ["right", "left"])
def test_brand_mark_gate_passes_a_steady_mark(tmp_path, side):
    video = mc.marked_clip(tmp_path / "steady.mp4", frames=60, sides=(side,))
    v = ck.check_brand_mark(video, side)
    assert v["ok"] is True and v["failing_frames"] == 0 and v["failing_times"] == []
    assert v["min_ratio"] >= ck.MARK_MIN_OPACITY and v["steady_level"] > 180


@pytest.mark.parametrize("side", ["right", "left"])
def test_brand_mark_gate_fails_a_fade_in_at_the_opening_and_at_a_seam(tmp_path, side):
    alphas = _seam_alphas()
    video = mc.marked_clip(tmp_path / "blink.mp4", frames=90, sides=(side,), segments=_segments_from(alphas))
    v = ck.check_brand_mark(video, side)
    assert v["ok"] is False and "error" not in v
    # frames 0-15 and 45-60: absent for 8, then every ramp step (alpha .1 ... .8) is under 95%
    assert v["failing_ranges"] == [{"from": 0.0, "to": 0.5, "frames": 16}, {"from": 1.5, "to": 2.0, "frames": 16}]
    assert v["failing_frames"] == 32 and v["failing_times"][:3] == [0.0, 0.033, 0.067]
    assert v["min_ratio"] < 0.05 and v["min_time"] < 8 / 30


@pytest.mark.parametrize("alpha,ok", [(0.97, True), (0.85, False)])
def test_brand_mark_gate_threshold_is_95_percent_of_the_steady_level(tmp_path, alpha, ok):
    alphas = [alpha if 30 <= i < 40 else 1.0 for i in range(60)]
    video = mc.marked_clip(tmp_path / "dip.mp4", frames=60, segments=_segments_from(alphas))
    v = ck.check_brand_mark(video)
    assert v["ok"] is ok
    if not ok:
        assert v["failing_ranges"] == [{"from": 1.0, "to": 1.3, "frames": 10}]


def test_brand_mark_gate_fails_a_video_with_no_mark_at_all(tmp_path):
    video = mc.marked_clip(tmp_path / "none.mp4", frames=30, segments=[(0, 29, 0)])    # alpha 0: nothing drawn
    v = ck.check_brand_mark(video)
    assert v["ok"] is False and v["error"] == "mark_missing" and v["failing_frames"] == 30
    assert v["min_ratio"] is None and v["expected_level"] > 180


def test_brand_mark_gate_reads_the_side_the_arm_puts_the_bug_on(tmp_path):
    video = mc.marked_clip(tmp_path / "right-only.mp4", frames=30, sides=("right",))
    assert ck.check_brand_mark(video, "right")["ok"] is True
    assert ck.check_brand_mark(video, "left")["error"] == "mark_missing"


def test_brand_mark_gate_cannot_verify_a_file_with_no_frames(tmp_path):
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"not a video")
    assert ck.check_brand_mark(junk) == {"ok": False, "side": "right", "min_opacity": 0.95, "error": "no_frames"}


def test_run_checker_fails_on_a_blinking_mark_and_names_the_frames(tmp_path, capsys):
    video = mc.marked_clip(tmp_path / "blink.mp4", frames=90, segments=_segments_from(_seam_alphas()))
    beats = [_beat("EVID-1", "EVID", {"img": "real/x.png", "box": [200, 300, 400, 500]})]
    result = ck.run_checker(video, beats)
    assert result["pass"] is False
    assert result["empty_frames"] == []                      # the plate is busy: only the mark gate caught it
    assert result["brand_mark"]["failing_ranges"][0] == {"from": 0.0, "to": 0.5, "frames": 16}
    beats_path = tmp_path / "beats.json"
    beats_path.write_text(json.dumps(beats))
    assert ck.main(["--video", str(video), "--beats", str(beats_path)]) == 1
    assert json.loads(capsys.readouterr().out)["brand_mark"]["failing_frames"] == 32


def test_run_checker_arm_a_reads_the_left_mark(tmp_path):
    right_only = mc.marked_clip(tmp_path / "right-only.mp4", frames=30, sides=("right",))
    result = ck.run_checker(right_only, [], headline=_parsed())
    assert result["pass"] is False
    assert result["brand_mark"]["side"] == "left" and result["brand_mark"]["error"] == "mark_missing"


# ── KIN entry grace ──

def _kin(t0=1.0, mode="KIN", tag="MAIN-1"):
    extra = {"img": "real/x.png", "box": [200, 300, 400, 500]} if mode in ("COMP", "EVID") else {}
    return {"tag": tag, "t0": t0, "t1": t0 + 1.0, "mode": mode, "extra": extra}


def test_kin_entry_frames_are_the_first_four_from_each_kin_t0_only():
    beats = [_kin(1.0, tag="A"), _kin(2.0, mode="COMP", tag="B"), _kin(3.0, tag="C")]
    entry = ck.kin_entry_frames(beats)
    assert sorted(entry) == [30, 31, 32, 33, 90, 91, 92, 93]
    assert entry[30] == ("A", 1) and entry[93] == ("C", 4)


def test_kin_grace_excuses_the_first_four_frames_while_the_mark_and_legal_pill_are_on(tmp_path):
    video = mc.marked_clip(tmp_path / "kin.mp4", frames=90, flat=[(30, 33)])
    plain = ck.run_checker(video, [])                         # no beats: today's behaviour
    assert plain["empty_frames"] == [1.0, 1.033, 1.067, 1.1] and plain["pass"] is False
    assert plain["empty_frames_excused"] == []
    result = ck.run_checker(video, [_kin()])
    assert result["empty_frames"] == [] and result["pass"] is True
    assert result["empty_frames_excused"] == [
        {"t": t, "beat": "MAIN-1", "entry_frame": k} for k, t in enumerate([1.0, 1.033, 1.067, 1.1], 1)]


def test_kin_grace_does_not_cover_the_fifth_frame(tmp_path):
    video = mc.marked_clip(tmp_path / "kin5.mp4", frames=90, flat=[(30, 34)])
    result = ck.run_checker(video, [_kin()])
    assert result["empty_frames"] == [1.133] and len(result["empty_frames_excused"]) == 4
    assert result["pass"] is False


def test_kin_grace_does_not_cover_a_beat_that_is_not_kin(tmp_path):
    video = mc.marked_clip(tmp_path / "comp.mp4", frames=90, flat=[(30, 33)])
    result = ck.run_checker(video, [_kin(mode="COMP", tag="COMP-1")])
    assert result["empty_frames"] == [1.0, 1.033, 1.067, 1.1] and result["empty_frames_excused"] == []
    assert result["pass"] is False


def test_kin_grace_does_not_cover_frames_away_from_the_kin_t0(tmp_path):
    video = mc.marked_clip(tmp_path / "away.mp4", frames=90, flat=[(30, 33)])
    result = ck.run_checker(video, [_kin(t0=2.0)])
    assert result["empty_frames"] == [1.0, 1.033, 1.067, 1.1] and result["empty_frames_excused"] == []


def test_kin_grace_needs_the_brand_mark_on_the_frame(tmp_path):
    video = mc.marked_clip(tmp_path / "nomark.mp4", frames=90, flat=[(30, 33)],
                           segments=[(0, 29, 1.0), (34, 89, 1.0)])
    result = ck.run_checker(video, [_kin()])
    assert result["empty_frames"] == [1.0, 1.033, 1.067, 1.1] and result["empty_frames_excused"] == []
    assert result["brand_mark"]["ok"] is False


def test_kin_grace_needs_the_legal_pill_on_the_frame(tmp_path):
    video = mc.marked_clip(tmp_path / "nolegal.mp4", frames=90, flat=[(30, 33)], legal_off=[(30, 33)])
    result = ck.run_checker(video, [_kin()])
    assert result["empty_frames"] == [1.0, 1.033, 1.067, 1.1] and result["empty_frames_excused"] == []
    assert result["brand_mark"]["ok"] is True                 # the mark is fine: it is the pill that is missing


def test_kin_grace_reads_the_mark_on_the_side_the_arm_uses(tmp_path):
    video = mc.marked_clip(tmp_path / "left.mp4", frames=90, sides=("left",), flat=[(30, 33)])
    left, excused = ck.excuse_kin_entry(video, [1.0, 1.033], [_kin()], "left")
    assert left == [] and len(excused) == 2
    right, excused = ck.excuse_kin_entry(video, [1.0, 1.033], [_kin()], "right")
    assert right == [1.0, 1.033] and excused == []


# ───────── the EP58 cuts themselves (task-f35f2935): both beats.json files satisfy the new gates ─────────

EP58 = Path(__file__).resolve().parents[1] / "prototypes" / "bl-ep58"
EP58_ARMS = (("arm B", EP58 / "beats.json"), ("arm A", EP58 / "armA" / "beats.json"))


def _ep58(path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, dict):
        return doc["beats"], ck.parse_headline(doc["headline"])
    return doc, None


@pytest.mark.parametrize("arm,path", EP58_ARMS)
def test_ep58_every_captioned_comp_beat_carries_its_takes_pill_centre(arm, path):
    beats, _ = _ep58(path)
    comp = [b for b in beats if b["mode"] == "COMP" and b["extra"].get("cap")]
    assert comp, arm
    for b in comp:
        assert b["extra"].get("cap_cy") == ck.COMP_TAKES[ck.lip_take(b["t0"])]["cy"], (arm, b["tag"])
    # FF / EVID / KIN pills stay at the .caplayer's own 1300
    assert not [b["tag"] for b in beats if b["mode"] != "COMP" and "cap_cy" in b.get("extra", {})]


@pytest.mark.parametrize("arm,path", EP58_ARMS)
def test_ep58_comp_evidence_lands_and_no_caption_touches_a_face(arm, path):
    beats, headline = _ep58(path)
    assert ck.check_comp_evidence_landing(beats, headline) == []
    assert ck.check_text_over_face(beats, None, headline, take_boxes=ck.take_face_boxes()) == []


def test_ep58_the_two_arms_share_every_comp_box_they_both_have():
    b_beats, _ = _ep58(EP58_ARMS[0][1])
    a_beats, _ = _ep58(EP58_ARMS[1][1])
    a = {x["tag"]: x["extra"] for x in a_beats if x["mode"] == "COMP"}
    shared = [(x["tag"], x["extra"]) for x in b_beats if x["mode"] == "COMP" and x["tag"] in a and "box" in x["extra"] and "box" in a[x["tag"]]]
    assert len(shared) >= 10
    for tag, ex in shared:
        assert ex["box"] == a[tag]["box"] and ex.get("img") == a[tag].get("img"), tag
