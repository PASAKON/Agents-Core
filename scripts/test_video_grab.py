"""Tests for lib/video_grab.py (task-c7d455aa D1/D2/D6/D8).

Every test stubs socket.getaddrinfo, requests.get, subprocess.run and
shutil.which -- no real DNS, HTTP, yt-dlp, or ffprobe ever runs here.
video_grab.py reuses lib.link_reader's check_url_safe/_fetch, so its DNS and
HTTP fakes patch lib.link_reader's module globals (lr.socket / lr.requests)
-- video_grab.py's own `import requests` is the SAME module object, so
patching one patches both call sites.

Proves, not just exercises (task's D8 required list):
  1. SSRF still applies to the whole grab_video() flow, including a redirect
     to a private address on the MEDIA download (not just the page fetch).
  2. The caption-anchoring rule: a page whose FIRST `"caption"` match in
     document order is a reply, but whose NEAREST-to-`"video_versions"`
     match is the post's own text, returns the post's caption -- proves the
     historical "first match" bug (a stranger's reply reported as the
     post's own words) cannot recur.
  3. A download ffprobe cannot decode (a CDN error page wearing .mp4) is
     reported as a failure and the file is deleted, never called a success.
  4. `.part` cleanup after a failed yt-dlp attempt is scoped by mtime to the
     current run -- a pre-existing `.part` from another process is left
     alone.
  5. grab_video() never raises.

Plus general coverage: yt-dlp success/retry/unsupported-fallthrough, the
Threads video_versions type-ascending sort, D6's size caps (advertised
Content-Length over the cap rejected up front; an oversized body aborted
mid-stream), and the login-wall / no-video reason_kind mapping.

Run standalone: python scripts/test_video_grab.py
Or under pytest:  pytest scripts/test_video_grab.py
"""
from __future__ import annotations

import socket
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.video_grab as vg  # noqa: E402
import lib.link_reader as lr  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes -- no real DNS, HTTP, or subprocess ever runs in this file.
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code=200, content: bytes | str = b"", headers=None, encoding="utf-8"):
        self.status_code = status_code
        self._content = content.encode(encoding) if isinstance(content, str) else content
        self.headers = headers or {}
        self.encoding = encoding
        self.closed = False

    def iter_content(self, chunk_size=65536):
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i:i + chunk_size]

    def close(self):
        self.closed = True


class FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Table(dict):
    def __init__(self):
        super().__init__()
        self.calls: list = []


@pytest.fixture
def fake_dns(monkeypatch):
    table = _Table()

    def _getaddrinfo(host, *args, **kwargs):
        if host not in table:
            raise AssertionError(f"unexpected DNS lookup: {host!r}")
        val = table[host]
        if isinstance(val, BaseException):
            raise val
        ips = val if isinstance(val, list) else [val]
        out = []
        for ip in ips:
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            out.append((family, socket.SOCK_STREAM, 6, "", (ip, 0)))
        return out

    monkeypatch.setattr(lr.socket, "getaddrinfo", _getaddrinfo)
    return table


@pytest.fixture
def fake_http(monkeypatch):
    """dict-like: fake_http["https://host/path"] = FakeResponse(...) (or a
    list, for a URL requested more than once -- e.g. redirect-then-target).
    `.calls` records every URL actually requested, in order."""
    table = _Table()

    def _get(url, **kwargs):
        table.calls.append(url)
        if url not in table:
            raise AssertionError(f"unexpected requests.get call: {url!r}")
        val = table[url]
        if isinstance(val, list):
            resp = val.pop(0)
        else:
            resp = val
        if isinstance(resp, BaseException):
            raise resp
        return resp

    # video_grab.py's `import requests` and lib.link_reader's `import
    # requests` are the same module object -- patching one patches the call
    # site both the page fetch (via lr._fetch) and the media download
    # (video_grab's own _download_media) actually use.
    monkeypatch.setattr(lr.requests, "get", _get)
    return table


@pytest.fixture
def fake_run(monkeypatch):
    """Queue-based subprocess.run fake, keyed by binary name (cmd[0]).
    fake_run.queues["yt-dlp"].append(action) / fake_run.queues["ffprobe"].append(...)
    where `action` is a FakeProc or a callable(cmd) -> FakeProc (for yt-dlp
    successes, which must also write the --print-to-file path)."""
    queues = {"yt-dlp": [], "ffprobe": []}
    calls = []

    def _run(cmd, capture_output=True, text=True, timeout=None):
        calls.append(cmd)
        binary = cmd[0]
        q = queues.get(binary)
        if not q:
            raise AssertionError(f"unexpected subprocess.run call: {cmd!r}")
        action = q.pop(0)
        if callable(action):
            return action(cmd)
        return action

    monkeypatch.setattr(vg.subprocess, "run", _run)
    monkeypatch.setattr(vg.shutil, "which", lambda name: f"/usr/bin/{name}")
    return SimpleNamespace(queues=queues, calls=calls)


