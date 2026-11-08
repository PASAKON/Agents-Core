from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    mod_path = Path(__file__).resolve().parents[1] / "prototypes" / "mypasakon-voice" / "assemble_ep1_v5.py"
    spec = importlib.util.spec_from_file_location("assemble_ep1_v5", mod_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["assemble_ep1_v5"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_blueprint_29_shots_and_c4_rulings():
    mod = _load_module()
    shots = mod.build_blueprint()
    assert len(shots) == 29
    assert shots[0].t_in == 0.0
    assert shots[-1].t_out == 105.72

    # Contiguous timecodes
    for a, b in zip(shots, shots[1:]):
        assert abs(a.t_out - b.t_in) < 1e-6, f"Gap between shot {a.idx} and {b.idx}"

    # CMO c4a: Shot 15 folded into Shot 14 (0:39.93 - 0:43.83 = 3.90s), exits via paper_flash into orig_shot 16
    s14 = shots[13]
    assert s14.idx == 14 and s14.orig_shot == 14
    assert abs(s14.t_in - 39.93) < 1e-6 and abs(s14.t_out - 43.83) < 1e-6
    assert abs(s14.duration - 3.90) < 1e-6
    s15 = shots[14]
    assert s15.orig_shot == 16
    assert s15.transition_in == "paper_flash"

    # CMO c4b: End card 100.24 - 105.72 (5.48s incl. 3.0s tail) with exact risk warning
    end_shot = shots[-1]
    assert end_shot.orig_shot == 30
    assert abs(end_shot.t_in - 100.24) < 1e-6 and abs(end_shot.t_out - 105.72) < 1e-6
    assert abs(end_shot.duration - 5.48) < 1e-6
    assert end_shot.pages[0].extra == "การเทรดมีความเสี่ยงสูง อาจสูญเสียเงินทุนทั้งหมด ศึกษาก่อนลงทุน"
    assert "Claude" in end_shot.pages[0].line1


def test_no_adjacent_face_crops_and_no_banned_chars():
    mod = _load_module()
    shots = mod.build_blueprint()
    banned = {"—", "–", "«", "»", "“", "”"}
    for a, b in zip(shots, shots[1:]):
        if a.shot_type == "A" and b.shot_type == "A":
            assert (a.face_zoom, a.face_offset) != (b.face_zoom, b.face_offset)
    for s in shots:
        for p in s.pages:
            for txt in (p.line1, p.line2, p.extra):
                assert not (set(txt) & banned), f"Banned char in shot {s.idx}: {txt}"
        for st in s.stickers:
            assert not (set(st.text) & banned), f"Banned char in sticker {st.text}"
