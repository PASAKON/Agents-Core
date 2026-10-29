"""Implementation of the single P2 card; receipts allow fail-closed --only reruns.

No recursive deletion. Existing steward NEVER rules take precedence over P2
reclamation targets: secret-named files and traefik_data stay on disk.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import drive_leg as drive, disk_steward as steward

VPS = Path('/opt/MoonieXHQ/Archive/mooniex-vps/20260613T193125Z')
MAC = Path('/opt/MoonieXHQ/Archive/mac-delta-20260924')
LINEPOSTER = Path('/opt/MoonieXHQ/Projects/MoonieX/LinePoster')
RECEIPTS = ROOT / 'state/storage/p2'
PATTERNS = ('.env*', '*.key', '*.pem', 'acme.json', '*secret*', '*credential*', '*token*', 'id_*')
LOGIN_NAMES = {'cookies', 'login data', 'local storage', 'localstorage', 'indexeddb',
               'local state', 'session storage', '.ssh', '.git'}
STEPS = {
    'a': 'install', 'b': 'sparse', 'c': 'archive', 'd': 'lineposter',
    'e': 'duplicate', 'f': 'prune', 'g': 'work', 'h': 'final',
}
PLANS = {
    'a': 'bash scripts/install-disk-steward.sh install; systemctl start --wait org-disk-steward.service; journalctl -u org-disk-steward.service -n 30 --no-pager (redacted)',
    'b': 'discover registered spend-guard-deploy + tool-value-deploy; git sparse-checkout set --cone tools lib config scripts runners policies; start --wait spend-guard, tool-value-collect, tool-value-report; disable sparse and stop on failure',
    'c': f'upload {VPS} and {MAC} to BACKUP/MoonieX HQ/Archive/contabo/; exclude traefik_data, secret names, login state and symlinks; verify dated tar + manifest by ID; save receipts; no deletion',
    'd': f'upload {LINEPOSTER} to BACKUP/MoonieX HQ/Projects/contabo/LinePoster/ as dated tar + manifest; exclude secrets; verify by ID; save receipt',
    'e': 'reverify d receipt on Drive; compare every duplicate/live file by md5; remove only backed-up matching files after guard_path; secret-named files and other NEVER-protected paths stay',
    'f': 'reverify c receipts on Drive; guard_path + md5 check each uploaded local file before unlink; preserve secret-named files, traefik_data and unmatched files; line-poster reserved for e',
    'g': 'guard both Work trees; tools/workdir.py close task-67579503 --archive; tools/workdir.py close task-18e3ab26 --archive; no task-row edits',
    'h': 'tools/disk_steward.py report; df -h /',
}


def excluded(path):
    return (any(part.lower() in LOGIN_NAMES | {'traefik_data'} or any(fnmatch.fnmatchcase(part.lower(), p)
                for p in PATTERNS) for part in path.parts) or drive._runner_secret(path))


def inventory(root, *, filter_secrets=True):
    """Fail on unreadable sources, never traverse symlinks, retain excluded names only."""
    if not root.is_dir() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('missing or symlink source')
    files, skipped = [], []
    def fail(error):
        raise error
    for parent, dirs, names in os.walk(root, followlinks=False, onerror=fail):
        for name in list(dirs):
            p = Path(parent) / name
            if p.is_symlink() or (filter_secrets and excluded(p.relative_to(root))):
                dirs.remove(name)
                skipped.append(str(p.relative_to(root)))
        for name in sorted(names):
            p = Path(parent) / name
            if not stat.S_ISREG(p.lstat().st_mode) or (filter_secrets and excluded(p.relative_to(root))):
                skipped.append(str(p.relative_to(root)))
            else:
                files.append(p)
    return sorted(files), sorted(skipped)


def digest(path):
    with drive._open_runner_source(path) as src:
        return hashlib.file_digest(src, 'md5').hexdigest()


def verify_receipt(receipt, *, rclone=None):
    """Re-read metadata and select by immutable ID, never a name-only match."""
    if receipt.get('verified') is not True:
        raise ValueError('unverified receipt')
    rows = drive._lsjson(rclone or drive.rclone_path(), drive.FOLDER_IDS['family'], receipt['remote_dir'])
    uploaded = {k: v for k, v in receipt.items() if k not in (
        'verified', 'tar_name', 'manifest_name', 'remote_dir', 'manifest_id')}
    data = (json.dumps(uploaded, indent=2, ensure_ascii=False) + '\n').encode()
    for fid, size, md5 in ((receipt['drive']['id'], receipt['bytes'], receipt['md5']),
                            (receipt['manifest_id'], len(data), hashlib.md5(data).hexdigest())):
        matches = [r for r in rows if fid and r.get('ID') == fid]
        if len(matches) != 1 or matches[0].get('Size') != size or matches[0].get('Hashes', {}).get('md5') != md5:
            raise ValueError('Drive ID/size/md5 verification failed')


def backup(root, destination, *, config_dir, rclone=None):
    files, skipped = inventory(root)
    if not files:
        raise ValueError('empty backup selection')
    print(f'Backup selection: {len(files)} regular files; excluded names: ' + json.dumps(skipped))
    name = root.name + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex
    # Snapshot once; quota retries replay precisely these bytes. Hash tar members,
    # not a second read of sources which may have changed while archiving.
    with tempfile.TemporaryFile() as snapshot:
        members = []
        with tarfile.open(fileobj=snapshot, mode='w') as tf:
            for path in files:
                with drive._open_runner_source(path) as src:
                    before = os.fstat(src.fileno())
                    info = tarfile.TarInfo(path.relative_to(root).as_posix())
                    info.size, info.mode, info.mtime = before.st_size, before.st_mode & 0o777, before.st_mtime
                    md5 = hashlib.md5()
                    class Reader:
                        def read(self, n):
                            data = src.read(n)
                            md5.update(data)
                            return data
                    tf.addfile(info, Reader())
                    after = os.fstat(src.fileno())
                    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                        raise ValueError('source changed during snapshot')
                    members.append(dict(path=info.name, size=info.size, md5=md5.hexdigest()))
        manifest = drive.build_manifest(name=name, machine='contabo', source=str(root), files=members,
            excluded=skipped, restore=f'Extract tar into {root}; excluded secrets remain local')
        def stream(sink):
            snapshot.seek(0)
            shutil.copyfileobj(snapshot, sink)
        result = drive.put(stream, drive.FOLDER_IDS['family'], destination, name, '.tar', manifest,
                           log_path_=drive.log_path(config_dir), who='disksteward-p2', rclone=rclone)
    verify_receipt(result, rclone=rclone)
    return result


def save(key, receipt):
    RECEIPTS.mkdir(parents=True, exist_ok=True, mode=0o700)
    if RECEIPTS.is_symlink() or RECEIPTS.stat().st_uid != os.geteuid() or RECEIPTS.stat().st_mode & 0o022:
        raise ValueError('untrusted receipt directory')
    tmp = RECEIPTS / (key + '.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(receipt, out)
    tmp.replace(RECEIPTS / (key + '.json'))


def load(key, root):
    with drive._open_runner_source(RECEIPTS / (key + '.json')) as src:
        receipt = json.load(src)
    if receipt['source'] != str(root):
        raise ValueError('receipt source mismatch')
    verify_receipt(receipt)
    return receipt


def remove_member(root, member):
    rel = Path(member['path'])
    if rel.is_absolute() or '..' in rel.parts or excluded(rel):
        raise ValueError('unsafe receipt member')
    path = root / rel
    if not path.exists():
        return
    try:
        steward.guard_path(path)
    except ValueError:
        print(f'SKIP protected path: {path}')
        return
    # Use an open parent fd, O_NOFOLLOW source, and inode/time checks immediately
    # before unlink. A renamed/symlink-substituted parent cannot redirect unlink.
    with drive._open_runner_source(path) as src:
        before = os.fstat(src.fileno())
        if before.st_size != member['size'] or hashlib.file_digest(src, 'md5').hexdigest() != member['md5']:
            print(f'SKIP changed file: {path}')
            return
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            after = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if fields(before) != fields(after):
                raise ValueError('source changed before unlink')
            steward.guard_path(path)
            os.unlink(path.name, dir_fd=fd)
        finally:
            os.close(fd)


def run(argv):
    # Child diagnostics can contain credentials; print command and exit status only.
    result = subprocess.run([str(x) for x in argv], cwd=ROOT, capture_output=True, text=True)
    print(f'{shlex.join(map(str, argv))}: rc={result.returncode}')
    if result.returncode:
        raise RuntimeError('command failed; child output suppressed to protect secrets')
    return result.stdout


# RUN-20261029-0435-3cf6: tool-value-report exited 2 ("already sent") and stopped the card.
NO_START = {'tool-value-report.service'}


def sparse():
    registered = {line[9:] for line in run(['git', 'worktree', 'list', '--porcelain']).splitlines() if line.startswith('worktree ')}
    for name in ('spend-guard-deploy', 'tool-value-deploy'):
        wt = ROOT / 'worktrees' / name
        if str(wt) not in registered or run(['git', '-C', wt, 'status', '--porcelain']).strip():
            raise ValueError('deploy checkout missing or dirty')
        services = []
        for unit in sorted((ROOT / 'deploy/systemd').glob('*.service')):
            if any(line.startswith('ExecStart=') and str(wt) + '/' in line for line in unit.read_text().splitlines()):
                services.append(unit.name)
        if not services:
            raise ValueError('no services reference deploy worktree')
        # apply-sparse is a role-based --no-checkout launcher API. These existing
        # service checkouts need an explicit service dependency cone instead.
        try:
            run(['git', '-C', wt, 'sparse-checkout', 'set', '--cone', 'tools', 'lib', 'config', 'scripts', 'runners', 'policies'])
            for unit in services:
                if unit in NO_START:
                    # A sender refuses an off-schedule rerun (exit 2) and must never mail twice;
                    # its sibling unit runs the same module, so that start proves the cone.
                    print(f'{unit}: not started (sends messages)')
                    continue
                run(['systemctl', 'start', '--wait', unit])
                print(run(['systemctl', 'show', unit, '--property=Result', '--property=ExecMainStatus']).strip())
        except Exception:
            run(['git', '-C', wt, 'sparse-checkout', 'disable'])
            raise


def execute(step):
    if step == 'a':
        print(run(['bash', 'scripts/install-disk-steward.sh', 'install']))
        try:
            run(['systemctl', 'start', '--wait', 'org-disk-steward.service'])
        finally:
            # Arbitrary child log messages may contain secrets. Preserve 30 journal
            # timestamps/units, redact MESSAGE entirely instead of guessing values.
            tail = run(['journalctl', '-u', 'org-disk-steward.service', '-n', '30', '--no-pager', '-o', 'json'])
            for line in tail.splitlines():
                row = json.loads(line)
                print(f"{row.get('__REALTIME_TIMESTAMP', '')} org-disk-steward.service [message redacted]")
    elif step == 'b':
        sparse()
    elif step == 'c':
        for key, root in (('vps', VPS), ('mac', MAC)):
            save(key, backup(root, 'Archive/contabo', config_dir=drive.config_dir()))
    elif step == 'd':
        save('lineposter', drive.lineposter(config_dir=drive.config_dir()))
    elif step == 'e':
        try:
            receipt = load('lineposter', LINEPOSTER)
        except (OSError, ValueError, drive.DriveLegError):
            print('SKIP duplicate: no current verified LinePoster receipt')
            return
        duplicate = VPS / 'line-poster'
        old, old_skips = inventory(duplicate, filter_secrets=False)
        live, live_skips = inventory(LINEPOSTER, filter_secrets=False)
        old_map = {p.relative_to(duplicate).as_posix(): digest(p) for p in old}
        live_map = {p.relative_to(LINEPOSTER).as_posix(): digest(p) for p in live}
        if old_skips or live_skips or old_map != live_map:
            print('SKIP duplicate: trees differ or contain nonregular files')
            return
        for member in receipt['files']:
            if live_map.get(member['path']) != member['md5']:
                print('SKIP duplicate: live tree changed since verified backup')
                return
        for member in receipt['files']:
            remove_member(duplicate, member)
    elif step == 'f':
        for key, root in (('vps', VPS), ('mac', MAC)):
            receipt = load(key, root)
            for member in receipt['files']:
                if root == VPS and Path(member['path']).parts[0] == 'line-poster':
                    continue  # Never bypass e's live-tree/LinePoster receipt gate.
                remove_member(root, member)
    elif step == 'g':
        for task in ('task-67579503', 'task-18e3ab26'):
            folder = Path('/opt/MoonieXHQ/Work') / task
            steward.guard_path(folder)
            for base, dirs, files in os.walk(folder):
                for name in dirs + files:
                    steward.guard_path(Path(base) / name)
            run([sys.executable, 'tools/workdir.py', 'close', task, '--archive'])
    elif step == 'h':
        print(run([sys.executable, 'tools/disk_steward.py', 'report']))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--only', choices=[*STEPS, *STEPS.values()])
    args = ap.parse_args(argv)
    if not args.dry_run and (os.geteuid() != 0 or 'worktrees' in ROOT.parts):
        ap.error('live card requires root in the main checkout')
    selected = [k for k, name in STEPS.items() if not args.only or args.only in (k, name)]
    print('=== before ===', flush=True)
    if args.dry_run:
        print('would run: df -h /')
    else:
        print(run(['df', '-h', '/']))
    try:
        for step in selected:
            print(f'=== {step}. {STEPS[step]} ===', flush=True)
            if args.dry_run:
                print('would: ' + PLANS[step])
            else:
                execute(step)
    except Exception as exc:
        print(f'P2 stopped: {type(exc).__name__}; no further steps (details suppressed to protect secrets)', file=sys.stderr)
        return 1
    finally:
        print('=== after ===')
        if args.dry_run:
            print('would run: df -h /')
        else:
            print(run(['df', '-h', '/']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
