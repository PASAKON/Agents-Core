"""Pure "given a URL, produce a local video file" logic (task-c7d455aa,
CEO follow-up to order #40 via SomPong): the CEO pastes a video link,
SomPong downloads it and files it into Drive.

No MCP here and no side channel besides the filesystem/network -- this is
the ONE implementation both scripts/threads-grab.sh (D2, a thin CLI
wrapper) and runners/relay_mcp_server.py's grab_video tool (D5) call, so
the two surfaces cannot drift. Tests live in scripts/test_video_grab.py.

Layered strategy, identical to scripts/threads-grab.sh's proven behaviour
(read that script's header first -- this is a straight port, not a
redesign):
  (a) yt-dlp via subprocess.run with a LIST of args, no shell, a hard
      per-attempt timeout. `"Unsupported URL"` falls through to (b)
      immediately (no retry -- yt-dlp will never learn this host).
      `"universal data for rehydration"` is the one retryable signature
      (TikTok's flaky extractor, measured 2026-08-18); anything else is a
      real failure, surfaced on the first attempt.
  (b) Threads path: fetch the page with the Googlebot UA (reusing
      lib.link_reader._fetch -- SSRF-guarded per redirect hop already),
      pull the video URL and caption out of the embedded JSON. Download
      the media itself with a browser UA and
      `Referer: https://www.threads.com/` -- fbcdn refuses some requests
      without it.

Caption anchoring (task-c7d455aa REVIEW-1 B2 -- this replaced an earlier,
wrong approach, see git history for the "closest by byte distance" version
this superseded): the caption reported is the one belonging to the SAME
JSON object as the `video_versions` array actually selected -- structural,
not textual proximity. Live reconnaissance against a real threads.com post
(2026-08-24) confirmed the page embeds one self-contained JSON document per
`<script type="application/json" data-sjs>` block; every post AND every
reply in the thread sits at `...edges[N].node.thread_items[0].post`, each
carrying its OWN `video_versions` and `caption` keys as direct siblings.
`_extract_threads_video_structural` parses that block with the real `json`
module and returns the `post` object whose `code` matches the URL's own
post code -- never "whichever caption text happens to be nearby".

That same reconnaissance is *why* the earlier "closest by distance"
approach was wrong, not just imprecise: on the actual URL this module is
tested against, the real post (code matching the URL, `video_versions`
populated) carries `"caption": null` -- it is a caption-less video post.
Every non-null caption text living near it in the raw HTML belongs to a
REPLY, and which reply's text sits closest is not even stable between
fetches (replies reorder). Textual proximity does not degrade gracefully
here; it fabricates plausible-looking, wrong attribution. Structural
lookup instead correctly reports "no caption" for this post -- honest
about what the data says, never a stranger's words presented as the
post's own.

Textual proximity is kept ONLY as a last-resort fallback
(_extract_threads_video, unchanged from before), used solely when the
structural lookup cannot run at all (the JSON script block is missing,
truncated, or does not parse, or the URL's post code cannot be matched
inside it) -- never silently preferred over a successful structural
result, including a structural result of "no caption". Every Threads
result carries an `"anchor"` field: `"structural"` or `"proximity"`, so a
reason to distrust a caption is visible in the data, not just in a
comment.

check_url_safe() (lib.link_reader, already unit-tested) gates every fetch:
the input URL up front, and the extracted CDN media URL again before it is
streamed to disk -- a URL pulled out of page content is still
attacker-influenced.

D6 caps, because this runs unattended on a 4-CPU VPS: VIDEO_GRAB_MAX_BYTES
(default 500 MiB) rejects a source that advertises a bigger Content-Length
before any byte is written, and aborts mid-stream if the actual body
exceeds it anyway; VIDEO_GRAB_OVERALL_TIMEOUT_S (default 900s) is a real
wall-clock deadline threaded through every stage (each subprocess/request
call is capped at whatever time remains, not just its own nominal
timeout) so one hung stage cannot silently eat the whole budget.

Every outcome is one of:
  {"status": "ok", "url", "via", "path" (Path), "caption", "uploader",
   "probe", "size", "anchor" (Threads only: "structural" | "proximity")}
  {"status": "error", "url", "reason_kind", "reason"}
`reason_kind` is one of: blocked, unsupported_site, no_video, login_wall,
download_failed, not_a_video, too_large, timeout -- so a caller (the MCP
tool, D5) can report which of "blocked / unsupported site / no video on
the page / login wall / ..." actually happened without re-parsing prose.

grab_video() NEVER RAISES. A bad download is verified with ffprobe before
it is ever called a success -- a CDN error page saved as bytes with a
.mp4 name is deleted and reported as a failure, never a success.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from collections import deque
from pathlib import Path
from urllib.parse import urljoin

import requests

from lib.link_reader import BROWSER_UA, GOOGLEBOT_UA, check_url_safe, _fetch

# ---------------------------------------------------------------------------
# D6 -- caps. Env-overridable so a deploy can tune them without a code edit;
# defaults chosen for "unattended on a 4-CPU VPS, vertical phone clips are
# the normal case" (see scripts/threads-grab.sh's own comment on why there
# is no short duration cap).
# ---------------------------------------------------------------------------
MAX_VIDEO_BYTES = int(os.environ.get("VIDEO_GRAB_MAX_BYTES", str(500 * 1024 * 1024)))
OVERALL_TIMEOUT_S = float(os.environ.get("VIDEO_GRAB_OVERALL_TIMEOUT_S", "900"))

YTDLP_BIN = "yt-dlp"
YTDLP_ATTEMPTS = 3
YTDLP_PER_ATTEMPT_TIMEOUT_S = 180
YTDLP_UNSUPPORTED_MARKER = "Unsupported URL"
YTDLP_RETRYABLE_MARKER = "universal data for rehydration"

PAGE_FETCH_TIMEOUT_S = 30.0     # matches threads-grab.sh's FETCH_TIMEOUT default
MEDIA_DOWNLOAD_TIMEOUT_S = 300.0  # matches threads-grab.sh's CURL_MAX_TIME default
MEDIA_MAX_REDIRECTS = 5
MEDIA_CHUNK_SIZE = 65536

THREADS_REFERER = "https://www.threads.com/"
FFPROBE_BIN = "ffprobe"

# Structural extraction (primary, REVIEW-1 B2): the `<script
# type="application/json" data-sjs>...</script>` block(s) Meta embeds a
# self-contained JSON document in. Matched non-greedily since a page can
# carry several such blocks and only one of them holds this post's data.
_SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)

# Proximity extraction (LAST-RESORT FALLBACK ONLY, see module docstring) --
# the window past "video_versions" to search for the type/url pairs when no
# script block parsed as JSON at all. Verified live 2026-08-24 against a
# real threads.com post (see git history for the byte-offset measurements
# that showed this heuristic's actual failure mode).
_VIDEO_VERSIONS_KEY = '"video_versions"'
_VIDEO_VERSIONS_WINDOW = 20000
_VIDEO_PAIR_RE = re.compile(r'"type"\s*:\s*(\d+)\s*,\s*"url"\s*:\s*"([^"]+)"')
_USERNAME_RE = re.compile(r'"username"\s*:\s*"([^"]{1,40})"')
_CAPTION_RE = re.compile(r'"caption"\s*:\s*\{[^{}]*"text"\s*:\s*"([^"]{1,300})"')
_POST_CODE_RE = re.compile(r"/post/([A-Za-z0-9_-]+)")


def _unescape_json_string(raw: str) -> str:
    try:
        return json.loads('"' + raw + '"')
    except (json.JSONDecodeError, ValueError):
        return raw


def _remaining(deadline: float) -> float:
    return max(0.0, deadline - time.monotonic())


def _fail(url: str, reason_kind: str, reason: str) -> dict:
    return {"status": "error", "url": url, "reason_kind": reason_kind, "reason": reason}


# ---------------------------------------------------------------------------
# ffprobe verification -- shared by both download paths. A CDN error page
# saved with a .mp4 name still writes bytes; ffprobe is what tells the
# difference between that and a real video.
# ---------------------------------------------------------------------------

def _verify_video(path: Path) -> tuple[bool, str]:
    """(ok, probe_text_or_reason). ffprobe missing entirely is NOT treated
    as a failure (nothing to compare against) -- same posture as
    threads-grab.sh's describe(), which prints a note and returns success."""
    if shutil.which(FFPROBE_BIN) is None:
        return True, "(ffprobe not installed -- cannot verify)"
    try:
        proc = subprocess.run(
            [FFPROBE_BIN, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,codec_name",
             "-show_entries", "format=duration", "-of", "default=nw=1", str(path)],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"ffprobe failed to run: {e}"
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout or "ffprobe exited non-zero").strip()
    info = (proc.stdout or "").strip()
    if not info:
        return False, "ffprobe returned no stream info"
    return True, info


