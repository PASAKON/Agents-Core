#!/usr/bin/env bash
# video-see.sh — let a Claude session actually look at a video.
#
# Claude ingests images, never video. Every path here turns a clip into the
# cheapest artefact that still answers the question being asked, and the
# cheapest artefact is very often not a picture at all.
#
#   screen  0 tok   cuts, frozen frames, black frames, spec check
#   dup     0 tok   which clips are the same clip
#   probe   0 tok   duration / resolution / does it even have audio
#   t1    ~660 tok  12-frame grid  -- structure, wardrobe, palette
#   t2  ~1,380 tok  12-frame grid  -- faces, props, background
#   t3  ~1,450 tok  20-frame grid  -- shot boundaries, pacing
#   at <N>          one full-resolution frame -- artefact hunting
#   audio           strip the audio track for a separate STT pass
#   note            append a verdict to video-notes.md
#
# Two things measured on 2026-08-29 rather than assumed, both of which
# changed the design:
#
#   Token cost tracks PIXEL DIMENSIONS only, never file bytes. JPEG quality
#   is therefore free, so -q:v stays high; compressing harder buys disk space
#   and a blurrier picture, nothing else.
#
#   A tier has to be a token budget, not a fixed tile width. Hard-coding
#   272px made a 9:16 clip cost 2,097 tokens under a tier labelled ~660,
#   because a grid of tall frames grows tall. Solving the tile width back out
#   of the budget holds every tier to its number at 16:9, 9:16 and 1:1.
#
# Run it on this machine. Pushing the work to Contabo was measured at 11.0s
# round trip (4.56 up + 5.22 ffmpeg + 1.22 back) against 0.96s locally -- the
# M1's hardware decoder beats 4 EPYC vCPUs even before the upload.
#
# Usage:
#   scripts/video-see.sh screen a.mp4 b.mp4 c.mp4
#   scripts/video-see.sh dup    *.mp4
#   scripts/video-see.sh t1     a.mp4 [b.mp4 c.mp4]      (max 3)
#   scripts/video-see.sh at 12  a.mp4
#   scripts/video-see.sh note   a.mp4 "face drifts after the second cut"
#   -o <dir>   where artefacts land (default: alongside the clip)

set -euo pipefail

# This box's locale uses a comma for the decimal separator, so printf %f
# rejects ffprobe's "20.064000" outright and set -e takes the whole loop with
# it. Numbers here are machine output, never display text -- pin them to C.
export LC_NUMERIC=C

# The cap is deliberate, not a limitation. Looking at a pile of clips in one
# breath is how frames blur together and clip 7 gets judged on clip 3's face;
# the fix is one clip at a time with a written verdict between, not a bigger
# batch. CEO 2026-08-29.
MAX_CLIPS=3

die() { echo "video-see: $*" >&2; exit 1; }

command -v ffmpeg  >/dev/null 2>&1 || die "ffmpeg not found (brew install ffmpeg)"
command -v ffprobe >/dev/null 2>&1 || die "ffprobe not found"

OUT_OVERRIDE=""
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    -o) OUT_OVERRIDE="${2:-}"; [ -n "$OUT_OVERRIDE" ] || die "-o needs a directory"; shift 2 ;;
    *)  ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}

MODE="${1:-}"
[ -n "$MODE" ] || die "usage: video-see.sh {screen|dup|probe|t1|t2|t3|at <sec>|audio|note} <file...>"
shift

AT_SEC=""
if [ "$MODE" = "at" ]; then
  AT_SEC="${1:-}"; [ -n "$AT_SEC" ] || die "at: need a second, e.g. 'at 12 clip.mp4'"
  shift
fi

