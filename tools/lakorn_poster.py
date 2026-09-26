#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-letter a people-only drama poster in the Thai lakorn layout — $0, local, exact Thai.

    .venv/bin/python tools/lakorn_poster.py IN.png OUT.png \
        --line1 "จุดจบของ" --line2 "เจ้าหนี้นอกระบบ" --english "THE END OF THE LOAN SHARK" \
        [--tagline "..."] [--scale 0.92] [--crop-top 0.125] [--title-top 1250] [--font kanit|pridi]

Why it exists (banchi covers, 2026-09-24): ChatGPT drew the right people but put the
title across the top, and needed a second edit turn just to draw it at all. The CEO:
"คนแบบนี้ถูกแล้ว ติดแค่ข้อความ … มันจะมีจุดที่อยู่ประจำของมัน". Six real Channel 3 posters
(ลายกินรี ×2, คลื่นชีวิต, 18 มงกุฎ, ลดา, เลือดเจ้าพระยา) share one layout, which this draws:

  top-left      the channel logo            → our wordmark (--brand)
  top-right     the production company       → our show name (--show)
  upper 2/3     the cast, faces              → the input picture, old title cropped off
  lower third   the title logo, centred, big → --line1 (small) over --line2 (big, gold)
  under it      the English title, spaced    → --english
  near it       the tagline (คำโปรย)          → --tagline
  very bottom   tiny billing block           → --credits

The canvas is 1080×1920 (the film is 9:16). Facebook shows a vertical video in the feed
as a centred 4:5 crop (y 285..1635), so the title block is kept above y 1635 and the
tool writes a *-feed45.png preview of exactly what the feed shows.

Thai is shaped by Pillow's raqm layout (tone marks stacked right); the tool refuses to
run without it rather than draw floating vowels.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

ROOT = Path(__file__).resolve().parent.parent
FONTS = {
    # Kanit ExtraBold, Thai subset (already in the repo for the BL cut template)
    "kanit": ROOT / ".claude/skills/blackliquidity-cut/template/assets/fonts/kanit-800-aa86a0cb.woff2",
    "pridi": Path("/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeSign/design-templates/chatudo/fonts/Pridi-Bold.ttf"),
}
LATIN = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
SMALL_TH = "/System/Library/Fonts/SukhumvitSet.ttc"  # face 4 = Semi Bold; Sathu shifted tone marks
W, H = 1080, 1920
FEED_TOP, FEED_BOTTOM = 285, 1635  # centred 4:5 crop of a 9:16 frame


def font(path, size, index=0):
    if str(path) == SMALL_TH:
        index = 4
    return ImageFont.truetype(str(path), size, index=index, layout_engine=ImageFont.Layout.RAQM)


def fit(path, text, max_w, size):
    while size > 20:
        f = font(path, size)
        l, t, r, b = f.getbbox(text)
        if r - l <= max_w:
            return f
        size -= 4
    return font(path, size)


def gradient(w, h, stops):
    """Vertical gradient through (pos, (r,g,b)) stops."""
    g = Image.new("RGB", (1, h))
    px = g.load()
    for y in range(h):
        p = y / max(1, h - 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= p <= p1:
                k = (p - p0) / max(1e-6, p1 - p0)
                px[0, y] = tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))
                break
    return g.resize((w, h))


GOLD = [(0.0, (255, 246, 205)), (0.45, (240, 196, 92)), (0.7, (200, 140, 40)), (1.0, (120, 72, 14))]
SILVER = [(0.0, (255, 255, 255)), (0.6, (215, 215, 222)), (1.0, (150, 150, 162))]


