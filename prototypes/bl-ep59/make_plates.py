#!/usr/bin/env python3
"""BL EP59: the derived evidence plates (task-2db3174c).

Why plates and not `shift`: a COMP still is lifted with `shift`, which exposes the dark brand background above
(EP58 leftover a) or beside the avatar (leftover b) and leaves body text at the size the capture had (leftover d).
Here every evidence still is re-drawn on its own 1080x1920 canvas -- a crop of the REAL capture, scaled, with the
page's own background filling the rest -- so the spotlight box lands inside the take's evidence zone with shift 0.
Nothing is redrawn or retouched: each plate is a crop of a file in media/real/, scaled; the manifest says which.

Compliance (CEO-cleared 1 Oct): every Facebook-post plate carries the label strip -- rows 893-946 of
real/fb-post-head.png, cut at the word gap before "10 ชม." -- so the visible `เนื้อหาที่สร้างโดย AI` label and the
already pixelated page/author name travel with the post on every frame it appears. The strip contains no
unpixelated name: the censor (tools/bl_realfootage.py pixelate_region, block 14-18) was applied to the whole
screenshot before any crop (REAL_MANIFEST.json). Run `python3 prototypes/bl-ep59/make_plates.py` (needs PIL).

Output: <work>/media/real/d-*.png and <work>/media/real/DERIVED_MANIFEST.json; plates.json beside this file holds
each plate's box in canvas px for make_beats.py.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
WORK = Path("/opt/MoonieXHQ/Work/bl-ep59")
REAL = WORK / "media/real"
TABLE = HERE / "take_table.json"

CANVAS_W, CANVAS_H = 1080, 1920
SAFE_L, SAFE_R = 54, 1026
ARM_A_TOP = 560                      # tools/bl_checker.py ARM_A_EVIDENCE_TOP: arm A darkens everything above this
PILL_HALF, HEAD_GAP, EVID_GAP, BORDER = 82, 24, 12, 10
PAD = 8                              # px between the text and the spotlight rectangle

# The EP58 measurement is the stand-in until prototypes/bl-ep59/take_table.json exists (same avatar, same framing).
PROVISIONAL = {"lip_a": 903.04, "lip_b": 968.56, "lip_c": 999.92}


def zone(take: str) -> tuple[float, float]:
    """(top, bottom) of the canvas band a COMP spotlight may occupy on `take`, arm A's (the narrower)."""
    if TABLE.exists():
        head_top = json.loads(TABLE.read_text())["takes"][take]["head_top"]
    else:
        head_top = PROVISIONAL[take]
    cy = math.floor(head_top - HEAD_GAP - PILL_HALF)
    return float(ARM_A_TOP), cy - PILL_HALF - EVID_GAP - BORDER


def page_bg(img: Image.Image, near: tuple[int, int, int, int]) -> tuple[int, int, int]:
    """The page colour: the most common pixel in the (x0, y0, x1, y1) patch."""
    patch = img.crop(near).convert("RGB")
    colours = patch.getcolors(maxcolors=patch.width * patch.height)
    return max(colours)[1]


class Plate:
    """One 1080x1920 canvas. paste() draws a crop of a real still; box() records the spotlight in canvas px."""

    def __init__(self, name: str, bg=(255, 255, 255)):
        self.name = name
        self.img = Image.new("RGB", (CANVAS_W, CANVAS_H), bg)
        self.parts: list[dict] = []

    def paste(self, src: str, rect: tuple[int, int, int, int], z: float, at: tuple[float, float]):
        """Crop `rect` (x0, y0, x1, y1 in the still), scale by z, put its top-left at `at`. Returns a mapper
        source -> canvas for boxes inside the crop."""
        s = Image.open(REAL / f"{src}.png").convert("RGB")
        x0, y0, x1, y1 = rect
        c = s.crop(rect)
        w, h = round((x1 - x0) * z), round((y1 - y0) * z)
        c = c.resize((w, h), Image.LANCZOS)
        ax, ay = round(at[0]), round(at[1])
        self.img.paste(c, (ax, ay))
        self.parts.append({"src": f"real/{src}.png", "crop": list(rect), "zoom": z, "at": [ax, ay]})
        return lambda x, y, ww, hh: [ax + (x - x0) * z, ay + (y - y0) * z, ww * z, hh * z]

    def save(self):
        self.img.save(REAL / f"d-{self.name}.png", optimize=True)


def box_out(m, rect, pad_x=PAD, pad_y=PAD, clamp=True):
    """Pad a canvas rect and keep it in the safe rectangle."""
    x, y, w, h = m(*rect)
    x, y, w, h = x - pad_x, y - pad_y, w + 2 * pad_x, h + 2 * pad_y
    if clamp:
        x2 = min(x + w, SAFE_R)
        x = max(x, SAFE_L)
        w = x2 - x
    return [round(x), round(y), round(w), round(h)]


PLATES: dict[str, dict] = {}