# ---------------------------------------------------------------------------
# (a) yt-dlp
# ---------------------------------------------------------------------------

def _ytdlp_download(url: str, dest_dir: Path, *, attempts: int, deadline: float) -> dict:
    """{"outcome": "ok", "path": Path} | {"outcome": "unsupported"} |
    {"outcome": "fail", "reason": str}.

    `.part` leftovers from a failed/timed-out attempt are cleaned up before
    returning, scoped by mtime to files newer than a marker created at the
    start of this call -- so this can never remove a concurrent grab's
    in-flight download (same discipline as threads-grab.sh's
    _ytdlp_cleanup, ported here rather than duplicated a second time).
    """
    if shutil.which(YTDLP_BIN) is None:
        return {"outcome": "fail", "reason": "yt-dlp not installed"}

    marker = dest_dir / f".video-grab-marker-{uuid.uuid4().hex}"
    marker.touch()
    pathfile = dest_dir / f".ytdlp-path-{uuid.uuid4().hex}"

    def cleanup_parts() -> None:
        marker_mtime = marker.stat().st_mtime if marker.exists() else 0
        for leftover in dest_dir.glob("*.part"):
            try:
                if leftover.stat().st_mtime >= marker_mtime:
                    leftover.unlink()
            except OSError:
                pass
        marker.unlink(missing_ok=True)
        pathfile.unlink(missing_ok=True)

    err = ""
    for attempt in range(1, attempts + 1):
        pathfile.unlink(missing_ok=True)
        remaining = _remaining(deadline)
        if remaining <= 0:
            cleanup_parts()
            return {"outcome": "fail", "reason": "overall time budget exceeded before yt-dlp ran"}
        per_attempt_timeout = min(YTDLP_PER_ATTEMPT_TIMEOUT_S, remaining)
        try:
            proc = subprocess.run(
                [YTDLP_BIN, "-f", "bv*+ba/best", "--no-playlist", "--restrict-filenames",
                 "--no-progress", "-P", str(dest_dir), "-o", "%(uploader)s-%(id)s.%(ext)s",
                 "--print-to-file", "after_move:filepath", str(pathfile), url],
                capture_output=True, text=True, timeout=per_attempt_timeout,
            )
        except subprocess.TimeoutExpired:
            cleanup_parts()
            return {"outcome": "fail", "reason": f"yt-dlp timed out after {per_attempt_timeout:.0f}s"}
        if proc.returncode == 0:
            path_text = pathfile.read_text().strip() if pathfile.exists() else ""
            cleanup_parts()
            if not path_text:
                return {"outcome": "fail", "reason": "yt-dlp exited 0 but wrote no output path"}
            file_path = Path(path_text.splitlines()[-1])
            if not file_path.is_file():
                return {"outcome": "fail", "reason": f"yt-dlp reported {file_path} but it is missing"}
            return {"outcome": "ok", "path": file_path}

        err = ((proc.stdout or "") + (proc.stderr or "")).strip()
        if YTDLP_UNSUPPORTED_MARKER in err:
            cleanup_parts()
            return {"outcome": "unsupported"}
        if YTDLP_RETRYABLE_MARKER not in err or attempt == attempts:
            cleanup_parts()
            return {"outcome": "fail", "reason": err[-500:] or "yt-dlp failed with no output"}
        time.sleep(min(attempt * 3, _remaining(deadline)))

    cleanup_parts()
    return {"outcome": "fail", "reason": err[-500:] or "yt-dlp failed with no output"}


