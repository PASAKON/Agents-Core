#!/usr/bin/env python3
"""BL EP60: the derived evidence plates (task-3ae66e7a). Shape from prototypes/bl-ep59/make_plates.py.

Every WikiFX still is re-drawn on its own 1080x1920 canvas -- a crop of the REAL capture, scaled, with the page's own
background filling the rest -- so the spotlight box lands inside the take's evidence zone with shift 0. Nothing is
redrawn or retouched; each plate is a crop of a file in media/real/, scaled; DERIVED_MANIFEST.json says which.

Compliance for gb-complaint.png (a user's complaint on WikiFX): the avatar block (a pixelated square, x 95-205 / y 225-280),
the pixelated tag beside the date and the rest of the user row are never inside a crop. Only three pieces are used: the
breadcrumb strip (y 153-170), the date `2021-02-03` (x 94-165) and two phrases of the complaint's first line that the
narration itself voices (`ไม่สามารถถอนเงินได้`, `ไม่สามารถติดต่อบุคคลที่ให้คำแนะนำได้`). The rest of that line (an amount and a
word for being cheated) is NOT shown: the script does not say it.

Run `python3 prototypes/bl-ep60/make_plates.py` (needs PIL). Output: <work>/media/real/d-*.png, DERIVED_MANIFEST.json and
plates.json beside this file (each plate's box in canvas px for make_beats.py).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
WORK = Path("/opt/MoonieXHQ/Work/bl-ep60")
REAL = WORK / "media/real"
TABLE = HERE / "take_table.json"

CANVAS_W, CANVAS_H = 1080, 1920
SAFE_L, SAFE_R = 54, 1026
ARM_A_TOP = 560                      # tools/bl_checker.py ARM_A_EVIDENCE_TOP: arm A darkens everything above this
PILL_HALF, HEAD_GAP, EVID_GAP, BORDER = 82, 24, 12, 10
PAD = 8                              # px between the text and the spotlight rectangle

# until take_table.json exists: EP59's measurement (same avatar, same framing)
PROVISIONAL = {"lip_a": 903.04, "lip_b": 968.56, "lip_c": 985.36}


def zone(take: str) -> tuple[float, float]:
    """(top, bottom) of the canvas band a COMP spotlight may occupy on `take`, arm A's (the narrower)."""
    head_top = json.loads(TABLE.read_text())["takes"][take]["head_top"] if TABLE.exists() else PROVISIONAL[take]
    cy = math.floor(head_top - HEAD_GAP - PILL_HALF)
    return float(ARM_A_TOP), cy - PILL_HALF - EVID_GAP - BORDER


def page_bg(img: Image.Image, near: tuple[int, int, int, int]) -> tuple[int, int, int]:
    patch = img.crop(near).convert("RGB")
    colours = patch.getcolors(maxcolors=patch.width * patch.height)
    return max(colours)[1]


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


def done(p: Plate, box, take=None, note="", credit=True, text_px=None):
    p.save()
    entry = {"file": f"real/d-{p.name}.png", "box": box, "take": take, "note": note, "credit": credit,
             "parts": p.parts}
    if text_px is not None:
        entry["text_px"] = round(text_px, 1)
    if box and take:
        top, bottom = zone(take)
        entry["zone"] = [top, bottom]
        entry["fits"] = box[1] >= top - 0.5 and box[1] + box[3] <= bottom + 0.5
    PLATES[p.name] = entry


def snap_rows(src: Image.Image, rows, bg, down=60, up=100, gap_x=(60, 1020)):
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


