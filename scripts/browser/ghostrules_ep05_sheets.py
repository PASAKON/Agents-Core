#!/usr/bin/env python3
"""Numbered contact sheets (40 per sheet) of the EP5 plates (task-ed742f4b).
Run with the Core venv (needs Pillow):
  .venv/bin/python scripts/browser/ghostrules_ep05_sheets.py --plates <dir> --out <dir>
Missing plates show as a grey 'MISSING' tile so gaps are visible."""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompts", default="/opt/MoonieXHQ/Work/ghostrules-full/ep05/plates_prompts/plates_all.json")
    a = ap.parse_args()
    names = [x["name"] for x in json.load(open(a.prompts, encoding="utf-8"))]
    cols, rows, tw, th = 8, 5, 240, 135
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
    for si in range(0, len(names), cols * rows):
        chunk = names[si:si + cols * rows]
        sheet = Image.new("RGB", (cols * tw, rows * (th + 20)), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, nm in enumerate(chunk):
            x, y = (i % cols) * tw, (i // cols) * (th + 20)
            p = Path(a.plates) / f"{nm}.png"
            if p.exists():
                im = Image.open(p).convert("RGB").resize((tw, th))
                sheet.paste(im, (x, y + 20))
            else:
                d.rectangle([x, y + 20, x + tw - 1, y + 20 + th - 1], fill=(70, 70, 70))
                d.text((x + 70, y + 80), "MISSING", fill=(255, 120, 120), font=font)
            d.text((x + 3, y + 2), f"{si + i + 1} {nm}", fill=(255, 255, 255), font=font)
        out = Path(a.out) / f"EP05-plates-sheet-{si // (cols * rows) + 1}.jpg"
        sheet.save(out, quality=85)
        print(out)

if __name__ == "__main__":
    main()