# ---------------------------------------------------------------------------
# (b) Threads: page JSON extraction + guarded media download.
# ---------------------------------------------------------------------------

def _find_post_with_video(obj, post_code: str) -> dict | None:
    """BFS the parsed JSON tree for the dict that is BOTH: carries a
    non-empty `video_versions` list, AND has `code == post_code`. Requires
    the code match on purpose -- a dict with real video content but the
    WRONG code is a different post/reply in the same thread (a repost or
    quoted video), and returning it would recreate exactly the
    misattribution bug this replaces. No match -> None, which tells the
    caller to fall back to proximity, never to guess."""
    queue = deque([obj])
    while queue:
        cur = queue.popleft()
        if isinstance(cur, dict):
            vv = cur.get("video_versions")
            if isinstance(vv, list) and vv and cur.get("code") == post_code:
                return cur
            queue.extend(cur.values())
        elif isinstance(cur, list):
            queue.extend(cur)
    return None


def _extract_threads_video_structural(html_text: str, post_code: str) -> dict | None:
    """The primary path (REVIEW-1 B2): parse each embedded JSON script
    block for real with the `json` module, find the ONE post object whose
    own `code` matches the URL and whose own `video_versions` is populated,
    and read that SAME object's OWN `caption`/`user` fields -- never a
    nearby object's.

    Returns {"video_url", "username", "caption" (str or None -- None means
    the post genuinely has no caption, a successful result, NOT a failure),
    "anchor": "structural"}, or None if no script block parses as JSON and
    yields a code-matching post with video content at all (caller falls
    back to _extract_threads_video's proximity heuristic in that case).
    """
    for m in _SCRIPT_BLOCK_RE.finditer(html_text):
        content = m.group(1)
        if "video_versions" not in content:
            continue
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            continue
        post = _find_post_with_video(data, post_code)
        if post is None:
            continue
        pairs = [(v.get("type"), v.get("url")) for v in post["video_versions"]
                 if isinstance(v, dict) and v.get("url")]
        if not pairs:
            continue
        pairs.sort(key=lambda p: (p[0] if isinstance(p[0], int) else 0))
        video_url = pairs[0][1]
        username = ((post.get("user") or {}).get("username")) or ""
        caption_obj = post.get("caption")
        caption_text = caption_obj.get("text") if isinstance(caption_obj, dict) else None
        caption = caption_text.replace("\n", " ") if caption_text else None
        return {"video_url": video_url, "username": username,
                "caption": caption, "anchor": "structural"}
    return None


