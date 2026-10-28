#!/usr/bin/env python3
"""Zero-model disk maintenance coordinator. Cleanup belongs to the delegated CLIs."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import storage_policy as policy

STATE = ROOT / 'state/storage'
GB = 1024**3


def live_cwds():
    if platform.system() == 'Linux':
        for link in Path('/proc').glob('[0-9]*/cwd'):
            try:
                yield link.resolve(strict=True)
            except OSError:
                continue
    else:
        try:
            import psutil
        except ImportError:
            return
        for proc in psutil.process_iter():
            try:
                yield Path(proc.cwd())
            except (psutil.Error, OSError):
                continue


def guard_path(path, *, cwds=None, in_use_image=False):
    """Reject secrets, login state, Docker data, and live cwd ancestors.

    PureWindowsPath stays lexical even on Unix. Archive/mooniex-vps is
    conservatively protected in full, including its nine secret-named files.
    """
    windows = isinstance(path, PureWindowsPath) or bool(re.match(r'^[A-Za-z]:[\\/]', str(path)))
    p = PureWindowsPath(path) if windows else Path(path).resolve()
    parts = [part.lower() for part in p.parts]
    text = '/'.join(parts)
    protected = {'cookies', 'login data', 'local storage', 'localstorage', 'indexeddb',
                 'local state', 'session storage', '.credentials.json', 'rclone.conf',
                 'hosts.yml', '.ssh', 'auth.json', 'acme.json'}
    if in_use_image or any(part in protected or any(s in part for s in ('oauth', 'credential', 'token', 'secret', 'winbox-keys'))
                           or part == '.env' or part.endswith(('.pem', '.key', '.env')) for part in parts):
        raise ValueError(f'NEVER: {path}')
    if 'tmp/claude-0' in text or 'docker/volumes' in text or 'docker/image' in text or 'docker/overlay2' in text or 'archive/mooniex-vps' in text:
        raise ValueError(f'NEVER: {path}')
    for cwd in live_cwds() if cwds is None else cwds:
        c = PureWindowsPath(cwd) if windows else Path(cwd).resolve()
        if c == p or p in c.parents:
            raise ValueError(f'live process cwd: {path}')
    return p


def machine(host):
    import yaml
    return yaml.safe_load(policy.MACHINES_PATH.read_text())['machines'][host]


def command(tool, *args):
    return [sys.executable, str(ROOT / 'tools' / tool), *args]


def plan(band, daily=True):
    actions = [dict(name='hub-band', note='Hub has no band ingestion field; record band in steward.jsonl'),
               dict(name='reap', argv=command('gc_stale_tasks.py', '--reap', '--go')),
               dict(name='review-idle', argv=command('gc_stale_tasks.py', '--review-idle', '--go'))]
    if shutil.which('docker'):
        actions.append(dict(name='build-cache', argv=['docker', 'builder', 'prune', '-f']))
    if platform.system() == 'Linux':
        actions.append(dict(name='journal', argv=['journalctl', '--vacuum-size=500M']))
    if daily:
        actions += [dict(name=verb, argv=command('drive_leg.py', verb), daily=True)
                    for verb in ('transcripts', 'runner-state')]
        actions.append(dict(name='orphans', argv=command('workdir.py', 'orphans', '--green'), daily=True))
        actions.append(dict(name='close-orphans', note='tools/workdir.py close <each green orphan> --archive'))
    if band != 'green':
        actions.append(dict(name='unread-caches', note='PLANNED ONLY: no CLI for caches unread 14 days'))
    if band in ('orange', 'red'):
        actions.append(dict(name='rebuild', argv=command('storage_reclaim.py', '--apply', '--steward-guard')))
        actions.append(dict(name='all-caches', note='PLANNED ONLY: no safe all-cache CLI'))
        actions.append(dict(name='largest-lane', note='blocker to C-level of largest measured lane'))
    if band == 'red':
        actions.append(dict(name='cto-red', note='letter to role cto, Main; once a day'))
    return actions


def record(row, dry_run=False):
    line = json.dumps(row, ensure_ascii=False)
    print(line)
    if not dry_run:
        STATE.mkdir(parents=True, exist_ok=True)
        with (STATE / 'steward.jsonl').open('a') as out:
            out.write(line + '\n')


def run_action(action, host, band, dry_run=False):
    before = shutil.disk_usage(Path.cwd()).free
    row = dict(ts=datetime.now(timezone.utc).isoformat(), host=host, band=band,
               **action, status='planned', rc=None, bytes_before=before, bytes_after=before)
    result = None
    try:
        for path in action.get('paths', []):
            guard_path(path)
            if action.get('guard_tree'):
                for base, dirs, files in os.walk(path, followlinks=False):
                    for name in dirs + files:
                        guard_path(Path(base) / name)
        if not dry_run and action.get('argv'):
            result = subprocess.run(action['argv'], cwd=ROOT, capture_output=True, text=True, timeout=1800)
            row.update(status='run', rc=result.returncode)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        row.update(status='refused', rc=1, error=str(exc))
    row['bytes_after'] = shutil.disk_usage(Path.cwd()).free
    record(row, dry_run)
    return result


def lane_usage(host):
    """Attribute existing task Work folders to their project's C-level owner."""
    from lib import db
    from tools.portfolio_watch import _owner_box
    work = Path(machine(host)['hq']) / 'Work'
    totals = {}
    with db.get_conn(readonly=True) as conn:
        if isinstance(conn, db._SnapshotConnection):
            raise RuntimeError('stale task hub')
        rows = conn.execute('SELECT t.id, t.worktree, p.lane, p.owner_session FROM tasks t '
                            'JOIN projects p ON p.id=t.project_id').fetchall()
        for row in rows:
            row = dict(row)
            box = _owner_box(row['lane'], row['owner_session'])
            if not box or row['lane'] not in {'cto', 'cmo', 'coo', 'cfo', 'cgo'}:
                continue
            folder = work / row['id']
            if folder.parent != work or folder.is_symlink():
                continue
            roots = [folder]
            checkout = Path(row['worktree']) if row['worktree'] else None
            if checkout and checkout.parent.name == 'worktrees' and not checkout.is_symlink():
                roots.append(checkout)
            size = 0
            for root in roots:
                for base, dirs, files in os.walk(root, followlinks=False):
                    dirs[:] = [d for d in dirs if not (Path(base) / d).is_symlink()]
                    for name in files:
                        p = Path(base) / name
                        if not p.is_symlink():
                            try:
                                size += p.stat().st_size
                            except OSError:
                                pass
            totals[box] = totals.get(box, 0) + size
    return totals