def _ytdlp_ok(final_path: Path):
    def _do(cmd):
        idx = cmd.index("--print-to-file")
        Path(cmd[idx + 2]).write_text(str(final_path) + "\n")
        return FakeProc(0)
    return _do


PROBE_OK = FakeProc(0, stdout="codec_name=h264\nwidth=720\nheight=1280\nduration=11.491020\n")
PROBE_BAD = FakeProc(1, stderr="Invalid data found when processing input")


# ---------------------------------------------------------------------------
# Synthetic Threads page HTML.
# ---------------------------------------------------------------------------

def _threads_html(*, video_urls=(("101", "https://scontent.cdn/v1.mp4"),
                                  ("102", "https://scontent.cdn/v2.mp4")),
                   username="uusanr", leading_reply: str | None = None,
                   post_caption: str | None = "อยากจีบแต่วาสนาไม่ถึง😭",
                   trailing_reply: str | None = None) -> str:
    """Builds a page where `"video_versions"` sits at a fixed offset, an
    optional reply caption is placed BEFORE it (far away, early in document
    order), the post's own caption sits immediately after it (nearest), and
    an optional reply sits well after (far away, late in document order) --
    the exact shape that makes "first match" and "nearest match" disagree.
    """
    parts = []
    if leading_reply is not None:
        parts.append('"caption":{"text":"' + leading_reply + '"}')
        parts.append("x" * 5000)
    pairs = ",".join(f'{{"type":{t},"url":"{u.replace("/", chr(92)+"/")}"}}' for t, u in video_urls)
    parts.append('"video_versions":[' + pairs + ']')
    parts.append("x" * 300)
    parts.append(f'"username":"{username}"')
    parts.append("x" * 200)
    if post_caption is not None:
        parts.append('"caption":{"text":"' + post_caption + '"}')
    if trailing_reply is not None:
        parts.append("x" * 20000)
        parts.append('"caption":{"text":"' + trailing_reply + '"}')
    return "".join(parts)


def _install_public_dns(fake_dns, hosts: list[str]) -> None:
    for h in hosts:
        fake_dns[h] = "93.184.216.34"


# ---------------------------------------------------------------------------
# 1. SSRF (D8 required)
# ---------------------------------------------------------------------------

def test_grab_video_rejects_blocked_input_url_before_any_network_call(fake_dns, fake_http):
    # check_url_safe resolves via getaddrinfo even for an IP literal -- it
    # never trusts the literal hostname string alone (see lib.link_reader).
    fake_dns["169.254.169.254"] = "169.254.169.254"
    result = vg.grab_video("http://169.254.169.254/latest/meta-data/", Path("/tmp/x"))
    assert result["status"] == "error"
    assert result["reason_kind"] == "blocked"
    assert fake_http.calls == []


def test_grab_video_rejects_media_redirect_to_private_address(fake_dns, fake_http, fake_run, tmp_path):
    """The page itself is public and safe; the extracted video_versions URL
    redirects to a private address. Must be blocked at the media-download
    hop, not just checked once up front."""
    _install_public_dns(fake_dns, ["www.threads.com", "public-cdn.example"])
    fake_dns["10.0.0.5"] = "10.0.0.5"
    fake_run.queues["yt-dlp"].append(FakeProc(1, stderr="ERROR: Unsupported URL"))
    html = _threads_html(video_urls=(("101", "https://public-cdn.example/v.mp4"),))
    url = "https://www.threads.com/@uusanr/post/DcXdxp7kjHj"
    fake_http[url] = FakeResponse(200, content=html)
    fake_http["https://public-cdn.example/v.mp4"] = FakeResponse(
        302, headers={"Location": "http://10.0.0.5/internal"})

    result = vg.grab_video(url, tmp_path)

    assert result["status"] == "error"
    assert result["reason_kind"] == "blocked"
    assert "http://10.0.0.5/internal" not in fake_http.calls