def _extract_threads_video(html_text: str) -> dict:
    """LAST-RESORT FALLBACK ONLY (see module docstring / REVIEW-1 B2) --
    used when _extract_threads_video_structural above could not run at all
    (no script block parsed, or none held a code-matching post). Picks the
    caption CLOSEST to `"video_versions"` in the raw page text, which is
    frequently wrong (it can return a reply's words, and which reply is
    closest is not even stable between fetches) -- never preferred over a
    successful structural result.

    {"video_url", "username", "caption", "anchor": "proximity"} on success,
    else {"error": str, "error_kind": "no_video" | "no_post_data" | "malformed"}.

    `error_kind` is a distinct field, not text a caller has to substring-match
    -- "no_post_data" is deliberately NOT resolved to login_wall/unsupported
    here, since that call needs the ORIGINAL url (does it even look like
    Threads?), which this function never sees. _threads_grab makes that call.
    """
    start = html_text.find(_VIDEO_VERSIONS_KEY)
    if start == -1:
        if '"caption"' in html_text:
            return {"error": "no video in this post (text/image only?)", "error_kind": "no_video"}
        return {"error": "page carried no post data (possible login wall, or the payload changed)",
                "error_kind": "no_post_data"}
    window = html_text[start:start + _VIDEO_VERSIONS_WINDOW]
    pairs = _VIDEO_PAIR_RE.findall(window)
    if not pairs:
        return {"error": "video_versions present but held no usable url", "error_kind": "malformed"}
    pairs.sort(key=lambda p: int(p[0]))
    video_url = _unescape_json_string(pairs[0][1])

    m = _USERNAME_RE.search(html_text)
    username = _unescape_json_string(m.group(1)) if m else ""

    caps = [(abs(cm.start() - start), cm.group(1)) for cm in _CAPTION_RE.finditer(html_text)]
    caption = _unescape_json_string(min(caps)[1]).replace("\n", " ") if caps else ""

    return {"video_url": video_url, "username": username, "caption": caption, "anchor": "proximity"}


