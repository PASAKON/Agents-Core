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
import argparse, json, os, re, subprocess, sys, time
import pathlib
import numpy as np
from PIL import Image, ImageDraw


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
    # R-B is what separates skin from this channel's backgrounds. Measured on
    # the 2026-09-18 reference: cheek 56, chin 67, neon wall 30-36, white polo
    # 1, black suit 4. The old threshold of 28 let the neon wall through, the
    # "face" became the whole frame, and safearea returned y>=1975 on a clip
    # whose chin is at 1030. 45 sits in the gap with room on both sides.
    skin = ((R > 95) & (R < 240) & (R - G > 12) & (R - G < 70) &
            (G - B > 8) & (G - B < 60) & (R - B > 45))
    # A face lives in the upper part of a 9:16 talking-head frame. Hands do not
    # always, and a hand raised into frame is a second skin blob that drags the
    # bottom of the bounding box down past the chin - that is the other way
    # this function used to lie.
    h = rgb.shape[0]
    skin = skin.copy()
    skin[int(h * 0.72):, :] = False
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
    # widest run, but a run spanning most of the frame is background bleeding
    # through, not a face - drop those and take the widest plausible one
    runs = [r for r in runs if len(r) <= rgb.shape[1] * 0.70] or runs
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
    # 0.50, not 0.60: calibrated 2026-09-18 against two references whose
    # chins were read off a pixel ruler by eye (old 800, new 940). No single
    # fraction fits both - 0.60 reads the lips as the chin on a wide-jawed
    # face, 0.45 walks down into the neck on a narrow one. 0.50 is the best
    # compromise and is still allowed to be ~50px high, which is why this
    # command now draws the answer instead of only printing it.
    thresh = width[widest] * 0.50
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
    print(f"\n  lowest chin across samples : y={chin}   (estimate, can read ~50px high)")
    print(f"  SAFE TEXT TOP              : y >= {chin + 60}")

    # The number alone has lied before, in both directions, so draw it. One look
    # at this image settles what no threshold reliably can: a line through the
    # lips is too high, a line on the collar is too low, a line on the jaw edge
    # is right.
    out = pathlib.Path(a.clip).with_suffix("").name + "-safearea.jpg"
    t_low = times[int(np.argmax(chins))] if len(chins) == len(times) else times[-1]
    rgb = frame(a.clip, t_low)
    im = Image.fromarray(rgb.astype("uint8")).resize((1080, 1920))
    d = ImageDraw.Draw(im)
    for y, col, lab in ((chin, (255, 90, 90), f"chin {chin}"),
                        (chin + 60, (90, 220, 255), f"SAFE TOP {chin + 60}")):
        d.line([0, y, 1080, y], fill=col, width=6)
        d.rectangle([8, y - 24, 430, y + 24], fill=(0, 0, 0))
        d.text((16, y - 14), lab, fill=col)
    im.save(out, quality=90)
    print(f"  drawn on            : {out}   <- LOOK AT THIS")
    print("  the red line must sit on the jaw edge. Through the lips = too high,")
    print("  on the collar = too low; in either case set the value by eye and say so.")
    print("  measure every clip you intend to put text over — framing differs")
    print("  between parts of the same lipsync set.")
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
    M_raw = pcm(a.master, rate=4000)
    # Pad the tail so a part that runs to the very last sample still fits the
    # scan. BL50's part C ended exactly where the track ended, the old
    # range(len-n) stopped one window short of its true start, and the scan
    # returned a spurious max at 84 s with r=0.03. The worker caught it by
    # hand; this is the fix.
    M_env = envelope(np.concatenate([M_raw, np.zeros(4000 * 3)]))
    Mfull = None
    results, weak = [], []
    for spec in a.parts:
        label, path = spec.split("=", 1)
        # coarse-match on the part's first 10 s only, so its length can never
        # push the true start outside the searchable range
        L_env = envelope(pcm(path, 0, 10, rate=4000))
        n = len(L_env)
        if n >= len(M_env):
            print(f"  {label}: part is longer than the master, skipped"); continue
        coarse = max((float(np.dot(L_env, M_env[i:i + n]) / n), i * 0.05)
                     for i in range(len(M_env) - n + 1))[1]
        # decode the master once and slice it in numpy; calling ffmpeg per
        # candidate offset turns a 3-second check into several minutes
        if Mfull is None:
            Mfull = pcm(a.master)
        fine_len = max(4.0, min(12.0, total - coarse - 0.9))
        L = nrm(pcm(path, 0, fine_len))
        win = len(L)
        best = (0.0, -9.0)
        lo = int(max(0.0, coarse - 0.8) * 16000)
        hi = int(min(total - fine_len, coarse + 0.8) * 16000)
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
    else:
        # Loudness. TikTok and YouTube both normalise toward -14 LUFS, so a
        # quieter file is turned UP by the platform -- lifting its noise floor --
        # and in a feed it simply sounds weak beside everything else. EP52
        # shipped at -20.2 LUFS, 6 dB under, with every other gate green,
        # because nothing here measured it. The hired TRADER UNCUT edit we
        # judged harshly on craft hit -14.0 exactly.
        try:
            _out = subprocess.run(
                ["ffmpeg", "-hide_banner", "-nostats", "-i", a.render,
                 "-af", "ebur128", "-f", "null", "-"],
                capture_output=True, text=True).stderr
            _m = re.search(r"Integrated loudness:\s*\n\s*I:\s*(-?[\d.]+)\s*LUFS", _out)
            if _m:
                _l = float(_m.group(1))
                print(f"  loudness  {_l:.1f} LUFS (target -14, tolerance 2)")
                if abs(_l + 14.0) > 2.0:
                    fail.append(
                        f"loudness {_l:.1f} LUFS is outside -16..-12 - normalise the "
                        f"master, never the mix: "
                        f"ffmpeg -i in.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy out.mp4")
            else:
                print("  loudness  NOT MEASURED (ebur128 returned no reading)")
        except FileNotFoundError:
            print("  loudness  skipped (ffmpeg not on PATH)")
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
def cmd_coverage(a):
    """Where the cut has no footage at all — a lipsync part or a plate — and
    text is carrying the frame alone. The channel's approved cuts run about
    half their length that way (BL51: 61 %, longest 44 s), so this is not a
    gate; it is the list step 5b works from. Fill a hole when a catalogued clip
    matches the claim on screen; keep the kinetic plate when nothing does."""
    import re
    html = open(a.composition, encoding="utf-8").read()
    dur = float(re.search(r'data-composition-id="[^"]+"[^>]*data-duration="([\d.]+)"', html).group(1)) \
        if re.search(r'data-composition-id="[^"]+"[^>]*data-duration="([\d.]+)"', html) else a.duration
    iv = []
    for m in re.finditer(r"<video[^>]*>", html):
        t = m.group(0)
        st = re.search(r'data-start="([\d.]+)"', t); du = re.search(r'data-duration="([\d.]+)"', t)
        if st and du:
            iv.append((float(st.group(1)), float(st.group(1)) + float(du.group(1))))
    iv.sort()
    cur, holes = 0.0, []
    for s0, s1 in iv:
        if s0 - cur >= a.min_gap:
            holes.append((cur, s0))
        cur = max(cur, s1)
    if dur and dur - cur >= a.min_gap:
        holes.append((cur, dur))
    total = sum(b - x for x, b in holes)
    print(f"  {len(iv)} video clips, composition {dur:.2f}s")
    for x, b in holes:
        flag = "  <- fill from the catalogue if a clip matches the claim" if b - x >= a.fill_from else ""
        print(f"  no footage {x:7.2f}-{b:7.2f}s  ({b - x:5.1f}s){flag}")
    if dur:
        print(f"  TOTAL without footage {total:.1f}s = {total / dur * 100:.0f}%   (BL51 approved cut: 61 %, longest hole 44 s)")
    print("  coverage is a list to work from, not a gate; see SKILL.md step 5b")


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


