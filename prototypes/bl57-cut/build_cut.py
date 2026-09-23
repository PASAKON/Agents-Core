#!/usr/bin/env python3
"""Generate EP57 index.html body content (plates + script section) from the beat table."""
import json

CANVAS_W, CANVAS_H = 1080, 1920

# ---- beat table -----------------------------------------------------------
# mode: FF (avatar full-frame, real lipsync) / COMP (avatar composite over evidence)
#       EVID (evidence still full-frame, no avatar) / KIN (kinetic text, no footage)
#       CHECK (graphic checklist card, handled separately)
BEATS = [
    # tag, t0, t1, mode, extra
    ("HOOK-1", 0.18, 2.64, "COMP", dict(img="real/wikifx-profile-score.png", box=None,
        cap="ใครใช้โบรกนี้อยู่ รีบเข้าเว็บไปเช็กด่วนเลย", avatar_src="lip", media0=0.18, shift=0)),
    ("HOOK-2", 3.08, 5.54, "FF", dict(cap="ตอนนี้แม่งปิดเว็บ เข้าไม่ได้แล้ว", avatar_src="lip", media0=3.08)),
    ("HOOK-3", 5.54, 7.38, "COMP", dict(img="real/xxlmarkets-direct-visit-error.png",
        box=(100,490,900,410), cap="นี่คือหลักฐานตอนที่กูพยายามเข้าเว็บ", avatar_src="lip", media0=5.54, shift=100)),
    ("HOOK-4", 7.82, 10.86, "COMP", dict(img="third-party/wikifx-xxlmarkets-review.jpg",
        box=(100,260,870,140), native_h=1350, credit="ขอบคุณภาพจาก WikiFX",
        cap="โบรกตัวนี้ชื่อ XXLMARKETS มึงดูภาพเอาเอง", avatar_src="lip", media0=7.82, shift=0)),
    ("PATTERN-1", 11.4, 14.97, "COMP", dict(img="real/wikifx-profile-website-inaccessible.png",
        box=(140,900,880,120), cap="เป็นโบรกฟอเร็กซ์ ที่ WikiFX บอกว่าเปิดที่อังกฤษตั้งแต่ปีสองพันยี่สิบเอ็ด",
        avatar_src="lip", media0=11.4, shift=220)),
    ("PATTERN-1b", 14.97, 17.86, "EVID", dict(img="real/wikifx-profile-website-inaccessible.png",
        box=(140,900,880,120), cap="ให้เทรดทั้งค่าเงิน หุ้น และสินค้า")),
    ("PATTERN-2", 18.48, 22.42, "EVID", dict(img="real/xxlmarkets-direct-visit-error.png",
        box=(100,490,900,410), cap="กูลองพิมพ์ชื่อเว็บนี้ใส่เบราว์เซอร์ตรงๆ หน้าเว็บขึ้นว่าเข้าไม่ได้")),
    ("PATTERN-3", 22.8, 27.78, "EVID", dict(img="real/xxlmarkets-www-visit-error.png",
        box=(100,490,900,410), cap="ลองอีกทาง ใส่ www นำหน้าบ้าง ใส่ https ตรงๆบ้าง")),
    ("PATTERN-4", 28.26, 30.78, "EVID", dict(img="real/xxlmarkets-www-visit-error.png",
        box=(100,490,900,410), cap="ผลเหมือนเดิมทุกครั้ง เข้าไม่ได้")),
    ("CONTEXT-1", 31.3, 35.44, "KIN", dict(lines=[
        ("bl-lg", "กูไม่เชื่อว่าแค่เว็บล่มเฉยๆ"), ("bl-md", 'เลยลอง<span class="y">เช็กเจ้าของชื่อเว็บ</span>นี้')])),
    ("CONTEXT-2", 36.12, 38.86, "KIN", dict(lines=[
        ("bl-md", "เข้าเว็บเช็กชื่อเว็บฟรีๆ"), ("bl-md", "พิมพ์ชื่อเว็บนี้ลงไป")])),
    ("CONTEXT-3", 39.66, 43.16, "EVID", dict(img="real/whois-no-match.png",
        box=(195,800,890,170), cap="เจอเลย ไม่มีใครเป็นเจ้าของชื่อเว็บนี้แล้วตอนนี้")),
    ("CONTEXT-4", 43.9, 47.72, "EVID", dict(img="real/whois-no-match.png",
        box=(195,800,890,170), cap="แต่เจอประวัติว่าเคยมีเจ้าของ ย้อนไปถึงปีสองพันยี่สิบสอง")),
    ("CONTEXT-5", 48.5, 54.22, "EVID", dict(img="real/whois-domain-history.jpg",
        native_w=1374, native_h=868, box=(160,755,690,100),
        cap="หน้าเดียวกันนี้มีตัวนับให้ดูชัดๆอีกด้วย สี่ครั้งตั้งแต่สองพันยี่สิบสองถึงสองพันยี่สิบหก")),
    ("MAIN-1", 54.84, 58.3, "KIN", dict(broll="broll/S14.mp4", lines=[
        ("bl-md", 'กูเลยลองไปดูที่<span class="y">WikiFX</span>'), ("bl-md", "เว็บที่เช็กโบรกทั่วโลก")])),
    ("MAIN-2", 58.3, 61.84, "EVID", dict(img="real/wikifx-profile-website-inaccessible.png",
        box=(140,900,880,120), cap="WikiFX เขียนไว้เองเหมือนกันว่าเว็บนี้เข้าไม่ได้ตามปกติ")),
    ("MAIN-3", 62.32, 65.44, "KIN", dict(lines=[
        ("bl-md", "แปลว่าไม่ใช่กูคนเดียวที่เข้าไม่ได้"), ("bl-md", '<span class="y">WikiFX</span>ก็เจอเหมือนกัน')])),
    ("MAIN-4", 66.12, 68.32, "KIN", dict(lines=[("bl-lg", "เช็กต่อว่ามีใบอนุญาต<br>ซื้อขายฟอเร็กซ์ไหม")])),
    ("MAIN-5", 69.04, 70.88, "COMP", dict(img="real/wikifx-profile-no-license.png",
        box=(130,800,790,370), cap="ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์เลย", avatar_src="lip", media0=69.04, shift=370)),
    ("MAIN-6", 71.44, 73.08, "FF", dict(cap="เช็กเรื่องหน่วยงานกำกับดูแลต่อ", avatar_src="lip", media0=71.44)),
    ("MAIN-7", 73.32, 76.06, "COMP", dict(img="real/wikifx-profile-no-regulation.png",
        box=(130,20,900,400), cap="เจอคำเตือนว่ายังไม่มีการกำกับดูแลที่ถูกต้องจริงๆ", avatar_src="lip", media0=73.32, shift=0)),
    ("MAIN-8", 76.36, 79.92, "COMP", dict(img="real/wikifx-profile-score.png",
        box=(0,780,660,270), cap="คะแนนความน่าเชื่อถือที่ WikiFX ให้ อยู่ที่หนึ่งจุดเก้าเก้าจากสิบ", avatar_src="lip", media0=76.36, shift=250)),
    ("MAIN-9", 80.26, 83.08, "COMP", dict(img="real/wikifx-profile-score.png",
        box=(695,455,385,160), cap="จดทะเบียนที่สหราชอาณาจักร เปิดมาแค่สองถึงห้าปี", avatar_src="lip", media0=80.26, shift=0)),
    ("MAIN-10", 83.4, 86.58, "EVID", dict(img="real/wikifx-profile-warning-banner.png",
        box=(320,440,750,100), cap="แล้วเจอคำเตือนอีกอัน ใบอนุญาตกำลังถูกตั้งข้อสงสัย")),
    ("MAIN-11", 86.84, 88.86, "EVID", dict(img="real/wikifx-profile-warning-banner.png",
        box=(320,440,750,100), cap="กลุ่มธุรกิจก็ถูกจัดว่าน่าสงสัยเหมือนกัน")),
    ("MAIN-12", 89.32, 93.24, "EVID", dict(img="real/fca-register-search-spinner.jpg",
        native_w=1374, native_h=868, box=(0,0,1374,500),
        cap="กูลองเช็กหน่วยงานการเงินของอังกฤษเองด้วย แต่หน้าเว็บโหลดผลไม่ขึ้นเลย")),
    ("MAIN-13", 93.64, 97.2, "KIN", dict(broll="broll/S26.mp4", lines=[
        ("bl-md", "กูไม่ได้บอกว่าเจ้านี้โกงแน่นอน"), ("bl-md", "กูแค่พาไปดูของจริงที่เช็กเจอ")])),
    ("CURIOSITY-1", 97.64, 100.16, "EVID", dict(img="third-party/wikifx-xxlmarkets-review.jpg",
        native_h=1350, box=(100,260,870,140), credit="ขอบคุณภาพจาก WikiFX",
        cap="นี่คือการ์ดที่ WikiFX เขาสรุปเรื่องนี้ไว้เองเลย")),
    ("CURIOSITY-2", 100.6, 104.28, "EVID", dict(img="third-party/wikifx-xxlmarkets-review.jpg",
        native_h=1350, box=(35,605,700,290), credit="ขอบคุณภาพจาก WikiFX",
        cap="คะแนนย่อยแทบทุกด้านก็แย่เหมือนกัน ทั้งกำกับดูแลและความเสี่ยง")),
    ("CURIOSITY-3", 104.74, 108.24, "KIN", dict(lines=[
        ("bl-md", "WikiFX เขียนไว้ด้วยว่า"), ("bl-md", "หน่วยงานการเงินของอังกฤษ"), ("bl-md", "ไม่พบข้อมูลเจ้านี้เหมือนกัน")])),
    ("CURIOSITY-4", 108.24, 114.22, "KIN", dict(lines=[
        ("bl-lg", "อันนี้ไม่ใช่กูพูดเอง"), ("bl-md", '<span class="y">WikiFX</span>เขียนไว้ มึงไปอ่านเองได้')])),
    ("CURIOSITY-5", 114.22, 117.74, "KIN", dict(broll="broll/S31.mp4", lines=[
        ("bl-lg", "โบรกที่ยังไหวอยู่จริง"), ("bl-md", "จะไม่ปล่อยให้เว็บหายไปเงียบๆแบบนี้")])),
    ("SUMMARY-1", 118.2, 119.32, "KIN", dict(lines=[("bl-xl n", "สรุปแบบไม่โลกสวย")])),
    ("SUMMARY-2", 119.76, 125.02, "KIN", dict(lines=[
        ("bl-lg n", "เว็บหาย"), ("bl-lg n", "ไม่มีใบอนุญาต"), ("bl-lg n", "ไม่มีหน่วยงานคุ้มครอง"),
        ("bl-sm", "สามอย่างนี้ไม่ใช่เรื่องบังเอิญ")])),
    ("SUMMARY-3", 125.4, 128.96, "KIN", dict(lines=[
        ("bl-md", "ก่อนฝากเงินโบรกไหนก็ตาม"), ("bl-md", 'เช็ก<span class="y">3 อย่าง</span>แบบที่กูทำให้ดูวันนี้')])),
    ("SUMMARY-7", 141.48, 145.64, "FF", dict(cap="กูไม่ได้แนะนำให้ใช้หรือเลิกใช้เจ้าไหน กูแค่ชี้วิธีเช็กให้เป็น", avatar_src="lip", media0=141.48)),
    ("SUMMARY-8", 146.08, 150.5, "FF", dict(cap='คอมเมนต์คำว่า <span class="y">เช็กเว็บโบรก</span> ถ้ามึงอยากได้ขั้นตอนเช็กเว็บและใบอนุญาตเอง', avatar_src="lip", media0=146.08)),
    ("SUMMARY-9", 150.8, 152.64, "FF", dict(cap="อย่าปล่อยให้เว็บหายไปพร้อมเงินมึง", avatar_src="lip", media0=150.8)),
]

