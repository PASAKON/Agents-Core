#!/usr/bin/env python3
"""The two rclone verbs stream_backup_to_drive.py uses (rcat, lsjson), done with the Mac's own Drive REST
resumable uploader (tools/work_archive.py) -- for when winbox's rclone is unreachable. BACKUP root only."""
import http.client, json, os, sys, tempfile, time, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv" / "bin" / "python"
if sys.prefix == sys.base_prefix and VENV.exists():  # tools/ needs the repo venv (yaml)
    os.execv(str(VENV), [str(VENV), __file__, *sys.argv[1:]])
sys.path.insert(0, str(ROOT))
from tools import work_archive as wa


def upload(path, name):
    """work_archive's resumable protocol, plus what it lacks: on a 5xx or a dropped connection, ask Drive
    where the upload stopped (PUT bytes */size) and resume from there instead of failing the whole file."""
    token, size = wa._access_token(), os.path.getsize(path)
    session = wa._init_resumable_session(wa._http, token, name, "application/x-tar", size)
    sent, fails = 0, 0
    with open(path, "rb") as fh:
        while True:
            fh.seek(sent)
            chunk = fh.read(min(wa.CHUNK_SIZE, size - sent))
            hdr = {"Content-Length": str(len(chunk)), "Content-Range": f"bytes {sent}-{sent + len(chunk) - 1}/{size}"}
            try:
                st, rh, body = wa._http("PUT", session, headers=hdr, body=chunk)
            except (OSError, http.client.HTTPException) as e:
                st, rh, body = None, {}, repr(e).encode()
            if st in (200, 201):
                meta = json.loads(body)
                break
            if st == 308:
                r = wa._header(rh, "Range")
                sent, fails = (int(r.rsplit("-", 1)[-1]) + 1 if r else sent + len(chunk)), 0
                continue
            fails += 1
            print(f"chunk at {sent}: status={st} {body[:120]!r}; retry {fails}", file=sys.stderr)
            if fails > 10:
                raise RuntimeError(f"gave up after {fails} failures at offset {sent}")
            time.sleep(min(60, 2 ** fails))
            try:
                st, rh, body = wa._http("PUT", session, headers={"Content-Length": "0", "Content-Range": f"bytes */{size}"}, body=b"")
            except (OSError, http.client.HTTPException):
                continue
            if st in (200, 201):
                meta = json.loads(body)
                break
            if st == 308:
                r = wa._header(rh, "Range")
                sent = int(r.rsplit("-", 1)[-1]) + 1 if r else 0
    return meta if meta.get("md5Checksum") else wa._get_file_metadata(wa._http, token, meta["id"])


a = sys.argv[1:]
root = a[a.index("--drive-root-folder-id") + 1]
if root != wa.BACKUP_FOLDER_ID:
    sys.exit(f"shim uploads to BACKUP root only, got {root}")
if a[0] == "rcat":
    name = a[1].split(":", 1)[1]
    fd, p = tempfile.mkstemp(dir=os.environ.get("SHIM_TMP"), suffix=".part")
    try:
        with os.fdopen(fd, "wb") as fh:
            while True:
                b = sys.stdin.buffer.read(8 << 20)
                if not b:
                    break
                fh.write(b)
        meta = upload(p, name)
        print(json.dumps(meta), file=sys.stderr)
    finally:
        os.remove(p)
elif a[0] == "lsjson":
    name = a[a.index("--include") + 1].lstrip("/").replace("\\[", "[")
    token = wa._access_token()
    q = f"name = '{name}' and '{root}' in parents and trashed = false"
    url = wa.DRIVE_FILES + "?" + urllib.parse.urlencode({"q": q, "fields": "files(id,name,size,md5Checksum)", "pageSize": 10})
    st, _, body = wa._http("GET", url, headers={"Authorization": "Bearer " + token})
    if st != 200:
        sys.exit(f"lsjson via REST failed: {st} {body[:200]!r}")
    print(json.dumps([{"Name": f["name"], "Size": int(f.get("size", 0)), "ID": f["id"],
                       "Hashes": {"md5": f.get("md5Checksum")}} for f in json.loads(body)["files"]]))
else:
    sys.exit(f"shim: unsupported verb {a[0]}")
