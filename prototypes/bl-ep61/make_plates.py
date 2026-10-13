#!/usr/bin/env python3
"""BL EP61: the derived evidence plates (task-03f18aab). Shape from prototypes/bl-ep60/make_plates.py.

Every Tickmill still (media/real/tm-*.png, the 1080x1920 captures of Tickmill's own public pages, 13 Oct 2026, buttons
already pixelated) is re-drawn on its own 1080x1920 canvas: a crop of the REAL capture, scaled, on a white card (the pages
are dark, and bl_merge refuses a flat dark frame). Nothing is redrawn or retouched; each plate is a crop of a file in
media/real/, scaled. DERIVED_MANIFEST.json says which crop of which still.

Compliance (CEO 2026-10-13, STATUS.md): the model photo of tm-header / tm-classic-para and the TradingView RAW card of
tm-header are never inside a crop. tm-header is used only for its header strip (y 62-132, x 0-250: logo) and for the
heading row of the first two cards (y 1098-1140, x 15-715; the TradingView card starts at x 724). tm-classic-para is used
from y 540 down; its photo ends at y 252. The censored (pixelated) buttons are never pulled back into a crop.

The calc cards (MAIN-4/5/6/9) and the checklist cards (SUMMARY-2/3/4) are the channel's OWN drawings (no source chip): every
figure on them equals prototypes/bl61-script/cost_check.py, and each says it is the channel's own arithmetic.

Run `python3 prototypes/bl-ep61/make_plates.py` (needs PIL). Output: <work>/media/real/d-*.png, DERIVED_MANIFEST.json and
plates.json beside this file (each plate's box in canvas px for make_beats.py).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
WORK = Path("/opt/MoonieXHQ/Work/bl-ep61")
REAL = WORK / "media/real"
TABLE = HERE / "take_table.json"

CANVAS_W, CANVAS_H = 1080, 1920
SAFE_L, SAFE_R = 54, 1026
ARM_A_TOP = 560                      # tools/bl_checker.py ARM_A_EVIDENCE_TOP: arm A darkens everything above this
PILL_HALF, HEAD_GAP, EVID_GAP, BORDER = 82, 24, 12, 10
PAD = 8                              # px between the text and the spotlight rectangle
EVID_PILL_TOP = 1300 - PILL_HALF     # an EVID caption pill (two lines) starts here

# until take_table.json exists: EP59/EP60's measurement (same avatar, same framing)
PROVISIONAL = {"lip_a": 903.04, "lip_b": 968.56, "lip_c": 985.36}

FONT = "/root/.fonts/NotoSansThai.ttf"


def zone(take: str) -> tuple[float, float]:
    """(top, bottom) of the canvas band a COMP spotlight may occupy on `take`, arm A's (the narrower)."""
    head_top = json.loads(TABLE.read_text())["takes"][take]["head_top"] if TABLE.exists() else PROVISIONAL[take]
    cy = math.floor(head_top - HEAD_GAP - PILL_HALF)
    return float(ARM_A_TOP), cy - PILL_HALF - EVID_GAP - BORDER


