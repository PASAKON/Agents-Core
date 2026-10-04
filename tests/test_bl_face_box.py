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