def done(p: Plate, box, take=None, note="", credit=False):
    p.save()
    entry = {"file": f"real/d-{p.name}.png", "box": box, "take": take, "note": note, "credit": credit,
             "parts": p.parts}
    if box and take:
        top, bottom = zone(take)
        entry["zone"] = [top, bottom]
        entry["fits"] = box[1] >= top - 0.5 and box[1] + box[3] <= bottom + 0.5
    PLATES[p.name] = entry


# ── the Facebook post ────────────────────────────────────────────────────────
STRIP_RECT = (150, 893, 775, 946)       # fb-post-head: pixelated name tail + `· เนื้อหาที่สร้างโดย AI`, no avatar rows
LABEL_RECT = (500, 897, 775, 937)       # the label text inside it (REAL_MANIFEST evidence_box 495,900,290,38)
STRIP_AT = (54, 566)                    # same place on every FB plate: the label never moves between beats


def build_fb():
    # HOOK-3: the label itself, enlarged (z 1.15), the post title under it for context
    p = Plate("fb-h3")
    ms = p.paste("fb-post-head", STRIP_RECT, 1.15, STRIP_AT)
    top = STRIP_AT[1] + (STRIP_RECT[3] - STRIP_RECT[1]) * 1.15 + 14
    p.paste("fb-post-head", (0, 1015, 1080, 1133), 0.9, (SAFE_L, top))
    box = box_out(ms, (LABEL_RECT[0], LABEL_RECT[1], LABEL_RECT[2] - LABEL_RECT[0], LABEL_RECT[3] - LABEL_RECT[1]),
                  pad_x=10, pad_y=6)
    done(p, box, "lip_a", "HOOK-3: the Facebook label `เนื้อหาที่สร้างโดย AI`, pixelated name beside it")

    # HOOK-4: strip + the post title, spotlight on its first line
    p = Plate("fb-h4")
    p.paste("fb-post-head", STRIP_RECT, 0.8, STRIP_AT)
    top = STRIP_AT[1] + (STRIP_RECT[3] - STRIP_RECT[1]) * 0.8 + 8
    mb = p.paste("fb-post-head", (0, 1015, 1080, 1133), 0.95, (SAFE_L - 34 * 0.95, top))
    done(p, box_out(mb, (34, 1015, 973, 50)), "lip_a", "HOOK-4: the post's title, first line")

    # PATTERN-1: strip + the paragraph lines 1-2, spotlight on line 1
    p = Plate("fb-p1")
    p.paste("fb-post-head", STRIP_RECT, 0.8, STRIP_AT)
    top = STRIP_AT[1] + (STRIP_RECT[3] - STRIP_RECT[1]) * 0.8 + 8
    mb = p.paste("fb-post-figure", (0, 863, 1080, 953), 0.95, (SAFE_L - 33 * 0.95, top))
    done(p, box_out(mb, (33, 863, 999, 45)), "lip_a", "PATTERN-1: paragraph line 1 (offer or charge a fee)")

    # PATTERN-2 / PATTERN-3: strip + paragraph lines 3-4; 2 spotlights line 3 ($10,000 up), 3 none
    p = Plate("fb-p2")
    p.paste("fb-post-head", STRIP_RECT, 0.8, STRIP_AT)
    mb = p.paste("fb-post-figure", (0, 963, 1080, 1058), 0.95, (SAFE_L - 33 * 0.95, top))
    done(p, box_out(mb, (35, 963, 872, 45)), "lip_a", "PATTERN-2/3: paragraph lines 3-4; PATTERN-2 spotlights line 3")

    # CONTEXT-1..4: strip + the whole question list, one spotlight per question
    p = Plate("fb-q")
    p.paste("fb-post-head", STRIP_RECT, 0.8, STRIP_AT)
    qz = 0.95
    qtop = 640
    mb = p.paste("fb-post-questions", (0, 692, 1080, 1209), qz, (SAFE_L - 34 * qz, qtop))
    boxes = {
        "intro": box_out(mb, (36, 692, 543, 46)),
        "q1": box_out(mb, (35, 779, 906, 84)),
        "q2": box_out(mb, (35, 905, 964, 50)),
        "q3": box_out(mb, (34, 987, 999, 90)),
        "q4": box_out(mb, (35, 1125, 983, 84)),
    }
    done(p, None, None, "CONTEXT-1..4 and the intro line: the post's four questions as written")
    PLATES["fb-q"]["boxes"] = boxes


# ── WikiFX / regulator pages ─────────────────────────────────────────────────
def snap_rows(src: Image.Image, rows, bg, down=60, up=100):
    """Move the window's edges to the nearest rows that are the page colour all the way across, so the crop never
    cuts through a line of text: r0 goes down to the first such row, r1 goes up to the last."""
    px = src.convert("RGB")
    def plain(r):
        row = list(px.crop((0, r, 1080, r + 1)).get_flattened_data() if hasattr(px, 'get_flattened_data') else px.crop((0, r, 1080, r + 1)).getdata())
        return all(max(abs(a - b) for a, b in zip(p, bg)) <= 10 for p in row)
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


