#!/usr/bin/env bash
# Grab TikTok clips at the best quality the post actually offers, and say what
# you got. One link or many.
#
#   bash scripts/tiktok-grab.sh <url> [url...]
#   DEST=~/Downloads bash scripts/tiktok-grab.sh <url>
#
# Written after pulling five clips by hand on 2026-08-18/19, where two things
# kept costing a manual retry:
#
# 1. The extractor is flaky. Three of those five failed at least once with
#    "Unable to extract universal data for rehydration" and then succeeded on
#    an identical second attempt — a TikTok-side stumble, not a bad link. So
#    every yt-dlp call here retries before it is allowed to fail.
# 2. "Best quality" is per-post, not a setting. Two of the five topped out at
#    540p because that is all the uploader posted; asking for more cannot
#    produce more. This prints the full format list next to what was taken, so
#    "is that really the max?" is answered with evidence rather than assumed.
#
# Resolution is read back with ffprobe from the file on disk. What yt-dlp
# labels a format and what the container actually holds are two different
# claims, and only the second one is the file you end up with.
set -uo pipefail

DEST="${DEST:-$HOME/Desktop}"
ATTEMPTS="${ATTEMPTS:-3}"
LOG="${LOG:-${TMPDIR:-/tmp}/tiktok-grab.log}"

[[ $# -ge 1 ]] || { echo "usage: $(basename "$0") <url> [url...]"; exit 2; }
command -v yt-dlp >/dev/null || { echo "yt-dlp not installed (brew install yt-dlp)"; exit 1; }
mkdir -p "$DEST"

# Retry the flaky extractor, but only for the flaky failure. Anything else is a
# real error and is surfaced on the first try rather than slept over.
retry() {
  local out rc
  for ((i = 1; i <= ATTEMPTS; i++)); do
    out="$("$@" 2>&1)"; rc=$?
    if [[ $rc -eq 0 ]]; then printf '%s' "$out"; return 0; fi
    if ! grep -q "universal data for rehydration" <<<"$out"; then
      printf '%s' "$out"; return $rc
    fi
    sleep $((i * 3))
  done
  printf '%s' "$out"; return 1
}

failed=0
for url in "$@"; do
  echo "──────────────────────────────────────────────────"
  echo "$url"

  # Ask yt-dlp which file this URL became. The obvious shortcut — take the
  # newest .mp4 in DEST — is wrong the moment the clip is already on disk:
  # nothing new is written, so "newest" is some earlier clip, and the script
  # confidently reports the wrong file at the right size. Caught doing exactly
  # that on its first run.
  pathfile="$(mktemp)"
  if ! retry yt-dlp -f "bv*+ba/best" --no-playlist --restrict-filenames \
        --no-progress -P "$DEST" -o "%(uploader)s-%(id)s.%(ext)s" \
        --print-to-file after_move:filepath "$pathfile" "$url" >>"$LOG" 2>&1
  then
    echo "  FAILED after $ATTEMPTS attempts — see $LOG"
    rm -f "$pathfile"
    failed=$((failed + 1))
    continue
  fi
  file="$(tail -1 "$pathfile" 2>/dev/null)"
  rm -f "$pathfile"

  [[ -f "$file" ]] || { echo "  no file produced"; failed=$((failed + 1)); continue; }

  echo "  file:   $file"
  echo "  size:   $(du -h "$file" | cut -f1 | tr -d ' ')"
  if command -v ffprobe >/dev/null; then
    ffprobe -v error -select_streams v:0 \
      -show_entries stream=width,height,codec_name \
      -show_entries format=duration -of default=nw=1 "$file" |
      while IFS='=' read -r k v; do printf '  %-7s %s\n' "$k:" "$v"; done
  fi

  echo "  qualities this post offers:"
  # Format ids carry hyphens and dots (h264_540p_504335-0), so anchor on the
  # container column, not on a guess at the id's alphabet — a too-narrow class
  # silently prints one row and looks like the post only offers one quality.
  retry yt-dlp -F "$url" 2>/dev/null | grep -E "^[^ ]+ +mp4 " | sed 's/^/    /' \
    || echo "    (format list unavailable — extractor would not answer)"
done

echo "──────────────────────────────────────────────────"
if [[ $failed -gt 0 ]]; then
  echo "$failed of $# failed"
  exit 1
fi
echo "$# of $# downloaded to $DEST"