# ---------------------------------------------------------------------------
# 2. Caption anchoring (D8 required)
# ---------------------------------------------------------------------------

def test_caption_anchoring_returns_post_caption_not_the_first_match_in_document_order():
    html = _threads_html(
        leading_reply="Hi DM",                              # first in doc order, far from video
        post_caption="อยากจีบแต่วาสนาไม่ถึง😭",              # nearest to video_versions
        trailing_reply="เค้าชอบทรงน้้",                       # also far, later in doc order
    )
    extracted = vg._extract_threads_video(html)
    assert extracted["caption"] == "อยากจีบแต่วาสนาไม่ถึง😭"
    assert extracted["caption"] != "Hi DM"


def test_video_versions_type_ascending_wins_regardless_of_document_order():
    html = _threads_html(video_urls=(("102", "https://scontent.cdn/lowres.mp4"),
                                      ("101", "https://scontent.cdn/highres.mp4")))
    extracted = vg._extract_threads_video(html)
    assert extracted["video_url"] == "https://scontent.cdn/highres.mp4"


def test_extract_threads_video_no_video_versions_but_has_caption_is_no_video():
    html = '"caption":{"text":"just a text post, no clip"}'
    extracted = vg._extract_threads_video(html)
    assert "error" in extracted
    assert "text/image only" in extracted["error"]


def test_extract_threads_video_no_post_data_at_all():
    html = "<html><body>some unrelated JS shell</body></html>"
    extracted = vg._extract_threads_video(html)
    assert "error" in extracted
    assert "login wall" in extracted["error"]


# ---------------------------------------------------------------------------
# 3. ffprobe verification deletes bad downloads, never calls them a success
#    (D8 required)
# ---------------------------------------------------------------------------

def test_ytdlp_success_but_undecodable_file_is_reported_failed_and_deleted(fake_run, tmp_path):
    target = tmp_path / "uploader-123.mp4"
    target.write_bytes(b"<html>error page</html>")
    fake_run.queues["yt-dlp"].append(_ytdlp_ok(target))
    fake_run.queues["ffprobe"].append(PROBE_BAD)

    result = vg.grab_video("https://youtube.com/watch?v=x", tmp_path)

    assert result["status"] == "error"
    assert result["reason_kind"] == "not_a_video"
    assert not target.exists()


def test_threads_success_but_undecodable_file_is_reported_failed_and_deleted(
        fake_dns, fake_http, fake_run, tmp_path):
    _install_public_dns(fake_dns, ["www.threads.com", "scontent.cdn"])
    fake_run.queues["yt-dlp"].append(FakeProc(1, stderr="ERROR: Unsupported URL"))
    fake_run.queues["ffprobe"].append(PROBE_BAD)
    html = _threads_html()
    url = "https://www.threads.com/@uusanr/post/DcXdxp7kjHj"
    fake_http[url] = FakeResponse(200, content=html)
    fake_http["https://scontent.cdn/v1.mp4"] = FakeResponse(200, content=b"not a real video" * 10)

    result = vg.grab_video(url, tmp_path)

    assert result["status"] == "error"
    assert result["reason_kind"] == "not_a_video"
    assert list(tmp_path.glob("*.mp4")) == []


# ---------------------------------------------------------------------------
# 4. `.part` cleanup scoped by mtime to the current run (D8 required)
# ---------------------------------------------------------------------------

def test_part_cleanup_only_removes_leftovers_from_the_current_run(fake_run, tmp_path):
    # A .part file from some OTHER, unrelated run/process, already sitting
    # in dest_dir before this grab_video() call starts.
    stale_part = tmp_path / "some-other-download.part"
    stale_part.write_bytes(b"x" * 1000)
    time.sleep(0.02)

    def _fail_and_leave_part(cmd):
        idx = cmd.index("-P")
        Path(cmd[idx + 1], "this-run.part").write_bytes(b"partial")
        return FakeProc(1, stderr="ERROR: some real failure, not retryable")

    fake_run.queues["yt-dlp"].append(_fail_and_leave_part)

    result = vg.grab_video("https://example.com/not-a-known-host", tmp_path)

    assert result["status"] == "error"
    assert stale_part.exists(), "a pre-existing .part from another run must be left alone"
    assert not (tmp_path / "this-run.part").exists(), "THIS run's own .part leftover must be cleaned up"


# ---------------------------------------------------------------------------
# 5. Never raises
# ---------------------------------------------------------------------------