def cto_main_box():
    """The primary CTO pointer, never an invented session named 'main'."""
    sid = (ROOT / 'state/locks/cto-active').read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,63}', sid):
        raise ValueError('Invalid primary CTO pointer')
    return 'cto-' + sid


def letters(host, band, day, stamps, dry_run):
    from tools import portfolio_watch as watch
    from lib import mailbox
    if stamps.get('lane_day') == day and band in ('green', 'yellow'):
        return  # the Work/checkout walk is costly; once a day unless orange/red
    try:
        totals = lane_usage(host)
    except Exception as exc:
        totals = {}
        record(dict(name='lane-measurement', status='unavailable', error=type(exc).__name__,
                    rc=1, bytes_before=None, bytes_after=None), dry_run)
    pending = []
    for box, size in totals.items():
        prev = stamps.get('lanes', {}).get(box)
        if stamps.get('lane_day') != day and (prev is None or round(prev / GB, 1) != round(size / GB, 1)):
            pending.append((box, f'{host}: disk พื้นที่ Work + checkout ของสาย {size / GB:.2f} GB', 'report', f'lane:{day}:{box}:{size}'))
    if band in ('orange', 'red') and totals:
        box = max(totals, key=totals.get)
        pending.append((box, f'{host}: disk {band}; สายนี้ใช้ Work มากที่สุด', 'blocker', f'orange:{day}:{box}'))
    if band == 'red':
        pending.append((cto_main_box(), f'{host}: disk red ต้องคืนพื้นที่', 'blocker', f'red:{day}'))
    # Reuse delivery's persistence/dedupe machinery with a separate state file.
    old_path = watch.STATE_PATH
    watch.STATE_PATH = STATE / f'letters-{host}.json'
    try:
        state = watch.load_state(datetime.now(timezone.utc))
        for box, body, kind, key in pending:
            episode = state['episodes'].setdefault(key, {'sent': [], 'start': watch._iso(datetime.now(timezone.utc)), 'red': False})
            if 'first' in episode['sent']:
                continue
            letter = dict(box=box, body=body, subject=body[:80], key=key, step='first')
            record(dict(name='letter', box=box, kind=kind, status='planned', rc=None,
                        bytes_before=None, bytes_after=None), dry_run)
            if not dry_run:
                watch.save_state(state)
                def send(role, sid, body, *_args, **kwargs):
                    kwargs['kind'] = kind
                    return mailbox.send(role, sid, body, 'system', 'disk-steward', **kwargs)
                _, errors = watch.deliver([letter], state, send=send)
                record(dict(name='letter', box=box, kind=kind, status='run', rc=1 if errors else 0,
                            bytes_before=None, bytes_after=None), False)
                if errors:
                    raise RuntimeError('; '.join(errors))
        if totals:
            stamps.update(lanes=totals, lane_day=day)
    finally:
        watch.STATE_PATH = old_path


