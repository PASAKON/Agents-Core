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


# ─────────────── CTO 2026-09-26 -- fixture-full never deletes staged files ────

@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_build_full_generator_refuses_to_drop_files_it_does_not_recreate(tmp_path):
    # task-9a4f1029 incident: a rebuild rmtree'd 37 scene clips staged
    # straight into generator/media/broll. The rebuild must refuse instead.
    episode_dir = _episode_work_dir(tmp_path)
    dest = tmp_path / "generator"
    run.build_full_generator(episode_dir, dest)
    staged = dest / "media" / "broll" / "S01.mp4"
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(b"scene-clip")

    with pytest.raises(SystemExit) as exc:
        run.build_full_generator(episode_dir, dest)
    assert "media/broll/S01.mp4" in str(exc.value)
    assert staged.read_bytes() == b"scene-clip"          # untouched
    assert not (tmp_path / "generator.staging").exists()  # no leftovers

    run.build_full_generator(episode_dir, dest, force=True)
    assert not staged.exists()


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_build_full_generator_keeps_files_that_live_in_the_source(tmp_path):
    episode_dir = _episode_work_dir(tmp_path)
    (episode_dir / "media" / "broll").mkdir()
    (episode_dir / "media" / "broll" / "S01.mp4").write_bytes(b"scene-clip")
    (episode_dir / "jev").mkdir()
    (episode_dir / "jev" / "decisions.base.jsonl").write_text("{}\n", encoding="utf-8")
    dest = tmp_path / "generator"

    run.build_full_generator(episode_dir, dest)
    run.build_full_generator(episode_dir, dest)   # a second rebuild is safe

    assert (dest / "media" / "broll" / "S01.mp4").read_bytes() == b"scene-clip"
    assert (dest / "jev" / "decisions.base.jsonl").is_file()


# ───────── task-ee30ba95 -- fixture-full carries the EPISODE's own avatar windows ─────
# build_cut.py (GENERATOR_BRANCH) is EP57's: lip_offset {a:0, b:68.3, c:137.16}, LIP_DUR
# {14.9, 14.65, 15.35}, TOTAL_DUR 153.0. EP58's lipsync parts sit at 0 / 38.77 / 80.84 and last
# 16.0 / 17.2 / 14.333 s, so a generator staged unchanged made bl_compose's window refusal check
# EP57's windows against EP58's beats.

from tools import bl_compose
from tools.bl_compose import ComposeError

EP58_OFFSETS = [{"part": "A", "file": "a.mp4", "true_s": 0.0, "r": 0.999},
                {"part": "B", "file": "b.mp4", "true_s": 38.77, "r": 1.0},
                {"part": "C", "file": "c.mp4", "true_s": 80.84, "r": 1.0}]
EP58_LIP_SECONDS = {"a": 16.0, "b": 17.2, "c": 14.333}


def _staged_total_dur(generator_dir) -> float:
    import ast
    tree = ast.parse((generator_dir / "build_cut.py").read_text(encoding="utf-8"))
    return next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "TOTAL_DUR" for t in n.targets))


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def _ep58_work_dir(tmp_path, offsets=None, with_episode_json=True):
    """An EP58-shaped work dir: tiny but real lip videos (ffprobe-able), a real 3.0 s mp3."""
    d = _episode_work_dir(tmp_path)
    (d / "audio-hq.mp3").unlink()
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=3.0", "-c:a", "libmp3lame", str(d / "audio-hq.mp3"))
    for part, seconds in EP58_LIP_SECONDS.items():
        _ffmpeg("-f", "lavfi", "-i", f"color=c=black:s=64x64:r=30:d={seconds}", "-pix_fmt", "yuv420p",
                str(d / "media" / f"lip_{part}.mp4"))
    (d / "offsets.json").write_text(json.dumps(EP58_OFFSETS if offsets is None else offsets), encoding="utf-8")
    if with_episode_json:
        (d / "episode.json").write_text(json.dumps({"episode": 58, "date": "2026-10-01"}), encoding="utf-8")
    (d / "real").mkdir()
    (d / "real" / "REAL_MANIFEST.json").write_text("{}", encoding="utf-8")
    return d


