#!/usr/bin/env python3
"""Cut a 10-12 min ILAG lakorn EP from an EDL (JSON) with the channel kit v1.

Generalises knowledge/brand-knowledge/brands/ilag/templates/build_demo.py (the hard-coded 44 s demo): every segment,
card, sticker, sfx and subtitle comes from the EDL.  The kit's look is untouched; this tool only sets the kit's text.

  ilag_cut.py plan   <edl.json> [--root DIR]
        validate, print the timeline.  Stdlib only, no ffmpeg.  Exit 1 with every error listed.
  ilag_cut.py cards  <edl.json> --out WORK [--kit TEMPLATES] [--root DIR] [--force]
        render every overlay the EDL needs (kit text set per card, 1080x1920 transparent PNG, cached by sha256) and the
        NG slam frames.  Needs Playwright + PIL: run it with /opt/MoonieXHQ/Agents/Core/.venv/bin/python.
  ilag_cut.py encode <edl.json> --out WORK [--root DIR] [--lock FILE]
        encode each segment to WORK/seg/<id>.mp4 (a segment whose inputs are unchanged is skipped), then concat copy +
        loudnorm to WORK/out/<output>.  Stdlib + ffmpeg/ffprobe on PATH only, so it runs on winbox Windows Python.
        On Linux without --lock it warns once and holds /opt/MoonieXHQ/Work/.bl-render.lock (one render at a time).

EDL (JSON).  Paths are relative to --root (default: the EDL's folder) and must resolve, symlinks followed, to inside
it: a src, sfx or kit that leads outside is an error.  The kit folder gives the template, fonts and logo only; the kit's
Python (render_kit.py, cut_logo.py) is always the repo's own copy.  The work folder (--out) may hold no symlink that
resolves outside it.  Times are seconds; gains are linear; every number must be finite and at most 1e6.
  top level   fps (24)  size [1080,1920]  sfx "sfx" (folder of <name>.wav)  kit "templates" (default for `cards --kit`)
              output "ilag-ep.mp4"  loudnorm -16 (LUFS)  segments [...]  note
  every segment   id (unique, A-Za-z0-9_-)  kind  note  cards  subs  sfx          (ng: cards/subs/sfx sit inside take/take2)
    cards [{el: skip|rewcard|flash|now|place|name|namegood|fact|lesson, at, dur, texts{...}}]
        0.25 s alpha fade in and out, inside the segment
        texts: skip/rewcard/now tct | flash fct, fsub | place pl1, pl2 | name, namegood nm1, nm2, nm3 | fact, lesson body
        (fact and lesson body may hold one "\n": it becomes the kit's <br>; no other text may span lines)
    subs  [{at, dur, text}]            segment-local time, no overlaps
    sfx   [{name, at, gain}]           <sfx>/<name>.wav
  kind clip   src in dur  [speed reverse grade(none|flash|desat) blur freeze_last gain wm blooper]
       still  src dur     [grade blur wm blooper]
       ng     take{src,in,dur}  freeze_at  tape  take2{src?,in,dur}  [rewind_in wm]
              expands to: the bad take, freeze + NG stamp + tape, rewind, take 2 with the "เทค 2" sticker
       title  src [in dur blur gain]  texts{season, ep, title, tagline}      (over a blurred clip or still; the title
                                                                              takes no quote marks)
       end    src [in dur blur gain]  texts{e2, e3, e4 [, e1, e5]}
       blooper_header  src [freeze_at dur]                                   (on a frozen frame)
  A clip/still with "blooper": true gets the "bltag" corner tag and no watermark.  grade "flash" adds the black and
  white flashback grade (kit v2) and the "อดีต" clock tag.  Story segments (clip, still, ng) carry the watermark; title, end, blooper_header and
  blooper segments never do.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FADE = 0.25                     # card alpha fade in/out, like build_demo.fade()
NG_FREEZE = 1.8                 # freeze + stamp + tape (build_demo B2)
NG_STAMP_FRAME, NG_TAPE_FRAME = 3, 9
NG_SCALES = {3: 1.55, 4: 1.25, 5: 1.06, 6: 0.97}
NG_SHAKE = {4: (14, -8), 5: (-9, 6), 6: (5, -3)}
REWIND_SPEED = 1.85
TAKE2_STICKER = 1.5
DEFAULT_LOCK = "/opt/MoonieXHQ/Work/.bl-render.lock"    # the BLACK LIQUIDITY render lock: one render at a time on Contabo
REVERSE_MAX = 8                 # seconds of source a reverse may buffer: every frame sits in RAM
NUM_MAX = 1e6                   # larger than any EDL number; inf, nan and 1e999 are typos that would overflow
SIZE = [1080, 1920]
ENC_SALT = "ilag_cut-2"         # bump when the filter graphs change: invalidates every cached segment
SRC_STAMP = ".src"              # in an NG frame folder: path, size and mtime_ns of the source the frames were cut from
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
REPO_KIT = Path(__file__).resolve().parents[1] / "knowledge/brand-knowledge/brands/ilag/templates"
KIT_PYTHON = ("render_kit.py", "cut_logo.py")    # the only Python `cards` runs: always REPO_KIT's copy, never an EDL path's
DASHES = "—–"
GUILLEMETS = "\u00ab\u00bb"
PATH_KEYS = {"src", "kit", "sfx", "output", "id"}      # strings the dash rule does not read

# kit element -> {EDL text key: CSS selector inside #<el>}; the selector names the node whose text we set
ELEMENTS = {
    "wm": {}, "ftag": {}, "rew": {}, "take2": {}, "bltag": {}, "blooper": {}, "ngs": {},
    "skip": {"tct": ".tct"}, "rewcard": {"tct": ".tct"}, "now": {"tct": ".tct"},
    "flash": {"fct": ".fct", "fsub": ".fsub"},
    "place": {"pl1": ".pl1", "pl2": ".pl2"},
    "name": {"nm1": ".nm1", "nm2": ".nm2", "nm3": ".nm3"}, "namegood": {"nm1": ".nm1", "nm2": ".nm2", "nm3": ".nm3"},
    "fact": {"body": ".body"}, "lesson": {"body": ".ls-plate"},
    "title": {"season": ".ts-series span", "ep": ".ts-pill .pill", "title": ".ts-ep span", "tagline": ".ts-tag"},
    "ng": {"tape": ".tape span"}, "ngt": {"tape": ".tape span"},
    "end": {"e1": ".e1 span", "e2": ".e2 span", "e3": ".e3 span", "e4": ".e4", "e5": ".e5"},
    "sub": {"sub": ".sub span"},
}
CARD_EL = ("skip", "rewcard", "flash", "now", "place", "name", "namegood", "fact", "lesson")
MULTILINE = {("fact", "body"), ("lesson", "body")}    # texts where the kit itself has a <br>; at most 2 lines
REQUIRED = {"skip": ("tct",), "rewcard": ("tct",), "flash": ("fct", "fsub"), "place": ("pl1", "pl2"),
            "name": ("nm1", "nm2", "nm3"), "namegood": ("nm1", "nm2", "nm3"), "fact": ("body",), "lesson": ("body",),
            "title": ("season", "ep", "title", "tagline"), "end": ("e2", "e3", "e4")}
GRADES = {
    "flash": "hue=s=0,eq=contrast=1.12,vignette=PI/4,noise=alls=9:allf=t",
    "desat": "hue=s=0.3,eq=brightness=-0.05",
    "rewind": "eq=saturation=0.75,noise=alls=14:allf=t",
}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class Fail(Exception):
    pass


def q(d, fps):
    """Round a length up to whole frames (what ffmpeg's -t does anyway), so every segment is a whole number of frames
    and the concat offsets stay on the frame grid."""
    return math.ceil(d * fps - 1e-6) / fps


def fmt(x):
    return f"{x:.6f}".rstrip("0").rstrip(".") or "0"


def enc_args(fps):
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(fps),
            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


# ------------------------------------------------------------------ validation + expansion into encodable parts
class V:
    """Collects every error and warning; getters return None when the field is wrong (the error is recorded)."""

    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def keys(self, obj, allowed, where):
        for k in obj:
            if k not in allowed:
                self.err(where, f"unknown field '{k}' (allowed: {', '.join(sorted(allowed))})")

    def num(self, obj, key, where, default=None, lo=None, gt=None, hi=None):
        if key not in obj:
            if default is None:
                self.err(where, f"'{key}' is required")
            return default
        x = obj[key]
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            self.err(where, f"'{key}' must be a number, got {x!r}")
            return None
        shown = repr(x) if len(repr(x)) <= 24 else repr(x)[:21] + "..."
        if isinstance(x, float) and not math.isfinite(x):           # json.loads takes Infinity, -Infinity, NaN, 1e999
            self.err(where, f"'{key}' must be a finite number, got {shown}")
            return None
        if abs(x) > NUM_MAX:                                         # q() and int() overflow long before this
            self.err(where, f"'{key}' must be at most {NUM_MAX:g} in size, got {shown}")
            return None
        for ok, bound in ((lo is None or x >= lo, f">= {lo}"), (gt is None or x > gt, f"> {gt}"),
                          (hi is None or x <= hi, f"<= {hi}")):
            if not ok:
                self.err(where, f"'{key}' must be {bound}, got {x}")
                return None
        return float(x)

    def string(self, obj, key, where, default=None):
        if key not in obj:
            if default is None:
                self.err(where, f"'{key}' is required")
            return default
        if not isinstance(obj[key], str) or not obj[key].strip():
            self.err(where, f"'{key}' must be a non-empty string")
            return None
        return obj[key]

    def flag(self, obj, key, where, default):
        if key not in obj:
            return default
        if not isinstance(obj[key], bool):
            self.err(where, f"'{key}' must be true or false")
            return default
        return obj[key]

    def texts(self, obj, el, where, required=None):
        t = obj.get("texts", {})
        if not isinstance(t, dict):
            self.err(where, "'texts' must be an object")
            return None
        known = ELEMENTS[el]
        for k, v in t.items():
            if k not in known:
                self.err(where, f"unknown text '{k}' for {el} (known: {', '.join(known) or 'none'})")
            elif not isinstance(v, str) or not v.strip():
                self.err(where, f"text '{k}' must be a non-empty string")
            elif "\n" in v and (el, k) not in MULTILINE:
                self.err(where, f"text '{k}' must be one line (only fact and lesson 'body' take a line break)")
            elif "\n" in v and (v.count("\n") > 1 or not all(x.strip() for x in v.split("\n"))):
                self.err(where, f"text '{k}' of {el}: at most 2 lines, none empty (the plate holds two)")
        for k in (required if required is not None else REQUIRED.get(el, ())):
            if k not in t:
                self.err(where, f"{el} needs text '{k}'")
        return {k: v for k, v in t.items() if k in known and isinstance(v, str)}


def card_key(el, texts):
    return hashlib.sha256(json.dumps({"el": el, "texts": texts}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def card_path(work, el, texts):
    return Path(work) / "cards" / f"{el}-{card_key(el, texts)[:16]}.png"


def frames_key(src, freeze_at, tape, fps):
    s = json.dumps({"src": src, "freeze_at": freeze_at, "tape": tape, "fps": fps}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def part(name, seg, dur, **kw):
    p = {"name": name, "seg": seg, "dur": dur, "media": "none", "src": None, "ss": 0.0, "span": dur, "speed": 1.0,
         "reverse": False, "grade": "none", "blur": 0, "freeze_last": 0.0, "gain": 1.0, "wm": False, "tags": [],
         "main_card": None, "cards": [], "subs": [], "sfx": [], "frames": None, "note": "", "_wh": tuple(SIZE)}
    p.update(kw)
    return p


def overlays_field(v, obj, where, length):
    """Validate cards / subs / sfx of one part; returns the normalised lists."""
    cards, subs, sfx = [], [], []
    for key, out in (("cards", cards), ("subs", subs), ("sfx", sfx)):
        raw = obj.get(key, [])
        if not isinstance(raw, list):
            v.err(where, f"'{key}' must be a list")
            continue
        for i, c in enumerate(raw):
            w = f"{where} {key}[{i}]"
            if not isinstance(c, dict):
                v.err(w, "must be an object")
                continue
            if key == "cards":
                v.keys(c, {"el", "at", "dur", "texts"}, w)
                el = c.get("el")
                if el not in CARD_EL:
                    v.err(w, f"'el' must be one of {', '.join(CARD_EL)}, got {el!r}")
                    continue
                at, dur = v.num(c, "at", w, lo=0), v.num(c, "dur", w, lo=0.5)
                tx = v.texts(c, el, w)
                if None not in (at, dur, tx):
                    out.append({"el": el, "at": at, "dur": dur, "texts": tx})
            elif key == "subs":
                v.keys(c, {"at", "dur", "text"}, w)
                at, dur, text = v.num(c, "at", w, lo=0), v.num(c, "dur", w, gt=0), v.string(c, "text", w)
                if text and "\n" in text:
                    v.err(w, "a subtitle line must be one line (cut it into two subs)")
                    text = None
                if None not in (at, dur, text):
                    out.append({"at": at, "dur": dur, "text": text})
            else:
                v.keys(c, {"name", "at", "gain"}, w)
                name, at, gain = v.string(c, "name", w), v.num(c, "at", w, lo=0), v.num(c, "gain", w, default=1.0, lo=0)
                if name and not NAME_RE.match(name):
                    v.err(w, f"sfx name {name!r} must be letters, digits, _ or -")
                    name = None
                if None not in (name, at, gain):
                    out.append({"name": name, "at": at, "gain": gain})
    if length is not None:
        for c in cards:
            if c["at"] + c["dur"] > length + 1e-6:
                v.err(where, f"card {c['el']} at {c['at']}+{c['dur']} ends past the segment ({fmt(length)} s)")
        for s in subs:
            if s["at"] + s["dur"] > length + 1e-6:
                v.err(where, f"sub {s['text'][:24]!r} at {s['at']}+{s['dur']} ends past the segment ({fmt(length)} s)")
        for s in sfx:
            if s["at"] >= length:
                v.err(where, f"sfx {s['name']} at {s['at']} starts after the segment ({fmt(length)} s)")
    ss = sorted(subs, key=lambda s: s["at"])
    for a, b in zip(ss, ss[1:]):
        if b["at"] < a["at"] + a["dur"] - 1e-6:
            v.err(where, f"subs overlap: {a['text'][:20]!r} ({a['at']}-{a['at'] + a['dur']}) and "
                         f"{b['text'][:20]!r} (from {b['at']})")
    return cards, subs, sfx


COMMON = {"id", "kind", "note", "cards", "subs", "sfx"}
KEYS = {
    "clip": COMMON | {"src", "in", "dur", "speed", "reverse", "grade", "blur", "freeze_last", "gain", "wm", "blooper"},
    "still": COMMON | {"src", "dur", "grade", "blur", "wm", "blooper"},
    "ng": {"id", "kind", "note", "take", "take2", "freeze_at", "tape", "rewind_in", "wm"},
    "title": COMMON | {"src", "in", "dur", "blur", "gain", "texts", "wm"},
    "end": COMMON | {"src", "in", "dur", "blur", "gain", "texts", "wm"},
    "blooper_header": COMMON | {"src", "freeze_at", "dur", "wm"},
}
TAKE_KEYS = {"src", "in", "dur", "gain", "cards", "subs", "sfx"}


def is_image(src):
    return Path(src).suffix.lower() in IMAGE_EXT


def expand_segment(v, seg, i, fps):
    """One EDL segment -> list of encodable parts (None when the segment has errors)."""
    if not isinstance(seg, dict):
        v.err(f"segment #{i + 1}", "must be an object")
        return None
    sid = seg.get("id")
    where = f"segment '{sid}'" if isinstance(sid, str) else f"segment #{i + 1}"
    if not isinstance(sid, str) or not ID_RE.match(sid):
        v.err(where, f"'id' must match {ID_RE.pattern}, got {sid!r}")
        return None
    kind = seg.get("kind")
    if kind not in KEYS:
        v.err(where, f"'kind' must be one of {', '.join(KEYS)}, got {kind!r}")
        return None
    n0 = len(v.errors)
    if kind == "ng" and any(k in seg for k in ("cards", "subs", "sfx")):
        v.err(where, "an ng segment takes cards, subs and sfx inside 'take' / 'take2' (each part has its own clock)")
    v.keys(seg, KEYS[kind] | ({"cards", "subs", "sfx"} if kind == "ng" else set()), where)
    story = kind in ("clip", "still", "ng") and not seg.get("blooper")
    wm = v.flag(seg, "wm", where, story)
    if story and not wm:
        v.err(where, "story segment has no watermark (wm must be true; only title, end, blooper_header and blooper "
                     "segments go without)")
    if not story and wm:
        v.err(where, f"{'blooper' if kind in ('clip', 'still') else kind} segment must not carry the watermark")
    parts = []
    if kind == "ng":
        parts = expand_ng(v, seg, sid, where, wm, fps)
    else:
        src = v.string(seg, "src", where)
        dur = v.num(seg, "dur", where, gt=0) if kind in ("clip", "still") else v.num(
            seg, "dur", where, default={"title": 3.0, "end": 4.5, "blooper_header": 2.2}[kind], gt=0)
        ss = v.num(seg, "in", where, default=0.0, lo=0) if kind in ("clip", "title", "end") else 0.0
        hold = v.num(seg, "freeze_last", where, default=0.0, lo=0) if kind == "clip" else 0.0
        if None not in (dur, hold):
            dur, hold = q(dur, fps), (q(hold, fps) if hold else 0.0)
        total = dur + hold if None not in (dur, hold) else None
        cards, subs, sfx = overlays_field(v, seg, where, total)
        if kind in ("clip", "still"):
            grade = seg.get("grade", "none")
            if grade not in ("none", "flash", "desat"):
                v.err(where, f"'grade' must be none, flash or desat, got {grade!r}")
            blur = v.num(seg, "blur", where, default=0.0, lo=0)
            blooper = v.flag(seg, "blooper", where, False)
            kw = dict(src=src, grade=grade, blur=blur, wm=story, cards=cards, subs=subs, sfx=sfx,
                      tags=(["ftag"] if grade == "flash" else []) + (["bltag"] if blooper else []))
            if kind == "clip":
                speed = v.num(seg, "speed", where, default=1.0, lo=0.25, hi=4)
                gain = v.num(seg, "gain", where, default=1.0, lo=0)
                rev = v.flag(seg, "reverse", where, False)
                if rev and dur and speed and dur * speed > REVERSE_MAX:
                    v.err(where, f"reverse buffers every frame in RAM; keep the source span <= {REVERSE_MAX} s "
                                 f"(got {fmt(dur * speed)})")
                if len(v.errors) == n0:
                    parts.append(part(sid, sid, total, media="video", ss=ss, span=dur * speed, speed=speed, reverse=rev,
                                      freeze_last=hold, gain=gain, **kw))
            elif len(v.errors) == n0:
                parts.append(part(sid, sid, dur, media="image", **kw))
        elif kind in ("title", "end"):
            blur = v.num(seg, "blur", where, default=22.0 if kind == "title" else 18.0, lo=0)
            gain = v.num(seg, "gain", where, default=0.15 if kind == "title" else 0.18, lo=0)
            tx = v.texts(seg, kind, where)
            sounds = [("whoosh", 0.0, 0.8), ("boom", 0.15, 1.0)] if kind == "title" else [("boom", 0.0, 0.7)]
            if len(v.errors) == n0:
                parts.append(part(sid, sid, dur, media="image" if is_image(src) else "video", src=src, ss=ss, span=dur,
                                  blur=blur, gain=gain, main_card={"el": kind, "texts": tx, "fade_in": 0.35},
                                  cards=cards, subs=subs,
                                  sfx=[{"name": n, "at": a, "gain": g} for n, a, g in sounds] + sfx))
        else:                                                           # blooper_header
            fz = v.num(seg, "freeze_at", where, default=0.0, lo=0)
            if len(v.errors) == n0:
                parts.append(part(sid, sid, dur, media="image" if is_image(src) else "freeze", src=src, ss=fz,
                                  grade="desat", main_card={"el": "blooper", "texts": {}, "fade_in": 0.2},
                                  cards=cards, subs=subs, sfx=[{"name": "scratch", "at": 0.0, "gain": 0.8}] + sfx))
    return parts if len(v.errors) == n0 else None


def expand_ng(v, seg, sid, where, wm, fps):
    n0 = len(v.errors)
    tape = v.string(seg, "tape", where)
    take, take2 = seg.get("take"), seg.get("take2")
    for nm, t in (("take", take), ("take2", take2)):
        if not isinstance(t, dict):
            v.err(where, f"'{nm}' is required: an object with src, in, dur")
    if not (isinstance(take, dict) and isinstance(take2, dict)):
        return None
    got = {}
    for nm, t in (("take", take), ("take2", take2)):
        w = f"{where} {nm}"
        v.keys(t, TAKE_KEYS, w)
        src = v.string(t, "src", w) if nm == "take" or "src" in t else take.get("src")
        ss, dur, gain = v.num(t, "in", w, lo=0), v.num(t, "dur", w, gt=0), v.num(t, "gain", w, default=1.0, lo=0)
        got[nm] = (src, ss, dur, gain, w)
    if any(None in x[:4] for x in got.values()):
        return None
    (src1, in1, dur1, g1, w1), (src2, in2, dur2, g2, w2) = got["take"], got["take2"]
    fz = v.num(seg, "freeze_at", where, default=in1 + dur1, lo=in1)
    rw = v.num(seg, "rewind_in", where, default=in1, lo=0)
    if fz is not None and rw is not None and fz <= rw:
        v.err(where, f"freeze_at ({fz}) must be after rewind_in ({rw})")
    if tape is None or fz is None or rw is None or len(v.errors) > n0:
        return None
    dur1, dur2, rdur = q(dur1, fps), q(dur2, fps), q((fz - rw) / REWIND_SPEED, fps)
    if rdur * REWIND_SPEED > REVERSE_MAX:                               # the rewind is a reversed clip: same RAM guard
        v.err(where, f"the rewind reverses {fmt(rdur * REWIND_SPEED)} s of the take and reverse buffers every frame in "
                     f"RAM; keep freeze_at - rewind_in <= {REVERSE_MAX} s (set rewind_in later in the take)")
    nfreeze = int(NG_FREEZE * fps) / fps
    c1, s1, f1 = overlays_field(v, t_obj(take), w1, dur1)
    c2, s2, f2 = overlays_field(v, t_obj(take2), w2, dur2)
    key = frames_key(src1, fz, tape, fps)
    if len(v.errors) > n0:
        return None
    return [
        part(f"{sid}.1take", sid, dur1, media="video", src=src1, ss=in1, gain=g1, wm=wm, cards=c1, subs=s1, sfx=f1,
             note="take"),
        part(f"{sid}.2freeze", sid, nfreeze, media="frames", note="freeze + NG stamp + tape",
             sfx=[{"name": "scratch", "at": 0.0, "gain": 0.9}, {"name": "thud", "at": 0.12, "gain": 1.0}],
             frames={"key": key, "src": src1, "freeze_at": fz, "tape": tape}),
        part(f"{sid}.3rew", sid, rdur, media="video", src=src1, ss=rw, span=rdur * REWIND_SPEED, speed=REWIND_SPEED,
             reverse=True,
             grade="rewind", wm=wm, tags=["rew"], gain=0.0, sfx=[{"name": "rewind", "at": 0.0, "gain": 0.9}],
             note="rewind"),
        part(f"{sid}.4take2", sid, dur2, media="video", src=src2, ss=in2, gain=g2, wm=wm,
             cards=[{"el": "take2", "at": 0.0, "dur": min(TAKE2_STICKER, dur2), "texts": {}}] + c2, subs=s2, sfx=f2,
             note="take 2"),
    ]


def t_obj(t):
    return {k: t[k] for k in ("cards", "subs", "sfx") if k in t}


def iter_text(obj, path=""):
    if isinstance(obj, dict):
        for k, x in obj.items():
            if k not in PATH_KEYS:
                yield from iter_text(x, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from iter_text(x, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def load_edl(path):
    try:
        edl = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Fail(f"cannot read EDL {path}: {e}")
    if not isinstance(edl, dict):
        raise Fail("the EDL must be a JSON object")
    return edl


def check(edl, root=None):
    """-> (errors, warnings, segments) where segments = [(segment dict, [parts])] in EDL order.  With a root, every
    path the EDL names (sources, sfx folder, kit folder) must also resolve, symlinks followed, to inside it."""
    v = V()
    v.keys(edl, {"fps", "size", "sfx", "kit", "output", "loudnorm", "segments", "note"}, "EDL")
    fps = v.num(edl, "fps", "EDL", default=24.0, lo=12, hi=60)
    if fps is not None and fps != int(fps):
        v.err("EDL", f"'fps' must be a whole number, got {fps}")
    fps = int(fps or 24)
    if edl.get("size", SIZE) != SIZE:
        v.err("EDL", f"'size' must be {SIZE} (the kit overlays are {SIZE[0]}x{SIZE[1]}), got {edl.get('size')!r}")
    out = v.string(edl, "output", "EDL", default="ilag-ep.mp4")
    if out and not re.match(r"^[^/\\:]+\.mp4$", out):
        v.err("EDL", f"'output' must be a file name ending .mp4, got {out!r}")
    v.num(edl, "loudnorm", "EDL", default=-16.0, lo=-70, hi=-5)
    for k in ("sfx", "kit"):
        if k in edl and not isinstance(edl[k], str):
            v.err("EDL", f"'{k}' must be a path string")
    segs = edl.get("segments")
    if not isinstance(segs, list) or not segs:
        v.err("EDL", "'segments' must be a non-empty list")
        return v.errors, v.warnings, []
    for path, text in iter_text(edl):
        if any(d in text for d in DASHES):
            v.err(path, f"text has an em or en dash (IRON-RULES 39): {text[:40]!r}")
        if any(g in text for g in GUILLEMETS):
            v.err(path, f"text has a guillemet, no \u00ab \u00bb in Thai text (CEO 2026-10-26; use \"...\" or none): "
                        f"{text[:40]!r}")
    ids, out_segs = {}, []
    for i, seg in enumerate(segs):
        ps = expand_segment(v, seg, i, fps)
        sid = seg.get("id") if isinstance(seg, dict) else None
        if isinstance(sid, str):
            if sid in ids:
                v.err(f"segment '{sid}'", f"duplicate id (also #{ids[sid] + 1})")
            ids.setdefault(sid, i)
        if ps is not None:
            out_segs.append((seg, ps))
    kinds = [s.get("kind") for s in segs if isinstance(s, dict)]
    if kinds.count("ng") > 2:
        v.err("EDL", f"{kinds.count('ng')} ng segments; at most 2 NG gags per EP (BRAND hard rule 4)")
    for k in ("title", "end", "blooper_header"):
        if kinds.count(k) > 1:
            v.err("EDL", f"{kinds.count(k)} {k} segments; at most 1")
    seen_header = False
    for seg in segs:
        if not isinstance(seg, dict):
            continue
        if seg.get("kind") == "blooper_header":
            seen_header = True
        elif seg.get("blooper") and not seen_header:
            v.err(f"segment '{seg.get('id')}'", "blooper segment must come after the blooper_header")
    if "blooper_header" in kinds and not any(isinstance(s, dict) and s.get("blooper") for s in segs):
        v.warnings.append("blooper_header with no blooper segment after it")
    if root is not None:
        named = [(f"segment '{p['seg']}' src", p["src"]) for _, ps in out_segs for p in ps if p["src"]]
        named += [(f"EDL '{k}'", edl[k]) for k in ("sfx", "kit") if isinstance(edl.get(k), str)]
        for what, path in dict.fromkeys(named):
            try:
                resolve(root, path, what)
            except Fail as e:
                v.errors.append(str(e))
    if not v.errors:
        total = sum(p["dur"] for _, ps in out_segs for p in ps)
        if "title" in kinds:
            hook = 0.0
            for s, ps in out_segs:
                if s["kind"] == "title":
                    break
                hook += sum(p["dur"] for p in ps)
            if not 12 <= hook <= 15:
                v.warnings.append(f"hook (everything before the title) is {hook:.1f} s; the format wants 12-15 s")
        else:
            v.warnings.append("no title segment: the hook length is not checked")
        if "end" not in kinds:
            v.warnings.append("no end card")
        used = {c["el"] for _, ps in out_segs for p in ps for c in p["cards"]}
        for el, pillar in (("lesson", "the takeaway"), ("fact", "the checked fact")):
            if el not in used:
                v.warnings.append(f"no {el} card: BRAND.md hard rule 7, every EP carries all four pillars "
                                  f"(morality, takeaway, knowledge, humour); {pillar} is missing")
        if not 600 <= total <= 1200:
            v.warnings.append(f"EP is {total:.1f} s; the channel format is 10-20 min")
    return v.errors, v.warnings, out_segs


# ------------------------------------------------------------------ overlays shared by `cards` and `encode`
def prim_overlays(p):
    """Overlays of one part in layer order: (el, texts, mode, a, b).  mode static|fadein|fade|enable."""
    o = []
    if p["wm"]:
        o.append(("wm", {}, "static", 0, 0))
    o += [(t, {}, "static", 0, 0) for t in p["tags"]]
    if p["main_card"]:
        m = p["main_card"]
        o.append((m["el"], m["texts"], "fadein", m["fade_in"], 0))
    o += [(c["el"], c["texts"], "fade", c["at"], c["at"] + c["dur"]) for c in p["cards"]]
    o += [("sub", {"sub": s["text"]}, "enable", s["at"], s["at"] + s["dur"]) for s in p["subs"]]
    return o


def wanted_cards(parts, with_frames):
    """Ordered unique [(el, texts)] the parts need.  with_frames adds what the NG slam frames are drawn from."""
    seen, out = set(), []
    for p in parts:
        need = [(el, tx) for el, tx, *_ in prim_overlays(p)]
        if with_frames and p["frames"]:
            need += [("wm", {}), ("ngs", {}), ("ngt", {"tape": p["frames"]["tape"]})]
        for el, tx in need:
            k = card_key(el, tx)
            if k not in seen:
                seen.add(k)
                out.append((el, tx))
    return out


def all_parts(segs):
    return [p for _, ps in segs for p in ps]


# ------------------------------------------------------------------ plan
def clock(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def cmd_plan(a):
    edl = load_edl(a.edl)
    errors, warnings, segs = check(edl, edl_root(a))
    for w in warnings:
        print(f"WARN  {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"ERROR {e}", file=sys.stderr)
        print(f"{len(errors)} error(s): the EDL is not valid", file=sys.stderr)
        return 1
    print(f"{'#':>3}  {'id':<10} {'kind':<14} {'start':>7} {'dur':>6}  overlays")
    t = 0.0
    for n, (seg, ps) in enumerate(segs, 1):
        dur = sum(p["dur"] for p in ps)
        bits = []
        for p in ps:
            if seg["kind"] == "ng":
                bits.append(f"{p['note']} {p['dur']:.1f}")
            bits += [el if mode in ("static", "fadein") else f"{el}@{a_:g}"
                     for el, _, mode, a_, _ in prim_overlays(p) if mode != "enable" and not seg["kind"] == "ng"]
            if p["subs"]:
                bits.append(f"sub x{len(p['subs'])}")
            if p["sfx"] and seg["kind"] != "ng":
                bits.append(f"sfx x{len(p['sfx'])}")
        print(f"{n:>3}  {seg['id']:<10} {seg['kind']:<14} {clock(t):>7} {dur:>6.1f}  {', '.join(bits)}")
        t += dur
    print(f"total {t:.1f} s ({clock(t)}), {len(segs)} segments, {len(all_parts(segs))} encodes, "
          f"{len(wanted_cards(all_parts(segs), True))} card PNGs")
    return 0


# ------------------------------------------------------------------ cards (Playwright + PIL)
def edl_root(a):
    """--root, else the EDL's own folder: absolute, symlinks followed."""
    return Path(a.root or Path(a.edl).resolve().parent).resolve()


def refuse_escaping_links(work):
    """Every symlink under WORK must resolve inside WORK.  A linked cards/, seg/, out/ or kit/ folder (or one linked
    file in them) would carry our writes, and the delete of a stale NG frame set, to wherever it points."""
    work = Path(work).resolve()
    bad = []
    for dirpath, dirs, files in os.walk(work):          # followlinks is off: a linked folder is listed, not entered
        for name in dirs + files:
            link = Path(dirpath) / name
            if not link.is_symlink():
                continue
            try:
                target = link.resolve()
            except (OSError, RuntimeError):             # a link loop
                bad.append(f"{link} -> (does not resolve)")
                continue
            if target != work and work not in target.parents:
                bad.append(f"{link} -> {target}")
    if bad:
        raise Fail(f"{len(bad)} symlink(s) in the work folder {work} point outside it; refused (remove them or give "
                   f"--out a real folder): " + "; ".join(bad[:5]) + (" ..." if len(bad) > 5 else ""))


def logo_source(kit):
    """(path, how): the kit folder's own logo.png (REBUILD step 0), else the Page's logo jpg next to the templates
    folder, which cut_logo.py turns into logo.png.  The logo is never redrawn."""
    kit = Path(kit)
    if (kit / "logo.png").exists():
        return kit / "logo.png", "png"
    jpg = kit.parent / "images" / "ilag-page-logo-1080.jpg"
    if jpg.exists() and (REPO_KIT / "cut_logo.py").exists():
        return jpg, "jpg"
    raise Fail(f"no logo for the kit: put logo.png in {kit} or keep images/ilag-page-logo-1080.jpg beside the templates "
               f"folder (REBUILD.md step 0 makes logo.png with cut_logo.py)")


def kit_fingerprint(kit):
    kit = Path(kit)
    h = hashlib.sha256()
    h.update((kit / "kit.tpl.html").read_bytes())
    h.update((REPO_KIT / "render_kit.py").read_bytes())                  # what actually runs
    src, how = logo_source(kit)
    h.update(src.read_bytes())
    if how == "jpg":
        h.update((REPO_KIT / "cut_logo.py").read_bytes())
    for f in sorted((kit / "fonts").glob("*.ttf")):
        h.update(f"{f.name}:{f.stat().st_size}".encode())
    return h.hexdigest()


def stage_kit(kit, work):
    """Copy the kit's data (template, fonts, logo) into WORK/kit (kit.html needs fonts/ and logo.png beside it) and
    build kit.html there.  The kit folder may be named by an EDL or by --kit, so it supplies text and pictures, never
    code: render_kit.py (run here) and cut_logo.py (run in a child) are always the repo's own copies, REPO_KIT."""
    kit, stage = Path(kit), Path(work) / "kit"
    for need in ("kit.tpl.html", "fonts"):
        if not (kit / need).exists():
            raise Fail(f"{kit} is not the ILAG templates folder: no {need}")
    for need in KIT_PYTHON:
        if not (REPO_KIT / need).is_file():
            raise Fail(f"the repo's own ILAG kit is incomplete: no {REPO_KIT / need}")
    src, how = logo_source(kit)
    stage.mkdir(parents=True, exist_ok=True)
    shutil.copy2(kit / "kit.tpl.html", stage / "kit.tpl.html")
    shutil.copy2(REPO_KIT / "render_kit.py", stage / "render_kit.py")
    shutil.copytree(kit / "fonts", stage / "fonts", dirs_exist_ok=True)
    if how == "png":
        shutil.copy2(src, stage / "logo.png")
    else:
        done = subprocess.run([sys.executable, "-I", str(REPO_KIT / "cut_logo.py"), str(src), str(stage / "logo.png")],
                              capture_output=True, text=True)
        if done.returncode:
            raise Fail(f"cut_logo.py failed (it needs numpy and PIL: use the Agents-Core venv python):\n"
                       f"{(done.stderr or done.stdout).strip()[-400:]}")
    import importlib.util
    spec = importlib.util.spec_from_file_location("ilag_render_kit", stage / "render_kit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "build_kit"):
        raise Fail(f"{REPO_KIT}/render_kit.py has no build_kit(): the repo's own kit is broken")
    return stage, mod.build_kit(stage)


def authored_fit_sizes(html):
    """{element id: {class attribute: font-size}} for a .fit node the kit gives an inline size (the 'now' card): the
    fit() re-run must put that size back, not wipe it.  Scoped by element: skip and now share one class string."""
    out, cur = {}, None
    for m in re.finditer(r'<div id="(\w+)" class="el"|class="([^"]*\bfit\b[^"]*)"\s+style="[^"]*?font-size:\s*([\d.]+px)',
                         html):
        if m.group(1):
            cur = m.group(1)
        else:
            out.setdefault(cur, {})[m.group(2)] = m.group(3)
    return out


SET_TEXT_JS = """async ({el, items, authored}) => {
  const root = document.getElementById(el);
  if (!root) throw new Error('kit has no #' + el);
  root.querySelectorAll('.fit').forEach(n => { n.style.fontSize = (authored[el] || {})[n.getAttribute('class')] || ''; });
  for (const [sel, txt] of items) {
    const n = root.querySelector(sel);
    if (!n) throw new Error('kit has no ' + sel + ' in #' + el);
    n.replaceChildren(...txt.split('\\n').flatMap((line, i) => i ? [document.createElement('br'), line] : [line]));
  }
  void root.offsetHeight;
  await document.fonts.ready;
  fit();
}"""


def render_card_set(kit, work, wanted, force=False):
    """Render [(el, texts)] to WORK/cards/<el>-<hash>.png.  Returns (rendered, reused)."""
    work = Path(work).resolve()                         # as_uri() below needs an absolute path
    refuse_escaping_links(work)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise Fail("cards needs Playwright + PIL: run with /opt/MoonieXHQ/Agents/Core/.venv/bin/python")
    (work / "cards").mkdir(parents=True, exist_ok=True)
    fp = kit_fingerprint(Path(kit))
    sidecar = work / "cards" / ".kit-sha"
    stale = sidecar.exists() and sidecar.read_text() != fp
    if stale:                                           # the kit changed since these PNGs were drawn: keep them aside
        (work / "cards" / ".old").mkdir(exist_ok=True)
        for f in (work / "cards").glob("*.png"):
            os.replace(f, work / "cards" / ".old" / f.name)
    todo = [(el, tx) for el, tx in wanted if force or not card_path(work, el, tx).exists()]
    if todo:
        stage, html = stage_kit(kit, work)
        authored = authored_fit_sizes(html)
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": SIZE[0], "height": SIZE[1]})
            for el, tx in todo:
                items = []
                for k, text in tx.items():
                    items.append([ELEMENTS[el][k], text])
                pg.goto((stage / "kit.html").as_uri() + f"?el={el}")
                pg.wait_for_function('document.body.dataset.ready === "1"')
                pg.evaluate(SET_TEXT_JS, {"el": el, "items": items, "authored": authored})
                pg.wait_for_timeout(120)
                dst = card_path(work, el, tx)
                pg.screenshot(path=str(dst) + ".tmp.png", omit_background=True)
                os.replace(str(dst) + ".tmp.png", dst)
            b.close()
    sidecar.write_text(fp)
    return len(todo), len(wanted) - len(todo), stale


def draw_ng_frames(work, root, p, fps, force=False):
    """The NG slam frames of build_demo B2, drawn in PIL so the slam and the shake are exact."""
    from PIL import Image, ImageEnhance
    f = p["frames"]
    d = Path(work) / "cards" / f"ng-{f['key']}"
    n = int(NG_FREEZE * fps)
    src = resolve(root, f["src"])
    if not src.exists():
        raise Fail(f"segment '{p['seg']}': source not found for the freeze frame: {src}")
    src_file, seen = d / SRC_STAMP, json.dumps(stat_key([src]))  # the key names the EDL's text; this names the file's state
    if not force and len(list(d.glob("*.jpg"))) == n and src_file.exists() and src_file.read_text() == seen:
        return False
    d.mkdir(parents=True, exist_ok=True)
    src_file.unlink(missing_ok=True)                            # no stamp until every frame is written
    for old in d.glob("*.jpg"):
        old.unlink()
    tmp = d / "freeze.png"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", fmt(f["freeze_at"]), "-i", str(src), "-frames:v", "1",
                        "-vf", f"scale={SIZE[0]}:{SIZE[1]}:force_original_aspect_ratio=increase,crop={SIZE[0]}:{SIZE[1]}",
                        str(tmp)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not tmp.exists():
        raise Fail(f"segment '{p['seg']}': cannot grab a frame at {f['freeze_at']} s of {src}\n{r.stderr[-600:]}")
    base = Image.open(tmp).convert("RGB")
    base = ImageEnhance.Brightness(ImageEnhance.Color(base).enhance(0.3)).enhance(0.8).convert("RGBA")
    wm = Image.open(card_path(work, "wm", {})).convert("RGBA")
    stamp = Image.open(card_path(work, "ngs", {})).convert("RGBA")
    tape = Image.open(card_path(work, "ngt", {"tape": f["tape"]})).convert("RGBA")
    big = base.resize((1112, 1978), Image.LANCZOS)
    for fr in range(n):
        dx, dy = NG_SHAKE.get(fr, (0, 0))
        im = big.crop((16 + dx, 29 + dy, 16 + dx + 1080, 29 + dy + 1920))
        im.alpha_composite(wm)
        if fr >= NG_STAMP_FRAME:
            s = NG_SCALES.get(fr, 1.0)
            st = stamp.resize((round(1080 * s), round(1920 * s)), Image.LANCZOS)
            x0, y0 = round(540 * s - 540), round(800 * s - 800)
            im.alpha_composite(st.crop((x0, y0, x0 + 1080, y0 + 1920)))
        if fr >= NG_TAPE_FRAME:
            im.alpha_composite(tape)
        im.convert("RGB").save(d / f"{fr:03d}.jpg", quality=94)
    tmp.unlink()
    src_file.write_text(seen)
    return True


def cmd_cards(a):
    edl = load_edl(a.edl)
    errors, warnings, segs = check(edl, edl_root(a))
    if errors:
        for e in errors:
            print(f"ERROR {e}", file=sys.stderr)
        return 1
    root, work = edl_root(a), Path(a.out).resolve()
    kit = a.kit or edl.get("kit")
    if not kit:
        raise Fail("no kit folder: pass --kit or set 'kit' in the EDL")
    kit = resolve(root, kit, "EDL 'kit'") if not a.kit else Path(a.kit)
    parts = all_parts(segs)
    wanted = wanted_cards(parts, True)
    rendered, reused, stale = render_card_set(kit, work, wanted, a.force)
    nf = sum(draw_ng_frames(work, root, p, int(edl.get("fps", 24)), a.force or stale)
             for p in parts if p["frames"])
    print(f"cards: {rendered} rendered, {reused} reused, {nf} NG frame set(s) drawn -> {work / 'cards'}")
    return 0


# ------------------------------------------------------------------ encode (stdlib + ffmpeg)
def inside(base, p, what, shown=None):
    """p with every symlink followed, which must sit inside base (followed too).  Returns that resolved path.
    `shown` is the text to quote in an error (what the EDL wrote), default p."""
    shown = repr(str(shown if shown is not None else p))[:120]
    try:
        base_r, p_r = Path(base).resolve(), Path(p).resolve()
    except (OSError, RuntimeError, ValueError) as e:             # a link loop, a NUL byte, ...
        raise Fail(f"{what}: {shown} does not resolve ({e}); refused")
    if p_r != base_r and base_r not in p_r.parents:
        raise Fail(f"{what}: {shown} resolves to {p_r}, outside {base_r}; refused (an EDL path must stay inside --root)")
    return p_r


def resolve(root, p, what="path"):
    """An EDL path against --root; refused when it (or a link on the way) leads outside.  Returned resolved, so the
    path that was checked is the path that is opened."""
    q = Path(p)
    return inside(root, q if q.is_absolute() else Path(root) / q, what, shown=p)


def sfx_file(root, sfx, name):
    return resolve(root, resolve(root, sfx, "sfx folder") / f"{name}.wav", f"sfx '{name}'")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise Fail(f"{cmd[0]} failed: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r.stdout


def probe(path, cache):
    path = str(path)
    if path not in cache:
        try:
            j = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                                "-of", "json", path]))
        except Fail as e:
            raise Fail(f"cannot read media {path}: {e}")
        vs = [s for s in j.get("streams", []) if s.get("codec_type") == "video"]
        cache[path] = {"w": vs[0]["width"] if vs else 0, "h": vs[0]["height"] if vs else 0,
                       "audio": any(s.get("codec_type") == "audio" for s in j.get("streams", [])),
                       "dur": float(j.get("format", {}).get("duration") or 0)}
    return cache[path]


