"""Cut a ~45 s ILAG kit demo from «ขายชื่อ» EP1 footage: one ffmpeg segment at a time, then concat + loudnorm."""
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageEnhance
except ImportError:  # winbox has no PIL: the slam frames are drawn beforehand
    Image = None

K = Path(sys.argv[1]).resolve()
ONLY_FRAMES = len(sys.argv) > 2 and sys.argv[2] == 'frames'
SRC = K / "footage/ep5-ep1.mp4"
O, S, SEG = K / "overlays", K / "sfx", K / "seg"
SEG.mkdir(exist_ok=True)
FPS = 24
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg failed: {' '.join(cmd)}\n{r.stderr[-2000:]}")


def clip(t, d):
    return ["-ss", f"{t}", "-t", f"{d}", "-i", str(SRC)]


def png(name, d):
    return ["-loop", "1", "-framerate", str(FPS), "-t", f"{d}", "-i", str(O / f"{name}.png")]


def sfx(name):
    return ["-i", str(S / f"{name}.wav")]


def silence(d):
    return ["-f", "lavfi", "-t", f"{d}", "-i", "anullsrc=r=48000:cl=stereo"]


def fade(i, a, b, tag):
    return (f"[{i}:v]format=rgba,fade=t=in:st={a}:d=0.25:alpha=1,"
            f"fade=t=out:st={b - 0.25:.2f}:d=0.25:alpha=1[{tag}]")


def seg(name, inputs, vf, af, d):
    if ONLY_FRAMES:
        return
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", f"{vf};{af}",
         "-map", "[v]", "-map", "[a]", *ENC, "-t", f"{d}", str(SEG / f"{name}.mp4")])


def mix(parts, d):
    """parts: list of (input_index, delay_s, gain); returns the audio filter ending in [a]."""
    chains, labels = [], []
    for n, (i, delay, gain) in enumerate(parts):
        ms = int(delay * 1000)
        chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms},volume={gain}[m{n}]")
        labels.append(f"[m{n}]")
    return ";".join(chains) + f";{''.join(labels)}amix=inputs={len(parts)}:duration=longest:normalize=0,atrim=0:{d},asetpts=PTS-STARTPTS[a]"


# A · hook cold open + character name card (4.5 s)
seg("a", [*clip(132.0, 4.5), *png("wm", 4.5), *png("name", 4.5)],
    f"[0:v]setpts=PTS-STARTPTS[b];{fade(2, 0.6, 3.9, 'n')};[b][1:v]overlay[b1];[b1][n]overlay,setsar=1,format=yuv420p[v]",
    mix([(0, 0, 1.0)], 4.5), 4.5)

# B1 · the take plays (1.4 s)
seg("b1", [*clip(140.0, 1.4), *png("wm", 1.4)],
    "[0:v]setpts=PTS-STARTPTS[b];[b][1:v]overlay,setsar=1,format=yuv420p[v]", mix([(0, 0, 1.0)], 1.4), 1.4)

# B2 · freeze + NG stamp slam + tape (1.8 s), frames drawn in PIL so the slam and the shake are exact
fr = K / "seg/b2frames"
fr.mkdir(exist_ok=True)
if Image is not None and not (fr / '000.jpg').exists():
  base = Image.open(K / "frames/f_141.4.png").convert("RGB")
  base = ImageEnhance.Brightness(ImageEnhance.Color(base).enhance(0.3)).enhance(0.8).convert("RGBA")
  wm, stamp, tape = (Image.open(O / f"{n}.png").convert("RGBA") for n in ("wm", "ngs", "ngt"))
  SCALES = {3: 1.55, 4: 1.25, 5: 1.06, 6: 0.97}
  SHAKE = {4: (14, -8), 5: (-9, 6), 6: (5, -3)}
  big = base.resize((1112, 1978), Image.LANCZOS)
  for f in range(int(1.8 * FPS)):
      dx, dy = SHAKE.get(f, (0, 0))
      im = big.crop((16 + dx, 29 + dy, 16 + dx + 1080, 29 + dy + 1920))
      im.alpha_composite(wm)
      if f >= 3:
          s = SCALES.get(f, 1.0)
          st = stamp.resize((round(1080 * s), round(1920 * s)), Image.LANCZOS)
          x0, y0 = round(540 * s - 540), round(800 * s - 800)
          im.alpha_composite(st.crop((x0, y0, x0 + 1080, y0 + 1920)))
      if f >= 9:
          im.alpha_composite(tape)
      im.convert("RGB").save(fr / f"{f:03d}.jpg", quality=94)
if ONLY_FRAMES:
    sys.exit("frames drawn")
seg("b2", ["-framerate", str(FPS), "-i", str(fr / "%03d.jpg"), *sfx("scratch"), *sfx("thud"), *silence(1.8)],
    "[0:v]scale=in_range=pc:out_range=tv,setsar=1,format=yuv420p[v]", mix([(3, 0, 1.0), (1, 0, 0.9), (2, 0.12, 1.0)], 1.8), 1.8)

# B3 · rewind: the take back to its first frame (the shot starts at src 139.5), reversed at 1.85x (1.0 s)
seg("b3", [*clip(139.55, 1.85), *png("wm", 1.0), *png("rew", 1.0), *sfx("rewind")],
    "[0:v]reverse,setpts=(PTS-STARTPTS)/1.85,fps=24,eq=saturation=0.75,noise=alls=14:allf=t[r];"
    "[r][1:v]overlay[r1];[r1][2:v]overlay,setsar=1,format=yuv420p[v]",
    mix([(3, 0, 0.9)], 1.0), 1.0)

