#!/usr/bin/env bash
# video-see.sh — let a Claude session actually look at a video.
#
# Claude ingests images, never video. Every path here turns a clip into the
# cheapest picture that still answers the question being asked.
#
# The only lever that changes token cost is PIXEL DIMENSIONS. Anthropic bills
# an image at roughly (width * height) / 750 tokens, independent of the file's
# byte size -- so JPEG quality is free. Measured 2026-08-29 on a 20s 720p clip;
# that is why -q:v is pinned high below and the tiers differ only in geometry.
#
# Tiers, cheapest first. Stop at the first one that answers the question.
#
#   probe  0 tok      duration / resolution / fps / does it even have audio
#   t1     ~660 tok   12-frame grid, 272px cells -- structure, wardrobe, palette
#   t2   ~1,380 tok   12-frame grid, 392px cells -- faces, props, background
#   t3   ~1,450 tok   20-frame grid, 312px cells -- shot boundaries, pacing
#   at <N>           one full-resolution frame at second N -- artifact hunting
#   audio            strip the audio track out for a separate STT pass
#
# Usage:
#   scripts/video-see.sh probe  clip.mp4
#   scripts/video-see.sh t1     clip.mp4 [outdir]
#   scripts/video-see.sh at 12  clip.mp4 [outdir]
#   scripts/video-see.sh audio  clip.mp4 [outdir]
#
# Prints the path to read and the token estimate. Read the printed path.

set -euo pipefail

die() { echo "video-see: $*" >&2; exit 1; }

command -v ffmpeg  >/dev/null 2>&1 || die "ffmpeg not found (brew install ffmpeg)"
command -v ffprobe >/dev/null 2>&1 || die "ffprobe not found"

MODE="${1:-}"; [ -n "$MODE" ] || die "usage: video-see.sh {probe|t1|t2|t3|at <sec>|audio} <file> [outdir]"
shift

# `at` takes a second positional before the file
AT_SEC=""
if [ "$MODE" = "at" ]; then
  AT_SEC="${1:-}"; [ -n "$AT_SEC" ] || die "at: need a second, e.g. 'at 12 clip.mp4'"
  shift
fi

SRC="${1:-}"; [ -n "$SRC" ] || die "no input file"
[ -f "$SRC" ] || die "not a file: $SRC"
OUT="${2:-$(dirname "$SRC")}"
mkdir -p "$OUT"

BASE="$(basename "${SRC%.*}")"

# One ffprobe call per value. A combined -show_entries returns them on separate
# lines in an order that is not guaranteed, and stitching that back together
# silently mislabels duration as "1280,720" -- which then passes an is-it-empty
# check and corrupts every downstream number. Ask for one thing at a time.
DUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0:nk=1 "$SRC" 2>/dev/null || true)"
WIDTH="$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0:nk=1 "$SRC" 2>/dev/null | head -1 || true)"
HEIGHT="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0:nk=1 "$SRC" 2>/dev/null | head -1 || true)"

# Validate the shape, not merely the presence -- non-empty garbage is the bug
# this guard exists to catch.
case "$DUR"    in ''|*[!0-9.]*) die "could not read a numeric duration from $SRC" ;; esac
case "$WIDTH"  in ''|*[!0-9]*)  die "could not read a numeric width from $SRC" ;; esac
case "$HEIGHT" in ''|*[!0-9]*)  die "could not read a numeric height from $SRC" ;; esac

# ---- probe -----------------------------------------------------------------
if [ "$MODE" = "probe" ]; then
  echo "file     : $SRC"
  echo "size     : $(du -h "$SRC" | cut -f1)"
  echo "duration : ${DUR}s"
  echo "video    : ${WIDTH}x${HEIGHT}"
  ffprobe -v error -show_entries format=bit_rate \
    -show_entries stream=codec_type,codec_name,r_frame_rate,channels \
    -of default=noprint_wrappers=1 "$SRC"
  # A clip whose audio is digital silence needs no STT pass at all.
  VOL="$(ffmpeg -hide_banner -nostats -i "$SRC" -af volumedetect -vn -f null - 2>&1 \
         | grep -E 'mean_volume' | sed 's/.*mean_volume: //' || true)"
  if [ -z "$VOL" ]; then
    echo "audio    : none"
  else
    echo "audio    : mean $VOL  (below -80 dB means silence, skip STT)"
  fi
  exit 0
