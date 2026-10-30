#!/usr/bin/env python3
"""Contabo Run Inbox bridge. Sheet must contain one exact Flow project URL."""
import argparse
import base64
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
LIVE_LEDGER = Path('/opt/MoonieXHQ/Agents/Core/docs/ops/credit-ledger.jsonl')
PYTHON = r'C:\mooniex\pwvenv\Scripts\python.exe'
REMOTE = r'C:\mooniex\flowcard'


def pattern(regex):
    def validate(value):
        if not re.fullmatch(regex, value):
            raise argparse.ArgumentTypeError('invalid value: ' + repr(value))
        return value
    return validate


def cap(value):
    pattern(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?')(value)
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError('cap must be finite and >= 0')
    return number


def parse(argv):
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument('--max-credits', required=True, type=cap)
    for name in ('sheet', 'ledger', 'dest'):
        p.add_argument('--' + name, required=True, type=pattern(r'/(?:[\w.-]+/)*[\w.-]+'))
    p.add_argument('--only', type=pattern(r'\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*'))
    p.add_argument('--resolution', choices=('720p', '360p'), default='720p')
    p.add_argument('--aspect', choices=('9:16', '16:9'), default='9:16')
    p.add_argument('--dry-run', action='store_true')
    for name in ('channel', 'purpose', 'task'):
        p.add_argument('--' + name, required=True, type=pattern(r'[\w .,:()/\-]{1,300}'))
    p.add_argument('--kind', choices=('test', 'production', 'reshoot', 'setup', 'other'), default='production')
    p.add_argument('--who', type=pattern(r'[\w.-]{1,100}'),
                   default=os.environ.get('CXO_ROLE', '') + '-' + os.environ.get('CXO_SESSION_ID', ''))
    a = p.parse_args(argv)
    if sum(v == '--max-credits' or v.startswith('--max-credits=') for v in argv) != 1:
        p.error('--max-credits must occur exactly once')
    if a.who == '-':
        p.error('--who or CXO_ROLE and CXO_SESSION_ID required')
    for name in ('sheet', 'ledger', 'dest'):
        if '..' in Path(getattr(a, name)).parts:
            p.error('parent traversal forbidden')
    return a


def digest(data):
    return hashlib.sha256(data).hexdigest()


def plain(path, flags=os.O_RDONLY):
    """A plain file, never through a symlink or a second hard link: the card runs as root
    and state/ is group-writable, so a planted link must not redirect a root read or write."""
    fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        os.close(fd)
        raise OSError(f'not a plain file: {path}')
    return os.fdopen(fd, 'rb' if flags == os.O_RDONLY else 'r+b')


def read_plain(path):
    with plain(path) as f:
        return f.read()


def write_plain(path, data):
    # Truncate only after the checks: O_TRUNC would empty a linked file before fstat runs.
    with plain(path, os.O_RDWR) as f:
        f.truncate(0)
        f.write(data)


def bundle():
    names = ['tools/' + n + '.py' for n in (
        'flow_shoot', 'flow_cdp', 'flow_ledger', 'clip_review', 'decide',
        'storage_policy', 'flow_shoot_card_remote')]
    names += ['lib/config.py', 'lib/decision_ledger.py', 'lib/session_names.py']
    names += [n for n in ('tools/__init__.py', 'lib/__init__.py') if (ROOT / n).exists()]
    names += [str(p.relative_to(ROOT)) for p in (ROOT / 'config').rglob('*.yaml')]
    return {n: (ROOT / n).read_bytes() for n in sorted(names)}


def inner_argv(a, folder):
    result = [PYTHON, '-u', folder + r'\tools\flow_shoot.py',
              'run', '--max-credits', str(a.max_credits),
              '--sheet', folder + r'\sheet.md', '--ledger', folder + r'\ledger.tsv',
              '--dest', folder + r'\out', '--resolution', a.resolution,
              '--aspect', a.aspect]
    if a.only:
        result += ['--only', a.only]
    if a.dry_run:
        result += ['--dry-run']
    return result


class Runner:
    """JSON RPC over one SSH connection; remote owns an OS lock until EOF."""
    def __init__(self):
        source = (ROOT / 'tools/flow_shoot_card_remote.py').read_bytes()
        code = "import base64,sys;exec(base64.b64decode(sys.stdin.readline()))"
        self.proc = subprocess.Popen(['ssh', 'winbox', f'{PYTHON} -u -c "{code}"'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.proc.stdin.write(base64.b64encode(source).decode() + '\n')
        self.proc.stdin.flush()

    def call(self, verb, **args):
        self.proc.stdin.write(json.dumps(dict(verb=verb, **args)) + '\n')
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError('remote connection lost')
            reply = json.loads(line)
            if 'output' in reply:
                print(reply['output'], flush=True)
                continue
            if 'error' in reply:
                raise RuntimeError(reply['error'])
            return reply['result']

    def kill(self, folder):
        script = (f"$file = '{folder}\\pid'\n"
                  "$end = (Get-Date).AddSeconds(20)\n"
                  "while (!(Test-Path $file) -and (Get-Date) -lt $end) { Start-Sleep -Milliseconds 100 }\n"
                  "$p = Get-Content $file -ErrorAction Stop\n& taskkill /PID $p /T /F\n\n")
        try:
            result = subprocess.run(['ssh', 'winbox', 'powershell -NoProfile -NonInteractive -Command -'],
                                    input=script, text=True, timeout=30, check=False)
            print(f'taskkill return code: {result.returncode}', flush=True)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f'taskkill failed: {exc}', flush=True)

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=30)


def main(argv=None, runner=None, live_path=LIVE_LEDGER):
    a = parse(argv)
    # Do not create a substitute ledger in the temporary checkout.
    with Path(live_path).open('r+'):
        pass
    try:
        sheet = read_plain(a.sheet)
        original = read_plain(a.ledger)
    except OSError as exc:
        print(f'refused: {exc}')
        return 4
    projects = set(re.findall(r'https://flow\.google\.com/(?:[^\s<>"`()]*/)?project/[a-zA-Z0-9-]+', sheet.decode()))
    if len(projects) != 1:
        print('sheet must identify exactly one Flow project URL')
        return 4
    project = projects.pop()
    r = runner or Runner()
    folder = None
    old_handlers = {}
    interrupted = [0]
    def stop(signum, frame):
        interrupted[0] = 128 + signum
        if folder:
            r.kill(folder)
    try:
        if not r.call('lock'):
            print('busy: another Flow card or a flow_shoot run is using winbox 9226')
            return 5
        try:
            before = r.call('balance', project=project, source=(ROOT / 'tools/flow_balance_ws.py').read_text())
            if before is None:
                return 4
        except RuntimeError:
            return 4
        if a.max_credits > before:
            print('over balance')
            return 3
        files = bundle()
        identity = digest(b''.join(n.encode() + b'\0' + bytes.fromhex(digest(b)) for n, b in files.items()))[:12]
        folder = REMOTE + '\\' + identity + '\\' + uuid.uuid4().hex
        for name, data in files.items():
            actual = r.call('put', folder=folder, name=name, data=base64.b64encode(data).decode())
            if actual != digest(data):
                return 2
        for name, data in [('sheet.md', sheet), ('ledger.tsv', original), ('project.txt', project.encode())]:
            if r.call('put', folder=folder, name=name, data=base64.b64encode(data).decode()) != digest(data):
                return 2
        for sig in (signal.SIGTERM, signal.SIGINT):
            old_handlers[sig] = signal.signal(sig, stop)
        code = r.call('run', folder=folder, argv=inner_argv(a, folder))
        pulled = r.call('list', folder=folder)
        ledger = original
        # Compare-and-swap the run's ledger; preserve concurrent edits.
        pull_error = None
        try:
            changed = digest(read_plain(a.ledger)) != digest(original)
        except OSError:
            changed = True
        if changed:
            pull_error = 'local shot ledger changed during run; remote copy retained'
        dest_ok = None
        received_clips = {}
        for entry in pulled:
            name = entry['name']
            if name != 'ledger.tsv' and not re.fullmatch(r'out/[\w.-]+', name):
                raise RuntimeError('unsafe output filename')
            if Path(name).name in ('.', '..'):
                raise RuntimeError('unsafe output filename')
            data = base64.b64decode(r.call('get', folder=folder, name=name))
            valid = len(data) == entry['size'] and digest(data) == entry['sha256']
            if name == 'ledger.tsv':
                if valid:
                    ledger = data
                else:
                    pull_error = 'pull hash mismatch: ' + name
                continue
            if dest_ok is None:
                try:
                    Path(a.dest).mkdir(parents=True, exist_ok=True)
                    dest_ok = stat.S_ISDIR(os.lstat(a.dest).st_mode)
                except OSError:
                    dest_ok = False
            if not dest_ok:
                pull_error = 'dest is not a plain directory; remote copy retained'
                continue
            target = Path(a.dest) / Path(name).name
            try:
                with target.open('xb') as f:
                    f.write(data)
                if digest(read_plain(target)) != entry['sha256'] or not valid:
                    pull_error = 'pull hash mismatch: ' + name
            except FileExistsError:
                try:
                    same = digest(read_plain(target)) == digest(data)
                except OSError:
                    same = False
                if not same:
                    pull_error = 'different existing clip: ' + str(target)
            if not valid:
                pull_error = 'pull hash mismatch: ' + name
            try:
                if valid and digest(read_plain(target)) == entry['sha256']:
                    received_clips[Path(name).name] = entry['sha256']
            except OSError:
                pass
        if pull_error is None:
            try:
                write_plain(a.ledger, ledger)
            except OSError as exc:
                pull_error = f'shot ledger not written: {exc}'
        if pull_error is not None:
            print(pull_error)
        try:
            after = r.call('balance', project=project, source=(ROOT / 'tools/flow_balance_ws.py').read_text())
        except RuntimeError:
            after = None
        note = ''
        if after is None:
            spent = r.call('estimate', folder=folder)
            note = 'After balance unavailable; sum of submitted shot estimates from run charge ledger.'
        elif after > before:
            spent = r.call('estimate', folder=folder)
            note = f'balance rose by {after - before:g}; amount = estimate sum'
        else:
            spent = before - after
        if a.dry_run:
            spent = 0
        sys.path.insert(0, str(ROOT))
        from tools import credit_ledger
        credit_ledger.add(argparse.Namespace(who=a.who, engine='flow', unit='credits',
            credits=spent, channel=a.channel, purpose=a.purpose, task=a.task,
            kind='test' if a.dry_run else a.kind, before=before, after=after,
            when=None, note=note, include_balances=True), path=Path(live_path))
        code = interrupted[0] or (2 if pull_error else code)
        if spent > a.max_credits:
            print(f'OVER CAP by {spent - a.max_credits:g}')
            code = 6
        verified = sum(
            row['status'] == 'verified'
            and bool(row.get('sha256'))
            and received_clips.get(row.get('file', '').replace('\\', '/').rsplit('/', 1)[-1]) == row['sha256']
            for row in csv.DictReader(ledger.decode().splitlines(), delimiter='\t'))
        print(f'SUMMARY balance_before={before} balance_after={after} spent={spent} cap={a.max_credits:g} shots_verified={verified} exit={code}')
        return code
    finally:
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        r.close()


if __name__ == '__main__':
    sys.exit(main())
