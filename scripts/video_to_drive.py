#!/usr/bin/env python3
"""Download short video links (TikTok, YouTube Shorts, game clips, book
reels) and land them directly in the CEO's Google Drive `Desktop Cloud`
root (task-c7d455aa D3 -- CEO follow-up to order #40, chosen today over
Telegram-send and over a new sub-folder).

    python scripts/video_to_drive.py <url> [url ...]

Per URL: download the best quality the post actually offers (staged under a
temp dir, never the CEO's Desktop), upload it straight into
`DRIVE_SOMPONG_GRAB_FOLDER_ID` -- no sub-folder, no find-or-create -- verify
by re-listing the destination folder (an upload API 200 is not evidence the
file is there), log it locally, then delete the local staging copy. On any
failure the local copy is kept and its path printed -- nothing is ever
deleted from Drive.

This is assembly, not new Drive plumbing -- it reuses:
  - scripts/gdrive-bridge/ilag_sync.py    -- upload(), api(), OAuth
  - scripts/gdrive-bridge/ilag_mirror.py  -- list_folder() verify-by-listing
  - scripts/tiktok-grab.sh                -- the flaky-extractor retry shape

DRIVE_SOMPONG_GRAB_FOLDER_ID is a NEW, separate constant from
DRIVE_VIDEO_PARENT_FOLDER_ID -- the latter resolves to `ALL DRAFT/BLACK
LIQUIDITY` and is load-bearing for mooniex-claudeflow/src/video/videodrive.js
and scripts/higgsfield/gen_loop.py. This module never reads that variable at
all (see the guard test in scripts/test_video_to_drive.py) -- repointing or
widening it here would silently break those two other production paths.
Per the CEO's exception (recorded in .claude/skills/gdrive-filing/SKILL.md,
"Desktop Cloud... AI never auto-files here"): uploads only, no deletes, no
reorganising, and never anywhere else on Drive.

D4 -- the OAuth env-file location is configurable (SOMPONG_DRIVE_ENV), because
SomPong runs on Contabo as user `secretary`, and
/root/projects/mooniex-claudeflow/.env is not readable by that user
(/root is drwx------). See resolve_oauth_env_candidates(). Falling back to
today's claudeflow candidates unchanged keeps the Mac working with no new
env var. Values are never printed.

task-e713c4e2 -- broker mode. `secretary` no longer holds the Drive OAuth
credential at all (runners/drive_upload_broker.py D1 owns it exclusively);
when DRIVE_UPLOAD_SOCKET is set, every upload goes through that unix-socket
broker instead of calling ilag_sync.upload()/apply_oauth_env_override()
directly -- this process never even attempts to read a credential file in
that mode. If the socket is unset (the Mac, today), the direct path below
is completely unchanged -- same functions, same tests, same behaviour.
If the broker is down, unreachable, or refuses (wrong uid, bad path, failed
Drive verify, ...), broker_upload() raises BrokerUploadError and
process_url() reports a normal FAIL -- never a silent fallback to a direct
credential SomPong must not have (D4: honest failure, not a quiet bypass).
Broker mode does not do the pre-upload "already there, skip" listing the
direct path does below -- that listing needs Drive read access, which is
exactly what `secretary` no longer has; a same-name re-upload in broker
mode lands as a second Drive file rather than being deduped.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "gdrive-bridge"))
import ilag_sync  # noqa: E402 -- module object, so its ENV_CANDIDATES can be overridden (D4)
from ilag_sync import upload, ts, mb, ACTOR_DEFAULT  # noqa: E402
from ilag_mirror import list_folder  # noqa: E402

CF_ENV_CANDIDATES = [
    Path("/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env"),
    Path("/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env.local"),
]

# task-c7d455aa D4 -- where GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN come
# from. Set by the CTO at deploy time on Contabo (never by this code, and
# never pointed at a file this code writes); unset on the Mac, where the
# claudeflow candidates above keep working exactly as before.
SOMPONG_DRIVE_ENV_VAR = "SOMPONG_DRIVE_ENV"

# task-c7d455aa D3 -- the CEO's Desktop Cloud root. A NEW variable, deliberately
# not DRIVE_VIDEO_PARENT_FOLDER_ID -- see the module docstring above.
DRIVE_SOMPONG_GRAB_FOLDER_ID = os.environ.get(
    "DRIVE_SOMPONG_GRAB_FOLDER_ID", "115w-UxOvdmPIc5X8nq_oV42EEsrVMRtR"
)

# TikTok intermittently fails extraction and succeeds on an identical retry
# (hit 3 of 5 clips on 2026-08-18, per scripts/tiktok-grab.sh). Only this
# error is worth retrying -- anything else is a real failure, first try.
RETRYABLE_ERROR = "universal data for rehydration"
DOWNLOAD_ATTEMPTS = 3
DEFAULT_LOG_PATH = Path(__file__).resolve().parents[1] / "output" / "video-to-drive" / "log.txt"


class DownloadError(RuntimeError):
    pass


# task-e713c4e2 D2 -- when set, names the unix socket
# runners/drive_upload_broker.py is listening on; every upload goes through
# broker_upload() instead of the direct ilag_sync path below. See module
# docstring "broker mode" section.
DRIVE_UPLOAD_SOCKET_VAR = "DRIVE_UPLOAD_SOCKET"
BROKER_CONNECT_TIMEOUT = 10.0     # seconds -- just opening the socket + sending one JSON line
BROKER_MAX_RESPONSE_BYTES = 64 * 1024


class BrokerUploadError(RuntimeError):
    pass


# --------------------------------------------------------------------------- env

def resolve_oauth_env_candidates() -> list[Path]:
    """Where to read GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN from.

    SOMPONG_DRIVE_ENV, if set, names exactly one file -- the CTO provisions
    it at deploy time (this code never touches it). Falls back to today's
    CF_ENV_CANDIDATES unchanged, so the Mac needs no new env var at all.
    """
    override = os.environ.get(SOMPONG_DRIVE_ENV_VAR)
    if override:
        return [Path(override)]
    return CF_ENV_CANDIDATES


def apply_oauth_env_override() -> None:
    """Point ilag_sync's OAuth loader at resolve_oauth_env_candidates().

    ilag_sync.py is shared, general-purpose Drive plumbing (also used by the
    unrelated Do Not Disturb mirror sweep) and hardcodes the Mac-only claudeflow
    paths -- this overrides its module-level ENV_CANDIDATES rather than forking
    a second OAuth loader. Call once, before the first upload()/list_folder().
    """
    ilag_sync.ENV_CANDIDATES = resolve_oauth_env_candidates()


# --------------------------------------------------------------------------- broker mode (task-e713c4e2 D2)

def _connect_broker_socket(sock_path: str, timeout: float) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect(sock_path)
    return sock


def _recv_line(sock: socket.socket, max_bytes: int) -> bytes:
    buf = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise BrokerUploadError(f"broker response exceeds {max_bytes} bytes")
        newline = buf.find(b"\n")
        if newline != -1:
            return bytes(buf[:newline])
    raise BrokerUploadError("broker closed the connection with no response")


def broker_upload(sock_path: str, local_path: Path, name: str, *,
                   timeout: float = BROKER_CONNECT_TIMEOUT, connect=None) -> dict:
    """Ask runners/drive_upload_broker.py to upload local_path over its unix
    socket -- the only Drive credential SomPong is ever near. Never sends a
    folder id: the broker's destination is fixed server-side. Raises
    BrokerUploadError on ANY failure (unreachable socket, timeout, malformed
    response, ok:false) -- D4: a broker problem is a reportable failure,
    never a silent fallback to a direct credential SomPong must not hold.
    """
    connect = connect or _connect_broker_socket
    try:
        sock = connect(sock_path, timeout)
    except OSError as e:
        raise BrokerUploadError(f"could not reach upload broker at {sock_path}: {e}") from e

    try:
        request = json.dumps({"op": "upload", "path": str(local_path), "name": name}) + "\n"
        try:
            sock.sendall(request.encode("utf-8"))
        except OSError as e:
            raise BrokerUploadError(f"could not send request to broker: {e}") from e
        try:
            raw = _recv_line(sock, BROKER_MAX_RESPONSE_BYTES)
        except OSError as e:
            raise BrokerUploadError(f"broker did not respond: {e}") from e
    finally:
        sock.close()

    try:
        res = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise BrokerUploadError(f"broker returned an unparseable response: {e}") from e
    if not isinstance(res, dict) or not res.get("ok"):
        reason = res.get("error", "unknown error") if isinstance(res, dict) else "malformed response"
        raise BrokerUploadError(f"broker refused the upload: {reason}")
    return res


# --------------------------------------------------------------------------- download

def download(url: str, dest_dir: Path, *, attempts: int = DOWNLOAD_ATTEMPTS,
             sleep=time.sleep) -> Path:
    """yt-dlp -f "bv*+ba/best", best quality the post actually offers.

    Retries only RETRYABLE_ERROR (3 attempts, backoff). Any other error
    surfaces on the first attempt -- no blanket retry.
    """
    pathfile = dest_dir / f".ytdlp-path-{uuid.uuid4().hex}"
    err = ""
    for attempt in range(1, attempts + 1):
        pathfile.unlink(missing_ok=True)
        proc = subprocess.run(
            ["yt-dlp", "-f", "bv*+ba/best", "--no-playlist", "--restrict-filenames",
             "--no-progress", "-P", str(dest_dir), "-o", "%(uploader)s-%(id)s.%(ext)s",
             "--print-to-file", "after_move:filepath", str(pathfile), url],
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            path_text = pathfile.read_text().strip() if pathfile.exists() else ""
            pathfile.unlink(missing_ok=True)
            if not path_text:
                raise DownloadError(f"yt-dlp exited 0 but wrote no output path for {url}")
            file_path = Path(path_text.splitlines()[-1])
            if not file_path.is_file():
                raise DownloadError(f"yt-dlp reported {file_path} but it is missing")
            return file_path

        err = ((proc.stdout or "") + (proc.stderr or "")).strip()
        if RETRYABLE_ERROR not in err or attempt == attempts:
            raise DownloadError(f"yt-dlp failed for {url}: {err[-500:] or 'no output'}")
        sleep(attempt * 3)

    raise DownloadError(f"yt-dlp failed for {url}: {err[-500:] or 'no output'}")


def probe_resolution(path: Path) -> str:
    """Read the resolution back from the file itself -- what yt-dlp printed
    as a format label is a different claim than what the container holds."""
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(path)],
        capture_output=True, text=True,
    )
    out = proc.stdout.strip()
    return out if out else "unknown"


# --------------------------------------------------------------------------- log

def append_local_log(log_path: Path, lines: list[str]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        for line in lines:
            f.write(line + "\n")


def _log_line(actor: str, action: str, name: str, resolution: str, size: int,
              url: str, file_id: str | None) -> str:
    link = f"https://drive.google.com/file/d/{file_id}/view" if file_id else "-"
    return " | ".join([ts(), actor, action, "FILE", name, link, resolution, str(size), url])


# --------------------------------------------------------------------------- per-url

def process_url(url: str, *, folder_id: str, stage_dir: Path, log_path: Path,
                 actor: str = ACTOR_DEFAULT, broker_socket: str | None = None) -> bool:
    print(f"── {url}")
    try:
        local_path = download(url, stage_dir)
    except DownloadError as e:
        print(f"  FAIL  download: {e}")
        return False

    size = local_path.stat().st_size
    resolution = probe_resolution(local_path)
    name = local_path.name

    if broker_socket:
        # task-e713c4e2 D2/D4 -- no direct Drive credential access here at
        # all: no pre-upload listing (that needs Drive read, which
        # `secretary` no longer has), just ask the broker and trust nothing
        # but its own answer. Any failure (unreachable, refused, broker's
        # own verify-by-listing came back empty) is BrokerUploadError --
        # reported as a normal FAIL, never a silent fallback to upload()/
        # list_folder() below.
        try:
            res = broker_upload(broker_socket, local_path, name)
        except BrokerUploadError as e:
            print(f"  FAIL  broker upload: {e}  (kept: {local_path})")
            return False
        print(f"  OK    {name}  {resolution}  {mb(size)}  -> {res.get('id', '?')}  (via broker)")
        append_local_log(log_path, [_log_line(actor, "ADD", name, resolution, size, url, res.get("id"))])
        local_path.unlink()
        return True

    try:
        existing = list_folder(folder_id)
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL  could not list destination folder: {e}  (kept: {local_path})")
        return False

    if existing.get(name) == size:
        print(f"  SKIP  {name} already on Drive at matching size ({mb(size)}, {resolution})")
        append_local_log(log_path, [_log_line(actor, "SKIP", name, resolution, size, url, None)])
        local_path.unlink()
        return True

    try:
        res = upload(local_path, name, folder_id)
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL  upload: {e}  (kept: {local_path})")
        return False

    # Same guard as the pre-upload listing above. Without it a transient blip
    # here escapes process_url, kills the whole batch mid-run, and skips the
    # summary — one flaky call losing every later URL, right after the upload
    # that did succeed.
    try:
        fresh = list_folder(folder_id)
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL  uploaded but could not verify (list failed: {e})  (kept: {local_path})")
        return False
    drive_size = fresh.get(name)
    if drive_size is None or drive_size != size:
        reason = ("not found in a fresh folder listing" if drive_size is None
                  else f"size mismatch (local {mb(size)} vs drive {mb(drive_size)})")
        print(f"  FAIL  verify: {name} {reason}  (kept: {local_path})")
        return False

    print(f"  OK    {name}  {resolution}  {mb(size)}  -> {res.get('id', '?')}")
    append_local_log(log_path, [_log_line(actor, "ADD", name, resolution, size, url, res.get("id"))])
    local_path.unlink()
    return True


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--actor", default=ACTOR_DEFAULT)
    ap.add_argument("--log-file", type=Path, default=DEFAULT_LOG_PATH)
    args = ap.parse_args(argv)

    missing_tools = [t for t in ("yt-dlp", "ffprobe") if shutil.which(t) is None]
    if missing_tools:
        print(f"missing required tool(s): {', '.join(missing_tools)} "
              "(brew install yt-dlp ffmpeg)", file=sys.stderr)
        return 1

    broker_socket = os.environ.get(DRIVE_UPLOAD_SOCKET_VAR) or None
    if not broker_socket:
        apply_oauth_env_override()
    folder_id = DRIVE_SOMPONG_GRAB_FOLDER_ID

    stage_dir = Path(tempfile.mkdtemp(prefix="video_to_drive_"))
    ok = 0
    for url in args.urls:
        if process_url(url, folder_id=folder_id, stage_dir=stage_dir,
                       log_path=args.log_file, actor=args.actor,
                       broker_socket=broker_socket):
            ok += 1

    total = len(args.urls)
    print(f"\n{ok} of {total} succeeded")
    try:
        stage_dir.rmdir()
    except OSError:
        print(f"staging dir kept (has undeleted file(s)): {stage_dir}")

    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
