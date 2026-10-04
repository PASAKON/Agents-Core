#!/usr/bin/env python3
"""BL EP59 beats: arm B (beats.json) and arm A (armA/beats.json), task-2db3174c.

Arm B is the editorial table below: plain studio close-up (FF) for the opening, no text at frame 0, the first caption at
1.0 s; then the cut rhythm FF / COMP / EVID / KIN. Arm A is arm B with only what the headline plate forces (CHANGES_A):
the three opening beats become img-less COMP beats riding the headline backdrop. Every other beat is copied byte for
byte, so the only variable between the arms is the first 3 s and the persistent plate.

    python3 prototypes/bl-ep59/make_beats.py            (reads plates.json and take_table.json beside it)
"""
import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path("/opt/MoonieXHQ/Work/bl-ep59")
CREDIT = "ขอบคุณภาพจาก WikiFX"
FPS = 30

HEADLINE = {
    "lines": ["ใครตรวจ WikiFX", "เว็บให้คะแนนโบรก?"],
    "red": "ใครตรวจ",
    "bug_side": "left",
    "backdrop": [
        {"t0": 0, "src": "real/fb-post-head.png"},
        {"t0": 1, "src": "real/wfx-about-score.png"},
        {"t0": 2, "src": "real/wfx-stmt-score.png"},
    ],
}

# tag -> (mode, plate or None, which box, extra)
#   plate  = a key of plates.json (a derived plate; EVID/COMP img = its file)
#   box    = None | "box" (the plate's) | a key of plate["boxes"]
#   extra  = merged last (kinetic lines, avatar_until ...)
KIN = lambda *lines: {"lines": [[c, t] for c, t in lines]}
LG, MD, XL = "bl-lg", "bl-md", "bl-xl"
TABLE = [
    ("HOOK-0",      "FF",   None, None, {}),                                  # silent lead-in, no caption
    ("HOOK-1",      "FF",   None, None, {}),
    ("HOOK-2",      "FF",   None, None, {}),
    ("HOOK-3",      "COMP", "fb-h3", "box", {}),
    ("HOOK-4",      "COMP", "fb-h4", "box", {}),
    ("PATTERN-1",   "COMP", "fb-p1", "box", {}),
    ("PATTERN-2",   "COMP", "fb-p2", "box", {}),
    ("PATTERN-3",   "COMP", "fb-p2", None,  {"avatar_until": 14.7}),
    ("PATTERN-4",   "KIN",  None, None, KIN((LG, "เขาถามสี่ข้อ"), (LG, "ผมสรุปให้"))),
    ("CONTEXT-1",   "EVID", "fb-q", "q1", {}),
    ("CONTEXT-2",   "EVID", "fb-q", "q2", {}),
    ("CONTEXT-3",   "EVID", "fb-q", "q3", {}),
    ("CONTEXT-4",   "EVID", "fb-q", "q4", {}),
    ("CONTEXT-5",   "KIN",  None, None, KIN((LG, "ถามได้"), (LG, "ทุกเว็บให้คะแนน"))),
    ("MAIN-1",      "KIN",  None, None, KIN((LG, "ผมไปเปิดหน้า"), (LG, "WikiFX เอง"))),
    ("MAIN-2",      "EVID", "about-score", "box", {}),
    ("MAIN-3",      "KIN",  None, None, KIN((LG, "ไม่ได้พูดถึง"), (LG, "ค่าบริการโบรกเกอร์"))),
    ("MAIN-4",      "EVID", "about-foot-mail", "box", {}),
    ("MAIN-5",      "COMP", "contact", "box", {}),
    ("MAIN-6",      "COMP", "terms", "box", {}),
    ("MAIN-7",      "COMP", "stmt-title", "box", {}),
    ("MAIN-8",      "COMP", "stmt-l1", "box", {}),
    ("MAIN-9",      "COMP", "stmt-l2", "box", {}),
    ("MAIN-10",     "EVID", "stmt-list", "box", {}),
    ("MAIN-11",     "COMP", "partner-a", "box", {"avatar_until": 53.9}),
    ("MAIN-12",     "EVID", "partner-b", "box", {}),
    ("MAIN-13",     "KIN",  None, None, KIN((LG, "ใครตรวจเว็บนี้"), (LG, "ไม่ได้ระบุ"))),
    ("CURIOSITY-1", "EVID", "about-intro", "box", {}),
    ("CURIOSITY-2", "KIN",  None, None, KIN((LG, "ยังไม่เจอ"), (LG, "ณ วันที่ถ่าย"))),
    ("CURIOSITY-3", "KIN",  None, None, KIN((LG, "ผมไม่ได้บอกว่า"), (LG, "ใครผิด"))),
    ("CURIOSITY-4", "EVID", "about-foot-note", "box", {}),
    ("CURIOSITY-5", "EVID", "mas-title", "box", {}),
    ("SUMMARY-1",   "KIN",  None, None, KIN((LG, "ผมไม่รู้ว่า"), (LG, "โพสต์นั้นจริงไหม"))),
    ("SUMMARY-2",   "KIN",  None, None, KIN((LG, "ถามสี่ข้อนี้"), (LG, "ได้ทุกเว็บ"))),
    ("SUMMARY-3",   "KIN",  None, None, KIN((XL, "หนึ่ง"), (MD, "ใครจ่ายเงิน"), (MD, "ให้เว็บ"))),
    ("SUMMARY-4",   "KIN",  None, None, KIN((XL, "สอง"), (MD, "จ่ายแล้ว"), (MD, "คะแนนเปลี่ยนไหม"))),
    ("SUMMARY-5",   "KIN",  None, None, KIN((XL, "สาม"), (MD, "ใครตรวจ"), (MD, "เว็บอีกที"))),
    ("SUMMARY-6",   "KIN",  None, None, KIN((XL, "สี่"), (MD, "กติกาให้คะแนน"), (MD, "เปิดไหม"))),
    ("SUMMARY-7",   "COMP", "mas-title-c", "box", {}),
    ("SUMMARY-8",   "COMP", "mas-plain", None, {}),
    ("SUMMARY-9",   "COMP", "mas-plain", None, {}),
]