def atempo(speed):
    out = []
    while speed > 2.0:
        out.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        out.append("atempo=0.5")
        speed /= 0.5
    if abs(speed - 1.0) > 1e-9:
        out.append(f"atempo={speed:.5f}")
    return out


def stat_key(files):
    out = []
    for f in files:
        st = Path(f).stat()
        out.append([str(f), st.st_size, st.st_mtime_ns])
    return out


def build_cmd(p, env):
    """-> (argv, input files) for one part.  Same patterns as build_demo.py."""
    fps, d, root = env["fps"], p["dur"], env["root"]
    args, files = [], []

    def add(a_, *f):
        args.extend(a_)
        files.extend(f)
        return sum(1 for x in args if x == "-i") - 1

    mk, src = p["media"], (resolve(root, p["src"], f"segment '{p['seg']}' src") if p["src"] else None)
    if mk == "video":
        vi = add(["-ss", fmt(p["ss"]), "-t", fmt(p["span"]), "-i", str(src)], src)
    elif mk == "image":
        vi = add(["-loop", "1", "-framerate", str(fps), "-t", fmt(d), "-i", str(src)], src)
    elif mk == "freeze":
        vi = add(["-ss", fmt(p["ss"]), "-i", str(src)], src)
    else:
        fdir = Path(env["work"]) / "cards" / f"ng-{p['frames']['key']}"
        vi = add(["-framerate", str(fps), "-i", str(fdir / "%03d.jpg")], *sorted(fdir.glob("*.jpg")))
    ch = []
    if mk == "frames":
        ch.append("scale=in_range=pc:out_range=tv")
    elif mk == "freeze":
        ch += ["trim=end_frame=1", "setpts=PTS-STARTPTS", f"tpad=stop_mode=clone:stop_duration={fmt(d)}", f"fps={fps}"]
    elif mk == "video":
        if p["reverse"]:
            ch.append("reverse")
        ch.append("setpts=PTS-STARTPTS" if p["speed"] == 1 else f"setpts=(PTS-STARTPTS)/{p['speed']:g}")
        if p["speed"] != 1:
            ch.append(f"fps={fps}")
    if mk != "frames" and p["_wh"] != tuple(SIZE):
        ch.append(f"scale={SIZE[0]}:{SIZE[1]}:force_original_aspect_ratio=increase,crop={SIZE[0]}:{SIZE[1]}")
    if p["grade"] != "none":
        ch.append(GRADES[p["grade"]])
    if p["blur"]:
        ch.append(f"boxblur={p['blur']:g}:2")
    if p["freeze_last"]:
        ch.append(f"tpad=stop_mode=clone:stop_duration={fmt(p['freeze_last'])}")
    vf = [f"[{vi}:v]{','.join(ch) or 'null'}[b]"]
    cur = "b"
    for k, (el, tx, mode, a_, b_) in enumerate(prim_overlays(p)):
        png = card_path(env["work"], el, tx)
        i = add(["-loop", "1", "-framerate", str(fps), "-t", fmt(d), "-i", str(png)], png)
        if mode == "static":
            vf.append(f"[{cur}][{i}:v]overlay[o{k}]")
        elif mode == "enable":
            vf.append(f"[{cur}][{i}:v]overlay=enable='between(t,{fmt(a_)},{fmt(b_)})'[o{k}]")
        else:
            if mode == "fadein":
                vf.append(f"[{i}:v]format=rgba,fade=t=in:st=0:d={a_:g}:alpha=1[c{k}]")
            else:
                vf.append(f"[{i}:v]format=rgba,fade=t=in:st={fmt(a_)}:d={FADE}:alpha=1,"
                          f"fade=t=out:st={b_ - FADE:.2f}:d={FADE}:alpha=1[c{k}]")
            vf.append(f"[{cur}][c{k}]overlay[o{k}]")
        cur = f"o{k}"
    vf.append(f"[{cur}]setsar=1,format=yuv420p[v]")
    parts = []                                                          # (input index, delay s, gain, extra filters)
    if mk == "video" and p["gain"] > 0 and env["probes"][str(src)]["audio"]:
        ex = (["areverse"] if p["reverse"] else []) + atempo(p["speed"])
        g = p["gain"]
        if p["grade"] == "flash":
            ex.append("lowpass=f=2600")
            g *= 0.8
        parts.append((vi, 0.0, g, ex))
    for s in p["sfx"]:
        wav = sfx_file(root, env["sfx"], s["name"])
        parts.append((add(["-i", str(wav)], wav), s["at"], s["gain"], []))
    si = add(["-f", "lavfi", "-t", fmt(d), "-i", "anullsrc=r=48000:cl=stereo"])
    parts.insert(0, (si, 0.0, 1.0, []))
    chains = []
    for n, (i, delay, gain, ex) in enumerate(parts):
        ms = int(delay * 1000)
        chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo{''.join(',' + e for e in ex)},"
                      f"adelay={ms}|{ms},volume={gain:g}[m{n}]")
    af = (";".join(chains) + f";{''.join(f'[m{n}]' for n in range(len(parts)))}amix=inputs={len(parts)}:"
          f"duration=longest:normalize=0,atrim=0:{fmt(d)},asetpts=PTS-STARTPTS[a]")
    out = Path(env["work"]) / "seg" / f"{p['name']}.part.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", f"{';'.join(vf)};{af}", "-map", "[v]",
           "-map", "[a]", *enc_args(fps), "-t", fmt(d), str(out)]
    return cmd, files


