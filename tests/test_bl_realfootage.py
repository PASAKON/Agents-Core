"""Unit tests for tools/bl_realfootage.py's censor-region maths (task-67f82679).

Pure functions only -- no Playwright, no ffmpeg, no network. These are where
a silent wrong answer would ship straight into a published episode (a censor
box that lands on the wrong pixels, or a Ken-Burns crop that leaks the
un-pixelated original), so each test is built to actually fail if the maths
regresses, not just to exercise the happy path.

Run via: pytest tests/test_bl_realfootage.py -q
(not in pytest.ini's default testpaths=scripts,lib -- run explicitly, same
convention as tests/test_higgsfield_gen_loop.py.)
"""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from tools import bl_realfootage as rf


# ─────────────────────────── compute_censor_pixel_box ──────────────────────

def test_zero_scroll_unit_dpr_is_identity_scaled():
    doc_box = {"x": 100, "y": 200, "width": 50, "height": 20}
    scroll = {"x": 0, "y": 0}
    assert rf.compute_censor_pixel_box(doc_box, scroll, 1.0) == (100, 200, 150, 220)


def test_device_pixel_ratio_scales_the_box():
    doc_box = {"x": 100, "y": 200, "width": 50, "height": 20}
    scroll = {"x": 0, "y": 0}
    assert rf.compute_censor_pixel_box(doc_box, scroll, 2.0) == (200, 400, 300, 440)


def test_scroll_offset_moves_box_up_as_page_scrolls_down():
    # element sits far down the document; once the page has scrolled past it
    # by (almost) its own y, it should land near the top of the frame.
    doc_box = {"x": 50, "y": 800, "width": 200, "height": 40}
    scroll = {"x": 0, "y": 750}
    assert rf.compute_censor_pixel_box(doc_box, scroll, 1.0) == (50, 50, 250, 90)


def test_layout_shift_mid_scroll_uses_fresh_box_not_stale():
    """The exact failure mode the task calls out: lazy-loaded content pushes
    an element down mid-scroll. A frame captured AFTER the shift must be
    censored using the SHIFTED box -- using the box measured before the
    shift would silently place the pixelation on the wrong pixels (and thus
    leave the real element uncensored)."""
    dpr = 2.0
    doc_box_before_shift = {"x": 100, "y": 800, "width": 200, "height": 40}
    doc_box_after_shift = {"x": 100, "y": 1100, "width": 200, "height": 40}  # banner pushed it +300 CSS px
    scroll_at_frame = {"x": 0, "y": 750}  # frame captured after the shift already happened

    correct = rf.compute_censor_pixel_box(doc_box_after_shift, scroll_at_frame, dpr)
    stale = rf.compute_censor_pixel_box(doc_box_before_shift, scroll_at_frame, dpr)

    assert correct == (200, 700, 600, 780)
    assert stale == (200, 100, 600, 180)
    assert correct != stale, "fresh vs stale box must diverge -- that divergence is the bug this guards"


def test_horizontal_scroll_offset_also_applied():
    doc_box = {"x": 500, "y": 0, "width": 30, "height": 30}
    scroll = {"x": 400, "y": 0}
    assert rf.compute_censor_pixel_box(doc_box, scroll, 1.0) == (100, 0, 130, 30)


# ─────────────────────────── clamp_box ──────────────────────────────────────

def test_clamp_box_within_frame_is_unchanged():
    assert rf.clamp_box((10, 10, 50, 50), 1080, 1920) == (10, 10, 50, 50)


def test_clamp_box_clips_overhang():
    assert rf.clamp_box((-20, -5, 1100, 1930), 1080, 1920) == (0, 0, 1080, 1920)


def test_clamp_box_fully_offscreen_returns_none():
    assert rf.clamp_box((2000, 2000, 2100, 2100), 1080, 1920) is None
    assert rf.clamp_box((-100, -100, -10, -10), 1080, 1920) is None


