#!/bin/bash
# Rebuild teaser-ngoen-tee-por-th.mp4 from the 7 source clips + teaser-th.srt.
# Run from the repo root: bash docs/reports/teaser-subtitled-20260917/render.sh
#
# This machine's ffmpeg (8.1, homebrew) has no libass/drawtext compiled in,
# so subtitle burn-in can't use the usual `-vf subtitles=...` filter. Instead
# render_subs_overlay.py draws the Thai text with PIL into a transparent
# ProRes4444 alpha .mov, then ffmpeg's `overlay` filter composites it on top —
# the same two-layer approach reel-editor-th's build.sh uses for captions.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
cd "$REPO_ROOT"

SRT="$HERE/teaser-th.srt"
OUT="$HERE/teaser-ngoen-tee-por-th.mp4"
OVERLAY="$HERE/.overlay-subs.mov"
BASE="$HERE/.base-teaser.mp4"

# 1. Assemble the base teaser from the 7 paid-for source clips, in order.
CLIPS=(
  "docs/reports/teaser-shoot-winbox-20260907/shot01.mp4"
  "docs/reports/teaser-shoot-winbox-20260907/shot02.mp4"
  "docs/reports/omni-voiced-scene-20260908/shot54-omni.mp4"
  "docs/reports/omni-voiced-scene-20260908/shot55-omni.mp4"
  "docs/reports/teaser-shoot-winbox-20260907-run2/shot56.mp4"
  "docs/reports/omni-voiced-scene-20260908/shot57-omni.mp4"
  "docs/reports/omni-vs-veo-shot58-20260908/shot58-omni.mp4"
)

CONCAT_LIST="$HERE/.concat-list.txt"
: > "$CONCAT_LIST"
for c in "${CLIPS[@]}"; do
  echo "file '$REPO_ROOT/$c'" >> "$CONCAT_LIST"
done

ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" -c copy "$BASE"
rm -f "$CONCAT_LIST"

# 2. Render the Thai subtitle overlay (transparent ProRes4444 alpha .mov)
#    sized/timed to match the base teaser.
source /Users/gob/.claude/skills/reel-editor-th/.venv/bin/activate
python3 "$HERE/render_subs_overlay.py" "$BASE" "$SRT" "$OVERLAY"

# 3. Composite: base + subtitle overlay -> final delivery mp4.
ffmpeg -y -i "$BASE" -i "$OVERLAY" \
  -filter_complex "[0:v][1:v]overlay=0:0:format=auto[v]" \
  -map "[v]" -map 0:a? \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  "$OUT"

rm -f "$BASE" "$OVERLAY"
echo "done -> $OUT"