def test_thai_short_date_is_day_month_buddhist_year():
    assert run.thai_short_date("2026-10-01") == "1 ต.ค. 69"
    assert run.thai_short_date("2026-09-23") == "23 ก.ย. 69"       # what assemble.py hardcodes for EP57


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_build_full_generator_without_offsets_json_keeps_ep57_windows(tmp_path):
    episode_dir = _episode_work_dir(tmp_path)           # no offsets.json: the EP57 shape
    assert run.lip_layout(episode_dir) is None
    run.build_full_generator(episode_dir, tmp_path / "generator")
    funcs = bl_compose.load_generator_functions(tmp_path / "generator")
    assert funcs["LIP_DUR"] == {"lip_a": 14.9, "lip_b": 14.65, "lip_c": 15.35}
    assert funcs["lip_offset"]("lip_b") == 68.3
    assert run.EP57_BRAND_BUG_DATE in (tmp_path / "generator" / "assemble.py").read_text(encoding="utf-8")
    assert _staged_total_dur(tmp_path / "generator") == 153.0


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_build_full_generator_carries_the_episodes_own_lip_windows(tmp_path):
    episode_dir = _ep58_work_dir(tmp_path)
    dest = tmp_path / "generator"
    run.build_full_generator(episode_dir, dest)

    funcs = bl_compose.load_generator_functions(dest)
    assert [funcs["lip_offset"](n) for n in ("lip_a", "lip_b", "lip_c")] == [0.0, 38.77, 80.84]
    # video length - 0.05..0.08 on the 0.05 s grid, EP57's own rule
    assert funcs["LIP_DUR"] == {"lip_a": 15.95, "lip_b": 17.15, "lip_c": 14.25}
    total = _staged_total_dur(dest)                                         # the decoded 3.0 s mp3, floored to a frame
    assert abs(total - 3.0) < 0.1 and abs(total * 30 - round(total * 30)) < 1e-6
    assert [funcs["pick_lip"](t) for t in (0.0, 38.76, 38.77, 80.83, 80.84, 95.0)] == \
        ["lip_a", "lip_a", "lip_b", "lip_b", "lip_c", "lip_c"]

    # the refusal now checks EP58's windows: t0=15.0 is inside lip_a for EP58 (not for EP57's [0,14.9)),
    # t0=70.0 is inside nothing for EP58 (inside EP57's lip_b [68.3,82.95)).
    bl_compose.check_avatar_window("X", "FF", 15.0, funcs["pick_lip"](15.0), funcs)
    with pytest.raises(ComposeError) as exc:
        bl_compose.check_avatar_window("X", "FF", 70.0, funcs["pick_lip"](70.0), funcs)
    assert "[38.77, 55.92)" in str(exc.value) and "[80.84, 95.09)" in str(exc.value)
    assert "68.3" not in str(exc.value)

    assert run.check_lip_windows(dest) == []
    # only the episode's dates/windows changed in the generator: the redaction still holds
    assert "BEATS = []" in (dest / "build_cut.py").read_text(encoding="utf-8")


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_build_full_generator_stamps_the_episode_date_and_stages_real(tmp_path):
    episode_dir = _ep58_work_dir(tmp_path)
    dest = tmp_path / "generator"
    run.build_full_generator(episode_dir, dest)
    assemble = (dest / "assemble.py").read_text(encoding="utf-8")
    assert '<div class="dt2">1 ต.ค. 69</div>' in assemble and run.EP57_BRAND_BUG_DATE not in assemble
    assert (dest / "real" / "REAL_MANIFEST.json").is_file()


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_build_full_generator_refuses_a_weak_lip_offset(tmp_path):
    weak = [dict(EP58_OFFSETS[0], r=0.5), *EP58_OFFSETS[1:]]
    episode_dir = _ep58_work_dir(tmp_path, offsets=weak)
    with pytest.raises(SystemExit) as exc:
        run.build_full_generator(episode_dir, tmp_path / "generator")
    assert "r=0.5" in str(exc.value)
    assert not (tmp_path / "generator").exists()


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_check_lip_windows_warns_when_ep57_windows_sit_on_other_lip_parts(tmp_path):
    # the failure this guards: no offsets.json, so EP57's LIP_DUR is kept, but the lip parts are EP58's
    episode_dir = _ep58_work_dir(tmp_path, with_episode_json=False)
    (episode_dir / "offsets.json").unlink()
    dest = tmp_path / "generator"
    run.build_full_generator(episode_dir, dest)
    warnings = run.check_lip_windows(dest)
    assert len(warnings) == 3 and all(w.startswith("WARNING") for w in warnings)
    assert "lip_a lasts 14.9s but media/lip_a.mp4 is 16.00s" in warnings[0]


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_spawn_full_for_another_episode_swaps_in_its_windows_and_paths(tmp_path, capsys):
    episode_dir = _ep58_work_dir(tmp_path)
    run.build_full_generator(episode_dir, episode_dir / run.FULL_FIXTURE_DIR_NAME)

    class _NS:
        episode_work_dir = str(episode_dir)

    assert run.cmd_spawn_full(_NS()) == 0
    out = capsys.readouterr().out
    assert "episode 58" in out and "episode 57" not in out
    assert "[0, 15.95)" in out and "[38.77, 55.92)" in out and "[80.84, 95.09)" in out
    assert "[0, 14.9)" not in out and "bl-split-ep57" not in out
    assert str(episode_dir) in out


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_fixture_full_dest_defaults_under_the_given_episode_not_ep57(tmp_path, capsys):
    episode_dir = _ep58_work_dir(tmp_path)
    args = run.build_arg_parser().parse_args(["fixture-full", "--episode-work-dir", str(episode_dir)])
    assert args.dest is None
    assert args.func(args) == 0
    out = capsys.readouterr().out
    assert (episode_dir / "generator" / "build_cut.py").is_file()
    assert "avatar windows bl_compose will enforce: lip_a [0, 15.95), lip_b [38.77, 55.92), lip_c [80.84, 95.09)" in out
    assert "WARNING: fixture-full is missing matte" in out        # this fixture has none; the real run must not
    assert str(run.FULL_EPISODE_WORK_DIR) not in out