def page(name, src, text_rect, z, cy, rows, take=None, note="", credit=True, zmax=1.4, bg_patch=None, xcrop=None,
         gap_x=(60, 1020), snap=True, fit=True, xmax=1080):
    """A page crop at zoom z (capped so the text rectangle fits the safe width -- and, on a COMP plate, the take's evidence
    zone), the spotlight centred on y `cy` (a COMP's cy is the middle of its zone when cy is None). rows = (r0, r1): the
    source rows that may be drawn; the rest of the canvas is the page colour (bg_patch or white)."""
    x, y, w, h = text_rect
    z = min(z, zmax, (SAFE_R - SAFE_L - 2 * PAD) / w)
    if take and fit:
        top, bottom = zone(take)
        z = min(z, (bottom - top - 2 * PAD - 2) / h)
        if cy is None:
            cy = (top + bottom) / 2
    s = Image.open(REAL / f"{src}.png").convert("RGB")
    bg = page_bg(s, bg_patch) if bg_patch else (255, 255, 255)
    if take:    # a COMP plate ends where the caption pill begins: page text running on under the pill reads as a mess
        limit = y + h / 2 + (zone(take)[1] + 6 - cy) / z
        rows = (rows[0], min(rows[1], math.floor(limit)))
    r0, r1 = snap_rows(s, rows, bg, gap_x=gap_x) if snap else rows
    p = Plate(name, bg)
    if xcrop is None:
        left = max(SAFE_L + PAD, (CANVAS_W - w * z) / 2)
        xr0, at_x = x - left / z, 0.0
    else:
        xr0, at_x = float(xcrop), SAFE_L + PAD - (x - xcrop) * z
    ay0 = cy + (r0 - (y + h / 2)) * z
    crop = (max(0, math.floor(xr0)), r0, min(xmax, math.ceil(xr0 + (CANVAS_W - at_x) / z)), r1)
    mb = p.paste(src, crop, z, (at_x + (crop[0] - xr0) * z, ay0))
    done(p, box_out(mb, text_rect), take, note, credit)
    return p


def card(name, src, text_rect, xspan, z, cy, rows, note="", credit=True, take=None):
    """A dark-page crop laid as a card on a white plate, centred on y `cy` (a flat dark plate reads empty: bl_merge refuses it)."""
    x, y, w, h = text_rect
    s = Image.open(REAL / f"{src}.png").convert("RGB")
    r0, r1 = snap_rows(s, rows, page_bg(s, (40, rows[0] + 5, 60, rows[0] + 25)))
    x0, x1 = xspan
    cw, ch = round((x1 - x0) * z), round((r1 - r0) * z)
    assert cw <= SAFE_R - SAFE_L, (name, cw)
    p = Plate(name, (255, 255, 255))
    at = ((CANVAS_W - cw) / 2, cy - (y + h / 2 - r0) * z)
    mb = p.paste(src, (x0, r0, x1, r1), z, at)
    done(p, box_out(mb, text_rect), take, note, credit)


def snippets(name, src, items, z, cy, take=None, note="", gap=34):
    """Several small crops of one still laid side by side on a white plate (the complaint: nothing but what is voiced).
    items = [(x0, y0, x1, y1), ...]; the spotlight spans them all."""
    ws = [round((r[2] - r[0]) * z) for r in items]
    total = sum(ws) + gap * (len(items) - 1)
    assert total <= SAFE_R - SAFE_L - 2 * PAD, (name, total)
    p = Plate(name, (255, 255, 255))
    x = (CANVAS_W - total) / 2
    boxes = []
    for r, w in zip(items, ws):
        h = (r[3] - r[1]) * z
        m = p.paste(src, r, z, (x, cy - h / 2))
        boxes.append(m(r[0], r[1], r[2] - r[0], r[3] - r[1]))
        x += w + gap
    bx0 = min(b[0] for b in boxes) - PAD
    by0 = min(b[1] for b in boxes) - PAD
    bx1 = max(b[0] + b[2] for b in boxes) + PAD
    by1 = max(b[1] + b[3] for b in boxes) + PAD
    done(p, [round(bx0), round(by0), round(bx1 - bx0), round(by1 - by0)], take, note, True)


def src_box(name, rect, pad_x=PAD, pad_y=PAD):
    """A spotlight box (canvas px) for a rectangle of the still the plate's first crop came from."""
    part = PLATES[name]["parts"][0]
    x0, y0 = part["crop"][0], part["crop"][1]
    z, (ax, ay) = part["zoom"], part["at"]
    x, y, w, h = rect
    return box_out(lambda a, b, c, d: [ax + (a - x0) * z, ay + (b - y0) * z, c * z, d * z], rect, pad_x, pad_y)


