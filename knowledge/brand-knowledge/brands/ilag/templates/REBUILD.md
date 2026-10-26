# Rebuild kit v2 (overlays, sheet, demo)

Work in a task folder (`Work/<task-id>/`), never in this repo folder: the scripts write `kit.html`,
`overlays/`, `tiles/`, `seg/` and `out/` next to themselves. `K` below is that folder.

```bash
cp -r knowledge/brand-knowledge/brands/ilag/templates/. "$K"/ && mkdir -p "$K"/{footage,frames,sfx,out}
PY=/opt/MoonieXHQ/Agents/Core/.venv/bin/python        # has Playwright + PIL

# 0. Logo: logo.png is the Page's own profile picture lifted off its black square (never redrawn).
#    It is made here every time, not kept in git (1.4 MB; media over 1 MB stays out of git, ADR 0030):
$PY -I "$K"/cut_logo.py knowledge/brand-knowledge/brands/ilag/images/ilag-page-logo-1080.jpg "$K"/logo.png

# 1. Overlays: every element, or a comma list (e.g. "name,end")
$PY -I "$K"/render_kit.py "$K"

# 2. Footage: "ขายชื่อ" EP1 from our own Page (183.6 s, 1080x1920, 24 fps)
yt-dlp -f "2016235605762298v+2016235019095690a" --merge-output-format mp4 \
  -o "$K/footage/ep5-ep1.%(ext)s" "https://www.facebook.com/61594116376333/videos/1376542657800427/"
for t in 0 30 66 78 132 140.5 141.4; do
  ffmpeg -v error -y -ss $t -i "$K"/footage/ep5-ep1.mp4 -frames:v 1 "$K"/frames/f_$t.png; done

# 3. Contact sheet (20 tiles) → out/ilag-kit-sheet-v2.jpg
$PY -I "$K"/compose_sheet.py "$K"

# 4. Sound effects, synthesised (no library, nothing to license)
cd "$K"/sfx
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.55*sin(2*PI*(950*t-900*t*t))*exp(-2.5*t)+0.18*(random(0)*2-1)*exp(-5*t)':s=48000:d=0.5" scratch.wav
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.95*sin(2*PI*52*t)*exp(-8*t)+0.5*sin(2*PI*104*t)*exp(-13*t)+0.35*(random(0)*2-1)*exp(-45*t)':s=48000:d=0.7" -af lowpass=f=1800 thud.wav
ffmpeg -v error -y -f lavfi -i "aevalsrc='(0.3*sin(2*PI*(1300+520*sin(2*PI*11*t))*t)+0.06*(random(0)*2-1))*(1-exp(-25*t))*exp(-0.6*t)':s=48000:d=1.0" rewind.wav
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.95*sin(2*PI*46*t)*exp(-2.6*t)+0.35*(random(0)*2-1)*exp(-4.5*t)':s=48000:d=1.8" -af lowpass=f=260 boom.wav
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.5*(random(0)*2-1)*pow(sin(PI*t/0.9),2)':s=48000:d=0.9" -af "highpass=f=500,lowpass=f=3500" whoosh.wav

# 5. Demo → out/ilag-kit-demo-v2.mp4 (44 s). The NG-slam frames need PIL, so draw them first;
#    the encode itself runs anywhere ffmpeg runs (winbox: ~1 min; Contabo: under the render lock).
$PY -I "$K"/build_demo.py "$K" frames
$PY -I "$K"/build_demo.py "$K"
```

The NG stamp and its tape line come in three cuts: `ng` (both, for the sheet), `ngs` (stamp only) and `ngt`
(tape only). `build_demo.py` animates the stamp in on its own and lays the tape over it 6 frames later. The
three source points of the demo sit inside one shot: the cut before the take is at src 139.5.
