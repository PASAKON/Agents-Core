"""THE SHADOW BELOW colour looks: custom 3D LUTs applied with FFmpeg, the way «Sorry, Sir» was graded (CEO 2026-09-27:
"เกรดสีด้วยอะไร -> คุณไงทำให้ ใช้อันนี้ทำ", pointing at its credit line "Custom 3D LUT · FFmpeg").

    python3 looks.py cube [--n 33]                 # writes LUTs/TSB_<look>.cube
    python3 looks.py sheet OUT.png FRAME.png ...   # rows = frames, columns = original + every look
    ffmpeg -i cut.mp4 -vf "lut3d=LUTs/TSB_Abyss.cube:interp=trilinear" -c:v libx264 -crf 17 -pix_fmt yuv420p \
           -c:a copy graded.mp4

The transform is «Sorry, Sir»'s (docs/astra-workspace/looks5.py: contrast, density, saturation, lift, and luma-neutral
shadow / mid / white tints), so the two films are graded by the same machine. Set interp=trilinear explicitly
(docs/decisions/look-parked-20260911.md): ffmpeg defaults to tetrahedral.

This film has two worlds, bright turquoise day and a black storm lit only by the child's gold glow, and the raw Wan3
clips read a little rendered. All three looks keep the gold warm (it is the story's only light) and differ in how far
they pull the rest toward film.
"""
import importlib.util, os, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_spec = importlib.util.spec_from_file_location(
    "looks5", Path(__file__).resolve().parents[2] / "astra-workspace" / "looks5.py")
L5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L5)

LOOKS = {
    # Abyss: deep-sea teal in the shadows and mids, warm highlights so the gold glow stands out; a little less colour.
    "Abyss": dict(contrast=.18, density=.03, saturation=.90, lift=.012,
                  shadow=[-.040, .008, .036], mid=[-.024, .004, .026],
                  white=[.020, .006, -.020], white_start=.60, white_end=.90),
    # Moonlight: restrained and silver, the most "photographed" of the three; deep blacks, least colour.
    "Moonlight": dict(contrast=.22, density=.05, saturation=.70, lift=.008,
                      shadow=[-.020, -.002, .036], mid=[-.012, .000, .020],
                      white=[-.016, .002, .022], white_start=.62, white_end=.92),
    # Glow: rich and punchy, cyan shadows against gold mids and highlights, blacks almost unlifted.
    "Glow": dict(contrast=.24, density=.00, saturation=1.30, lift=.004,
                 shadow=[-.035, .010, .028], mid=[.030, .010, -.030],
                 white=[.035, .012, -.035], white_start=.58, white_end=.90),
}


def apply(img, look):
    rgb = np.asarray(img.convert("RGB"), dtype=np.float64) / 255.0
    return Image.fromarray((L5.transform(rgb, LOOKS[look]) * 255 + .5).astype(np.uint8))


def cube(look, out, n):
    b, g, r = np.meshgrid(*(np.linspace(0, 1, n),) * 3, indexing="ij")
    vals = L5.transform(np.stack([r, g, b], axis=-1).reshape(-1, 3), LOOKS[look])
    assert np.isfinite(vals).all() and vals.min() >= 0 and vals.max() <= 1
    with open(out, "w", newline="\n") as f:
        f.write(f'TITLE "THE SHADOW BELOW {look}"\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        np.savetxt(f, vals, fmt="%.6f %.6f %.6f")


def sheet(out, frames, cell=(480, 270)):
    cols = ["Original"] + list(LOOKS)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    s = Image.new("RGB", (cell[0] * len(cols), cell[1] * len(frames) + 34), (20, 20, 20))
    d = ImageDraw.Draw(s)
    for c, name in enumerate(cols):
        d.text((c * cell[0] + cell[0] / 2, 17), f"{c}. {name}" if c else name, font=font, fill=(240, 240, 240),
               anchor="mm")
    for r, f in enumerate(frames):
        src = Image.open(f).convert("RGB").resize(cell, Image.LANCZOS)
        for c, name in enumerate(cols):
            s.paste(src if c == 0 else apply(src, name), (c * cell[0], 34 + r * cell[1]))
    s.save(out)
    print(out, s.size)


if __name__ == "__main__":
    if sys.argv[1] == "cube":
        n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 33
        os.makedirs("LUTs", exist_ok=True)
        for lk in LOOKS:
            cube(lk, f"LUTs/TSB_{lk}.cube", n)
            print(f"LUTs/TSB_{lk}.cube")
    elif sys.argv[1] == "sheet":
        sheet(sys.argv[2], sys.argv[3:])
