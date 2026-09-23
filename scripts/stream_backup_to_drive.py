#!/usr/bin/env python3
"""stream_backup_to_drive.py -- stream a frozen file list to Drive as one verified tar, then free the disk.

Built 2026-09-24 for winbox's pre-reinstall backup (CEO: "สำรองก่อน ... ระหว่างสำรอง ทยอยลบข้อมูลที่
สำรองแล้วด้วย"; Drive folder BACKUP/Winbox Reinstall 2026-09-24 approved "อณุมัติ"). Same shape as
windows/cookierun_backup_stream.py (the Cookie Run plan runner), generalised: any paths, exclude globs,
a Drive folder id instead of a path, and a delete step that only removes files that did not change
after the list was frozen.

Per run, in this order -- nothing is deleted unless every step passed:
  1. walk the paths once and FREEZE the list (path, size, mtime_ns). Reparse points (junctions,
     symlinks) are never followed and never deleted: a followed junction deletes its target.
  2. tar (mode "w|", PAX) straight into `rclone rcat <remote><name>.tar --drive-root-folder-id <id>`,
     md5 + sha256 + byte count taken from the bytes rclone was fed. No local copy.
  3. read the object back (`rclone lsjson --hash`): size AND md5 must equal the stream's.
  4. upload <name>.manifest.json beside it (every file with size + mtime, hashes, restore line) and
     read that back too.
  5. only with --delete-after-verify: remove each frozen file whose size + mtime are still the frozen
     ones, then prune the directories left empty (never --base itself, never outside it).

Runs on winbox with its own Python 3.11 (stdlib only), copied to %TEMP%. Launch it with pythonw so it
owns no window:
    pythonw stream_backup_to_drive.py --name downloads-other --root-id <folderId> \
        --base C:\\Users\\UsEr\\Downloads --path C:\\Users\\UsEr\\Downloads \
        --exclude *.exe --exclude *.msi [--paths-file list.txt] [--extra DIR] \
        [--delete-after-verify] [--dry-run]
Everything it says goes to <workdir>/<name>.log; <workdir>/<name>.progress.txt is rewritten every few
seconds; <workdir>/<name>.result.json is the machine-readable outcome.

Never pipe the tar through PowerShell (it re-encodes binary) -- this script feeds rclone directly.
"""
import argparse
import fnmatch
import hashlib
import json
import os
import socket
import stat
import subprocess
import sys
import tarfile
import time

WIN = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
FLAGS = (CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS) if WIN else 0
REPARSE = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT
RCLONE_PATH_FILE = r"C:\Users\UsEr\cookierun-bot\tools\rclone_path.txt"

LOG = None


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    if LOG:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    if sys.stdout:  # None under pythonw; a cp1252 console cannot print Thai names
        enc = sys.stdout.encoding or "utf-8"
        print(line.encode(enc, "backslashreplace").decode(enc), flush=True)


def lower_own_priority():
    if WIN:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS)


def is_reparse(st):
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & REPARSE)


def under(path, base):
    path, base = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(base))
    return path == base or path.startswith(base.rstrip("\\/") + os.sep)


def freeze(paths, excludes):
    """Walk once. Returns (files [(path, size, mtime_ns)], dirs [path], skipped [[path, why]])."""
    globs = [g.lower() for g in excludes]

    def excluded(name):
        return any(fnmatch.fnmatch(name.lower(), g) for g in globs)

    files, dirs, skipped, stack = [], [], [], []
    for p in paths:
        try:
            st = os.lstat(p)
        except OSError as e:
            skipped.append([p, f"lstat: {e}"])
            continue
        if is_reparse(st):
            skipped.append([p, "reparse point, not followed"])
        elif stat.S_ISDIR(st.st_mode):
            stack.append(p)
        elif not excluded(os.path.basename(p)):
            files.append((p, st.st_size, st.st_mtime_ns))
    while stack:
        d = stack.pop()
        dirs.append(d)
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name)
        except OSError as e:
            skipped.append([d, f"scandir: {e}"])
            continue
        for e in entries:
            if excluded(e.name):
                continue
            try:
                st = e.stat(follow_symlinks=False)
            except OSError as err:
                skipped.append([e.path, f"stat: {err}"])
                continue
            if is_reparse(st):
                skipped.append([e.path, "reparse point, not followed"])
            elif stat.S_ISDIR(st.st_mode):
                stack.append(e.path)
            else:
                files.append((e.path, st.st_size, st.st_mtime_ns))
    files.sort()
    return files, dirs, skipped


