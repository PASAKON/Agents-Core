"""tools/ilag_cut.py: EDL validation (plan), segment encode + cache (encode), kit cards (cards).

Sources are tiny synthetic ffmpeg lavfi clips made in tmp_path; nothing real is read and nothing is written in the repo
tree.  plan needs no ffmpeg; encode needs ffmpeg/ffprobe; the cards tests need Playwright (+ chromium) and PIL and skip
without them.

Run via: pytest tests/test_ilag_cut.py -q
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import ilag_cut

REPO = Path(__file__).resolve().parents[1]
DEMO_EDL = REPO / "tests/fixtures/ilag_cut/demo_edl.json"
KIT = REPO / "knowledge/brand-knowledge/brands/ilag/templates"
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not on PATH")
needs_pil = pytest.mark.skipif(not importlib.util.find_spec("PIL"), reason="PIL missing")


def have_browser():
    if not all(importlib.util.find_spec(m) for m in ("playwright", "PIL", "numpy")):    # numpy: cut_logo.py
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


needs_cards = pytest.mark.skipif(not (HAS_FFMPEG and have_browser()), reason="Playwright/chromium/PIL/numpy/ffmpeg missing")


@pytest.fixture(autouse=True)
def private_render_lock(tmp_path, monkeypatch):
    """`encode` takes the box's shared render lock by default (review item 7): a test must never wait on, or hold, the
    real /opt/MoonieXHQ/Work/.bl-render.lock."""
    monkeypatch.setattr(ilag_cut, "DEFAULT_LOCK", str(tmp_path / "default-render.lock"), raising=False)


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


# ------------------------------------------------------------------ fixtures
TOTAL = 1.2 + (0.5 + 43 / 24 + 7 / 24 + 20 / 24) + 1.0       # a + the four NG parts (whole frames) + the end card


def base_edl():
    return {
        "fps": 24, "size": [1080, 1920], "sfx": "sfx", "kit": "templates", "output": "ep.mp4",
        "segments": [
            {"id": "a", "kind": "clip", "src": "footage/a.mp4", "in": 0.0, "dur": 1.2,
             "cards": [{"el": "name", "at": 0.2, "dur": 0.8,
                        "texts": {"nm1": "เสี่ยบอย", "nm2": "นักต้มตุ๋น", "nm3": "ฉายา: ชื่อใครก็ซวย"}}],
             "subs": [{"at": 0.1, "dur": 0.5, "text": "หนึ่ง"}, {"at": 0.6, "dur": 0.5, "text": "สอง"}]},
            {"id": "b", "kind": "ng", "tape": "AI ให้เสี่ยตบไหล่ผิดคน!",
             "take": {"src": "footage/a.mp4", "in": 0.0, "dur": 0.5}, "take2": {"in": 0.0, "dur": 0.8}},
            {"id": "z", "kind": "end", "src": "footage/a.mp4", "in": 0.0, "dur": 1.0,
             "texts": {"e2": "EP.2", "e3": "ใครประกันตัวเสี่ยบอย?", "e4": "พรุ่งนี้ 20:00 น."}},
        ],
    }


def kitchen_sink_edl():
    """Every kind and every clip option, so each filter graph is run once."""
    seg = [
        {"id": "c1", "kind": "clip", "src": "footage/a.mp4", "in": 0.0, "dur": 0.8, "speed": 1.5, "gain": 0.5,
         "cards": [{"el": "skip", "at": 0.0, "dur": 0.6, "texts": {"tct": "หนึ่งเดือนต่อมา"}}],
         "sfx": [{"name": "whoosh", "at": 0.05, "gain": 0.5}]},
        {"id": "c2", "kind": "clip", "src": "footage/a.mp4", "in": 0.2, "dur": 0.6, "reverse": True, "grade": "flash",
         "freeze_last": 0.4, "cards": [{"el": "flash", "at": 0.1, "dur": 0.7,
                                        "texts": {"fct": "ย้อนกลับไปเมื่อสามปีก่อน", "fsub": "ความทรงจำของแม่ศรี"}}]},
        {"id": "c3", "kind": "clip", "src": "footage/silent.mp4", "in": 0.0, "dur": 0.6, "grade": "desat", "blur": 8},
        {"id": "s1", "kind": "still", "src": "footage/still.png", "dur": 0.7,
         "cards": [{"el": "place", "at": 0.0, "dur": 0.6, "texts": {"pl1": "ตลาด", "pl2": "เช้าวันจันทร์ 06:30 น."}},
                   {"el": "now", "at": 0.0, "dur": 0.6}]},
        {"id": "s2", "kind": "clip", "src": "footage/a.mp4", "in": 0.0, "dur": 0.8,
         "cards": [{"el": "namegood", "at": 0.0, "dur": 0.6,
                    "texts": {"nm1": "แม่ศรี", "nm2": "แม่ค้าผักดอง", "nm3": "ใจดีจนโดนยืมชื่อ"}},
                   {"el": "fact", "at": 0.1, "dur": 0.6, "texts": {"body": "ค้ำประกันให้ใคร\nเจ้าหนี้ทวงจากคนค้ำได้"}},
                   {"el": "lesson", "at": 0.1, "dur": 0.6, "texts": {"body": "ชื่อเสียงสร้างมาทั้งชีวิต"}}]},
        {"id": "t", "kind": "title", "src": "footage/a.mp4", "dur": 1.0,
         "texts": {"season": "ตลาดนี้มีกรรม", "ep": "EP.1", "title": "ตบผิดคน", "tagline": "ทำชั่วแล้ว AI ก็ช่วยไม่ได้"}},
        {"id": "z", "kind": "end", "src": "footage/still.png", "dur": 1.0,
         "texts": {"e2": "EP.2", "e3": "ใครประกันตัว?", "e4": "พรุ่งนี้ 20:00 น."}},
        {"id": "h", "kind": "blooper_header", "src": "footage/a.mp4", "freeze_at": 0.5, "dur": 0.8},
        {"id": "h2", "kind": "clip", "src": "footage/a.mp4", "in": 0.0, "dur": 0.6, "blooper": True},
    ]
    return {"fps": 24, "sfx": "sfx", "output": "sink.mp4", "segments": seg}


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    """root folder: footage/a.mp4 (2 s, 24 fps, audio), silent.mp4, still.png, sfx/*.wav."""
    root = tmp_path_factory.mktemp("ilag_root")
    (root / "footage").mkdir()
    (root / "sfx").mkdir()
    if not HAS_FFMPEG:
        return root
    lav = ["-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=24:duration=2"]
    enc = ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    ff(*lav, "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2", *enc, "-c:a", "aac", "-shortest",
       root / "footage/a.mp4")
    ff(*lav, *enc, root / "footage/silent.mp4")
    ff(*lav, "-frames:v", "1", root / "footage/still.png")
    for n in ("scratch", "thud", "rewind", "boom", "whoosh"):
        ff("-f", "lavfi", "-i", "sine=frequency=300:sample_rate=48000:duration=0.4", root / f"sfx/{n}.wav")
    return root


def write(tmp_path, edl, name="edl.json"):
    p = tmp_path / name
    p.write_text(json.dumps(edl, ensure_ascii=False), encoding="utf-8")
    return p


def dummy_cards(work, edl):
    """Transparent stand-ins for every card PNG and NG frame set the EDL needs (what `cards` would have drawn)."""
    errors, _, segs = ilag_cut.check(edl)
    assert not errors, errors
    parts = ilag_cut.all_parts(segs)
    (Path(work) / "cards").mkdir(parents=True, exist_ok=True)
    png, jpg = Path(work) / "dummy.png", Path(work) / "dummy.jpg"
    ff("-f", "lavfi", "-i", "color=c=black@0.0:s=1080x1920,format=rgba", "-frames:v", "1", png)
    ff("-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=24", "-frames:v", "1", jpg)
    for el, tx in ilag_cut.wanted_cards(parts, False):
        shutil.copy(png, ilag_cut.card_path(work, el, tx))
    for p in parts:
        if p["frames"]:
            d = Path(work) / "cards" / f"ng-{p['frames']['key']}"
            d.mkdir(exist_ok=True)
            for i in range(int(ilag_cut.NG_FREEZE * 24)):
                shutil.copy(jpg, d / f"{i:03d}.jpg")


def plan(tmp_path, edl, capsys):
    code = ilag_cut.main(["plan", str(write(tmp_path, edl))])
    cap = capsys.readouterr()
    return code, cap.out, cap.err


# ------------------------------------------------------------------ plan: validation
def test_valid_edl_plans(tmp_path, capsys):
    code, out, err = plan(tmp_path, base_edl(), capsys)
    assert code == 0, err
    assert f"total {TOTAL:.1f} s" in out and "6 encodes" in out
    assert "ERROR" not in err


def test_ng_expands_to_the_four_build_demo_parts():
    errors, _, segs = ilag_cut.check(base_edl())
    assert not errors
    ng = [p for s, ps in segs if s["kind"] == "ng" for p in ps]
    assert [p["note"] for p in ng] == ["take", "freeze + NG stamp + tape", "rewind", "take 2"]
    assert [round(p["dur"] * 24) for p in ng] == [12, 43, 7, 20]      # frames: take, int(1.8 s), 0.5 s / 1.85, take 2
    assert ng[3]["cards"][0]["el"] == "take2" and ng[2]["tags"] == ["rew"]
    assert [p["wm"] for p in ng] == [True, False, True, True]      # the freeze frames carry the watermark baked in
    assert ("wm", {}) in ilag_cut.wanted_cards(ng[1:2], True)       # so `cards` must draw it for them


def test_demo_edl_reproduces_build_demo(capsys):
    assert ilag_cut.main(["plan", str(DEMO_EDL)]) == 0
    out = capsys.readouterr().out
    assert "total 44.3 s" in out and "13 encodes" in out
    errors, warnings, segs = ilag_cut.check(json.loads(DEMO_EDL.read_text(encoding="utf-8")))
    assert [p["name"] for p in ilag_cut.all_parts(segs)] == [
        "a", "b.1take", "b.2freeze", "b.3rew", "b.4take2", "c", "d", "e1", "e2", "f", "g", "h1", "h2"]
    assert not any("hook" in w for w in warnings)    # 13.1 s before the title


def mutate(fn):
    e = base_edl()
    fn(e)
    return e


FAULTS = [
    ("em dash", lambda e: e["segments"][0]["subs"][0].update(text="หนึ่ง — สอง"), "em or en dash"),
    ("en dash", lambda e: e["segments"][0]["cards"][0]["texts"].update(nm2="ก–ข"), "em or en dash"),
    ("guillemet in a card", lambda e: e["segments"][0]["cards"][0]["texts"].update(nm1="\u00abเสี่ยบอย\u00bb"),
     "guillemet"),
    ("guillemet in a sub", lambda e: e["segments"][0]["subs"][0].update(text="เรื่อง \u00abขายชื่อ\u00bb"), "guillemet"),
    ("guillemet in a note", lambda e: e["segments"][0].update(note="ฉาก \u00abตลาด\u00bb"), "guillemet"),
    ("line break in a name", lambda e: e["segments"][0]["cards"][0]["texts"].update(nm2="นักต้มตุ๋น\nประจำตลาด"),
     "must be one line"),
    ("line break in a sub", lambda e: e["segments"][0]["subs"][0].update(text="หนึ่ง\nสอง"), "must be one line"),
    ("three lines in a fact", lambda e: e["segments"][0]["cards"].append(
        {"el": "fact", "at": 0.1, "dur": 0.6, "texts": {"body": "ก\nข\nค"}}), "at most 2 lines"),
    ("empty second line", lambda e: e["segments"][0]["cards"].append(
        {"el": "lesson", "at": 0.1, "dur": 0.6, "texts": {"body": "ก\n "}}), "at most 2 lines"),
    ("three NG", lambda e: e["segments"].extend(
        {**copy.deepcopy(e["segments"][1]), "id": f"ng{i}"} for i in range(2)), "at most 2 NG"),
    ("no watermark", lambda e: e["segments"][0].update(wm=False), "no watermark"),
    ("watermark on the end card", lambda e: e["segments"][2].update(wm=True), "must not carry the watermark"),
    ("card past the end", lambda e: e["segments"][0]["cards"][0].update(at=0.9), "ends past the segment"),
    ("sub past the end", lambda e: e["segments"][0]["subs"][1].update(at=1.0), "ends past the segment"),
    ("subs overlap", lambda e: e["segments"][0]["subs"][1].update(at=0.4), "subs overlap"),
    ("duplicate id", lambda e: e["segments"][2].update(id="a"), "duplicate id"),
    ("typo'd field", lambda e: e["segments"][0].update(durr=1), "unknown field 'durr'"),
    ("card too short to fade", lambda e: e["segments"][0]["cards"][0].update(dur=0.3), "'dur' must be >= 0.5"),
    ("name card missing a text", lambda e: e["segments"][0]["cards"][0]["texts"].pop("nm3"), "needs text 'nm3'"),
    ("end card missing e4", lambda e: e["segments"][2]["texts"].pop("e4"), "needs text 'e4'"),
    ("ng cards at the top", lambda e: e["segments"][1].update(cards=[]), "inside 'take'"),
    ("freeze before rewind", lambda e: e["segments"][1].update(rewind_in=0.5), "freeze_at"),
    ("bad size", lambda e: e.update(size=[720, 1280]), "'size' must be"),
    ("bad output", lambda e: e.update(output="../x.mp4"), "'output' must be"),
    ("bloopers need a header", lambda e: e["segments"].append(
        {"id": "bl", "kind": "clip", "src": "footage/a.mp4", "in": 0, "dur": 0.5, "blooper": True}), "after the blooper_header"),
]


@pytest.mark.parametrize("name,fault,message", FAULTS, ids=[f[0] for f in FAULTS])
def test_plan_refuses(name, fault, message, tmp_path, capsys):
    code, out, err = plan(tmp_path, mutate(fault), capsys)
    assert code == 1 and message in err, err
    assert out == ""                                  # no timeline for an invalid EDL


def test_plan_lists_every_error_at_once(tmp_path, capsys):
    e = base_edl()
    e["segments"][0]["subs"][0]["text"] = "ก — ข"
    e["segments"][0]["wm"] = False
    e["segments"][0]["cards"][0]["at"] = 1.1
    code, _, err = plan(tmp_path, e, capsys)
    assert code == 1
    assert err.count("ERROR") == 3 and "3 error(s)" in err


def test_fact_and_lesson_take_one_line_break_and_namegood_is_a_card(tmp_path, capsys):
    e = base_edl()
    e["segments"][0]["cards"] += [
        {"el": "namegood", "at": 0.0, "dur": 0.6, "texts": {"nm1": "แม่ศรี", "nm2": "แม่ค้า", "nm3": "ใจดี"}},
        {"el": "fact", "at": 0.1, "dur": 0.6, "texts": {"body": "บรรทัดหนึ่ง\nบรรทัดสอง"}},
        {"el": "lesson", "at": 0.1, "dur": 0.6, "texts": {"body": "ข้อคิด"}}]
    code, _, err = plan(tmp_path, e, capsys)
    assert code == 0, err
    assert "no lesson card" not in err and "no fact card" not in err


def test_missing_pillars_warn_but_do_not_fail(tmp_path, capsys):
    code, _, err = plan(tmp_path, base_edl(), capsys)
    assert code == 0
    assert "no lesson card" in err and "no fact card" in err and "four pillars" in err
    e = base_edl()
    e["segments"][0]["cards"].append({"el": "lesson", "at": 0.1, "dur": 0.6, "texts": {"body": "ข้อคิด"}})
    _, _, err = plan(tmp_path, e, capsys)
    assert "no lesson card" not in err and "no fact card" in err


def test_hook_outside_12_to_15_s_warns(tmp_path, capsys):
    e = base_edl()
    e["segments"].insert(1, {"id": "t", "kind": "title", "src": "footage/a.mp4",
                             "texts": {"season": "ก", "ep": "EP.1", "title": "ข", "tagline": "ค"}})
    code, _, err = plan(tmp_path, e, capsys)
    assert code == 0 and "hook (everything before the title) is 1.2 s" in err


def test_card_key_is_stable_and_text_sensitive():
    k = ilag_cut.card_key("sub", {"sub": "สวัสดี"})
    assert k == ilag_cut.card_key("sub", {"sub": "สวัสดี"})
    assert k != ilag_cut.card_key("sub", {"sub": "สวัสดีค่ะ"}) and k != ilag_cut.card_key("skip", {"sub": "สวัสดี"})


# ------------------------------------------------------------------ encode
def encode(tmp_path, media, edl, work, capsys, *extra):
    p = write(tmp_path, edl)
    code = ilag_cut.main(["encode", str(p), "--root", str(media), "--out", str(work), *extra])
    cap = capsys.readouterr()
    return code, cap.out, cap.err


@needs_ffmpeg
def test_encode_three_segments_then_nothing_to_redo(tmp_path, media, capsys):
    edl, work = base_edl(), tmp_path / "work"
    dummy_cards(work, edl)
    code, out, err = encode(tmp_path, media, edl, work, capsys)
    assert code == 0, err
    assert "encoded 6, unchanged 0" in out           # a + the 4 NG parts + the end card
    final = work / "out/ep.mp4"
    info = probe(final, "stream=codec_type,pix_fmt,sample_aspect_ratio,r_frame_rate,sample_rate,width,height:format=duration")
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert (v["pix_fmt"], v["sample_aspect_ratio"], v["r_frame_rate"]) == ("yuv420p", "1:1", "24/1")
    assert (v["width"], v["height"], a["sample_rate"]) == (1080, 1920, "48000")
    assert abs(float(info["format"]["duration"]) - TOTAL) < 0.35
    for line in ("pix_fmt=yuv420p", "SAR=1:1", "fps=24/1", "48000 Hz"):
        assert line in out
    seg_files = lambda: {p: p.stat().st_mtime_ns for p in (work / "seg").glob("*.mp4") if p.name != "joined.mp4"}
    stamps = seg_files()
    code, out, err = encode(tmp_path, media, edl, work, capsys)
    assert code == 0, err
    assert "encoded 0, unchanged 6" in out
    assert len(stamps) == 6 and stamps == seg_files()                                      # nothing rewritten


@needs_ffmpeg
def test_one_changed_segment_is_the_only_one_re_encoded(tmp_path, media, capsys):
    edl, work = base_edl(), tmp_path / "work"
    dummy_cards(work, edl)
    assert encode(tmp_path, media, edl, work, capsys)[0] == 0
    edl["segments"][2]["in"] = 0.5                    # the end card's background starts elsewhere
    code, out, err = encode(tmp_path, media, edl, work, capsys)
    assert code == 0, err
    assert "encoded 1, unchanged 5" in out


@needs_ffmpeg
def test_every_kind_encodes_with_one_format(tmp_path, media, capsys):
    edl, work = kitchen_sink_edl(), tmp_path / "work"
    dummy_cards(work, edl)
    code, out, err = encode(tmp_path, media, edl, work, capsys)
    assert code == 0, err
    for f in sorted((work / "seg").glob("*.mp4")):    # concat copy is only safe when every segment matches
        if f.name == "joined.mp4":
            continue
        info = probe(f, "stream=codec_type,pix_fmt,sample_aspect_ratio,r_frame_rate,sample_rate,channels,width,height")
        got = {s["codec_type"]: s for s in info["streams"]}
        assert (got["video"]["pix_fmt"], got["video"]["sample_aspect_ratio"], got["video"]["r_frame_rate"],
                got["video"]["width"]) == ("yuv420p", "1:1", "24/1", 1080), f.name
        assert (got["audio"]["sample_rate"], got["audio"]["channels"]) == ("48000", 2), f.name
    dur = float(probe(work / "out/sink.mp4", "format=duration")["format"]["duration"])
    assert abs(dur - (0.8 + 1.0 + 0.6 + 0.7 + 0.8 + 1.0 + 1.0 + 0.8 + 0.6)) < 0.45, dur    # c1 c2+hold c3 s1 s2 t z h h2


@needs_ffmpeg
def test_refuses_missing_inputs_and_lists_them(tmp_path, media, capsys):
    edl, work = base_edl(), tmp_path / "work"
    edl["segments"][0]["src"] = "footage/nope.mp4"
    edl["segments"][0]["sfx"] = [{"name": "ding", "at": 0.1, "gain": 1}]
    code, _, err = encode(tmp_path, media, edl, work, capsys)       # no cards drawn either
    assert code == 1
    assert "source not found" in err and "sfx 'ding' not found" in err
    assert "card PNG(s) missing" in err and "run `ilag_cut.py cards` first" in err and "NG slam frames missing" in err


@needs_ffmpeg
def test_refuses_a_source_that_is_too_short(tmp_path, media, capsys):
    edl, work = base_edl(), tmp_path / "work"
    edl["segments"][0].update({"in": 1.9, "dur": 1.0, "cards": [], "subs": []})
    dummy_cards(work, edl)
    code, _, err = encode(tmp_path, media, edl, work, capsys)
    assert code == 1 and "a.mp4 is only" in err


@needs_ffmpeg
def test_lock_is_held_for_the_whole_encode(tmp_path, media, capsys, monkeypatch):
    fcntl = pytest.importorskip("fcntl")
    edl, work, lock = base_edl(), tmp_path / "work", tmp_path / "render.lock"
    dummy_cards(work, edl)
    seen = []
    real_run = ilag_cut.run

    def spy(cmd):
        if cmd[0] == "ffmpeg":                        # every ffmpeg call of the encode runs inside the lock
            with open(lock, "a+") as other:           # a second opener must be refused while we encode
                try:
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    seen.append("free")
                except OSError:
                    seen.append("held")
        return real_run(cmd)

    monkeypatch.setattr(ilag_cut, "run", spy)
    code, _, err = encode(tmp_path, media, edl, work, capsys, "--lock", str(lock))
    assert code == 0, err
    assert seen and set(seen) == {"held"}
    with open(lock, "a+") as other:                   # and it is let go afterwards
        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_edl_errors_stop_encode_before_ffmpeg(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(ilag_cut, "run", lambda cmd: pytest.fail("ffmpeg must not run on an invalid EDL"))
    e = base_edl()
    e["segments"][0]["wm"] = False
    code, _, err = encode(tmp_path, tmp_path, e, tmp_path / "w", capsys)
    assert code == 1 and "no watermark" in err


# ------------------------------------------------------------------ cards (Playwright + PIL)
@pytest.fixture(scope="module")
def drawn(tmp_path_factory, media):
    """`cards` run once over the 3-segment EDL: real kit text, real NG slam frames."""
    tmp = tmp_path_factory.mktemp("ilag_cards")
    edl, work = base_edl(), tmp / "work"
    p = write(tmp, edl)
    code = ilag_cut.main(["cards", str(p), "--root", str(media), "--kit", str(KIT), "--out", str(work)])
    assert code == 0
    return edl, p, work


@needs_cards
def test_cards_draws_every_overlay_and_the_ng_frames(drawn, media):
    from PIL import Image
    edl, _, work = drawn
    _, _, segs = ilag_cut.check(edl)
    parts = ilag_cut.all_parts(segs)
    for el, tx in ilag_cut.wanted_cards(parts, True):
        im = Image.open(ilag_cut.card_path(work, el, tx))
        assert im.size == (1080, 1920) and im.mode == "RGBA", el
    frames = sorted((work / "cards").glob("ng-*/*.jpg"))
    assert len(frames) == 43 and Image.open(frames[0]).size == (1080, 1920)


