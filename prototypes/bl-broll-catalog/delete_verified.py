#!/usr/bin/env python3
"""delete_verified.py — remove the LOCAL copy of each clip that is proven on Drive.

CEO 2026-09-18: "หลังจาก Up ลง Gdrive แล้วฝากลบในเครื่องด้วย … เช็คให้ชัวร์ก่อนลบ อย่าพลาด".

Refuses to delete anything unless EVERY row in the manifest is verified. Then, per
file, re-fetches the Drive md5 immediately before that one deletion and deletes
only on a fresh match. One file at a time, logged, never a glob. --dry-run prints
what would go.
"""
import json, sys, hashlib, importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta
ROOT = Path(__file__).resolve().parent
CAT, MAN = ROOT / "broll-catalog.json", ROOT / "drive-manifest.json"
SRC = Path("/Users/gob/Desktop/archive")
LOG = Path.home() / ".claude/logs/drive-archive.log"
DRY = "--dry-run" in sys.argv
spec = importlib.util.spec_from_file_location("ilag", "/Users/gob/MoonieXHQ/Agents/Core/scripts/gdrive-bridge/ilag_sync.py")
ilag = importlib.util.module_from_spec(spec); spec.loader.exec_module(ilag)
now = lambda: datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")

rows = json.load(open(CAT, encoding="utf-8")); man = json.load(open(MAN))
missing = [r["n"] for r in rows if not man.get(str(r["n"]), {}).get("verified")]
if missing:
    print(f"REFUSING: {len(missing)} of {len(rows)} rows are not verified on Drive: {missing}")
    sys.exit(2)

def local_md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()

deleted = kept = 0
for r in rows:
    m = man[str(r["n"])]; p = SRC / r["source_file"]
    if not p.exists():
        print(f"[{r['n']:02d}] already gone locally"); continue
    live = ilag.api(f"https://www.googleapis.com/drive/v3/files/{m['drive_id']}",
                    params={"fields": "id,md5Checksum,size,trashed"})
    fresh_ok = (live.get("md5Checksum") == m["local_md5"] and not live.get("trashed")
                and int(live.get("size", -1)) == m["bytes"] and local_md5(p) == m["local_md5"])
    if not fresh_ok:
        kept += 1
        print(f"[{r['n']:02d}] KEEP — Drive re-check failed: {live}")
        continue
    if DRY:
        print(f"[{r['n']:02d}] would delete {p.name}  (drive {m['drive_id']} md5 ok)"); continue
    p.unlink(); deleted += 1
    with open(LOG, "a") as f:
        f.write(f"{now()} | {p} | DELETED LOCAL after fresh Drive md5 re-check | id {m['drive_id']} | md5 {m['local_md5']}\n")
    print(f"[{r['n']:02d}] deleted {p.name}")
left = sorted(x.name for x in SRC.iterdir()) if SRC.exists() else []
print(f"\n{'DRY RUN ' if DRY else ''}deleted={deleted} kept={kept}  remaining in archive: {len(left)} {left[:5]}")
