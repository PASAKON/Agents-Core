#!/bin/bash
# Rebuild ONE ILAG hook take end to end (task-ee1dbcf0):  make_hook.sh <take-name>
#   fal take (mp3 + json) -> align.py loader -> make_edl.py -> kit cards -> encode -> mix (-16 LUFS) -> 720p + 1080 master + 2 fps sheet
# <take-name> is a file stem in the takes folder, or a unique prefix of one:  make_hook.sh t2   or   make_hook.sh t2_George_s0.5
# Result: $HD/out/v4/<take>/hook-<take>-720p.mp4, -master-1080.mp4, -contact-2fps.jpg, timing.json   ($0 spend: local files and ffmpeg only)
# Runs one render at a time (flock on the shared lock), nice 19, and refuses when free memory is low.
# env overrides:  TAKES_DIR  HD (hookdemo work folder)  MIN_AVAIL_MB (default 1200)  LOCK  CORE_PY
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
TAKES_DIR="${TAKES_DIR:-/opt/MoonieXHQ/Work/task-e58b9235/voice-v4/takes}"
HD="${HD:-/opt/MoonieXHQ/Work/task-e58b9235/hookdemo}"
LOCK="${LOCK:-/opt/MoonieXHQ/Work/.bl-render.lock}"
CORE="${CORE:-/opt/MoonieXHQ/Agents/Core}"
CORE_PY="${CORE_PY:-$CORE/.venv/bin/python}"
MIN_AVAIL_MB="${MIN_AVAIL_MB:-1200}"
TOOL_BRANCH=agent/developer-task-b7e13b61   # ilag_cut.py + kit with build_kit() (PR #468)

if [ "${1:-}" != "--locked" ]; then
  [ $# -eq 1 ] || { echo "usage: make_hook.sh <take-name>   (takes in $TAKES_DIR)" >&2; exit 64; }
  want="$1"
  if [ -f "$TAKES_DIR/$want.mp3" ]; then stem="$want"; else
    n=$(find "$TAKES_DIR" -maxdepth 1 -type f -name "${want}_*.mp3" | wc -l)
    [ "$n" -eq 1 ] || { echo "make_hook.sh: '$want' matches $n takes in $TAKES_DIR, need exactly 1" >&2; find "$TAKES_DIR" -maxdepth 1 -name '*.mp3' >&2; exit 64; }
    stem=$(basename "$(find "$TAKES_DIR" -maxdepth 1 -type f -name "${want}_*.mp3")" .mp3)
  fi
  [ -f "$TAKES_DIR/$stem.json" ] || { echo "make_hook.sh: $TAKES_DIR/$stem.json is missing" >&2; exit 66; }
  echo "== take $stem"; free -m
  avail=$(free -m | awk '/^Mem:/{print $7}')
  [ "$avail" -ge "$MIN_AVAIL_MB" ] || { echo "make_hook.sh: only $avail MB available, need $MIN_AVAIL_MB (one render at a time, CEO rule)" >&2; exit 75; }
  # cheap checks before waiting for the lock: the loader fails loudly on a bad json
  python3 "$HERE/align.py" "$TAKES_DIR/$stem.json" "$HERE/phrases.json" --narration "$HERE/narration.txt" >/dev/null
  exec flock "$LOCK" nice -n 19 "$0" --locked "$stem"
fi

stem="$2"
mkdir -p "$HD"
if [ ! -f "$HD/_tool/tools/ilag_cut.py" ]; then
  echo "== unpacking ilag_cut + kit from $TOOL_BRANCH into $HD/_tool"
  mkdir -p "$HD/_tool"
  git -C "$CORE" archive "$TOOL_BRANCH" tools/ilag_cut.py knowledge/brand-knowledge/brands/ilag/templates | tar -x -C "$HD/_tool"
fi
[ -f "$HD/src/ep5-ep1.mp4" ] || { echo "make_hook.sh: source $HD/src/ep5-ep1.mp4 is missing" >&2; exit 66; }
OUT="$HD/out/v4/$stem"
python3 "$HERE/build.py" "$HD" --audio "$TAKES_DIR/$stem.mp3" --align "$TAKES_DIR/$stem.json" \
  --narration "$HERE/narration.txt" --py "$CORE_PY" --out "$OUT" --name "hook-$stem"
echo "== loudness"
ffmpeg -nostats -i "$OUT/hook-$stem-720p.mp4" -af ebur128=peak=true -f null - 2>&1 | awk '/Integrated loudness/{f=1} f&&/I:|Peak:/' | tr -s ' ' | head -4
ls -l "$OUT"