@needs_cards
def test_custom_text_changes_the_name_card(drawn, tmp_path):
    from PIL import Image, ImageChops
    _, _, work = drawn
    custom = {"nm1": "เสี่ยบอย", "nm2": "นักต้มตุ๋นประจำตลาด", "nm3": "ฉายา: ชื่อใครก็ซวยคนนั้น"}
    ilag_cut.render_card_set(KIT, work, [("name", {}), ("name", {**custom, "nm1": "ป้าสมร"})])
    default, changed = (Image.open(ilag_cut.card_path(work, "name", t)).convert("RGBA")
                        for t in ({}, {**custom, "nm1": "ป้าสมร"}))
    assert changed.size == (1080, 1920) and changed.mode == "RGBA"
    assert ImageChops.difference(default, changed).getbbox() is not None
    assert changed.getchannel("A").getbbox() is not None          # something was drawn


def first_text_line_width(png):
    """Width of the topmost solid-alpha line of a card (the gold text; the ornament under it is a separate band)."""
    from PIL import Image
    solid = Image.open(png).getchannel("A").point(lambda v: 255 if v > 250 else 0)
    rows = list(solid.resize((1, solid.height), Image.BOX).tobytes())
    top = next(y for y, v in enumerate(rows) if v)
    end = next(y for y in range(top, len(rows)) if not any(rows[y:y + 7]))
    left, _, right, _ = solid.crop((0, top, solid.width, end)).getbbox()
    return right - left


