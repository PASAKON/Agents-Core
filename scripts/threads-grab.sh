#!/usr/bin/env bash
# Grab the video behind a link — one entry point for every site, including the
# ones yt-dlp refuses.
#
#   bash scripts/threads-grab.sh <url> [url...]
#   DEST=~/Downloads bash scripts/threads-grab.sh <url>
#
# Two paths, tried in that order:
#
#   1. yt-dlp. Covers YouTube, TikTok, Facebook, Instagram, X and ~1800 other
#      sites, and it is somebody else's job to keep those extractors working.
#      Always try it first; never hand-roll what it already does.
#   2. Threads. yt-dlp answers `ERROR: Unsupported URL` for threads.com AND
#      threads.net (measured 2026-08-24, both domains), so a Threads link dies
#      at step 1 no matter how it is spelled. This walks Meta's own embedded
#      JSON instead — see the Googlebot note below for why that is not as
#      fragile as it sounds.
#
# The Googlebot user-agent is load-bearing, not a flourish. The same Threads
# post, fetched three ways on 2026-08-24:
#
#     normal browser UA     260,562 chars   0 og: tags      JS shell, nothing
#     facebookexternalhit   547,292 chars   og: present     no video JSON
#     Googlebot/2.1         627,533 chars   og: present     video JSON present
#
# Meta serves materially different HTML per crawler UA. Only the Googlebot
# variant carries `"video_versions"`, so only that one can be downloaded from.
# This is the same ladder lib/link_reader.py walks for read_link, kept
# deliberately consistent with it.
#
# Every file is verified with ffprobe before it is called a success. A CDN that
# hands back an error page still writes bytes to disk, and "the file exists and
# is 40KB" is not evidence that a video was downloaded.
set -uo pipefail

DEST="${DEST:-$HOME/Desktop}"
ATTEMPTS="${ATTEMPTS:-3}"
LOG="${LOG:-${TMPDIR:-/tmp}/threads-grab.log}"

