#!/bin/bash
# Rebuild ONE ILAG hook take end to end (task-ee1dbcf0):  make_hook.sh <take-name>
#   fal take (mp3 + json) -> align.py loader -> make_edl.py -> kit cards -> encode -> mix (-16 LUFS) -> 720p + 1080 master + 2 fps sheet
# <take-name> is a file stem in the takes folder, or a unique prefix of one:  make_hook.sh t2   or   make_hook.sh t2_George_s0.5
# Result: $OUT_ROOT/<take>/hook-<take>-720p.mp4, -master-1080.mp4, -contact-2fps.jpg, timing.json   ($0 spend: local files and ffmpeg only)
# Runs one render at a time (flock on the shared lock), nice 19, and refuses when free memory is low.
# ilag_cut.py and the kit come from origin/main (fetched first, unpacked once per commit into $HD/_tool-<sha8>), and each
# commit gets its own work folder, so a newer tool never reuses segments encoded by an older one.
# A take with pace tags in its alignment ("[rushed] ...") needs nothing special: align.py drops every [...] run.
#   TAKES_DIR=/opt/MoonieXHQ/Work/task-e58b9235/voice-v4-fast/takes make_hook.sh f1
# env overrides:  TAKES_DIR  HD (hookdemo work folder)  OUT_ROOT (default $HD/out/v4-main)  MIN_AVAIL_MB (default 1200)  LOCK  CORE_PY
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
TAKES_DIR="${TAKES_DIR:-/opt/MoonieXHQ/Work/task-e58b9235/voice-v4/takes}"
HD="${HD:-/opt/MoonieXHQ/Work/task-e58b9235/hookdemo}"
LOCK="${LOCK:-/opt/MoonieXHQ/Work/.bl-render.lock}"
CORE="${CORE:-/opt/MoonieXHQ/Agents/Core}"
CORE_PY="${CORE_PY:-$CORE/.venv/bin/python}"
MIN_AVAIL_MB="${MIN_AVAIL_MB:-1200}"
OUT_ROOT="${OUT_ROOT:-$HD/out/v4-main}"

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
  # ilag_cut.py + the kit as they are on origin/main now (#468 merged; main's render_kit.py has build_kit())
  git -C "$HERE" fetch -q origin +main:refs/remotes/origin/main
  TOOL_SHA=$(git -C "$HERE" rev-parse refs/remotes/origin/main)
  git -C "$HERE" show "$TOOL_SHA:knowledge/brand-knowledge/brands/ilag/templates/render_kit.py" | grep -q "def build_kit" \
    || { echo "make_hook.sh: render_kit.py at origin/main $TOOL_SHA has no build_kit(), ilag_cut would crash" >&2; exit 70; }
  echo "== tool from origin/main $TOOL_SHA"
  export TOOL_SHA
  exec flock "$LOCK" nice -n 19 "$0" --locked "$stem"
fi

stem="$2"
mkdir -p "$HD"
SHA8="${TOOL_SHA:0:8}"
TOOL="$HD/_tool-$SHA8"
if [ ! -f "$TOOL/tools/ilag_cut.py" ]; then
  echo "== unpacking ilag_cut + kit from origin/main $SHA8 into $TOOL"
  mkdir -p "$TOOL.part"
  git -C "$HERE" archive "$TOOL_SHA" tools/ilag_cut.py knowledge/brand-knowledge/brands/ilag/templates \
    knowledge/brand-knowledge/brands/ilag/images/ilag-page-logo-1080.jpg | tar -x -C "$TOOL.part"
  mv "$TOOL.part" "$TOOL"
fi
[ -f "$HD/src/ep5-ep1.mp4" ] || { echo "make_hook.sh: source $HD/src/ep5-ep1.mp4 is missing" >&2; exit 66; }
OUT="$OUT_ROOT/$stem"
python3 "$HERE/build.py" "$HD" --audio "$TAKES_DIR/$stem.mp3" --align "$TAKES_DIR/$stem.json" \
  --narration "$HERE/narration.txt" --py "$CORE_PY" --out "$OUT" --name "hook-$stem" --work-name "hook-$stem-$SHA8" \
  --ilag-cut "$TOOL/tools/ilag_cut.py" --kit "$TOOL/knowledge/brand-knowledge/brands/ilag/templates"
echo "== loudness"
ffmpeg -nostats -i "$OUT/hook-$stem-720p.mp4" -af ebur128=peak=true -f null - 2>&1 | awk '/Integrated loudness/{f=1} f&&/I:|Peak:/' | tr -s ' ' | head -4
ls -l "$OUT"