NOTE_TEXT=""
if [ "$MODE" = "note" ]; then
  [ $# -ge 2 ] || die "note: usage 'note <clip> \"<verdict>\"'"
  NOTE_TEXT="${*:2}"
  set -- "$1"
fi

[ $# -ge 1 ] || die "no input file"
for f in "$@"; do [ -f "$f" ] || die "not a file: $f"; done

outdir_for() { [ -n "$OUT_OVERRIDE" ] && echo "$OUT_OVERRIDE" || dirname "$1"; }

# ffprobe is queried one value at a time. A combined -show_entries returns them
# on separate lines in no guaranteed order, and stitching that back together
# assigned "1280,720" to duration -- which then sailed through an is-it-empty
# guard and corrupted every derived number downstream.
probe_val() { ffprobe -v error ${2:+-select_streams v:0} -show_entries "$1" -of csv=p=0:nk=1 "$3" 2>/dev/null | head -1; }

load_dims() { # sets DUR WIDTH HEIGHT for $1
  DUR="$(probe_val format=duration '' "$1")"
  WIDTH="$(probe_val stream=width v "$1")"
  HEIGHT="$(probe_val stream=height v "$1")"
  # Validate the shape, not merely the presence -- non-empty garbage is the
  # bug these guards exist to catch.
  case "$DUR"    in ''|*[!0-9.]*) die "no numeric duration in $1 -- is it a video?" ;; esac
  case "$WIDTH"  in ''|*[!0-9]*)  die "no numeric width in $1" ;; esac
  case "$HEIGHT" in ''|*[!0-9]*)  die "no numeric height in $1" ;; esac
}

# ---- screen: the whole free tier ------------------------------------------
if [ "$MODE" = "screen" ]; then
  for f in "$@"; do
    load_dims "$f"
    FPS_R="$(probe_val stream=r_frame_rate v "$f")"
    FPS="$(python3 -c "n,d='${FPS_R:-0/1}'.split('/'); print(round(int(n)/max(int(d),1),2))")"
    echo "$(basename "$f")"
    printf '  spec    %.2fs  %sx%s  %sfps  %s\n' "$DUR" "$WIDTH" "$HEIGHT" "$FPS" "$(du -h "$f" | cut -f1 | tr -d ' ')"

    CUTS="$(ffmpeg -hide_banner -i "$f" -vf "scdet=t=12,metadata=print:key=lavfi.scd.time:file=-" \
            -f null - 2>&1 | grep -oE "lavfi\.scd\.time=[0-9.]+" | cut -d= -f2 | tr '\n' ' ' || true)"
    if [ -z "$CUTS" ]; then
      echo "  cuts    none (single continuous shot)"
    else
      echo "  cuts    ${CUTS}  -> $(( $(echo "$CUTS" | wc -w) + 1 )) shots"
    fi

    # A frozen stretch is a real generator failure, not a stylistic choice.
    FRZ="$(ffmpeg -hide_banner -i "$f" -vf "freezedetect=n=-50dB:d=0.5" -map 0:v -f null - 2>&1 \
           | grep -oE "freeze_start: [0-9.]+" | cut -d' ' -f2 | tr '\n' ' ' || true)"
    [ -z "$FRZ" ] && echo "  freeze  none" || echo "  freeze  FROZEN at ${FRZ}s"

    BLK="$(ffmpeg -hide_banner -i "$f" -vf "blackdetect=d=0.3:pix_th=0.10" -f null - 2>&1 \
           | grep -oE "black_start:[0-9.]+" | cut -d: -f2 | tr '\n' ' ' || true)"
    [ -z "$BLK" ] && echo "  black   none" || echo "  black   BLACK at ${BLK}s"

    VOL="$(ffmpeg -hide_banner -nostats -i "$f" -af volumedetect -vn -f null - 2>&1 \
           | grep -E 'mean_volume' | sed 's/.*mean_volume: //' || true)"
    [ -z "$VOL" ] && echo "  audio   none" || echo "  audio   mean $VOL"
    echo
  done
  echo "0 image tokens spent. Escalate only what looks wrong."
  exit 0
fi