fi

# ---- audio -----------------------------------------------------------------
if [ "$MODE" = "audio" ]; then
  DEST="$OUT/$BASE.wav"
  # 16 kHz mono is what every STT engine wants; anything richer is wasted bytes.
  ffmpeg -v error -y -i "$SRC" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$DEST"
  echo "wav      : $DEST"
  echo "next     : whisper-cli -m <model> -l th -f '$DEST'   (or Deepgram, see src/video/videostt.js)"
  exit 0
fi

# ---- at <sec> --------------------------------------------------------------
if [ "$MODE" = "at" ]; then
  DEST="$OUT/$BASE.at${AT_SEC}s.jpg"
  # Cap the long edge at 1568 -- past that the API downscales and the extra
  # pixels are paid for in transfer but never seen.
  ffmpeg -v error -y -ss "$AT_SEC" -i "$SRC" \
    -vf "scale='min(1568,iw)':-2" -frames:v 1 -q:v 2 "$DEST"
  OW="$(ffprobe -v error -select_streams v:0 -show_entries stream=width  -of csv=p=0:nk=1 "$DEST" | head -1)"
  OH="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0:nk=1 "$DEST" | head -1)"
  echo "frame    : $DEST"
  echo "at       : ${AT_SEC}s of ${DUR}s"
  echo "tokens   : ~$(( OW * OH / 750 ))  (${OW}x${OH})"
  exit 0
fi

# ---- contact sheets --------------------------------------------------------
# A tier is a TOKEN BUDGET and a frame count, never a fixed pixel size. Hard-
# coding the tile width made a 9:16 clip cost 2,097 tokens at "t1 ~660" -- the
# grid grows tall when the frames are tall. Solving the tile width back out of
# the budget keeps every tier honest whatever the source aspect ratio is.
case "$MODE" in
  t1) N=12; BUDGET=660  ;;
  t2) N=12; BUDGET=1380 ;;
  t3) N=20; BUDGET=1450 ;;
  *)  die "unknown mode: $MODE" ;;
esac

read -r COLS ROWS TILE_W TILE_H <<EOF
$(python3 - "$WIDTH" "$HEIGHT" "$N" "$BUDGET" <<'PY'
import sys, math
w, h, n, budget = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])

# Grid shape does not change the pixel total -- only n does -- so pick the shape
# that keeps the sheet itself wide and readable rather than a tall ribbon.
tall = h > w
shapes = {12: (6, 2) if tall else (4, 3), 20: (10, 2) if tall else (5, 4)}
cols, rows = shapes[n]

# total_px = n * tw^2 * (h/w)  ->  tw = sqrt(budget * 750 / (n * h/w))
tw = math.sqrt(budget * 750 / (n * (h / w)))

# Nothing is gained past a 1568px long edge; the API downscales beyond it.
scale = min(1568 / (cols * tw), 1568 / (rows * tw * h / w), 1.0)
tw = int(tw * scale)

tw -= tw % 2
th = int(tw * h / w); th -= th % 2
print(cols, rows, max(tw, 2), max(th, 2))
PY
)
EOF
[ -n "${TILE_H:-}" ] || die "could not compute a grid for ${WIDTH}x${HEIGHT}"

FPS=$(python3 -c "print($N/$DUR)")

DEST="$OUT/$BASE.$MODE.jpg"
# -q:v 2 on purpose: JPEG quality does not move the token count, so there is
# no reason to hand the model a blurrier picture than it could have had.
ffmpeg -v error -y -i "$SRC" \
  -vf "fps=${FPS},scale=${TILE_W}:${TILE_H},tile=${COLS}x${ROWS}" \
  -frames:v 1 -q:v 2 "$DEST"

SHEET_W=$(( COLS * TILE_W ))
SHEET_H=$(( ROWS * TILE_H ))
STEP=$(python3 -c "print(round($DUR/$N, 2))")

echo "sheet    : $DEST"
echo "grid     : ${COLS}x${ROWS} = ${N} frames, one every ${STEP}s across ${DUR}s"
echo "reading  : left to right, top to bottom"
echo "size     : ${SHEET_W}x${SHEET_H}  (cell ${TILE_W}x${TILE_H})"
echo "tokens   : ~$(( SHEET_W * SHEET_H / 750 ))"