# SUMMARY-4/5/6 handled as one CHECK card, not in BEATS above
CHECK_ITEMS = [
    dict(t0=129.38, t1=132.88, x="เข้าเว็บโบรกตรงๆตอนนี้เลย ยังเปิดอยู่จริงไหม"),
    dict(t0=133.52, t1=137.26, x="เช็กชื่อเว็บที่เว็บตรวจสอบฟรีๆ ยังมีเจ้าของอยู่ไหม"),
    dict(t0=137.86, t1=141.02, x="เข้า WikiFX เช็กว่ามีใบอนุญาตจริงไหม"),
]

TOTAL_DUR = 153.0

import sys
WINDOW_START = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
WINDOW_END = float(sys.argv[2]) if len(sys.argv) > 2 else TOTAL_DUR

def lip_offset(src):
    return {"lip_a": 0.0, "lip_b": 68.30, "lip_c": 137.16}[src]

# real measured durations of the normalized/matted lipsync parts (ffprobe) -
# never let a beat's avatar overlay run past the source's actual last frame.
LIP_DUR = {"lip_a": 14.90, "lip_b": 14.65, "lip_c": 15.35}

def pick_lip(t0):
    if t0 < 15.5: return "lip_a"
    if t0 < 84: return "lip_b"
    return "lip_c"

