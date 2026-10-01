"""Unit tests for tools/bl_merge.py (task-1678d38e, docs/ops/bl-split-ab-2026-09-25).

Synthetic ffmpeg fixtures only (testsrc/color lavfi sources), same
convention as tests/test_bl_checker.py -- including a deliberately failing
seam (one black frame right at a join) that the seam gate must catch.

Run via: pytest tests/test_bl_merge.py -q
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools import bl_merge as mg

W, H, RATE = 270, 480, 30


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _testsrc_segment(path: Path, frames: int, rate: int = RATE, w: int = W, h: int = H) -> None:
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate={rate}",
          "-frames:v", str(frames), "-pix_fmt", "yuv420p", str(path)])


def _testsrc_segment_with_trailing_black_frame(path: Path, content_frames: int, rate: int = RATE,
                                                w: int = W, h: int = H) -> None:
    """content_frames of testsrc followed by EXACTLY one black frame -- a
    frame-exact stand-in for a segment render that ends on a bad frame."""
    _run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate={rate}",
        "-f", "lavfi", "-i", f"color=black:size={w}x{h}:rate={rate}",
        "-filter_complex",
        f"[0:v]trim=start_frame=0:end_frame={content_frames},setpts=PTS-STARTPTS[a];"
        f"[1:v]trim=start_frame=0:end_frame=1,setpts=PTS-STARTPTS[b];"
        "[a][b]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-r", str(rate), "-pix_fmt", "yuv420p", str(path),
    ])


def _silent_audio(path: Path, duration: float) -> None:
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
          "-t", str(duration), str(path)])


def _segments(*ids: str) -> list[dict]:
    return [{"id": sid} for sid in ids]


# ─────────────────────────── pure-python gate logic ───────────────────────

def test_check_frame_count_within_tolerance():
    r = mg.check_frame_count(actual_frames=4591, audio_duration=153.0514, fps=30)
    assert r["ok"] is True
    assert r["expected"] == 4591


def test_check_frame_count_outside_tolerance():
    r = mg.check_frame_count(actual_frames=4585, audio_duration=153.0514, fps=30, tolerance=1)
    assert r["ok"] is False


def test_check_seams_flags_empty_frame_near_join():
    empty_times = [26 / 30]
    bad = mg.check_seams(empty_times, seam_frame_indices=[27], fps=30, window=3)
    assert len(bad) == 1
    assert bad[0]["seam_frame"] == 27


def test_check_seams_ignores_empty_frame_far_from_any_join():
    empty_times = [10 / 30]
    bad = mg.check_seams(empty_times, seam_frame_indices=[27], fps=30, window=3)
    assert bad == []


def test_check_seams_no_empty_frames_passes():
    assert mg.check_seams([], seam_frame_indices=[27, 90], fps=30) == []


def test_check_caption_styles_single_style_across_segments(tmp_path):
    (tmp_path / "seg01.html").write_text('caption(0.1, 1.0, "hi");', encoding="utf-8")
    (tmp_path / "seg02.html").write_text('caption(0.1, 1.0, "bye");', encoding="utf-8")
    assert mg.check_caption_styles(["seg01", "seg02"], tmp_path) == []


def test_check_caption_styles_flags_mixed_styles_across_segments(tmp_path):
    (tmp_path / "seg01.html").write_text('caption(0.1, 1.0, "hi");', encoding="utf-8")
    (tmp_path / "seg02.html").write_text('addCap(0.1, 1.0, "bye", "rail", null);', encoding="utf-8")
    bad = mg.check_caption_styles(["seg01", "seg02"], tmp_path)
    assert bad != []


def test_check_caption_styles_none_dir_skips_gate():
    assert mg.check_caption_styles(["seg01"], None) == []


def test_check_audio_offset_reads_start_time(monkeypatch, tmp_path):
    monkeypatch.setattr(mg, "probe_audio_start_time", lambda p: 0.01)
    r = mg.check_audio_offset(tmp_path / "x.mp4")
    assert r["ok"] is True
    monkeypatch.setattr(mg, "probe_audio_start_time", lambda p: 0.2)
    r = mg.check_audio_offset(tmp_path / "x.mp4")
    assert r["ok"] is False


# ─────────────────────────── verify_same_codec ─────────────────────────────

def test_verify_same_codec_passes_for_identical_parts(tmp_path):
    p1, p2 = tmp_path / "a.mp4", tmp_path / "b.mp4"
    _testsrc_segment(p1, 10)
    _testsrc_segment(p2, 10)
    assert mg.verify_same_codec([p1, p2]) == []


def test_verify_same_codec_flags_resolution_mismatch(tmp_path):
    p1, p2 = tmp_path / "a.mp4", tmp_path / "b.mp4"
    _testsrc_segment(p1, 10, w=270, h=480)
    _testsrc_segment(p2, 10, w=320, h=480)
    mismatches = mg.verify_same_codec([p1, p2])
    assert mismatches
    assert any("width" in m for m in mismatches)


# ─────────────────────────── end-to-end merge() ────────────────────────────

def test_merge_passes_when_everything_clean(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _testsrc_segment(parts_dir / "seg01.mp4", 60)  # 2.0s
    _testsrc_segment(parts_dir / "seg02.mp4", 60)  # 2.0s
    audio = tmp_path / "audio.wav"
    _silent_audio(audio, 4.0)

    result = mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4")
    assert result["pass"] is True, result["gates"]
    assert result["gates"]["empty_frames"] == []
    assert result["gates"]["seam_failures"] == []
    assert result["gates"]["frame_count"]["ok"] is True
    assert mg.failed_gate_names(result) == []


def test_merge_refuses_on_mismatched_codec_params(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _testsrc_segment(parts_dir / "seg01.mp4", 60, w=270, h=480)
    _testsrc_segment(parts_dir / "seg02.mp4", 60, w=320, h=480)
    audio = tmp_path / "audio.wav"
    _silent_audio(audio, 4.0)

    with pytest.raises(mg.MergeError, match="codec"):
        mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4")


def test_merge_catches_a_black_frame_right_at_the_seam(tmp_path):
    # seg01 ends on one black frame (a bad render at the join); seg02 is
    # clean. The seam gate must attribute the failure to that specific join.
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _testsrc_segment_with_trailing_black_frame(parts_dir / "seg01.mp4", content_frames=26)  # 27 frames
    _testsrc_segment(parts_dir / "seg02.mp4", 30)  # 30 frames
    audio = tmp_path / "audio.wav"
    _silent_audio(audio, 57 / RATE)

    result = mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4")
    assert result["pass"] is False
    assert result["gates"]["seam_failures"], result["gates"]
    assert result["gates"]["seam_failures"][0]["seam_frame"] == 27
    assert "empty_frames" in mg.failed_gate_names(result)
    assert "seam_failures" in mg.failed_gate_names(result)


def test_merge_raises_on_missing_part(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _testsrc_segment(parts_dir / "seg01.mp4", 30)
    audio = tmp_path / "audio.wav"
    _silent_audio(audio, 2.0)

    with pytest.raises(mg.MergeError, match="missing"):
        mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4")


# ─────────────────────────── CLI ───────────────────────────────────────────

def test_main_end_to_end_exit_codes(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _testsrc_segment(parts_dir / "seg01.mp4", 30)
    _testsrc_segment(parts_dir / "seg02.mp4", 30)
    audio = tmp_path / "audio.wav"
    _silent_audio(audio, 2.0)
    seg_json = tmp_path / "segments.json"
    seg_json.write_text(json.dumps({"segments": _segments("seg01", "seg02")}), encoding="utf-8")

    rc = mg.main([str(seg_json), "--parts", str(parts_dir), "--audio", str(audio),
                  "-o", str(tmp_path / "final.mp4")])
    assert rc == 0


# ── arm A (headline plate): the empty-frame gate takes the arm's mask ──

from tools import bl_checker as ck  # noqa: E402

_ARM_A_HEADLINE = {"lines": ["โบรกเกอร์ถูกเตือน", "คุณรู้หรือยัง"], "red": "เตือน", "bug_side": "left",
                   "backdrop": [{"t0": 0.0, "src": "real/a.png"}, {"t0": 1.0, "src": "real/b.png"},
                                {"t0": 2.0, "src": "real/c.png"}]}


def _clean_two_part_job(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _testsrc_segment(parts_dir / "seg01.mp4", 30)
    _testsrc_segment(parts_dir / "seg02.mp4", 30)
    audio = tmp_path / "audio.wav"
    _silent_audio(audio, 2.0)
    seg_json = tmp_path / "segments.json"
    seg_json.write_text(json.dumps({"segments": _segments("seg01", "seg02")}), encoding="utf-8")
    return seg_json, parts_dir, audio


def _spy_empty_frames(monkeypatch):
    seen = []
    real = ck.detect_empty_frames

    def spy(path, **kw):
        seen.append(kw)
        return real(path, **kw)
    monkeypatch.setattr(mg.bl_checker, "detect_empty_frames", spy)
    return seen


def test_merge_arm_a_headline_gives_the_gate_the_arm_a_mask(tmp_path, monkeypatch):
    seen = _spy_empty_frames(monkeypatch)
    seg_json, parts_dir, audio = _clean_two_part_job(tmp_path)
    headline = ck.parse_headline(_ARM_A_HEADLINE)
    mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4", headline=headline)
    assert seen == [ck.arm_mask_kwargs(headline)]
    assert seen[0]["bug_side"] == "left" and len(seen[0]["extra_zones"]) == 1


def test_main_beats_arm_a_object_passes_the_mask_bare_list_does_not(tmp_path, monkeypatch):
    seen = _spy_empty_frames(monkeypatch)
    seg_json, parts_dir, audio = _clean_two_part_job(tmp_path)
    base = [str(seg_json), "--parts", str(parts_dir), "--audio", str(audio), "-o", str(tmp_path / "final.mp4")]
    arm_a = tmp_path / "beats-a.json"
    arm_a.write_text(json.dumps({"headline": _ARM_A_HEADLINE, "beats": []}, ensure_ascii=False), encoding="utf-8")
    arm_b = tmp_path / "beats-b.json"
    arm_b.write_text("[]", encoding="utf-8")
    assert mg.main(base + ["--beats", str(arm_a)]) == 0
    assert mg.main(base + ["--beats", str(arm_b)]) == 0
    assert mg.main(base) == 0
    assert seen[0]["bug_side"] == "left"
    assert seen[1] == {} and seen[2] == {}


def test_main_beats_bad_schema_exits_2_before_merging(tmp_path, monkeypatch):
    seen = _spy_empty_frames(monkeypatch)
    seg_json, parts_dir, audio = _clean_two_part_job(tmp_path)
    bad = tmp_path / "beats-bad.json"
    bad.write_text(json.dumps({"beats": []}), encoding="utf-8")
    rc = mg.main([str(seg_json), "--parts", str(parts_dir), "--audio", str(audio),
                  "-o", str(tmp_path / "final.mp4"), "--beats", str(bad)])
    assert rc == 2 and seen == []


# ── KIN-entry grace (task-c32c40e8, CMO ruling 2026-10-01): with --beats, <=4 empty frames from a KIN t0 are excused
#    while the brand mark and the legal pill are on screen. The seam sits on the KIN's t0, as EP58's 71.567 s did. ──

import bl_mark_clips as mc  # noqa: E402

SEAM_FRAME = 45   # 1.5 s


def _kin_job(tmp_path, flat_frames=4, sides=("right",)):
    """Two 45-frame 1080x1920 parts; part 2 opens with `flat_frames` bare-plate frames (an empty KIN entry), the brand
    mark and the legal pill on every frame of both."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    mc.marked_clip(parts_dir / "seg01.mp4", frames=45, sides=sides)
    mc.marked_clip(parts_dir / "seg02.mp4", frames=45, sides=sides, flat=[(0, flat_frames - 1)] if flat_frames else ())
    audio = tmp_path / "audio.wav"
    _silent_audio(audio, 3.0)
    seg_json = tmp_path / "segments.json"
    seg_json.write_text(json.dumps({"segments": _segments("seg01", "seg02")}), encoding="utf-8")
    return seg_json, parts_dir, audio


