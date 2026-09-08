#!/usr/bin/env python3
"""Upload one finished clip to Sorry, Sir / All Scene / Fix-1, and log it.

    upload_fix1.py <local-file> <drive-name> [note...]

Reuses the same OAuth-refresh-token + resumable-upload pattern as
ilag_sync.py / upload_sorry_sir_soundtrack.py. Generic replacement for the
soundtrack script's hardcoded 3-file list -- this one takes any single clip
and any target name, for repeat use across Fix-1 waves.
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

FIX1_FOLDER_ID = "1WBk3uts8UaJQwBZuLwWjTFf6mcCMoidc"   # All Scene/Fix-1 — CLOSED to new clips 2026-09-08
FIX2_FOLDER_ID = "1rkCQ5SSZeOvyX-0UZXe3OvBtFhObHrkw"   # All Scene/Fix-2 — the SECOND EDIT (CEO 2026-09-08):
                                                      # every clip from 2026-09-08 to the end of the project
FOLDERS = {FIX1_FOLDER_ID: "All Scene/Fix-1", FIX2_FOLDER_ID: "All Scene/Fix-2"}
LOGS_FILE_ID = "1bSH4v-E8PLkUtZVACum_O2nW1_FlsBuW"      # Sorry, Sir/logs.txt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ilag_sync import access_token, DRIVE_UPLOAD  # noqa: E402


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
    from gdrive_move import call  # noqa: E402
    call("append_log", fileId=LOGS_FILE_ID, lines=[line])


def ts() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("local_file")
    ap.add_argument("drive_name")
    ap.add_argument("note", nargs="*", default=["Fix-2 wave upload"])
    ap.add_argument("--actor", default="AI:browser_operator")
    ap.add_argument("--folder-id", default=FIX2_FOLDER_ID,
                    help="destination folder id (default: Fix-2, the second edit; "
                         "Fix-1 is closed to new clips since 2026-09-08)")
    args = ap.parse_args()

    local = Path(args.local_file)
    if not local.exists():
        raise SystemExit(f"local file not found: {local}")

    res = upload(local, args.drive_name, args.folder_id)
    link = f"https://drive.google.com/file/d/{res['id']}/view"
    print(f"UP {args.drive_name}  ({local.stat().st_size / 1048576:.1f} MB)  {link}")

    note = " ".join(args.note)
    line = " | ".join([ts(), args.actor, "ADD", "FILE", args.drive_name, link,
                       FOLDERS.get(args.folder_id, args.folder_id), "-", note])
    append_log_line(line)
    print("LOGGED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
