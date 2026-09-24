"""Unit tests for tools/bl_scripter.py (task-67bb7a11).

No live model call anywhere in this file -- `claude -p` is mocked by
monkeypatching subprocess.run / run_claude_p. ffmpeg IS exercised for real
(it's a local, free, deterministic binary, not a paid model) to prove frame
extraction actually produces a usable JPEG, using tiny lavfi-synthesized
fixtures instead of real episode media.

Run via: pytest tests/test_bl_scripter.py -q
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from tools import bl_scripter as sc


# ─────────────────────────── input parsing ──────────────────────────────

def test_read_script_tsv_handles_csv_quoted_screen_notes(tmp_path):
    # A screen note field can itself contain doubled-quote CSV escaping
    # (see prototypes/bl57-script/SCRIPT.tsv, CONTEXT-3's row) -- csv.reader
    # with delimiter="\t" must unescape it, a naive .split("\t") would not.
    p = tmp_path / "SCRIPT.tsv"
    p.write_text(
        'HOOK-1\tline one\tshot-a\tshow\tplain note\n'
        'HOOK-2\tline two\t\thook\t"note with a literal ""quoted"" word, and a comma"\n',
        encoding="utf-8",
    )
    rows = sc.read_script_tsv(p)
    assert [r["tag"] for r in rows] == ["HOOK-1", "HOOK-2"]
    assert rows[0]["shot"] == "shot-a"
    assert rows[0]["beat"] == "show"
    assert rows[1]["screen"] == 'note with a literal "quoted" word, and a comma'
    assert rows[1]["shot"] == ""


def test_read_timings_tsv_skips_header(tmp_path):
    p = tmp_path / "timings.tsv"
    p.write_text("tag\tt0\tt1\nHOOK-1\t0.18\t2.64\nHOOK-2\t3.08\t5.54\n", encoding="utf-8")
    timings = sc.read_timings_tsv(p)
    assert timings == {"HOOK-1": (0.18, 2.64), "HOOK-2": (3.08, 5.54)}


def test_read_jev_decisions_keys_by_line_and_question(tmp_path):
    p = tmp_path / "decisions.jsonl"
    p.write_text(
        json.dumps({"line_id": "HOOK-1", "question": "bl.beat", "choice": "show", "final": "show"}) + "\n"
        + json.dumps({"line_id": "HOOK-1", "question": "bl.focus_device", "choice": "spotlight"}) + "\n"
        + json.dumps({"line_id": "HOOK-2", "question": "bl.beat", "choice": "hook", "final": None}) + "\n",
        encoding="utf-8",
    )
    per_line = sc.read_jev_decisions(p)
    assert per_line["HOOK-1"]["bl.beat"]["final"] == "show"
    assert per_line["HOOK-1"]["bl.focus_device"]["choice"] == "spotlight"
    assert per_line["HOOK-2"]["bl.beat"]["choice"] == "hook"


def test_read_jev_decisions_missing_file_returns_empty(tmp_path):
    assert sc.read_jev_decisions(tmp_path / "nope.jsonl") == {}
    assert sc.read_jev_decisions(None) == {}


# ─────────────────────────── the per-line list ──────────────────────────

def _fixture_script_rows():
    return [
        {"tag": "HOOK-1", "spoken": "spoken one", "shot": "shot-a", "beat": "show", "screen": "screen one"},
        {"tag": "HOOK-2", "spoken": "spoken two", "shot": "", "beat": "hook", "screen": ""},
        {"tag": "HOOK-3", "spoken": "spoken three", "shot": "shot-b", "beat": "show", "screen": "screen three"},
    ]


def test_build_line_table_joins_timings_and_jev_and_sorts_by_t0():
    rows = _fixture_script_rows()
    timings = {"HOOK-1": (0.18, 2.64), "HOOK-2": (3.08, 5.54), "HOOK-3": (5.54, 7.38)}
    jev = {"HOOK-1": {"bl.beat": {"final": "show", "choice": "show"}}}
    lines = sc.build_line_table(rows, timings, jev, t_max=None)
    assert [l["tag"] for l in lines] == ["HOOK-1", "HOOK-2", "HOOK-3"]
    assert lines[0]["jev_decision"] == "show"
    assert lines[1]["jev_decision"] is None
    assert lines[0]["spoken"] == "spoken one"
    assert lines[0]["screen"] == "screen one"


def test_build_line_table_respects_t_max():
    rows = _fixture_script_rows()
    timings = {"HOOK-1": (0.18, 2.64), "HOOK-2": (3.08, 5.54), "HOOK-3": (5.54, 7.38)}
    lines = sc.build_line_table(rows, timings, {}, t_max=5.0)
    assert [l["tag"] for l in lines] == ["HOOK-1", "HOOK-2"]


def test_build_line_table_drops_tags_missing_from_timings():
    rows = _fixture_script_rows()
    timings = {"HOOK-1": (0.18, 2.64)}  # HOOK-2/HOOK-3 have no timing row
    lines = sc.build_line_table(rows, timings, {}, t_max=None)
    assert [l["tag"] for l in lines] == ["HOOK-1"]


# ─────────────────────────── frame extraction ────────────────────────────

def _make_still(path: Path, w: int, h: int, color=(200, 30, 30)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (w, h), color).save(path)


def _make_tiny_video(path: Path, w=320, h=568, dur=1.0, fps=10) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate={fps}:duration={dur}",
         "-pix_fmt", "yuv420p", str(path)],
        check=True, capture_output=True,
    )


def test_find_still_checks_real_then_third_party(tmp_path):
    media_dir = tmp_path / "media"
    _make_still(media_dir / "third-party" / "some-shot.jpg", 100, 100)
    assert sc.find_still(media_dir, "some-shot") == media_dir / "third-party" / "some-shot.jpg"
    _make_still(media_dir / "real" / "some-shot.png", 100, 100)
    # real/ wins when both exist (checked first)
    assert sc.find_still(media_dir, "some-shot") == media_dir / "real" / "some-shot.png"
    assert sc.find_still(media_dir, "") is None
    assert sc.find_still(media_dir, "missing-shot") is None


def test_scale_still_to_caps_width_and_preserves_aspect(tmp_path):
    src = tmp_path / "big.png"
    _make_still(src, 1600, 900)
    dst = tmp_path / "out" / "big.jpg"
    w, h = sc.scale_still_to(src, dst, max_w=sc.MAX_FRAME_W)
    assert dst.exists()
    assert w == sc.MAX_FRAME_W
    assert h == round(900 * sc.MAX_FRAME_W / 1600)


def test_scale_still_to_leaves_small_image_unscaled(tmp_path):
    src = tmp_path / "small.png"
    _make_still(src, 400, 300)
    dst = tmp_path / "out" / "small.jpg"
    w, h = sc.scale_still_to(src, dst, max_w=sc.MAX_FRAME_W)
    assert (w, h) == (400, 300)


def test_extract_video_frame_produces_scaled_jpeg(tmp_path):
    video = tmp_path / "lipsync_part_a.mp4"
    _make_tiny_video(video, w=1000, h=1800)
    dst = tmp_path / "frames" / "HOOK-1.jpg"
    w, h = sc.extract_video_frame(video, 0.2, dst, max_w=sc.MAX_FRAME_W)
    assert dst.exists()
    assert w == sc.MAX_FRAME_W


def test_find_lipsync_part_picks_part_a_for_early_t0(tmp_path):
    media_dir = tmp_path / "media"
    (media_dir).mkdir()
    _make_tiny_video(media_dir / "lipsync_part_a.mp4", dur=0.3)
    result = sc.find_lipsync_part(media_dir, 3.08)
    assert result is not None
    path, media_start = result
    assert path.name == "lipsync_part_a.mp4"
    assert media_start == 3.08  # offset 0.0 for part a


def test_find_lipsync_part_none_when_no_part_present(tmp_path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    assert sc.find_lipsync_part(media_dir, 3.08) is None


def test_prepare_frames_dedupes_repeated_stills_and_extracts_avatar_frames(tmp_path):
    media_dir = tmp_path / "media"
    _make_still(media_dir / "real" / "shot-a.png", 1080, 1920)
    _make_tiny_video(media_dir / "lipsync_part_a.mp4", w=640, h=1024, dur=1.0)
    lines = [
        {"tag": "HOOK-1", "t0": 0.1, "shot": "shot-a"},
        {"tag": "HOOK-2", "t0": 0.2, "shot": "shot-a"},  # same still, must dedupe
        {"tag": "HOOK-3", "t0": 0.3, "shot": ""},        # avatar-only line
        {"tag": "HOOK-4", "t0": 5.0, "shot": "missing-shot"},  # no file -> missing
    ]
    frames = sc.prepare_frames(lines, media_dir, tmp_path / "work")
    assert list(frames["stills"].keys()) == ["shot-a"]
    assert frames["stills"]["shot-a"]["path"].exists()
    assert list(frames["avatars"].keys()) == ["HOOK-3"]
    assert frames["avatars"]["HOOK-3"]["path"].exists()
    assert frames["missing"] == ["HOOK-4"]


# ─────────────────────────── schema validation ───────────────────────────

def _valid_beat(tag="HOOK-1"):
    return {"tag": tag, "t0": 0.1, "t1": 1.0, "mode": "FF", "extra": {"cap": "x"}}


def test_validate_beats_accepts_well_formed_rows():
    beats = [_valid_beat("HOOK-1"), _valid_beat("HOOK-2")]
    assert sc.validate_beats(beats, ["HOOK-1", "HOOK-2"]) == beats


def test_validate_beats_rejects_non_list():
    with pytest.raises(sc.ScripterSchemaError):
        sc.validate_beats({"beats": []}, ["HOOK-1"])


def test_validate_beats_rejects_missing_required_key():
    bad = {"tag": "HOOK-1", "t0": 0.1, "t1": 1.0, "mode": "FF"}  # no extra
    with pytest.raises(sc.ScripterSchemaError, match="missing required key"):
        sc.validate_beats([bad], ["HOOK-1"])


def test_validate_beats_rejects_bad_mode():
    bad = _valid_beat("HOOK-1")
    bad["mode"] = "ZOOM"
    with pytest.raises(sc.ScripterSchemaError, match="invalid mode"):
        sc.validate_beats([bad], ["HOOK-1"])


def test_validate_beats_rejects_missing_tag_vs_line_table():
    beats = [_valid_beat("HOOK-1")]
    with pytest.raises(sc.ScripterSchemaError, match="missing tags"):
        sc.validate_beats(beats, ["HOOK-1", "HOOK-2"])


def test_validate_beats_rejects_extra_tag_not_in_line_table():
    beats = [_valid_beat("HOOK-1"), _valid_beat("GHOST-1")]
    with pytest.raises(sc.ScripterSchemaError, match="unexpected tags"):
        sc.validate_beats(beats, ["HOOK-1"])


def test_extract_json_text_strips_markdown_fence():
    raw = '```json\n{"beats": []}\n```'
    assert sc.extract_json_text(raw) == '{"beats": []}'


def test_extract_json_text_takes_outermost_braces_when_no_fence():
    raw = 'here is my answer:\n{"beats": [1, 2]}\nthanks'
    assert sc.extract_json_text(raw) == '{"beats": [1, 2]}'


def test_extract_json_text_passthrough_when_already_clean():
    raw = '{"beats": []}'
    assert sc.extract_json_text(raw) == raw


# ─────────────────────────── claude-p backend (mocked) ──────────────────

def test_run_claude_p_parses_wrapper_json(monkeypatch):
    fake_stdout = json.dumps({"session_id": "abc123", "result": '{"beats": []}',
                               "usage": {"input_tokens": 10}, "num_turns": 1})

    def fake_run(cmd, capture_output, text):
        assert cmd[0] == "claude" and cmd[1] == "-p"
        assert "--allowed-tools" in cmd and "Read" in cmd
        return subprocess.CompletedProcess(cmd, 0, stdout=fake_stdout, stderr="")

    monkeypatch.setattr(sc.subprocess, "run", fake_run)
    wrapper = sc.run_claude_p("some prompt")
    assert wrapper["session_id"] == "abc123"


def test_run_claude_p_raises_on_nonzero_exit(monkeypatch):
    def fake_run(cmd, capture_output, text):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    monkeypatch.setattr(sc.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="exited 1"):
        sc.run_claude_p("some prompt")


def test_usage_from_transcript_sums_assistant_turns(tmp_path):
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {}}) + "\n"
        + json.dumps({"type": "assistant", "message": {"usage": {
            "input_tokens": 5, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 0, "output_tokens": 20}}}) + "\n"
        + json.dumps({"type": "assistant", "message": {"usage": {
            "input_tokens": 2, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 100, "output_tokens": 8}}}) + "\n",
        encoding="utf-8",
    )
    result = sc.usage_from_transcript(transcript)
    assert result["turns"] == 2
    assert result["tokens"] == {"input_tokens": 7, "cache_creation_input_tokens": 100,
                                 "cache_read_input_tokens": 100, "output_tokens": 28}


def test_run_scripter_claude_p_end_to_end_mocked(monkeypatch, tmp_path):
    lines = [{"tag": "HOOK-1", "t0": 0.1, "t1": 1.0, "spoken": "x", "screen": "", "shot": "", "jev_decision": None}]
    frames = {"stills": {}, "avatars": {}, "missing": []}

    wrapper = {
        "session_id": "no-such-session",
        "result": json.dumps({"beats": [{"tag": "HOOK-1", "t0": 0.1, "t1": 1.0, "mode": "FF", "extra": {"cap": "x"}}]}),
        "usage": {"input_tokens": 50, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 30},
        "num_turns": 1,
        "total_cost_usd": 0.01,
    }
    monkeypatch.setattr(sc, "run_claude_p", lambda prompt, model="sonnet": wrapper)

    beats, usage = sc.run_scripter_claude_p(lines, frames, tmp_path)
    assert beats == [{"tag": "HOOK-1", "t0": 0.1, "t1": 1.0, "mode": "FF", "extra": {"cap": "x"}}]
    assert usage["backend"] == "claude-p"
    assert usage["tokens"]["input_tokens"] == 50
    assert usage["cost_usd_reported_max_plan"] == 0.01
    assert usage["cost_usd_api_equivalent"] == pytest.approx(50 / 1e6 * 2.00 + 30 / 1e6 * 10.00)


def test_run_scripter_claude_p_raises_on_schema_mismatch(monkeypatch, tmp_path):
    lines = [{"tag": "HOOK-1", "t0": 0.1, "t1": 1.0, "spoken": "x", "screen": "", "shot": "", "jev_decision": None}]
    frames = {"stills": {}, "avatars": {}, "missing": []}
    wrapper = {
        "session_id": None,
        "result": json.dumps({"beats": [{"tag": "WRONG-TAG", "t0": 0.1, "t1": 1.0, "mode": "FF", "extra": {}}]}),
        "usage": {}, "num_turns": 1, "total_cost_usd": 0.0,
    }
    monkeypatch.setattr(sc, "run_claude_p", lambda prompt, model="sonnet": wrapper)
    with pytest.raises(sc.ScripterSchemaError):
        sc.run_scripter_claude_p(lines, frames, tmp_path)


def test_enrich_beats_with_still_metadata_rescales_box_to_native_pixels():
    # The model measures a box in the SCALED (frame_w x frame_h) image it
    # was shown; the tool must rescale it to the still's true native pixels
    # and fill in img/native_w/native_h itself rather than trust the model
    # to invent a correct file path (measured wrong in the live run).
    lines = [{"tag": "HOOK-1", "shot": "shot-a"}, {"tag": "HOOK-2", "shot": ""}]
    frames = {"stills": {"shot-a": {"path": Path("/tmp/x.jpg"), "frame_w": 441, "frame_h": 784,
                                     "native_w": 882, "native_h": 1568, "rel_source": "real/shot-a.png",
                                     "source": "/orig/real/shot-a.png"}},
              "avatars": {}, "missing": []}
    beats = [
        {"tag": "HOOK-1", "t0": 0, "t1": 1, "mode": "COMP", "extra": {"box": [50, 60, 100, 80], "cap": "x"}},
        {"tag": "HOOK-2", "t0": 1, "t1": 2, "mode": "FF", "extra": {"cap": "y"}},
    ]
    out = sc.enrich_beats_with_still_metadata(beats, lines, frames)
    assert out[0]["extra"]["img"] == "real/shot-a.png"
    assert out[0]["extra"]["native_w"] == 882
    assert out[0]["extra"]["native_h"] == 1568
    # frame is exactly half native resolution here -> box doubles
    assert out[0]["extra"]["box"] == [100.0, 120.0, 200.0, 160.0]
    # avatar-only line (no shot) is untouched
    assert "img" not in out[1]["extra"]


def test_enrich_beats_with_still_metadata_leaves_beats_without_a_still_unchanged():
    lines = [{"tag": "HOOK-2", "shot": ""}]
    beats = [{"tag": "HOOK-2", "t0": 0, "t1": 1, "mode": "FF", "extra": {"cap": "y"}}]
    out = sc.enrich_beats_with_still_metadata(beats, lines, {"stills": {}, "avatars": {}, "missing": []})
    assert out == [{"tag": "HOOK-2", "t0": 0, "t1": 1, "mode": "FF", "extra": {"cap": "y"}}]


def test_build_claude_p_prompt_lists_still_and_avatar_frame_paths(tmp_path):
    lines = [
        {"tag": "HOOK-1", "t0": 0.1, "t1": 1.0, "spoken": "s1", "screen": "sc1", "shot": "shot-a", "jev_decision": None},
        {"tag": "HOOK-2", "t0": 1.0, "t1": 2.0, "spoken": "s2", "screen": "", "shot": "", "jev_decision": "hook"},
    ]
    frames = {
        "stills": {"shot-a": {"path": tmp_path / "shot-a.jpg", "frame_w": 441, "frame_h": 784,
                               "native_w": 882, "native_h": 1568, "rel_source": "real/shot-a.png",
                               "source": str(tmp_path / "real" / "shot-a.png")}},
        "avatars": {"HOOK-2": {"path": tmp_path / "HOOK-2.jpg", "w": 882, "h": 1568,
                                "source": "lipsync_part_a.mp4", "media_start": 1.0}},
        "missing": [],
    }
    prompt = sc.build_claude_p_prompt(lines, frames)
    assert str(tmp_path / "shot-a.jpg") in prompt
    assert str(tmp_path / "HOOK-2.jpg") in prompt
    assert "HOOK-1" in prompt and "HOOK-2" in prompt
    assert "jev_decision='hook'" in prompt


def test_backend_flag_only_accepts_claude_p():
    ap = sc.build_arg_parser()
    args = ap.parse_args(["--script", "s.tsv", "--timings", "t.tsv", "--media-dir", "m"])
    assert args.backend == "claude-p"
    with pytest.raises(SystemExit):
        ap.parse_args(["--script", "s.tsv", "--timings", "t.tsv", "--media-dir", "m", "--backend", "api"])
