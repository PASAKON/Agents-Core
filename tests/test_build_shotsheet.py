"""TEXT_ONLY in tools/build_shotsheet.py (2026-09-26, taachang ACT3): a character
listed in d.TEXT_ONLY is described in words with no reference chip, and every
<IMAGE_REF_N> after it is renumbered. Flow deleted every prompt carrying the
11-year-old's plates with his face in frame; the same shots without his chips
rendered. A data file without TEXT_ONLY must build exactly as before."""
from __future__ import annotations

import re
import types

from tools import build_shotsheet


def _data(text_only=None):
    d = types.SimpleNamespace()
    d.CHAR = {
        "boy": ("@boy__face", "a small boy in a navy T-shirt", "The little boy"),
        "gran": ("@gran__face", "an old woman in a sarong", "The old woman"),
    }
    d.WARDROBE = {"boy": "@boy__home", "gran": "@gran__home"}
    d.VOICE = {"boy": ("", "a high bright voice"), "gran": ("", "a soft husky voice")}
    d.LOC = {"home": ("@home", "a small zinc shack")}
    d.NOT = {"nosubs": "No subtitles."}
    d.PROPS_BY_SHOT = {1: ["@notebook"]}
    d.PROP_FOR_NOT = {}
    d.STYLE = "Vertical 9:16."
    d.SHOTS = [(1, 8, "Two-shot", ["boy", "gran"], "home", "afternoon", "he shows her a notebook",
                [("boy", "proud", "ดูสิยาย"), ("gran", "moved", "เก่งจัง")], ["nosubs"])]
    if text_only is not None:
        d.TEXT_ONLY = text_only
    return d


def _prompt(md: str) -> str:
    return md.split("```")[1]


def test_text_only_character_gets_no_chip_and_refs_are_renumbered():
    md = build_shotsheet.build(_data({"boy"}), "3")
    attach = re.search(r"^\*\*ATTACH\*\* (.*)$", md, re.M).group(1)
    assert "@boy__face" not in attach and "@boy__home" not in attach
    handles = re.findall(r"`(@[\w_]+)`→REF_(\d+)", attach)
    assert [h for h, _ in handles] == ["@gran__face", "@home", "@notebook", "@gran__home"]
    assert [int(i) for _, i in handles] == [0, 1, 2, 3]
    p = _prompt(md)
    # every ref the prompt uses exists in the attach list, and none is left dangling
    used = {int(i) for i in re.findall(r"<IMAGE_REF_(\d+)>", p)}
    assert used == {0, 1, 2, 3}
    # the boy is still described and still speaks, just without a ref tag
    assert "a small boy in a navy T-shirt," in p
    assert 'The little boy speaks Thai' in p
    assert "The old woman <IMAGE_REF_0> speaks Thai" in p
    assert "a small zinc shack <IMAGE_REF_1>" in p


def test_without_text_only_the_boy_keeps_his_chips():
    md = build_shotsheet.build(_data(), "3")
    attach = re.search(r"^\*\*ATTACH\*\* (.*)$", md, re.M).group(1)
    assert "`@boy__face`→REF_0" in attach and "@boy__home" in attach
    assert "The little boy <IMAGE_REF_0> speaks Thai" in _prompt(md)


def test_empty_text_only_builds_exactly_like_no_text_only():
    assert build_shotsheet.build(_data(set()), "3") == build_shotsheet.build(_data(), "3")
