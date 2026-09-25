"""Unit tests for the BLACK LIQUIDITY layered EDL (task-42e3b6af):
scripts/bl_edl.py (shared pure functions), scripts/bl_compose.py (layers ->
index.html) and scripts/bl_check.py (the P1 gate).

Pure functions only -- no ffmpeg, no hyperframes CLI, no network. These are
the checks a real episode's cut depends on (a gap, an overlap, a dangling
id, an avatar sitting on a WikiFX score), so each test is built to actually
fail if the logic regresses, not just to exercise the happy path.

Stdlib + pytest only, per requirements.txt (a test importing anything else
stops CI collection for every session -- evidence: 47f9d942).

Run via: pytest tests/test_bl_compose.py -q
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import scripts.bl_edl as bl_edl
import scripts.bl_compose as compose
import scripts.bl_check as check


# --------------------------------------------------------------- fixtures
def make_p1(events, **overrides):
    doc = {
        "episode": "epTEST",
        "duration": 10.0,
        "audio": {"media": "media/audio.mp3"},
        "bug_date": "1 ม.ค. 69",
        "lipsync_offsets": {"A": 0.0, "B": 58.72},
        "events": events,
    }
    doc.update(overrides)
    return doc


def avatar_event(eid, t0, t1, part="A"):
    return {
        "id": eid, "t0": t0, "t1": t1, "type": "plate",
        "params": {"role": "avatar", "kind": "video", "media": "media/lip_a.mp4",
                   "lipsync_part": part, "avatar_mode": "full", "darken": False},
    }


def scene_event(eid, t0, t1, darken=False):
    return {
        "id": eid, "t0": t0, "t1": t1, "type": "plate",
        "params": {"role": "scene", "kind": "video", "media": "media/s01.mp4",
                    "media_start": 0.0, "avatar_mode": "none", "darken": darken},
    }


def bg_event(eid, t0, t1):
    return {
        "id": eid, "t0": t0, "t1": t1, "type": "plate",
        "params": {"role": "bg", "avatar_mode": "none"},
    }


def real_still_event(eid, t0, t1, real_source="real/score.png", composite=False):
    p = {"role": "real_still", "kind": "image", "media": "real/score.png",
         "media_start": 0.0, "avatar_mode": "none", "darken": False,
         "real_source": real_source}
    if composite:
        p["avatar_mode"] = "composite"
        p["avatar"] = {"media": "media/matte/lip_a-matte.webm", "lipsync_part": "A"}
    return {"id": eid, "t0": t0, "t1": t1, "type": "plate", "params": p}


# ============================================================ validate_p1
def test_validate_p1_accepts_a_legal_document():
    doc = make_p1([avatar_event("p1-1", 0.0, 2.0), scene_event("p1-2", 2.0, 10.0)])
    bl_edl.validate_p1(doc)  # must not raise


def test_validate_p1_rejects_unknown_role():
    doc = make_p1([{"id": "p1-1", "t0": 0.0, "t1": 1.0, "type": "plate",
                     "params": {"role": "bogus", "kind": "video", "media": "x.mp4",
                                "media_start": 0.0, "avatar_mode": "none"}}])
    with pytest.raises(bl_edl.EDLError, match="unknown role"):
        bl_edl.validate_p1(doc)


def test_validate_p1_rejects_full_avatar_mode_on_non_avatar_role():
    ev = scene_event("p1-1", 0.0, 1.0)
    ev["params"]["avatar_mode"] = "full"
    doc = make_p1([ev])
    with pytest.raises(bl_edl.EDLError, match="only legal on role 'avatar'"):
        bl_edl.validate_p1(doc)


def test_validate_p1_rejects_avatar_role_missing_lipsync_part():
    ev = avatar_event("p1-1", 0.0, 1.0)
    del ev["params"]["lipsync_part"]
    doc = make_p1([ev])
    with pytest.raises(bl_edl.EDLError, match="requires params.lipsync_part"):
        bl_edl.validate_p1(doc)


def test_validate_p1_rejects_darken_on_real_footage():
    ev = real_still_event("p1-1", 0.0, 1.0)
    ev["params"]["darken"] = True
    doc = make_p1([ev])
    with pytest.raises(bl_edl.EDLError, match="darken=true is illegal"):
        bl_edl.validate_p1(doc)


def test_validate_p1_rejects_real_role_missing_real_source():
    ev = real_still_event("p1-1", 0.0, 1.0)
    del ev["params"]["real_source"]
    doc = make_p1([ev])
    with pytest.raises(bl_edl.EDLError, match="requires params.real_source"):
        bl_edl.validate_p1(doc)


def test_validate_p1_rejects_composite_over_avatar_role():
    ev = avatar_event("p1-1", 0.0, 1.0)
    ev["params"]["avatar_mode"] = "composite"
    ev["params"]["avatar"] = {"media": "x.webm", "lipsync_part": "A"}
    doc = make_p1([ev])
    with pytest.raises(bl_edl.EDLError, match="requires avatar_mode 'full'"):
        bl_edl.validate_p1(doc)


def test_validate_p1_rejects_duplicate_id():
    doc = make_p1([avatar_event("p1-1", 0.0, 1.0), scene_event("p1-1", 1.0, 2.0)])
    with pytest.raises(bl_edl.EDLError, match="duplicate id"):
        bl_edl.validate_p1(doc)


def test_validate_p1_accepts_bg_role_with_no_media():
    doc = make_p1([avatar_event("p1-1", 0.0, 2.0), bg_event("p1-2", 2.0, 10.0)])
    bl_edl.validate_p1(doc)  # must not raise -- a text-only stretch is legal


def test_validate_p1_rejects_bg_role_with_composite_avatar():
    ev = bg_event("p1-1", 0.0, 1.0)
    ev["params"]["avatar_mode"] = "composite"
    doc = make_p1([ev])
    with pytest.raises(bl_edl.EDLError, match="only supports avatar_mode 'none'"):
        bl_edl.validate_p1(doc)


def test_check_media_exists_skips_bg_events(tmp_path: Path):
    doc = make_p1([bg_event("p1-1", 0.0, 10.0)])
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "audio.mp3").write_bytes(b"x")
    assert bl_edl.check_media_exists(doc, tmp_path) == []


def test_compose_p1_renders_nothing_for_a_bg_event():
    doc = make_p1([avatar_event("p1-1", 0.0, 4.0), bg_event("p1-2", 4.0, 10.0)])
    template = bl_edl.DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    html = compose.compose_p1(doc, template)
    assert 'id="v1"' in html and 'id="v2"' not in html  # only p1-1's avatar tag, nothing for p1-2


def test_validate_p1_rejects_t0_not_less_than_t1():
    ev = scene_event("p1-1", 5.0, 5.0)
    doc = make_p1([ev])
    with pytest.raises(bl_edl.EDLError, match="must be < t1"):
        bl_edl.validate_p1(doc)


# ========================================================= lipsync seating
def test_p1_media_start_derives_from_offset():
    ev = avatar_event("p1-1", 9.46, 11.60, part="B")
    ms = bl_edl.p1_media_start(ev, {"B": 58.72})
    assert ms == pytest.approx(9.46 - 58.72, abs=1e-3)


def test_check_lipsync_seating_flags_part_not_yet_begun():
    # part B's own offset is 58.72s; using it at t0=9.46 asks to play the
    # file before it has started -- media_start would be negative.
    events = [avatar_event("p1-1", 9.46, 11.60, part="B")]
    problems = bl_edl.check_lipsync_seating(events, {"B": 58.72})
    assert len(problems) == 1
    assert "p1-1" in problems[0] and "<0" in problems[0]


def test_check_lipsync_seating_clean_when_offset_already_passed():
    events = [avatar_event("p1-1", 69.00, 72.60, part="B")]
    assert bl_edl.check_lipsync_seating(events, {"B": 58.72}) == []


def test_check_lipsync_seating_flags_unknown_part():
    events = [avatar_event("p1-1", 0.0, 1.0, part="Z")]
    problems = bl_edl.check_lipsync_seating(events, {"A": 0.0})
    assert "no entry in lipsync_offsets" in problems[0]


# ============================================================== coverage
def test_check_coverage_clean_tiling():
    events = [avatar_event("p1-1", 0.0, 4.0), scene_event("p1-2", 4.0, 10.0)]
    assert bl_edl.check_coverage(events, 10.0) == []


def test_check_coverage_flags_a_gap():
    events = [avatar_event("p1-1", 0.0, 4.0), scene_event("p1-2", 5.0, 10.0)]
    problems = bl_edl.check_coverage(events, 10.0)
    assert any("gap" in p for p in problems)


def test_check_coverage_flags_an_overlap():
    events = [avatar_event("p1-1", 0.0, 5.0), scene_event("p1-2", 4.0, 10.0)]
    problems = bl_edl.check_coverage(events, 10.0)
    assert any("overlap" in p for p in problems)


def test_check_coverage_flags_short_of_full_duration():
    events = [avatar_event("p1-1", 0.0, 8.0)]
    problems = bl_edl.check_coverage(events, 10.0)
    assert any("gap" in p and "8.000" in p for p in problems)


# ------------------------------------------------------------ media exists
def test_check_media_exists_flags_missing_file(tmp_path: Path):
    doc = make_p1([avatar_event("p1-1", 0.0, 10.0)])
    (tmp_path / "media").mkdir()
    # audio.media missing, plate media missing too
    problems = bl_edl.check_media_exists(doc, tmp_path)
    assert any("audio" in p for p in problems)
    assert any("p1-1" in p for p in problems)


def test_check_media_exists_clean_when_files_present(tmp_path: Path):
    doc = make_p1([avatar_event("p1-1", 0.0, 10.0)])
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "audio.mp3").write_bytes(b"x")
    (tmp_path / "media" / "lip_a.mp4").write_bytes(b"x")
    assert bl_edl.check_media_exists(doc, tmp_path) == []


# ------------------------------------------------------- avatar/evidence box
def test_check_avatar_evidence_overlap_fails_with_no_manifest(tmp_path: Path):
    events = [real_still_event("p1-1", 0.0, 10.0, composite=True)]
    problems = bl_edl.check_avatar_evidence_overlap(events, tmp_path)
    assert len(problems) == 1 and "does not exist" in problems[0]


def test_check_avatar_evidence_overlap_fails_with_no_evidence_box(tmp_path: Path):
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "REAL_MANIFEST.json").write_text(
        json.dumps([{"file": "real/score.png", "kind": "still"}]))
    events = [real_still_event("p1-1", 0.0, 10.0, composite=True)]
    problems = bl_edl.check_avatar_evidence_overlap(events, tmp_path)
    assert len(problems) == 1 and "no evidence_box" in problems[0]


def test_check_avatar_evidence_overlap_catches_a_real_overlap(tmp_path: Path):
    (tmp_path / "real").mkdir()
    # a score box inside the avatar's fixed composite box (x0-480, y845-1920)
    (tmp_path / "real" / "REAL_MANIFEST.json").write_text(json.dumps(
        [{"file": "real/score.png", "evidence_box": [{"x": 100, "y": 900, "w": 200, "h": 100}]}]))
    events = [real_still_event("p1-1", 0.0, 10.0, composite=True)]
    problems = bl_edl.check_avatar_evidence_overlap(events, tmp_path)
    assert len(problems) == 1 and "overlaps the evidence box" in problems[0]


def test_check_avatar_evidence_overlap_clean_when_box_is_clear(tmp_path: Path):
    (tmp_path / "real").mkdir()
    # a score box well above the avatar's box (avatar top is y=845)
    (tmp_path / "real" / "REAL_MANIFEST.json").write_text(json.dumps(
        [{"file": "real/score.png", "evidence_box": [{"x": 100, "y": 200, "w": 200, "h": 100}]}]))
    events = [real_still_event("p1-1", 0.0, 10.0, composite=True)]
    assert bl_edl.check_avatar_evidence_overlap(events, tmp_path) == []


# =========================================================== P2-P4 layers
REGISTRY = {"headline": {}, "sfx": {}}


def test_validate_layer_accepts_a_clean_p2_with_a_ref_to_p1():
    doc = {"episode": "epTEST", "duration": 10.0,
           "events": [{"id": "p2-1", "t0": 1.0, "t1": 2.0, "type": "headline",
                        "params": {}, "refs": ["p1-1"]}]}
    ids = bl_edl.validate_layer("p2", doc, REGISTRY, {"p1-1"})
    assert ids == {"p2-1"}


def test_validate_layer_rejects_unknown_type():
    doc = {"episode": "epTEST", "duration": 10.0,
           "events": [{"id": "p2-1", "t0": 0.0, "t1": 1.0, "type": "not_a_real_type", "params": {}}]}
    with pytest.raises(bl_edl.EDLError, match="unknown type"):
        bl_edl.validate_layer("p2", doc, REGISTRY, set())


def test_validate_layer_rejects_dangling_ref():
    doc = {"episode": "epTEST", "duration": 10.0,
           "events": [{"id": "p2-1", "t0": 0.0, "t1": 1.0, "type": "headline",
                        "params": {}, "refs": ["p1-does-not-exist"]}]}
    with pytest.raises(bl_edl.EDLError, match="dangling id"):
        bl_edl.validate_layer("p2", doc, REGISTRY, {"p1-1"})


def test_validate_layer_rejects_event_outside_duration():
    doc = {"episode": "epTEST", "duration": 5.0,
           "events": [{"id": "p2-1", "t0": 4.0, "t1": 6.0, "type": "headline", "params": {}}]}
    with pytest.raises(bl_edl.EDLError, match=r"outside \[0, 5.0\]"):
        bl_edl.validate_layer("p2", doc, REGISTRY, set())


# ================================================================ compose
def test_compose_p1_produces_expected_video_tag_and_duration():
    doc = make_p1([avatar_event("p1-1", 0.0, 4.0), scene_event("p1-2", 4.0, 10.0)])
    template = bl_edl.DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    html = compose.compose_p1(doc, template)
    assert 'src="media/lip_a.mp4"' in html
    assert 'data-media-start="0.00"' in html
    assert 'data-duration="10.00"' in html  # root duration
    assert '<div class="dt2">1 ม.ค. 69</div>' in html
    assert 'src="media/audio.mp3"' in html
    # the kit's generator functions must survive untouched
    assert "function kinetic(top, at, out, lines, ruleW)" in template
    assert "function kinetic(top, at, out, lines, ruleW)" in html


def test_compose_p1_raises_on_invalid_layer():
    doc = make_p1([scene_event("p1-1", 0.0, 5.0)])  # gap 5-10 -- compose still
    # builds (coverage is bl_check's job), but a structurally broken doc must
    # still fail loudly at compose time:
    del doc["audio"]["media"]
    template = bl_edl.DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    with pytest.raises(bl_edl.EDLError):
        compose.compose_p1(doc, template)


def test_compose_main_end_to_end_writes_file(tmp_path: Path):
    edl_dir = tmp_path / "edl"
    edl_dir.mkdir()
    doc = make_p1([avatar_event("p1-1", 0.0, 10.0)])
    (edl_dir / "p1_layout.json").write_text(json.dumps(doc))
    out = tmp_path / "composed" / "index.html"
    rc = compose.main([str(edl_dir), "--media-root", str(tmp_path), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    assert 'src="media/lip_a.mp4"' in out.read_text(encoding="utf-8")


def test_compose_main_fails_loudly_on_dangling_p2_ref(tmp_path: Path, capsys):
    edl_dir = tmp_path / "edl"
    edl_dir.mkdir()
    doc = make_p1([avatar_event("p1-1", 0.0, 10.0)])
    (edl_dir / "p1_layout.json").write_text(json.dumps(doc))
    (edl_dir / "p2_focus.json").write_text(json.dumps({
        "episode": "epTEST", "duration": 10.0,
        "events": [{"id": "p2-1", "t0": 0.0, "t1": 1.0, "type": "headline",
                     "params": {}, "refs": ["nonexistent-id"]}],
    }))
    out = tmp_path / "composed" / "index.html"
    rc = compose.main([str(edl_dir), "--media-root", str(tmp_path), "--out", str(out)])
    assert rc == 1
    assert "dangling id" in capsys.readouterr().err


def test_compose_main_fails_loudly_on_unknown_p2_type(tmp_path: Path, capsys):
    edl_dir = tmp_path / "edl"
    edl_dir.mkdir()
    doc = make_p1([avatar_event("p1-1", 0.0, 10.0)])
    (edl_dir / "p1_layout.json").write_text(json.dumps(doc))
    (edl_dir / "p2_focus.json").write_text(json.dumps({
        "episode": "epTEST", "duration": 10.0,
        "events": [{"id": "p2-1", "t0": 0.0, "t1": 1.0, "type": "totally_made_up", "params": {}}],
    }))
    out = tmp_path / "composed" / "index.html"
    rc = compose.main([str(edl_dir), "--media-root", str(tmp_path), "--out", str(out)])
    assert rc == 1
    assert "unknown type" in capsys.readouterr().err


# ================================================================== check
def _touch_media(root: Path, *rel_paths: str) -> None:
    for rel in rel_paths:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")


def test_check_p1_passes_a_clean_episode(tmp_path: Path):
    edl_dir = tmp_path / "edl"
    edl_dir.mkdir()
    doc = make_p1([avatar_event("p1-1", 0.0, 4.0), scene_event("p1-2", 4.0, 10.0)])
    (edl_dir / "p1_layout.json").write_text(json.dumps(doc))
    _touch_media(tmp_path, "media/audio.mp3", "media/lip_a.mp4", "media/s01.mp4")
    problems = check.run_p1(edl_dir, tmp_path)
    assert problems == []


def test_check_p1_reports_every_category_at_once(tmp_path: Path):
    edl_dir = tmp_path / "edl"
    edl_dir.mkdir()
    # gap (4-5), missing media, and a part-not-yet-begun seating error
    doc = make_p1([
        avatar_event("p1-1", 0.0, 4.0),
        {"id": "p1-2", "t0": 5.0, "t1": 10.0, "type": "plate",
         "params": {"role": "avatar", "kind": "video", "media": "media/lip_b.mp4",
                     "lipsync_part": "B", "avatar_mode": "full", "darken": False}},
    ])
    (edl_dir / "p1_layout.json").write_text(json.dumps(doc))
    _touch_media(tmp_path, "media/audio.mp3", "media/lip_a.mp4")  # lip_b.mp4 missing on purpose
    problems = check.run_p1(edl_dir, tmp_path)
    joined = "\n".join(problems)
    assert "coverage" in joined and "gap" in joined
    assert "media" in joined and "lip_b.mp4" in joined
    assert "lipsync" in joined and "<0" in joined


def test_check_p1_cli_exit_code(tmp_path: Path, capsys):
    edl_dir = tmp_path / "edl"
    edl_dir.mkdir()
    doc = make_p1([avatar_event("p1-1", 0.0, 10.0)])
    (edl_dir / "p1_layout.json").write_text(json.dumps(doc))
    _touch_media(tmp_path, "media/audio.mp3", "media/lip_a.mp4")
    rc = check.main(["p1", str(edl_dir), "--media-root", str(tmp_path)])
    assert rc == 0
    assert "P1 CHECK PASSED" in capsys.readouterr().out


# ============================================================ registry file
def test_event_types_registry_contains_the_seed_twelve():
    registry = bl_edl.load_registry()
    expected = {
        "hook_slide", "avatar_shrink", "hard_cut", "spotlight", "highlight_sweep",
        "zoom", "fade", "caption_chip", "headline", "data_label", "sfx", "music_bed",
    }
    assert expected <= set(registry.keys())


# ============================================================ example EDL
def test_example_edl_directory_is_internally_consistent():
    """The tiny epXX example under edl/example/ must itself pass shape
    validation and every cross-layer ref must resolve -- it is documentation,
    and documentation that doesn't validate against its own schema is worse
    than none."""
    example_dir = bl_edl.SKILL_DIR / "edl" / "example"
    p1 = bl_edl.load_json(example_dir / "p1_layout.json")
    bl_edl.validate_p1(p1)
    ids = {ev["id"] for ev in p1["events"]}
    registry = bl_edl.load_registry()
    for layer_name, filename in (("p2", "p2_focus.json"), ("p3", "p3_text.json"), ("p4", "p4_audio.json")):
        doc = bl_edl.load_json(example_dir / filename)
        ids |= bl_edl.validate_layer(layer_name, doc, registry, ids)


# ═══════════════════════════════════════════════════════════════════
# Unit tests for tools/bl_compose.py (task-aae4f843) -- the beats.json
# (Scripter/Editor output shape {tag,t0,t1,mode,extra}) -> rendered-cut
# adapter used by the BL Editor A/B/C experiment. A DIFFERENT tool from
# scripts/bl_compose.py above (that one is the general EDL P1-P4 layer
# compositor from task-42e3b6af) -- this file tests both because the
# two tasks independently landed on the same test filename.
#
# No render, no real episode media -- a synthetic 2-beat beats.json and
# a tiny synthetic generator dir (its own build_cut.py exposing the same
# function names/signatures the real build_cut.py has, plus a minimal
# assemble.py + template index.html carrying the exact marker strings
# the real assemble.py depends on). Same convention test_bl_checker.py
# uses synthetic ffmpeg fixtures instead of real episode media.
# ═══════════════════════════════════════════════════════════════════
from tools import bl_compose as bc

# ─────────────────────────── synthetic generator dir ─────────────────────

_BUILD_CUT_PY = '''
CANVAS_W, CANVAS_H = 1080, 1920

def lip_offset(src):
    return {"lip_a": 0.0}[src]

LIP_DUR = {"lip_a": 999.0}

def pick_lip(t0):
    return "lip_a"

def img_placement(extra):
    nw = extra.get("native_w", 1080)
    nh = extra.get("native_h", 1920)
    if nw == 1080 and nh == 1920:
        return 1080, 1920, 0, 0, 1.0
    if nw == 1080:
        return 1080, nh, 0, 0, 1.0
    scale = 1080 / nw
    disp_h = round(nh * scale)
    top = round((1920 - disp_h) / 2)
    return 1080, disp_h, top, 0, scale

def box_to_canvas(box, place):
    if box is None:
        return None
    dw, dh, top, left, scale = place
    x, y, w, h = box
    return (left + x * scale, top + y * scale, w * scale, h * scale)

def pct(v, dim):
    return round(v / dim * 1000) / 10

def esc(s):
    return s.replace('"', "&quot;")

PLATE_TRACK = 0
AVATAR_TRACK = 1

# Everything below here must NEVER execute -- load_generator_functions only
# selects the FunctionDef/Assign nodes above. If this ran, it would raise,
# and the test would fail loudly instead of silently passing on shadowed data.
BEATS_SENTINEL_SHOULD_NOT_RUN = 1 / 0
'''

_ASSEMBLE_PY = '''
"""Minimal stand-in for the real assemble.py -- same CLI + marker contract
(TEMPLATE, PIECES, AUDIO_MEDIA_START positional args; splices plates/
script_lines/caps_js into the video-track and #bug markers; OUT=TEMPLATE)."""
import json, sys

TEMPLATE = sys.argv[1]
PIECES = sys.argv[2]
AUDIO_MEDIA_START = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0

data = json.load(open(PIECES))
src = open(TEMPLATE).read()

plates_html = "\\n".join(data["plates"])
script_lines = "\\n".join(data["script_lines"])
caps_js = "\\n".join(data["caps_js"])
total_dur = data["total_dur"]

src = src.replace(
    'data-composition-id="main" data-start="0" data-duration="0"',
    f'data-composition-id="main" data-start="0" data-duration="{total_dur}"')

start = src.index("<!-- VIDEO TRACK")
end = src.index('<audio id="va"')
src = src[:start] + f"<!-- VIDEO TRACK -->\\n{plates_html}\\n" + src[end:]

src = src.replace(
    '<audio id="va" src="media/voice.m4a" data-start="0" data-duration="0"',
    f'<audio id="va" src="media/voice.mp3" data-start="0" data-duration="{total_dur}"')

old_marker = 'tl.from("#bug", { x: -50, opacity: 0, duration: 0.7, ease: "power3.out" }, 0.25);'
new_cut = old_marker + "\\n" + script_lines + "\\n" + caps_js
src = src.replace(old_marker, new_cut)

open(TEMPLATE, "w").write(src)
print("wrote", TEMPLATE)
'''

_TEMPLATE_HTML = '''<!doctype html>
<html><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="0">
<!-- VIDEO TRACK - replace with plates -->
<audio id="va" src="media/voice.m4a" data-start="0" data-duration="0"></audio>
<script>
tl.from("#bug", { x: -50, opacity: 0, duration: 0.7, ease: "power3.out" }, 0.25);
</script>
</div>
</body></html>
'''


@pytest.fixture
def generator_dir(tmp_path):
    d = tmp_path / "generator"
    d.mkdir()
    (d / "build_cut.py").write_text(_BUILD_CUT_PY, encoding="utf-8")
    (d / "assemble.py").write_text(_ASSEMBLE_PY, encoding="utf-8")
    (d / "index.html").write_text(_TEMPLATE_HTML, encoding="utf-8")
    return d


@pytest.fixture
def beats_2():
    return [
        {"tag": "A1", "t0": 0.0, "t1": 2.0, "mode": "FF",
         "extra": {"cap": "Hello world"}},
        {"tag": "A2", "t0": 2.0, "t1": 5.0, "mode": "EVID",
         "extra": {"img": "real/x.png", "cap": "Evidence caption", "box": [0, 0, 1080, 1920]}},
    ]


# ─────────────────────────── unit tests ───────────────────────────────────

def test_load_generator_functions_skips_side_effects(generator_dir):
    # If this ran the sentinel line at the bottom of _BUILD_CUT_PY, it would
    # raise ZeroDivisionError -- reaching here at all is the assertion.
    funcs = bc.load_generator_functions(generator_dir)
    assert set(bc._ALLOWED_FUNCS) <= set(funcs)
    assert funcs["pick_lip"](0.0) == "lip_a"
    assert funcs["LIP_DUR"] == {"lip_a": 999.0}


def test_compute_ext_end_holds_until_next(beats_2):
    ext_end = bc.compute_ext_end(beats_2, t_max=5.0)
    assert ext_end["A1"] == 2.0  # holds until A2 starts
    assert ext_end["A2"] == 5.0  # last beat holds until t_max


def test_emit_pieces_ff_and_evid_timings_and_captions(generator_dir, beats_2):
    funcs = bc.load_generator_functions(generator_dir)
    pieces = bc.emit_pieces(beats_2, t_max=5.0, funcs=funcs)

    ff_plate = next(p for p in pieces["plates"] if "v_a1" in p)
    assert 'data-start="0.0"' in ff_plate
    assert 'data-duration="2.0"' in ff_plate

    evid_plate = next(p for p in pieces["plates"] if "v_a2" in p)
    assert 'data-start="2.0"' in evid_plate
    assert 'data-duration="3.0"' in evid_plate

    # one caption style, every mode (SKILL.md §6f, task-99f3d2e8 item 2) --
    # both captions call the template's single caption(at, out, text)
    # generator, never addCap(..., kind, ...) or a per-mode chip/rail.
    caps_text = "\n".join(pieces["caps_js"])
    assert "Hello world" in caps_text
    assert "Evidence caption" in caps_text
    assert caps_text.count("caption(") == 2
    assert "addCap" not in caps_text
    assert "chip-ff" not in caps_text and "chip-comp" not in caps_text and "rail" not in caps_text


def test_compose_writes_html_with_both_captions_and_timings(generator_dir, beats_2, tmp_path):
    out_dir = tmp_path / "out"
    index_path = bc.compose(beats_2, generator_dir, t_max=5.0, out_dir=out_dir)

    assert index_path.is_file()
    html = index_path.read_text(encoding="utf-8")

    assert "Hello world" in html
    assert "Evidence caption" in html
    assert 'data-start="0.0"' in html and 'data-duration="2.0"' in html
    assert 'data-start="2.0"' in html and 'data-duration="3.0"' in html

    pieces = json.loads((out_dir / "cut_pieces.json").read_text(encoding="utf-8"))
    assert pieces["total_dur"] == pytest.approx(4.9997)


def test_emit_pieces_rejects_check_mode(generator_dir):
    funcs = bc.load_generator_functions(generator_dir)
    beats = [{"tag": "X", "t0": 0.0, "t1": 1.0, "mode": "CHECK", "extra": {}}]
    with pytest.raises(bc.ComposeError):
        bc.emit_pieces(beats, t_max=5.0, funcs=funcs)


def test_redact_ground_truth_blanks_beats_but_keeps_functions(generator_dir):
    # task-9ba58d91's own REPORT.md: an Arm-A editor has to open build_cut.py
    # to understand img_placement/box_to_canvas, and the branch's copy still
    # carries this exact window's real human-editor answer as a hardcoded
    # BEATS list right there -- ground-truth contamination. Verify the
    # redaction actually blanks it while every function load_generator_
    # functions() needs still loads clean from the redacted source.
    from tools.bl_ab_run import _redact_ground_truth

    src = (generator_dir / "build_cut.py").read_text(encoding="utf-8")
    src_with_answer = src.replace(
        "PLATE_TRACK = 0",
        'BEATS = [("HOOK-1", 0.0, 1.0, "EVID", dict(img="real/secret.png"))]\n'
        'CHECK_ITEMS = [dict(t0=1.0, t1=2.0, x="secret checklist item")]\n'
        "PLATE_TRACK = 0",
    )
    redacted = _redact_ground_truth(src_with_answer)

    assert "real/secret.png" not in redacted
    assert "secret checklist item" not in redacted
    assert "BEATS = []" in redacted
    assert "CHECK_ITEMS = []" in redacted

    (generator_dir / "build_cut.py").write_text(redacted, encoding="utf-8")
    funcs = bc.load_generator_functions(generator_dir)
    assert funcs["pick_lip"](0.0) == "lip_a"
    assert funcs["img_placement"]({}) == (1080, 1920, 0, 0, 1.0)


# ═══════════════════════════════════════════════════════════════════
# task-99f3d2e8 item 2 -- one caption style, integration level: a real
# compose() covering all four modes must pass bl_checker's gate; the old
# addCap-shaped output (task-1678d38e's own regression fixture, kept here
# too since this is the tool that used to emit it) must still fail it.
# ═══════════════════════════════════════════════════════════════════

def test_composed_html_covering_all_modes_passes_one_caption_style_gate(generator_dir, tmp_path):
    from tools import bl_checker as ck

    beats = [
        {"tag": "HOOK-1", "t0": 0.0, "t1": 2.0, "mode": "FF", "extra": {"cap": "hook line"}},
        {"tag": "CONTEXT-1", "t0": 2.0, "t1": 5.0, "mode": "COMP",
         "extra": {"img": "real/score.png", "cap": "comp line", "box": [0, 0, 1080, 1920]}},
        {"tag": "MAIN-8", "t0": 5.0, "t1": 8.0, "mode": "EVID",
         "extra": {"img": "real/warn.png", "cap": "evid line", "box": [0, 0, 1080, 1920]}},
        {"tag": "SUMMARY-1", "t0": 8.0, "t1": 10.0, "mode": "KIN",
         "extra": {"lines": [["hl", "kinetic line"]]}},
    ]
    out_dir = tmp_path / "out"
    index_path = bc.compose(beats, generator_dir, t_max=10.0, out_dir=out_dir)
    html = index_path.read_text(encoding="utf-8")

    assert "hook line" in html and "comp line" in html and "evid line" in html and "kinetic line" in html
    assert ck.caption_style_signatures(html) == {"caption"}
    assert ck.check_one_caption_style(html) == []


def test_old_addcap_shaped_output_still_fails_the_same_gate():
    # The exact shape this tool's OWN emit_pieces used to write before this
    # task's fix (addCap with a "kind" per mode) -- kept as a regression
    # test per the task brief ("must fail on the old EP57 generator").
    from tools import bl_checker as ck

    old_style_html = (
        'addCap(0.10, 2.00, "hook line", "chip-ff", null);'
        'addCap(2.00, 5.00, "comp line", "chip-comp", 700);'
        'addCap(5.00, 8.00, "evid line", "rail", null);'
    )
    assert ck.caption_style_signatures(old_style_html) == {"chip-ff", "chip-comp", "rail"}
    assert ck.check_one_caption_style(old_style_html) != []


# ═══════════════════════════════════════════════════════════════════
# task-99f3d2e8 item 3 -- plates hold by construction: a beat's plate
# duration is whatever ext_end computed (hold until the next plate),
# never capped by the underlying media's own remaining length.
# ═══════════════════════════════════════════════════════════════════

_BUILD_CUT_PY_SHORT_LIP = _BUILD_CUT_PY.replace('LIP_DUR = {"lip_a": 999.0}', 'LIP_DUR = {"lip_a": 1.0}')


@pytest.fixture
def generator_dir_short_lip(tmp_path):
    d = tmp_path / "generator_short_lip"
    d.mkdir()
    (d / "build_cut.py").write_text(_BUILD_CUT_PY_SHORT_LIP, encoding="utf-8")
    (d / "assemble.py").write_text(_ASSEMBLE_PY, encoding="utf-8")
    (d / "index.html").write_text(_TEMPLATE_HTML, encoding="utf-8")
    return d


def test_emit_pieces_ff_plate_holds_past_short_lip_media(generator_dir_short_lip):
    # lip_a.mp4 is only 1.0s long (LIP_DUR) but this beat's plate must
    # still hold the FULL 4.0s until the next beat starts (SKILL.md §6g).
    # The old capped code (`min(dur, LIP_DUR[lipname]-media_start)`) would
    # have truncated data-duration to ~1.0s here, leaving a 3.0s gap.
    # A2 is KIN, not FF -- it only exists to give A1 an end boundary, and
    # (task-9a4f1029) an FF/COMP beat at t0=4.0 would itself fall outside
    # this fixture's own [0, 1.0) avatar window (pick_lip always returns
    # "lip_a" here, unconditionally) and correctly raise ComposeError; that
    # check is exercised on its own below, not conflated with this test.
    funcs = bc.load_generator_functions(generator_dir_short_lip)
    beats = [
        {"tag": "A1", "t0": 0.0, "t1": 4.0, "mode": "FF", "extra": {"cap": "hi"}},
        {"tag": "A2", "t0": 4.0, "t1": 6.0, "mode": "KIN", "extra": {"lines": [["bl-lg", "bye"]]}},
    ]
    pieces = bc.emit_pieces(beats, t_max=6.0, funcs=funcs)
    ff_plate = next(p for p in pieces["plates"] if "v_a1" in p)
    assert 'data-duration="4.0"' in ff_plate


def test_emit_pieces_comp_avatar_holds_past_short_lip_media(generator_dir_short_lip):
    # A2 is KIN for the same reason as the FF test above -- see its comment.
    funcs = bc.load_generator_functions(generator_dir_short_lip)
    beats = [
        {"tag": "A1", "t0": 0.0, "t1": 4.0, "mode": "COMP", "extra": {"img": "real/x.png", "cap": "hi"}},
        {"tag": "A2", "t0": 4.0, "t1": 6.0, "mode": "KIN", "extra": {"lines": [["bl-lg", "bye"]]}},
    ]
    pieces = bc.emit_pieces(beats, t_max=6.0, funcs=funcs)
    avatar_plate = next(p for p in pieces["plates"] if "av_a1" in p)
    assert 'data-duration="4.0"' in avatar_plate  # not capped to LIP_DUR's 1.0
    img_plate = next(p for p in pieces["plates"] if p.startswith("<img") and "v_a1" in p)
    assert 'data-duration="4.0"' in img_plate


def test_emit_pieces_comp_avatar_until_still_shortens_avatar_on_purpose(generator_dir):
    # an editor CAN end the avatar composite early (the base plate still
    # holds full duration) -- that is a deliberate call, distinct from the
    # LIP_DUR truncation bug above, and must still work.
    funcs = bc.load_generator_functions(generator_dir)
    beats = [
        {"tag": "A1", "t0": 0.0, "t1": 4.0, "mode": "COMP",
         "extra": {"img": "real/x.png", "cap": "hi", "avatar_until": 2.0}},
        {"tag": "A2", "t0": 4.0, "t1": 6.0, "mode": "FF", "extra": {"cap": "bye"}},
    ]
    pieces = bc.emit_pieces(beats, t_max=6.0, funcs=funcs)
    avatar_plate = next(p for p in pieces["plates"] if "av_a1" in p)
    img_plate = next(p for p in pieces["plates"] if p.startswith("<img") and "v_a1" in p)
    assert 'data-duration="2.0"' in avatar_plate  # avatar_until ends it early, on purpose
    assert 'data-duration="4.0"' in img_plate     # the base plate still holds the full window


# ═══════════════════════════════════════════════════════════════════
# task-9a4f1029 item 4 -- avatar windows: an FF/COMP beat outside every
# recorded lipsync window must fail fast and clearly, before any render is
# attempted, instead of hyperframes' own media_start_out_of_range surfacing
# after a 60s+ render (task-1a5eb073's pilot). generator_dir_short_lip's
# own fake pick_lip() always returns "lip_a" with LIP_DUR 1.0s -- a beat at
# t0=0.5 is inside [0, 1.0), a beat at t0=4.0 is not.
# ═══════════════════════════════════════════════════════════════════

def test_check_avatar_window_passes_inside_the_window(generator_dir_short_lip):
    funcs = bc.load_generator_functions(generator_dir_short_lip)
    bc.check_avatar_window("A1", "FF", 0.5, "lip_a", funcs)  # must not raise


def test_check_avatar_window_raises_outside_the_window(generator_dir_short_lip):
    funcs = bc.load_generator_functions(generator_dir_short_lip)
    with pytest.raises(bc.ComposeError, match=r"lip_a"):
        bc.check_avatar_window("A1", "FF", 4.0, "lip_a", funcs)


def test_check_avatar_window_message_names_the_valid_window(generator_dir_short_lip):
    funcs = bc.load_generator_functions(generator_dir_short_lip)
    with pytest.raises(bc.ComposeError, match=r"\[0, 1\)"):
        bc.check_avatar_window("A1", "FF", 4.0, "lip_a", funcs)


def test_check_avatar_window_skips_when_generator_has_no_lip_dur(generator_dir):
    # the default fixture's LIP_DUR is 999.0 -- effectively unrestricted --
    # so nothing outside it here should ever raise for a realistic t0.
    funcs = bc.load_generator_functions(generator_dir)
    bc.check_avatar_window("A1", "FF", 500.0, "lip_a", funcs)  # must not raise


def test_emit_pieces_ff_beat_outside_avatar_window_raises(generator_dir_short_lip):
    funcs = bc.load_generator_functions(generator_dir_short_lip)
    beats = [{"tag": "DEAD-ZONE", "t0": 4.0, "t1": 6.0, "mode": "FF", "extra": {"cap": "hi"}}]
    with pytest.raises(bc.ComposeError, match="DEAD-ZONE"):
        bc.emit_pieces(beats, t_max=6.0, funcs=funcs)


def test_emit_pieces_comp_beat_outside_avatar_window_raises(generator_dir_short_lip):
    funcs = bc.load_generator_functions(generator_dir_short_lip)
    beats = [{"tag": "DEAD-ZONE", "t0": 4.0, "t1": 6.0, "mode": "COMP",
              "extra": {"img": "real/x.png", "cap": "hi"}}]
    with pytest.raises(bc.ComposeError, match="DEAD-ZONE"):
        bc.emit_pieces(beats, t_max=6.0, funcs=funcs)


def test_emit_pieces_ff_beat_inside_avatar_window_renders_clean(generator_dir_short_lip):
    funcs = bc.load_generator_functions(generator_dir_short_lip)
    beats = [{"tag": "A1", "t0": 0.5, "t1": 1.0, "mode": "FF", "extra": {"cap": "hi"}}]
    pieces = bc.emit_pieces(beats, t_max=1.0, funcs=funcs)  # must not raise
    assert any("v_a1" in p for p in pieces["plates"])


# ═══════════════════════════════════════════════════════════════════
# task-9a4f1029 item 1 -- a KIN beat with no plate named defaults to its
# own line's S{n:02d} broll (darkened), never the bare kit background.
# ═══════════════════════════════════════════════════════════════════

_SCRIPT_TSV = (
    "1\tHOOK-1\tline one text\t\tshow\tnote one\n"
    "2\tSUMMARY-1\tline two text\t\tshow\tnote two\n"
)


def test_load_script_line_map_reads_tag_to_line_number(generator_dir):
    (generator_dir / "SCRIPT.tsv").write_text(_SCRIPT_TSV, encoding="utf-8")
    assert bc.load_script_line_map(generator_dir) == {"HOOK-1": 1, "SUMMARY-1": 2}


def test_load_script_line_map_empty_when_no_script_tsv(generator_dir):
    assert bc.load_script_line_map(generator_dir) == {}


def test_default_kin_broll_pads_the_line_number():
    assert bc.default_kin_broll("SUMMARY-1", {"SUMMARY-1": 2}) == "broll/S02.mp4"
    assert bc.default_kin_broll("SUMMARY-1", {"SUMMARY-1": 40}) == "broll/S40.mp4"


def test_default_kin_broll_none_for_unknown_tag():
    assert bc.default_kin_broll("NOT-IN-SCRIPT", {"SUMMARY-1": 2}) is None


def test_emit_pieces_kin_defaults_to_own_line_broll(generator_dir):
    (generator_dir / "SCRIPT.tsv").write_text(_SCRIPT_TSV, encoding="utf-8")
    funcs = bc.load_generator_functions(generator_dir)
    script_line_map = bc.load_script_line_map(generator_dir)
    beats = [{"tag": "SUMMARY-1", "t0": 0.0, "t1": 2.0, "mode": "KIN",
              "extra": {"lines": [["bl-lg", "hi"]]}}]
    pieces = bc.emit_pieces(beats, t_max=2.0, funcs=funcs, script_line_map=script_line_map)
    plate = next(p for p in pieces["plates"] if "v_summary1" in p)
    assert 'src="media/broll/S02.mp4"' in plate
    assert "plate-darkened" in plate


def test_emit_pieces_kin_editor_named_broll_overrides_the_default(generator_dir):
    (generator_dir / "SCRIPT.tsv").write_text(_SCRIPT_TSV, encoding="utf-8")
    funcs = bc.load_generator_functions(generator_dir)
    script_line_map = bc.load_script_line_map(generator_dir)
    beats = [{"tag": "SUMMARY-1", "t0": 0.0, "t1": 2.0, "mode": "KIN",
              "extra": {"broll": "S14.mp4", "lines": [["bl-lg", "hi"]]}}]
    pieces = bc.emit_pieces(beats, t_max=2.0, funcs=funcs, script_line_map=script_line_map)
    plate = next(p for p in pieces["plates"] if "v_summary1" in p)
    assert 'src="media/S14.mp4"' in plate  # editor's own choice, not the default S02.mp4


def test_emit_pieces_kin_explicit_falsy_broll_opts_out(generator_dir):
    (generator_dir / "SCRIPT.tsv").write_text(_SCRIPT_TSV, encoding="utf-8")
    funcs = bc.load_generator_functions(generator_dir)
    script_line_map = bc.load_script_line_map(generator_dir)
    beats = [{"tag": "SUMMARY-1", "t0": 0.0, "t1": 2.0, "mode": "KIN",
              "extra": {"broll": "", "lines": [["bl-lg", "hi"]]}}]
    pieces = bc.emit_pieces(beats, t_max=2.0, funcs=funcs, script_line_map=script_line_map)
    assert not any("v_summary1" in p for p in pieces["plates"])  # no plate at all, by choice


def test_emit_pieces_kin_no_default_without_script_tsv(generator_dir):
    # no SCRIPT.tsv staged -> old behaviour: no plate, no crash.
    funcs = bc.load_generator_functions(generator_dir)
    beats = [{"tag": "SUMMARY-1", "t0": 0.0, "t1": 2.0, "mode": "KIN",
              "extra": {"lines": [["bl-lg", "hi"]]}}]
    pieces = bc.emit_pieces(beats, t_max=2.0, funcs=funcs)  # script_line_map omitted entirely
    assert not any("v_summary1" in p for p in pieces["plates"])


def test_compose_wires_script_line_map_automatically(generator_dir, tmp_path):
    (generator_dir / "SCRIPT.tsv").write_text(_SCRIPT_TSV, encoding="utf-8")
    beats = [{"tag": "SUMMARY-1", "t0": 0.0, "t1": 2.0, "mode": "KIN",
              "extra": {"lines": [["bl-lg", "hi"]]}}]
    out_dir = tmp_path / "out"
    index_path = bc.compose(beats, generator_dir, t_max=2.0, out_dir=out_dir)
    html = index_path.read_text(encoding="utf-8")
    assert 'src="media/broll/S02.mp4"' in html


def test_emit_pieces_kin_script_line_comment_names_the_tag(generator_dir):
    # the trailing `// TAG` comment (task-9a4f1029) lets tools/bl_checker.py
    # identify which beat a kinetic() call belongs to.
    funcs = bc.load_generator_functions(generator_dir)
    beats = [{"tag": "SUMMARY-1", "t0": 0.0, "t1": 2.0, "mode": "KIN",
              "extra": {"lines": [["bl-lg", "hi"]]}}]
    pieces = bc.emit_pieces(beats, t_max=2.0, funcs=funcs)
    assert any(line.endswith("// SUMMARY-1") for line in pieces["script_lines"])


# ═══════════════════════════════════════════════════════════════════
# task-9a4f1029 item 3 -- spotlight exits exactly when its plate does.
# assemble.py's own spotlight() (off-limits) calls hide(id, out-0.1) and
# hide()'s duration is a hard-coded 0.18s, so the fade actually finishes
# 0.08s AFTER whatever `out` this tool passes -- SPOTLIGHT_EXIT_LEAD tunes
# the ARGUMENT so the unmodified formula lands exactly on t1.
# ═══════════════════════════════════════════════════════════════════

def test_spotlight_exit_lead_is_the_measured_overshoot():
    # hide()'s own formula (index.html, off-limits): starts at out-0.1,
    # duration 0.18 -> finishes at out+0.08. Passing t1-LEAD as `out` must
    # make that finish land exactly on t1.
    assert bc.SPOTLIGHT_EXIT_LEAD == pytest.approx(0.18 - 0.1)


def test_emit_pieces_comp_spotlight_out_arg_leads_t1_by_the_exit_lead(generator_dir):
    funcs = bc.load_generator_functions(generator_dir)
    beats = [{"tag": "A1", "t0": 0.0, "t1": 4.0, "mode": "COMP",
              "extra": {"img": "real/x.png", "cap": "hi", "box": [0, 0, 1080, 1920]}}]
    pieces = bc.emit_pieces(beats, t_max=4.0, funcs=funcs)
    spotlight_call = next(s for s in pieces["script_lines"] if s.startswith('spotlight("sp_a1"'))
    # spotlight("sp_a1", <at>, <out>, ...) -- out is the 3rd argument
    out_arg = float(spotlight_call.split(",")[2].strip())
    assert out_arg == pytest.approx(4.0 - bc.SPOTLIGHT_EXIT_LEAD)


def test_emit_pieces_evid_spotlight_out_arg_leads_t1_by_the_exit_lead(generator_dir):
    funcs = bc.load_generator_functions(generator_dir)
    beats = [{"tag": "A1", "t0": 0.0, "t1": 4.0, "mode": "EVID",
              "extra": {"img": "real/x.png", "cap": "hi", "box": [0, 0, 1080, 1920]}}]
    pieces = bc.emit_pieces(beats, t_max=4.0, funcs=funcs)
    spotlight_call = next(s for s in pieces["script_lines"] if s.startswith('spotlight("sp_a1"'))
    out_arg = float(spotlight_call.split(",")[2].strip())
    assert out_arg == pytest.approx(4.0 - bc.SPOTLIGHT_EXIT_LEAD)


# ═══════════════════════════════════════════════════════════════════
# task-99f3d2e8 item 4 -- range render: emit_pieces()'s t0_window shift
# (placement is relative, media seek stays absolute) + trim_range()'s
# frame-exact, video-only, fixed-encoder normalization pass.
# ═══════════════════════════════════════════════════════════════════

def test_emit_pieces_t0_window_shifts_placement_not_media_seek(generator_dir):
    funcs = bc.load_generator_functions(generator_dir)
    beats = [
        {"tag": "S1", "t0": 10.0, "t1": 12.0, "mode": "FF", "extra": {"cap": "seg line 1"}},
        {"tag": "S2", "t0": 12.0, "t1": 14.0, "mode": "FF", "extra": {"cap": "seg line 2"}},
    ]
    pieces = bc.emit_pieces(beats, t_max=15.0, funcs=funcs, t0_window=10.0)

    plate = next(p for p in pieces["plates"] if "v_s1" in p)
    assert 'data-start="0.0"' in plate            # placement is RELATIVE to the window
    assert 'data-media-start="10.0"' in plate     # media seek stays ABSOLUTE (lip_offset=0.0)
    caps_text = "\n".join(pieces["caps_js"])
    assert "caption(0.0, 2.0, " in caps_text      # caption timing shifts with placement

    last_plate = next(p for p in pieces["plates"] if "v_s2" in p)
    assert 'data-start="2.0"' in last_plate
    assert 'data-duration="3.0"' in last_plate    # holds to t_max(15.0)-t0_window(10.0) = 5.0


def test_emit_pieces_t0_window_excludes_beats_before_the_window(generator_dir):
    funcs = bc.load_generator_functions(generator_dir)
    beats = [
        {"tag": "BEFORE", "t0": 5.0, "t1": 8.0, "mode": "FF", "extra": {"cap": "x"}},
        {"tag": "IN", "t0": 10.0, "t1": 12.0, "mode": "FF", "extra": {"cap": "y"}},
    ]
    pieces = bc.emit_pieces(beats, t_max=15.0, funcs=funcs, t0_window=10.0)
    assert not any("v_before" in p for p in pieces["plates"])
    assert any("v_in" in p for p in pieces["plates"])


def test_emit_pieces_total_dur_uses_window_duration_not_t_max(generator_dir):
    funcs = bc.load_generator_functions(generator_dir)
    beats = [{"tag": "S1", "t0": 10.0, "t1": 12.0, "mode": "FF", "extra": {"cap": "x"}}]
    pieces = bc.emit_pieces(beats, t_max=15.0, funcs=funcs, t0_window=10.0)
    assert pieces["total_dur"] == pytest.approx(4.9997)  # window is 15.0-10.0 = 5.0s, not 15.0s


def test_compose_with_t0_window_writes_relative_placement_to_disk(generator_dir, tmp_path):
    beats = [{"tag": "S1", "t0": 39.3, "t1": 41.3, "mode": "FF", "extra": {"cap": "seg2 opening line"}}]
    out_dir = tmp_path / "out"
    index_path = bc.compose(beats, generator_dir, t_max=65.8333, out_dir=out_dir, t0=39.3)
    html = index_path.read_text(encoding="utf-8")
    assert 'data-start="0.0"' in html
    assert "seg2 opening line" in html


# ─────────────────────────── trim_range (real ffmpeg, synthetic fixtures) ──

def _ffmpeg(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _testsrc(path: Path, duration: float, rate: int = 30, w: int = 64, h: int = 64) -> None:
    _ffmpeg(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", f"-i", f"testsrc=size={w}x{h}:rate={rate}",
             "-t", str(duration), "-pix_fmt", "yuv420p", str(path)])


def _count_frames(path: Path) -> int:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True, text=True, check=True)
    return int(r.stdout.strip())


def test_trim_range_two_adjacent_ranges_concat_to_same_frame_count_as_the_union(tmp_path):
    # task-99f3d2e8 item 4's own test criterion, verbatim: two adjacent
    # ranges, concatenated the way bl_merge.py does (-c copy), must have
    # the same total frame count as one full render of the union.
    full = tmp_path / "full10.mp4"
    _testsrc(full, duration=10.0)

    out_a = tmp_path / "a.mp4"
    out_b = tmp_path / "b.mp4"
    out_union = tmp_path / "union.mp4"
    bc.trim_range(full, dur=5.0, out_path=out_a)
    bc.trim_range(full, dur=5.0, out_path=out_b)
    bc.trim_range(full, dur=10.0, out_path=out_union)
    assert _count_frames(out_a) == 150 and _count_frames(out_b) == 150 and _count_frames(out_union) == 300

    concat_list = tmp_path / "concat.txt"
    concat_list.write_text(f"file '{out_a.resolve()}'\nfile '{out_b.resolve()}'\n", encoding="utf-8")
    concatenated = tmp_path / "concatenated.mp4"
    _ffmpeg(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", str(concat_list), "-c", "copy", str(concatenated)])

    assert _count_frames(concatenated) == _count_frames(out_union)


def test_trim_range_drops_audio_and_forces_exact_frame_count(tmp_path):
    src = tmp_path / "src.mp4"
    _ffmpeg(["ffmpeg", "-y", "-v", "error",
             "-f", "lavfi", "-i", "testsrc=size=64x64:rate=30",
             "-f", "lavfi", "-i", "sine=frequency=440",
             "-t", "3.0", "-pix_fmt", "yuv420p", "-shortest", str(src)])
    out = tmp_path / "trimmed.mp4"
    bc.trim_range(src, dur=2.0, out_path=out)

    assert _count_frames(out) == 60
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                        "stream=codec_type", "-of", "csv=p=0", str(out)],
                       capture_output=True, text=True)
    assert r.stdout.strip() == ""  # no audio stream, per the segment contract


def test_trim_range_uses_consistent_encoder_settings_every_call(tmp_path):
    # bl_merge.py's verify_same_codec() requires identical codec/resolution/
    # pix_fmt/frame-rate across every part -- prove two independently
    # trimmed ranges (different source lengths) still probe identically.
    from tools import bl_merge as mg

    src_a = tmp_path / "src_a.mp4"
    src_b = tmp_path / "src_b.mp4"
    _testsrc(src_a, duration=4.0)
    _testsrc(src_b, duration=7.0)
    out_a = tmp_path / "range_a.mp4"
    out_b = tmp_path / "range_b.mp4"
    bc.trim_range(src_a, dur=3.0, out_path=out_a)
    bc.trim_range(src_b, dur=6.0, out_path=out_b)

    assert mg.verify_same_codec([out_a, out_b]) == []
