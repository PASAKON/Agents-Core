import numpy as np
import pytest
from tools.bl_face_box import alpha_bounds, canvas_box, geometry


def test_geometry_reads_css_including_shift(tmp_path):
    template = tmp_path / 'index.html'
    template.write_text('.avatar-comp { height: 68%; left: 0; bottom: 120px; transform: translateX(-6%); }')
    geom = geometry(template)
    assert geom['scale'] == .68
    assert canvas_box([100, 300, 700, 1101], geom) == [23, 698, 409, 546]


def test_increasing_bottom_anchored_scale_lifts_face():
    geom = dict(scale=.56, left=0, bottom=0, translate_x=-.06)
    small = canvas_box([100, 300, 700, 1101], geom, .60)
    large = canvas_box([100, 300, 700, 1101], geom, .68)
    assert large[1] + large[3] < small[1] + small[3]
    assert large[2] > small[2]


def test_chin_bound_prevents_early_neck_false_pass():
    alpha = np.zeros((1920, 1080), dtype=np.uint8)
    alpha[300:, 100:600] = 255
    alpha[800, 100:600] = 0
    alpha[800, 200:500] = 255
    old, neck = alpha_bounds(alpha)
    conservative, _ = alpha_bounds(alpha, 1100)
    assert neck == 800
    assert old[3] == 801
    assert conservative[3] == 1101


def test_missing_alpha_fails_closed():
    with pytest.raises(ValueError, match='empty matte'):
        alpha_bounds(np.zeros((1920, 1080), dtype=np.uint8))


def test_unsupported_geometry_fails_closed(tmp_path):
    template = tmp_path / 'index.html'
    template.write_text('.avatar-comp {height: 800px;}')
    with pytest.raises(ValueError):
        geometry(template)


# ── the head-top envelope that places the COMP caption (task-f35f2935) ──
import json  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402

from tools import bl_checker as ck  # noqa: E402
from tools.bl_face_box import CHIN_ROW, USED_RANGES, canvas_y, envelope_from_frames  # noqa: E402
import scripts.bl_edl as bl_edl  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MEASUREMENT = ROOT / 'docs/reports/task-f35f2935/head-top.json'
TEMPLATE = ROOT / '.claude/skills/CMO_Procedure_BlackLiquidity_Cut/template/index.html'


def _frame(top, x0=100, x1=600):
    """A silhouette: a head from row `top` (a 120-px-deep block) and shoulders from `top` + 300 down to the matte's end."""
    alpha = np.zeros((1920, 1080), dtype=np.uint8)
    alpha[top:, x0:x1] = 255
    alpha[top + 150:top + 300, x0 + 40:x1 - 40] = 255        # a narrower neck: keeps the profile valid
    alpha[top + 150:top + 300, x0:x0 + 40] = 0
    alpha[top + 150:top + 300, x1 - 40:x1] = 0
    return alpha


def test_envelope_takes_the_highest_top_over_every_frame_and_reports_where_it_was():
    frames = [(0.0, _frame(300)), (1 / 30, _frame(250, 80, 620)), (2 / 30, _frame(260)), (0.5, _frame(280))]
    env = envelope_from_frames(frames, 0.0, 1.0, chin_row=1000)
    assert env['top'] == 250 and env['top_at'] == pytest.approx(1 / 30)
    assert env['frames'] == 4
    assert env['source_bounds'] == [80, 250, 620, 1001]           # x unioned over frames; y from the top to chin_row + 1
    assert env['min_top_0_5s'] == 280                             # only t = 0.0 (300) and 0.5 (280) are on the 0.5 s grid


def test_envelope_between_half_second_samples_sees_what_a_half_second_grid_misses():
    frames = [(0.0, _frame(400)), (0.2, _frame(350)), (0.5, _frame(400))]
    env = envelope_from_frames(frames, 0.0, 0.6, chin_row=1000)
    assert env['top'] == 350 and env['min_top_0_5s'] == 400


def test_envelope_maps_the_top_through_the_templates_css():
    geom = geometry(TEMPLATE)
    env = envelope_from_frames([(0.0, _frame(104))], 0.0, 0.1, chin_row=1000, geom=geom)
    assert env['canvas_top'] == round(104 * .56 + 1920 * (1 - .56), 2) == 903.04