# ---- dup: which of these are the same clip --------------------------------
if [ "$MODE" = "dup" ]; then
  [ $# -ge 2 ] || die "dup: need at least two files"
  python3 - "$@" <<'PY'
import subprocess, sys, os

def duration(p):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","csv=p=0:nk=1",p], capture_output=True, text=True)
    try: return max(float(r.stdout.strip()), 0.1)
    except ValueError: return 0.1

def sig(p, n=16):
    # Sample across the WHOLE clip. Sampling at a fixed fps instead reads only
    # the opening second, and two different takes of the same scene share an
    # opening -- which makes everything look like a duplicate.
    fps = n / duration(p)
    raw = subprocess.run(
        ["ffmpeg","-v","error","-i",p,"-vf",f"fps={fps},scale=9:8,format=gray",
         "-frames:v",str(n),"-f","rawvideo","-"], capture_output=True).stdout
    out = []
    for f in range(len(raw)//72):
        b = raw[f*72:(f+1)*72]; bits = 0
        for r in range(8):
            for c in range(8):
                bits = (bits << 1) | (1 if b[r*9+c] > b[r*9+c+1] else 0)
        out.append(bits)
    return out

def dist(a, b):
    if not a or not b: return 64.0
    m = min(len(a), len(b))
    return sum(bin(a[i] ^ b[i]).count("1") for i in range(m)) / m

paths = sys.argv[1:]
sigs = {p: sig(p) for p in paths}
# Separation measured at 0.2 bits for a re-encode of the same clip against
# 40.4 for unrelated footage, so the thresholds sit in a very wide valley.
hits = 0
for i in range(len(paths)):
    for j in range(i+1, len(paths)):
        d = dist(sigs[paths[i]], sigs[paths[j]])
        if d < 8:    tag, mark = "DUPLICATE", "!"
        elif d < 16: tag, mark = "similar  ", "?"
        else:        continue
        hits += 1
        print(f"  {mark} {d:5.1f} bits  {tag}  {os.path.basename(paths[i])}  vs  {os.path.basename(paths[j])}")
print("  no duplicates" if not hits else "")
print("0 image tokens spent.")
PY
  exit 0
fi

# ---- note: the written verdict --------------------------------------------
if [ "$MODE" = "note" ]; then
  SRC="$1"; OUT="$(outdir_for "$SRC")"; mkdir -p "$OUT"
  NOTES="$OUT/video-notes.md"
  [ -f "$NOTES" ] || printf '# Video review notes\n\n' > "$NOTES"
  printf -- '- `%s` — %s — %s\n' "$(basename "$SRC")" "$(date '+%Y-%m-%d %H:%M')" "$NOTE_TEXT" >> "$NOTES"
  echo "noted    : $NOTES"
  exit 0
fi

# Everything past here spends image tokens, so the cap applies.
[ $# -le "$MAX_CLIPS" ] || die "$# clips given, cap is $MAX_CLIPS per run. Look at $MAX_CLIPS, write a note for each, then run again."

# ---- probe ----------------------------------------------------------------
if [ "$MODE" = "probe" ]; then
  for f in "$@"; do
    load_dims "$f"
    echo "file     : $f"
    echo "size     : $(du -h "$f" | cut -f1 | tr -d ' ')"
    echo "duration : ${DUR}s"
    echo "video    : ${WIDTH}x${HEIGHT}"
    VOL="$(ffmpeg -hide_banner -nostats -i "$f" -af volumedetect -vn -f null - 2>&1 \
           | grep -E 'mean_volume' | sed 's/.*mean_volume: //' || true)"
    [ -z "$VOL" ] && echo "audio    : none" \
                  || echo "audio    : mean $VOL  (below -80 dB is silence, skip STT)"
    echo
  done
  exit 0
fi

# ---- audio ----------------------------------------------------------------
if [ "$MODE" = "audio" ]; then
  for f in "$@"; do
    OUT="$(outdir_for "$f")"; mkdir -p "$OUT"
    DEST="$OUT/$(basename "${f%.*}").wav"
    # 16 kHz mono is what every STT engine wants; richer is wasted bytes.
    ffmpeg -v error -y -i "$f" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$DEST"
    echo "wav      : $DEST"
  done
  echo "next     : whisper-cli -m <model> -l th -f <wav>   (or Deepgram, src/video/videostt.js)"
  exit 0
fi

# ---- at <sec> -------------------------------------------------------------
if [ "$MODE" = "at" ]; then
  for f in "$@"; do
    load_dims "$f"
    OUT="$(outdir_for "$f")"; mkdir -p "$OUT"
    DEST="$OUT/$(basename "${f%.*}").at${AT_SEC}s.jpg"
    # Cap the long edge at 1568 -- the API downscales past that, so the extra
    # pixels are paid for in transfer and never seen.
    ffmpeg -v error -y -ss "$AT_SEC" -i "$f" -vf "scale='min(1568,iw)':-2" -frames:v 1 -q:v 2 "$DEST"
    OW="$(probe_val stream=width v "$DEST")"; OH="$(probe_val stream=height v "$DEST")"
    echo "frame    : $DEST"
    echo "at       : ${AT_SEC}s of ${DUR}s"
    echo "tokens   : ~$(( OW * OH / 750 ))  (${OW}x${OH})"
  done
  exit 0
fi

# ---- contact sheets -------------------------------------------------------
case "$MODE" in
  t1) N=12; BUDGET=660  ;;
  t2) N=12; BUDGET=1380 ;;
  t3) N=20; BUDGET=1450 ;;
  *)  die "unknown mode: $MODE" ;;