def _extract_threads_video_with_anchor(html_text: str, url: str) -> dict:
    """The one entry point _threads_grab calls: try the structural lookup
    first (needs the URL's own post code), fall back to proximity only when
    structural genuinely could not resolve anything -- never when it
    resolved successfully to an empty caption, which is a different, valid
    outcome (see module docstring)."""
    m = _POST_CODE_RE.search(url)
    post_code = m.group(1) if m else None
    if post_code:
        structural = _extract_threads_video_structural(html_text, post_code)
        if structural is not None:
            return structural
    fallback = _extract_threads_video(html_text)
    return fallback


def _download_media(url: str, dest_path: Path, *, referer: str, user_agent: str,
                     max_bytes: int, deadline: float,
                     timeout_s: float = MEDIA_DOWNLOAD_TIMEOUT_S) -> tuple[bool, str | None]:
    """Stream `url` to `dest_path`, SSRF-checked on every hop (same
    discipline as lib.link_reader._fetch, just writing to disk instead of
    memory since a video is too big for that module's ~2MB text cap).
    Rejects up front when the server advertises a size over `max_bytes`,
    and aborts mid-stream if the actual body exceeds it anyway."""
    current = url
    headers = {"User-Agent": user_agent}
    if referer:
        headers["Referer"] = referer
    for _hop in range(MEDIA_MAX_REDIRECTS + 1):
        reason = check_url_safe(current)
        if reason:
            return False, f"blocked: {reason}"
        remaining = _remaining(deadline)
        if remaining <= 0:
            return False, "timeout"
        try:
            resp = requests.get(current, headers=headers, timeout=min(timeout_s, remaining),
                                 stream=True, allow_redirects=False)
        except requests.exceptions.Timeout:
            return False, "timeout"
        except requests.exceptions.RequestException as e:
            return False, f"request failed: {e}"

        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                return False, f"redirect (HTTP {resp.status_code}) with no Location header"
            current = urljoin(current, location)
            continue
        if resp.status_code >= 400:
            resp.close()
            return False, f"HTTP {resp.status_code}"

        content_length = resp.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > max_bytes:
                    resp.close()
                    return False, f"advertised size {content_length} bytes exceeds cap ({max_bytes} bytes)"
            except ValueError:
                pass

        written = 0
        try:
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=MEDIA_CHUNK_SIZE):
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > max_bytes:
                        resp.close()
                        dest_path.unlink(missing_ok=True)
                        return False, f"download exceeded cap ({max_bytes} bytes) mid-stream"
                    if time.monotonic() > deadline:
                        resp.close()
                        dest_path.unlink(missing_ok=True)
                        return False, "timeout mid-download"
                    f.write(chunk)
        except requests.exceptions.RequestException as e:
            resp.close()
            dest_path.unlink(missing_ok=True)
            return False, f"error while downloading: {e}"
        resp.close()
        if written == 0:
            dest_path.unlink(missing_ok=True)
            return False, "empty response body"
        return True, None
    return False, f"too many redirects (> {MEDIA_MAX_REDIRECTS})"


