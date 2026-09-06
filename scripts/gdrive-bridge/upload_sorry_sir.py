#!/usr/bin/env python3
"""Generic single-file uploader for the «Sorry, Sir» Higgsfield generation wave
(task-da1c3064, resuming task-4da71aee's dead absence-wave-virgin28 queue).

Reuses the same OAuth-refresh-token + resumable-upload pattern as
upload_suno_cues.py / ilag_sync.py — gdrive_move.py's Apps Script bridge can
only create *text* files, so binary clips go straight to the Drive REST API.

    python3 upload_sorry_sir.py <local_path> <drive_name> <parent_folder_id>

Prints the created file's Drive link on success.
"""
from __future__ import annotations

import json
import mimetypes
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENV_CANDIDATES = [
    Path("/Users/gob/Projects/mooniex-claudeflow/.env"),
    Path("/Users/gob/Projects/mooniex-claudeflow/.env.local"),
]

DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"

_token_cache: dict[str, object] = {}


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


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        return 1
    local_path, drive_name, parent_id = sys.argv[1], sys.argv[2], sys.argv[3]
    p = Path(local_path)
    if not p.exists():
        raise SystemExit(f"local file not found: {p}")
    res = upload(p, drive_name, parent_id)
    link = f"https://drive.google.com/file/d/{res['id']}/view"
    print(json.dumps({"id": res["id"], "name": res.get("name"), "link": link,
                       "size": p.stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