esac

TOTAL=0
for f in "$@"; do
  load_dims "$f"
  OUT="$(outdir_for "$f")"; mkdir -p "$OUT"

  read -r COLS ROWS TILE_W TILE_H <<EOF
$(python3 - "$WIDTH" "$HEIGHT" "$N" "$BUDGET" <<'PY'
import sys, math
w, h, n, budget = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
# Grid shape does not change the pixel total -- only n does -- so pick the
# shape that keeps the sheet wide and readable rather than a tall ribbon.
tall = h > w
cols, rows = {12: (6, 2) if tall else (4, 3), 20: (10, 2) if tall else (5, 4)}[n]
# total_px = n * tw^2 * (h/w)  ->  tw = sqrt(budget * 750 / (n * h/w))
tw = math.sqrt(budget * 750 / (n * (h / w)))
tw = int(tw * min(1568 / (cols * tw), 1568 / (rows * tw * h / w), 1.0))
tw -= tw % 2
th = int(tw * h / w); th -= th % 2
print(cols, rows, max(tw, 2), max(th, 2))
PY
)
EOF
  [ -n "${TILE_H:-}" ] || die "could not compute a grid for ${WIDTH}x${HEIGHT}"

  FPS=$(python3 -c "print($N/$DUR)")
  DEST="$OUT/$(basename "${f%.*}").$MODE.jpg"
  # -q:v 2 on purpose: JPEG quality does not move the token count, so there is
  # no reason to hand the model a blurrier picture than it could have had.
  ffmpeg -v error -y -i "$f" \
    -vf "fps=${FPS},scale=${TILE_W}:${TILE_H},tile=${COLS}x${ROWS}" \
    -frames:v 1 -q:v 2 "$DEST"

  SW=$(( COLS * TILE_W )); SH=$(( ROWS * TILE_H ))
  TOK=$(( SW * SH / 750 )); TOTAL=$(( TOTAL + TOK ))
  STEP=$(python3 -c "print(round($DUR/$N, 2))")

  echo "sheet    : $DEST"
  echo "grid     : ${COLS}x${ROWS} = ${N} frames, one every ${STEP}s across ${DUR}s"
  echo "reading  : left to right, top to bottom"
  echo "size     : ${SW}x${SH}  (cell ${TILE_W}x${TILE_H})"
  echo "tokens   : ~${TOK}"
  echo
done

[ $# -gt 1 ] && echo "total    : ~${TOTAL} tokens for $# clips"
echo "after    : video-see.sh note <clip> \"<verdict>\"  -- write it down before the next clip"