def page(name, src, text_rect, z, cy, rows, take=None, note="", credit=True, zmax=1.4, bg_patch=None, xcrop=None):
    """A page crop at zoom z (capped so the text rectangle fits the safe width), the spotlight centred on y `cy`.
    rows = (r0, r1): the source rows that may be drawn (snapped to plain rows); the rest of the canvas is the page
    colour, taken from bg_patch (x0, y0, x1, y1) or white. xcrop = the source x where the crop's left edge sits (a
    plain column, chosen so the crop does not cut through a neighbouring element); the box is then put at the safe
    margin."""
    x, y, w, h = text_rect
    z = min(z, zmax, (SAFE_R - SAFE_L - 2 * PAD) / w)
    s = Image.open(REAL / f"{src}.png").convert("RGB")
    bg = page_bg(s, bg_patch) if bg_patch else (255, 255, 255)
    r0, r1 = snap_rows(s, rows, bg)
    p = Plate(name, bg)
    if xcrop is None:
        left = max(SAFE_L + PAD, (CANVAS_W - w * z) / 2)          # canvas x of the text rectangle's left edge
        xr0, at_x = x - left / z, 0.0                             # source x at canvas x 0
    else:
        xr0, at_x = float(xcrop), SAFE_L + PAD - (x - xcrop) * z  # the crop's own left edge sits at canvas at_x
    ay0 = cy + (r0 - (y + h / 2)) * z                        # canvas y of source row r0
    crop = (max(0, math.floor(xr0)), r0, min(1080, math.ceil(xr0 + (CANVAS_W - at_x) / z)), r1)
    mb = p.paste(src, crop, z, (at_x + (crop[0] - xr0) * z, ay0))
    box = box_out(mb, text_rect)
    done(p, box, take, note, credit)
    return p


def build_pages():
    DARK = (50, 56, 67)
    # COMP, lip_b
    page("contact", "wfx-contact", (30, 702, 218, 46), 1.4, 660, (690, 1100), "lip_b",
         "MAIN-5: the contact page's business-cooperation tab", bg_patch=(500, 800, 520, 820))
    page("terms", "wfx-terms", (336, 318, 408, 34), 1.0, 650, (130, 520), "lip_b",
         "MAIN-6: Service Agreement of WikiFX (a user software agreement)", bg_patch=(10, 300, 30, 320))
    page("stmt-title", "wfx-stmt-title", (96, 334, 818, 92), 1.1, 650, (170, 495), "lip_b",
         "MAIN-7: title of the 12 Jun 2025 statement", bg_patch=(1000, 300, 1020, 320))
    page("stmt-l1", "wfx-stmt-score", (56, 639, 896, 70), 1.1, 650, (560, 1200), "lip_b",
         "MAIN-8: 'operates independently ... not linked to partnerships or payments'")
    page("stmt-l2", "wfx-stmt-score", (56, 680, 884, 32), 1.1, 650, (560, 1200), "lip_b",
         "MAIN-9: 'a five-dimensional model, covering:'")
    page("partner-a", "wfx-stmt-partner", (86, 848, 908, 72), 1.05, 660, (830, 1100), "lip_b",
         "MAIN-11: 'Partnered brokers ... Complaint Mediation Window'")
    # EVID
    page("stmt-list", "wfx-stmt-score", (60, 740, 930, 440), 1.0, 900, (560, 1250), None,
         "MAIN-10: the five indices; no weights given")
    page("partner-b", "wfx-stmt-partner", (86, 1474, 904, 222), 1.0, 860, (1440, 1740), None,
         "MAIN-12: why non-partners do not have the window")
    page("about-score", "wfx-about-score", (185, 938, 530, 215), 1.2, 820, (900, 1250), None,
         "MAIN-2: the scoring-system paragraph on the About page")
    page("about-foot-mail", "wfx-about-footer", (85, 1852, 310, 30), 2.0, 820, (1851, 1895), None,
         "MAIN-4: the advertising contact line, enlarged", bg_patch=(40, 1700, 60, 1720))
    page("about-foot-note", "wfx-about-footer", (388, 1538, 606, 60), 1.6, 820, (1500, 1620), None,
         "CURIOSITY-4: the site's own note to check key details with official sources", bg_patch=(40, 1570, 60, 1590),
         xcrop=386)
    page("about-intro", "wfx-about-top", (470, 640, 140, 44), 2.0, 820, (632, 700), None,
         "CURIOSITY-1: the About page, 'เราคือใคร' (Who we are)")
    # the regulator register (no WikiFX image: no credit)
    page("mas-title", "mas-register", (245, 292, 590, 52), 1.5, 820, (262, 362), None,
         "CURIOSITY-5: an official register's own page, 'Financial Institutions Directory'", credit=False,
         bg_patch=(500, 270, 520, 285))
    page("mas-title-c", "mas-register", (245, 292, 590, 52), 1.5, 680, (262, 362), "lip_c",
         "SUMMARY-7: the same register page, spotlight on its title", credit=False, bg_patch=(500, 270, 520, 285))
    page("mas-plain", "mas-register", (245, 292, 590, 52), 1.5, 680, (262, 362), "lip_c",
         "SUMMARY-8/9: same register page, no spotlight", credit=False, bg_patch=(500, 270, 520, 285))
    PLATES["mas-plain"]["box"] = None


def main():
    build_fb()
    build_pages()
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