def _threads_grab(url: str, dest_dir: Path, *, max_bytes: int, deadline: float,
                   page_timeout_s: float = PAGE_FETCH_TIMEOUT_S,
                   media_timeout_s: float = MEDIA_DOWNLOAD_TIMEOUT_S) -> dict:
    remaining = _remaining(deadline)
    if remaining <= 0:
        return _fail(url, "timeout", "overall time budget exceeded before the Threads page was fetched")
    info, fetch_reason = _fetch(url, GOOGLEBOT_UA, timeout_s=min(page_timeout_s, remaining))
    if info is None:
        return _fail(url, "download_failed", fetch_reason or "fetch failed")
    if info["status_code"] in (401, 403):
        return _fail(url, "login_wall", f"HTTP {info['status_code']} (site may require login)")
    if info["status_code"] >= 400:
        return _fail(url, "download_failed", f"HTTP {info['status_code']}")

    extracted = _extract_threads_video_with_anchor(info["text"], url)
    if "error" in extracted:
        error_kind = extracted["error_kind"]
        if error_kind == "no_post_data":
            # Ambiguous on the page alone -- resolved using the URL: a real
            # Threads/Instagram link that carries no post JSON at all is
            # plausibly a login wall; anything else just isn't a site either
            # layer understands (this is reached even for non-Threads hosts,
            # since yt-dlp's "unsupported" outcome always earns one Threads
            # attempt -- see the orchestrator below).
            kind = "login_wall" if ("threads.com" in url or "threads.net" in url) else "unsupported_site"
        else:
            kind = error_kind  # "no_video" or "malformed" -> download_failed-ish, kept as-is
            if kind == "malformed":
                kind = "download_failed"
        return _fail(url, kind, extracted["error"])

    m = _POST_CODE_RE.search(url)
    code = m.group(1) if m else "post"
    username = extracted["username"]
    out_name = f"{username or 'threads'}-{code}.mp4"
    dest_path = dest_dir / out_name

    ok, dl_reason = _download_media(
        extracted["video_url"], dest_path, referer=THREADS_REFERER, user_agent=BROWSER_UA,
        max_bytes=max_bytes, deadline=deadline, timeout_s=media_timeout_s,
    )
    if not ok:
        kind = "blocked" if (dl_reason or "").startswith("blocked:") else (
            "too_large" if "cap (" in (dl_reason or "") else
            "timeout" if dl_reason == "timeout" or "timeout" in (dl_reason or "") else "download_failed"
        )
        return _fail(url, kind, dl_reason or "download failed")

    return {
        "status": "ok", "url": url, "via": "threads (embedded JSON, Googlebot UA)",
        "path": dest_path, "caption": extracted["caption"] or None,
        "uploader": username or None, "anchor": extracted["anchor"],
    }


# ---------------------------------------------------------------------------
# Orchestrator -- mirrors scripts/threads-grab.sh's per-url case statement
# exactly (D2's "behaviour contract"). yt-dlp's "unsupported" outcome always
# gets one Threads attempt (the shell script tries it unconditionally, not
# just for threads.com/net URLs -- a deliberate generality, kept as-is); a
# real yt-dlp failure only gets a Threads attempt when the URL itself looks
# like a Threads link.
# ---------------------------------------------------------------------------

