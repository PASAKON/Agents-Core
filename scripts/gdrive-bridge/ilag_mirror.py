#!/usr/bin/env python3
"""Upload staged Higgsfield downloads into a Do Not Disturb scene folder,
verify the size on Drive, log the ADD line, then delete the local copy.

This is the "download to staging, upload, verify, log, delete" loop from the
gdrive-filing skill's YT: ILAG section, generalised beyond the one-time
`ilag_sync.py` Desktop-mirror sweep so it can run against whatever a browser
operator just downloaded to ~/Downloads (or any other staging path).

Nothing is ever deleted before its Drive copy is confirmed by a fresh listing
of the target folder (not a trust-the-upload-response guess) with a matching
size. If verification fails the local file is left alone and reported.

Usage:
    ilag_mirror.py <folder_id> <where> <note> <file> [<file> ...]
    ilag_mirror.py --actor "AI:browser_operator-task-XXXX" \\
        1DKJv_H9LQ7B39gpcF_8-qYRX5QE08AjD "All Scene/S9-B" \\
        "uploaded from Higgsfield, mirroring sweep" \\
        ~/Downloads/hf_20260812_222133_5f012ea8-*.mp4 ...

<where> and <note> are shared across all files in one call; run it once per
(folder, note) group. Prints one line per file: UP/SKIP/FAIL, then a final
verify pass and delete pass.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ilag_sync import upload, api, append_log, ts, mb, DRIVE_FILES, ACTOR_DEFAULT  # noqa: E402


def list_folder(folder_id: str) -> dict[str, int]:
    """name -> size, for one folder (non-recursive)."""
    out: dict[str, int] = {}
    page = None
    while True:
        params = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken, files(id,name,size)",
            "pageSize": "200",
        }
        if page:
            params["pageToken"] = page
        res = api(DRIVE_FILES, params=params, timeout=60)
        for f in res.get("files", []):
            out[f["name"]] = int(f.get("size") or 0)
        page = res.get("nextPageToken")
        if not page:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder_id")
    ap.add_argument("where", help='e.g. "All Scene/S9-B"')
    ap.add_argument("note")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--actor", default=ACTOR_DEFAULT)
    ap.add_argument("--no-delete", action="store_true",
                     help="upload+verify+log but keep local copies")
    args = ap.parse_args()

    paths = [Path(f).expanduser() for f in args.files]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        print("missing local file(s):")
        for p in missing:
            print(" ", p)
        return 1

    uploaded: list[tuple[Path, dict]] = []
    failed: list[tuple[Path, str]] = []

    for p in paths:
        try:
            res = upload(p, p.name, args.folder_id)
            uploaded.append((p, res))
            print(f"  UP   {p.name}  ({mb(p.stat().st_size)})")
        except Exception as e:  # noqa: BLE001
            failed.append((p, str(e)))
            print(f"  FAIL {p.name}: {e}")

    if not uploaded:
        print("nothing uploaded, nothing to verify/log/delete")
        return 1 if failed else 0

    # Re-list the folder fresh from Drive rather than trusting the upload
    # response -- that's the point of "verify before delete".
    drive_now = list_folder(args.folder_id)

    verified: list[tuple[Path, dict]] = []
    size_mismatch: list[Path] = []
    log_lines: list[str] = []
    for p, res in uploaded:
        local_size = p.stat().st_size
        drive_size = drive_now.get(p.name)
        if drive_size is None:
            size_mismatch.append(p)
            print(f"  ALERT {p.name}: uploaded but not found in a fresh folder listing")
        elif drive_size != local_size:
            size_mismatch.append(p)
            print(f"  ALERT {p.name}: local {mb(local_size)} vs drive {mb(drive_size)} -- size mismatch")
        else:
            verified.append((p, res))
            log_lines.append(" | ".join([
                ts(), args.actor, "ADD", "FILE", p.name,
                f"https://drive.google.com/file/d/{res['id']}/view",
                args.where, str(len(drive_now)), args.note,
            ]))

    if log_lines:
        append_log(log_lines)
        print(f"logged {len(log_lines)} line(s)")

    if not args.no_delete:
        for p, _ in verified:
            p.unlink()
            print(f"  DEL  {p.name}  (verified on Drive, removed from staging)")

    if size_mismatch:
        print(f"\n{len(size_mismatch)} file(s) NOT deleted -- verification failed, left in place")
    if failed:
        print(f"{len(failed)} file(s) failed to upload")

    return 1 if (failed or size_mismatch) else 0


if __name__ == "__main__":
    raise SystemExit(main())
