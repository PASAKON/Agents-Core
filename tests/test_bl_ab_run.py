"""Unit tests for tools/bl_ab_run.py's spawn-full/spawn-seg (task-99f3d2e8)
and build_full_generator (task-9a4f1029).

Only the pure, local pieces -- everything else in bl_ab_run.py drives ssh/
scp/delegate_task against a real box and has no unit test for the same
reason (no fixture can stand in for a real remote host). spawn-full/
spawn-seg are pure string plumbing over the checked-in BRIEF-*.md files, so
they're worth covering directly. build_full_generator/cmd_fixture_full do
no ssh/scp either (fixture-full's own comment: "this box IS Contabo
already... no ssh/scp round-trip") -- also worth covering, though it does
run two real (read-only) `git show` calls against GENERATOR_BRANCH, so
those tests skip if that ref isn't available in this clone.

Run via: pytest tests/test_bl_ab_run.py -q
"""
from __future__ import annotations

import io
import json
import subprocess
from contextlib import redirect_stdout

import pytest

from tools import bl_ab_run as run


def _generator_branch_available() -> bool:
    r = subprocess.run(["git", "rev-parse", "--verify", run.GENERATOR_BRANCH],
                        cwd=run.ROOT, capture_output=True)
    return r.returncode == 0


def _capture(func, args) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = func(args)
    assert rc == 0
    return buf.getvalue()


def test_brief_arm1_md_and_brief_seg_md_exist_on_disk():
    assert run.BRIEF_ARM1_PATH.is_file()
    assert run.BRIEF_SEG_PATH.is_file()


def test_brief_body_strips_the_explainer_above_the_marker():
    body = run._brief_body(run.BRIEF_ARM1_PATH)
    assert body.startswith("## Brief given to the worker")
    assert "CTO ruling 2026-09-25" not in body  # that's in the stripped explainer


def test_spawn_full_prints_brief_arm1_verbatim(capsys):
    class _NS: ...
    rc = run.cmd_spawn_full(_NS())
    assert rc == 0
    out = capsys.readouterr().out
    assert "## Brief given to the worker" in out
    assert "seconds 0.0 to" in out and "153.0333" in out
    assert "DRY RUN" in out and "NOT spawned" in out


def test_spawn_seg_substitutes_all_four_placeholders(tmp_path, capsys):
    segments = {"segments": [
        {"id": "seg02", "t0": 39.3, "t1": 65.8333, "frame_count": 796,
         "lines": [{"tag": "CONTEXT-3", "t0": 39.66, "t1": 43.16, "text": "x"},
                   {"tag": "MAIN-1", "t0": 54.84, "t1": 58.3, "text": "y"}]},
    ]}
    seg_path = tmp_path / "segments.json"
    seg_path.write_text(json.dumps(segments), encoding="utf-8")

    class _NS:
        segments = str(seg_path)
        seg = "seg02"

    rc = run.cmd_spawn_seg(_NS())
    assert rc == 0
    out = capsys.readouterr().out
    assert "{seg}" not in out and "{t0}" not in out and "{t1}" not in out and "{tags}" not in out
    assert "segment `seg02`" in out
    assert "39.3 to 65.8333" in out
    assert "CONTEXT-3, MAIN-1" in out
    assert "prototypes/bl-split-ep57/seg02/beats.json" in out
    assert "--t0 39.3 --t-max 65.8333" in out


def test_spawn_seg_unknown_segment_errors(tmp_path, capsys):
    seg_path = tmp_path / "segments.json"
    seg_path.write_text(json.dumps({"segments": [{"id": "seg01", "t0": 0, "t1": 1, "lines": []}]}),
                         encoding="utf-8")

    class _NS:
        segments = str(seg_path)
        seg = "seg99"

    rc = run.cmd_spawn_seg(_NS())
    assert rc == 1
    assert "not found" in capsys.readouterr().err


def test_brief_seg_template_has_no_stray_format_braces_outside_the_four_placeholders():
    # cmd_spawn_seg uses plain .replace(), not str.format(), specifically
    # because the brief's body is full of literal JSON-shaped braces
    # (beats.json's own {"tag","t0",...} shape) -- prove those substrings
    # survive a substitution untouched (they would raise/vanish under
    # .format()).
    body = run._brief_body(run.BRIEF_SEG_PATH)
    substituted = (body.replace("{seg}", "segXX").replace("{t0}", "0.0")
                        .replace("{t1}", "1.0").replace("{tags}", "TAG-1"))
    assert '{"tag", "t0", "t1", "mode", "extra"}' in substituted
    assert '{"cap": "<caption>"}' in substituted


# ─────────── task-9a4f1029 item 6 -- BRIEF-arm1.md / BRIEF-seg.md identity ───