def pick_lock(arg, platform=None):
    """The lock file for `encode`: --lock as given; on Linux without it the box's shared render lock (the BLACK
    LIQUIDITY renders hold the same file), with one warning; nowhere else (flock is Linux only)."""
    if arg:
        return arg
    if not (platform or sys.platform).startswith("linux"):
        return None
    folder = Path(DEFAULT_LOCK).parent
    if not folder.is_dir():
        print(f"WARN  no --lock given and {folder} does not exist: encoding with no render lock", file=sys.stderr)
        return None
    print(f"WARN  no --lock given: holding the shared render lock {DEFAULT_LOCK} for this encode (one render at a "
          f"time on this box); pass --lock FILE to use another", file=sys.stderr)
    return DEFAULT_LOCK


def lock_file(path):
    try:
        import fcntl
    except ImportError:
        print("WARN  --lock ignored: file locks need Linux (flock)", file=sys.stderr)
        return None
    f = open(path, "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(f"waiting for the render lock {path} ...", file=sys.stderr)
        fcntl.flock(f, fcntl.LOCK_EX)
    return f


def preflight(edl, segs, root, work, probes):
    """Missing files and sources too short for their span; every problem listed."""
    errs = []
    for p in all_parts(segs):
        if p["src"]:
            try:
                src = resolve(root, p["src"], f"segment '{p['seg']}' src")
            except Fail as e:
                errs.append(str(e))
                continue
            info = None
            if not src.exists():
                errs.append(f"segment '{p['seg']}': source not found: {src}")
            else:
                try:
                    info = probe(src, probes)
                except Fail as e:
                    errs.append(str(e))
            if info:
                p["_wh"] = (info["w"], info["h"])
                if p["media"] == "video" and p["ss"] + p["span"] > info["dur"] + 0.1:
                    errs.append(f"segment '{p['seg']}': reads {fmt(p['ss'])}+{fmt(p['span'])} s but {src.name} is only "
                                f"{info['dur']:.2f} s long")
                if p["media"] == "freeze" and p["ss"] > info["dur"] + 0.1:
                    errs.append(f"segment '{p['seg']}': freeze_at {fmt(p['ss'])} is past the end of {src.name}")
        else:
            p["_wh"] = tuple(SIZE)
        if p["frames"]:
            fdir = Path(work) / "cards" / f"ng-{p['frames']['key']}"
            if not fdir.is_dir() or not list(fdir.glob("*.jpg")):
                errs.append(f"segment '{p['seg']}': NG slam frames missing ({fdir}); run `cards` first")
            else:                                                       # drawn from a file that has since been replaced?
                fsrc, stamp = resolve(root, p["frames"]["src"], f"segment '{p['seg']}' src"), fdir / SRC_STAMP
                if fsrc.exists() and stamp.exists() and stamp.read_text() != json.dumps(stat_key([fsrc])):
                    errs.append(f"segment '{p['seg']}': NG slam frames are stale: {fsrc.name} changed since they were "
                                f"drawn; run `cards` again")
        for s in p["sfx"]:
            try:
                wav = sfx_file(root, edl.get("sfx", "sfx"), s["name"])
            except Fail as e:
                errs.append(f"segment '{p['seg']}': {e}")
                continue
            if not wav.exists():
                errs.append(f"segment '{p['seg']}': sfx '{s['name']}' not found in {wav.parent}")
    missing = [(el, tx) for el, tx in wanted_cards(all_parts(segs), False) if not card_path(work, el, tx).exists()]
    if missing:
        errs.append(f"{len(missing)} card PNG(s) missing from {Path(work) / 'cards'}; run `ilag_cut.py cards` first "
                    f"(first: {missing[0][0]} {json.dumps(missing[0][1], ensure_ascii=False)})")
    return errs


def cmd_encode(a):
    edl = load_edl(a.edl)
    errors, warnings, segs = check(edl, edl_root(a))
    for w in warnings:
        print(f"WARN  {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"ERROR {e}", file=sys.stderr)
        return 1
    root, work = edl_root(a), Path(a.out).resolve()
    refuse_escaping_links(work)
    probes = {}
    errs = preflight(edl, segs, root, work, probes)
    if errs:
        for e in errs:
            print(f"ERROR {e}", file=sys.stderr)
        return 1
    lock = pick_lock(a.lock)
    lk = lock_file(lock) if lock else None
    try:
        fps = int(edl.get("fps", 24))
        env = {"fps": fps, "root": root, "work": work, "sfx": edl.get("sfx", "sfx"), "probes": probes}
        seg_dir = work / "seg"
        seg_dir.mkdir(parents=True, exist_ok=True)
        done = reused = 0
        parts = all_parts(segs)
        for n, p in enumerate(parts, 1):
            cmd, files = build_cmd(p, env)
            key = hashlib.sha256(json.dumps([ENC_SALT, cmd, stat_key(files)], ensure_ascii=False).encode()).hexdigest()
            mp4, stamp = seg_dir / f"{p['name']}.mp4", seg_dir / f"{p['name']}.key"
            if mp4.exists() and stamp.exists() and stamp.read_text() == key:
                reused += 1
                print(f"[{n}/{len(parts)}] {p['name']}: unchanged")
                continue
            print(f"[{n}/{len(parts)}] {p['name']}: encoding {p['dur']:.2f} s")
            stamp.unlink(missing_ok=True)
            part_mp4 = Path(cmd[-1])
            run(cmd)
            os.replace(part_mp4, mp4)
            stamp.write_text(key)
            done += 1
        (seg_dir / "list.txt").write_text("".join(f"file '{p['name']}.mp4'\n" for p in parts), encoding="utf-8")
        joined = seg_dir / "joined.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(seg_dir / "list.txt"),
             "-c", "copy", str(joined)])
        (work / "out").mkdir(exist_ok=True)
        final = work / "out" / edl.get("output", "ilag-ep.mp4")
        ln = float(edl.get("loudnorm", -16))
        run(["ffmpeg", "-v", "error", "-y", "-i", str(joined), "-c:v", "copy", "-af",
             f"loudnorm=I={ln:g}:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
             "-movflags", "+faststart", str(final)])
    finally:
        if lk:
            lk.close()
    j = json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,pix_fmt,sample_aspect_ratio,r_frame_rate,sample_rate,channels:format=duration",
                        "-of", "json", str(final)]))
    vs = next(s for s in j["streams"] if s["codec_type"] == "video")
    au = next(s for s in j["streams"] if s["codec_type"] == "audio")
    print(f"encoded {done}, unchanged {reused}")
    print(f"final: {final}")
    print(f"duration: {float(j['format']['duration']):.2f} s")
    print(f"video: pix_fmt={vs['pix_fmt']} SAR={vs.get('sample_aspect_ratio')} fps={vs['r_frame_rate']}")
    print(f"audio: {au['sample_rate']} Hz, {au['channels']} ch")
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="ilag_cut.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="verb", required=True)
    for name, fn in (("plan", cmd_plan), ("cards", cmd_cards), ("encode", cmd_encode)):
        sp = sub.add_parser(name)
        sp.add_argument("edl")
        sp.add_argument("--root", help="base folder of the EDL's relative paths (default: the EDL's folder)")
        if name != "plan":
            sp.add_argument("--out", required=True, help="work folder: cards/, seg/, out/")
        if name == "cards":
            sp.add_argument("--kit", help="the ILAG templates folder (default: 'kit' in the EDL)")
            sp.add_argument("--force", action="store_true", help="re-render every card")
        if name == "encode":
            sp.add_argument("--lock", help=f"hold an exclusive flock on this file for the whole encode (Linux only; "
                                           f"default there: {DEFAULT_LOCK})")
        sp.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except Fail as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