def tick(host=None, dry_run=False, simulate_free=None):
    host = policy.host_key(host)
    if not dry_run and host != policy.host_key():
        raise ValueError('A live tick may only maintain its local host')
    if simulate_free is not None and not dry_run:
        raise ValueError('--simulate-free requires --dry-run')
    free = simulate_free if simulate_free is not None else shutil.disk_usage(Path.cwd()).free / GB
    band = policy.host_band(free, host=host)
    stamp_file = STATE / f'{host}.json'
    stamps = json.loads(stamp_file.read_text()) if stamp_file.exists() else {}
    day = datetime.now(timezone.utc).date().isoformat()
    actions = plan(band)
    failed = False
    cfg = machine(host)
    work = Path(cfg['hq']) / 'Work'
    for action in actions:
        if action['name'] == 'orphans':
            action['argv'] += ['--root', str(work)]
        if action['name'] in ('transcripts', 'runner-state'):
            runners = policy.load(policy.POLICY_PATH)['runners']
            selected = ['claude'] if action['name'] == 'transcripts' else [k for k in runners if k != 'claude']
            action['paths'] = sorted({entry['path'].replace('$HOME', cfg['home']).replace(
                '$CLAUDE_CONFIG_DIR', os.environ.get('CLAUDE_CONFIG_DIR', cfg['claude_config_dir']))
                for k in selected for entry in runners[k]['paths']})
    for action in actions:
        if action.get('daily') and stamps.get(action['name']) == day:
            continue
        result = run_action(action, host, band, dry_run)
        if action.get('argv') and not dry_run and (result is None or result.returncode):
            failed = True
        if result is not None and result.returncode == 0:
            if action['name'] == 'orphans':
                ok = True
                for orphan in json.loads(result.stdout):
                    tid = orphan['task']
                    if not re.fullmatch(r'task-[A-Za-z0-9-]+', tid):
                        continue
                    closed = run_action(dict(name='close', argv=command('workdir.py', 'close', tid, '--archive', '--root', str(work)),
                                             paths=[str(work / tid)], guard_tree=True), host, band)
                    ok = ok and closed is not None and closed.returncode == 0
                if not ok:
                    failed = True
                    continue
            if action.get('daily'):
                stamps[action['name']] = day
    try:
        letters(host, band, day, stamps, dry_run)
    except Exception as exc:
        failed = True
        record(dict(name='letters', status='failed', rc=1, error=type(exc).__name__,
                    bytes_before=None, bytes_after=None), dry_run)
    if not dry_run:
        STATE.mkdir(parents=True, exist_ok=True)
        temp = stamp_file.with_suffix('.tmp')
        temp.write_text(json.dumps(stamps))
        temp.replace(stamp_file)
    return int(failed)


def report():
    print('เครื่อง | ว่าง GB | ระดับ | ข้อมูลล่าสุด')
    for host in policy.load(policy.POLICY_PATH)['hosts']:
        free = None
        observed = 'ไม่มีข้อมูล'
        for directory in (Path('/opt/usage/disk'), Path('/opt/disk-monitor')):
            latest = directory / f'{host}.json'
            history = directory / f'{host}.hist.jsonl'
            try:
                if latest.exists():
                    row = json.loads(latest.read_text())
                    free = row['volumes'][0]['free_bytes'] / GB
                    observed = row.get('observed_at', row.get('received_at', '?'))
                elif history.exists():
                    row = json.loads(history.read_text().splitlines()[-1])
                    free, observed = row['free'] / GB, str(row['t'])
                if free is not None:
                    break
            except (OSError, ValueError, KeyError, IndexError):
                continue
        if free is None and host == policy.host_key():
            free, observed = shutil.disk_usage(Path.cwd()).free / GB, 'เครื่องนี้'
        print(f'{host} | {free:.2f} | {policy.host_band(free, host=host)} | {observed}' if free is not None
              else f'{host} | ? | ? | {observed}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='verb', required=True)
    p = sub.add_parser('tick')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--simulate-free', type=float)
    p.add_argument('--host', choices=list(policy.load(policy.POLICY_PATH)['hosts']))
    sub.add_parser('report')
    args = parser.parse_args(argv)
    if args.verb == 'report':
        report()
        return 0
    return tick(args.host, args.dry_run, args.simulate_free)


if __name__ == '__main__':
    sys.exit(main())
