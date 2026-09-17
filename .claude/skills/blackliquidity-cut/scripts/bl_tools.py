#!/usr/bin/env python3
"""bl_tools.py — the checks that make a BLACK LIQUIDITY cut reproducible.

Every rule in here started life as a defect that a human eye caught and the
build gates did not. They are in a script, not in prose, because a rule that
relies on the author remembering it gets skipped.

  offsets   where each lipsync part REALLY sits in the master audio
  safearea  the y range on a clip where text will not cover the face
  verify    final gate on a rendered mp4: duration, fps, audio lag, seating
  sheet     contact sheet of N frames — read one image, not 4000

Only numpy + Pillow + ffmpeg/ffprobe. No venv needed.
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image


# ----------------------------------------------------------------- helpers
def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def pcm(src, ss=None, dur=None, rate=16000):
    cmd = ["ffmpeg", "-v", "error"]
    if ss is not None:
        cmd += ["-ss", f"{ss:.3f}"]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-i", src, "-vn", "-ar", str(rate), "-ac", "1", "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(float)


def nrm(a):
    return (a - a.mean()) / (a.std() + 1e-9)


def envelope(a, win=200):
    n = len(a) // win
    if n < 2:
        return np.zeros(1)
    e = np.abs(a[: n * win].reshape(n, win)).mean(axis=1)
    return nrm(e)


def probe(path):
    out = sh(["ffprobe", "-v", "error", "-show_entries",
              "stream=codec_type,width,height,r_frame_rate,nb_frames",
              "-show_entries", "format=duration", "-of", "json", path])
    return json.loads(out) if out.strip() else {}


def frame(src, t, w=216, h=384):
    tmp = "/tmp/_bl_frame.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", src,
                    "-frames:v", "1", "-update", "1", "-vf", f"scale={w}:{h}",
                    "-q:v", "2", tmp], check=True)
    return np.asarray(Image.open(tmp).convert("RGB")).astype(int)


# ------------------------------------------------------------------ faces
def face_box(rgb):
    """Bounding box of the speaker's face, in SOURCE pixels (1080x1920 assumed).

    Skin detection has to reject the red trading-chart plates these clips use:
    a candle has R-G around 140, skin around 40. Getting that wrong makes the
    'face' the whole frame and the safe area meaningless.
    """
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    skin = ((R > 95) & (R < 240) & (R - G > 12) & (R - G < 70) &
            (G - B > 8) & (G - B < 60) & (R - B > 28))
    colcount = skin.sum(axis=0)
    cols = np.where(colcount > 3)[0]
    if len(cols) < 4:
        return None
    runs, cur = [], [cols[0]]
    for c in cols[1:]:
        if c - cur[-1] <= 2:
            cur.append(c)
        else:
            runs.append(cur); cur = [c]
    runs.append(cur)
    run = max(runs, key=len)
    sub = skin[:, run[0]:run[-1] + 1]
    ys = np.where(sub.any(axis=1))[0]
    if not len(ys):
        return None
    sx, sy = 1080 / rgb.shape[1], 1920 / rgb.shape[0]

    # The skin blob runs face -> neck -> open collar, so its bottom is nowhere
    # near the chin. The face is wide and the neck is narrow: walk down from the
    # widest row and call it the chin where the width drops under 60% of that.
    width = sub.sum(axis=1)
    widest = int(np.argmax(width))
    thresh = width[widest] * 0.60
    chin = ys.max()
    for r in range(widest, ys.max() + 1):
        if width[r] < thresh:
            chin = r
            break
    return dict(x0=int(run[0] * sx), x1=int((run[-1] + 1) * sx),
                y0=int(ys.min() * sy), y1=int(ys.max() * sy),
                chin=int(chin * sy))


def cmd_safearea(a):
    """Where may a text block sit on this clip without crossing the face?"""
    if a.at:
        times = [float(t) for t in a.at.split(",")]
    else:
        dur = float(probe(a.clip)["format"]["duration"])
        times = [dur * f for f in (0.1, 0.3, 0.5, 0.7, 0.9)]
    chins = []
    for t in times:
        b = face_box(frame(a.clip, t))
        if not b:
            print(f"  t={t:6.2f}s  no face found"); continue
        chins.append(b["chin"])
        print(f"  t={t:6.2f}s  skin y{b['y0']:4d}-{b['y1']:4d}   CHIN y{b['chin']:4d}   x{b['x0']:4d}-{b['x1']:4d}")
    if not chins:
        print("\n  no face on this clip — text may sit anywhere")
        return 0
    chin = max(chins)
    print(f"\n  lowest chin across samples : y={chin}")
    print(f"  SAFE TEXT TOP              : y >= {chin + 60}")
    print("  a block whose `top` is above this WILL cross the face on some frame.")
    print("  measure every clip you intend to put text over — framing can differ")
    print("  between parts of the same lipsync set, and eyeballing two frames is")
    print("  how you end up with a rule that is wrong for the third.")
    return 0


# ---------------------------------------------------------------- offsets
def cmd_offsets(a):
    """Find where each lipsync part actually sits in the master audio.

    The filenames lie. On BL51 they claimed 0s / 63s / 125s and the parts
    really sat at 0.00 / 62.71 / 125.42 — 9 and 13 frames of lip error if
    you trust the name. A fine scan around the nominal value is not enough:
    part B scored r=0.025 there. Scan the whole track on an envelope first,
    then refine at sample level.
    """
    total = float(probe(a.master)["format"]["duration"])
    M_env = envelope(pcm(a.master, rate=4000))
    results, weak = [], []
    for spec in a.parts:
        label, path = spec.split("=", 1)
        L_env = envelope(pcm(path, rate=4000))
        n = len(L_env)
        if n >= len(M_env):
            print(f"  {label}: part is longer than the master, skipped"); continue
        coarse = max((float(np.dot(L_env, M_env[i:i + n]) / n), i * 0.05)
                     for i in range(len(M_env) - n))[1]
        # decode the master once and slice it in numpy; calling ffmpeg per
        # candidate offset turns a 3-second check into several minutes
        L = nrm(pcm(path, 0, 12))
        Mfull = pcm(a.master)
        win = len(L)
        best = (0.0, -9.0)
        lo = int(max(0.0, coarse - 0.8) * 16000)
        hi = int(min(total - 12, coarse + 0.8) * 16000)
        for i in range(lo, hi, 160):                       # 10 ms steps
            M = Mfull[i:i + win]
            if len(M) < win:
                break
            M = nrm(M)
            r = float(np.dot(L, M) / win)
            if r > best[1]:
                best = (round(i / 16000, 2), r)
        results.append(dict(part=label, file=os.path.basename(path),
                            true_s=best[0], r=round(best[1], 3)))
        print(f"  {label}: TRUE OFFSET {best[0]:7.2f}s   r={best[1]:.3f}   ({os.path.basename(path)})")
        if best[1] < 0.9:
            weak.append(label)
    if a.json:
        json.dump(results, open(a.json, "w"), indent=1)
        print(f"\n  written -> {a.json}")
    if weak:
        print("\n  WARNING: " + ", ".join(weak) + " matched weakly. That part may be"
              " from a different take — do not seat it until a human confirms.")
        return 1
    return 0


# ----------------------------------------------------------------- verify
def cmd_verify(a):
    fail = []
    info = probe(a.render)
    streams = info.get("streams", [])
    v = next((s for s in streams if s["codec_type"] == "video"), None)
    au = next((s for s in streams if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    print(f"  file      {os.path.basename(a.render)}")
    if not v:
        print("  FAIL: no video stream"); return 1
    print(f"  video     {v['width']}x{v['height']} @ {v['r_frame_rate']}  "
          f"{v.get('nb_frames','?')} frames  {dur:.2f}s")
    if (v["width"], v["height"]) != (1080, 1920):
        fail.append(f"resolution is {v['width']}x{v['height']}, must be 1080x1920")
    if v["r_frame_rate"] != "30/1":
        fail.append(f"frame rate is {v['r_frame_rate']}, must be 30/1")
    if not au:
        fail.append("no audio stream")
    if a.duration and abs(dur - float(a.duration)) > 0.2:
        fail.append(f"duration {dur:.2f}s is not the expected {a.duration}s")

    if au and a.audio:
        print("  audio sync vs the master voice:")
        for p in [x for x in (dur * 0.05, dur * 0.45, dur * 0.90) if x + 8 < dur]:
            A, Bm = nrm(pcm(a.render, p, 8)), nrm(pcm(a.audio, p, 8))
            m = min(len(A), len(Bm))
            c = np.correlate(A[:m], Bm[:m], "same")
            lag = (c.argmax() - len(c) // 2) / 16000
            r = float(c.max() / m)
            ok = abs(lag) <= 0.034 and r > 0.9      # 0.034s = one frame at 30fps
            print(f"    t={p:6.1f}s  lag {lag*1000:+5.0f} ms  r={r:.3f}  {'ok' if ok else 'FAIL'}")
            if not ok:
                fail.append(f"audio drifts {lag*1000:+.0f} ms at t={p:.0f}s")

    # Seating is an AUDIO question, not a picture one. A 0.29 s error is 9
    # frames, and a talking head barely moves in 9 frames, so frame differencing
    # waves it through. Correlating the rendered audio against the part's own
    # audio catches it instantly - that is how 62.71 was found in the first
    # place. This needs the ORIGINAL part file, the one that still has audio,
    # not a copy normalised with -an.
    for spec in (a.seat or []):
        label, path, at = spec.split("=", 2)
        at = float(at)
        L = pcm(path, 0, 10)
        if L.size < 16000:
            print(f"  lipsync {label}: {os.path.basename(path)} has no audio — "
                  f"pass the ORIGINAL part file, not the -an copy")
            fail.append(f"cannot check seating of {label}: no audio in {os.path.basename(path)}")
            continue
        R = pcm(a.render, at, 10)
        m = min(len(L), len(R))
        c = np.correlate(nrm(L[:m]), nrm(R[:m]), "same")
        lag = (c.argmax() - len(c) // 2) / 16000
        r = float(c.max() / m)
        ok = abs(lag) <= 0.034 and r > 0.9
        print(f"  lipsync {label} seated at {at:.2f}s: lag {lag*1000:+5.0f} ms  "
              f"r={r:.3f}  {'ok' if ok else 'FAIL'}")
        if not ok:
            fail.append(f"lipsync {label} is {lag*1000:+.0f} ms out at {at:.2f}s "
                        f"(run `bl_tools.py offsets` and seat it where that says)")

    print()
    if fail:
        for f in fail:
            print(f"  FAIL: {f}")
        return 1
    print("  VERIFY PASSED")
    return 0


# ------------------------------------------------------------------ sheet
def cmd_sheet(a):
    from PIL import ImageDraw
    times = [float(t) for t in a.at.split(",")]
    cols = a.cols or min(6, len(times))
    rows = (len(times) + cols - 1) // cols
    tw, th, pad, lab = 230, 409, 8, 20
    sheet = Image.new("RGB", (cols * (tw + pad) + pad,
                              rows * (th + lab + pad) + pad), "#141414")
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(times):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", a.render,
                        "-frames:v", "1", "-update", "1", "-vf", f"scale={tw}:{th}",
                        "-q:v", "3", "/tmp/_bl_sheet.jpg"], check=True)
        im = Image.open("/tmp/_bl_sheet.jpg")
        x = pad + (i % cols) * (tw + pad)
        y = pad + (i // cols) * (th + lab + pad)
        d.text((x + 2, y + 3), f"{t:.1f}s", fill="#dcdcdc")
        sheet.paste(im, (x, y + lab))
    sheet.save(a.out, quality=92)
    print(f"  {len(times)} frames -> {a.out}  ({sheet.size[0]}x{sheet.size[1]})")
    print("  read this one image instead of scrubbing the video.")
    return 0


# ------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("offsets", help="find the true position of each lipsync part")
    o.add_argument("--master", required=True, help="the full voice track")
    o.add_argument("--parts", nargs="+", required=True, metavar="LABEL=FILE")
    o.add_argument("--json", help="write the result here")
    o.set_defaults(fn=cmd_offsets)

    s = sub.add_parser("safearea", help="where text may sit without covering the face")
    s.add_argument("clip")
    s.add_argument("--at", help="comma-separated seconds (default: 5 across the clip)")
    s.set_defaults(fn=cmd_safearea)

    v = sub.add_parser("verify", help="final gate on a rendered mp4")
    v.add_argument("render")
    v.add_argument("--audio", help="master voice track to check sync against")
    v.add_argument("--duration", help="expected duration in seconds")
    v.add_argument("--seat", nargs="*", metavar="LABEL=FILE=AT",
                   help="check a lipsync clip is seated where you think")
    v.set_defaults(fn=cmd_verify)

    c = sub.add_parser("sheet", help="contact sheet of N frames")
    c.add_argument("render")
    c.add_argument("--at", required=True)
    c.add_argument("--out", default="sheet.jpg")
    c.add_argument("--cols", type=int)
    c.set_defaults(fn=cmd_sheet)

    a = p.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