def test_check_broll_coverage_names_scene_clips_that_were_never_made(tmp_path):
    (tmp_path / "media" / "broll").mkdir(parents=True)
    (tmp_path / "SCRIPT.tsv").write_text("HOOK-1\ta\tx\tshow\tn\nHOOK-2\tb\ty\tshow\tn\nHOOK-3\tc\tz\tshow\tn\n",
                                          encoding="utf-8")
    assert run.check_broll_coverage(tmp_path) == []             # no broll staged at all: nothing to compare to
    for n in (1, 3):
        (tmp_path / "media" / "broll" / f"S{n:02d}.mp4").write_bytes(b"x")
    warnings = run.check_broll_coverage(tmp_path)
    assert len(warnings) == 1 and "S02.mp4 (HOOK-2)" in warnings[0] and warnings[0].startswith("WARNING")


# ───────── task-406c21f3 -- arm A on the REAL staged generator, and the tool push ─────────

def _arm_a_real_beats():
    return [
        {"tag": "H1", "t0": 0.0, "t1": 1.2, "mode": "COMP", "extra": {"cap": "Hook one"}},
        {"tag": "H2", "t0": 1.2, "t1": 2.4, "mode": "COMP", "extra": {"cap": "Hook two"}},
        {"tag": "H3", "t0": 2.4, "t1": 3.4, "mode": "COMP", "extra": {}},
        {"tag": "E1", "t0": 3.4, "t1": 5.0, "mode": "EVID",
         "extra": {"img": "real/x.png", "native_w": 1080, "native_h": 1500, "box": [40, 800, 900, 500],
                   "credit": "WikiFX", "cap": "Evidence"}},
        {"tag": "K1", "t0": 5.0, "t1": 6.0, "mode": "KIN",
         "extra": {"broll": "broll/S01.mp4", "lines": [["w", "Hello"]]}},
    ]


