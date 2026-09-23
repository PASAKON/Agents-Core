#!/usr/bin/env python3
"""cookierun_backup_stream.py -- stream Cookie Run data to Drive as verified tars, then free the disk.

Written 2026-09-24 for the CEO's order before winbox's Windows reinstall
("สำรองข้อมูล CookieRun Replay และข้อมูล Training ทั้งหมดก่อนได้เลย · ระหว่างสำรอง ทยอยลบ
ข้อมูลที่สำรองแล้วด้วย"). C: had 0.8 GB free, so nothing is staged locally: each part is
`tar -> rclone rcat` straight into Drive, hashed on the way (the same shape as
cookierun-bot/tools/stream_take_to_drive.py, generalised to any list of paths).

Per part, in this order, and nothing is deleted unless every step passed:
  1. stream the tar, md5 + sha256 + byte count computed from the bytes rclone was fed
  2. read the Drive object back (rclone lsjson --hash): size AND md5 must equal the stream's
  3. upload <part>.manifest.json next to it (file list, sizes, hashes, restore line)
  4. append a ledger line; only then, with --delete, remove exactly the files in that part
     (never a whole directory by name) and the directories they leave empty

    python cookierun_backup_stream.py <plan.json> [--delete] [--only ID]

plan.json: [{"id", "dest": "gdrive:BACKUP/CookieRun Backup/<folder>/<name>.tar",
             "base": <dir the tar paths are relative to>, "paths": [dirs or files],
             "keep": true -> back up only, never delete}, ...]
A part already in the ledger as verified is skipped, so a re-run resumes.
"""
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import time