def _kin_beat(t0=1.5, mode="KIN"):
    extra = {"img": "real/x.png", "box": [200, 300, 400, 500]} if mode == "COMP" else {}
    return {"tag": "CURIOSITY-5", "t0": t0, "t1": t0 + 1.0, "mode": mode, "extra": extra}


def test_merge_without_beats_still_refuses_an_empty_kin_entry_at_a_seam(tmp_path):
    seg_json, parts_dir, audio = _kin_job(tmp_path)
    result = mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4")
    assert result["pass"] is False
    assert result["gates"]["empty_frames"] == [1.5, 1.533, 1.567, 1.6]
    assert result["gates"]["seam_failures"][0]["seam_frame"] == SEAM_FRAME
    assert "empty_frames_excused" not in result["gates"]


def test_merge_with_beats_excuses_the_first_four_frames_of_a_kin_entry(tmp_path):
    seg_json, parts_dir, audio = _kin_job(tmp_path)
    result = mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4", beats=[_kin_beat()])
    assert result["pass"] is True, result["gates"]
    assert result["gates"]["empty_frames"] == [] and result["gates"]["seam_failures"] == []
    assert [e["entry_frame"] for e in result["gates"]["empty_frames_excused"]] == [1, 2, 3, 4]
    assert {e["beat"] for e in result["gates"]["empty_frames_excused"]} == {"CURIOSITY-5"}