@pytest.mark.skipif(not _generator_branch_available(),
                     reason=f"{run.GENERATOR_BRANCH} not fetched in this clone")
def test_arm_a_composes_on_the_real_staged_generator_without_touching_it(tmp_path):
    from tools import bl_checker
    episode_dir = _ep58_work_dir(tmp_path)
    (episode_dir / "media" / "real").mkdir()
    for name in ("a", "b", "c", "x"):
        (episode_dir / "media" / "real" / f"{name}.png").write_bytes(b"png")
    dest = tmp_path / "generator"
    run.build_full_generator(episode_dir, dest)
    snapshot = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file() and "media" not in p.relative_to(dest).parts}

    headline = bl_checker.parse_headline({
        "lines": ["โบรกเกอร์ไม่อยากให้คุณรู้", "Weltrade เปิดบัญชีง่ายจริงไหม"], "red": "ไม่อยากให้คุณรู้",
        "bug_side": "left",
        "backdrop": [{"t0": 0.0, "src": "real/a.png"}, {"t0": 1.0, "src": "real/b.png"},
                     {"t0": 2.0, "src": "real/c.png"}]})
    beats = _arm_a_real_beats()
    html = bl_compose.compose(beats, dest, 6.0, tmp_path / "out", headline=headline).read_text(encoding="utf-8")

    # the real template's own anchors took the plate and the override; the real assemble.py ran unmodified
    assert html.count('id="hl"') == 1 and html.count('<style id="arm-a-bug">') == 1
    assert html.index('<style id="arm-a-bug">') < html.index("</head>") < html.index('id="hl"') < html.index('id="bug"')
    assert 'src="media/real/a.png"' in html and 'src="media/real/c.png"' in html
    assert 'data-composition-id="main"' in html and "spotlight(" in html and "caption(" in html
    assert bl_checker.check_headline_plate(headline, html) == []
    assert bl_checker.check_headline(headline, beats) == []
    assert {p: p.read_bytes() for p in snapshot} == snapshot, "the staged generator must not be edited"

    # the same generator, an arm-B table: no arm-A artefact anywhere
    arm_b = [b for b in beats if b["mode"] != "COMP"]
    html_b = bl_compose.compose(arm_b, dest, 6.0, tmp_path / "out-b").read_text(encoding="utf-8")
    assert 'id="hl"' not in html_b and "arm-a" not in html_b and "hl-red" not in html_b
    assert '<div class="bug" id="bug">' in html_b


def test_push_tool_ships_bl_checker_with_bl_compose(monkeypatch):
    import argparse
    # bl_compose imports bl_checker's arm-A schema; a box that gets one without the other cannot import it
    sent = []
    monkeypatch.setattr(run, "sh", lambda cmd, **kw: sent.append(cmd))
    assert run.cmd_push_tool(argparse.Namespace(worktree="/opt/wt")) == 0
    assert [c[2].split("/")[-1] for c in sent] == ["bl_compose.py", "bl_checker.py"]
    assert all(c[:2] == ["scp", "-q"] and c[3] == f"{run.SSH_ALIAS}:/opt/wt/tools/{c[2].split('/')[-1]}" for c in sent)
    assert all(c[2] == str(run.ROOT / "tools" / c[2].split("/")[-1]) for c in sent)