def font(px: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(FONT, px)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


class Plate:
    """One 1080x1920 canvas. paste() draws a crop of a real still; the mapper it returns turns still px into canvas px."""

    def __init__(self, name: str, bg=(255, 255, 255)):
        self.name = name
        self.img = Image.new("RGB", (CANVAS_W, CANVAS_H), bg)
        self.parts: list[dict] = []

    def paste(self, src: str, rect, z: float, at):
        s = Image.open(REAL / f"{src}.png").convert("RGB")
        x0, y0, x1, y1 = rect
        c = s.crop(rect).resize((round((x1 - x0) * z), round((y1 - y0) * z)), Image.LANCZOS)
        ax, ay = round(at[0]), round(at[1])
        self.img.paste(c, (ax, ay))
        self.parts.append({"src": f"real/{src}.png", "crop": list(rect), "zoom": z, "at": [ax, ay]})
        return lambda x, y, ww, hh: [ax + (x - x0) * z, ay + (y - y0) * z, ww * z, hh * z]

    def save(self):
        self.img.save(REAL / f"d-{self.name}.png", optimize=True)


def box_out(m, rect, pad_x=PAD, pad_y=PAD, clamp=True):
    x, y, w, h = m(*rect)
    x, y, w, h = x - pad_x, y - pad_y, w + 2 * pad_x, h + 2 * pad_y
    if clamp:
        x2 = min(x + w, SAFE_R)
        x = max(x, SAFE_L)
        w = x2 - x
    return [round(x), round(y), round(w), round(h)]


PLATES: dict[str, dict] = {}


def done(p: Plate, box, take=None, note="", credit=True, text_px=None, own=False):
    p.save()
    entry = {"file": f"real/d-{p.name}.png", "box": box, "take": take, "note": note, "credit": credit, "parts": p.parts}
    if own:
        entry["own_graphic"] = True
    if text_px is not None:
        entry["text_px"] = round(text_px, 1)
    if box and take:
        top, bottom = zone(take)
        entry["zone"] = [top, bottom]
        entry["fits"] = box[1] >= top - 0.5 and box[1] + box[3] <= bottom + 0.5
    PLATES[p.name] = entry


def card(name, src, text_rect, xspan, z, cy, rows, note="", credit=True, take=None, box_rect=None):
    """A dark-page crop laid as a card on a white plate, text rectangle centred on y `cy` (cy None = the middle of the
    COMP zone). A COMP plate must end where the caption pill begins: the crop is clipped to zone bottom + 6."""
    x, y, w, h = text_rect
    if take:
        top, bottom = zone(take)
        if cy is None:
            cy = (top + bottom) / 2
        z = min(z, (bottom - top - 2 * PAD - 2) / h)
    x0, x1 = xspan
    r0, r1 = rows
    z = min(z, (SAFE_R - SAFE_L) / (x1 - x0))
    if take:
        limit = y + h / 2 + (zone(take)[1] + 6 - cy) / z
        r1 = min(r1, math.floor(limit))
        r0 = max(r0, math.ceil(y + h / 2 - (cy - zone(take)[0]) / z))
    cw, ch = round((x1 - x0) * z), round((r1 - r0) * z)
    p = Plate(name, (255, 255, 255))
    at = ((CANVAS_W - cw) / 2, cy - (y + h / 2 - r0) * z)
    mb = p.paste(src, (x0, r0, x1, r1), z, at)
    done(p, box_out(mb, box_rect or text_rect), take, note, credit, text_px=None)
    PLATES[name]["z"] = round(z, 3)


def rows_stack(name, src, items, z, cy, take=None, note="", gap=10, box_idx=None):
    """Several small crops of ONE still stacked as rows on a white plate (a line of body text split at a word: the page's
    own order, each row large enough to read). items = [(x0, y0, x1, y1), ...]; the spotlight spans them all."""
    hs = [round((r[3] - r[1]) * z) for r in items]
    total = sum(hs) + gap * (len(items) - 1)
    p = Plate(name, (255, 255, 255))
    y = cy - total / 2
    boxes = []
    for r, h in zip(items, hs):
        w = (r[2] - r[0]) * z
        assert w <= SAFE_R - SAFE_L - 2 * PAD, (name, w)
        m = p.paste(src, r, z, ((CANVAS_W - w) / 2, y))
        boxes.append(m(r[0], r[1], r[2] - r[0], r[3] - r[1]))
        y += h + gap
    sel = [boxes[i] for i in box_idx] if box_idx is not None else boxes
    bx0 = min(b[0] for b in sel) - PAD
    by0 = min(b[1] for b in sel) - PAD
    bx1 = max(b[0] + b[2] for b in sel) + PAD
    by1 = max(b[1] + b[3] for b in sel) + PAD
    done(p, [round(bx0), round(by0), round(bx1 - bx0), round(by1 - by0)], take, note, True)
    PLATES[name]["z"] = z


def src_box(name, rect, pad_x=PAD, pad_y=PAD):
    """A spotlight box (canvas px) for a rectangle of the still the plate's first crop came from."""
    part = PLATES[name]["parts"][0]
    x0, y0 = part["crop"][0], part["crop"][1]
    z, (ax, ay) = part["zoom"], part["at"]
    x, y, w, h = rect
    return box_out(lambda a, b, c, d: [ax + (a - x0) * z, ay + (b - y0) * z, c * z, d * z], rect, pad_x, pad_y)




def page_bg(img: Image.Image, near) -> tuple[int, int, int]:
    patch = img.crop(near).convert("RGB")
    colours = patch.getcolors(maxcolors=patch.width * patch.height)
    return max(colours)[1]


def snap_rows(src: Image.Image, rows, down=40, up=60, gap_x=(60, 1020)):
    """Move the window's edges to the nearest rows that are one colour all the way across, so a crop never cuts a text line."""
    px = src.convert("RGB")

    def plain(r):
        ext = px.crop((gap_x[0], r, gap_x[1], r + 1)).getextrema()
        return all(e[1] - e[0] <= 12 for e in ext)
    r0, r1 = rows
    for r in range(r0, min(r0 + down, r1)):
        if plain(r):
            r0 = r
            break
    for r in range(r1, max(r1 - up, r0), -1):
        if plain(r):
            r1 = r
            break
    return r0, r1


def page(name, src, text_rect, z, cy, rows, take=None, note="", credit=True, zmax=1.4, xcrop=0, own=None, box_rect=None):
    """A WHITE-page crop (tm-classic-para / tm-raw-example) at zoom z, the text rectangle centred on y `cy` (a COMP's cy is
    the middle of its zone when None). Full-width crop from `xcrop`; rows = (r0, r1) of the still that may be drawn, clipped
    on a COMP plate to where the caption pill begins."""
    x, y, w, h = text_rect
    z = min(z, zmax)
    if take:
        top, bottom = zone(take)
        z = min(z, (bottom - top - 2 * PAD - 2) / h)
        if cy is None:
            cy = (top + bottom) / 2
    s = Image.open(REAL / f"{src}.png").convert("RGB")
    r0, r1 = rows
    if take:
        r1 = min(r1, math.floor(y + h / 2 + (zone(take)[1] + 6 - cy) / z))
        r0 = max(r0, math.ceil(y + h / 2 - (cy - zone(take)[0]) / z))
    r0, r1 = snap_rows(s, (r0, r1))
    p = Plate(name, (255, 255, 255))
    at_x = SAFE_L + PAD
    ay0 = cy + (r0 - (y + h / 2)) * z
    x1 = min(1080, math.ceil(xcrop + (CANVAS_W - at_x) / z))
    mb = p.paste(src, (xcrop, r0, x1, r1), z, (at_x, ay0))
    done(p, box_out(mb, box_rect or text_rect), take, note, credit)
    PLATES[name]["z"] = round(z, 3)
    PLATES[name]["rows"] = [r0, r1]
    return p, mb


# ── the channel's own drawings: calc cards, checklist cards, COMP strips ──────────────────────────────────────────────
INK = (20, 28, 48)
MUTED = (96, 104, 124)
RULE = (200, 205, 215)
CARD_BG = (246, 247, 250)


def T(d, xy, s, f, fill=INK, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def calc_card(d, left, top, width, kind, upto="all", compact=False):
    """One calc card (identical drawing for both): title, the spread row with its formula names, the commission row and the
    total. Ink on a light card, one weight scale, no green/red, no arrow. Returns {row: rect} in canvas px. `compact` drops
    the formula-name note and tightens the rows so two cards fit one EVID band (MAIN-9)."""
    if compact:
        y_rule1, y_spread, y_rule2, y_comm, y_rule3, y_total, h, fs = 62, 72, 128, 138, 190, 198, 276, (38, 30, 40, 50)
    else:
        y_rule1, y_spread, y_rule2, y_comm, y_rule3, y_total, h, fs = 82, 98, 192, 208, 266, 282, 372, (46, 34, 44, 58)
    full_h = h
    if upto == "spread":
        h = y_rule2 + 2
    d.rounded_rectangle((left, top, left + width, top + h), 24, fill=CARD_BG, outline=RULE, width=3)
    x0, x1 = left + 34, left + width - 34
    T(d, (x0, top + 12), "Classic" if kind == "classic" else "Raw", font(fs[0], "Bold"))
    T(d, (x1, top + 12 + (fs[0] - 27) // 2), "คำนวณเอง จากเลขบนหน้าเว็บ · 1 ล็อต", font(27, "Regular"), MUTED, "ra")
    spread = "1.6 × 1 × $10 = $16.00" if kind == "classic" else "0.0 × 1 × $10 = $0.00"
    comm = "$0.00" if kind == "classic" else "$3 × 2 ข้าง = $6.00"
    total = "$16.00" if kind == "classic" else "$6.00"
    d.line((x0, top + y_rule1, x1, top + y_rule1), fill=RULE, width=2)
    T(d, (x0, top + y_spread + 4), "สเปรด", font(fs[1], "Medium"), MUTED)
    T(d, (x1, top + y_spread), spread, font(fs[2], "Bold"), INK, "ra")
    if not compact:
        T(d, (x1, top + y_spread + 58), "สเปรด × ขนาด × ค่าพิป", font(24, "Regular"), MUTED, "ra")
    out = {"spread": (left + 14, top + y_rule1, width - 28, y_rule2 - y_rule1), "all": (left, top, width, h)}
    if upto == "spread":
        return out
    d.line((x0, top + y_rule2, x1, top + y_rule2), fill=RULE, width=2)
    T(d, (x0, top + y_comm + 4), "คอมมิชชัน", font(fs[1], "Medium"), MUTED)
    T(d, (x1, top + y_comm), comm, font(fs[2], "Bold"), INK, "ra")
    d.line((x0, top + y_rule3, x1, top + y_rule3), fill=INK, width=4)
    T(d, (x0, top + y_total + 8), "รวม", font(fs[2] - 4, "Bold"))
    T(d, (x1, top + y_total), total, font(fs[3], "ExtraBold"), INK, "ra")
    out.update({"comm": (left + 14, top + y_rule2, width - 28, y_rule3 - y_rule2),
                "total": (left + 14, top + y_rule3, width - 28, full_h - y_rule3 - 2)})
    return out


def own_plate(name, drawer, note, box=None, boxes=None, take=None):
    p = Plate(name, (255, 255, 255))
    d = ImageDraw.Draw(p.img)
    rects = drawer(d)
    p.parts.append({"src": None, "own_graphic": note})

    def tr(r):
        return [round(max(SAFE_L, r[0])), round(r[1]), round(min(SAFE_R, r[0] + r[2]) - max(SAFE_L, r[0])), round(r[3])]
    done(p, tr(rects[box]) if box else None, take, note, credit=False, own=True)
    if boxes:
        PLATES[name]["boxes"] = {k: tr(rects[k]) for k in boxes}
    return p


def centered(d, y, s, f, fill=INK):
    d.text((CANVAS_W / 2, y), s, font=f, fill=fill, anchor="ma")


def build():
    A, B, C = "lip_a", "lip_b", "lip_c"
    # ── COMP, lip_a (zone about 133 px) ──────────────────────────────────────────────────────────────────────
    card("raw-spread", "tm-raw", (172, 1383, 532, 50), (150, 740), 1.5, None, (1368, 1447), take=A,
         note="HOOK-2: Tickmill Raw card, table row `Spreads From 0.0 pips`")
    card("head-logo", "tm-header", (55, 78, 160, 36), (0, 250), 1.6, None, (62, 132), take=A,
         note="HOOK-3: Tickmill's page header, logo only (crop x 0-250, y 62-132: no photo, no TradingView card)")
    card("head-pair", "tm-header", (37, 1105, 533, 32), (15, 715), 1.35, None, (1098, 1142), take=A,
         note="HOOK-4: headings of the first two account cards, CLASSIC ACCOUNT and RAW ACCOUNT (crop x 15-715 stops short of the TradingView card at x 724)")
    card("formula-line", "tm-formula", (44, 868, 373, 24), (28, 470), 2.2, None, (862, 898), take=A,
         note="PATTERN-1: Tickmill FAQ formula `Trade Cost = Spread x Trade Size x Pip Value`")
    rows_stack("swaps-rows", "tm-swaps", [(40, 913, 488, 941), (488, 913, 806, 941)], 1.85, 626, A,
               "PATTERN-2: Tickmill FAQ `What are swaps?` answer, first sentence in two rows: swaps are overnight interest charges applied when you hold a position past 00:00 platform time")
    # ── COMP, lip_b (zone about 169 px): the white pages' big text ────────────────────────────────────────
    page("classic-para", "tm-classic-para", (0, 995, 1015, 125), 0.9, None, (990, 1130), B, zmax=0.9,
         note="MAIN-3: Tickmill Classic page: `... with variable spreads starting from 1.6 pips and no commissions.`")
    page("ex-commission", "tm-raw-example", (0, 930, 1055, 60), 0.9, None, (862, 996), B, zmax=0.9,
         note="MAIN-7: Raw page example: `... commission per side would be 3 USD and 6 USD`")
    page("ex-round", "tm-raw-example", (0, 930, 1055, 125), 0.9, None, (924, 1062), B, zmax=0.9,
         note="MAIN-8: Raw page example: `... would be 3 USD and 6 USD round turn (or the equivalent amount in the`")

    # ── COMP, lip_c (zone about 229 px): the channel's own words, no source chip ────────────────────────────
    def strip_recap(d):
        centered(d, 592, "เช็กลิสต์ 3 ข้อ", font(34, "Medium"), MUTED)
        centered(d, 650, "อ่านหน้าบัญชี  ·  บวกสเปรดกับคอมมิชชัน", font(40, "Bold"))
        centered(d, 710, "ถามเรื่องสว็อปเป็นข้อความ", font(40, "Bold"))
        return {"all": (60, 576, 960, 204)}
    own_plate("recap-strip", strip_recap, "SUMMARY-5: the three checks as a strip (the channel's own words)", box="all", take=C)

    def strip_cta(d):
        centered(d, 596, "คอมเมนต์", font(44, "Medium"), MUTED)
        centered(d, 662, "“เช็กลิสต์”", font(86, "ExtraBold"))
        return {"all": (60, 576, 960, 204)}
    own_plate("cta-strip", strip_cta, "SUMMARY-6: the CTA word (the channel's own words)", box="all", take=C)

    def strip_date(d):
        centered(d, 596, "ข้อมูลจากหน้าเว็บของ Tickmill", font(40, "Medium"), MUTED)
        centered(d, 662, "ณ 13 ต.ค. 2569", font(80, "ExtraBold"))
        return {"all": (60, 576, 960, 204)}
    own_plate("date-strip", strip_date, "SUMMARY-7: the date the figures were read (the channel's own words)", box="all", take=C)

    # ── EVID (band 570-1200; the pill sits at 1300) ──────────────────────────────────────────────────────────
    _, mb = page("raw-example", "tm-raw-example", (0, 798, 1055, 320), 0.9, 800, (792, 1130), None, zmax=0.9,
                 note="CONTEXT-1/2: Tickmill Raw page, the worked example paragraph (1 lot EURUSD, contract size 100,000 EUR)")
    PLATES["raw-example"]["boxes"] = {"lot": box_out(mb, (0, 798, 1055, 60)),
                                      "size": box_out(mb, (0, 863, 600, 60))}

    # MAIN-6: the Raw page's own `0.0 pips` line and the channel's own spread row for the Raw card under it
    p = Plate("raw-para-calc", (255, 255, 255))
    mb = p.paste("tm-raw-example", (0, 398, 1080, 462), 0.9, (SAFE_L + PAD, 640))
    d = ImageDraw.Draw(p.img)
    rects = calc_card(d, 84, 790, 912, "raw", upto="spread")
    done(p, box_out(mb, (0, 400, 945, 56)), None,
         "MAIN-6: Raw page line `fluctuating spreads starting from 0.0 pips.` and the channel's own spread row 0.0 x 1 x $10 = $0.00")
    PLATES["raw-para-calc"]["boxes"] = {"spread": [round(v) for v in rects["spread"]]}

    # CONTEXT-3: the logo and the date the figures were read
    p = Plate("logo-date", (255, 255, 255))
    mb = p.paste("tm-header", (0, 62, 250, 132), 2.4, ((CANVAS_W - 600) / 2, 640))
    d = ImageDraw.Draw(p.img)
    centered(d, 860, "ข้อมูลจากหน้าเว็บของ Tickmill", font(46, "Bold"))
    centered(d, 930, "ณ 13 ต.ค. 2569", font(58, "ExtraBold"))
    done(p, box_out(mb, (55, 78, 160, 36)), None, "CONTEXT-3: Tickmill logo (header crop) and the capture date, the channel's own words under it")

    # MAIN-1: the FAQ question and the formula line, big (the sentence between them is wider than any crop and is left out)
    rows_stack("formula-faq", "tm-formula", [(28, 780, 470, 815), (28, 864, 470, 894)], 2.1, 760, None,
               "MAIN-1: Tickmill FAQ `How do you calculate your transaction cost?` and the formula line `Trade Cost = Spread x Trade Size x Pip Value`",
               gap=40, box_idx=[1])

    # MAIN-2: the same two rows on top, the channel's own pip-value card under it
    p = Plate("formula-own", (255, 255, 255))
    zf = 2.1
    x_at = (CANVAS_W - 442 * zf) / 2
    p.paste("tm-formula", (28, 780, 470, 815), zf, (x_at, 590))
    p.paste("tm-formula", (28, 864, 470, 894), zf, (x_at, 590 + 73 + 30))
    d = ImageDraw.Draw(p.img)
    d.rounded_rectangle((84, 840, 996, 1090), 24, fill=CARD_BG, outline=RULE, width=3)
    T(d, (118, 856), "คำนวณเอง", font(42, "Bold"))
    T(d, (962, 866), "ไม่ได้อยู่ในหน้าเว็บ", font(28, "Regular"), MUTED, "ra")
    d.line((118, 918, 962, 918), fill=RULE, width=2)
    T(d, (118, 940), "1 ล็อต = 100,000 หน่วย", font(36, "Medium"), MUTED)
    T(d, (962, 990), "100,000 × 0.0001 = $10", font(58, "ExtraBold"), INK, "ra")
    T(d, (118, 1030), "ต่อ 1 พิป", font(34, "Medium"), MUTED)
    done(p, [84, 840, 912, 250], None, "MAIN-2: the page's formula rows and the channel's own arithmetic card 100,000 x 0.0001 = $10 per pip (not on the page)")
    PLATES["formula-own"]["boxes"] = {"card": [84, 840, 912, 250]}

    # MAIN-4/5: calc card 1 (Classic)
    own_plate("calc-classic", lambda d: calc_card(d, 84, 600, 912, "classic"),
              "MAIN-4/5: calc card 1 (Classic): 1.6 x 1 x $10 = $16.00, commission $0.00, total $16.00 (cost_check.py)",
              box="all", boxes=["spread", "comm", "total"])

    # MAIN-9: both cards, same size, same ink, no arrow
    def d_both(d):
        r1 = calc_card(d, 84, 590, 912, "classic", compact=True)
        r2 = calc_card(d, 84, 590 + 276 + 16, 912, "raw", compact=True)
        return {"classic_total": r1["total"], "raw_total": r2["total"], "all": (84, 590, 912, 568)}
    own_plate("calc-both", d_both, "MAIN-9: both calc cards (compact), Classic $16.00 and Raw $6.00, same size, same ink, no arrow",
              box="all", boxes=["classic_total", "raw_total"])

    def d_floor(d):
        centered(d, 590, "ทั้งสองยอดเป็นค่าต่ำสุด", font(52, "ExtraBold"))
        centered(d, 662, "คิดจากเลข “เริ่มที่” บนหน้าเว็บ", font(38, "Medium"), MUTED)
        for i, (nm, v) in enumerate((("Classic", "$16.00"), ("Raw", "$6.00"))):
            x = 84 + i * 464
            d.rounded_rectangle((x, 770, x + 448, 1000), 24, fill=CARD_BG, outline=RULE, width=3)
            T(d, (x + 224, 790), nm, font(44, "Bold"), INK, "ma")
            T(d, (x + 224, 860), v, font(76, "ExtraBold"), INK, "ma")
            T(d, (x + 224, 960), "ขั้นต่ำ", font(32, "Medium"), MUTED, "ma")
        return {"all": (84, 770, 912, 230)}
    own_plate("floor", d_floor, "CURIOSITY-3: both totals are floors computed from the advertised `from` numbers", box="all")

    # CURIOSITY-2: Classic card sentence + the table row (two crops of one still, on white)
    rows_stack("classic-card", "tm-classic", [(85, 362, 830, 598), (85, 1372, 700, 1434)], 1.2, 880, None,
               "CURIOSITY-2: Tickmill Classic card: the sentence and the table row `Spreads From 1.6 pips`", gap=24, box_idx=[1])

    def d_check(d):
        centered(d, 600, "เช็กลิสต์ก่อนเทรด", font(56, "ExtraBold"))
        items = ["อ่านหน้าประเภทบัญชีให้จบ", "บวกสเปรดกับคอมมิชชัน ตามล็อต", "ถามโบรกเป็นข้อความ ว่าสว็อปเท่าไหร่"]
        rects = {}
        for i, tx in enumerate(items):
            y = 720 + i * 150
            d.rounded_rectangle((84, y, 996, y + 126), 22, fill=CARD_BG, outline=RULE, width=3)
            d.ellipse((112, y + 27, 184, y + 99), fill=INK)
            T(d, (148, y + 63), str(i + 1), font(46, "Bold"), (255, 255, 255), "mm")
            T(d, (214, y + 63), tx, font(40, "Bold"), INK, "lm")
            rects[str(i + 1)] = (84, y, 912, 126)
        return rects
    own_plate("checklist", d_check, "SUMMARY-2/3/4: the three checks as one card, one row boxed per beat (the channel's own words)",
              boxes=["1", "2", "3"])


def main():
    build()
    (HERE / "plates.json").write_text(json.dumps(PLATES, indent=1, ensure_ascii=False) + "\n")
    manifest = {k: {"file": v["file"], "parts": v["parts"], "note": v["note"]} for k, v in PLATES.items()}
    (WORK / "media/real/DERIVED_MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    bad = [k for k, v in PLATES.items() if v.get("fits") is False]
    for k, v in PLATES.items():
        print(f"{k:14s} box={v['box']} zone={v.get('zone')} fits={v.get('fits')} z={v.get('z')}")
    if bad:
        print("DOES NOT FIT THE ZONE:", bad)
        return 1


if __name__ == "__main__":
    sys.exit(main())
