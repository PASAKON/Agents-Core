#!/usr/bin/env python3
"""Measure COMP matte envelopes and map them using template CSS.

Alpha is a silhouette, not a facial-landmark detector. The historical narrowest
row heuristic can stop ABOVE the mouth. Supply a visually reviewed --chin-row
(source pixels, inclusive) to extend its envelope conservatively. Results without
that bound are explicitly unverified and cannot select a production scale.

task-f35f2935: the HEAD-TOP envelope. For each lipsync take the minimum canvas y of
the avatar's top opaque row over EVERY frame of the range the cut can show (30 fps,
not 0.5 s steps: the head moves ~5 px a frame in the take's first second, and a
0.5 s sample read 111 where frame 0 is 104). That number places the COMP caption
pill: tools/bl_checker.py COMP_TAKES holds it, `python tools/bl_face_box.py ...`
regenerates it, and tests/test_bl_face_box.py pins the table against the committed
measurement (docs/reports/task-f35f2935/head-top.json).
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
CHIN_ROW = 1100   # source px, inclusive: below every chin seen (lip_a/b/c about 1020-1040) and above the shoulders' bulk
FPS = 30
# Take-relative [from, to) seconds of the matte frames the EP58 cut can actually show in a COMP beat: lip_a opens the
# video at its first frame (HOOK-1 is pulled back to the window start), lip_b's first COMP is MAIN-5 at 39.28
# (take 0.51 s), lip_c's first COMP is arm A SUMMARY-7 at 88.69 (take 7.85 s). Before those, the take's opening pose
# (head 100-250 px higher) is never on screen with a caption, so it must not place the pill.
USED_RANGES = {'lip_a': (0.0, 15.95), 'lip_b': (0.5, 17.15), 'lip_c': (7.8, 14.25)}


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


def canvas_y(src_y, geom):
    """Canvas y of a source row at the template's avatar scale (the transform canvas_box applies to y)."""
    return src_y * geom['scale'] + 1920 * (1 - geom['scale']) - geom['bottom']


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


def stream_alpha(path, start, end):
    """Yield (take_seconds, alpha) for every 30 fps frame of the matte in [start, end). One decoder process."""
    cmd = ['ffmpeg', '-v', 'error', '-threads', '2', '-ss', str(start), '-t', str(end - start),
           '-c:v', 'libvpx-vp9', '-i', str(path), '-vf', 'alphaextract,format=gray', '-f', 'rawvideo', '-']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    k = 0
    try:
        while True:
            raw = proc.stdout.read(1920 * 1080)
            if len(raw) < 1920 * 1080:
                break
            yield round(start + k / FPS, 4), np.frombuffer(raw, np.uint8).reshape(1920, 1080)
            k += 1
    finally:
        proc.stdout.close()
        proc.wait()
    if not k:
        raise ValueError(f'{path}: no alpha frames in [{start}, {end})')


def envelope_from_frames(frames, start, end, chin_row=CHIN_ROW, geom=None):
    """The avatar silhouette envelope over `frames`, an iterable of (take_seconds, alpha) -- see head_envelope().

    `top` is the minimum top opaque row (a row with more than 8 pixels over alpha 128) in source px; `source_bounds`
    is x0, top, x1, chin_row + 1 unioned over the frames (the head + neck + shoulder box the text_over_face gate
    judges). `min_top_0_5s` is the same minimum read at 0.5 s steps only, for comparison with the d4c1f234 sampling."""
    top, top_at, x0, x1, n, top_half = None, None, None, None, 0, None
    for t, alpha in frames:
        box, _ = alpha_bounds(alpha, chin_row)
        n += 1
        if top is None or box[1] < top:
            top, top_at = box[1], t
        x0 = box[0] if x0 is None else min(x0, box[0])
        x1 = box[2] if x1 is None else max(x1, box[2])
        if abs((t * 2) - round(t * 2)) < 1e-6 and (top_half is None or box[1] < top_half):
            top_half = box[1]
    if not n:
        raise ValueError('no alpha frames')
    out = dict(range=[start, end], frames=n, top=top, top_at=top_at, min_top_0_5s=top_half,
               source_bounds=[x0, top, x1, chin_row + 1])
    if geom:
        out['canvas_top'] = round(canvas_y(top, geom), 2)
    return out


def head_envelope(path, start, end, chin_row=CHIN_ROW, geom=None):
    """envelope_from_frames over every 30 fps frame of the matte in take-seconds [start, end)."""
    return envelope_from_frames(stream_alpha(path, start, end), start, end, chin_row, geom)


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
    parser.add_argument('--chin-row', type=int, default=CHIN_ROW,
                        help='reviewed conservative source-pixel lower bound; same framing across takes')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    geom = geometry(args.template)
    result = dict(geometry=geom, chin_row=args.chin_row, fps=FPS, chin_verified=False,
                  note='A supplied bound still requires visual review across every relevant frame.', takes={})
    for name in ('lip_a', 'lip_b', 'lip_c'):
        matte = args.matte_dir / f'{name}-matte.webm'
        used = head_envelope(matte, *USED_RANGES[name], chin_row=args.chin_row, geom=geom)
        whole = head_envelope(matte, 0.0, USED_RANGES[name][1], chin_row=args.chin_row, geom=geom)
        used['comp_box'] = canvas_box(used['source_bounds'], geom)
        used['ff_box'] = [used['source_bounds'][0], used['source_bounds'][1],
                          used['source_bounds'][2] - used['source_bounds'][0],
                          used['source_bounds'][3] - used['source_bounds'][1]]
        result['takes'][name] = dict(used=used, whole_take=dict(
            range=whole['range'], frames=whole['frames'], top=whole['top'], top_at=whole['top_at'],
            canvas_top=whole['canvas_top']))
        print(name, 'used', used['range'], 'top', used['top'], 'at', used['top_at'], '-> canvas', used['canvas_top'],
              '| whole take top', whole['top'], 'at', whole['top_at'], flush=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