@needs_cards
def test_fit_keeps_the_kits_own_inline_size_per_element(drawn):
    """skip and now share the class string 'tct gold drop fit'; only now authors font-size:100px (skip is 116px).  The
    same text must come out about 16% wider on skip; a size map keyed by the class alone gave both 100px."""
    _, _, work = drawn
    t = {"tct": "ทดสอบ"}
    ilag_cut.render_card_set(KIT, work, [("skip", t), ("now", t)])
    skip, now = (first_text_line_width(ilag_cut.card_path(work, el, t)) for el in ("skip", "now"))
    assert 1.12 < skip / now < 1.20, (skip, now)


@needs_cards
def test_cards_are_cached_and_a_kit_change_redraws(drawn, tmp_path, media, capsys):
    edl, p, work = drawn
    assert ilag_cut.main(["cards", str(p), "--root", str(media), "--kit", str(KIT), "--out", str(work)]) == 0
    assert "0 rendered" in capsys.readouterr().out
    kit2 = tmp_path / "kit2"
    shutil.copytree(KIT, kit2)
    shutil.copy(work / "kit/logo.png", kit2 / "logo.png")         # a work-folder kit has logo.png, not images/
    (kit2 / "kit.tpl.html").write_text((kit2 / "kit.tpl.html").read_text(encoding="utf-8") + "\n<!-- v2 -->\n",
                                       encoding="utf-8")
    assert ilag_cut.main(["cards", str(p), "--root", str(media), "--kit", str(kit2), "--out", str(work)]) == 0
    assert "0 rendered" not in capsys.readouterr().out            # the old cards were drawn from another kit