RC = open(r"C:\Users\UsEr\cookierun-bot\tools\rclone_path.txt").read().strip()
HERE = r"C:\mooniex\pclease"
LEDGER = os.path.join(HERE, "backup_ledger.jsonl")
PROGRESS = os.path.join(HERE, "backup_progress.txt")
NW = 0x08000000


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(os.path.join(HERE, "backup_stream.log"), "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def c_free_gb():
    import shutil
    return shutil.disk_usage("C:\\").free / 1e9


def ledger():
    if not os.path.exists(LEDGER):
        return {}
    out = {}
    for line in open(LEDGER, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        out[r["id"]] = r
    return out


def write_ledger(row):
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def files_of(paths):
    out = []
    for p in paths:
        if os.path.isfile(p):
            out.append(p)
            continue
        for root, dirs, fs in os.walk(p):
            dirs.sort()
            for f in sorted(fs):
                out.append(os.path.join(root, f))
    return out


class Hasher:
    """File-like sink: forwards to rclone's stdin, hashing and counting."""

    def __init__(self, pipe):
        self.pipe, self.n = pipe, 0
        self.sha, self.md5 = hashlib.sha256(), hashlib.md5()

    def write(self, b):
        self.pipe.write(b)
        self.sha.update(b)
        self.md5.update(b)
        self.n += len(b)
        return len(b)

    def flush(self):
        self.pipe.flush()


def progress(plan, done_ids, current=None):
    done = [p for p in plan if p["id"] in done_ids]
    gb_done = sum(p.get("bytes", 0) for p in done) / 1e9
    gb_all = sum(p.get("bytes", 0) for p in plan) / 1e9
    line = (f"{time.strftime('%Y-%m-%d %H:%M:%S')} winbox Cookie Run backup: {len(done)}/{len(plan)} parts "
            f"verified, {gb_done:.1f}/{gb_all:.1f} GB of this plan, {gb_all - gb_done:.1f} GB left; "
            f"C: free {c_free_gb():.1f} GB" + (f"; now: {current}" if current else ""))
    with open(PROGRESS, "w", encoding="utf-8") as fh:
        fh.write(line + "\n")


def drive_obj(dest):
    r = subprocess.run([RC, "lsjson", dest, "--hash", "--files-only"], capture_output=True, text=True,
                       creationflags=NW, timeout=300)
    try:
        items = json.loads(r.stdout or "[]")
    except ValueError:
        return None
    return items[0] if items else None


def run_part(part, delete):
    files = [f for f in files_of(part["paths"]) if os.path.exists(f)]
    src_bytes = sum(os.path.getsize(f) for f in files)
    log(f"{part['id']}: {len(files)} files, {src_bytes / 1e9:.2f} GB -> {part['dest']}")
    t0 = time.time()
    p = subprocess.Popen([RC, "rcat", part["dest"], "--drive-chunk-size", "64M", "--retries", "3",
                          "--low-level-retries", "20"], stdin=subprocess.PIPE, creationflags=NW)
    h = Hasher(p.stdin)
    try:
        with tarfile.open(fileobj=h, mode="w|", format=tarfile.PAX_FORMAT) as tf:
            for f in files:
                tf.add(f, arcname=os.path.relpath(f, part["base"]).replace("\\", "/"), recursive=False)
        p.stdin.close()
    except Exception as e:
        p.kill()
        log(f"{part['id']}: STREAM FAILED {e!r}")
        return False
    rc = p.wait()
    secs = time.time() - t0
    if rc != 0:
        log(f"{part['id']}: rclone rcat rc={rc} after {secs:.0f}s - not verified, nothing deleted")
        return False
    md5, sha = h.md5.hexdigest(), h.sha.hexdigest()
    obj = drive_obj(part["dest"])
    hashes = (obj or {}).get("Hashes") or {}
    ok = bool(obj) and obj.get("Size") == h.n and hashes.get("md5") == md5 and \
        (hashes.get("sha256") in (None, sha))
    if not ok:
        log(f"{part['id']}: VERIFY FAILED stream {h.n} {md5} vs drive {obj and obj.get('Size')} {hashes}")
        return False
    manifest = {"id": part["id"], "dest": part["dest"], "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "files": len(files), "src_bytes": src_bytes, "tar_bytes": h.n, "md5": md5, "sha256": sha,
                "drive_id": obj.get("ID"), "base": part["base"], "paths": part["paths"],
                "why": "pre-reinstall backup of winbox, CEO 2026-09-24",
                "restore": f"rclone copyto \"{part['dest']}\" part.tar && tar xf part.tar -C <base>",
                "listing": [[os.path.relpath(f, part["base"]).replace("\\", "/"), os.path.getsize(f)] for f in files]}
    mdest = part["dest"][:-4] + ".manifest.json"
    r = subprocess.run([RC, "rcat", mdest], input=json.dumps(manifest, ensure_ascii=False, indent=1).encode("utf-8"),
                       capture_output=True, creationflags=NW, timeout=600)
    if r.returncode != 0 or not drive_obj(mdest):
        log(f"{part['id']}: manifest upload failed - tar is verified, nothing deleted")
        return False
    row = {k: manifest[k] for k in ("id", "dest", "files", "src_bytes", "tar_bytes", "md5", "sha256", "drive_id")}
    row.update(status="verified", secs=round(secs), mb_s=round(h.n / 1e6 / max(secs, 1), 1), t=time.time())
    write_ledger(row)
    log(f"{part['id']}: VERIFIED {h.n / 1e9:.2f} GB in {secs:.0f}s ({row['mb_s']} MB/s) md5 {md5}")
    if delete:
        freed = 0
        for f in files:
            try:
                freed += os.path.getsize(f)
                os.remove(f)
            except OSError:
                pass
        for pth in part["paths"]:
            if os.path.isdir(pth):
                for root, dirs, fs in sorted(os.walk(pth, topdown=False), key=lambda x: -len(x[0])):
                    try:
                        os.rmdir(root)
                    except OSError:
                        pass
        write_ledger({"id": part["id"], "status": "deleted", "freed_bytes": freed, "t": time.time()})
        log(f"{part['id']}: deleted {len(files)} files, {freed / 1e9:.2f} GB freed; C: free {c_free_gb():.1f} GB")
    return True


def main():
    plan = json.load(open(sys.argv[1], encoding="utf-8"))
    delete = "--delete" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    done = {i for i, r in ledger().items() if r.get("status") in ("verified", "deleted")}
    for part in plan:
        if only and part["id"] != only:
            continue
        if part["id"] in done:
            continue
        progress(plan, done, current=part["id"])
        for attempt in range(3):
            # "keep": back up but never delete -- files the app or the bot still
            # reads while it sits parked (ESC_HOLD, pipe_token, config, templates):
            # removing ESC_HOLD would let the watchdog resume farming mid-backup.
            if run_part(part, delete and not part.get("keep")):
                done.add(part["id"])
                break
            log(f"{part['id']}: attempt {attempt + 1} failed; retrying in 60 s")
            time.sleep(60)
        progress(plan, done)
    log(f"plan finished: {len(done & {p['id'] for p in plan})}/{len(plan)} parts verified")
    open(os.path.join(HERE, "backup_stream.done"), "w").write(time.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
