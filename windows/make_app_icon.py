#!/usr/bin/env python3
"""make_app_icon.py -- the Cookie Run Script app icon, drawn rather than cropped.

Built instead of cropping the game's art for two reasons that both matter. The
art is Devsisters' and this is our tool, not theirs; and a crop off a screenshot
arrives at whatever resolution it happened to be, with soft edges, and turns to
mush at the 16 px the Windows taskbar actually shows.

Drawn at 1024 and downsampled with LANCZOS, every size from 16 to 256 stays
crisp, and the palette can be changed in one place.

**The constraint that drives every decision here: it has to read at 16 px.**
At that size a picture is a silhouette and two or three colours, nothing more.
So the design is one unmistakable shape (the gingerbread runner, mid-stride)
against a hot oven circle, with a single cyan visor slash that says "machine".
The circuit traces and rim light are for 128 px and up; they vanish politely
below that instead of turning into noise.

    python make_app_icon.py [--out DIR]
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

S = 1024                      # draw big, downsample later
SIZES = [16, 24, 32, 48, 64, 128, 256]

# Cookie Run Classic runs warm: oven light behind a gingerbread body. The cyan
# is the only cold colour on the icon, which is what makes it read as the "bot"
# part rather than just another cookie.
# First attempt put a mid-brown cookie on a mid-orange glow. Same hue family,
# so at 16 px the silhouette dissolved into the background and all that survived
# was the cyan slash. Contrast is not a finishing touch on an icon, it is the
# whole readability budget.
#
# So: DARK ground, BRIGHT cookie. A Windows taskbar is dark, which makes this
# the high-contrast direction as well as the pretty one.
OVEN_HOT = (255, 148, 36)      # the glow behind him, kept tight
OVEN_DEEP = (26, 14, 18)       # near-black, not brown
DOUGH = (247, 190, 120)        # bright enough to hold its own against the glow
DOUGH_DARK = (196, 128, 66)
KEYLINE = (40, 20, 12)         # the outline that makes it survive downsampling
ICING = (255, 245, 228)
CYAN = (86, 236, 255)


def radial(size, inner, outer):
    """Oven glow. Done by hand rather than with a gradient helper so the falloff
    can be squared -- a linear falloff looks like a flat disc at small sizes."""
    img = Image.new("RGB", (size, size), outer)
    d = ImageDraw.Draw(img)
    steps = 140
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(size * 0.58 * t)
        f = (1 - t) ** 1.7
        c = tuple(int(outer[k] + (inner[k] - outer[k]) * f) for k in range(3))
        d.ellipse([size // 2 - r, size // 2 - r, size // 2 + r, size // 2 + r], fill=c)
    return img


def limb(d, pts, width, fill):
    d.line(pts, fill=fill, width=width, joint="curve")
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - width // 2, p[1] - width // 2,
                   p[0] + width // 2, p[1] + width // 2], fill=fill)


def draw_runner(d, cx, cy, k, body, dark, keyline):
    """Gingerbread man, mid-stride, facing right.

    Two things make this read rather than blob, and the first attempt had
    neither. The head must sit ON the torso with a visible neck, not sink into
    it -- overlapping them made one shape with a bump. And every part gets a
    KEYLINE: a dark stroke under each limb, drawn slightly fatter first. Without
    it, downsampling averages a bright limb into a bright background and the
    pose disappears below 48 px.

    Proportions are the giveaway for this game: head nearly a third of the
    height, limbs short and thick. Human proportions stop reading as Cookie Run
    at any size.
    """
    def lb(pts, w, fill):
        d.line(pts, fill=keyline, width=int(w * 1.34), joint="curve")
        for p in (pts[0], pts[-1]):
            r = int(w * 0.67)
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=keyline)
        d.line(pts, fill=fill, width=w, joint="curve")
        for p in (pts[0], pts[-1]):
            r = w // 2
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill)

    head_r = int(210 * k)
    hy = cy - int(250 * k)
    aw, lw = int(86 * k), int(96 * k)

    # behind the body: trailing arm and trailing leg
    lb([(cx - int(30 * k), cy - int(70 * k)), (cx - int(250 * k), cy + int(40 * k))], aw, dark)
    lb([(cx - int(20 * k), cy + int(150 * k)), (cx - int(215 * k), cy + int(295 * k))], lw, dark)

    # torso, with its own keyline
    tx0, ty0, tx1, ty1 = (cx - int(120 * k), cy - int(90 * k),
                          cx + int(120 * k), cy + int(190 * k))
    g = int(14 * k)
    d.rounded_rectangle([tx0 - g, ty0 - g, tx1 + g, ty1 + g], radius=int(110 * k), fill=keyline)
    d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=int(100 * k), fill=body)

    # in front: driving leg and leading arm
    lb([(cx + int(30 * k), cy + int(150 * k)), (cx + int(170 * k), cy + int(190 * k)),
        (cx + int(150 * k), cy + int(330 * k))], lw, body)
    lb([(cx + int(40 * k), cy - int(60 * k)), (cx + int(265 * k), cy - int(170 * k))], aw, body)

    # head last, sitting clear of the torso with a real neck gap
    d.ellipse([cx - head_r - g, hy - head_r - g, cx + head_r + g, hy + head_r + g], fill=keyline)
    d.ellipse([cx - head_r, hy - head_r, cx + head_r, hy + head_r], fill=body)
    return head_r, hy


def build(out_dir: Path):
    img = radial(S, OVEN_HOT, OVEN_DEEP).convert("RGBA")
    d = ImageDraw.Draw(img)

    cx, cy, k = S // 2, int(S * 0.55), S / 1024 * 1.12
    head_r, hy = draw_runner(d, cx, cy, k, DOUGH, DOUGH_DARK, KEYLINE)

    # The circuit traces that were here are gone. They were invisible below
    # 128 px and turned to speckle in the downsample, which is worse than
    # absent: an icon is judged at the size it is shown, not the size it is
    # drawn.
    # THE identity mark: one cyan visor across the eyes. This is the whole icon
    # at 16 px -- orange disc, dark cookie, cyan slash.
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    vx0, vx1 = cx - int(head_r * 0.92), cx + int(head_r * 0.98)
    vy = hy - int(8 * k)
    gd.rounded_rectangle([vx0, vy - int(30 * k), vx1, vy + int(30 * k)],
                         radius=int(28 * k), fill=CYAN + (255,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(int(22 * k))))
    d.rounded_rectangle([vx0, vy - int(26 * k), vx1, vy + int(26 * k)],
                        radius=int(24 * k), fill=CYAN)

    # Icing rim on the lit side, the detail that says "cookie" rather than "man"
    d.arc([cx - head_r, hy - head_r, cx + head_r, hy + head_r],
          start=155, end=250, fill=ICING, width=max(2, int(12 * k)))

    out_dir.mkdir(parents=True, exist_ok=True)
    master = out_dir / "app_icon_1024.png"
    img.convert("RGB").save(master)

    sizes = [img.convert("RGB").resize((n, n), Image.LANCZOS) for n in SIZES]
    ico = out_dir / "app_icon.ico"
    sizes[-1].save(ico, format="ICO", sizes=[(n, n) for n in SIZES])

    # A contact sheet at real scale, because the only honest way to judge an
    # icon is to look at the size it will actually be seen at.
    sheet = Image.new("RGB", (sum(SIZES) + 20 * len(SIZES) + 20, 300), (32, 32, 36))
    x = 20
    for n, im in zip(SIZES, sizes):
        sheet.paste(im, (x, 150 - n // 2))
        x += n + 20
    sheet.save(out_dir / "app_icon_sheet.png")
    print(f"wrote {master.name}, {ico.name} ({'/'.join(map(str, SIZES))}), app_icon_sheet.png")
    return ico


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"C:\Users\UsEr\cookierun-bot\assets")
    a = ap.parse_args()
    build(Path(a.out))
