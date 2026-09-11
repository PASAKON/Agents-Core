"""Five genuinely different directions, not five intensities of one.

Built on Astra's transform (shared-LUT-source.py) plus the `lift` term added in lookD.py.
The CEO's note — that D2 amounts to "tint it orange" — is correct, and it is only one of
several ways to read the Grand Budapest reference. In particular V3 Vitrine tints nothing:
it leaves the architecture neutral and lets the costumes carry all the colour, which is
closer to how Anderson's interiors actually work.
"""
import sys
import numpy as np
from PIL import Image

LUMA = np.array([.2126, .7152, .0722])

LOOKS = {
 # 1 — the one already seen. Warm amber everywhere, high chroma.
 'V1_Lacquer': dict(contrast=.16, density=.00, saturation=1.45, lift=.012,
                    shadow=[.026, -.004, -.010], mid=[.050, .008, -.048],
                    white=[-.022, .002, .028], white_start=.70, white_end=.94),

 # 2 — Grand Budapest structure: teal shadows vs pink-cream highlights.
 'V2_Confection': dict(contrast=.10, density=-.02, saturation=1.38, lift=.022,
                       shadow=[-.018, .002, .024], mid=[.030, .004, -.020],
                       white=[.032, .000, -.014], white_start=.60, white_end=.92),

 # 3 — NO TINT AT ALL. Neutral/slightly cool architecture, chroma pushed hardest
 #     of the five. The room stays a white box; the coats do the work.
 'V3_Vitrine': dict(contrast=.14, density=.01, saturation=1.62, lift=.014,
                    shadow=[-.006, .001, .008], mid=[.004, .001, -.006],
                    white=[-.030, .002, .034], white_start=.62, white_end=.92),

 # 4 — the hotel exterior: everything leans rose/magenta, greens pulled toward pink.
 'V4_RoseHotel': dict(contrast=.12, density=-.01, saturation=1.40, lift=.020,
                      shadow=[.014, -.010, .012], mid=[.046, -.012, .018],
                      white=[.038, -.008, .010], white_start=.58, white_end=.90),

 # 5 — faded-poster / Asteroid City: olive-gold mids, magenta shadows, flattest curve.
 'V5_BitterAlmond': dict(contrast=.08, density=-.03, saturation=1.34, lift=.030,
                         shadow=[.018, -.008, .014], mid=[.030, .030, -.052],
                         white=[.006, .014, -.026], white_start=.64, white_end=.94),
}


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def transform(rgb, p):
    y = rgb @ LUMA
    chroma = np.max(rgb, axis=-1) - np.min(rgb, axis=-1)
    target = y + p['contrast'] * y * (1 - y) * (y - .45) - p['density'] * y * (1 - y)
    lift = p.get('lift', 0.0)
    target = target * (1 - lift) + lift
    v = target[..., None] + (rgb - y[..., None]) * p['saturation']
    shadow = smooth(0, .10, y) * (1 - smooth(.12, .38, y))
    white = smooth(p['white_start'], p['white_end'], y) * (1 - .5 * smooth(.08, .35, chroma))
    mid = (np.exp(-((y - .43) / .28) ** 2) * (1 - smooth(.72, .94, y))
           * (1 - .25 * smooth(.25, .65, chroma)) * smooth(0, .10, y))
    for zone, key in [(shadow, 'shadow'), (mid, 'mid'), (white, 'white')]:
        delta = np.array(p[key])
        delta = delta - (delta @ LUMA)
        v = v + zone[..., None] * delta
    yy = np.clip(v @ LUMA, 0, 1)
    d = v - yy[..., None]
    high, low = np.max(d, axis=-1), np.min(d, axis=-1)
    scale = np.ones_like(yy)
    scale = np.minimum(scale, np.divide(1 - yy, high, out=np.ones_like(yy), where=high > 1e-10))
    scale = np.minimum(scale, np.divide(-yy, low, out=np.ones_like(yy), where=low < -1e-10))
    return np.clip(yy[..., None] + d * scale[..., None], 0, 1)


def cube(look, out, n=65):
    b, g, r = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n),
                          np.linspace(0, 1, n), indexing='ij')
    grid = np.stack([r, g, b], axis=-1).reshape(-1, 3)
    vals = transform(grid, LOOKS[look])
    assert np.isfinite(vals).all() and vals.min() >= 0 and vals.max() <= 1
    with open(out, 'w', newline='\n') as f:
        f.write(f'TITLE "Sorry Sir {look}"\nLUT_3D_SIZE {n}\n'
                'DOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        np.savetxt(f, vals, fmt='%.8f %.8f %.8f')


if __name__ == '__main__':
    if sys.argv[1] == 'cube':
        import os
        os.makedirs('LUTs', exist_ok=True)
        for lk in LOOKS:
            cube(lk, f'LUTs/{lk}.cube')
            print(f'LUTs/{lk}.cube')
    else:
        src, look, out = sys.argv[1:4]
        img = np.asarray(Image.open(src).convert('RGB'), dtype=np.float64) / 255.0
        Image.fromarray((transform(img, LOOKS[look]) * 255 + .5).astype(np.uint8)).save(out)
        print(out)