class Sink:
    """File-like: forwards to rclone's stdin, hashing and counting what it forwards."""

    def __init__(self, pipe):
        self.pipe, self.n = pipe, 0
        self.md5, self.sha = hashlib.md5(), hashlib.sha256()

    def write(self, b):
        self.pipe.write(b)
        self.md5.update(b)
        self.sha.update(b)
        self.n += len(b)
        return len(b)

    def flush(self):
        self.pipe.flush()


class Exact:
    """Reads exactly `size` bytes: stops early if the file grew, pads with NULs if it shrank."""

    def __init__(self, fh, size):
        self.fh, self.left, self.short = fh, size, False

    def read(self, n=-1):
        if self.left <= 0:
            return b""
        n = self.left if n is None or n < 0 or n > self.left else n
        b = self.fh.read(n)
        if len(b) < n:
            self.short = True
            b += b"\0" * (n - len(b))
        self.left -= n
        return b


class Progress:
    def __init__(self, path, total_files, total_bytes):
        self.path, self.tf, self.tb, self.t0, self.last = path, total_files, total_bytes, time.time(), 0

    def tick(self, nfiles, nbytes, force=False):
        now = time.time()
        if not force and now - self.last < 5:
            return
        self.last = now
        rate = nbytes / 1e6 / max(now - self.t0, 1)
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {nfiles}/{self.tf} files, "
                     f"{nbytes / 1e9:.2f}/{self.tb / 1e9:.2f} GB, {rate:.1f} MB/s\n")


class Drive:
    def __init__(self, rclone, remote, root_id):
        self.rc, self.remote, self.root = rclone, remote, root_id

    def _args(self, name):
        return [f"{self.remote}{name}", "--drive-root-folder-id", self.root]

    def stat(self, name):
        """Every object called `name` in the folder (Drive allows duplicates), with md5 + ID."""
        r = subprocess.run([self.rc, "lsjson", "--hash", "--files-only", "--no-mimetype",
                            "--drive-root-folder-id", self.root, self.remote,
                            "--include", "/" + name.replace("[", "\\[")],
                           capture_output=True, text=True, creationflags=FLAGS, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f"lsjson rc={r.returncode}: {r.stderr.strip()[-400:]}")
        return json.loads(r.stdout or "[]")

    def rcat(self, name, stderr=None, data=None):
        cmd = [self.rc, "rcat", *self._args(name), "--drive-chunk-size", "64M",
               "--low-level-retries", "20", "--stats", "0"]
        if data is not None:
            return subprocess.run(cmd, input=data, capture_output=True, creationflags=FLAGS, timeout=1800)
        return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=stderr, creationflags=FLAGS)


def stream(files, extras, base, drive, name, prog):
    """Tar every frozen file (+ extras, arcname _extra/...) into rclone. Returns (sink, bad, changed)."""
    errf = open(os.path.join(os.path.dirname(prog.path), f"{name}.rclone.err"), "wb")
    p = drive.rcat(f"{name}.tar", stderr=errf)
    sink = Sink(p.stdin)
    bad, changed, nfiles = {}, set(), 0
    try:
        with tarfile.open(fileobj=sink, mode="w|", format=tarfile.PAX_FORMAT) as tf:
            members = [(f, os.path.relpath(f, base).replace("\\", "/"), size, mt) for f, size, mt in files]
            for xdir, xfiles in extras:
                top = "_extra/" + os.path.basename(xdir.rstrip("\\/"))
                members += [(f, top + "/" + os.path.relpath(f, xdir).replace("\\", "/"), size, mt)
                            for f, size, mt in xfiles]
            for path, arc, size, mt in members:
                try:
                    fh = open(path, "rb")
                except OSError as e:
                    bad[path] = f"open: {e}"
                    continue
                with fh:
                    ti = tarfile.TarInfo(arc)
                    ti.size, ti.mtime, ti.mode = size, mt / 1e9, 0o644
                    src = Exact(fh, size)
                    tf.addfile(ti, src)
                    st = os.fstat(fh.fileno())
                    if src.short or st.st_size != size or st.st_mtime_ns != mt:
                        changed.add(path)
                nfiles += 1
                prog.tick(nfiles, sink.n)
        p.stdin.close()
    except (OSError, ValueError) as e:
        p.kill()
        p.wait()
        errf.close()
        raise RuntimeError(f"stream broke after {sink.n} bytes: {e!r}")
    rc = p.wait()
    errf.close()
    prog.tick(nfiles, sink.n, force=True)
    if rc != 0:
        raise RuntimeError(f"rclone rcat rc={rc} (see {name}.rclone.err)")
    return sink, bad, changed