# ---- hold-until-next: no beat may go empty before the next one starts -----
# CTO review 2026-09-24: 35 empty stretches (16.8s, 11% of the episode) where
# a plate/block ended at its own line's t1 but the next line's TTS pause ran
# past it. The reference never goes empty - a plate holds until the next cut.
# Build one merged, absolute-time timeline (BEATS + the CHECK block as one
# pseudo-entry) and give every entry an EXT_END = the next entry's own start
# (or TOTAL_DUR for the last one), so duration/hold times extend to cover
# the pause instead of stopping at the spoken line's own end.
_tl_markers = [(t0, tag) for tag, t0, t1, mode, ex in BEATS]
_tl_markers.append((CHECK_ITEMS[0]["t0"], "__CHECK__"))
_tl_markers.sort(key=lambda m: m[0])
EXT_END = {}
for i, (t0, tag) in enumerate(_tl_markers):
    nxt = _tl_markers[i + 1][0] if i + 1 < len(_tl_markers) else TOTAL_DUR
    EXT_END[tag] = nxt

# ---- image sizing: native px -> canvas placement -------------------------
def img_placement(extra):
    """Returns (disp_w, disp_h, top, left, scale) for the plate at native res."""
    nw = extra.get("native_w", 1080)
    nh = extra.get("native_h", 1920)
    if nw == 1080 and nh == 1920:
        return 1080, 1920, 0, 0, 1.0
    if nw == 1080:  # portrait but shorter than canvas (e.g. 1080x1350)
        top = 0  # top-aligned; avatar/kit dark fills the rest below
        return 1080, nh, top, 0, 1.0
    # landscape source (e.g. 1374x868): scale to canvas width, center vertically
    scale = 1080 / nw
    disp_h = round(nh * scale)
    top = round((1920 - disp_h) / 2)
    return 1080, disp_h, top, 0, scale

