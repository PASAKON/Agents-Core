#!/usr/bin/env python3
"""Measure COMP matte envelopes and map them using template CSS.

Alpha is a silhouette, not a facial-landmark detector. The historical narrowest
row heuristic can stop ABOVE the mouth. Supply a visually reviewed --chin-row
(source pixels, inclusive) to extend its envelope conservatively. Results without
that bound are explicitly unverified and cannot select a production scale.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import subprocess

import numpy as np

TEMPLATE = Path(__file__).resolve().parents[1] / '.claude/skills/CMO_Procedure_BlackLiquidity_Cut/template/index.html'
WINDOWS = {'lip_a': (0.0, 15.9, 0.0), 'lip_b': (39.28, 55.9, 38.77), 'lip_c': (88.69, 95.0, 80.84)}


def geometry(template=TEMPLATE):
    css = re.search(r'\.avatar-comp\s*\{([^}]+)\}', Path(template).read_text())
    if not css:
        raise ValueError('missing .avatar-comp CSS rule')
    body = css[1]
    height = re.search(r'\bheight:\s*([\d.]+)%', body)
    translate = re.search(r'translateX\(\s*(-?[\d.]+)%\)', body)
    if not height or not translate:
        raise ValueError('expected percentage height and translateX')
    def px(name):
        match = re.search(rf'\b{name}:\s*(-?[\d.]+)(?:px)?\s*;', body)
        if not match:
            raise ValueError(f'expected pixel {name}')
        return float(match[1])
    return dict(scale=float(height[1]) / 100, translate_x=float(translate[1]) / 100,
                left=px('left'), bottom=px('bottom'))


def canvas_box(bounds, geom, scale=None):
    """Source x0,y0,x1,y1 (exclusive end); round OUTWARD for a safe gate."""
    s = geom['scale'] if scale is None else scale
    if not 0 < s <= 1:
        raise ValueError('scale must be in (0, 1]')
    dx = geom['left'] + geom['translate_x'] * 1080 * s
    dy = 1920 * (1 - s) - geom['bottom']
    x0, y0, x1, y1 = bounds
    a, b = math.floor(x0 * s + dx), math.floor(y0 * s + dy)
    return [a, b, math.ceil(x1 * s + dx) - a, math.ceil(y1 * s + dy) - b]


def alpha_bounds(alpha, chin_row=None):
    mask = alpha > 128
    rows = mask.sum(axis=1)
    ys = np.flatnonzero(rows > 8)
    if not len(ys):
        raise ValueError('empty matte')
    top = int(ys[0])
    start, end = top + 120, min(top + 520, len(rows))
    if start >= end or not np.all(rows[start:end] > 0):
        raise ValueError('invalid head profile')
    neck = start + int(np.argmin(rows[start:end]))
    bottom = max(neck + 1, chin_row + 1 if chin_row is not None else 0)
    if bottom > alpha.shape[0] or bottom <= top:
        raise ValueError('chin row outside matte')
    cols = np.flatnonzero(mask[top:bottom].any(axis=0))
    return [int(cols[0]), top, int(cols[-1]) + 1, bottom], neck


def measure(path, window, chin_row=None):
    a, b, offset = window
    bounds, profiles = [], []
    for absolute in np.arange(a, b, .5):
        relative = round(float(absolute - offset), 3)
        result = subprocess.run(['ffmpeg', '-v', 'error', '-threads', '1', '-c:v', 'libvpx-vp9',
            '-ss', str(relative), '-i', str(path), '-frames:v', '1', '-vf',
            'format=rgba,alphaextract,format=gray', '-f', 'rawvideo', '-'], capture_output=True, check=True)
        if len(result.stdout) != 1920 * 1080:
            raise ValueError(f'{path}: missing alpha frame at {relative}')
        alpha = np.frombuffer(result.stdout, np.uint8).reshape(1920, 1080)
        box, neck = alpha_bounds(alpha, chin_row)
        bounds.append(box)
        rows = (alpha > 128).sum(axis=1)
        profiles.append(dict(absolute=round(float(absolute), 3), legacy_neck=neck,
                             widths_700_to_1150=[int(rows[y]) for y in range(700, 1151, 25)]))
    arr = np.array(bounds)
    return [int(arr[:, 0].min()), int(arr[:, 1].min()), int(arr[:, 2].max()), int(arr[:, 3].max())], profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', type=Path, default=TEMPLATE)
    parser.add_argument('--matte-dir', type=Path, required=True)
    parser.add_argument('--chin-row', type=int, help='reviewed conservative source-pixel lower bound; same framing across takes')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    geom = geometry(args.template)
    result = dict(geometry=geom, chin_row=args.chin_row, sampling_seconds=.5,
                  chin_verified=False, note='A supplied bound still requires visual review across every relevant frame.', takes={})
    for name, window in WINDOWS.items():
        bounds, profiles = measure(args.matte_dir / f'{name}-matte.webm', window, args.chin_row)
        candidates = {}
        for s in (.60, .64, .68):
            box = canvas_box(bounds, geom, s)
            candidates[str(s)] = dict(box=box, bottom=box[1]+box[3], clearance=1218-box[1]-box[3],
                                      geometry_clears=box[1]+box[3] <= 1198)
        result['takes'][name] = dict(window=window, source_bounds=bounds, template_box=canvas_box(bounds, geom),
                                     candidates=candidates, profiles=profiles)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    for name, take in result['takes'].items():
        print(name, take['source_bounds'], take['candidates'])


if __name__ == '__main__':
    main()
