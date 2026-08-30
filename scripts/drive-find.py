#!/usr/bin/env python3
"""Search the CEO's Drive from the command line, using the org's own OAuth.

The claude.ai Google Drive MCP disappears from a session's tool registry when
that session is resumed or forked, and it cannot be re-added without a restart.
That left the CTO unable to verify what had actually been filed during the
«Sorry, Sir» shoot. This reads the same Drive through `ilag_sync`, which
already holds a refresh token, so Drive stays checkable regardless of MCP
state.

    scripts/drive-find.py absence-S            # name contains
    scripts/drive-find.py absence- --keepers   # hide FLAGGED/SUPERSEDED takes
    scripts/drive-find.py '' --folder <id>     # everything in one folder
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "gdrive-bridge"))
import ilag_sync as s  # noqa: E402

REJECT_MARKERS = ("-FLAGGED-", "-SUPERSEDED-")


def main() -> int:
    ap = argparse.ArgumentParser(description="Search Drive by filename.")
    ap.add_argument("needle", help="substring of the filename ('' to match all)")
    ap.add_argument("--folder", help="restrict to this folder id")
    ap.add_argument("--mime", default="video/mp4",
                    help="mime type, or 'any' (default: video/mp4)")
    ap.add_argument("--keepers", action="store_true",
                    help="hide takes marked FLAGGED or SUPERSEDED")
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()

    clauses = ["trashed=false"]
    if args.needle:
        clauses.append(f"name contains '{args.needle}'")
    if args.mime != "any":
        clauses.append(f"mimeType='{args.mime}'")
    if args.folder:
        clauses.append(f"'{args.folder}' in parents")

    files, page = [], None
    while len(files) < args.limit:
        params = {
            "q": " and ".join(clauses),
            "fields": "nextPageToken,files(name,id,createdTime,size)",
            "orderBy": "createdTime desc",
            "pageSize": min(100, args.limit - len(files)),
        }
        if page:
            params["pageToken"] = page
        resp = s.api(s.DRIVE_FILES, params=params)
        files.extend(resp.get("files", []))
        page = resp.get("nextPageToken")
        if not page:
            break

    if args.keepers:
        files = [f for f in files
                 if not any(m in f["name"] for m in REJECT_MARKERS)]

    for f in files:
        size = int(f.get("size") or 0)
        print(f"{f['createdTime'][:16]}  {size / 1e6:6.1f}MB  {f['name']}")
    print(f"\n{len(files)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
