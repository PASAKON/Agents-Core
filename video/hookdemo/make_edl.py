"""Build edl.json + timing.json for the ILAG 15 s hook demo (task-ee1dbcf0) from the per-phrase narrator durations.

usage: make_edl.py <hookdemo dir>      reads work/vo/durs.json + work/phrases.json, writes work/edl.json, work/timing.json
"""
import json
import math
import sys
from pathlib import Path

H = Path(sys.argv[1])
FPS = 24
DUR = json.loads((H / "work/vo/durs.json").read_text())
PH = json.loads((H / "work/phrases.json").read_text(encoding="utf-8"))
START, IN_GAP, LINE_GAP = 0.10, 0.04, 0.14

# phrase start times
t, ph_t = START, {}
for i, row in enumerate(DUR, 1):
    for j, d in enumerate(row, 1):
        ph_t[(i, j)] = t
        t += d + IN_GAP
    t += LINE_GAP - IN_GAP
VO_END = t - LINE_GAP

# (cut start phrase | None=0, src time, shot id, what the cut shows)
CUTS = [
    (None,   4.2,   "S1",  "the mother pounding at the stall"),
    ((1, 2), 54.0,  "S7",  "the mother chopping garlic"),
    ((1, 3), 8.0,   "S1",  "the mother pounding, collector beside her"),
    ((2, 1), 45.0,  "S6",  "pestle raised at her son"),
    ((2, 3), 48.0,  "S6",  "the son takes it in"),
    ((3, 1), 37.0,  "S5",  "phone held at arm's length, no glasses"),
    ((4, 1), 20.5,  "S3",  "the son asks what is wrong"),
    ((4, 2), 22.5,  "S3",  "the mother's bright smile over the papaya"),
    ((5, 1), 11.0,  "S2",  "the collector at the stall"),
    ((5, 2), 9.5,   "S1",  "the collector speaking: the rent"),
    ((5, 3), 13.0,  "S2",  "the mother, palms pressed together"),
    ((6, 1), 17.0,  "S2",  "the collector looking back: tomorrow noon"),
    ((6, 2), 52.0,  "S7",  "the son wiping his hands, jaw set"),
    ((6, 3), 133.0, "S17", "a hand of blank cards fanned out"),
]
SUBS = {  # (line, phrase) -> on-screen text, one line each
    (1, 1): "ป้าคนนี้", (1, 2): "ตำส้มตำเก็บเงินแปดหมื่น", (1, 3): "ห้าปี",
    (2, 1): "ใครแตะ", (2, 2): "โดนสากชี้หน้า", (2, 3): "แม้แต่ลูกชาย",
    (3, 1): "แว่นลืมได้", (3, 2): "แต่แปดหมื่น อยู่ครบ",
    (4, 1): "ลูกถามทีไร", (4, 2): "ตอบว่าไม่มีอะไร", (4, 3): "ยิ้มสุดฤทธิ์",
    (5, 1): "แต่วันนี้", (5, 2): "เจ้าของแผงมาทวงสามพัน", (5, 3): "แล้วเธอก็...",
    (6, 1): "พรุ่งนี้เที่ยง", (6, 2): "ลูกชายต้อง", (6, 3): "ทำอะไรบางอย่าง",
}


def fq(x):
    return round(x * FPS) / FPS


starts = [0.0 if c[0] is None else fq(ph_t[c[0]] - 0.02) for c in CUTS]
ends = starts[1:] + [12.0]
segs, timing = [], []
for n, (c, s, e) in enumerate(zip(CUTS, starts, ends), 1):
    frames = round((e - s) * FPS)
    dur = round(frames / FPS - 1e-5, 6)  # ilag_cut ceils to frames with a 1e-6 tolerance: 25/24 written as 1.041667 became 26 frames
    subs = []
    span = frames / FPS
    for key, text in SUBS.items():
        a = ph_t[key]
        if s - 0.03 <= a < s + span - 0.03:
            subs.append({"at": math.floor(max(a - s - 0.02, 0.0) * 1000) / 1000, "dur": 0, "text": text})
    for k, sb in enumerate(subs):  # a sub stays up until the next one starts, the last until the cut ends
        nxt = subs[k + 1]["at"] if k + 1 < len(subs) else span
        sb["dur"] = math.floor((nxt - sb["at"]) * 1000 - 2) / 1000  # stays inside the segment
    segs.append({"id": f"h{n:02d}", "kind": "clip", "src": "src/ep5-ep1.mp4", "in": c[1], "dur": dur, "gain": 0.12,
                 "note": f"{c[2]}: {c[3]}", "subs": subs, "sfx": [{"name": "thud", "at": 0.0, "gain": 0.3}]})
    timing.append({"cut": n, "from": s, "to": e, "src": c[1], "shot": c[2], "what": c[3], "subs": [x["text"] for x in subs]})
segs.append({"id": "title", "kind": "title", "src": "src/ep5-ep1.mp4", "in": 8.0, "dur": 2.0, "gain": 0.12,
             "texts": {"season": "ขายชื่อ", "ep": "EP.1", "title": "สามพันแลกชื่อ", "tagline": "คุ้มจริงเหรอ?"}})
segs.append({"id": "rew", "kind": "clip", "src": "src/ep5-ep1.mp4", "in": 4.2, "dur": 1.0, "gain": 0.3,
             "cards": [{"el": "rewcard", "at": 0.0, "dur": 1.0, "texts": {"tct": "ย้อนกลับไปเมื่อเช้านี้"}}],
             "sfx": [{"name": "whoosh", "at": 0.0, "gain": 0.5}]})
edl = {"fps": FPS, "size": [1080, 1920], "sfx": "work/sfx", "output": "hook-demo-master.mp4", "loudnorm": -16,
       "note": "ILAG 15 s Chinese-style hook demo, task-ee1dbcf0", "segments": segs}
(H / "work/edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=1), encoding="utf-8")
(H / "work/timing.json").write_text(json.dumps(
    {"vo_end": round(VO_END, 3), "phrase_start": {f"{a}.{b}": round(v, 3) for (a, b), v in ph_t.items()},
     "cuts": timing}, ensure_ascii=False, indent=1), encoding="utf-8")
print("voice ends", round(VO_END, 2), "cuts", len(CUTS), "durations", [round(e - s, 2) for s, e in zip(starts, ends)])