def test_merge_with_beats_refuses_a_fifth_empty_frame(tmp_path):
    seg_json, parts_dir, audio = _kin_job(tmp_path, flat_frames=5)
    result = mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4", beats=[_kin_beat()])
    assert result["pass"] is False
    assert result["gates"]["empty_frames"] == [1.633]
    assert "empty_frames" in mg.failed_gate_names(result)


def test_merge_with_beats_does_not_excuse_a_beat_that_is_not_kin(tmp_path):
    seg_json, parts_dir, audio = _kin_job(tmp_path)
    result = mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4",
                      beats=[_kin_beat(mode="COMP")])
    assert result["pass"] is False
    assert result["gates"]["empty_frames"] == [1.5, 1.533, 1.567, 1.6]
    assert result["gates"]["seam_failures"] and result["gates"]["empty_frames_excused"] == []


def test_merge_arm_a_with_beats_reads_the_left_mark(tmp_path):
    seg_json, parts_dir, audio = _kin_job(tmp_path, sides=("left",))
    headline = ck.parse_headline(_ARM_A_HEADLINE)
    result = mg.merge(_segments("seg01", "seg02"), parts_dir, audio, tmp_path / "final.mp4",
                      headline=headline, beats=[_kin_beat()])
    assert result["pass"] is True, result["gates"]
    assert len(result["gates"]["empty_frames_excused"]) == 4


def test_main_beats_switches_the_kin_grace_on(tmp_path):
    seg_json, parts_dir, audio = _kin_job(tmp_path)
    base = [str(seg_json), "--parts", str(parts_dir), "--audio", str(audio), "-o", str(tmp_path / "final.mp4")]
    beats = tmp_path / "beats.json"
    beats.write_text(json.dumps([_kin_beat()]), encoding="utf-8")
    assert mg.main(base) == 1
    assert mg.main(base + ["--beats", str(beats)]) == 0
