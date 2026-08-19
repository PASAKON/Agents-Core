#!/usr/bin/env python3
"""Download short video links (TikTok, YouTube Shorts, game clips, book
reels) and land them in the CEO's Google Drive, in a folder named exactly
`desktop cloud` under `DRIVE_VIDEO_PARENT_FOLDER_ID`.

    python scripts/video_to_drive.py <url> [url ...]

Per URL: download the best quality the post actually offers (staged under a
temp dir, never the CEO's Desktop), upload it into `desktop cloud`, verify by
re-listing the destination folder (an upload API 200 is not evidence the file
is there), log it locally, then delete the local staging copy. On any
failure the local copy is kept and its path printed -- nothing is ever
deleted from Drive.

This is assembly, not new Drive plumbing -- it reuses:
  - scripts/gdrive-bridge/ilag_sync.py    -- upload(), api(), OAuth
  - scripts/gdrive-bridge/ilag_mirror.py  -- list_folder() verify-by-listing
  - scripts/tiktok-grab.sh                -- the flaky-extractor retry shape

Auth (GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN, DRIVE_VIDEO_PARENT_FOLDER_ID)
is read from mooniex-claudeflow's .env, same as scripts/higgsfield/gen_loop.py.
Values are never printed.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "gdrive-bridge"))
from ilag_sync import upload, api, ts, mb, DRIVE_FILES, ACTOR_DEFAULT  # noqa: E402
from ilag_mirror import list_folder  # noqa: E402

CF_ENV_CANDIDATES = [
    Path("/Users/gob/Projects/mooniex-claudeflow/.env"),
    Path("/Users/gob/Projects/mooniex-claudeflow/.env.local"),
]

FOLDER_NAME = "desktop cloud"
# TikTok intermittently fails extraction and succeeds on an identical retry
# (hit 3 of 5 clips on 2026-08-18, per scripts/tiktok-grab.sh). Only this
# error is worth retrying -- anything else is a real failure, first try.
RETRYABLE_ERROR = "universal data for rehydration"
DOWNLOAD_ATTEMPTS = 3
DEFAULT_LOG_PATH = Path(__file__).resolve().parents[1] / "output" / "video-to-drive" / "log.txt"


class DownloadError(RuntimeError):
    pass


# --------------------------------------------------------------------------- env

def load_parent_folder_id(candidates: list[Path] = CF_ENV_CANDIDATES) -> str:
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == "DRIVE_VIDEO_PARENT_FOLDER_ID":
                val = value.strip().strip('"').strip("'")
                if val:
                    return val
    raise SystemExit("missing DRIVE_VIDEO_PARENT_FOLDER_ID in claudeflow .env")


# --------------------------------------------------------------------------- folder

def find_or_create_folder(name: str, parent_id: str) -> str:
    """Search `parent_id` for a sub-folder named `name`; create only if absent.

    Drive allows duplicate names, so a create-without-searching is a real
    bug -- the search always runs first, and creation only happens on a
    genuine miss. Callers should call this once per run and cache the id.
    """
    safe_name = name.replace("'", "\\'")
    q = (f"name = '{safe_name}' and '{parent_id}' in parents and trashed = false "
         "and mimeType = 'application/vnd.google-apps.folder'")
    res = api(DRIVE_FILES, params={"q": q, "fields": "files(id,name)", "pageSize": "10"}, timeout=60)
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    made = api(DRIVE_FILES, method="POST", params={"fields": "id,name"},
               data=json.dumps({"name": name, "parents": [parent_id],
                                "mimeType": "application/vnd.google-apps.folder"}).encode(),
               headers={"Content-Type": "application/json"})
    return made["id"]


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
                 actor: str = ACTOR_DEFAULT) -> bool:
    print(f"── {url}")
    try:
        local_path = download(url, stage_dir)
    except DownloadError as e:
        print(f"  FAIL  download: {e}")
        return False

    size = local_path.stat().st_size
    resolution = probe_resolution(local_path)
    name = local_path.name

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

    fresh = list_folder(folder_id)
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

    parent_id = load_parent_folder_id()
    folder_id = find_or_create_folder(FOLDER_NAME, parent_id)

    stage_dir = Path(tempfile.mkdtemp(prefix="video_to_drive_"))
    ok = 0
    for url in args.urls:
        if process_url(url, folder_id=folder_id, stage_dir=stage_dir,
                       log_path=args.log_file, actor=args.actor):
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
