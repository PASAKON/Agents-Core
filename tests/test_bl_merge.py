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