[[ $# -ge 1 ]] || { echo "usage: $(basename "$0") <url> [url...]"; exit 2; }
command -v python3 >/dev/null || { echo "python3 not found"; exit 1; }
mkdir -p "$DEST"

# A vertical phone clip is the normal case here, so a 1-minute cap would be
# wrong; these are bounded to stop a hung CDN, not to limit length.
CURL_MAX_TIME="${CURL_MAX_TIME:-300}"
FETCH_TIMEOUT="${FETCH_TIMEOUT:-30}"

GOOGLEBOT_UA="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
BROWSER_UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# Report what the container actually holds, not what the download claimed.
# Returns non-zero when the file is not a decodable video, which is how a
# saved error page gets caught instead of being reported as a clip.
describe() {
  local f="$1" info
  command -v ffprobe >/dev/null || { echo "    (ffprobe not installed — cannot verify)"; return 0; }
  info="$(ffprobe -v error -select_streams v:0 \
            -show_entries stream=width,height,codec_name \
            -show_entries format=duration -of default=nw=1 "$f" 2>&1)" || return 1
  [[ -n "$info" ]] || return 1
  sed 's/^/    /' <<<"$info"
}

# yt-dlp's extractors stumble transiently (TikTok especially — three of five
# clips on 2026-08-18 failed once with "Unable to extract universal data for
# rehydration" and then succeeded unchanged). Retry only that signature; any
# other error is real and is surfaced on the first try rather than slept over.
ytdlp_grab() {
  local url="$1" pathfile marker out rc i
  command -v yt-dlp >/dev/null || return 1
  pathfile="$(mktemp)"
  # A failed yt-dlp run abandons its .part file in DEST. Two dead YouTube
  # attempts left 121 MB of them sitting there on the first real test of this
  # script — on the CEO's Desktop, by default. Cleanup is scoped by
  # mtime-newer-than-this-marker so it can only ever remove leftovers from
  # THIS run, never a concurrent grab's in-flight download.
  marker="$(mktemp)"
  for ((i = 1; i <= ATTEMPTS; i++)); do
    out="$(yt-dlp -f "bv*+ba/best" --no-playlist --restrict-filenames \
             --no-progress -P "$DEST" -o "%(uploader)s-%(id)s.%(ext)s" \
             --print-to-file after_move:filepath "$pathfile" "$url" 2>&1)"
    rc=$?
    printf '%s\n' "$out" >>"$LOG"
    [[ $rc -eq 0 ]] && break
    # "Unsupported URL" means yt-dlp will never handle this host. Fail fast so
    # the caller falls through to path 2 instead of sleeping through retries
    # that cannot change the answer.
    grep -q "Unsupported URL" <<<"$out" && { _ytdlp_cleanup "$pathfile" "$marker"; return 2; }
    grep -q "universal data for rehydration" <<<"$out" || { _ytdlp_cleanup "$pathfile" "$marker"; return 1; }
    sleep $((i * 3))
  done
  [[ $rc -eq 0 ]] || { _ytdlp_cleanup "$pathfile" "$marker"; return 1; }
  YTDLP_FILE="$(tail -1 "$pathfile" 2>/dev/null)"
  rm -f "$pathfile" "$marker"
  [[ -f "$YTDLP_FILE" ]]
}

_ytdlp_cleanup() {
  local pathfile="$1" marker="$2"
  find "$DEST" -maxdepth 1 -name '*.part' -newer "$marker" -delete 2>/dev/null
  rm -f "$pathfile" "$marker"
}

# Pull the highest-quality video URL out of Meta's embedded JSON.
# `type` is Meta's quality tier and sorts ascending-is-better (101 above 102),
# so the list is ordered by it rather than trusting document order.
threads_video_url() {
  local url="$1"
  python3 - "$url" "$GOOGLEBOT_UA" "$FETCH_TIMEOUT" <<'PY'
import json, re, sys, urllib.request

url, ua, timeout = sys.argv[1], sys.argv[2], float(sys.argv[3])
try:
    req = urllib.request.Request(url, headers={"User-Agent": ua,
                                                "Accept-Language": "th,en;q=0.8"})
    html = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
except Exception as e:
    print(f"ERR fetch failed: {e}", file=sys.stderr)
    sys.exit(1)

start = html.find('"video_versions"')
if start == -1:
    # Distinguish "this post has no video" from "we got the wrong page".
    # Only the first is worth telling the user to stop retrying about.
    kind = "no video in this post (text/image only?)" if '"caption"' in html \
           else "page carried no post data (login wall, or Meta changed the payload)"
    print(f"ERR {kind}", file=sys.stderr)
    sys.exit(1)

window = html[start:start + 20000]
pairs = re.findall(r'"type"\s*:\s*(\d+)\s*,\s*"url"\s*:\s*"([^"]+)"', window)
if not pairs:
    print("ERR video_versions present but held no usable url", file=sys.stderr)
    sys.exit(1)
pairs.sort(key=lambda p: int(p[0]))
print(json.loads('"' + pairs[0][1] + '"'))          # unescape \/ and \uXXXX

def unescape(s):
    return json.loads('"' + s + '"')

m = re.search(r'"username"\s*:\s*"([^"]{1,40})"', html)
print(unescape(m.group(1)) if m else "")

# The caption must be ANCHORED TO THE VIDEO, never "the first caption on the
# page". A Threads post page carries the post's own caption plus every reply
# under it, all in the same `"caption":{"text":...}` shape, and Meta does not
# order them predictably between fetches. Measured on this page (2026-08-24),
# distance from `"video_versions"`:
#
#     +9,100  'อยากจีบแต่วาสนาไม่ถึง😭'   <- the post itself
#    +15,080  'Hi DM'                      <- a reply
#    +20,990  'เค้าชอบทรงน้้'              <- a reply
#     ... seven more replies, ~6,000 chars apart
#
# Taking the first match returned a REPLY as if it were the post's own words
# on the very first run of this script. Closest-to-the-video wins instead,
# measured in both directions so a page that puts the caption before the media
# still resolves correctly.
caps = [(abs(m.start() - start), m.group(1)) for m in
        re.finditer(r'"caption"\s*:\s*\{[^{}]*"text"\s*:\s*"([^"]{1,300})"', html)]
print(unescape(min(caps)[1]).replace("\n", " ") if caps else "")
PY
}

threads_grab() {
  local url="$1" meta video user caption code out
  meta="$(threads_video_url "$url" 2>>"$LOG")" || return 1
  video="$(sed -n 1p <<<"$meta")"
  user="$(sed -n 2p <<<"$meta")"
  caption="$(sed -n 3p <<<"$meta")"
  [[ -n "$video" ]] || return 1

  # Post code from the URL itself — the CDN filename is a signed blob and
  # carries nothing a human would recognise.
  code="$(sed -E 's#.*/post/([A-Za-z0-9_-]+).*#\1#' <<<"$url")"
  out="$DEST/${user:-threads}-${code}.mp4"

  # Referer matters: fbcdn refuses some requests that arrive without one.
  curl -sL --max-time "$CURL_MAX_TIME" --fail \
       -A "$BROWSER_UA" -e "https://www.threads.com/" \
       -o "$out" "$video" 2>>"$LOG" || { rm -f "$out"; return 1; }
  THREADS_FILE="$out"
  THREADS_CAPTION="$caption"
  [[ -s "$out" ]]
}

failed=0
for url in "$@"; do
  echo "──────────────────────────────────────────────────"
  echo "$url"
  file=""
  caption=""

  YTDLP_FILE=""; THREADS_FILE=""; THREADS_CAPTION=""
  ytdlp_grab "$url"
  case $? in
    0) file="$YTDLP_FILE"; echo "  via:    yt-dlp" ;;
    2) # yt-dlp does not know this host — Threads lands here.
       if threads_grab "$url"; then
         file="$THREADS_FILE"; caption="$THREADS_CAPTION"
         echo "  via:    threads (embedded JSON, Googlebot UA)"
       fi ;;
    *) # yt-dlp knows the host but failed. Worth one Threads attempt anyway if
       # the link is a Threads link spelled a way yt-dlp half-recognised.
       if [[ "$url" == *threads.com* || "$url" == *threads.net* ]] && threads_grab "$url"; then
         file="$THREADS_FILE"; caption="$THREADS_CAPTION"
         echo "  via:    threads (embedded JSON, Googlebot UA)"
       fi ;;
  esac

  if [[ -z "$file" || ! -f "$file" ]]; then
    echo "  FAILED — nothing downloaded (see $LOG)"
    failed=$((failed + 1))
    continue
  fi

  echo "  file:   $file"
  echo "  size:   $(du -h "$file" | cut -f1 | tr -d ' ')"
  [[ -n "$caption" ]] && echo "  caption: $caption"
  if ! describe "$file"; then
    # Bytes on disk that ffprobe cannot decode are an error page wearing an
    # .mp4 extension. Delete it rather than leave a booby-trapped file behind.
    echo "  FAILED — downloaded file is not a decodable video, deleted"
    rm -f "$file"
    failed=$((failed + 1))
  fi
done

echo "──────────────────────────────────────────────────"
if [[ $failed -gt 0 ]]; then
  echo "$failed of $# failed"
  exit 1
fi
echo "$# of $# downloaded to $DEST"
