#!/usr/bin/env python3
"""BL EP61 beats: arm B (beats.json) and arm A (armA/beats.json), task-03f18aab. Shape from prototypes/bl-ep60/make_beats.py.

Arm B is the editorial table below: a plain studio close-up (FF) for the opening, no text at frame 0, the first caption at
1.0 s; then the cut rhythm COMP / EVID / KIN. FF stops after the opening on purpose: arm A refuses an FF beat (the headline
plate stays up), so every later beat is one both arms can render byte for byte. Arm A = arm B with only what the headline
plate forces (CHANGES_A): the two FF opening beats become img-less COMP beats riding the headline backdrop.

The lipsync takes cover [0, 16.01), [28.72, 41.84), [53.93, 67.67): COMP needs the avatar, so the beats that start in the
two holes (16.01-28.72, 41.84-53.93) are EVID or KIN, and a COMP that runs past a take's end names avatar_until.

    python3 prototypes/bl-ep60/make_beats.py            (reads plates.json and take_table.json beside it)
"""
import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path("/opt/MoonieXHQ/Work/bl-ep61")
CREDIT = "ที่มา: เว็บไซต์ Tickmill ณ 13 ต.ค. 2569"
BRAND_DISPLAY = {"ติ๊กมิลล์": " Tickmill "}
FPS = 30
AUDIO_SECONDS = 68.0174          # decoded length of audio-hq-decoded.wav

HEADLINE = {
    "lines": ["Tickmill 1 ล็อต", "จ่ายจริงเท่าไหร่?"],
    "red": "เท่าไหร่",
    "bug_side": "left",
    "backdrop": [
        {"t0": 0, "src": "real/tm-classic.png"},
        {"t0": 1, "src": "real/tm-raw.png"},
        {"t0": 2, "src": "real/tm-formula.png"},
    ],
}

# tag -> (mode, plate or None, which box, extra)
#   plate = a key of plates.json (a derived plate); box = None | "box" (the plate's) | a key of plate["boxes"]
KIN = lambda broll, *lines: {"broll": f"broll/{broll}.mp4", "lines": [[c, t] for c, t in lines]}
LG, MD, XL = "bl-lg", "bl-md", "bl-xl"
TABLE = [
    ("HOOK-0",      "FF",   None, None, {}),                                  # silent lead-in, no caption
    ("HOOK-1",      "FF",   None, None, {}),
    ("HOOK-2",      "COMP", "raw-spread", "box", {}),
    ("HOOK-3",      "COMP", "head-logo", "box", {}),
    ("HOOK-4",      "COMP", "head-pair", "box", {}),
    ("PATTERN-1",   "COMP", "formula-line", "box", {}),
    ("PATTERN-2",   "COMP", "swaps-rows", "box", {}),
    ("PATTERN-3",   "KIN",  None, None, KIN("S07", (LG, "ตัวอย่างนี้"), (LG, "จบในวัน"), (LG, "ไม่มีสว็อป"))),
    ("CONTEXT-1",   "EVID", "raw-example", "lot", {}),
    ("CONTEXT-2",   "EVID", "raw-example", "size", {}),
    ("CONTEXT-3",   "EVID", "logo-date", "box", {}),
    ("MAIN-1",      "EVID", "formula-faq", "box", {}),
    ("MAIN-2",      "EVID", "formula-own", "card", {}),
    ("MAIN-3",      "COMP", "classic-para", "box", {}),
    ("MAIN-4",      "EVID", "calc-classic", "spread", {}),
    ("MAIN-5",      "EVID", "calc-classic", "total", {}),
    ("MAIN-6",      "EVID", "raw-para-calc", "box", {}),
    ("MAIN-7",      "COMP", "ex-commission", "box", {}),
    ("MAIN-8",      "COMP", "ex-round", "box", {}),
    ("MAIN-9",      "EVID", "calc-both", "raw_total", {}),
    ("CURIOSITY-1", "KIN",  None, None, KIN("S20", (LG, "ศูนย์ทั้งคู่"), (LG, "แต่ไม่ฟรีทั้งคู่"))),
    ("CURIOSITY-2", "EVID", "classic-card", "box", {}),
    ("CURIOSITY-3", "EVID", "floor", "box", {}),
    ("SUMMARY-1",   "KIN",  None, None, KIN("S23", (LG, "ก่อนเทรด"), (LG, "เช็กสามอย่างเอง"))),
    ("SUMMARY-2",   "EVID", "checklist", "1", {}),
    ("SUMMARY-3",   "EVID", "checklist", "2", {}),
    ("SUMMARY-4",   "EVID", "checklist", "3", {}),
    ("SUMMARY-5",   "COMP", "recap-strip", "box", {}),
    ("SUMMARY-6",   "COMP", "cta-strip", "box", {}),
    ("SUMMARY-7",   "COMP", "date-strip", "box", {"avatar_until": 67.55}),   # bl_compose enforces lip_c [53.93, 67.58); the clip ends at 68.02
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
    for line in (HERE / "timings.tsv").read_text().splitlines()[1:]:
        tag, a, b = line.split("\t")
        rows[tag] = (float(a), float(b))
    return rows


def load_captions():
    out = {}
    for l in (WORK / "SCRIPT.tsv").read_text(encoding="utf-8").splitlines():
        if l.strip():
            tag, text = l.split("\t")[0], l.split("\t")[1]
            for k, v in BRAND_DISPLAY.items():
                text = text.replace(k, v)
            out[tag] = " ".join(text.split())
    return out


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
    # 2040 frames = the decoded audio (68.017 s). bl_merge reads the mp3's container duration and may expect +-1 more, so the
    # merge runs against a PCM copy of the same audio (audio-hq-decoded.wav; see REPORT, gate notes)
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
