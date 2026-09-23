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
