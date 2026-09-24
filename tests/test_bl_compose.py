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

    caps_text = "\n".join(pieces["caps_js"])
    assert "Hello world" in caps_text
    assert "Evidence caption" in caps_text
    assert "chip-ff" in caps_text
    assert "rail" in caps_text


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
