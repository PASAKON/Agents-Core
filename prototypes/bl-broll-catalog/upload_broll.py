#!/usr/bin/env python3
"""upload_broll.py — push the catalogued B-roll to Drive, verify every file by md5, log every file.

Never deletes anything. Re-runnable: a row already verified is skipped, and a
file that already exists in the destination with a matching md5 is adopted
rather than uploaded twice. Deletion of the local copies is a separate,
deliberate step (delete_verified.py) that re-checks Drive first.
"""
import json, sys, time, importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent
CAT, MAN = ROOT / "broll-catalog.json", ROOT / "drive-manifest.json"
SRC = Path("/Users/gob/Desktop/archive")
DEST = "1vg8j7DY_hPE-X3yyTsp6ZrM8Gf72cfVG"      # AI Assets/BLACK LIQUIDITY (9:16) — by id, never by name
LOG = Path.home() / ".claude/logs/drive-archive.log"
spec = importlib.util.spec_from_file_location("ilag", "/Users/gob/Projects/Agents/scripts/gdrive-bridge/ilag_sync.py")
ilag = importlib.util.module_from_spec(spec); spec.loader.exec_module(ilag)
TZ = timezone(timedelta(hours=7))
now = lambda: datetime.now(TZ).isoformat(timespec="seconds")

def meta(fid):
    return ilag.api(f"https://www.googleapis.com/drive/v3/files/{fid}",
                    params={"fields": "id,name,size,md5Checksum,parents,trashed"})

def existing(name):
    q = f"name = '{name}' and '{DEST}' in parents and trashed = false"
    r = ilag.api("https://www.googleapis.com/drive/v3/files",
                 params={"q": q, "fields": "files(id,name,size,md5Checksum)", "pageSize": 5})
    return r.get("files", [])

rows = json.load(open(CAT, encoding="utf-8"))
man = json.load(open(MAN)) if MAN.exists() else {}
LOG.parent.mkdir(parents=True, exist_ok=True)
save = lambda: json.dump(man, open(MAN, "w"), indent=1)
def log(line):
    with open(LOG, "a") as f: f.write(line + "\n")

ok_n = skip_n = bad_n = 0
for r in rows:
    key = str(r["n"])
    if man.get(key, {}).get("verified"):
        skip_n += 1; continue
    src, name = SRC / r["source_file"], r["filename"]
    try:
        ex = [f for f in existing(name) if f.get("md5Checksum") == r["local_md5"]]
        if ex:
            fid, how = ex[0]["id"], "adopted-existing"
        else:
            fid, how = ilag.upload(src, name, DEST)["id"], "uploaded"
        m = meta(fid)
        ok = (m.get("md5Checksum") == r["local_md5"] and int(m.get("size", -1)) == r["local_bytes"]
              and DEST in m.get("parents", []) and not m.get("trashed"))
        man[key] = {"n": r["n"], "source_file": r["source_file"], "filename": name, "drive_id": fid,
                    "local_md5": r["local_md5"], "drive_md5": m.get("md5Checksum"), "bytes": r["local_bytes"],
                    "verified": bool(ok), "how": how, "at": now()}
        save()
        log(f"{now()} | {src} | AI Assets/BLACK LIQUIDITY (9:16)/{name} | 1 file | {r['local_bytes']} B | "
            f"md5 {r['local_md5']} | drive md5 {m.get('md5Checksum')} | {'verified' if ok else 'MISMATCH'} | id {fid}")
        print(f"[{r['n']:02d}] {how:16s} {'OK ' if ok else 'BAD'} {name}", flush=True)
        ok_n += ok; bad_n += (not ok)
    except Exception as e:
        man[key] = {"n": r["n"], "source_file": r["source_file"], "filename": name,
                    "verified": False, "error": repr(e)[:300], "at": now()}
        save(); bad_n += 1
        print(f"[{r['n']:02d}] ERROR {name}: {e!r}"[:220], flush=True)
        time.sleep(5)

print(f"\nDONE verified={ok_n} skipped={skip_n} failed={bad_n} of {len(rows)}")
print("ALL_VERIFIED" if all(man.get(str(r['n']), {}).get('verified') for r in rows) else "NOT_ALL_VERIFIED")