# ─────────────────────────── partial_box ────────────────────────────────────

def test_partial_box_right_forty_percent():
    box = (0, 0, 100, 50)
    assert rf.partial_box(box, fraction=0.4, side="right") == (60, 0, 100, 50)


def test_partial_box_left_side():
    box = (0, 0, 100, 50)
    assert rf.partial_box(box, fraction=0.25, side="left") == (0, 0, 25, 50)


def test_partial_box_top_bottom():
    box = (0, 0, 100, 200)
    assert rf.partial_box(box, fraction=0.5, side="bottom") == (0, 100, 100, 200)
    assert rf.partial_box(box, fraction=0.5, side="top") == (0, 0, 100, 100)


# ─────────────────────────── region_box ─────────────────────────────────────

def test_region_box_top_strip_of_a_card():
    # the real shape found on WikiFX's complaint cards: an 860x398 card
    # whose avatar+username sit in roughly the top 12% -- region_box lets a
    # rule target "top strip of whatever ancestor card was found" without
    # needing the exact (often minified/varying) avatar/username selector.
    card = (110, 5175, 970, 5573)  # left, top, right, bottom (CSS px, pre-scroll-adjust)
    top_strip = rf.region_box(card, top=0.0, bottom=0.15, left=0.0, right=1.0)
    assert top_strip == (110, 5175, 970, 5235)


def test_region_box_full_region_is_identity():
    box = (10, 20, 110, 220)
    assert rf.region_box(box, top=0.0, bottom=1.0, left=0.0, right=1.0) == box


# ─────────────────────────── pixelate_region ────────────────────────────────

def test_pixelate_region_flattens_block_to_uniform_color():
    # a 4x4 image where every pixel is a distinct value; after pixelating
    # the whole thing as one 4x4 block, every pixel must become identical
    # (the mosaic average), proving detail was actually destroyed, not just
    # visually blurred.
    arr = np.arange(16, dtype=np.uint8).reshape(4, 4)
    arr3 = np.stack([arr, arr, arr], axis=-1)
    img = Image.fromarray(arr3, mode="RGB")

    out = rf.pixelate_region(img, (0, 0, 4, 4), block=4)
    out_arr = np.array(out)
    unique_pixels = {tuple(px) for row in out_arr for px in row}
    assert len(unique_pixels) == 1, f"expected one flat mosaic color, got {unique_pixels}"


def test_pixelate_region_leaves_outside_box_untouched():
    arr = np.full((10, 10, 3), 200, dtype=np.uint8)
    arr[0:5, 0:5] = 10  # distinct region we will pixelate
    img = Image.fromarray(arr, mode="RGB")

    out = rf.pixelate_region(img, (0, 0, 5, 5), block=5)
    out_arr = np.array(out)
    # untouched region unchanged
    assert np.array_equal(out_arr[5:, 5:], arr[5:, 5:])
    assert out_arr.shape == arr.shape


def test_pixelate_region_empty_box_is_noop():
    img = Image.new("RGB", (10, 10), (1, 2, 3))
    out = rf.pixelate_region(img, (5, 5, 5, 8), block=4)  # zero width
    assert np.array_equal(np.array(out), np.array(img))


# ─────────────────────────── nine_sixteen_crop_around ───────────────────────

def test_nine_sixteen_crop_matches_target_ratio():
    box = (500, 800, 700, 850)  # a wide, short box (e.g. a text line)
    crop = rf.nine_sixteen_crop_around(box, img_w=1080, img_h=1920, pad=1.8)
    left, top, right, bottom = crop
    w, h = right - left, bottom - top
    assert w > 0 and h > 0
    assert abs((w / h) - (9 / 16)) < 0.02


def test_nine_sixteen_crop_stays_within_image_bounds():
    box = (10, 10, 40, 30)  # near the top-left corner
    crop = rf.nine_sixteen_crop_around(box, img_w=1080, img_h=1920, pad=3.0)
    left, top, right, bottom = crop
    assert left >= 0 and top >= 0 and right <= 1080 and bottom <= 1920