@needs_cards
def test_cards_then_encode_end_to_end(drawn, media, tmp_path, capsys):
    edl, p, work = drawn
    code = ilag_cut.main(["encode", str(p), "--root", str(media), "--out", str(work)])
    cap = capsys.readouterr()
    assert code == 0, cap.err
    assert "encoded 6" in cap.out and (work / "out/ep.mp4").stat().st_size > 10_000


def run_kit_overlays(work, names):
    """The kit's own render (render_kit.py, as REBUILD step 1 runs it) of some elements, from the staged copy."""
    subprocess.run([sys.executable, "-I", str(work / "kit/render_kit.py"), str(work / "kit"), ",".join(names)],
                   check=True, capture_output=True)
    return work / "kit/overlays"


SAMPLES = {      # the kit's own sample lines (kit.tpl.html), with the kit's <br> written as \n
    "title": {"season": "ตลาดนี้มีกรรม", "ep": "EP.1", "title": "ตบผิดคน", "tagline": "ทำชั่วแล้ว AI ก็ช่วยไม่ได้"},
    "name": {"nm1": "เสี่ยบอย", "nm2": "นักต้มตุ๋นประจำตลาด", "nm3": "ฉายา: ชื่อใครก็ซวยคนนั้น"},
    "namegood": {"nm1": "แม่ศรี", "nm2": "แม่ค้าผักดองเจ้าเก่าของตลาด", "nm3": "ใจดีจนโดนยืมชื่อ"},
    "fact": {"body": "ค้ำประกันให้ใคร ถ้าคนกู้ไม่จ่าย\nเจ้าหนี้ทวงเงินจากคนค้ำได้"},
    "lesson": {"body": "ชื่อเสียงสร้างมาทั้งชีวิต\nพังได้ด้วยลายเซ็นเดียว"},
    "place": {"pl1": "ตลาดซอยมะขาม", "pl2": "เช้าวันจันทร์ 06:30 น."},
    "end": {"e2": "EP.2", "e3": "ใครประกันตัวเสี่ยบอยออกมา?", "e4": "พรุ่งนี้ 20:00 น."},
}


