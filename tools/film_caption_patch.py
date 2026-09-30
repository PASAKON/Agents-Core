"""Remove a burned-in caption from a LOCKED-OFF clip, free, using the clip's own clean background.

Why: Omni 1.1 burned a correctly spelled Thai caption into EP1 shot 6 (mid-frame, 15-45 % of the
height) although the prompt carried the no-subtitles negative. `burned_text_scan.py` only reads the
bottom band (78-96 %) so it said "0 of 18". The bottom-crop free fix in CMO_Gate_Flow_Omni1.1_FilmQC
cannot help when the text is mid-frame. A re-fire costs 15 credits and a caption survives re-fires.

How: median of every 4th frame of the top 45 % = a caption-free background plate (the dog and the
text move, the room does not); per frame, white pixels with a dark outline on a dense text line are
masked (+9 px) and replaced from the plate. Audio is copied untouched.

Use only when the camera does not move and the caption is ABOVE the moving subject (shot 6: caption
at 15-36 %, dog's head top at 36 %). Look at one frame before and after; a moving subject under the
text would be replaced by background.

    python3 tools/film_caption_patch.py <in.mp4> <out.mp4>      # 720x1280 clips; numpy + ffmpeg only
"""
import subprocess, sys, numpy as np
src, dst = sys.argv[1], sys.argv[2]
W, H, Y1 = 720, 1280, int(1280*0.45)   # patch only the top 45% (above the dog's head line)
FS = W*H*3
def frames():
    p = subprocess.Popen(["ffmpeg","-v","error","-i",src,"-f","rawvideo","-pix_fmt","rgb24","-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(FS)
        if len(b) < FS: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.wait()
reg = np.stack([f[:Y1].copy() for i, f in enumerate(frames()) if i % 4 == 0])
bg = np.median(reg, axis=0).astype(np.uint8)
print("background from", len(reg), "frames", flush=True)
def dil(m, r):
    o = m.copy()
    for d in range(1, r+1):
        o[d:] |= m[:-d]; o[:-d] |= m[d:]
    m2 = o.copy()
    for d in range(1, r+1):
        m2[:, d:] |= o[:, :-d]; m2[:, :-d] |= o[:, d:]
    return m2
enc = subprocess.Popen(["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r","24","-i","-",
    "-i",src,"-map","0:v","-map","1:a","-c:v","libx264","-crf","14","-preset","medium","-pix_fmt","yuv420p","-c:a","copy","-shortest",dst],
    stdin=subprocess.PIPE)
n_patched = 0; per_frame = []
for i, f in enumerate(frames()):
    top = f[:Y1]
    white = (top > 215).all(axis=2)
    dark = top.max(axis=2) < 80
    near = np.zeros_like(dark)
    for d in range(2, 7):
        near[:, d:] |= dark[:, :-d]; near[:, :-d] |= dark[:, d:]
    txt = white & near
    # caption glyphs form dense horizontal runs; ignore isolated specks
    rows = txt.sum(axis=1)
    band = np.zeros(Y1, bool)
    for y in range(Y1 - 30):
        if rows[y:y+30].sum() > 120: band[y:y+30] = True      # a text line: many hits inside a 30 px band
    txt &= band[:, None]
    m = dil(txt, 9)
    out = f.copy()
    if m.any():
        out[:Y1][m] = bg[m]; n_patched += 1
    per_frame.append(int(m.sum()))
    enc.stdin.write(out.tobytes())
enc.stdin.close(); enc.wait()
print("patched frames", n_patched, "of", len(per_frame), "max mask px", max(per_frame))
