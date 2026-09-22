#!/usr/bin/env python3
"""Upload the 3 waltz soundtrack files to Sorry, Sir/Soundtrack.

task-ccab4d57. Reuses the same OAuth-refresh-token + resumable-upload pattern
as upload_suno_cues.py / ilag_sync.py (those scripts are scoped to their own
jobs and are not touched here).

    python3 upload_sorry_sir_soundtrack.py            # upload all 3, log each immediately
    python3 upload_sorry_sir_soundtrack.py --dry-run  # list what would upload, no writes
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=7))
ACTOR = "AI:browser_operator-task-ccab4d57"

SOUNDTRACK_FOLDER_ID = "1CN5ceI34pxKfAf6b9UkIK1DcgB08BvfC"
LOGS_FILE_ID = "1bSH4v-E8PLkUtZVACum_O2nW1_FlsBuW"

DOWNLOADS = Path.home() / "Downloads"
FILES = [
    DOWNLOADS / "The Great Balalaika Waltz.wav",
    DOWNLOADS / "The Great Balalaika Waltz-2.wav",
    DOWNLOADS / "Elegy for a Fading Waltz.wav",
]

NOTE = "soundtrack upload for Sorry, Sir project setup"

ENV_CANDIDATES = [
    Path("/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env"),
    Path("/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env.local"),
]

DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"


def _load_oauth() -> dict:
    found: dict[str, str] = {}
    for path in ENV_CANDIDATES:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key.startswith("GOOGLE_OAUTH_"):
                found.setdefault(key, value.strip().strip('"').strip("'"))
    missing = [k for k in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET",
                           "GOOGLE_OAUTH_REFRESH_TOKEN") if k not in found]
    if missing:
        raise SystemExit("missing Drive OAuth vars: " + ", ".join(missing))
    return found


_token_cache: dict[str, object] = {}


def access_token() -> str:
    now = datetime.now(timezone.utc).timestamp()
    if _token_cache.get("value") and float(_token_cache.get("exp", 0)) > now:
        return str(_token_cache["value"])
    cfg = _load_oauth()
    body = urllib.parse.urlencode({
        "client_id": cfg["GOOGLE_OAUTH_CLIENT_ID"],
        "client_secret": cfg["GOOGLE_OAUTH_CLIENT_SECRET"],
        "refresh_token": cfg["GOOGLE_OAUTH_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body,
                                 method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    _token_cache["value"] = data["access_token"]
    _token_cache["exp"] = now + int(data.get("expires_in", 3600)) - 60
    return data["access_token"]


def upload(local_path: Path, name: str, parent_id: str) -> dict:
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    size = local_path.stat().st_size
    meta = json.dumps({"name": name, "parents": [parent_id]}).encode()
    init = urllib.request.Request(
        DRIVE_UPLOAD + "?" + urllib.parse.urlencode({"uploadType": "resumable",
                                                     "fields": "id,name,size"}),
        data=meta,
        headers={
            "Authorization": "Bearer " + access_token(),
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime,
            "X-Upload-Content-Length": str(size),
        },
        method="POST",
    )
    with urllib.request.urlopen(init, timeout=60) as resp:
        session_url = resp.headers["Location"]

    body = local_path.read_bytes()
    put = urllib.request.Request(
        session_url, data=body,
        headers={"Content-Type": mime, "Content-Length": str(size)},
        method="PUT",
    )
    with urllib.request.urlopen(put, timeout=1800) as resp:
        return json.loads(resp.read())


def append_log_line(line: str) -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    from gdrive_move import call  # noqa: E402
    call("append_log", fileId=LOGS_FILE_ID, lines=[line])


def ts() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def mb(n: int) -> str:
    return f"{n / 1048576:.1f} MB"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--start-count", type=int, default=0,
                    help="running file count in the folder before this add (default 0, "
                         "folder is empty)")
    args = ap.parse_args()

    missing = [f for f in FILES if not f.exists()]
    if missing:
        raise SystemExit("missing local file(s): " + ", ".join(str(m) for m in missing))

    if args.dry_run:
        for f in FILES:
            print(f"  WOULD UPLOAD {f.name}  ({mb(f.stat().st_size)})")
        return 0

    n = args.start_count
    for f in FILES:
        res = upload(f, f.name, SOUNDTRACK_FOLDER_ID)
        link = f"https://drive.google.com/file/d/{res['id']}/view"
        print(f"  UP {f.name}  ({mb(f.stat().st_size)})  {link}")
        n += 1
        line = " | ".join([ts(), ACTOR, "ADD", "FILE", f.name, link,
                           "Soundtrack", str(n), NOTE])
        append_log_line(line)
        print(f"  LOGGED n={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