# ------------------------------------------------------------------- safezone
# TikTok's own published safe area is a 540x960 reference with margins
# 126 top / 60 left / 120 right / 378 bottom. Doubled onto this canvas:
SAFE = {"left": 120, "top": 252, "right": 840, "bottom": 1500}
# bottom is the MEASURED organic one: TikTok's caption block starts at y~1550
# on a real post. The published spec says 1164, but that margin exists to clear
# an ad unit's CTA button, which an organic post does not have.
# And what a real phone does to the frame, measured on a post of the CEO's own
# (1188x2576, 2026-09-18): a 9:16 video is scaled to COVER a 19.5:9 screen, so
# 97px of EACH SIDE is cropped away and never rendered at all. Anything at
# x<97 or x>983 does not exist for that viewer.
CROP_X = 97
# The like/comment rail starts here. Anything whose top is above it is judged
# against the left margin on both sides, not against the rail's 240.
RAIL_TOP = 900
TIKTOK_UI = [
    ("app nav (For You / Following)", "y", 138, 186),
    ("right rail (avatar, like, comment)", "x", 873, 983),
    ("caption + username block", "y", 1550, 1700),
    ("scrub bar", "y", 1770, 1810),
]


def cmd_safezone(a):
    """Flag every absolutely-positioned overlay that leaves the TikTok safe box."""
    import re as _re
    html = pathlib.Path(a.composition).read_text(encoding="utf-8")
    # left/right/top on a rule that also carries position:absolute, plus inline styles
    bad, seen = [], 0
    for m in _re.finditer(r"\n\s*((?:[.#][\w-]+\s*)+)\{([^}]*position:\s*absolute[^}]*)\}", html, _re.S):
        sel, body = m.group(1).strip(), m.group(2)
        if sel in (".clip", ".bl-bg"):
            continue
        if " " in sel:          # a descendant rule is positioned against its own
            continue            # parent box, not against the frame
        seen += 1
        def num(prop):
            mm = _re.search(prop + r":\s*(-?\d+)px", body)
            return int(mm.group(1)) if mm else None
        left, right, top = num("left"), num("right"), num("top")
        if left is not None and left < SAFE["left"]:
            bad.append(f"{sel}: left {left} < {SAFE['left']}"
                       + ("  (BELOW x=97 — physically cropped off the phone)" if left < CROP_X else ""))
        # The 240 right margin exists for the like/comment rail, and the rail
        # starts at y~960. A rule that lives ABOVE it may come back in to 120 --
        # that is what .blk.wide is, and it is why the brand bug sits at
        # right:150. Judging every rule by the same margin flagged the bug as a
        # rail collision at y=310, which is 650px clear of the rail.
        # `right: N` is a MARGIN, so the element's right edge sits at 1080-N.
        # Compare margin against required margin -- the old form compared the
        # margin against a coordinate (right < 1080 - 240 = 840) and so failed
        # almost any numeric margin. It only ever looked correct because every
        # real offender happened to be a small number.
        above_rail = top is not None and top < RAIL_TOP
        # SAFE["right"] is the EDGE coordinate (840); the margin is 1080 minus it.
        min_right = SAFE["left"] if above_rail else (1080 - SAFE["right"])
        if right is not None and right < min_right:
            where = ("above the rail, but past the crop edge at x=983"
                     if above_rail else "runs under the like/comment rail")
            bad.append(f"{sel}: right margin {right} < {min_right} "
                       f"-> right edge x{1080 - right} ({where})")
        if top is not None and top < SAFE["top"]:
            bad.append(f"{sel}: top {top} < {SAFE['top']} (sits under the app's own nav)")
        if top is not None and top > SAFE["bottom"]:
            for name, axis, lo, hi in TIKTOK_UI:
                if axis == "y" and lo <= top <= hi:
                    bad.append(f"{sel}: top {top} lands on TikTok's {name}")
                    break
            else:
                bad.append(f"{sel}: top {top} > {SAFE['bottom']} (past the safe bottom)")
    print(f"  safe box  x {SAFE['left']}-{SAFE['right']}   y {SAFE['top']}-{SAFE['bottom']}"
          f"   (frame is cropped outside x {CROP_X}-{1080 - CROP_X})")
    print(f"  checked {seen} absolutely-positioned rules")
    if not bad:
        print("  OK - nothing leaves the safe box")
        return 0
    for b in bad:
        print("  FAIL " + b)
    return 1