def test_grab_video_never_raises_on_internal_error(fake_dns, fake_http, fake_run, tmp_path, monkeypatch):
    _install_public_dns(fake_dns, ["youtube.com"])

    def _boom(*a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(vg, "_ytdlp_download", _boom)

    result = vg.grab_video("https://youtube.com/watch?v=x", tmp_path)

    assert result["status"] == "error"
    assert "boom" in result["reason"]


# ---------------------------------------------------------------------------
# yt-dlp: success / retry / unsupported fallthrough / real-failure fallthrough
# ---------------------------------------------------------------------------

def test_ytdlp_success_returns_via_ytdlp_no_caption(fake_run, tmp_path):
    target = tmp_path / "uploader-abc.mp4"
    target.write_bytes(b"x" * 10)
    fake_run.queues["yt-dlp"].append(_ytdlp_ok(target))
    fake_run.queues["ffprobe"].append(PROBE_OK)

    result = vg.grab_video("https://youtube.com/watch?v=x", tmp_path)

    assert result["status"] == "ok"
    assert result["via"] == "yt-dlp"
    assert result["path"] == target
    assert result["caption"] is None
    assert result["probe"] == PROBE_OK.stdout.strip()
    assert result["size"] == 10


def test_ytdlp_retries_only_the_rehydration_signature(fake_run, tmp_path):
    target = tmp_path / "uploader-abc.mp4"
    target.write_bytes(b"x" * 10)
    fake_run.queues["yt-dlp"] = [
        FakeProc(1, stderr="ERROR: Unable to extract universal data for rehydration"),
        FakeProc(1, stderr="ERROR: Unable to extract universal data for rehydration"),
        _ytdlp_ok(target),
    ]
    fake_run.queues["ffprobe"].append(PROBE_OK)

    result = vg.grab_video("https://tiktok.com/@u/video/1", tmp_path, ytdlp_attempts=3)

    assert result["status"] == "ok"
    assert len(fake_run.calls) == 4  # 3 yt-dlp attempts + 1 ffprobe


def test_ytdlp_unsupported_url_falls_through_immediately_no_retry(fake_dns, fake_http, fake_run, tmp_path):
    fake_run.queues["yt-dlp"].append(FakeProc(1, stderr="ERROR: Unsupported URL"))
    _install_public_dns(fake_dns, ["example.org"])
    fake_http["https://example.org/x"] = FakeResponse(200, content="<html>no post data here</html>")

    result = vg.grab_video("https://example.org/x", tmp_path)

    assert result["status"] == "error"
    assert result["reason_kind"] == "unsupported_site"
    yt_dlp_calls = [c for c in fake_run.calls if c[0] == "yt-dlp"]
    assert len(yt_dlp_calls) == 1, "Unsupported URL must never be retried"


def test_ytdlp_real_failure_on_non_threads_url_never_attempts_threads(fake_run, tmp_path):
    fake_run.queues["yt-dlp"].append(FakeProc(1, stderr="ERROR: some real, non-retryable failure"))

    result = vg.grab_video("https://example.org/x", tmp_path)

    assert result["status"] == "error"
    assert result["reason_kind"] == "download_failed"
    assert "yt-dlp failed" in result["reason"]


def test_ytdlp_real_failure_on_threads_looking_url_still_tries_threads(
        fake_dns, fake_http, fake_run, tmp_path):
    fake_run.queues["yt-dlp"].append(FakeProc(1, stderr="ERROR: some real, non-retryable failure"))
    fake_run.queues["ffprobe"].append(PROBE_OK)
    _install_public_dns(fake_dns, ["www.threads.com", "scontent.cdn"])
    html = _threads_html()
    url = "https://www.threads.com/@uusanr/post/DcXdxp7kjHj"
    fake_http[url] = FakeResponse(200, content=html)
    fake_http["https://scontent.cdn/v1.mp4"] = FakeResponse(200, content=b"real video bytes" * 5)

    result = vg.grab_video(url, tmp_path)

    assert result["status"] == "ok"
    assert result["via"] == "threads (embedded JSON, Googlebot UA)"
    assert result["caption"] == "อยากจีบแต่วาสนาไม่ถึง😭"


# ---------------------------------------------------------------------------
# Threads: login wall / no video / full happy path
# ---------------------------------------------------------------------------

def test_threads_login_wall_status_code(fake_dns, fake_http, fake_run, tmp_path):
    fake_run.queues["yt-dlp"].append(FakeProc(1, stderr="ERROR: Unsupported URL"))
    _install_public_dns(fake_dns, ["www.threads.com"])
    url = "https://www.threads.com/@u/post/abc"
    fake_http[url] = FakeResponse(403, content="blocked")

    result = vg.grab_video(url, tmp_path)

    assert result["status"] == "error"
    assert result["reason_kind"] == "login_wall"


def test_threads_full_happy_path_via_googlebot_json(fake_dns, fake_http, fake_run, tmp_path):
    fake_run.queues["yt-dlp"].append(FakeProc(1, stderr="ERROR: Unsupported URL"))
    fake_run.queues["ffprobe"].append(PROBE_OK)
    _install_public_dns(fake_dns, ["www.threads.com", "scontent.cdn"])
    html = _threads_html()
    url = "https://www.threads.com/@uusanr/post/DcXdxp7kjHj"
    fake_http[url] = FakeResponse(200, content=html)
    fake_http["https://scontent.cdn/v1.mp4"] = FakeResponse(200, content=b"real video bytes" * 5)

    result = vg.grab_video(url, tmp_path)

    assert result["status"] == "ok"
    assert result["via"] == "threads (embedded JSON, Googlebot UA)"
    assert result["uploader"] == "uusanr"
    assert result["caption"] == "อยากจีบแต่วาสนาไม่ถึง😭"
    assert result["path"].name == "uusanr-DcXdxp7kjHj.mp4"
    assert result["path"].exists()


def test_threads_page_fetch_uses_googlebot_ua_and_media_fetch_uses_browser_ua_with_referer(
        fake_dns, fake_http, fake_run, tmp_path, monkeypatch):
    fake_run.queues["yt-dlp"].append(FakeProc(1, stderr="ERROR: Unsupported URL"))
    fake_run.queues["ffprobe"].append(PROBE_OK)
    _install_public_dns(fake_dns, ["www.threads.com", "scontent.cdn"])
    html = _threads_html()
    url = "https://www.threads.com/@uusanr/post/DcXdxp7kjHj"

    seen_headers = {}
    table = fake_http

    def _get(u, headers=None, **kw):
        seen_headers[u] = headers or {}
        table.calls.append(u)
        if u not in table:
            raise AssertionError(f"unexpected requests.get call: {u!r}")
        return table[u]

    monkeypatch.setattr(lr.requests, "get", _get)
    fake_http[url] = FakeResponse(200, content=html)
    fake_http["https://scontent.cdn/v1.mp4"] = FakeResponse(200, content=b"real video bytes" * 5)

    result = vg.grab_video(url, tmp_path)

    assert result["status"] == "ok"
    assert seen_headers[url]["User-Agent"] == lr.GOOGLEBOT_UA
    media_headers = seen_headers["https://scontent.cdn/v1.mp4"]
    assert media_headers["User-Agent"] == lr.BROWSER_UA
    assert media_headers["Referer"] == vg.THREADS_REFERER


# ---------------------------------------------------------------------------
# D6 caps
# ---------------------------------------------------------------------------

def test_download_media_rejects_advertised_size_over_cap_before_writing_bytes(
        fake_dns, fake_http, tmp_path):
    _install_public_dns(fake_dns, ["cdn.example"])
    url = "https://cdn.example/big.mp4"
    fake_http[url] = FakeResponse(200, content=b"x" * 100, headers={"Content-Length": "999999999"})

    ok, reason = vg._download_media(url, tmp_path / "out.mp4", referer=None,
                                     user_agent="ua", max_bytes=1000,
                                     deadline=time.monotonic() + 30)

    assert ok is False
    assert "exceeds cap" in reason
    assert not (tmp_path / "out.mp4").exists()


def test_download_media_aborts_mid_stream_past_cap(fake_dns, fake_http, tmp_path):
    _install_public_dns(fake_dns, ["cdn.example"])
    url = "https://cdn.example/big.mp4"
    # No Content-Length header advertised -- only caught while streaming.
    fake_http[url] = FakeResponse(200, content=b"y" * 5000)

    ok, reason = vg._download_media(url, tmp_path / "out.mp4", referer=None,
                                     user_agent="ua", max_bytes=1000,
                                     deadline=time.monotonic() + 30)

    assert ok is False
    assert "exceeded cap" in reason
    assert not (tmp_path / "out.mp4").exists()


def test_grab_video_max_bytes_env_default_is_500mib():
    assert vg.MAX_VIDEO_BYTES == 500 * 1024 * 1024


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
