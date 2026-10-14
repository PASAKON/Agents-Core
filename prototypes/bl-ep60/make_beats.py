#!/usr/bin/env python3
"""BL EP60 beats: arm B (beats.json) and arm A (armA/beats.json), task-3ae66e7a. Shape from prototypes/bl-ep59/make_beats.py.

Arm B is the editorial table below: a plain studio close-up (FF) for the opening, no text at frame 0, the first caption at
1.0 s; then the cut rhythm COMP / EVID / KIN. FF stops after the opening on purpose: arm A refuses an FF beat (the headline
plate stays up), so every later beat is one both arms can render byte for byte. Arm A = arm B with only what the headline
plate forces (CHANGES_A): the two FF opening beats become img-less COMP beats riding the headline backdrop.

The lipsync takes cover [0, 14.37), [38.14, 53.01), [74.17, 89.80): COMP needs the avatar, so the beats that start in the
two holes (14.37-38.14, 53.01-74.17) are EVID or KIN, and a COMP that runs past a take's end names avatar_until.

    python3 prototypes/bl-ep60/make_beats.py            (reads plates.json and take_table.json beside it)
"""
import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path("/opt/MoonieXHQ/Work/bl-ep60")
CREDIT = "ขอบคุณภาพจาก WikiFX"
FPS = 30
AUDIO_SECONDS = 90.2294          # decoded length of audio-hq.mp3 (the alignment report's last line)

HEADLINE = {
    "lines": ["WikiFX: GB เคยมีใบ", "ถูกเพิกถอนแล้ว"],
    "red": "เพิกถอน",
    "bug_side": "left",
    "backdrop": [
        {"t0": 0, "src": "real/gb-article-oct.png"},
        {"t0": 1, "src": "real/gb-warning.png"},
        {"t0": 2, "src": "real/gb-licence.png"},
    ],
}

# tag -> (mode, plate or None, which box, extra)
#   plate = a key of plates.json (a derived plate); box = None | "box" (the plate's) | a key of plate["boxes"]
KIN = lambda broll, *lines: {"broll": f"broll/{broll}.mp4", "lines": [[c, t] for c, t in lines]}
LG, MD, XL = "bl-lg", "bl-md", "bl-xl"
TABLE = [
    ("HOOK-0",      "FF",   None, None, {}),                                  # silent lead-in, no caption
    ("HOOK-1",      "FF",   None, None, {}),
    ("HOOK-2",      "COMP", "warning", "box", {}),
    ("HOOK-3",      "COMP", "oct-title", "box", {}),
    ("HOOK-4",      "COMP", "header-tile", "box", {}),
    ("PATTERN-1",   "COMP", "complaint-date", "box", {}),
    ("PATTERN-2",   "COMP", "complaint-words", "box", {"avatar_until": 14.3}),   # lip_a ends at 14.3 (bl_compose window)
    ("PATTERN-3",   "KIN",  None, None, KIN("S06", (LG, "คนเดียว"), (LG, "วันเดียว"), (LG, "สองโพสต์"))),
    ("PATTERN-4",   "KIN",  None, None, KIN("S25", (LG, "ยืนยันแทนเขา"), (LG, "ไม่ได้"))),
    ("CONTEXT-1",   "EVID", "score", "box", {}),
    ("CONTEXT-2",   "KIN",  None, None, KIN("S11", (LG, "เลขขยับได้"), (LG, "ตามวันที่เปิดดู"))),
    ("CONTEXT-3",   "EVID", "oct-top", "byline", {}),
    ("CONTEXT-4",   "EVID", "oct-top", "title", {}),
    ("CONTEXT-5",   "EVID", "entity", "cysec", {}),
    ("MAIN-1",      "EVID", "header-crumb", "box", {}),
    ("MAIN-2",      "EVID", "licence-card", "box", {}),
    ("MAIN-3",      "EVID", "licence-suspect", "box", {}),
    ("MAIN-4",      "KIN",  None, None, KIN("S03", (LG, "นี่คือสิ่งที่"), (LG, "WikiFX เขียน"))),
    ("MAIN-5",      "COMP", "basic-country", "box", {}),
    ("MAIN-6",      "COMP", "basic-name", "box", {}),
    ("MAIN-7",      "COMP", "lic-no", "box", {}),
    ("MAIN-8",      "COMP", "lic-date", "box", {}),
    ("MAIN-9",      "COMP", "related-head", "box", {}),
    ("MAIN-10",     "EVID", "related-card", "box", {}),
    ("MAIN-11",     "COMP", "revoked-l1", "box", {"avatar_until": 52.94}),     # lip_b ends at 52.94
    ("MAIN-12",     "EVID", "revoked-p", "box", {}),
    ("MAIN-13",     "EVID", "revoked-cysec", "box", {}),
    ("CURIOSITY-1", "EVID", "entity", "uk", {}),
    ("CURIOSITY-2", "EVID", "entity", "names", {}),
    ("CURIOSITY-3", "EVID", "survey-title", "box", {}),
    ("CURIOSITY-4", "EVID", "survey-body", "box", {}),
    ("CURIOSITY-5", "KIN",  None, None, KIN("S30", (LG, "ดูวันที่"), (LG, "ของหลักฐาน"), (LG, "ทุกครั้ง"))),
    ("SUMMARY-1",   "KIN",  None, None, KIN("S02", (LG, "สรุป"), (LG, "GB ยังมีใบไหม"))),
    ("SUMMARY-2",   "KIN",  None, None, KIN("S21", (LG, "ยังไม่ได้เช็ก"), (LG, "ที่ CySEC เอง"))),
    ("SUMMARY-3",   "KIN",  None, None, KIN("S24", (LG, "ก่อนเลือกโบรก"), (LG, "เช็กสามอย่าง"))),
    ("SUMMARY-4",   "KIN",  None, None, KIN("S20", (XL, "หนึ่ง"), (MD, "ค้นเลขใบ"), (MD, "ที่เว็บทางการ"))),
    ("SUMMARY-5",   "KIN",  None, None, KIN("S29", (XL, "สอง"), (MD, "ชื่อบริษัท"), (MD, "ต้องตรงกัน"))),
    ("SUMMARY-6",   "KIN",  None, None, KIN("S16", (XL, "สาม"), (MD, "ลองถอน"), (MD, "ก้อนเล็กก่อน"))),
    ("SUMMARY-7",   "COMP", "oct-title-c", "box", {}),
    ("SUMMARY-8",   "COMP", "survey-plain", "box", {}),
    ("SUMMARY-9",   "COMP", "survey-date", "box", {"avatar_until": 89.72}),   # lip_c ends at 89.72, the clip at 90.23
]