def test_nine_sixteen_crop_contains_the_source_box_when_it_fits():
    box = (500, 900, 580, 940)
    crop = rf.nine_sixteen_crop_around(box, img_w=1080, img_h=1920, pad=1.8)
    left, top, right, bottom = crop
    bl, bt, br, bb = box
    assert left <= bl and top <= bt and right >= br and bottom >= bb


def test_nine_sixteen_crop_never_exceeds_max_frame_fraction():
    """Regression: task-67f82679 EP55, 2026-09-23. A crop target whose tight
    text match failed upstream and fell back to a whole paragraph element
    (measured live: 617x81 CSS px) exploded through the old formula to
    (0, 0, 1080, 1920) -- literally the entire frame. That frame happened to
    also contain an unrelated embedded screenshot with what looked like a
    real account number, uncensored. The cap must hold even for a box this
    disproportionate, and the result must still be smaller than the full
    frame -- "not zoomed enough" is an acceptable degraded output, "shows
    the whole page" is not."""
    box = (70, 992, 687, 1073)  # the exact box that triggered the incident
    crop = rf.nine_sixteen_crop_around(box, img_w=1080, img_h=1920, pad=2.0)
    left, top, right, bottom = crop
    w, h = right - left, bottom - top
    assert crop != (0, 0, 1080, 1920)
    assert w <= 1080 * 0.7 + 1 and h <= 1920 * 0.7 + 1


def test_nine_sixteen_crop_cap_is_configurable():
    box = (70, 992, 687, 1073)
    tight_cap = rf.nine_sixteen_crop_around(box, img_w=1080, img_h=1920, pad=2.0, max_frame_fraction=0.3)
    loose_cap = rf.nine_sixteen_crop_around(box, img_w=1080, img_h=1920, pad=2.0, max_frame_fraction=0.7)
    tight_area = (tight_cap[2] - tight_cap[0]) * (tight_cap[3] - tight_cap[1])
    loose_area = (loose_cap[2] - loose_cap[0]) * (loose_cap[3] - loose_cap[1])
    assert tight_area < loose_area


# ─────────────────────────── lerp_rect ───────────────────────────────────────

def test_lerp_rect_endpoints():
    r0 = (0, 0, 1080, 1920)
    r1 = (400, 700, 700, 1000)
    assert rf.lerp_rect(r0, r1, 0.0) == pytest.approx(r0)
    assert rf.lerp_rect(r0, r1, 1.0) == pytest.approx(r1)


def test_lerp_rect_midpoint():
    r0 = (0, 0, 100, 200)
    r1 = (20, 40, 80, 160)
    mid = rf.lerp_rect(r0, r1, 0.5)
    assert mid == pytest.approx((10, 20, 90, 180))


def test_lerp_rect_clamps_t():
    r0 = (0, 0, 100, 100)
    r1 = (50, 50, 150, 150)
    assert rf.lerp_rect(r0, r1, -1.0) == pytest.approx(r0)
    assert rf.lerp_rect(r0, r1, 2.0) == pytest.approx(r1)


# ─────────────────────────── shot_content_hash ───────────────────────────────

def test_shot_hash_stable_for_identical_dict():
    shot = {"id": "x", "url": "https://a", "covers": ["A"], "censor": []}
    assert rf.shot_content_hash(shot) == rf.shot_content_hash(dict(shot))


def test_shot_hash_changes_when_config_changes():
    shot = {"id": "x", "url": "https://a", "covers": ["A"], "censor": []}
    changed = {**shot, "url": "https://b"}
    assert rf.shot_content_hash(shot) != rf.shot_content_hash(changed)


def test_shot_hash_independent_of_key_order():
    a = {"id": "x", "url": "https://a", "covers": ["A", "B"]}
    b = {"covers": ["A", "B"], "url": "https://a", "id": "x"}
    assert rf.shot_content_hash(a) == rf.shot_content_hash(b)