def build():
    L = "lip_a"
    # ── COMP, lip_a (zone about 133 px tall: one or two text lines) ──────────────────────────────────────────
    page("warning", "gb-warning", (40, 900, 940, 110), 1.1, None, (880, 1030), L,
         "HOOK-2: WikiFX's red warning card on the GB page, dated 2026-10-01", bg_patch=(500, 850, 520, 865))
    page("oct-title", "gb-article-oct", (0, 400, 1080, 130), 1.0, None, (380, 560), L,
         "HOOK-3: WikiFX article title: GB used to sit under CySEC but the licence was revoked", bg_patch=(500, 370, 520, 385))
    page("header-tile", "gb-header", (205, 475, 450, 120), 1.0, None, (460, 596), L,
         "HOOK-4: GB's profile tile on WikiFX, red label `ยังไม่มีการกำกับดูแล`", bg_patch=(10, 300, 30, 320), xcrop=190, xmax=690, snap=False)
    snippets("complaint-date", "gb-complaint", [(70, 152, 297, 168), (94, 1043, 166, 1060)], 2.4, 626, L,
             "PATTERN-1: complaint page breadcrumb (GB, feedback details) and its date 2021-02-03; no user row")
    snippets("complaint-words", "gb-complaint", [(93, 292, 211, 322), (562, 292, 776, 322)], 2.3, 626, L,
             "PATTERN-2: two phrases of the user's text: cannot withdraw / cannot contact; the rest of the line is not shown")
    # ── COMP, lip_b ─────────────────────────────────────────────────────────────────────────────────────────
    B = "lip_b"
    page("basic-country", "gb-basic", (40, 855, 370, 75), 1.6, None, (845, 960), B,
         "MAIN-5: basic information, region of registration: Cyprus", bg_patch=(500, 1300, 520, 1320), xmax=560)
    page("basic-name", "gb-basic", (40, 1105, 370, 45), 1.8, None, (1090, 1170), B,
         "MAIN-6: basic information, company name Goldenburg Group Limited", bg_patch=(500, 1300, 520, 1320), xmax=560)
    page("lic-no", "gb-article-licence", (0, 940, 1080, 50), 1.0, None, (925, 1010), B,
         "MAIN-7: the article's line with licence number 242/14", bg_patch=(500, 1200, 520, 1220))
    page("lic-date", "gb-article-licence", (0, 940, 1080, 95), 1.0, None, (925, 1075), B,
         "MAIN-8: the article's line `effective from 14 July 2014`", bg_patch=(500, 1200, 520, 1220))
    page("related-head", "gb-related", (158, 800, 300, 60), 1.8, None, (790, 880), B,
         "MAIN-9: the `related companies` heading", bg_patch=(500, 400, 520, 420), snap=False)
    page("revoked-l1", "gb-article-revoked", (0, 870, 1080, 48), 1.0, None, (860, 940), B,
         "MAIN-11: the article's first line: current licence status `revoked`", bg_patch=(500, 600, 520, 620))
    # ── COMP, lip_c ─────────────────────────────────────────────────────────────────────────────────────────
    C = "lip_c"
    page("header-plain", "gb-header", (205, 475, 450, 120), 1.0, None, (460, 596), C,
         "SUMMARY-7: GB's profile tile again (box = the tile, only so the credit chip has a top to clear)", bg_patch=(10, 300, 30, 320), xcrop=190, xmax=690, snap=False)
    # a WikiFX still needs its credit chip, and bl_checker refuses a credit with no box (no evidence top to clear): box the tile
    PLATES["header-plain"]["box"] = [54, 600, 490, 130]
    page("survey-date", "gb-survey", (90, 215, 850, 75), 1.2, None, (200, 330), C,
         "SUMMARY-9: the 2019 survey page title and its date 2019-05-31 (tag `Good`)", bg_patch=(500, 400, 520, 420))
    page("survey-plain", "gb-survey", (90, 215, 850, 75), 1.2, None, (200, 330), C,
         "SUMMARY-8: the same survey header as SUMMARY-9, same box", bg_patch=(500, 400, 520, 420))
    PLATES["survey-plain"]["box"] = PLATES["survey-date"]["box"]   # same placement as survey-date; same credit rule as above
    # ── EVID (full canvas to use; the pill sits at 1300) ────────────────────────────────────────────────────
    page("score", "gb-header", (205, 780, 450, 260), 1.6, 840, (440, 1090), None,
         "CONTEXT-1: GB's profile on WikiFX: the score tile, 1.38 out of 10", bg_patch=(10, 300, 30, 320), xcrop=190, xmax=690, snap=False)
    page("oct-top", "gb-article-oct", (0, 400, 1080, 130), 1.0, 760, (240, 740), None,
         "CONTEXT-3/4: the article's top: breadcrumb, title, `WikiFX | 10h`", bg_patch=(500, 600, 520, 620))
    PLATES["oct-top"]["boxes"] = {"byline": src_box("oct-top", (28, 560, 150, 32)),
                                  "title": src_box("oct-top", (290, 405, 370, 62))}
    page("entity", "gb-article-entity", (0, 925, 1080, 80), 1.0, 700, (900, 1480), None,
         "CONTEXT-5, CURIOSITY-1/2: the article's review and licence paragraphs", bg_patch=(500, 1700, 520, 1720))
    PLATES["entity"]["boxes"] = {"cysec": src_box("entity", (0, 1340, 1080, 46)),
                                 "uk": src_box("entity", (0, 925, 1080, 95)),
                                 "names": src_box("entity", (0, 1292, 352, 46))}
    page("header-crumb", "gb-header", (158, 340, 345, 45), 1.0, 760, (300, 1090), None,
         "MAIN-1: GB's WikiFX page: breadcrumb `หน้าแรก - โบรกเกอร์ - GB`", bg_patch=(10, 300, 30, 320), snap=False)
    page("licence-card", "gb-licence", (10, 615, 1060, 690), 1.0, 880, (590, 1320), None,
         "MAIN-2: the forex-licence tab: `ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์`", bg_patch=(500, 570, 520, 585), snap=False)
    page("licence-suspect", "gb-licence", (60, 1715, 860, 110), 1.0, 860, (1380, 1840), None,
         "MAIN-3: company overview, `ใบอนุญาตในการกำกับดูแลกำลังถูกตั้งข้อสงสัย`", bg_patch=(500, 1500, 520, 1520))
    page("related-card", "gb-related", (158, 930, 554, 90), 1.7, 840, (810, 1075), None,
         "MAIN-10: related company card GOLDENBURG GROUP LTD(Cyprus), tags `ยกเลิกการจดทะเบียน` and Cyprus",
         bg_patch=(500, 400, 520, 420), xcrop=100, xmax=745, snap=False, zmax=1.6)
    page("revoked-p", "gb-article-revoked", (0, 870, 1080, 105), 1.0, 820, (860, 1050), None,
         "MAIN-12: `GB ไม่มีใบอนุญาตกำกับดูแลที่มีผลบังคับใช้จริงในปัจจุบันแล้ว`", bg_patch=(500, 600, 520, 620))
    page("revoked-cysec", "gb-article-revoked", (0, 965, 1080, 80), 1.0, 820, (860, 1050), None,
         "MAIN-13: `ตรวจสอบสถานะล่าสุดกับ CySEC โดยตรงก่อนตัดสินใจ`", bg_patch=(500, 600, 520, 620))
    page("survey-title", "gb-survey", (90, 215, 850, 75), 1.12, 780, (130, 330), None,
         "CURIOSITY-3: the 2019 survey page title, date 2019-05-31", bg_patch=(500, 400, 520, 420))
    # CURIOSITY-4: the survey's title strip over its body text (two crops of one page: the body alone is a tiny box on blank)
    sv = Image.open(REAL / "gb-survey.png").convert("RGB")
    p = Plate("survey-body", page_bg(sv, (500, 400, 520, 420)))
    p.paste("gb-survey", (70, 205, 950, 300), 1.0, (100, 640))
    mb = p.paste("gb-survey", (86, 1062, 944, 1130), 1.12, (60, 790))
    done(p, box_out(mb, (90, 1065, 840, 60)), None, "CURIOSITY-4: survey title and the text `licence CIF 242/14 under CySEC`")


def main():
    build()
    out = HERE / "plates.json"
    out.write_text(json.dumps(PLATES, indent=1, ensure_ascii=False) + "\n")
    manifest = {f"real/d-{k}.png": {"derived_from": sorted({p["src"] for p in v["parts"]}), "note": v["note"],
                                    "parts": v["parts"], "retouched": False}
                for k, v in PLATES.items()}
    (REAL / "DERIVED_MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    for k, v in PLATES.items():
        print(f"{k:16s} box={v['box']} zone={v.get('zone')} fits={v.get('fits')}")


if __name__ == "__main__":
    sys.exit(main())
