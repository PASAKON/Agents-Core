#!/usr/bin/env python3
"""Compare the local "Do Not Disturb" mirror against its Google Drive branch.

Scope is deliberately one project: `ALL DRAFT/YT: ILAG/Do Not Disturb` and the
CEO's local mirror of it. Nothing else on Drive is touched (CEO 2026-08-12:
"หน้าที่คุณจะช่วยดูแล การย้ายไฟล์ลง Gdrive แค่โปรเจคนี้โปรเจคเดียว").

Why not the Apps Script bridge: `gdrive_move.py` talks to a web app that can
only create *text* files, and the mirror is ~500 MB of mp4/webp. Uploads go
straight to the Drive REST API instead, resumably, reusing the OAuth refresh
token mooniex-claudeflow already holds for this same Drive.

    ilag_sync.py diff              # read-only report (default)
    ilag_sync.py upload            # upload what is only-local, then log it
    ilag_sync.py diff --log        # report AND append findings to logs.txt

A file present on Drive but missing locally is reported as an ALERT, not as
routine drift: the CEO does not delete files except true duplicates or broken
generations, and keeps every superseded take as generation history. So a
disappearance is a signal that something went wrong, and it is never resolved
by deleting the Drive copy — this tool never deletes anything, anywhere.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

TZ = timezone(timedelta(hours=7))
ACTOR_DEFAULT = "AI:cto"

LOCAL_ROOT = Path("/Users/gob/Desktop/Do Not Disdurb")
DRIVE_ROOT_ID = "1GT_h_D6pMMpPuspoP7d_lXz9dzZQAt6w"   # Do Not Disturb
LOGS_FILE_ID = "1GVmc1Cqg-97YMcCd303_1EbNFhaiIfiO"    # its logs.txt

# The local mirror and Drive disagree on spelling in a few places. Drive is
# canonical (the CEO corrected "All Sence" -> "All Scene" there on 2026-08-12);
# these map a local folder name onto the Drive one so the two trees line up.
FOLDER_ALIASES = {
    "All Screne": "All Scene",
    "SoudTrack": "Soundtrack",
    "Charactor": "Character",
}

IGNORE_NAMES = {".DS_Store", "Thumbs.db"}

# Where claudeflow's env file lives, per host. `MOONIEX_CLAUDEFLOW_ENV` wins when set,
# so a new box needs an env var rather than a code change. Mac paths first (the common
# case), then the Contabo VPS, whose repo lives under /root/projects.
ENV_CANDIDATES = [
    Path(p) for p in filter(None, [
        os.environ.get("MOONIEX_CLAUDEFLOW_ENV"),
        "/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env",
        "/Users/gob/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env.local",
        "/root/projects/mooniex-claudeflow/.env",
        "/root/projects/mooniex-claudeflow/.env.local",
    ])
]

DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"


# --------------------------------------------------------------------------- auth

def _load_oauth() -> dict:
    """Pull the Drive OAuth triple out of claudeflow's env file.

    Values are never printed, logged, or written anywhere. Only their presence
    is ever reported.
    """
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


def api(url: str, *, method: str = "GET", params: dict | None = None,
        data: bytes | None = None, headers: dict | None = None,
        timeout: int = 300):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    hdrs = {"Authorization": "Bearer " + access_token()}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else {}


# --------------------------------------------------------------------------- trees

def walk_local(root: Path) -> dict[str, dict]:
    """relative posix path -> {size, abs}. Folder names alias-mapped to Drive's."""
    out: dict[str, dict] = {}
    if not root.exists():
        raise SystemExit(f"local mirror not found: {root}")
    for path in root.rglob("*"):
        if path.is_dir() or path.name in IGNORE_NAMES:
            continue
        parts = list(path.relative_to(root).parts)
        parts[:-1] = [FOLDER_ALIASES.get(p, p) for p in parts[:-1]]
        out["/".join(parts)] = {"size": path.stat().st_size, "abs": path}
    return out


def walk_drive(folder_id: str) -> tuple[dict[str, dict], dict[str, str]]:
    """relative path -> file meta, plus a map of relative folder path -> id."""
    files: dict[str, dict] = {}
    folders: dict[str, str] = {"": folder_id}
    stack = [(folder_id, "")]
    while stack:
        fid, pre = stack.pop()
        page = None
        while True:
            params = {
                "q": f"'{fid}' in parents and trashed = false",
                "fields": "nextPageToken, files(id,name,mimeType,size,modifiedTime)",
                "pageSize": "200",
            }
            if page:
                params["pageToken"] = page
            res = api(DRIVE_FILES, params=params, timeout=60)
            for f in res.get("files", []):
                rel = f"{pre}{f['name']}"
                if f["mimeType"] == "application/vnd.google-apps.folder":
                    folders[rel] = f["id"]
                    stack.append((f["id"], rel + "/"))
                else:
                    files[rel] = {"id": f["id"], "size": int(f.get("size") or 0),
                                  "mime": f["mimeType"]}
            page = res.get("nextPageToken")
            if not page:
                break
    return files, folders


# --------------------------------------------------------------------------- upload

def upload(local_path: Path, name: str, parent_id: str) -> dict:
    """Resumable upload. Returns the created file's metadata."""
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


