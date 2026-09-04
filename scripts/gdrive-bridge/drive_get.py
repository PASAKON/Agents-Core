#!/usr/bin/env python3
"""Pull a file back DOWN from Drive by name.

Everything else in this directory pushes: ilag_mirror uploads, ilag_sync
mirrors, gdrive_move moves. Nothing fetched, and that turned out to matter —
operators file a take, verify it on Drive and correctly delete their local
staging copy, at which point the CTO can no longer watch the clip they are
supposed to sign off on. This closes that hole.

    drive_get.py <name-or-substring> [dest-dir] [--folder <id>]

Prints one line per candidate and downloads the newest match. Default folder is
All Scene/Fix-1, which is where every Fix-1 take is filed.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ilag_sync import DRIVE_FILES, access_token, api  # noqa: E402

FIX1_FOLDER = "1WBk3uts8UaJQwBZuLwWjTFf6mcCMoidc"   # All Scene/Fix-1


def find(name: str, folder: str) -> list[dict]:
    """Newest first. `name` is matched as a substring, case-insensitively."""
    out: list[dict] = []
    page = None
    while True:
        params = {
            "q": f"'{folder}' in parents and trashed=false",
            "fields": "nextPageToken,files(id,name,size,modifiedTime)",
            "orderBy": "modifiedTime desc",
            "pageSize": 200,
        }
        if page:
            params["pageToken"] = page
        res = api(DRIVE_FILES, params=params)
        out.extend(res.get("files", []))
        page = res.get("nextPageToken")
        if not page:
            break
    needle = name.lower()
    return [f for f in out if needle in f["name"].lower()]


def download(file_id: str, dest: Path) -> int:
    req = urllib.request.Request(
        f"{DRIVE_FILES}/{file_id}?alt=media",
        headers={"Authorization": "Bearer " + access_token()},
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=900) as resp, dest.open("wb") as fh:
        shutil.copyfileobj(resp, fh)
    return dest.stat().st_size


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("dest", nargs="?", default=".")
    ap.add_argument("--folder", default=FIX1_FOLDER)
    ap.add_argument("--all", action="store_true", help="fetch every match, not just the newest")
    args = ap.parse_args()

    hits = find(args.name, args.folder)
    if not hits:
        print(f"no match for {args.name!r} in folder {args.folder}")
        return 1
    for f in hits:
        print(f"  {f.get('modifiedTime','?')}  {int(f.get('size',0))/1e6:7.1f}MB  {f['name']}")

    targets = hits if args.all else hits[:1]
    for f in targets:
        dest = Path(args.dest) / f["name"]
        size = download(f["id"], dest)
        # Size is checked against Drive's own record rather than trusted from
        # the response, because a truncated download still exits cleanly.
        want = int(f.get("size", 0))
        ok = "OK" if not want or size == want else f"SIZE MISMATCH want={want}"
        print(f"GOT  {dest}  ({size/1e6:.1f}MB)  {ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