def grab_video(url: str, dest_dir: Path, *, ytdlp_attempts: int = YTDLP_ATTEMPTS,
                max_bytes: int = MAX_VIDEO_BYTES, overall_timeout_s: float = OVERALL_TIMEOUT_S,
                page_timeout_s: float = PAGE_FETCH_TIMEOUT_S,
                media_timeout_s: float = MEDIA_DOWNLOAD_TIMEOUT_S) -> dict:
    """Download the video behind `url` into `dest_dir`. Never raises --
    every failure mode becomes {"status": "error", "reason_kind", "reason"}.
    """
    try:
        return _grab_video_impl(url, dest_dir, ytdlp_attempts=ytdlp_attempts,
                                 max_bytes=max_bytes, overall_timeout_s=overall_timeout_s,
                                 page_timeout_s=page_timeout_s, media_timeout_s=media_timeout_s)
    except Exception as e:  # last-resort net, same posture as link_reader.read_link
        return _fail(url, "download_failed", f"internal error: {e!r}")


def _grab_video_impl(url: str, dest_dir: Path, *, ytdlp_attempts: int, max_bytes: int,
                      overall_timeout_s: float, page_timeout_s: float, media_timeout_s: float) -> dict:
    url = (url or "").strip()
    if not url:
        return _fail(url, "blocked", "empty URL")
    reason = check_url_safe(url)
    if reason:
        return _fail(url, "blocked", f"blocked: {reason}")

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + overall_timeout_s

    def _verify_or_delete(result: dict) -> dict:
        ok, probe_or_reason = _verify_video(result["path"])
        if not ok:
            result["path"].unlink(missing_ok=True)
            return _fail(url, "not_a_video",
                         f"downloaded file is not a decodable video: {probe_or_reason}")
        result["probe"] = probe_or_reason
        result["size"] = result["path"].stat().st_size
        return result

    yt = _ytdlp_download(url, dest_dir, attempts=ytdlp_attempts, deadline=deadline)

    if yt["outcome"] == "ok":
        return _verify_or_delete({"status": "ok", "url": url, "via": "yt-dlp",
                                   "path": yt["path"], "caption": None, "uploader": None})

    if yt["outcome"] == "fail":
        if "threads.com" not in url and "threads.net" not in url:
            return _fail(url, "download_failed", f"yt-dlp failed: {yt['reason']}")
        # else: fall through to one Threads attempt, same as the shell script.

    # yt["outcome"] == "unsupported", or a real yt-dlp failure on a
    # threads.com/net-looking URL.
    threads_result = _threads_grab(url, dest_dir, max_bytes=max_bytes, deadline=deadline,
                                    page_timeout_s=page_timeout_s, media_timeout_s=media_timeout_s)
    if threads_result["status"] != "ok":
        return threads_result

    return _verify_or_delete(threads_result)


# ---------------------------------------------------------------------------
# CLI entry point for scripts/threads-grab.sh (D2). Prints ONE compact JSON
# line to stdout (Path objects stringified) -- the bash wrapper reads it
# with a small python3 -c helper and does its own printing (size via `du
# -h`, so the CLI's exact byte-for-byte formatting never has to be
# reproduced here). Positional argv so the shell script controls its own
# already-resolved defaults (DEST/ATTEMPTS/CURL_MAX_TIME/FETCH_TIMEOUT)
# without this file guessing at env var names.
# ---------------------------------------------------------------------------

def _cli_main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(json.dumps({"status": "error", "reason": "usage: video_grab.py <url> <dest_dir> "
                                                        "[attempts] [media_timeout_s] [page_timeout_s]"}))
        return 2
    url = argv[0]
    dest_dir = Path(argv[1])
    attempts = int(argv[2]) if len(argv) > 2 and argv[2] else YTDLP_ATTEMPTS
    media_timeout = float(argv[3]) if len(argv) > 3 and argv[3] else MEDIA_DOWNLOAD_TIMEOUT_S
    page_timeout = float(argv[4]) if len(argv) > 4 and argv[4] else PAGE_FETCH_TIMEOUT_S

    result = grab_video(url, dest_dir, ytdlp_attempts=attempts,
                         media_timeout_s=media_timeout, page_timeout_s=page_timeout)
    out = dict(result)
    if "path" in out:
        out["path"] = str(out["path"])
    print(json.dumps(out, ensure_ascii=False))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_cli_main(sys.argv[1:]))
