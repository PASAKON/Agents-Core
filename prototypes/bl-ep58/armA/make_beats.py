#!/usr/bin/env python3
"""Arm-A beats.json for BL EP58 = arm B (prototypes/bl-ep58/beats.json) with only what the headline plate forces.

Arm B's file is read, never written. Every change is listed in CHANGES with the reason; anything not listed is
copied byte for byte (same tags, timings, captions, boxes). Run from the repo root:
    python3 prototypes/bl-ep58/armA/make_beats.py
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARM_B = HERE.parent / "beats.json"
OUT = HERE / "beats.json"

HEADLINE = {
    "lines": ["Weltrade ถูกร้องเรียน", "ถอนไม่ออก?"],
    "red": "ร้องเรียน",
    "bug_side": "left",
    "backdrop": [
        {"t0": 0, "src": "real/weltrade-header.png"},
        {"t0": 1, "src": "real/weltrade-warning.png"},
        {"t0": 2, "src": "real/wikifx-article-sep.png"},
    ],
}

# tag -> (mode or None to keep, function(extra) -> new extra, why)
def set_extra(**kw):
    def f(extra):
        out = {k: v for k, v in extra.items() if k not in ("box", "shift", "img", "avatar_until")}
        out.update(kw)
        return out
    return f

def patch(**kw):
    def f(extra):
        out = dict(extra)
        for k, v in kw.items():
            if v is None:
                out.pop(k, None)
            else:
                out[k] = v
        return out
    return f

LICENCE = "real/weltrade-licence.png"
CHANGES = {
    # first 3 s: the beats on screen at 0/1/2 s ride the three backdrop images (img-less COMP)
    "HOOK-1": (None, patch(img=None, box=None), "rides the headline backdrop 0/1/2 s"),
    "HOOK-2": (None, patch(img=None, box=None), "img-less COMP, stays on the 3rd backdrop (WikiFX article, 30 Sep) until HOOK-3's card"),
    # COMP stills whose evidence sat in the headline/date-stamp zone (y 276-522): move the page down
    "PATTERN-1": (None, patch(shift=-140), "article title was under the plate; evidence 852-898"),
    "PATTERN-2": (None, patch(shift=-470), "complaint text was at y 290; page moved below the plate, evidence 760-815"),
    "PATTERN-3": (None, patch(shift=-470), "same; evidence 755-945"),
    "MAIN-6": (None, patch(shift=-100), "title clear of the plate; evidence 892-937"),
    "MAIN-7": (None, patch(shift=-300), "green label was at y 470; now 770-845"),
    "MAIN-8": (None, patch(shift=-520), "survey title was at y 200 (under the bug and the plate); now 720-780"),
    "MAIN-9": (None, patch(shift=-520), "same; now 780-825"),
    # EVID beats whose box sat under the plate (EVID cannot shift)
    "PATTERN-4": ("KIN", lambda e: {"lines": [["bl-lg", "นี่คำผู้ร้องเรียน"], ["bl-lg", "ไม่ใช่ของกู"]], "broll": ""},
                  "complaint-1 text is only at y 285-340, under the plate; no avatar window at 16.6 s so COMP is out; KIN keeps the attribution on screen"),
    "CONTEXT-4": (None, patch(box=[40, 555, 320, 45]), "article title (y 405-600) is under the plate; spotlight the dated byline row 'WikiFX | Yesterday 06:11'"),
    "CURIOSITY-1": (None, patch(box=[205, 540, 450, 255]), "box top 475 met the date stamp; starts below it"),
    # MAIN-13: arm B moved to a new still whose contents row sits at y 687-713 (task-cc55e620); arm A follows it exactly
    "MAIN-13": (None, patch(img="real/wikifx-article-sep-contents.png", box=[60, 660, 480, 76], shift=None), "follows arm B: new contents still, box inside the safe area (60,660,480,76); no EVID lift needed"),
    # FF is refused in arm A: avatar lower, matted, over the licence page
    "SUMMARY-7": ("COMP", lambda e: {"img": LICENCE, "cap": e["cap"], "shift": 300}, "FF refused; COMP over the licence page, no box"),
    "SUMMARY-8": ("COMP", lambda e: {"img": LICENCE, "cap": e["cap"], "shift": 300}, "FF refused; same plate, no box"),
    "SUMMARY-9": ("COMP", lambda e: {"img": LICENCE, "cap": e["cap"], "shift": 300, "box": [54, 1170, 700, 70]},
                  "FF refused; spotlight the licence number line (50691) the caption sends people to check"),
}

def main():
    arm_b = json.loads(ARM_B.read_text(encoding="utf-8"))
    out = []
    for b in arm_b:
        b = copy.deepcopy(b)
        if b["tag"] in CHANGES:
            mode, fn, _why = CHANGES[b["tag"]]
            b["extra"] = fn(b.get("extra") or {})
            if mode:
                b["mode"] = mode
        out.append(b)
    OUT.write_text(json.dumps({"headline": HEADLINE, "beats": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    changed = [t for t in CHANGES]
    print(f"wrote {OUT} ({len(out)} beats, {len(changed)} changed vs arm B)")

if __name__ == "__main__":
    main()
