#!/usr/bin/env bash
# Grab the video behind a link — one entry point for every site, including the
# ones yt-dlp refuses.
#
#   bash scripts/threads-grab.sh <url> [url...]
#   DEST=~/Downloads bash scripts/threads-grab.sh <url>
#
# Thin wrapper over lib/video_grab.py (task-c7d455aa D2) — that module is now
# the ONE implementation of "given a URL, produce a local video file" (yt-dlp
# first, then a Threads/Googlebot-JSON path for the hosts yt-dlp refuses; see
# its module docstring for the full layered strategy, the Googlebot-UA
# measurements, and the caption-anchoring rule this script used to carry
# inline before the refactor). This file now only handles argv/env defaults,
# turns the module's one-line JSON result into fixed lines, and prints —
# ffprobe verification and `.part` cleanup both moved into lib/video_grab.py
# so there is a single implementation of each, not two that can drift.
#
# The CLI output contract is unchanged from before this refactor (verified
# live, task-c7d455aa D9):
#
#   ──────────────────────────────────────────────────
#   <url>
#     via:    yt-dlp | threads (embedded JSON, Googlebot UA)
#     file:   <path>
#     size:   <du -h>
#     caption: <only printed when one was found>
#       <ffprobe stream/format info, indented 4 spaces>
#   ──────────────────────────────────────────────────
#   N of N downloaded to DEST   (or "K of N failed", exit 1)
#
# A failed URL always prints just "FAILED — nothing downloaded (see $LOG)" —
# the real reason is in $LOG, never on stdout, same as before.
set -uo pipefail

DEST="${DEST:-$HOME/Desktop}"
ATTEMPTS="${ATTEMPTS:-3}"
LOG="${LOG:-${TMPDIR:-/tmp}/threads-grab.log}"
# A vertical phone clip is the normal case here, so a 1-minute cap would be
# wrong; these bound a hung CDN/page fetch, not clip length.
CURL_MAX_TIME="${CURL_MAX_TIME:-300}"
FETCH_TIMEOUT="${FETCH_TIMEOUT:-30}"

[[ $# -ge 1 ]] || { echo "usage: $(basename "$0") <url> [url...]"; exit 2; }
command -v python3 >/dev/null || { echo "python3 not found"; exit 1; }
mkdir -p "$DEST"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
GRAB_PY="$ROOT/lib/video_grab.py"

# lib/video_grab.py needs `ROOT` on sys.path for its own `from lib.link_reader
# import ...` — running it by absolute file path only puts lib/ itself
# (its own directory) on sys.path[0], not ROOT.
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Six fixed lines out of one JSON blob: status / via / file / caption /
# reason / probe. `probe` is printed LAST and may itself be multi-line
# (ffprobe's default=nw=1 output), so nothing else depends on a fixed line
# count -- the caller reads lines 1-5 with `sed -n Np` and everything from
# line 6 on (`tail -n +6`) is the probe block, verbatim.
_parse_result() {
  python3 -c '
import json, sys
try:
    d = json.loads(sys.argv[1])
except Exception:
    d = {}
for k in ("status", "via", "path", "caption", "reason"):
    v = d.get(k)
    print(v if v is not None else "")
print(d.get("probe") or "", end="")
' "$1"
}

failed=0
for url in "$@"; do
  echo "──────────────────────────────────────────────────"
  echo "$url"

  out_json="$(python3 "$GRAB_PY" "$url" "$DEST" "$ATTEMPTS" "$CURL_MAX_TIME" "$FETCH_TIMEOUT" 2>>"$LOG")"
  { echo "── $url"; echo "${out_json:-(no output)}"; } >>"$LOG"
  [[ -n "$out_json" ]] || out_json='{}'

  parsed="$(_parse_result "$out_json")"
  status="$(sed -n '1p' <<<"$parsed")"
  via="$(sed -n '2p' <<<"$parsed")"
  file="$(sed -n '3p' <<<"$parsed")"
  caption="$(sed -n '4p' <<<"$parsed")"
  probe="$(tail -n +6 <<<"$parsed")"

  if [[ "$status" != "ok" || -z "$file" || ! -f "$file" ]]; then
    echo "  FAILED — nothing downloaded (see $LOG)"
    failed=$((failed + 1))
    continue
  fi

  echo "  via:    $via"
  echo "  file:   $file"
  echo "  size:   $(du -h "$file" | cut -f1 | tr -d ' ')"
  [[ -n "$caption" ]] && echo "  caption: $caption"
  [[ -n "$probe" ]] && sed 's/^/    /' <<<"$probe"
done

echo "──────────────────────────────────────────────────"
if [[ $failed -gt 0 ]]; then
  echo "$failed of $# failed"
  exit 1
fi
echo "$# of $# downloaded to $DEST"