def box_to_canvas(box, place):
    """box=(x,y,w,h) in native px -> (x,y,w,h) in canvas px, using placement."""
    if box is None:
        return None
    dw, dh, top, left, scale = place
    x, y, w, h = box
    return (left + x * scale, top + y * scale, w * scale, h * scale)

def pct(v, dim):
    return round(v / dim * 1000) / 10  # 1 decimal %

# ---- HTML emission ---------------------------------------------------------
plates = []   # static <img>/<video> tags
script_lines = []  # JS lines appended after the generator defs
cap_entries = []   # (t0, t1, text, kind) kind: rail|chip-comp|chip-ff
track_ctr = [1]

def new_track():
    track_ctr[0] += 1
    return track_ctr[0]

PLATE_TRACK = 0
AVATAR_TRACK = 1

def esc(s):
    return s.replace('"', "&quot;")

for tag, abs_t0, abs_t1, mode, ex in BEATS:
    if abs_t0 < WINDOW_START - 0.001 or abs_t0 >= WINDOW_END - 0.001:
        continue
    t0 = round(abs_t0 - WINDOW_START, 3)
    abs_t1_ext = min(EXT_END[tag], WINDOW_END)  # hold until the next beat starts
    t1 = round(abs_t1_ext - WINDOW_START, 3)
    dur = round(t1 - t0, 3)
    safe_id = tag.lower().replace("-", "")
    if mode == "FF":
        lipname = pick_lip(abs_t0)
        media_start = round(abs_t0 - lip_offset(lipname), 3)
        clip_dur = min(dur, round(LIP_DUR[lipname] - media_start, 3))
        plates.append(
            f'<video class="clip" id="v_{safe_id}" src="media/{lipname}.mp4" muted playsinline '
            f'data-start="{t0}" data-duration="{clip_dur}" data-media-start="{media_start}" '
            f'data-track-index="{PLATE_TRACK}"></video>')
        cap_entries.append((t0, t1, ex["cap"], "chip-ff", None))

    elif mode == "COMP":
        place = img_placement(ex)
        dw, dh, top, left, scale = place
        img = ex["img"]
        shift = ex.get("shift", 0)
        plate_dur = dur
        avatar_dur = dur
        if "avatar_until" in ex:
            avatar_dur = round(ex["avatar_until"] - abs_t0, 3)
        lipname = pick_lip(abs_t0)
        media_start0 = round(abs_t0 - lip_offset(lipname), 3)
        avatar_dur = min(avatar_dur, round(LIP_DUR[lipname] - media_start0, 3))
        style = f'top:{top - shift}px;left:{left}px;right:auto;bottom:auto;width:{dw}px;height:{dh}px;transform:none'
        plates.append(
            f'<img class="clip" id="v_{safe_id}" src="media/{img}" '
            f'style="{style}" data-start="{t0}" data-duration="{plate_dur}" '
            f'data-track-index="{PLATE_TRACK}">')
        media_start = round(abs_t0 - lip_offset(lipname), 3)
        plates.append(
            f'<video class="avatar-comp" id="av_{safe_id}" src="media/matte/{lipname}-matte.webm" '
            f'muted playsinline data-start="{t0}" data-duration="{avatar_dur}" '
            f'data-media-start="{media_start}" data-track-index="{AVATAR_TRACK}"></video>')
        box_c = box_to_canvas(ex.get("box"), place)
        if box_c:
            bx, by, bw, bh = box_c
            by -= shift
            box_bottom = by + bh
            # caption must clear BOTH the evidence box and the avatar (top 845px) -
            # prefer just above the box; only below it if that gap is big enough;
            # drop the caption rather than write it over the evidence (skill precedent).
            cap_y = None
            if by - 150 >= 150:
                cap_y = round(by - 150)
            elif 845 - (box_bottom + 15) >= 100:
                cap_y = round(box_bottom + 15)
            if cap_y is not None:
                cap_entries.append((t0, t1, ex["cap"], "chip-comp", cap_y))
            script_lines.append(
                f'spotlight("sp_{safe_id}", {t0+0.15}, {t1}, {round(bx)}, {round(by)}, {round(bw)}, {round(bh)});')
        else:
            cap_entries.append((t0, t1, ex["cap"], "chip-comp", 700))
        if ex.get("credit"):
            script_lines.append(f'credit("cr_{safe_id}", {t0+0.1}, {t1}, "{esc(ex["credit"])}");')

    elif mode == "EVID":
        place = img_placement(ex)
        dw, dh, top, left, scale = place
        img = ex["img"]
        style = f'top:{top}px;left:{left}px;right:auto;bottom:auto;width:{dw}px;height:{dh}px'
        plates.append(
            f'<img class="clip" id="v_{safe_id}" src="media/{img}" '
            f'style="{style}" data-start="{t0}" data-duration="{dur}" '
            f'data-track-index="{PLATE_TRACK}">')
        box_c = box_to_canvas(ex.get("box"), place)
        if box_c:
            bx, by, bw, bh = box_c
            script_lines.append(
                f'spotlight("sp_{safe_id}", {t0+0.25}, {t1}, {round(bx)}, {round(by)}, {round(bw)}, {round(bh)});')
        if ex.get("credit"):
            script_lines.append(f'credit("cr_{safe_id}", {t0+0.1}, {t1}, "{esc(ex["credit"])}");')
        cap_entries.append((t0, t1, ex["cap"], "rail", None))

    elif mode == "KIN":
        if ex.get("broll"):
            plates.append(
                f'<video class="clip plate-darkened" id="v_{safe_id}" src="media/{ex["broll"]}" muted playsinline '
                f'data-start="{t0}" data-duration="{dur}" data-media-start="0" '
                f'data-track-index="{PLATE_TRACK}"></video>')
        lines_js = ", ".join(
            '{c:"%s", h:%s}' % (c, json.dumps(h, ensure_ascii=False)) for c, h in ex["lines"]
        )
        script_lines.append(f'kinetic(760, {t0+0.05}, {t1}, [{lines_js}], 0);')

