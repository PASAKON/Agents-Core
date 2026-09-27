"""YT: ILAG Drive helpers over REST (ClaudeFlow OAuth) for boxes without the Apps Script bridge config (Contabo).

ls/child/mkfolder (create only if absent), upload (refuses a same-name file, md5 checked by id),
append_log (GET -> append -> PATCH -> the old text must survive as a prefix), rename, line() for the
9-field logs.txt contract. Used 2026-09-24 to build the TopView trailer project (cto-e1e3d3ef).
"""
import json, os, sys, urllib.request, urllib.parse, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

os.environ.setdefault("MOONIEX_CLAUDEFLOW_ENV", "/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env")
sys.path.insert(0, "/opt/MoonieXHQ/Agents/Core/scripts/gdrive-bridge")
import ilag_sync as s  # noqa: E402

FOLDER = "application/vnd.google-apps.folder"
ACTOR = os.environ.get("ILAG_LOG_ACTOR", "AI:unknown")  # set AI:<role>-<sid> before logging
TH = timezone(timedelta(hours=7))


def now():
    return datetime.now(TH).isoformat(timespec="seconds")


def ls(fid):
    out, page = [], None
    while True:
        p = {"q": f"'{fid}' in parents and trashed = false",
             "fields": "nextPageToken, files(id,name,mimeType,size,md5Checksum)", "pageSize": "200"}
        if page:
            p["pageToken"] = page
        r = s.api(s.DRIVE_FILES, params=p, timeout=60)
        out += r.get("files", [])
        page = r.get("nextPageToken")
        if not page:
            return out


def child(parent, name):
    for f in ls(parent):
        if f["name"] == name:
            return f
    return None


def mkfolder(parent, name):
    """Create only if absent. Returns (id, created?)."""
    got = child(parent, name)
    if got:
        return got["id"], False
    made = s.api(s.DRIVE_FILES, method="POST", params={"fields": "id,name"},
                 data=json.dumps({"name": name, "parents": [parent], "mimeType": FOLDER}).encode(),
                 headers={"Content-Type": "application/json"})
    return made["id"], True


def upload(path, name, parent):
    """Refuses to create a second file of the same name in the folder."""
    got = child(parent, name)
    if got:
        return got, False
    meta = s.upload(Path(path), name, parent)
    info = s.api(s.DRIVE_FILES + "/" + meta["id"], params={"fields": "id,name,size,md5Checksum"})
    local = hashlib.md5(Path(path).read_bytes()).hexdigest()
    if info.get("md5Checksum") != local:
        raise SystemExit(f"MD5 MISMATCH {name}: drive {info.get('md5Checksum')} local {local}")
    return info, True


def upload_stream(path, name, parent, chunk=64 * 1024 * 1024):
    """upload() for big files: a resumable session fed 64 MB at a time, md5 computed while reading, checked by id.
    upload() (ilag_sync.upload) holds the whole file in memory — 1.2 GB on Contabo's 7.9 GB, next to other jobs,
    is how background jobs get reaped. Refuses a same-name file like upload()."""
    got = child(parent, name)
    if got:
        return got, False
    size = os.path.getsize(path)
    req = urllib.request.Request(
        s.DRIVE_UPLOAD + "?uploadType=resumable&fields=id,name,size,md5Checksum", method="POST",
        data=json.dumps({"name": name, "parents": [parent]}).encode(),
        headers={"Authorization": "Bearer " + s.access_token(), "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Length": str(size)})
    session = urllib.request.urlopen(req, timeout=60).headers["Location"]
    md5, sent, meta = hashlib.md5(), 0, None
    with open(path, "rb") as f:
        while sent < size:
            buf = f.read(chunk)
            md5.update(buf)
            end = sent + len(buf) - 1
            put = urllib.request.Request(session, data=buf, method="PUT", headers={
                "Authorization": "Bearer " + s.access_token(), "Content-Length": str(len(buf)),
                "Content-Range": f"bytes {sent}-{end}/{size}"})
            try:
                meta = json.loads(urllib.request.urlopen(put, timeout=600).read() or b"{}")
            except urllib.error.HTTPError as e:
                if e.code != 308:  # 308 = chunk stored, send the next one
                    raise
            sent = end + 1
            print(f"  {name}: {sent / size:.0%}", flush=True)
    if not meta or meta.get("md5Checksum") != md5.hexdigest():
        raise SystemExit(f"MD5 MISMATCH {name}: drive {meta and meta.get('md5Checksum')} local {md5.hexdigest()}")
    return meta, True


def read_text(fid):
    req = urllib.request.Request(s.DRIVE_FILES + "/" + fid + "?alt=media",
                                 headers={"Authorization": "Bearer " + s.access_token()})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")


def put_text(fid, text):
    req = urllib.request.Request(
        s.DRIVE_UPLOAD + "/" + fid + "?uploadType=media", data=text.encode("utf-8"),
        headers={"Authorization": "Bearer " + s.access_token(),
                 "Content-Type": "text/plain; charset=utf-8"}, method="PATCH")
    urllib.request.urlopen(req, timeout=60).read()


def append_log(fid, lines):
    """GET -> append -> PATCH -> re-read: the old text must be an intact prefix."""
    old = read_text(fid)
    add = "".join(l.rstrip("\n") + "\n" for l in lines)
    base = old if old.endswith("\n") or not old else old + "\n"
    put_text(fid, base + add)
    back = read_text(fid)
    if not back.startswith(old) or not back.endswith(add):
        raise SystemExit(f"LOG APPEND CHECK FAILED on {fid}")
    return len(old.encode()), len(back.encode())


def line(action, typ, name, link, where, n, note):
    return " | ".join([now(), ACTOR, action, typ, name, link, where, str(n), note])


def flink(fid):
    return f"https://drive.google.com/drive/folders/{fid}"


def link(fid):
    return f"https://drive.google.com/file/d/{fid}/view"


def rename(fid, name):
    return s.api(s.DRIVE_FILES + "/" + fid, method="PATCH", params={"fields": "id,name"},
                 data=json.dumps({"name": name}).encode(),
                 headers={"Content-Type": "application/json"})