def test_envelope_with_no_frames_fails_closed():
    with pytest.raises(ValueError, match='no alpha frames'):
        envelope_from_frames([], 0.0, 1.0)


def test_canvas_y_agrees_with_canvas_box():
    geom = geometry(TEMPLATE)
    assert canvas_y(104, geom) == pytest.approx(903.04)
    assert canvas_box([0, 104, 10, 200], geom)[1] == math.floor(canvas_y(104, geom))


# The checker's COMP_TAKES is a copy of the measurement; this is the place it is held to the file the tool wrote.
def test_the_checkers_take_table_is_the_committed_measurement():
    doc = json.loads(MEASUREMENT.read_text(encoding='utf-8'))
    assert doc['chin_row'] == CHIN_ROW and set(doc['takes']) == set(ck.COMP_TAKES)
    geom = geometry(TEMPLATE)
    assert doc['geometry'] == geom
    for take, row in ck.COMP_TAKES.items():
        used = doc['takes'][take]['used']
        assert used['range'] == list(USED_RANGES[take])
        assert row['head_top'] == used['canvas_top'] == round(canvas_y(used['top'], geom), 2), take
        assert row['comp_box'] == tuple(used['comp_box']) == tuple(canvas_box(used['source_bounds'], geom)), take
        assert row['ff_box'] == tuple(used['ff_box']), take
        assert ck.comp_caption_cy(take) == row['cy'] == math.floor(used['canvas_top'] - 24 - 82), take


def test_the_measured_ranges_are_what_a_comp_or_ff_beat_can_show():
    # the take's opening pose (head ~100-250 source px higher) is shown by no beat with a caption: a take only
    # opens on screen at the window's first plate (lip_a, 0.0) or at a COMP's t0 (lip_b MAIN-5 39.28, lip_c 88.69)
    assert USED_RANGES['lip_a'][0] == 0.0
    assert USED_RANGES['lip_b'][0] == 0.5 <= 39.28 - 38.77
    assert USED_RANGES['lip_c'][0] <= 88.69 - 80.84
    for take, (_, end) in USED_RANGES.items():
        assert end == {'lip_a': 15.95, 'lip_b': 17.15, 'lip_c': 14.25}[take]      # build_cut.py's LIP_DUR


def test_avatar_box_in_the_edl_checker_is_the_templates_composite_box():
    geom = geometry(TEMPLATE)
    assert geom['scale'] == .56 and geom['bottom'] == 0 and geom['left'] == 0
    assert bl_edl.AVATAR_BOX['y0'] == round(1920 * (1 - geom['scale']) - geom['bottom']) == 845
    assert bl_edl.AVATAR_BOX['y1'] == 1920


# task-2db3174c: the tool writes the checker's --take-table file for any episode (EP59 first).
def test_take_table_from_a_measurement_loads_in_the_checker_and_derives_cy_the_same_way():
    from tools.bl_face_box import take_table_from
    measured = dict(chin_row=1100, fps=30, geometry={'scale': .56}, takes={
        'lip_a': dict(used=dict(canvas_top=898.24, top=99, top_at=0.1, frames=12, range=[0.0, 0.4],
                                comp_box=[-25, 898, 573, 564], ff_box=[21, 99, 1021, 1002])),
        'lip_b': dict(used=dict(canvas_top=968.56, top=215, top_at=1.0, frames=9, range=[0.5, 0.8],
                                comp_box=[-7, 968, 576, 494], ff_box=[54, 215, 1026, 886]))})
    doc = take_table_from(measured, {'lip_a': 0.0, 'lip_b': 38.53}, episode=59)
    assert doc['episode'] == 59 and doc['takes']['lip_a']['cy'] == math.floor(898.24 - 24 - 82) == 792
    table = ck.load_take_table(doc)
    assert table['seats'] == (('lip_a', 0.0), ('lip_b', 38.53))
    assert ck.comp_caption_cy('lip_b', table) == doc['takes']['lip_b']['cy'] == 862
    assert 'episode' not in take_table_from(measured, {'lip_a': 0.0, 'lip_b': 1.0})