# --------------------------------------------------------------------- matte
def cmd_matte(a):
    """Matte the avatar out of a baked-background lipsync clip -> alpha WebM.

    Needs torch (+ MPS). bl_tools.py's other commands stay numpy+Pillow-only
    on purpose; this one command is the exception. Run it with a Python that
    has torch, e.g. the venv this task built:
      /Users/gob/.claude/skills/reel-editor-th/.venv/bin/python3 bl_tools.py matte ...
    Compared 2026-09-23 against rembg(u2net) and attempted mediapipe on the
    EP55 real lipsync files: RVM mobilenetv3 on MPS won on both edge quality
    (rembg leaked alpha over ~15-17% of the frame on the red-lit set vs RVM's
    ~1%) and speed. See the skill's field notes for the full comparison.
    """
    try:
        import torch
    except ImportError:
        print("no torch in this interpreter. Run with a venv that has it, e.g.:")
        print("  /Users/gob/.claude/skills/reel-editor-th/.venv/bin/python3 " + sys.argv[0] + " matte ...")
        return 1
    import numpy as np

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    info = probe(a.input)
    vstream = next(s for s in info["streams"] if s["codec_type"] == "video")
    W, H = int(vstream["width"]), int(vstream["height"])
    num, den = (vstream.get("r_frame_rate") or "25/1").split("/")
    fps = float(num) / float(den or 1)
    out = a.out or (os.path.splitext(a.input)[0] + "-matte.webm")

    print(f"  loading RVM ({a.model}) on {device} ...")
    model = torch.hub.load("PeterL1n/RobustVideoMatting", a.model, trust_repo=True)
    model = model.eval().to(device)

    reader = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", a.input,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    writer = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
         "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", str(a.crf),
         "-auto-alt-ref", "0", "-disposition:v", "default", out],
        stdin=subprocess.PIPE)

    frame_bytes = W * H * 3
    rec = [None] * 4
    n = 0
    t0 = time.time()
    with torch.no_grad():
        while True:
            if a.max_frames and n >= a.max_frames:
                break
            raw = reader.stdout.read(frame_bytes)
            if len(raw) < frame_bytes:
                break
            rgb = np.frombuffer(raw, dtype=np.uint8).reshape(H, W, 3)
            t = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255).unsqueeze(0).to(device)
            fgr, pha, *rec = model(t, *rec, downsample_ratio=a.downsample)
            fgr_np = (fgr[0].permute(1, 2, 0).clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)
            pha_np = (pha[0, 0].clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)
            rgba = np.dstack([fgr_np, pha_np])
            writer.stdin.write(rgba.tobytes())
            n += 1
            if n % 30 == 0:
                print(f"  {n} frames ({n / fps:.1f}s) ...")
    reader.stdout.close(); reader.wait()
    writer.stdin.close(); writer.wait()
    dt = time.time() - t0
    size = os.path.getsize(out) if os.path.exists(out) else 0
    print(f"  {n} frames -> {out}  ({size / 1e6:.1f} MB)  "
          f"{dt:.1f}s total, {dt / max(n, 1) * 1000:.0f} ms/frame, {n / max(dt, 1e-9):.1f} fps")
    if a.preview:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", out,
                        "-vf", "format=rgba,pad=iw:ih:0:0:color=0x2c2c2cff",
                        "-frames:v", "1", a.preview], check=False)
        print(f"  preview frame -> {a.preview}")
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
    v.add_argument("--seat", nargs="+", action="extend", metavar="LABEL=FILE=AT",
                   help="check a lipsync clip is seated where you think")
    v.set_defaults(fn=cmd_verify)

    g = sub.add_parser("coverage", help="stretches of the cut with no footage (what 5b fills)")
    g.add_argument("composition", help="cut/index.html")
    g.add_argument("--duration", type=float, default=0.0, help="only if the root has no data-duration")
    g.add_argument("--min-gap", type=float, default=3.0)
    g.add_argument("--fill-from", type=float, default=8.0, help="holes this long or longer get flagged")
    g.set_defaults(fn=cmd_coverage)

    c = sub.add_parser("sheet", help="contact sheet of N frames")
    c.add_argument("render")
    c.add_argument("--at", required=True)
    c.add_argument("--out", default="sheet.jpg")
    c.add_argument("--cols", type=int)
    c.set_defaults(fn=cmd_sheet)

    z = sub.add_parser("safezone", help="overlays that leave the TikTok safe box")
    z.add_argument("composition", help="cut/index.html")
    z.set_defaults(fn=cmd_safezone)

    m = sub.add_parser("matte", help="matte the avatar out of a baked-bg clip (needs torch)")
    m.add_argument("input")
    m.add_argument("--out", help="default: <input>-matte.webm")
    m.add_argument("--model", default="mobilenetv3", choices=["mobilenetv3", "resnet50"])
    m.add_argument("--downsample", type=float, default=0.5, help="RVM internal downsample ratio")
    m.add_argument("--crf", type=int, default=32, help="libvpx-vp9 CRF, lower = better quality/bigger")
    m.add_argument("--max-frames", type=int, help="stop early, for a quick test")
    m.add_argument("--preview", help="save one composited preview frame here")
    m.set_defaults(fn=cmd_matte)

    a = p.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