def delete_frozen(files, dirs, base, keep):
    """Remove frozen files still at their frozen size + mtime; prune dirs left empty under base."""
    removed, freed, kept = 0, 0, 0
    for path, size, mt in files:
        if path in keep:
            kept += 1
            continue
        try:
            st = os.lstat(path)
        except FileNotFoundError:
            continue
        if is_reparse(st) or st.st_size != size or st.st_mtime_ns != mt:
            kept += 1
            continue
        try:
            os.remove(path)
        except PermissionError:
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)
        removed += 1
        freed += size
    pruned = 0
    for d in sorted(dirs, key=lambda x: -len(x)):
        if not under(d, base) or os.path.normcase(os.path.abspath(d)) == os.path.normcase(os.path.abspath(base)):
            continue
        try:
            os.rmdir(d)
            pruned += 1
        except OSError:
            pass
    return removed, freed, kept, pruned


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--name", required=True, help="object name on Drive, without .tar")
    ap.add_argument("--root-id", required=True, help="Drive folder id the tar lands in")
    ap.add_argument("--base", required=True, help="arcnames are relative to this; nothing outside it")
    ap.add_argument("--path", action="append", default=[], help="file or dir to back up (repeatable)")
    ap.add_argument("--paths-file", help="UTF-8 text file, one path per line")
    ap.add_argument("--exclude", action="append", default=[], help="glob on file/dir names (repeatable)")
    ap.add_argument("--extra", action="append", default=[],
                    help="dir tarred whole under _extra/<basename>/ (bundles, patches); never deleted")
    ap.add_argument("--remote", default="gdrive:")
    ap.add_argument("--rclone", default=None)
    ap.add_argument("--workdir", default=os.path.join(os.environ.get("TEMP", "/tmp"), "stream_backup"))
    ap.add_argument("--delete-after-verify", action="store_true")
    ap.add_argument("--overwrite", action="store_true", help="replace an existing <name>.tar on Drive")
    ap.add_argument("--dry-run", action="store_true", help="freeze and report; upload nothing")
    ap.add_argument("--why", default="winbox pre-reinstall backup, CEO 2026-09-24")
    a = ap.parse_args()

    global LOG
    os.makedirs(a.workdir, exist_ok=True)
    LOG = os.path.join(a.workdir, f"{a.name}.log")
    result_path = os.path.join(a.workdir, f"{a.name}.result.json")
    lower_own_priority()
    rclone = a.rclone or (open(RCLONE_PATH_FILE).read().strip() if os.path.exists(RCLONE_PATH_FILE) else "rclone")
    t0 = time.time()
    res = {"name": a.name, "root_id": a.root_id, "status": "failed", "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    def finish(**kw):
        res.update(kw, secs=round(time.time() - t0))
        with open(result_path, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
        log("RESULT " + json.dumps({k: v for k, v in res.items() if k not in ("skipped", "changed")},
                                   ensure_ascii=False))
        return 0 if res["status"] in ("verified", "deleted", "dry-run") else 1

    paths = [os.path.abspath(p) for p in a.path]
    if a.paths_file:
        with open(a.paths_file, encoding="utf-8-sig") as fh:
            paths += [os.path.abspath(ln.strip()) for ln in fh if ln.strip()]
    outside = [p for p in paths if not under(p, a.base)]
    if not paths or outside:
        return finish(error=f"no paths, or paths outside --base: {outside[:5]}")

    lock = os.path.join(a.workdir, f"{a.name}.lock")
    try:
        os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        return finish(error=f"{lock} exists -- another run of this name is live, or crashed (remove it)")
    try:
        files, dirs, skipped = freeze(paths, a.exclude)
        extras = []
        for x in a.extra:
            xf, _, xs = freeze([os.path.abspath(x)], [])
            extras.append((os.path.abspath(x), xf))
            skipped += xs
        src_bytes = sum(s for _, s, _ in files) + sum(s for _, xf in extras for _, s, _ in xf)
        nfiles = len(files) + sum(len(xf) for _, xf in extras)
        log(f"{a.name}: froze {nfiles} files, {src_bytes / 1e9:.3f} GB, {len(skipped)} skipped, "
            f"from {len(paths)} paths under {a.base}")
        if a.dry_run:
            tops = {}
            for f, s, _ in files:
                top = os.path.relpath(f, a.base).replace("\\", "/").split("/")[0]
                n, b = tops.get(top, (0, 0))
                tops[top] = (n + 1, b + s)
            return finish(status="dry-run", files=nfiles, src_bytes=src_bytes,
                          top=sorted(([k, n, b] for k, (n, b) in tops.items()), key=lambda r: -r[2])[:40],
                          skipped=skipped)
        if not nfiles:
            return finish(error="nothing to back up after excludes")

        drive = Drive(rclone, a.remote, a.root_id)
        tar_name, man_name = f"{a.name}.tar", f"{a.name}.manifest.json"
        if drive.stat(tar_name) and not a.overwrite:
            return finish(error=f"{tar_name} already exists in the folder -- pass --overwrite to replace it")
        prog = Progress(os.path.join(a.workdir, f"{a.name}.progress.txt"), nfiles, src_bytes)
        sink, bad, changed = stream(files, extras, a.base, drive, a.name, prog)
        md5, sha = sink.md5.hexdigest(), sink.sha.hexdigest()
        objs = drive.stat(tar_name)
        if len(objs) != 1 or objs[0].get("Size") != sink.n or (objs[0].get("Hashes") or {}).get("md5") != md5:
            return finish(error="VERIFY FAILED", stream_bytes=sink.n, md5=md5,
                          drive=[[o.get("ID"), o.get("Size"), (o.get("Hashes") or {}).get("md5")] for o in objs])
        drive_id = objs[0].get("ID")
        log(f"{a.name}: VERIFIED {sink.n / 1e9:.3f} GB md5 {md5} id {drive_id}")

        skipped += [[p, why] for p, why in bad.items()]
        manifest = {
            "name": a.name, "tar": tar_name, "drive_folder_id": a.root_id, "drive_id": drive_id,
            "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": socket.gethostname(), "why": a.why,
            "base": a.base, "paths": paths, "excludes": a.exclude, "extras": [x for x, _ in extras],
            "files": nfiles - len(bad), "src_bytes": src_bytes, "tar_bytes": sink.n, "md5": md5, "sha256": sha,
            "restore": (f'rclone copyto "{a.remote}{tar_name}" {tar_name} --drive-root-folder-id {a.root_id}'
                        f' && tar xf {tar_name} -C "{a.base}"   (_extra/ holds bundles/patches, not paths)'),
            "skipped": skipped, "changed_during_stream": sorted(changed),
            "listing": [[os.path.relpath(f, a.base).replace("\\", "/"), s,
                         time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(m / 1e9))]
                        for f, s, m in files if f not in bad],
        }
        mbytes = json.dumps(manifest, ensure_ascii=False, indent=1).encode("utf-8")
        r = drive.rcat(man_name, data=mbytes)
        mobjs = drive.stat(man_name)
        if r.returncode != 0 or len(mobjs) != 1 or \
                (mobjs[0].get("Hashes") or {}).get("md5") != hashlib.md5(mbytes).hexdigest():
            return finish(error="manifest upload/verify failed -- tar is verified, nothing deleted",
                          drive_id=drive_id, md5=md5, tar_bytes=sink.n)
        out = dict(status="verified", files=nfiles - len(bad), src_bytes=src_bytes, tar_bytes=sink.n,
                   md5=md5, sha256=sha, drive_id=drive_id, manifest_id=mobjs[0].get("ID"),
                   skipped=skipped, changed=sorted(changed))
        if a.delete_after_verify:
            keep = set(bad) | changed
            removed, freed, kept, pruned = delete_frozen(files, dirs, a.base, keep)
            log(f"{a.name}: deleted {removed} files ({freed / 1e9:.3f} GB), kept {kept} changed/unreadable, "
                f"pruned {pruned} empty dirs")
            out.update(status="deleted", deleted=removed, freed_bytes=freed, kept=kept, pruned_dirs=pruned)
        return finish(**out)
    except Exception as e:  # the result file must always say what happened
        return finish(error=repr(e))
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