def ensure_folder(rel_dir: str, folders: dict[str, str], *, create: bool) -> str | None:
    """Resolve a relative folder path to a Drive id, creating it only if asked.

    Returns None when the folder is absent and creation was not authorised —
    the gdrive-filing skill forbids inventing folders without the CEO's say-so.
    """
    if rel_dir in folders:
        return folders[rel_dir]
    if not create:
        return None
    parent_rel, _, name = rel_dir.rpartition("/")
    parent_id = ensure_folder(parent_rel, folders, create=create) if parent_rel else folders[""]
    if parent_id is None:
        return None
    made = api(DRIVE_FILES, method="POST",
               params={"fields": "id,name"},
               data=json.dumps({"name": name, "parents": [parent_id],
                                "mimeType": "application/vnd.google-apps.folder"}).encode(),
               headers={"Content-Type": "application/json"})
    folders[rel_dir] = made["id"]
    return made["id"]


# --------------------------------------------------------------------------- log

def append_log(lines: list[str]) -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    from gdrive_move import call  # noqa: E402
    for start in range(0, len(lines), 40):
        call("append_log", fileId=LOGS_FILE_ID, lines=lines[start:start + 40])


def ts() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def mb(n: int) -> str:
    return f"{n / 1048576:.1f} MB"


# --------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["diff", "upload"], nargs="?", default="diff")
    ap.add_argument("--log", action="store_true", help="append findings to logs.txt")
    ap.add_argument("--actor", default=ACTOR_DEFAULT, help="actor string for log lines")
    ap.add_argument("--create-folders", action="store_true",
                    help="create Drive folders that exist only locally (ASK THE CEO FIRST)")
    args = ap.parse_args()

    local = walk_local(LOCAL_ROOT)
    drive, folders = walk_drive(DRIVE_ROOT_ID)

    only_local = sorted(set(local) - set(drive))
    # Drive-native files were never in the mirror and never will be: the log
    # itself, and anything Google owns the format of (Docs/Sheets/Slides have
    # no local bytes to compare). Alerting on them every run would train the
    # reader to skim past the alerts that do matter.
    only_drive = sorted(p for p in set(drive) - set(local)
                        if not drive[p]["mime"].startswith("application/vnd.google-apps")
                        and p.rpartition("/")[2] != "logs.txt")
    both = sorted(set(local) & set(drive))
    size_mismatch = [p for p in both if drive[p]["size"] and local[p]["size"] != drive[p]["size"]]

    print(f"local  : {len(local)} file(s), {mb(sum(f['size'] for f in local.values()))}")
    print(f"drive  : {len(drive)} file(s)")
    print(f"in both: {len(both)}   size-mismatch: {len(size_mismatch)}")
    print()

    print(f"== ONLY LOCAL - not on Drive yet ({len(only_local)}) ==")
    unmapped = set()
    for p in only_local:
        d = p.rpartition("/")[0]
        if d and d not in folders:
            unmapped.add(d)
        print(f"  {p}  ({mb(local[p]['size'])})")
    print()

    if unmapped:
        print("== folders that do not exist on Drive ==")
        for d in sorted(unmapped):
            print(f"  {d}/   <- needs the CEO's OK before creating (skill Rule 3)")
        print()

    print(f"== ONLY ON DRIVE - missing locally ({len(only_drive)}) ==")
    if only_drive:
        print("  ALERT: the CEO does not delete files except duplicates or broken")
        print("  generations, so anything here is worth explaining, not ignoring.")
    for p in only_drive:
        print(f"  {p}")
    print()

    if size_mismatch:
        print(f"== SAME NAME, DIFFERENT SIZE ({len(size_mismatch)}) ==")
        for p in size_mismatch:
            print(f"  {p}  local {mb(local[p]['size'])} vs drive {mb(drive[p]['size'])}")
        print()

    if args.mode == "diff":
        if args.log:
            lines = [f"# DIFF {ts()} by {args.actor} - local mirror vs Drive: "
                     f"{len(only_local)} only-local, {len(only_drive)} only-drive, "
                     f"{len(size_mismatch)} size-mismatch"]
            for p in only_drive:
                lines.append(" | ".join([ts(), args.actor, "ALERT", "FILE",
                                         p.rpartition("/")[2],
                                         f"https://drive.google.com/file/d/{drive[p]['id']}/view",
                                         p.rpartition("/")[0] or "/", "-",
                                         "on Drive but missing from the local mirror"]))
            append_log(lines)
            print(f"logged {len(lines)} line(s)")
        return 0

    uploaded, skipped, failed = 0, 0, []
    log_lines: list[str] = []
    for p in only_local:
        rel_dir, _, name = p.rpartition("/")
        parent = (ensure_folder(rel_dir, folders, create=args.create_folders)
                  if rel_dir else folders[""])
        if parent is None:
            print(f"  SKIP {p}  (Drive folder '{rel_dir}' does not exist)")
            skipped += 1
            continue
        try:
            res = upload(local[p]["abs"], name, parent)
            uploaded += 1
            print(f"  UP   {p}  ({mb(local[p]['size'])})")
            log_lines.append(" | ".join([
                ts(), args.actor, "ADD", "FILE", name,
                f"https://drive.google.com/file/d/{res['id']}/view",
                rel_dir or "/", "-", "uploaded from the local Desktop mirror"]))
        except Exception as e:  # noqa: BLE001
            failed.append((p, str(e)))
            print(f"  FAIL {p}: {e}")

    print(f"\nuploaded {uploaded}, skipped {skipped}, failed {len(failed)}")
    if log_lines:
        append_log(log_lines)
        print(f"logged {len(log_lines)} line(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
