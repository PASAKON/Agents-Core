#!/usr/bin/env python3
"""BL EP62 beats (CXM, one arm = EP61 arm B's look), W2 for PH #13db8720. Shape from prototypes/bl-ep61/make_beats.py.

Differences from EP61, all forced by the box (4 cores, ~2 GB free, deadline 17:45 TH) and the brief:
- NO COMP beats. A COMP beat needs the RVM matte of the lipsync take: 31/20/18 min per part on this CPU box (SKILL field note
  2026-10-04) and torch/torchvision are not installed here. The avatar is shown FF (full frame, the studio close-up) on the
  verdict/CTA lines; every "show" line is an EVID still or a KIN text card.
- Timings come from the voice's own pauses (timing/silence_align.py), not whisper.

The lipsync takes (offsets.json: A 0.00, B 26.03, C 52.85) cover [0, 13.70), [26.03, 41.58), [52.85, 67.30) in the generator
(build_cut.py LIP_DUR), so an FF beat must start AND end inside one of them; the next beat starts before the take ends.

    python3 prototypes/bl-ep62/make_beats.py
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
TOTAL = math.floor(67.7896 * FPS + 1e-6) / FPS      # decoded voice 67.7896 s -> 2033 frames
LEAD = 0.10
MAX_WINDOW = 9.0
ATTR = "ตามที่เจ้าของโพสต์เล่า"
TOXIC = "ตามที่เธอเล่า: Toxic Trading / Latency Arbitrage"


def nb(*words):
    """Each phrase is one unbreakable run: the render's Chrome has no Thai dictionary (template `.nb`)."""
    return " ".join(f'<span class="nb">{w}</span>' for w in words)


LG, MD, XL = "bl-lg", "bl-md", "bl-xl"
Y = lambda s: f'<span class="y">{s}</span>'
KIN = lambda *lines, broll=False: {"broll": broll, "lines": [[c, t] for c, t in lines]}
CLAIM, ACCT, FULL = "real/cxm-post-claim.png", "real/cxm-post-account.png", "real/cxm-post-full.png"
EV = lambda img, box, cap, credit=ATTR: {"img": img, "box": box, "cap": cap, "credit": credit}