# B4 · take 2 plays on (4.4 s)
seg("b4", [*clip(139.55, 4.4), *png("wm", 4.4), *png("take2", 4.4)],
    f"[0:v]setpts=PTS-STARTPTS[b];{fade(2, 0.0, 1.5, 't')};[b][1:v]overlay[b1];[b1][t]overlay,setsar=1,format=yuv420p[v]",
    mix([(0, 0, 1.0)], 4.4), 4.4)

# C · EP title sting (3.0 s)
seg("c", [*clip(128.0, 3.0), *png("title", 3.0), *sfx("boom"), *sfx("whoosh")],
    "[0:v]setpts=PTS-STARTPTS,boxblur=22:2[b];[1:v]format=rgba,fade=t=in:st=0:d=0.35:alpha=1[t];"
    "[b][t]overlay,setsar=1,format=yuv420p[v]",
    mix([(0, 0, 0.15), (3, 0, 0.8), (2, 0.15, 1.0)], 3.0), 3.0)

# D · same-day rewind card into the story + place stamp (6.0 s)
seg("d", [*clip(0.0, 6.0), *png("wm", 6.0), *png("rewcard", 6.0), *png("place", 6.0), *sfx("whoosh")],
    f"[0:v]setpts=PTS-STARTPTS[b];{fade(2, 0.15, 2.45, 'r')};{fade(3, 2.7, 5.9, 'p')};"
    "[b][1:v]overlay[b1];[b1][r]overlay[b2];[b2][p]overlay,setsar=1,format=yuv420p[v]",
    mix([(0, 0, 1.0), (4, 0, 0.6)], 6.0), 6.0)

# E1 · flashback: sepia, vignette, grain, the card and the 'อดีต' tag (5.0 s)
seg("e1", [*clip(30.0, 5.0), *png("wm", 5.0), *png("flash", 5.0), *png("ftag", 5.0), *sfx("whoosh")],
    "[0:v]setpts=PTS-STARTPTS,colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,"
    f"vignette=PI/4,noise=alls=9:allf=t[b];{fade(2, 0.2, 2.8, 'f')};"
    "[b][1:v]overlay[b1];[b1][f]overlay[b2];[b2][3:v]overlay,setsar=1,format=yuv420p[v]",
    "[0:a]lowpass=f=2600,volume=0.8[x];[4:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.6[w];"
    "[x][w]amix=inputs=2:duration=first:normalize=0,atrim=0:5,asetpts=PTS-STARTPTS[a]", 5.0)

# E2 · back to the present (3.0 s)
seg("e2", [*clip(36.0, 3.0), *png("wm", 3.0), *png("now", 3.0)],
    f"[0:v]setpts=PTS-STARTPTS[b];{fade(2, 0.1, 1.7, 'n')};[b][1:v]overlay[b1];[b1][n]overlay,setsar=1,format=yuv420p[v]",
    mix([(0, 0, 1.0)], 3.0), 3.0)

# F · time skip (5.0 s)
seg("f", [*clip(66.0, 5.0), *png("wm", 5.0), *png("skip", 5.0), *sfx("whoosh")],
    f"[0:v]setpts=PTS-STARTPTS[b];{fade(2, 0.2, 2.8, 's')};[b][1:v]overlay[b1];[b1][s]overlay,setsar=1,format=yuv420p[v]",
    mix([(0, 0, 1.0), (3, 0.05, 0.5)], 5.0), 5.0)

# G · end card with the open question (4.5 s)
seg("g", [*clip(76.0, 4.5), *png("end", 4.5), *sfx("boom")],
    "[0:v]setpts=PTS-STARTPTS,boxblur=18:2[b];[1:v]format=rgba,fade=t=in:st=0:d=0.35:alpha=1[e];"
    "[b][e]overlay,setsar=1,format=yuv420p[v]",
    mix([(0, 0, 0.18), (2, 0, 0.7)], 4.5), 4.5)

# H1 · blooper header on a frozen NG frame (2.2 s)
seg("h1", [*png("blooper", 2.2), "-loop", "1", "-framerate", str(FPS), "-t", "2.2", "-i", str(K / "frames/f_141.4.png"),
           *sfx("scratch"), *silence(2.2)],
    "[1:v]hue=s=0.3,eq=brightness=-0.05[b];[0:v]format=rgba,fade=t=in:st=0:d=0.2:alpha=1[h];[b][h]overlay,setsar=1,format=yuv420p[v]",
    mix([(3, 0, 1.0), (2, 0, 0.8)], 2.2), 2.2)

# H2 · the blooper itself with the corner tag (2.5 s)
seg("h2", [*clip(140.0, 2.5), *png("bltag", 2.5)],
    "[0:v]setpts=PTS-STARTPTS[b];[b][1:v]overlay,setsar=1,format=yuv420p[v]", mix([(0, 0, 1.0)], 2.5), 2.5)

order = ["a", "b1", "b2", "b3", "b4", "c", "d", "e1", "e2", "f", "g", "h1", "h2"]
(SEG / "list.txt").write_text("".join(f"file '{SEG / n}.mp4'\n" for n in order))
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(SEG / "list.txt"), "-c", "copy", str(SEG / "joined.mp4")])
run(["ffmpeg", "-v", "error", "-y", "-i", str(SEG / "joined.mp4"), "-c:v", "copy",
     "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
     "-movflags", "+faststart", str(K / "out/ilag-kit-demo-v1.mp4")])
print("demo done")