def draw_title(canvas, text, f, cx, top, stops, stroke=5, shadow=14):
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    w, h = r - l, b - t
    x, y = int(cx - w / 2), int(top)
    pad = shadow * 3
    mask = Image.new("L", (w + 2 * pad, h + 2 * pad))
    ImageDraw.Draw(mask).text((pad - l, pad - t), text, font=f, fill=255)
    outline = Image.new("L", mask.size)
    ImageDraw.Draw(outline).text((pad - l, pad - t), text, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
    glow = outline.filter(ImageFilter.GaussianBlur(shadow))
    dark = Image.new("RGB", mask.size, (0, 0, 0))
    canvas.paste(dark, (x - pad, y - pad + 6), glow.point(lambda v: min(255, int(v * 1.6))))
    canvas.paste(Image.new("RGB", mask.size, (46, 22, 0)), (x - pad, y - pad), outline)
    canvas.paste(gradient(mask.size[0], mask.size[1], stops), (x - pad, y - pad), mask)
    return y + h


def logo_from_black(path, max_w, max_h):
    """A title logo drawn on pure black -> RGBA. Light-on-black is 'screened' in:
    alpha = the brightest channel (a small floor drops JPEG-ish noise), colour =
    pixel / alpha, which is exact when the ground really is black."""
    rgb = np.asarray(Image.open(path).convert("RGB")).astype("float32")
    peak = rgb.max(axis=2)
    alpha = np.clip((peak - 18) * 255.0 / 200.0, 0, 255)
    col = np.clip(rgb / np.maximum(alpha[..., None] / 255.0, 1e-3), 0, 255)
    out = Image.fromarray(np.dstack([col, alpha]).astype("uint8"), "RGBA")
    box = out.getchannel("A").getbbox()
    if box:
        out = out.crop(box)
    k = min(max_w / out.width, max_h / out.height)
    return out.resize((int(out.width * k), int(out.height * k)), Image.LANCZOS)


def draw_plain(canvas, text, f, cx, top, fill, spacing=0, shadow=6, anchor_left=None):
    d = ImageDraw.Draw(canvas)
    if spacing:
        text = (" " * spacing).join(text) if spacing > 0 else text
    l, t, r, b = f.getbbox(text)
    x = anchor_left if anchor_left is not None else int(cx - (r - l) / 2)
    sh = Image.new("L", canvas.size)
    ImageDraw.Draw(sh).text((x - l, top - t + 3), text, font=f, fill=200)
    canvas.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(shadow)))
    d.text((x - l, top - t), text, font=f, fill=fill)
    return top + (b - t)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--line1", default="", help="typed title, small line (ignored with --logo)")
    ap.add_argument("--line2", default="", help="typed title, big line (ignored with --logo)")
    ap.add_argument("--logo", type=Path, help="a title LOGO drawn on pure black (e.g. by ChatGPT) — used instead of typed lines")
    ap.add_argument("--cta", default="", help="the airtime line of a lakorn poster, e.g. 'ดูจบในตอนเดียว'")
    ap.add_argument("--tagline-top", action="store_true", help="put the quoted tagline at the top, under the corner marks")
    ap.add_argument("--english", default="")
    ap.add_argument("--tagline", default="")
    ap.add_argument("--brand", default="ILAG STUDIO")
    ap.add_argument("--show", default="ละครสั้นคุณธรรม")
    ap.add_argument("--credits", default="ละครสั้นคุณธรรม by ILAG Studio  ·  ภาพและเสียงสร้างด้วย AI")
    ap.add_argument("--font", choices=sorted(FONTS), default="kanit")
    ap.add_argument("--crop-top", type=float, default=0.125, help="fraction of the source height holding the old title")
    ap.add_argument("--scale", type=float, default=1.0, help="shrink the picture (<1) when a low face would sit under the title")
    ap.add_argument("--img-top", type=int, default=130, help="canvas y where the cropped picture starts")
    ap.add_argument("--title-top", type=int, default=1250, help="canvas y where the title block starts")
    ap.add_argument("--logo-h", type=int, default=260,
                    help="max height of the --logo; raise it with a lower --title-top to fill the space under the title")
    args = ap.parse_args()

    if not features.check("raqm"):
        print("REFUSED: Pillow has no raqm — Thai tone marks would float. Use the repo .venv.", file=sys.stderr)
        return 1

    src = Image.open(args.src).convert("RGB")
    sw, sh = src.size
    pic = src.crop((0, int(sh * args.crop_top), sw, sh))
    pw = int(W * args.scale)
    pic = pic.resize((pw, int(pic.height * pw / sw)), Image.LANCZOS)

    # background: the picture itself, blurred and darkened, so the headroom and the
    # title area carry the scene's own colours instead of a flat band
    bg = pic.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(60))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (8, 6, 10)), 0.55)
    canvas = bg.copy()

    alpha = Image.new("L", pic.size, 255)
    ad = ImageDraw.Draw(alpha)
    top_fade, bottom_fade = 90, 380
    for y in range(top_fade):
        ad.line([(0, y), (pw, y)], fill=int(255 * y / top_fade))
    for y in range(bottom_fade):
        yy = pic.height - bottom_fade + y
        ad.line([(0, yy), (pw, yy)], fill=int(255 * (1 - y / bottom_fade) ** 1.4))
    if pw < W:  # a shrunk picture melts into the blurred copy at both sides
        side = Image.linear_gradient("L").rotate(90, expand=True).resize((60, pic.height))
        alpha.paste(Image.new("L", (60, pic.height), 0), (0, 0), side.transpose(Image.FLIP_LEFT_RIGHT))
        alpha.paste(Image.new("L", (60, pic.height), 0), (pw - 60, 0), side)
        alpha = Image.composite(alpha, Image.new("L", alpha.size, 0), alpha)
    canvas.paste(pic, ((W - pw) // 2, args.img_top), alpha)

    # darken the lower third further so the title always reads
    shade = gradient(W, H - 1150, [(0.0, (0, 0, 0)), (1.0, (0, 0, 0))])
    sm = Image.linear_gradient("L").resize((W, H - 1150)).point(lambda v: int(v * 0.8))
    canvas.paste(shade, (0, 1150), sm)

    # corners: channel-logo slot and production slot
    draw_plain(canvas, args.brand, ImageFont.truetype(LATIN, 30), 0, 44, (236, 214, 160), anchor_left=44)
    fs = font(SMALL_TH, 30)
    l, t, r, b = fs.getbbox(args.show)
    draw_plain(canvas, args.show, fs, 0, 40, (236, 214, 160), anchor_left=W - 44 - (r - l))

    tagline = args.tagline
    if tagline and not tagline.startswith(("“", '"')):
        tagline = f"“{tagline}”"  # lakorn taglines sit in quotes
    if tagline and args.tagline_top:
        draw_plain(canvas, tagline, font(SMALL_TH, 34), W / 2, 92, (245, 240, 230))
        tagline = ""

    y = args.title_top
    if args.logo:
        logo = logo_from_black(args.logo, 1000, args.logo_h)  # 260 keeps logo+English+airtime inside the 4:5 crop at --title-top 1215
        # CEO 2026-09-26: the title fills the space it has — not cramped, not too big, not too small.
        # Approved on taachang: 733x400 at --title-top 1095; the 476x260 default read as too small.
        if logo.height < 340 and logo.width < 0.6 * W:
            print(f"WARN: title logo {logo.width}x{logo.height} is small for the biggest element — raise --logo-h "
                  f"(~400) and lower --title-top so the block still ends above {FEED_BOTTOM}")
        if logo.width > W - 2 * 60:
            print(f"WARN: title logo {logo.width} px wide leaves under 60 px each side — lower --logo-h")
        x = (W - logo.width) // 2
        shadow = Image.new("L", canvas.size)
        shadow.paste(logo.getchannel("A"), (x, y + 6))
        # spread, then blur: a pale letter over a pale shirt still gets a dark halo
        halo = shadow.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(16))
        canvas.paste((0, 0, 0), (0, 0), halo.point(lambda v: min(255, int(v * 1.25))))
        canvas.paste(logo, (x, y), logo)
        y += logo.height + 14
    else:
        if not (args.line1 and args.line2):
            print("REFUSED: give --logo, or both --line1 and --line2", file=sys.stderr)
            return 2
        title_font = FONTS[args.font]
        f1 = fit(title_font, args.line1, 620, 92)
        y = draw_title(canvas, args.line1, f1, W / 2, y, SILVER, stroke=4, shadow=10) + 8
        f2 = fit(title_font, args.line2, 990, 170)
        y = draw_title(canvas, args.line2, f2, W / 2, y, GOLD, stroke=6, shadow=16) + 16
    if args.english:
        y = draw_plain(canvas, "  ".join(args.english.upper().split(" ")), ImageFont.truetype(LATIN, 30),
                       W / 2, y, (238, 206, 140)) + 16
    if tagline:
        y = draw_plain(canvas, tagline, font(SMALL_TH, 36), W / 2, y, (245, 240, 230)) + 10
    if args.cta:
        fc = font(SMALL_TH, 34)
        l, t, r, b = fc.getbbox(args.cta)
        pw, ph = (r - l) + 56, (b - t) + 26
        px, py = (W - pw) // 2, y + 8
        ImageDraw.Draw(canvas).rounded_rectangle((px, py, px + pw, py + ph), radius=ph // 2,
                                                 fill=(150, 20, 24), outline=(236, 196, 110), width=2)
        ImageDraw.Draw(canvas).text((px + 28 - l, py + 13 - t), args.cta, font=fc, fill=(255, 244, 220))
        y = py + ph
    if y > FEED_BOTTOM:
        print(f"WARN: title block ends at y={y}, below the 4:5 feed crop ({FEED_BOTTOM}) — lower --title-top")

    draw_plain(canvas, args.credits, font(SMALL_TH, 24), W / 2, H - 70, (190, 180, 165), shadow=3)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out)
    feed = args.out.with_name(args.out.stem + "-feed45.png")
    canvas.crop((0, FEED_TOP, W, FEED_BOTTOM)).save(feed)
    print(f"wrote {args.out} ({W}x{H}) + {feed.name}; title block y {args.title_top}..{y}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
