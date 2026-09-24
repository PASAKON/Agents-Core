"""Unit tests for tools/bl_compose.py (task-aae4f843).

No render, no real episode media -- a synthetic 2-beat beats.json and a
tiny synthetic generator dir (its own build_cut.py exposing the same
function names/signatures build_cut.py has, plus a minimal assemble.py +
template index.html carrying the exact marker strings the real assemble.py
depends on). This exercises bl_compose's OWN orchestration (AST-selective
function loading, hold-until-next timing, per-mode HTML emission, the
assemble.py splice) end to end without depending on the real branch-only
generator or any network/git-fetch, the same convention test_bl_checker.py
uses synthetic ffmpeg fixtures instead of real episode media.

Run via: pytest tests/test_bl_compose.py -q
"""
from __future__ import annotations

import json

import pytest

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
