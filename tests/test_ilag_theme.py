"""Unit tests for tools/ilag_theme.py: the v2 palette (gold, white, black, CEO 2026-10-26) and that no render
path still draws the v1 navy + cream look (PH IlagLakorn, task-3c96bb47).

The Story card is rendered for real with Pillow (Taviraj from the brand kit on hosts without Sukhumvit Set);
nothing here needs ffmpeg, the network or ChatGPT.

Run via: pytest tests/test_ilag_theme.py -q
"""
from __future__ import annotations

import inspect
import json
from collections import Counter

import pytest

from tools import ilag_theme as th

V1_NAMES = ("NAVY", "CARD_CREAM", "CARD_BG", "CARD_GOLD", "CARD_WHITE", "STAMP_RED")
V1_HEX = ("0A1A38", "FFF4D6", "0C0D1E", "F6C453", "B8322A")
V1_WORDS = ("navy", "indigo", "cream")


def _rgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _pixels(img):
    """RGBA tuples of an RGBA image (Image.getdata is deprecated)."""
    return zip(*[iter(img.tobytes())] * 4)


def _dominant(card, box, ignore=_rgb("#0A0A0A")):
    """The most common opaque colour in the box that is not the plate ground."""
    seen = Counter(px[:3] for px in _pixels(card.crop(box)) if px[3] == 255 and px[:3] != ignore)
    return seen.most_common(1)[0][0]


# ─────────────────────────── tokens ─────────────────────────────────────

def test_v2_palette_hex_values():
    assert th.BLACK == "#0A0A0A"
    assert th.WHITE == "#FFFFFF"
    assert th.GOLD == "#F7C64E"
    assert th.GOLD_METAL == ("#FDE165", "#F7C440", "#E49C1D")  # top to bottom
    assert th.STAMP_GOLD == "#E8B230"
    assert th.INK == "#111111"
    assert th.MIST == "#C9C9C9"


@pytest.mark.parametrize("name", V1_NAMES)
def test_v1_tokens_are_gone(name):
    assert not hasattr(th, name)


# ─────────────────────────── poster ─────────────────────────────────────

@pytest.fixture
def poster_prompt(tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "name": "know-t", "character": "the farmer", "scene": "A rice field.", "sub": "ก่อนเซ็นสัญญา",
        "points": ["จุดที่หนึ่ง", "จุดที่สอง", "จุดที่สาม"], "tip": "อ่านก่อนเซ็น", "title": "ขายฝากนาแม่"}, ensure_ascii=False))
    job = tmp_path / "job.json"
    th.poster_job(str(spec), str(job))
    return json.loads(job.read_text())[0]["prompt"]


def test_poster_prompt_uses_the_v2_tokens(poster_prompt):
    for value in (th.BLACK, th.WHITE, th.GOLD, th.INK, *th.GOLD_METAL):
        assert value in poster_prompt
    assert "pure black panel" in poster_prompt


@pytest.mark.parametrize("v1", V1_HEX + V1_WORDS)
def test_poster_prompt_names_no_v1_colour(poster_prompt, v1):
    assert v1.lower() not in poster_prompt.lower()


# ─────────────────────────── story card ─────────────────────────────────

TITLE, QUESTION = "ขายฝากนาแม่", "แม่คำปุนจะรักษานาไว้ได้ไหม?"


def test_story_card_ground_is_black_and_transparent_outside():
    card = th.card_image(TITLE, QUESTION)
    assert card.size == (1080, 1920)
    assert card.getpixel((0, 0)) == (0, 0, 0, 0)
    assert card.getpixel((100, 1460)) == (*_rgb(th.BLACK), 255)


def test_story_card_lines_are_gold_white_mist():
    card = th.card_image(TITLE, QUESTION)
    assert _dominant(card, (60, 1480, 1020, 1560)) == _rgb(th.GOLD)    # line 1, y 1520
    assert _dominant(card, (60, 1590, 1020, 1630)) == _rgb(th.WHITE)   # line 2, y 1610
    assert _dominant(card, (60, 1660, 1020, 1700)) == _rgb(th.MIST)    # line 3, y 1680


def test_story_card_draws_only_the_v2_colours():
    card = th.card_image(TITLE, QUESTION)
    opaque = Counter(px[:3] for px in _pixels(card) if px[3] == 255)
    solid = {rgb for rgb, _ in opaque.most_common(4)}  # anti-aliased edges are spread over hundreds of blends
    assert solid == {_rgb(c) for c in (th.BLACK, th.GOLD, th.WHITE, th.MIST)}


def test_story_writes_the_card_png_and_hands_it_to_ffmpeg(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(th.subprocess, "run", lambda argv, **kw: calls.append(argv))
    out = tmp_path / "story.mp4"
    args = th.argparse.Namespace(film="film.mp4", start=3.0, dur=20.0, title=TITLE, question=QUESTION, out=str(out))
    th.story(args)
    png = tmp_path / "story.card.png"
    assert png.exists()
    (argv,) = calls
    assert argv[0] == "ffmpeg" and str(png) in argv and str(out) == argv[-1]
    assert "gte(t,15.0)" in " ".join(argv)  # the card shows on the last 5 s


def test_story_card_refuses_a_line_too_long_for_the_plate():
    with pytest.raises(SystemExit):
        th.card_image("ก" * 120, QUESTION)


# ─────────────────────────── no v1 on any render path ───────────────────

def test_no_render_path_refers_to_a_v1_token_or_a_guillemet():
    paths = (th.POSTER_PROMPT, *(inspect.getsource(f) for f in (th.poster_job, th.card_image, th.story, th._font)))
    for src in paths:
        for name in V1_NAMES:
            assert name not in src
        for v1 in V1_HEX:
            assert v1.lower() not in src.lower()
        assert "\u00ab" not in src and "\u00bb" not in src