# the opening: beat starts that are not "line start minus 0.10 s"
FIXED_T0 = {"HOOK-0": 0.0, "HOOK-1": 1.0}
LEAD = 0.10
MAX_WINDOW = 9.0

# Arm A: the first three beats ride the headline backdrop (img-less COMP, no box, no credit); nothing else changes.
CHANGES_A = {
    "HOOK-0": "COMP", "HOOK-1": "COMP", "HOOK-2": "COMP",
}


def frame(t: float) -> float:
    return round(math.floor(t * FPS + 1e-6) / FPS, 4)


def load_timings():
    rows = {}
    for line in (WORK / "timings.tsv").read_text().splitlines()[1:]:
        tag, a, b = line.split("\t")
        rows[tag] = (float(a), float(b))
    return rows


def load_captions():
    caps = {}
    for line in (WORK / "SCRIPT.tsv").read_text().splitlines():
        parts = line.split("\t")
        caps[parts[0]] = parts[1]
    return caps


def lip_of(t0, seats):
    name = None
    for take, start in seats:
        if t0 >= start - 1e-6:
            name = take
    return name


def main():
    plates = json.loads((HERE / "plates.json").read_text())
    table_path = HERE / "take_table.json"
    if table_path.exists():
        tt = json.loads(table_path.read_text())
        cy = {k: v["cy"] for k, v in tt["takes"].items()}
        seats = sorted((k, v["seat"]) for k, v in tt["takes"].items())
        src = "take_table.json"
    else:
        cy = {"lip_a": 797, "lip_b": 862, "lip_c": 893}
        seats = [("lip_a", 0.0), ("lip_b", 38.53), ("lip_c", 76.23)]
        src = "PROVISIONAL (EP58 numbers): re-run after take_table.json exists"
    print("cap_cy source:", src, cy)
    seats = sorted(seats, key=lambda s: s[1])
    timings = load_timings()
    caps = load_captions()
    beats = []
    for tag, mode, plate, box_key, extra in TABLE:
        start = FIXED_T0.get(tag)
        if start is None:
            start = frame(timings[tag][0] - LEAD)
        ex = {}
        if mode == "FF":
            if tag != "HOOK-0":
                ex["cap"] = caps[tag]
        elif mode == "KIN":
            ex.update(copy.deepcopy(extra))
        else:
            p = plates[plate]
            ex["img"] = p["file"]
            ex["cap"] = caps[tag]
            box = p["box"] if box_key == "box" else (p["boxes"][box_key] if box_key else None)
            if box:
                ex["box"] = box
            if p.get("credit"):
                ex["credit"] = CREDIT
            if mode == "COMP":
                ex["cap_cy"] = cy[lip_of(start, seats)]
            ex.update(copy.deepcopy(extra))
        beats.append({"tag": tag, "t0": start, "mode": mode, "extra": ex})
    (HERE / "beats.json").write_text(json.dumps(beats, indent=1, ensure_ascii=False) + "\n")

    armA = []
    for b in beats:
        b = copy.deepcopy(b)
        if b["tag"] in CHANGES_A:
            b["mode"] = CHANGES_A[b["tag"]]
            ex = {k: v for k, v in b["extra"].items() if k in ("cap",)}
            ex["cap_cy"] = cy["lip_a"]
            b["extra"] = ex
        armA.append(b)
    doc = {"headline": HEADLINE, "beats": armA}
    (HERE / "armA").mkdir(exist_ok=True)
    (HERE / "armA/beats.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    # render windows: <= MAX_WINDOW s, every seam exactly on a beat's t0 (the same for both arms)
    total = frame(94.0839)
    cuts = sorted({b["t0"] for b in beats if b["t0"] > 0})
    segs, start, k = [], 0.0, 1
    while start < total - 1e-6:
        ends = [c for c in cuts if start + 1e-6 < c <= start + MAX_WINDOW + 1e-6]
        end = ends[-1] if ends and total - start > MAX_WINDOW else total
        segs.append({"id": f"seg{k:02d}", "t0": start, "t1": end})
        start, k = end, k + 1
    (HERE / "segments.json").write_text(json.dumps({"segments": segs, "total": total}, indent=1) + "\n")
    print("windows", len(segs), [round(g["t1"] - g["t0"], 2) for g in segs])
    modes = {}
    for b in beats:
        modes[b["mode"]] = modes.get(b["mode"], 0) + 1
    print("arm B modes", modes)
    for b in beats:
        print(f"{b['t0']:7.3f} {b['tag']:12s} {b['mode']:5s} {json.dumps(b['extra'], ensure_ascii=False)[:150]}")


if __name__ == "__main__":
    sys.exit(main())