def changed_pixels(a, b):
    from PIL import Image, ImageChops
    d = ImageChops.difference(Image.open(a).convert("RGBA"), Image.open(b).convert("RGBA")).convert("L")
    return sum(d.point(lambda v: 255 if v > 24 else 0).histogram()[255:])


TOLERANCE = 0.001 * 1080 * 1920    # Chromium is not bit-exact between runs (a 223 px wobble was seen on `title`)


@needs_cards
@pytest.mark.parametrize("el", sorted(SAMPLES))
def test_the_kits_own_text_comes_out_as_the_kits_own_overlay(el, drawn):
    """Setting the kit's sample text through ilag_cut (with \\n for the kit's <br>) must give back the tile the CEO is
    reviewing."""
    _, _, work = drawn
    ilag_cut.render_card_set(KIT, work, [(el, SAMPLES[el])])
    changed = changed_pixels(ilag_cut.card_path(work, el, SAMPLES[el]), run_kit_overlays(work, [el]) / f"{el}.png")
    assert changed < TOLERANCE, f"{el}: {changed} px differ from the kit's own overlay"


@needs_cards
def test_the_line_break_matters(drawn):
    """Probe: the fact's words with a space where the kit has its <br> do NOT match the kit's tile, so the match above
    is not a coincidence of wrapping.  (The lesson plate wraps by width at the same place, so it cannot tell.)"""
    _, _, work = drawn
    spaced = {"body": SAMPLES["fact"]["body"].replace("\n", " ")}
    ilag_cut.render_card_set(KIT, work, [("fact", spaced)])
    assert changed_pixels(ilag_cut.card_path(work, "fact", spaced), run_kit_overlays(work, ["fact"]) / "fact.png") > TOLERANCE


@needs_cards
def test_cards_refuses_a_kit_with_no_logo(drawn, tmp_path, media, capsys):
    _, p, _ = drawn
    bare = tmp_path / "bare"
    shutil.copytree(KIT, bare)                       # no images/ beside it and no logo.png inside
    code = ilag_cut.main(["cards", str(p), "--root", str(media), "--kit", str(bare), "--out", str(tmp_path / "w")])
    assert code == 1 and "no logo for the kit" in capsys.readouterr().err


