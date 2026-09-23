"""Build groundtruth.tsv, the answer key for Jev: one row per spoken line,
from the seed's 45-line segment transcript (better-split than our own
vad_filter=False rerun -- see RUNLOG.md). Text corrected against on-screen
captions read by eye where the seed's rough ASR was wrong (spelling only,
never timing). Class/entry/focus/target/sfx are looked up against
census.json's own P1/P2/P4 arrays, not re-decided here.

Usage: python build_groundtruth.py > ../groundtruth.tsv
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
census = json.load(open(os.path.join(HERE, "..", "census.json")))

# (t0, t1, text) -- from seed/transcript-small.txt, spelling-corrected
# against captions actually read on screen (สปรติ->สเปรด, บันชี->บัญชี,
# กากไว้->กักไว้, ดาลลา->ดอลลาร์, เกรียบ->เปรียบ, หอด->หลอก, ทักกูมา as read).
LINES = [
(0.00,1.90,"มึงเคยใช้ XM Trade Forex ไหม?"),
(1.90,5.24,"แล้วมึงรู้ไหมว่าบัญชีสแตนดาร์ดของ XM สเปรดแม่งสูงชิบหาย?"),
(5.24,7.24,"คำถามคือ ทำไมมันต้องสูง?"),
(7.24,9.20,"คุณจะบอกความจริงที่ไม่มีใครบอกมึง"),
(9.20,11.34,"สเปรดที่สูง ไม่ได้สูงเพราะตลาด"),
(11.34,14.08,"แต่มันสูงเพราะมีเงินบางส่วนถูกกักไว้"),
(14.08,15.16,"กักไว้ทำอะไร?"),
(15.16,16.30,"กักไว้เป็นรีเบต"),
(16.30,17.76,"แต่มึงเคยได้คืนเต็มไหม?"),
(17.76,19.00,"ส่วนใหญ่ ไม่"),
(19.00,20.24,"มึงดูตัวอย่างนี้"),
(20.24,22.88,"บัญชี IB ที่ให้รีเบตทองคำสูงสุดจริง"),
(22.88,24.64,"คือ 15 ดอลลาร์ต่อ 1 ลอต"),
(24.64,26.26,"แต่ถ้ามึงเทรดบัญชีสแตนดาร์ด"),
(26.26,28.30,"แค่เปิดไม้แรก 0.01 ลอต"),
(28.30,30.12,"มึงก็ติดลบไปแล้ว 30 เซนต์"),
(30.12,31.16,"ถ้ามึงกด 1 ลอต"),
(31.16,33.20,"มึงติดลบ 30 ดอลลาร์ทั้งที"),
(33.20,34.20,"คำถามคือ"),
(34.20,35.90,"ถ้ารีเบตมันมี 15 ดอลลาร์"),
(35.90,37.74,"แล้วอีก 15 ดอลลาร์ หายไปไหน?"),
(37.74,38.66,"กูตอบให้"),
(38.66,40.70,"มันไปอยู่กับ IB ที่ชวนมึงมาเทรด"),
(40.70,42.10,"และที่หน้าเท่ากว่าคือ"),
(42.10,44.20,"IB พวกนั้นคืนให้มึงนิดเดียว"),
(44.20,46.20,"หรือบางคนไม่คืนให้มึงเลย"),
(46.20,47.34,"แปลกตรงๆคือ"),
(47.34,48.34,"มึงเป็นคนกด"),
(48.34,49.34,"มึงเป็นคนเสี่ยง"),
(49.34,51.10,"แต่คนอื่นกินเงินมึงเงียบ"),
(51.10,52.26,"หูพูดตรงนี้เลยนะ"),
(52.26,55.30,"ใครใช้ XM แล้วได้รีเบตมันไม่ถึง 15 ดอลลาร์ต่อหลอด"),
(55.30,56.54,"มึงกำลังเสียเปรียบ"),
(56.54,59.40,"ใครใช้ X-ness แล้วได้คืนไม่ถึง 8 ดอลลาร์ต่อหลอด"),
(59.40,61.20,"มึงก็เสียผลประโยชน์เหมือนกัน"),
(61.20,62.60,"ตลาดมันหลอกพอแล้ว"),
(62.60,64.40,"อย่ามาโง่เสียเงินให้ระบบอีก"),
(64.40,65.80,"ใครฟังมาถึงตรงนี้"),
(65.80,68.26,"กูเชื่อว่า มึงไม่อยากเสียเงินฟรีอีกต่อไป"),
(68.26,71.96,"ใครอยากได้ XM หรือ X-ness เรียบเต็ม ทักกูมา"),
(71.96,73.66,"บโรคอื่นก็มีคืนเหมือนกัน"),
(73.66,77.10,"เพราะกูดีลตรงกับโบรกเกอร์ ไม่ผ่านเอเย่นต์ ไม่ผ่านคนกลาง"),
(77.10,80.26,"ไม่กักเงินมึง มึงดูตัวเลขมึงตัดสินใจเอง"),
(80.26,82.46,"แต่จำไว้ เงินทุกล็อตที่มึงกด"),
(82.46,85.12,"มันควรเป็นของมึง ไม่ใช่ของคนอื่น"),
]

def shot_at(t):
    for s in census["p1_shots"]:
        if s["t0"] <= t < s["t1"] or (t == census["source"]["duration_s"] and s["id"] == len(census["p1_shots"])):
            return s
    return census["p1_shots"][-1]

CTA_START = 64.40  # per CTO review 2: cta for every line from here on

def classify(t0, t1):
    """MECHANICAL per CTO review 2 (2026-09-23 22:45), not judgement:
    hook = shot 1 (cold open); cta = every line from 64.40s on; otherwise
    the avatar_mode of the P1 shot covering the line's MIDPOINT decides:
    composite -> show, full -> verdict."""
    if t0 < 1.867:
        return "hook"
    if t0 >= CTA_START:
        return "cta"
    mid_shot = shot_at((t0 + t1) / 2)
    return "show" if mid_shot["avatar_mode"] == "composite" else "verdict"

def entry_type(t0, t1):
    """MECHANICAL per CTO review 2: shrink if a P2 avatar_shrink starts
    inside [t0,t1); else cut if a P1 hard-cut boundary falls at or inside
    [t0,t1); else '-'."""
    for e in census["p2_focus_events"]:
        if e["type"] == "avatar_shrink" and e["t0"] is not None and t0 <= e["t0"] < t1:
            return "shrink"
    for s in census["p1_shots"]:
        if s["entry"] == "cut" and (abs(s["t0"] - t0) < 0.05 or t0 < s["t0"] < t1):
            return "cut"
    return "-"

# An event with a real t0 belongs to exactly one line -- whichever line's
# span contains it. Computed once so a nearby-fallback on an adjacent line
# can never re-claim an event that already has a proper home (this is what
# CTO review 2 meant by "attached to the wrong line": the 51.27 avatar_shrink
# was showing on both 49.34-51.10 AND its real home 51.10-52.26 before this
# fix).
_CLAIMED_EVENT_IDS = set()
for _e in census["p2_focus_events"]:
    if _e["t0"] is not None:
        for _t0, _t1, _ in LINES:
            if _t0 <= _e["t0"] < _t1:
                _CLAIMED_EVENT_IDS.add(id(_e))
                break

def focus_event_near(t0, t1):
    """An event whose own t0 falls inside this line's span always wins.
    Only if none does, fall back to the nearest event within 0.3s outside
    the span -- and only among events with no proper home elsewhere, so an
    event already claimed by its real line never duplicates onto a neighbor."""
    inside = [e for e in census["p2_focus_events"] if e["t0"] is not None and t0 <= e["t0"] < t1]
    if inside:
        e = inside[0]
        return e["type"], e.get("target", "-"), e.get("spoken_word") or "-"
    for e in census["p2_focus_events"]:
        if id(e) in _CLAIMED_EVENT_IDS:
            continue
        if e["t0"] is not None and t0 - 0.3 <= e["t0"] <= t1 + 0.3:
            return e["type"], e.get("target", "-"), e.get("spoken_word") or "-"
    return "-", "-", "-"

def sfx_near(t0, t1):
    hits = [x for x in census["p4_sfx"] if t0 - 0.3 <= x["t"] <= t1 + 0.3]
    if not hits:
        return "-"
    return ";".join(f"{x['rough_class']}@{x['t']:.2f}" for x in hits)

print("t0\tt1\ttext\tclass\tentry_type\tfocus_device\ttarget\thighlighted_word\tsfx")
for t0, t1, text in LINES:
    cls = classify(t0, t1)
    entry = entry_type(t0, t1)
    focus, target, hlword = focus_event_near(t0, t1)
    sfx = sfx_near(t0, t1)
    print(f"{t0:.2f}\t{t1:.2f}\t{text}\t{cls}\t{entry}\t{focus}\t{target}\t{hlword}\t{sfx}")