# tag -> (mode, fixed t0 or None, extra)
TABLE = [
    ("HOOK-0",      "FF",   0.0,    {}),
    ("HOOK-1",      "EVID", 1.0,    EV(CLAIM, [120, 950, 720, 55], nb("ถือ 2 ชม.", "→", 'โดนข้อหา "เร็วเกิน"'))),
    ("HOOK-2",      "EVID", None,   EV(CLAIM, [120, 850, 720, 60], nb("เธอเล่าว่า", "CXM", "ไม่จ่ายกำไร", "เกือบ 6 ล้านบาท"))),
    ("HOOK-3",      "EVID", None,   EV(ACCT, [120, 818, 720, 55], nb("CXM แจ้งในอีเมลว่า", 'เป็น "ท็อกซิกเทรดดิ้ง"'), TOXIC)),
    ("HOOK-4",      "FF",   None,   {"cap": nb("เธอเลยถาม", "สามข้อ", "ที่ยังไร้คำตอบ")}),
    ("PATTERN-1",   "EVID", None,   EV(ACCT, [120, 818, 720, 55], nb("เธอเล่าว่า", "เปิดบัญชีเซนต์", "กับ CXM"))),
    ("PATTERN-2",   "EVID", None,   EV(FULL, [120, 1622, 720, 62], nb("22 กันยายน", "เธอว่า", "ไม่ใช้บอทเลย"))),
    ("CONTEXT-1",   "KIN",  None,   KIN((LG, "เธอเล่าว่า"), (MD, "กำไร"), (LG, Y("18,484,191.83")), (MD, "US cent"), (MD, "ราว $184,841.92"))),
    ("CONTEXT-2",   "KIN",  None,   KIN((MD, "เธอเล่าว่า: ขอถอนเงิน"), (XL, Y("$30,000")), (LG, "ถูกปฏิเสธ"), broll="broll/b39.mp4")),
    ("CONTEXT-3",   "EVID", None,   EV(ACCT, [120, 818, 720, 55], nb("เหตุผลในอีเมล", "คือเลเทนซีอาร์บิทราจ", "ตามที่เธอเล่า"))),
    ("CONTEXT-4",   "KIN",  None,   KIN((MD, "ตามโพสต์ต้นทาง"), (LG, "ใช้ประโยชน์จาก"), (LG, Y("ราคาที่ล่าช้า")), (MD, "ของระบบซื้อขาย"), broll="broll/b12.mp4")),
    ("CONTEXT-5",   "KIN",  None,   KIN((MD, "เธอเล่าว่า:"), (LG, "ได้คืนเฉพาะ" + Y("เงินต้น")), (LG, "กำไรยังไม่ได้"), broll="broll/b03.mp4")),
    ("MAIN-1",      "KIN",  None,   KIN((MD, "คำถามของเธอ ข้อ 1/3"), (LG, Y("ออเดอร์ไหน") + "ผิด?"))),
    ("MAIN-2",      "KIN",  None,   KIN((MD, "คำถามของเธอ ข้อ 2/3"), (LG, "ล่าช้า"), (LG, Y("กี่มิลลิวินาที") + "?"), broll="broll/b28.mp4")),
    ("MAIN-3",      "KIN",  None,   KIN((MD, "คำถามของเธอ ข้อ 3/3"), (XL, "ผิดกฎ" + Y("ข้อไหน") + "?"))),
    ("MAIN-4",      "KIN",  None,   KIN((MD, "เธอเล่าว่า:"), (LG, "MT5 Journal"), (XL, Y("116 หน้า")), broll="broll/b07.mp4")),
    ("MAIN-5",      "FF",   None,   {"cap": nb("ฝั่ง CXM", "เรายังไม่ได้ฟัง")}),
    ("CURIOSITY-1", "KIN",  41.5333, KIN((LG, "ก่อนเปิดบัญชี"), (LG, "เคยอ่าน" + Y("ข้อตกลง")), (LG, "ข้อนี้ไหม?"))),
    ("CURIOSITY-2", "KIN",  None,   KIN((LG, "ใครตัดสินว่า"), (LG, "อะไรคือ" + Y("ท็อกซิก")), (MD, "และดูจากอะไร?"))),
    ("SUMMARY-1",   "KIN",  None,   KIN((MD, "ก่อนเปิดบัญชีเซนต์"), (XL, "เช็ก " + Y("4 อย่าง")))),
    ("SUMMARY-2",   "KIN",  None,   KIN((MD, "เช็กข้อ 1/4"), (LG, "อ่านข้อตกลง"), (LG, Y("เรื่องท็อกซิก") + "ให้จบ"))),
    ("SUMMARY-3",   "KIN",  None,   KIN((MD, "เช็กข้อ 2/4"), (LG, "ลอง" + Y("ถอนก้อนเล็ก") + "ก่อน"), broll="broll/b29.mp4")),
    ("SUMMARY-4",   "KIN",  None,   KIN((MD, "เช็กข้อ 3/4"), (LG, "เก็บ" + Y("บันทึกเทรด")), (LG, "กับภาพหน้าจอทุกวัน"))),
    ("SUMMARY-5",   "KIN",  None,   KIN((MD, "เช็กข้อ 4/4"), (LG, "ตรวจ" + Y("บริษัท")), (LG, "และหน่วยกำกับ"), (LG, "ของบัญชี"))),
    ("SUMMARY-6",   "FF",   None,   {"cap": nb("เราไม่ได้แนะนำเจ้าไหน", "แค่ชี้วิธีดูให้เป็น")}),
    ("SUMMARY-7",   "FF",   None,   {"cap": nb('คอมเมนต์ "เช็กลิสต์"', "ถ้าอยากได้")}),
    ("SUMMARY-8",   "FF",   None,   {"cap": nb("ยังฟังฝั่งเดียว", "เช็กก่อนเชื่อ")}),
    # the take C ends at 67.30 and the voice at 67.79: the last half second is a text card (the .bl-legal label stays on)
    ("SUMMARY-9",   "KIN",  67.2667, KIN((LG, "ยังฟัง" + Y("ฝั่งเดียว")), (LG, "เช็กก่อนเชื่อ"))),
]


def frame(t):
    return round(math.floor(t * FPS + 1e-6) / FPS, 4)


def load_timings():
    rows = {}
    for line in (HERE / "timings.tsv").read_text().splitlines()[1:]:
        tag, a, b = line.split("\t")
        rows[tag] = (float(a), float(b))
    return rows


def main():
    timings = load_timings()
    beats = []
    for tag, mode, fixed, extra in TABLE:
        t0 = fixed if fixed is not None else frame(timings[tag][0] - LEAD)
        beats.append({"tag": tag, "t0": t0, "mode": mode, "extra": extra})
    (HERE / "beats.json").write_text(json.dumps(beats, indent=1, ensure_ascii=False) + "\n")
    cuts = sorted({b["t0"] for b in beats if b["t0"] > 0})
    segs, start, k = [], 0.0, 1
    while start < TOTAL - 1e-6:
        ends = [c for c in cuts if start + 1e-6 < c <= start + MAX_WINDOW + 1e-6]
        end = ends[-1] if ends and TOTAL - start > MAX_WINDOW else TOTAL
        segs.append({"id": f"seg{k:02d}", "t0": start, "t1": end})
        start, k = end, k + 1
    (HERE / "segments.json").write_text(json.dumps({"segments": segs, "total": TOTAL}, indent=1) + "\n")
    print("windows", len(segs), [round(g["t1"] - g["t0"], 2) for g in segs], "total", TOTAL, round(TOTAL * FPS))
    modes = {}
    for b in beats:
        modes[b["mode"]] = modes.get(b["mode"], 0) + 1
    print("modes", modes)
    for b in beats:
        print(f"{b['t0']:7.3f} {b['tag']:12s} {b['mode']:5s}")


if __name__ == "__main__":
    sys.exit(main())
