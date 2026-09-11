"""Per-shot balance — the node-01 layer, done by measurement instead of by hand.

The CEO's diagnosis was right: applying one LUT to every frame cannot reconcile shots that
started from different balances, and a shared look amplifies that drift rather than hiding it.
This is the missing layer. It is deliberately NOT a taste judgement — it measures where each
shot's neutrals sit, and pulls them toward a common point. Taste stays in the LUT on top.

Key safeguard: the balance is measured on LOW-CHROMA pixels only. A shot dominated by a red
coat must not be "corrected" until the coat goes grey — only its walls, skin-neutral and
concrete should drive the measurement. STRENGTH < 1 keeps deliberate colour alive.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SRC = sys.argv[1]
LUT = sys.argv[2] if len(sys.argv) > 2 else None
OUT = sys.argv[3] if len(sys.argv) > 3 else 'balanced.mp4'
STRENGTH = 0.75          # how far each shot is pulled toward the common neutral
CHROMA_MAX = 0.14        # pixels more colourful than this never drive the measurement
WORK = Path('sb'); WORK.mkdir(exist_ok=True)


def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def duration(p):
    return float(run(f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{p}"').stdout)


def cuts(p):
    out = run(f'ffmpeg -v info -y -i "{p}" -filter:v '
              f'"select=\'gt(scene,0.30)\',metadata=print:file=-" -f null - 2>/dev/null').stdout
    ts = [float(l.split('pts_time:')[1]) for l in out.splitlines() if 'pts_time:' in l]
    return ts


def shot_neutral(p, a, b):
    """Mean RGB of the near-neutral pixels across a few frames of one shot."""
    mids = [a + (b - a) * f for f in (0.25, 0.5, 0.75)]
    acc, n = np.zeros(3), 0
    for i, t in enumerate(mids):
        f = WORK / f'probe{i}.png'
        run(f'ffmpeg -v error -y -ss {t:.3f} -i "{p}" -frames:v 1 "{f}"')
        if not f.exists():
            continue
        img = np.asarray(Image.open(f).convert('RGB'), dtype=np.float64) / 255.0
        chroma = img.max(2) - img.min(2)
        y = img @ np.array([.2126, .7152, .0722])
        # near-neutral, and in the usable middle of the range
        m = (chroma < CHROMA_MAX) & (y > .12) & (y < .92)
        if m.sum() < 500:
            m = (y > .12) & (y < .92)
        acc += img[m].mean(0); n += 1
    return (acc / max(n, 1)) if n else np.array([.5, .5, .5])


def main():
    dur = duration(SRC)
    bounds = [0.0] + [t for t in cuts(SRC) if 0.4 < t < dur - 0.4] + [dur]
    shots = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
    shots = [s for s in shots if s[1] - s[0] > 0.20]
    print(f'{len(shots)} shots in {dur:.1f}s', flush=True)

    neutrals = [shot_neutral(SRC, a, b) for a, b in shots]
    weights = np.array([b - a for a, b in shots])
    target = np.average(np.array(neutrals), axis=0, weights=weights)   # the film's own common point
    print(f'common neutral target  R{target[0]:.3f} G{target[1]:.3f} B{target[2]:.3f}', flush=True)

    parts, report = [], []
    for i, ((a, b), nv) in enumerate(zip(shots, neutrals)):
        gain = np.clip(target / np.maximum(nv, 1e-4), 0.80, 1.25)
        gain = 1.0 + (gain - 1.0) * STRENGTH
        gain = gain / gain[1]            # hold green — shift colour, never exposure
        vf = (f'colorchannelmixer=rr={gain[0]:.5f}:gg={gain[1]:.5f}:bb={gain[2]:.5f}')
        if LUT:
            vf += f',lut3d={LUT}:interp=trilinear'
        seg = WORK / f'p{i:04d}.mp4'
        run(f'ffmpeg -v error -y -ss {a:.3f} -to {b:.3f} -i "{SRC}" -vf "{vf}" '
            f'-c:v libx264 -crf 18 -preset faster -pix_fmt yuv420p -an "{seg}"')
        parts.append(seg)
        drift = float(np.abs(gain - 1).max())
        report.append(dict(shot=i, start=round(a, 2), end=round(b, 2),
                           gain=[round(float(g), 4) for g in gain], drift=round(drift, 4)))
        if drift > 0.04:
            print(f'  shot {i:3d} {a:6.2f}-{b:6.2f}  gain '
                  f'{gain[0]:.3f}/{gain[1]:.3f}/{gain[2]:.3f}  DRIFT {drift:.3f}', flush=True)

    lst = WORK / 'list.txt'
    lst.write_text(''.join(f"file '{p.resolve()}'\n" for p in parts))
    run(f'ffmpeg -v error -y -f concat -safe 0 -i "{lst}" -c copy "{WORK}/v.mp4"')
    run(f'ffmpeg -v error -y -i "{WORK}/v.mp4" -i "{SRC}" -map 0:v -map 1:a? '
        f'-c:v copy -c:a aac -b:a 160k -shortest "{OUT}"')
    Path(OUT + '.shots.json').write_text(json.dumps(report, indent=1))
    worst = sorted(report, key=lambda r: -r['drift'])[:8]
    print(f"\nwrote {OUT}")
    print("biggest corrections (these are the shots a human should look at):")
    for r in worst:
        print(f"  shot {r['shot']:3d} at {r['start']:6.2f}s  drift {r['drift']:.3f}")


main()