def test_briefs_share_identical_editorial_content_outside_the_split():
    """The two briefs must stay word-for-word identical outside the range
    description and BRIEF-seg.md's own "Segment contract" section (both
    files' own header text says so; task-99f3d2e8's RUNLOG recorded this as
    a small ad-hoc Python diff, never a checked-in test -- this makes that
    check durable so a future edit to one brief can't silently drift from
    the other, exactly what task-9a4f1029 risked by adding the avatar-
    windows bullet to both)."""
    arm1 = run._brief_body(run.BRIEF_ARM1_PATH)
    seg = run._brief_body(run.BRIEF_SEG_PATH)

    # normalise the intentionally-different range wording so the rest can
    # be compared line for line.
    arm1_norm = arm1.replace(
        "You are cutting the WHOLE BLACK LIQUIDITY episode 57 -- seconds 0.0 to\n"
        "153.0333 (all 40 lines, tags HOOK-1..4 through SUMMARY-1..9) -- exactly as\n"
        "if this were a real episode to finish. Your only job is to make the same",
        "SPLIT-RANGE-PLACEHOLDER Your only job is to make the same")
    seg_norm = seg.replace(
        "You are cutting BLACK LIQUIDITY episode 57, segment `{seg}` -- seconds\n"
        "{t0} to {t1} (tags {tags}) -- exactly as if this were a real episode to\n"
        "finish. This is Arm 2 (\"ช่วยกัน\") of the split-editor A/B: N editors each\n"
        "cut one segment in parallel from the SAME fixed skill + template, and the\n"
        "CTO concats/merges the parts afterward with `tools/bl_merge.py` -- you\n"
        "never see or touch any other segment. Your only job is to make the same",
        "SPLIT-RANGE-PLACEHOLDER Your only job is to make the same")

    # BRIEF-seg.md's own "Segment contract" section (and everything after
    # it -- write/render/push/report, which differ by design between a
    # whole-episode and a ranged render) has no counterpart in BRIEF-arm1.md
    # at all, so it's excluded from both sides of the comparison entirely.
    seg_marker = "## Segment contract"
    arm1_marker = "**Write** `prototypes/bl-split-ep57/arm1/beats.json`."
    assert seg_marker in seg_norm and arm1_marker in arm1_norm
    shared_arm1 = arm1_norm[:arm1_norm.index(arm1_marker)]
    shared_seg = seg_norm[:seg_norm.index(seg_marker)]
    assert shared_arm1 == shared_seg


# ───────── task-9a4f1029 item 4 -- avatar windows named in both briefs ─────

def test_briefs_name_the_avatar_windows_identically():
    arm1 = run._brief_body(run.BRIEF_ARM1_PATH)
    seg = run._brief_body(run.BRIEF_SEG_PATH)
    for window in ("[0, 14.9)", "[68.3, 82.95)", "[137.16, 152.51)"):
        assert window in arm1, f"BRIEF-arm1.md missing avatar window {window}"
        assert window in seg, f"BRIEF-seg.md missing avatar window {window}"


# ─────────────── task-9a4f1029 item 5 -- fixture-full stages voice.mp3 ────

def _episode_work_dir(tmp_path, audio_bytes: bytes = b"fake-mp3-bytes"):
    d = tmp_path / "episode"
    (d / "media").mkdir(parents=True)
    (d / "audio-hq.mp3").write_bytes(audio_bytes)
    (d / "SCRIPT.tsv").write_text("1\tHOOK-1\ttext\t\tshow\tnote\n", encoding="utf-8")
    (d / "timings.tsv").write_text("HOOK-1\t0.0\t1.0\n", encoding="utf-8")
    return d


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_build_full_generator_stages_voice_mp3_from_audio_hq(tmp_path):
    # assemble.py (off-limits) hardcodes <audio src="media/voice.mp3">;
    # fixture-full never staged that file (the CTO copied it by hand for
    # task-1a5eb073's pilot) -- this is the fix, verified directly.
    audio_bytes = b"fake-mp3-bytes-for-voice-staging-test"
    episode_dir = _episode_work_dir(tmp_path, audio_bytes)
    dest = tmp_path / "generator"

    run.build_full_generator(episode_dir, dest)

    voice_mp3 = dest / "media" / "voice.mp3"
    assert voice_mp3.is_file()
    assert voice_mp3.read_bytes() == audio_bytes
    # the master track (used for the real mux) is staged too, same source
    assert (dest / "audio-hq.mp3").read_bytes() == audio_bytes


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_cmd_fixture_full_end_to_end_stages_voice_mp3(tmp_path, capsys):
    episode_dir = _episode_work_dir(tmp_path)
    dest_dir = tmp_path / "generator"

    class _NS:
        episode_work_dir = str(episode_dir)
        dest = str(dest_dir)

    rc = run.cmd_fixture_full(_NS())
    assert rc == 0
    assert (dest_dir / "media" / "voice.mp3").is_file()
