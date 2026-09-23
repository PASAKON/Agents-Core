#!/usr/bin/env python3
"""The two rclone verbs stream_backup_to_drive.py uses (rcat, lsjson), done with the Mac's own Drive REST
resumable uploader (tools/work_archive.py) -- for when winbox's rclone is unreachable. BACKUP root only."""
import json, os, sys, tempfile, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv" / "bin" / "python"
if sys.prefix == sys.base_prefix and VENV.exists():  # tools/ needs the repo venv (yaml)
    os.execv(str(VENV), [str(VENV), __file__, *sys.argv[1:]])
sys.path.insert(0, str(ROOT))
from tools import work_archive as wa
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
        meta = wa._default_uploader(Path(p), name)
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