# ─────────────────────────── Shot / CensorRule loading ──────────────────────

def test_shot_from_dict_resolves_censor_profile():
    profiles = {"ads": [{"label": "signup", "text": "สมัคร", "kind": "full"}]}
    d = {"id": "s1", "url": "https://x", "covers": ["A"], "censor_profiles": ["ads"]}
    shot = rf.Shot.from_dict(d, profiles)
    assert len(shot.censor) == 1
    assert shot.censor[0].label == "signup"
    assert shot.censor[0].text == "สมัคร"


# ─────────────────────────── _rule_target anchor fallback ───────────────────
# Regression test for a real bug found in the EP55 live run 2026-09-23: a PII
# censor rule with only `ancestor`+`region` (no `text`/`selector` of its own,
# e.g. "walk up from wherever we're already zooming and pixelate the top
# strip") silently resolved to {ok: false} in the browser -- it had nothing to
# find -- so the complaint-card PII rule censored NOTHING. The fix: a rule
# with no anchor of its own inherits the shot's own crop anchor.

def test_rule_target_falls_back_to_shot_crop_anchor(tmp_path):
    runner = rf.RealFootageRunner("t", tmp_path)
    rule = rf.CensorRule(label="pii", kind="region", ancestor="nearest_with_img",
                          region={"top": 0, "bottom": 0.15})
    shot = rf.Shot(id="s", url="https://x", covers=["A"],
                    crop={"text": "48,994.87", "pad": 1.6})
    target = runner._rule_target(rule, shot)
    assert target["text"] == "48,994.87"
    assert target["selector"] is None
    assert target["ancestor"] == "nearest_with_img"


def test_rule_target_keeps_its_own_anchor_when_it_has_one(tmp_path):
    runner = rf.RealFootageRunner("t", tmp_path)
    rule = rf.CensorRule(label="cta", kind="full", text="สมัคร")
    shot = rf.Shot(id="s", url="https://x", covers=["A"], crop={"text": "some other text"})
    target = runner._rule_target(rule, shot)
    assert target["text"] == "สมัคร"  # NOT overridden by the shot's crop text


def test_rule_target_avatar_heuristic_ignores_crop_fallback(tmp_path):
    # regression: an avatar_heuristic rule scans the WHOLE page by shape and
    # must never accidentally inherit the shot's crop text/selector as its
    # own anchor (that would turn a site-wide PII sweep into a single-spot
    # search, same class of bug as the original ancestor-fallback miss).
    runner = rf.RealFootageRunner("t", tmp_path)
    rule = rf.CensorRule(label="avatars", avatar_heuristic=True)
    shot = rf.Shot(id="s", url="https://x", covers=["A"], crop={"text": "1.69"})
    target = runner._rule_target(rule, shot)
    assert target["text"] is None
    assert target["selector"] is None
    assert target["avatar_heuristic"] is True


def test_rule_target_stays_unresolved_with_no_anchor_and_no_crop(tmp_path):
    runner = rf.RealFootageRunner("t", tmp_path)
    rule = rf.CensorRule(label="pii", kind="region", ancestor="nearest_with_img")
    shot = rf.Shot(id="s", url="https://x", covers=["A"])  # action=capture, no crop
    target = runner._rule_target(rule, shot)
    assert target["text"] is None and target["selector"] is None


def test_shot_from_dict_merges_explicit_censor_and_profile():
    profiles = {"ads": [{"label": "signup", "text": "สมัคร"}]}
    d = {
        "id": "s1", "url": "https://x", "covers": ["A"],
        "censor_profiles": ["ads"],
        "censor": [{"label": "logo", "selector": "header img", "kind": "partial", "fraction": 0.4}],
    }
    shot = rf.Shot.from_dict(d, profiles)
    labels = {c.label for c in shot.censor}
    assert labels == {"signup", "logo"}
