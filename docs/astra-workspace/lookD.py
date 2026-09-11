"""Look D — stylised/saturated variants on Astra's exact transform, plus a `lift` term.

Astra's shared-LUT-source.py has no way to raise the black floor: its shadow delta is
luma-neutralised, so it tints shadows without lifting them. The Grand Budapest reference
the CEO chose has milky, lifted blacks, so `lift` is added here. Everything else is
Astra's math, unchanged, so D stays comparable with A/B/C.
"""
import sys
import numpy as np
from PIL import Image

LUMA = np.array([.2126, .7152, .0722])

PARAMS = {
    # Astra's originals, for reference in the contact sheets
    'A_Quiet_Museum': dict(contrast=.20, density=.04, saturation=.95, lift=0.0,
                           shadow=[.017, -.001, -.012], mid=[.035, .006, -.042],
                           white=[-.040, .002, .045], white_start=.65, white_end=.90),

    # D1 "Confection" — the literal Grand Budapest structure:
    # high saturation, flat mid contrast, milky lifted blacks,
    # COOL/teal shadows against WARM pink-cream highlights (the complementary anchor).
    # This deliberately inverts the film's written "warm shadow, cold white".
    'D1_Confection': dict(contrast=.10, density=-.02, saturation=1.38, lift=.022,
                          shadow=[-.018, .002, .024], mid=[.030, .004, -.020],
                          white=[.032, .000, -.014], white_start=.60, white_end=.92),

    # D2 "Lacquer" — keeps the film's OWN identity (warm shadow, cool white) but loud:
    # saturation pushed harder than D1, contrast flattened, only a small lift.
    'D2_Lacquer': dict(contrast=.16, density=.00, saturation=1.45, lift=.012,
                       shadow=[.026, -.004, -.010], mid=[.050, .008, -.048],
                       white=[-.022, .002, .028], white_start=.70, white_end=.94),
}


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def transform(rgb, p):
    y = rgb @ LUMA
    chroma = np.max(rgb, axis=-1) - np.min(rgb, axis=-1)
    target = y + p['contrast'] * y * (1 - y) * (y - .45) - p['density'] * y * (1 - y)
    # NEW: raise the black floor for milky shadows, then re-seat chroma on it.
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
    # Astra's hue-preserving gamut compression, verbatim.
    yy = np.clip(v @ LUMA, 0, 1)
    d = v - yy[..., None]
    high = np.max(d, axis=-1)
    low = np.min(d, axis=-1)
    scale = np.ones_like(yy)
    scale = np.minimum(scale, np.divide(1 - yy, high, out=np.ones_like(yy), where=high > 1e-10))
    scale = np.minimum(scale, np.divide(-yy, low, out=np.ones_like(yy), where=low < -1e-10))
    return np.clip(yy[..., None] + d * scale[..., None], 0, 1)


def apply_to(path, look, out):
    img = np.asarray(Image.open(path).convert('RGB'), dtype=np.float64) / 255.0
    res = transform(img, PARAMS[look])
    Image.fromarray((res * 255 + .5).astype(np.uint8)).save(out)
    return out


def write_cube(look, out, n=65):
    b, g, r = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n),
                          np.linspace(0, 1, n), indexing='ij')
    grid = np.stack([r, g, b], axis=-1).reshape(-1, 3)
    values = transform(grid, PARAMS[look])
    assert np.isfinite(values).all() and values.min() >= 0 and values.max() <= 1
    with open(out, 'w', newline='\n') as f:
        f.write(f'TITLE "Sorry Sir {look}"\nLUT_3D_SIZE {n}\n'
                'DOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        np.savetxt(f, values, fmt='%.8f %.8f %.8f')
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'cube':
        for lk in ('D1_Confection', 'D2_Lacquer'):
            print(write_cube(lk, f'LUTs/{lk}.cube'))
    else:
        print(apply_to(sys.argv[1], sys.argv[2], sys.argv[3]))
