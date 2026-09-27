#!/usr/bin/env bash
# build.sh — assemble one Thai talking-head reel.
#
#   build.sh <source.mp4> <workdir> [style]
#
# Expects <workdir>/timeline.py to already exist (you author it per clip).
# style: clean (default) | bold | terminal
#
# Steps: HDR->SDR tonemap -> render caption/card overlay -> derive+mix SFX ->
# composite (no color filter, subtle push-in) -> tag bt709 -> covers.
# Outputs land in <workdir>/out/.
set -euo pipefail
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
SRC="$1"; WORK="$2"; STYLE="${3:-clean}"
mkdir -p "$WORK/out"

# make the engine importable next to the per-clip timeline.py
cp -f "$SCRIPTS"/render_*.py "$SCRIPTS/build_audio.py" "$WORK/"
cd "$WORK"

echo "[1/6] HDR->SDR tonemap (AVFoundation)"
if [ ! -x "$SCRIPTS/tonemap" ]; then
  swiftc -O "$SCRIPTS/tonemap.swift" -o "$SCRIPTS/tonemap" 2>/dev/null || true
fi
if [ -x "$SCRIPTS/tonemap" ]; then
  "$SCRIPTS/tonemap" "$SRC" out/sdr_master.mov && BASE="out/sdr_master.mov"
else
  echo "  (tonemap unavailable; using source directly — check colors!)"; BASE="$SRC"
fi

echo "[2/7] render scene overlay (cutaways+hook+cta, NO captions) style=$STYLE"
python3 render_overlay_video.py "$STYLE" "out/overlay_scene_${STYLE}.mov" scene

echo "[3/7] render caption overlay (word-by-word subs ONLY, added last) style=$STYLE"
python3 render_overlay_video.py "$STYLE" "out/overlay_subs_${STYLE}.mov" subs

echo "[4/7] derive + mix SFX"
python3 build_audio.py "$SRC" "out/sfx_mix.m4a"

echo "[5/7] composite (true color, no filter, subtle push-in; captions layered LAST)"
# scale-to-cover + centered crop (not a bare non-uniform scale) so sources that
# aren't already 9:16 (this one is 640x1024) don't get horizontally squeezed.
# Scene (cuts/hook/cta) composites onto the picture first; captions are a
# separate final layer on top so they never bake into/pick up any cutaway's
# background -- picture-lock everything else first, subtitle last.
ffmpeg -y -loglevel error -i "$BASE" -i "out/overlay_scene_${STYLE}.mov" -i "out/overlay_subs_${STYLE}.mov" -filter_complex \
"[0:v]scale=-2:1920:flags=bicubic,crop=1080:1920,zoompan=z='min(1.0+on/1600,1.09)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,setsar=1[base];[base][1:v]overlay=0:0[scene];[scene][2:v]overlay=0:0[v]" \
-map "[v]" -c:v hevc_videotoolbox -b:v 12M -tag:v hvc1 -colorspace bt709 -color_primaries bt709 -color_trc bt709 -r 30 -movflags +faststart "out/_video_${STYLE}.mp4"

echo "[6/7] mux audio + force bt709 tags"
ffmpeg -y -loglevel error -i "out/_video_${STYLE}.mp4" -i "out/sfx_mix.m4a" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -movflags +faststart "out/reel_${STYLE}.mp4"

echo "[7/7] covers (from true-color frame)"
ffmpeg -y -loglevel error -ss 5 -i "$BASE" -vf "scale=-2:1920,crop=1080:1920" -frames:v 1 -update 1 out/_face.jpg 2>/dev/null
python3 render_cover.py out/_face.jpg || true

echo "DONE -> $WORK/out/reel_${STYLE}.mp4"
ls -la "out/reel_${STYLE}.mp4" out/cover_*.jpg 2>/dev/null || true
