#!/usr/bin/env python3
"""MoonieX logo workflow node — reusable brand-mark stamping for any poster/image.

Two placements (import or CLI):
  stamp_footer(im)  -> MOONIEX gold wordmark, bottom-center      (use on logo-less posters)
  stamp_corner(im)  -> moon + MOONIEX vertical lockup, top-right (+2px drop shadow)

build_lockup() (re)builds the transparent vertical lockup from the brand source assets.
All functions take and return a PIL RGBA Image so they chain into any pipeline.

CLI:
  python scripts/mooniex_logo.py IMAGE.png corner            # -> IMAGE_logo.png
  python scripts/mooniex_logo.py IMAGE.png footer -o OUT.png
  python scripts/mooniex_logo.py --build-lockup              # regenerate lockup asset
"""
import os, argparse
from PIL import Image, ImageFilter

# brand source assets
MOON = "/Users/gob/MoonieXHQ/Projects/MoonieX/WebApp/public/brand/logo-mark.png"        # gold crescent+pagoda
WORDMARK = "/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/assets/mooniex-footer.png"  # gold MOONIEX wordmark
LOCKUP_CACHE = "/Users/gob/MoonieXHQ/Agents/Core/output/personal-brand/lockup-vertical.png"


def _trim(im):
    bb = im.getbbox()
    return im.crop(bb) if bb else im


def build_lockup(gap_ratio=0.12, save=LOCKUP_CACHE):
    """Vertical lockup: moon on top, MOONIEX below, transparent. Returns RGBA Image."""
    moon = _trim(Image.open(MOON).convert("RGBA"))
    wm = _trim(Image.open(WORDMARK).convert("RGBA"))
    mw = 900
    mn = moon.resize((mw, int(moon.height * mw / moon.width)))
    ww = int(mw * 0.92); wm2 = wm.resize((ww, int(wm.height * ww / wm.width)))
    gap = int(mn.height * gap_ratio)
    h = mn.height + gap + wm2.height
    out = Image.new("RGBA", (mw, h), (0, 0, 0, 0))
    out.paste(mn, ((mw - mn.width) // 2, 0), mn)
    out.paste(wm2, ((mw - wm2.width) // 2, mn.height + gap), wm2)
    if save:
        os.makedirs(os.path.dirname(save), exist_ok=True)
        out.save(save)
    return out


def _lockup():
    if os.path.exists(LOCKUP_CACHE):
        return _trim(Image.open(LOCKUP_CACHE).convert("RGBA"))
    return _trim(build_lockup())


def _drop_shadow(layer, sprite, x, y, blur=3, offsets=((3, 3), (2, 2))):
    sil = Image.composite(Image.new("RGBA", sprite.size, (0, 0, 0, 255)),
                          Image.new("RGBA", sprite.size, (0, 0, 0, 0)),
                          sprite.getchannel("A")).filter(ImageFilter.GaussianBlur(blur))
    for ox, oy in offsets:
        layer.paste(sil, (x + ox, y + oy), sil)
        layer.paste(sil, (x + ox, y + oy), sil)


def stamp_footer(im, width_ratio=0.20, bottom_pad=0.04, alpha=235):
    """MOONIEX wordmark, bottom-center (TradeTech-style footer)."""
    im = im.convert("RGBA"); W, H = im.size
    wm = _trim(Image.open(WORDMARK).convert("RGBA"))
    lw = int(W * width_ratio); lh = int(lw * wm.height / wm.width); wm = wm.resize((lw, lh))
    if alpha < 255:
        wm.putalpha(wm.getchannel("A").point(lambda v: int(v * alpha / 255)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.paste(wm, ((W - lw) // 2, H - lh - int(H * bottom_pad)), wm)
    im.alpha_composite(layer)
    return im


def stamp_corner(im, width_ratio=0.0775, right_pad=0.0225, top_pad=0.02, shadow=True):
    """Moon + MOONIEX vertical lockup, top-right, with a 2px dark drop shadow."""
    im = im.convert("RGBA"); W, H = im.size
    lk = _lockup()
    lw = int(W * width_ratio); lh = int(lw * lk.height / lk.width); lk = lk.resize((lw, lh))
    x = W - lw - int(W * right_pad); y = int(H * top_pad)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if shadow:
        _drop_shadow(layer, lk, x, y)
    layer.paste(lk, (x, y), lk)
    im.alpha_composite(layer)
    return im


PLACEMENTS = {"footer": stamp_footer, "corner": stamp_corner}


def apply(image_path, placement="corner", out=None):
    im = Image.open(image_path).convert("RGBA")
    if placement == "both":
        im = stamp_corner(stamp_footer(im))
    else:
        im = PLACEMENTS[placement](im)
    out = out or os.path.splitext(image_path)[0] + "_logo.png"
    im.convert("RGB").save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?")
    ap.add_argument("placement", nargs="?", default="corner", choices=["footer", "corner", "both"])
    ap.add_argument("-o", "--out")
    ap.add_argument("--build-lockup", action="store_true")
    args = ap.parse_args()
    if args.build_lockup:
        print("lockup ->", build_lockup().size, LOCKUP_CACHE); return
    if not args.image:
        ap.error("image required (or --build-lockup)")
    print("stamped ->", apply(args.image, args.placement, args.out))


if __name__ == "__main__":
    main()
