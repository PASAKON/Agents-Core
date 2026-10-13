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


def rows_stack(name, src, items, z, cy, take=None, note="", gap=10):
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
    bx0 = min(b[0] for b in boxes) - PAD
    by0 = min(b[1] for b in boxes) - PAD
    bx1 = max(b[0] + b[2] for b in boxes) + PAD
    by1 = max(b[1] + b[3] for b in boxes) + PAD
    done(p, [round(bx0), round(by0), round(bx1 - bx0), round(by1 - by0)], take, note, True)
    PLATES[name]["z"] = z


def src_box(name, rect, pad_x=PAD, pad_y=PAD):
    """A spotlight box (canvas px) for a rectangle of the still the plate's first crop came from."""
    part = PLATES[name]["parts"][0]
    x0, y0 = part["crop"][0], part["crop"][1]
    z, (ax, ay) = part["zoom"], part["at"]
    x, y, w, h = rect
    return box_out(lambda a, b, c, d: [ax + (a - x0) * z, ay + (b - y0) * z, c * z, d * z], rect, pad_x, pad_y)


# ── the channel's own drawings: calc cards and checklist cards ───────────────────────────────────────────────────────
INK = (20, 28, 48)
MUTED = (96, 104, 124)
RULE = (200, 205, 215)
CARD_BG = (246, 247, 250)


def _text(d, xy, s, f, fill=INK, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def calc_card(d, top, title, sub, rows, total_label, total_val, left=84, right=996, height=None):
    """One calc card (the same drawing for every card): title, a formula row with its names under it, plain rows, a
    total. Ink on white, one weight scale, no green/red, no arrow. Returns (bottom, rect of the total row)."""
    h = height or 470
    d.rounded_rectangle((left, top, right, top + h), 28, fill=CARD_BG, outline=RULE, width=3)
    _text(d, (left + 40, top + 26), title, font(54, "Bold"))
    _text(d, (left + 40, top + 92), sub, font(32, "Regular"), MUTED)
    y = top + 150
    for label, val, small in rows:
        d.line((left + 40, y, right - 40, y), fill=RULE, width=2)
        _text(d, (left + 40, y + 18), label, font(40, "Medium"), MUTED)
        _text(d, (right - 40, y + 14), val, font(50, "Bold"), INK, "ra")
        if small:
            _text(d, (right - 40, y + 76), small, font(30, "Regular"), MUTED, "ra")
        y += 124 if small else 86
    d.line((left + 40, y, right - 40, y), fill=INK, width=4)
    _text(d, (left + 40, y + 14), total_label, font(46, "Bold"))
    _text(d, (right - 40, y + 6), total_val, font(66, "ExtraBold"), INK, "ra")
    return top + h, (left + 20, y - 4, right - left - 40, 94)


def classic_card(d, top):
    return calc_card(d, top, "Classic", "คำนวณเอง จากเลขบนหน้าเว็บ Tickmill · 1 ล็อต",
                     [("สเปรด", "1.6 × 1 × $10 = $16.00", "สเปรด × ขนาด × ค่าพิป"), ("คอมมิชชัน", "$0.00", None)],
                     "รวม", "$16.00")


def raw_card(d, top):
    return calc_card(d, top, "Raw", "คำนวณเอง จากเลขบนหน้าเว็บ Tickmill · 1 ล็อต",
                     [("สเปรด", "0.0 × 1 × $10 = $0.00", "สเปรด × ขนาด × ค่าพิป"), ("คอมมิชชัน", "$3 × 2 ข้าง = $6.00", None)],
                     "รวม", "$6.00")
