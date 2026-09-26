"""The 16:9 cover for THE SHADOW BELOW, laid out like the «Sorry, Sir» cover (CEO 2026-09-27).

    python3 cover.py --bg cover-bg.png --logo title-logo.png --watermark Watermark.png [--out cover.png]

The background and the title lettering are ChatGPT images (tools/chatgpt_images.py): the background from the N10
shadow-from-above frame at 7 s, the title drawn on pure black the way the ละครสั้นคุณธรรม covers are made and lifted
off the black with tools/lakorn_poster.logo_from_black. Only the platform watermark and the "AI SHORT FILM" label are
added here, as on «Sorry, Sir» (Drive Sorry, Sir/Poster/SorrySir-YouTube-Thumbnail-1280x720-v2.jpg), measured at
1280x720: title top-centre, x 278-994 (56% of the width), top at 8.75%; a thin, widely spaced line under it;
"AI SHORT FILM" top-left at x 5.5%, y 3.75%, 20% wide, bold caps with a 2 px hard dark shadow; the festival mark
lower right, 20% wide, its centre at 61% of the height, 11% in from the right edge, on empty picture. The TopView
mark keeps its official colours (a challenge requirement), unlike the «Sorry, Sir» laurel, which was recoloured.
"""
import argparse, importlib.util
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
HERE = Path(__file__).resolve().parent
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BOOK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def logo_from_black(path, max_w, max_h):
    spec = importlib.util.spec_from_file_location("lp", HERE.parents[2] / "tools" / "lakorn_poster.py")
    lp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lp)
    return lp.logo_from_black(path, max_w, max_h)


def spaced(draw, xy, text, font, fill, tracking, anchor_centre=False, shadow=None):
    """Draw text letter by letter with extra tracking (px); returns its width."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy
    if anchor_centre:
        x -= total / 2
    for ch, w in zip(text, widths):
        if shadow:
            draw.text((x + 2, y + 2), ch, font=font, fill=shadow)
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bg", required=True)
    ap.add_argument("--logo", required=True)
    ap.add_argument("--watermark", required=True)
    ap.add_argument("--subtitle", default="ILAG STUDIO")
    ap.add_argument("--label", default="AI SHORT FILM")
    ap.add_argument("--wm-centre-y", type=float, default=0.61, help="watermark centre as a fraction of the height")
    ap.add_argument("--out", default="cover.png")
    a = ap.parse_args()

    img = Image.open(a.bg).convert("RGB")
    k = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    img = img.convert("RGBA")

    logo = logo_from_black(a.logo, 0.56 * W, 0.30 * H)
    lx, ly = (W - logo.width) // 2, round(0.0875 * H)
    img.alpha_composite(logo, (lx, ly))

    d = ImageDraw.Draw(img)
    sub = ImageFont.truetype(BOOK, round(0.028 * H))
    spaced(d, (W / 2, ly + logo.height + round(0.035 * H)), a.subtitle, sub, (200, 208, 210, 255),
           tracking=round(0.012 * W), anchor_centre=True)

    lab = ImageFont.truetype(BOLD, round(0.022 * H * 1.35))
    spaced(d, (round(0.055 * W), round(0.0375 * H)), a.label, lab, (234, 246, 244, 255),
           tracking=round(0.0045 * W), shadow=(10, 18, 22, 255))

    wm = Image.open(a.watermark).convert("RGBA")
    ww = round(0.20 * W)
    wm = wm.resize((ww, round(wm.height * ww / wm.width)), Image.LANCZOS)
    img.alpha_composite(wm, (W - round(0.11 * W) - ww, round(a.wm_centre_y * H - wm.height / 2)))

    img.convert("RGB").save(a.out)
    print(a.out, img.size)


if __name__ == "__main__":
    main()