print(f"plates: {len(plates)}  script_lines: {len(script_lines)}  captions: {len(cap_entries)}")

# ---- CHECK block (SUMMARY-4/5/6) — may itself be split across ≤9s windows.
# CTO 2026-09-24 03:00: windows must stay <=9s/270 frames, but the block spans
# 11.6s. An item/the block already due before this window starts must appear
# ALREADY REVEALED, not re-animate (same continuation problem as the #bug
# logo re-entering at a seam).
#
# First attempt gave GSAP a negative "at"/"t", reasoning a tween positioned
# before t=0 would already be resolved by the time playback reaches 0. WRONG,
# verified by reading the actual rendered frames: a GSAP tween scheduled at a
# NEGATIVE timeline position never fires during forward playback from t=0 - it
# is not "pre-resolved", it is skipped outright, so the whole block stayed at
# its CSS opacity:0 for the window's entire 3.1s (task-501f1d89, window w21,
# t=138.5-141.25 read back as fully empty). GSAP tl.set(...) AT t=0 (not
# negative) is what actually worked for the #bug logo fix above - so here too:
# still call check() with harmless real numbers (nothing renders wrong even if
# its own tweens fire, because the block only reaches t=0 already time-shifted
# past them), then override with plain DOM writes (not GSAP, so nothing later
# can skip or undo them) forcing anything already-due to its resting state.
# check_call is always emitted FIRST in assemble.py, so its block() call is
# always the page's first "b" counter value - id "b1" is reliable to target.
CHECK_ABS_START = CHECK_ITEMS[0]["t0"]
_ci = [it for it in CHECK_ITEMS if it["t0"] < WINDOW_END - 0.001]
check_override_js = []
if _ci and CHECK_ABS_START < WINDOW_END - 0.001 and EXT_END["__CHECK__"] > WINDOW_START + 0.001:
    is_continuation = WINDOW_START > CHECK_ABS_START + 0.001
    check_items_js = ", ".join(
        '{x:%s, t:%s}' % (json.dumps(it["x"], ensure_ascii=False),
                           0 if it["t0"] < WINDOW_START - 0.001 else round(it["t0"] - WINDOW_START, 3))
        for it in _ci
    )
    _check_at = 0 if is_continuation else round(CHECK_ABS_START - WINDOW_START, 3)
    _check_end = round(min(EXT_END["__CHECK__"], WINDOW_END) - WINDOW_START, 3)
    check_call = (f'check(560, {_check_at}, {_check_end}, '
                  f'\'เช็ก 3 อย่างก่อนฝากเงิน\', [{check_items_js}]);')
    if is_continuation:
        check_override_js.append(
            'document.getElementById("b1").style.opacity = 1;'
            ' document.getElementById("b1t").style.clipPath = "inset(0 0% 0 0)";')
        for idx, it in enumerate(_ci):
            if it["t0"] < WINDOW_START - 0.001:
                check_override_js.append(
                    f'var _r{idx} = document.getElementById("b1r{idx}"); '
                    f'if (_r{idx}) {{ _r{idx}.style.opacity = 1; _r{idx}.style.transform = "translateX(0px)"; }}')