# the opening: beat starts that are not "line start minus 0.10 s"
FIXED_T0 = {"HOOK-0": 0.0, "HOOK-1": 1.0}
LEAD = 0.10
MAX_WINDOW = 9.0

# Arm A: the two FF opening beats ride the headline backdrop (img-less COMP, no box, no credit); nothing else changes.
CHANGES_A = {"HOOK-0": "COMP", "HOOK-1": "COMP"}


def frame(t: float) -> float:
    return round(math.floor(t * FPS + 1e-6) / FPS, 4)


def load_timings():
    rows = {}
    for line in (WORK / "timings.tsv").read_text().splitlines()[1:]:
        tag, a, b = line.split("\t")
        rows[tag] = (float(a), float(b))
    return rows


def load_captions():
    return {l.split("\t")[0]: l.split("\t")[1] for l in (WORK / "SCRIPT.tsv").read_text().splitlines() if l.strip()}


def lip_of(t0, seats):
    name = None
    for take, start in seats:
        if t0 >= start - 1e-6:
            name = take
    return name


def main():
    plates = json.loads((HERE / "plates.json").read_text())
    tt = json.loads((HERE / "take_table.json").read_text())
    cy = {k: v["cy"] for k, v in tt["takes"].items()}
    seats = sorted(((k, v["seat"]) for k, v in tt["takes"].items()), key=lambda s: s[1])
    print("cap_cy from take_table.json:", cy)
    timings, caps = load_timings(), load_captions()
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
    (HERE / "armA").mkdir(exist_ok=True)
    (HERE / "armA/beats.json").write_text(json.dumps({"headline": HEADLINE, "beats": armA}, indent=1, ensure_ascii=False) + "\n")
    # render windows: <= MAX_WINDOW s, every seam exactly on a beat's t0 (the same for both arms)
    # 2706 frames = the decoded audio (90.229 s). bl_merge reads the mp3's container duration (90.279 s: a 25 ms start offset plus
    # padding) and would expect 2708 +-1, so the merge runs against a PCM copy of the same audio (see REPORT, gate notes)
    total = frame(AUDIO_SECONDS)
    cuts = sorted({b["t0"] for b in beats if b["t0"] > 0})
    segs, start, k = [], 0.0, 1
    while start < total - 1e-6:
        ends = [c for c in cuts if start + 1e-6 < c <= start + MAX_WINDOW + 1e-6]
        end = ends[-1] if ends and total - start > MAX_WINDOW else total
        segs.append({"id": f"seg{k:02d}", "t0": start, "t1": end})
        start, k = end, k + 1
    (HERE / "segments.json").write_text(json.dumps({"segments": segs, "total": total}, indent=1) + "\n")
    print("windows", len(segs), [round(g["t1"] - g["t0"], 2) for g in segs], "total", total, round(total * FPS))
    modes = {}
    for b in beats:
        modes[b["mode"]] = modes.get(b["mode"], 0) + 1
    print("arm B modes", modes)
    for b in beats:
        print(f"{b['t0']:7.3f} {b['tag']:12s} {b['mode']:5s} {json.dumps(b['extra'], ensure_ascii=False)[:140]}")


if __name__ == "__main__":
    sys.exit(main())