# ================================================================== Codex review of PR #468 (task-762348af)
def make_symlink(link, target):
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("cannot create symlinks here")


def colour_png(path):
    ff("-f", "lavfi", "-i", "color=c=red:s=64x64", "-frames:v", "1", path)


# ------------------------------------------------------------------ 1. EDL paths stay inside --root, kit Python is the repo's
def escape_world(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "outside"
    (root / "footage").mkdir(parents=True)
    outside.mkdir()
    (outside / "secret.mp4").write_bytes(b"not a video")
    return root, outside


def _link_src(e, root, outside):
    make_symlink(root / "footage/link.mp4", outside / "secret.mp4")
    e["segments"][0]["src"] = "footage/link.mp4"


ESCAPES = [
    ("dot-dot src", lambda e, r, o: e["segments"][0].update(src="../outside/secret.mp4")),
    ("absolute src", lambda e, r, o: e["segments"][0].update(src=str(o / "secret.mp4"))),
    ("symlinked src", _link_src),
    ("end card src", lambda e, r, o: e["segments"][2].update(src="footage/../../outside/secret.mp4")),
    ("ng take src", lambda e, r, o: e["segments"][1]["take"].update(src="../outside/secret.mp4")),
    ("ng take2 src", lambda e, r, o: e["segments"][1]["take2"].update(src="../outside/secret.mp4")),
    ("sfx folder", lambda e, r, o: e.update(sfx="../outside")),
    ("kit folder", lambda e, r, o: e.update(kit="../outside")),
]


@pytest.mark.parametrize("name,escape", ESCAPES, ids=[x[0] for x in ESCAPES])
def test_plan_refuses_an_edl_path_that_leaves_root(name, escape, tmp_path, capsys):
    root, outside = escape_world(tmp_path)
    e = base_edl()
    escape(e, root, outside)
    code, out, err = plan(root, e, capsys)
    assert code == 1 and "outside" in err and "refused" in err, err
    assert out == ""


def test_plan_still_takes_paths_that_stay_inside_root(tmp_path, capsys):
    root, _ = escape_world(tmp_path)
    e = base_edl()
    e["segments"][0]["src"] = "footage/../footage/a.mp4"                 # a .. that comes back
    e["segments"][2]["src"] = str(root / "footage/a.mp4")                # absolute, but inside
    code, _, err = plan(root, e, capsys)
    assert code == 0, err


@needs_ffmpeg
def test_encode_never_reaches_ffmpeg_for_an_escaping_source(tmp_path, capsys, monkeypatch):
    root, outside = escape_world(tmp_path)
    monkeypatch.setattr(ilag_cut, "run", lambda cmd: pytest.fail(f"{cmd[0]} must not run: {cmd}"))
    e = base_edl()
    e["segments"][0]["src"] = "../outside/secret.mp4"
    code, _, err = encode(root, root, e, tmp_path / "work", capsys)
    assert code == 1 and "outside" in err


@needs_ffmpeg
def test_encode_refuses_an_sfx_file_that_is_a_link_out_of_root(tmp_path, media, capsys, monkeypatch):
    root, outside = tmp_path / "root", tmp_path / "outside"
    shutil.copytree(media, root)
    outside.mkdir()
    shutil.copy(root / "sfx/boom.wav", outside / "boom.wav")
    (root / "sfx/boom.wav").unlink()
    make_symlink(root / "sfx/boom.wav", outside / "boom.wav")
    e, work = base_edl(), tmp_path / "work"
    e["segments"][0]["sfx"] = [{"name": "boom", "at": 0.1, "gain": 1}]
    dummy_cards(work, e)
    real_run = ilag_cut.run
    monkeypatch.setattr(ilag_cut, "run", lambda cmd: pytest.fail("ffmpeg must not run") if cmd[0] == "ffmpeg"
                        else real_run(cmd))
    code, _, err = encode(root, root, e, work, capsys)
    assert code == 1 and "boom" in err and "outside" in err, err


def test_output_name_cannot_carry_a_windows_drive(tmp_path, capsys):
    code, _, err = plan(tmp_path, mutate(lambda e: e.update(output="C:x.mp4")), capsys)
    assert code == 1 and "'output' must be" in err


def booby_trapped_kit(tmp_path, how):
    """A copy of the kit whose two Python files write a marker when they run."""
    base, marker = tmp_path / "evil", tmp_path / "marker"
    kit = base / "templates"
    shutil.copytree(KIT, kit)
    trap = f"import pathlib\npathlib.Path({str(marker)!r}).write_text('ran')\ndef build_kit(K):\n    return ''\n"
    for f in ("render_kit.py", "cut_logo.py"):
        (kit / f).write_text(trap, encoding="utf-8")
    if how == "png":
        colour_png(kit / "logo.png")
    else:
        (base / "images").mkdir()
        ff("-f", "lavfi", "-i", "color=c=red:s=64x64", "-frames:v", "1", base / "images/ilag-page-logo-1080.jpg")
    return kit, marker


@needs_ffmpeg
@pytest.mark.parametrize("how", ["png", "jpg"])
def test_the_kit_python_always_comes_from_the_repo_kit(how, tmp_path):
    """An EDL (or --kit) folder with its own render_kit.py / cut_logo.py must not get them run: the data (template,
    fonts, logo) is read from the folder, the Python is the repo's own."""
    kit, marker = booby_trapped_kit(tmp_path, how)
    try:
        stage, _ = ilag_cut.stage_kit(kit, tmp_path / "work")
    except ilag_cut.Fail:
        stage = tmp_path / "work/kit"                  # the repo's cut_logo.py may refuse the fake jpg; fine
    assert not marker.exists(), "the kit folder's own Python ran"
    if (stage / "render_kit.py").exists():
        assert (stage / "render_kit.py").read_bytes() == (KIT / "render_kit.py").read_bytes()


# ------------------------------------------------------------------ 2. a symlinked work sub-folder cannot redirect writes
def test_refuse_escaping_links_unit(tmp_path):
    work, outside = tmp_path / "work", tmp_path / "outside"
    (work / "real").mkdir(parents=True)
    outside.mkdir()
    make_symlink(work / "alias", work / "real")                        # inside: fine
    ilag_cut.refuse_escaping_links(work)
    make_symlink(work / "real/out", outside)                           # escapes: refused, named
    with pytest.raises(ilag_cut.Fail) as e:
        ilag_cut.refuse_escaping_links(work)
    assert str(work / "real/out") in str(e.value) and "outside" in str(e.value)


@needs_ffmpeg
@pytest.mark.parametrize("sub", ["seg", "out"])
def test_encode_refuses_a_symlinked_work_folder(sub, tmp_path, media, capsys):
    edl, work, outside = base_edl(), tmp_path / "work", tmp_path / "outside"
    dummy_cards(work, edl)
    outside.mkdir()
    make_symlink(work / sub, outside)
    code, _, err = encode(tmp_path, media, edl, work, capsys)
    assert code == 1 and "outside" in err and sub in err, err
    assert list(outside.iterdir()) == [], "something was written through the link"


def test_cards_refuses_a_symlinked_cards_folder(tmp_path, media, capsys):
    work, outside = tmp_path / "work", tmp_path / "outside"
    work.mkdir()
    outside.mkdir()
    make_symlink(work / "cards", outside)
    code = ilag_cut.main(["cards", str(write(tmp_path, base_edl())), "--root", str(media), "--kit", str(KIT),
                          "--out", str(work)])
    err = capsys.readouterr().err
    assert code == 1 and "outside" in err and "cards" in err, err
    assert list(outside.iterdir()) == [], "something was written through the link"


def test_cards_refuses_a_symlinked_kit_stage(tmp_path, media, capsys):
    work, outside = tmp_path / "work", tmp_path / "outside"
    work.mkdir()
    outside.mkdir()
    make_symlink(work / "kit", outside)
    code = ilag_cut.main(["cards", str(write(tmp_path, base_edl())), "--root", str(media), "--kit", str(KIT),
                          "--out", str(work)])
    assert code == 1 and "outside" in capsys.readouterr().err
    assert list(outside.iterdir()) == []


# ------------------------------------------------------------------ 3. a relative --out
def test_cards_hands_an_absolute_work_folder_to_the_renderer(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(ilag_cut, "render_card_set",
                        lambda kit, work, wanted, force=False: seen.update(work=work) or (0, 0, False))
    monkeypatch.setattr(ilag_cut, "draw_ng_frames", lambda work, *a, **k: seen.update(ng=work) or False)
    monkeypatch.chdir(tmp_path)
    p = write(tmp_path, base_edl())
    assert ilag_cut.main(["cards", str(p), "--root", ".", "--kit", str(KIT), "--out", "rel/work"]) == 0
    assert Path(seen["work"]).is_absolute() and Path(seen["ng"]).is_absolute(), seen


@needs_cards
def test_cards_with_a_relative_out_draws_instead_of_crashing_on_as_uri(tmp_path, media, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = write(tmp_path, base_edl())
    assert ilag_cut.main(["cards", str(p), "--root", str(media), "--kit", str(KIT), "--out", "work"]) == 0
    assert list((tmp_path / "work/cards").glob("*.png"))


@needs_ffmpeg
def test_encode_with_a_relative_out_and_root(tmp_path, media, capsys, monkeypatch):
    edl = base_edl()
    dummy_cards(tmp_path / "work", edl)
    monkeypatch.chdir(tmp_path)
    p = write(tmp_path, edl)
    code = ilag_cut.main(["encode", str(p), "--root", os.path.relpath(media, tmp_path), "--out", "work"])
    cap = capsys.readouterr()
    assert code == 0, cap.err
    assert (tmp_path / "work/out/ep.mp4").exists()


# ------------------------------------------------------------------ 4. NG frame cache vs a source replaced at the same path
def stub_ng_cards(work, parts):
    """Transparent stand-ins for every card the NG slam frames are composited from."""
    (Path(work) / "cards").mkdir(parents=True, exist_ok=True)
    png = Path(work) / "stub.png"
    ff("-f", "lavfi", "-i", "color=c=black@0.0:s=1080x1920,format=rgba", "-frames:v", "1", png)
    for el, tx in ilag_cut.wanted_cards(parts, True):
        shutil.copy(png, ilag_cut.card_path(work, el, tx))


def solid_video(path, colour):
    ff("-f", "lavfi", "-i", f"color=c={colour}:s=1080x1920:r=24:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", path)


@needs_ffmpeg
@needs_pil
def test_ng_frames_are_redrawn_when_the_source_is_replaced_at_the_same_path(tmp_path):
    from PIL import Image, ImageStat
    root, work = tmp_path / "root", tmp_path / "work"
    (root / "footage").mkdir(parents=True)
    solid_video(root / "footage/a.mp4", "red")
    _, _, segs = ilag_cut.check(base_edl())
    parts = ilag_cut.all_parts(segs)
    ng = next(p for p in parts if p["frames"])
    stub_ng_cards(work, parts)
    first = work / "cards" / f"ng-{ng['frames']['key']}" / "000.jpg"
    luma = lambda: ImageStat.Stat(Image.open(first).convert("L")).mean[0]
    assert ilag_cut.draw_ng_frames(work, root, ng, 24) is True
    red = luma()
    assert ilag_cut.draw_ng_frames(work, root, ng, 24) is False          # unchanged source: the cache still holds
    solid_video(root / "footage/a.mp4", "blue")                           # same path, other picture
    assert ilag_cut.draw_ng_frames(work, root, ng, 24) is True, "stale frames were reused"
    assert luma() < red - 10, (luma(), red)


@needs_ffmpeg
@needs_pil
def test_encode_refuses_ng_frames_drawn_from_a_replaced_source(tmp_path, capsys):
    root, work = tmp_path / "root", tmp_path / "work"
    (root / "footage").mkdir(parents=True)
    (root / "sfx").mkdir()
    for n in ("scratch", "thud", "rewind", "boom", "whoosh"):
        ff("-f", "lavfi", "-i", "sine=frequency=300:sample_rate=48000:duration=0.4", root / f"sfx/{n}.wav")
    solid_video(root / "footage/a.mp4", "red")
    edl = base_edl()
    _, _, segs = ilag_cut.check(edl)
    parts = ilag_cut.all_parts(segs)
    stub_ng_cards(work, parts)
    ilag_cut.draw_ng_frames(work, root, next(p for p in parts if p["frames"]), 24)
    solid_video(root / "footage/a.mp4", "blue")
    code, _, err = encode(root, root, edl, work, capsys)
    assert code == 1 and "stale" in err and "`cards`" in err, err


# ------------------------------------------------------------------ 5. the NG rewind reverses in RAM like a reversed clip
def test_ng_rewind_span_over_8_s_is_refused(tmp_path, capsys):
    e = mutate(lambda e: e["segments"][1]["take"].update(dur=9.0))        # rewind_in defaults to the take's start
    code, out, err = plan(tmp_path, e, capsys)
    assert code == 1 and "reverse buffers every frame in RAM" in err and "rewind" in err, err
    assert out == ""


def test_ng_rewind_span_over_8_s_by_explicit_times_is_refused(tmp_path, capsys):
    def long_rewind(e):
        e["segments"][1]["take"].update(dur=12.0)
        e["segments"][1].update(rewind_in=1.0, freeze_at=11.0)
    code, _, err = plan(tmp_path, mutate(long_rewind), capsys)
    assert code == 1 and "reverse buffers every frame in RAM" in err, err


def test_a_long_take_is_fine_when_rewind_in_keeps_the_span_short(tmp_path, capsys):
    def long_take(e):
        e["segments"][1]["take"].update(dur=12.0)
        e["segments"][1].update(rewind_in=9.0)                            # freeze_at defaults to 12: a 3 s rewind
    code, _, err = plan(tmp_path, mutate(long_take), capsys)
    assert code == 0, err


# ------------------------------------------------------------------ 6. take-2 sticker longer than its part; non-finite numbers
def test_take2_sticker_is_clamped_to_its_part():
    errors, _, segs = ilag_cut.check(base_edl())                          # take 2 is 0.8 s, the sticker is 1.5 s
    assert not errors
    take2 = [p for _, ps in segs for p in ps if p["note"] == "take 2"][0]
    sticker = take2["cards"][0]
    assert sticker["el"] == "take2" and sticker["at"] + sticker["dur"] <= take2["dur"] + 1e-9, (sticker, take2["dur"])
    e = base_edl()
    e["segments"][1]["take2"]["dur"] = 3.0                                # a long part keeps the full sticker
    _, _, segs = ilag_cut.check(e)
    take2 = [p for _, ps in segs for p in ps if p["note"] == "take 2"][0]
    assert take2["cards"][0]["dur"] == ilag_cut.TAKE2_STICKER


def raw_plan(tmp_path, edl_text, capsys):
    p = tmp_path / "edl.json"
    p.write_text(edl_text, encoding="utf-8")
    code = ilag_cut.main(["plan", str(p)])
    cap = capsys.readouterr()
    return code, cap.out, cap.err


@pytest.mark.parametrize("literal", ["Infinity", "-Infinity", "NaN", "1e999", "1" + "0" * 400])
def test_a_non_finite_or_absurd_number_is_a_clear_error_not_a_traceback(literal, tmp_path, capsys):
    text = json.dumps(base_edl(), ensure_ascii=False).replace('"dur": 1.2', f'"dur": {literal}', 1)
    assert literal in text
    code, out, err = raw_plan(tmp_path, text, capsys)
    assert code == 1 and ("'dur' must be a finite number" in err or "'dur' must be at most" in err), err
    assert "Traceback" not in err and out == ""


@pytest.mark.parametrize("field", ["at", "in", "gain", "blur", "freeze_last", "speed"])
def test_every_number_field_refuses_infinity(field, tmp_path, capsys):
    def put(e):
        s = e["segments"][0]
        if field == "at":
            s["cards"][0]["at"] = float("inf")
        else:
            s[field] = float("inf")
    code, _, err = plan(tmp_path, mutate(put), capsys)
    assert code == 1 and f"'{field}' must be" in err and "Traceback" not in err, err


# ------------------------------------------------------------------ 7. encode on Linux takes the shared render lock by default
def test_pick_lock_rules(tmp_path, capsys):
    lock = ilag_cut.DEFAULT_LOCK
    assert ilag_cut.pick_lock("mine.lock", "linux") == "mine.lock"
    assert capsys.readouterr().err == ""                                  # an explicit lock: no default, no warning
    assert ilag_cut.pick_lock(None, "linux") == lock
    err = capsys.readouterr().err
    assert err.count("WARN") == 1 and lock in err and "--lock" in err
    assert ilag_cut.pick_lock(None, "darwin") is None and ilag_cut.pick_lock(None, "win32") is None
    assert capsys.readouterr().err == ""                                  # no flock off Linux: the old --lock warning only


def test_pick_lock_without_the_lock_folder_warns_and_goes_on(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(ilag_cut, "DEFAULT_LOCK", str(tmp_path / "no-such-folder" / ".bl-render.lock"))
    assert ilag_cut.pick_lock(None, "linux") is None
    err = capsys.readouterr().err
    assert err.count("WARN") == 1 and "no render lock" in err


def test_the_default_lock_is_the_black_liquidity_render_lock():
    src = Path(ilag_cut.__file__).read_text(encoding="utf-8")
    assert '"/opt/MoonieXHQ/Work/.bl-render.lock"' in src


@needs_ffmpeg
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="the default lock is Linux only")
def test_encode_without_lock_holds_the_default_lock_and_warns_once(tmp_path, media, capsys, monkeypatch):
    fcntl = pytest.importorskip("fcntl")
    edl, work, lock = base_edl(), tmp_path / "work", ilag_cut.DEFAULT_LOCK
    dummy_cards(work, edl)
    seen, real_run = [], ilag_cut.run

    def spy(cmd):
        if cmd[0] == "ffmpeg":
            with open(lock, "a+") as other:
                try:
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    seen.append("free")
                except OSError:
                    seen.append("held")
        return real_run(cmd)

    monkeypatch.setattr(ilag_cut, "run", spy)
    code, _, err = encode(tmp_path, media, edl, work, capsys)             # no --lock
    assert code == 0, err
    assert seen and set(seen) == {"held"}
    assert err.count("render lock") == 1 and lock in err                 # six segments, one warning
    with open(lock, "a+") as other:                                       # let go afterwards
        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