else:
    check_call = ""

# ---- captions ---------------------------------------------------------------
caps_js = []
for t0, t1, text, kind, y in cap_entries:
    yarg = "null" if y is None else str(y)
    caps_js.append(f'addCap({t0}, {t1}, {json.dumps(text, ensure_ascii=False)}, "{kind}", {yarg});')

# ---- write output pieces to disk for inspection before splicing ------------
suffix = "" if (WINDOW_START == 0.0 and WINDOW_END == TOTAL_DUR) else f"-{WINDOW_START:g}-{WINDOW_END:g}"
OUT = f"/Users/gob/MoonieXHQ/Work/task-501f1d89/tmp/cut_pieces{suffix}.json"
with open(OUT, "w") as f:
    json.dump({
        "plates": plates,
        "script_lines": script_lines,
        "check_call": check_call,
        "check_override_js": check_override_js,
        "caps_js": caps_js,
        # CTO 2026-09-24: each window's duration must land EXACTLY on a 30fps frame
        # boundary from the renderer's own point of view, or it ceils up an extra
        # frame per window and 24 windows' worth of that drifts audio ~300ms out
        # of lipsync. Float rounding alone still left values like 215.00001 (still
        # ceils to 216) - bias just under the target frame count to be safe.
        "total_dur": round((round((WINDOW_END - WINDOW_START) * 30) / 30) - 0.0003, 6),
    }, f, ensure_ascii=False, indent=2)
print("wrote", OUT)
