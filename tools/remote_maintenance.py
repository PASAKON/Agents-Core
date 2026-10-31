"""DB-free operations invoked only through the authenticated hub mesh key.

The hub supplies task metadata, never a shell command. Native roots are read
locally; paths and Git identity are checked again before destructive work.
"""
from __future__ import annotations

import atexit
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import stat
import subprocess
import tempfile
import time

from lib import config
from tools import disk_steward, workdir
from tools.node_dispatch import PAYLOAD_RE, _redact

MAX_TASKS = 3
MAX_BYTES = 2 * 1024**3
TERMINAL = {'done', 'merged', 'cancelled', 'failed'}
MEDIA = set('png jpg jpeg gif webp heic mp4 mov webm mkv avi mp3 wav m4a aac flac ogg'.split())
# The launcher's own scratch files: never part of a recovery commit.
SCRATCH = ['.worker.pid', '.worker.json', 'TASK.md', '.org-task.json', '.org-worker.mcp.json',
           'CTO-FEEDBACK.md', 'REPORT.md', 'BLOCKER.md', 'HEARTBEAT', 'MAILBOX.md', ':(glob)*.log']
# A worker that exited without its launcher's commit step is recovered by the
# hub only after its git state has been still this long (the launcher, a
# separate process from the recorded worker pid, may still be mid-step).
RECOVERY_QUIET_S = 300
# What this module scans before it pushes: the publish verbs below (publish_branch
# and publish_ph, which codex/agy workers reach through the hub) and the commit the
# hub makes for a dead worker. A claude worker's own `git push` is not covered yet;
# that changes with the role contract, not here. The mesh call that carries a
# publish times out at 300 s (lib/mesh.py).
GITLEAKS_TIMEOUT_S = 120
# The scanner's rules: its built-in set, named explicitly so no other config is looked up.
HUB_GITLEAKS_TOML = '[extend]\nuseDefault = true\n'
WINBOX_MIN_FREE_RAM = 4 * 1024**3
MAX_FINDINGS = 5


def encode(row):
    """Lowercase hex of the compact JSON: the only characters on the wire are
    [0-9a-f], so no remote shell or parser has anything to re-read."""
    return json.dumps(row, separators=(',', ':')).encode().hex()


def reap_grace_seconds():
    """Remote terminal-task grace, independent of local orphan retention."""
    policy = disk_steward.policy
    hours = float(policy.load(policy.POLICY_PATH)['remote_reap']['grace_hours'])
    if not 0 < hours < float('inf'):
        raise ValueError('remote reap grace must be positive and finite')
    return hours * 3600


def decode(payload):
    if not isinstance(payload, str) or not PAYLOAD_RE.fullmatch(payload):
        raise ValueError('malformed payload')
    value = json.loads(bytes.fromhex(payload).decode('utf-8'))
    if not isinstance(value, dict):
        raise ValueError('metadata must be an object')
    return value


def contained(path, root):
    """Lexical Windows validation also works in Unix tests; native check follows."""
    windows = isinstance(root, PureWindowsPath) or bool(PureWindowsPath(str(root)).drive)
    cls = PureWindowsPath if windows else Path
    p, r = cls(path), cls(root)
    if not windows and ('\\' in str(path) or PureWindowsPath(str(path)).drive):
        raise ValueError('foreign path syntax')
    if not p.is_absolute() or '..' in p.parts or p == r or r not in p.parents:
        raise ValueError('path outside root')
    if windows and os.name != 'nt':
        return p
    p, r = Path(p), Path(r).resolve()
    if r not in p.resolve().parents:
        raise ValueError('resolved path outside root')
    for parent in [p, *p.parents]:
        if parent == r:
            break
        if parent.is_symlink() or (parent.exists() and
                getattr(parent.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('linked/reparse path')
    return p


_NO_HOOKS = []


def _no_hooks():
    """An empty directory to use as core.hooksPath: no hook in the worker's repo runs."""
    if not _NO_HOOKS or not os.path.isdir(_NO_HOOKS[0]):
        _NO_HOOKS[:] = [tempfile.mkdtemp(prefix='hub-nohooks-')]
        atexit.register(shutil.rmtree, _NO_HOOKS[0], True)
    return _NO_HOOKS[0]


def hub_env():
    """The environment of every git and gitleaks process the hub starts: replace
    refs are never followed, nothing prompts, and the hub's own database and
    Infisical values are not passed on to anything a worker could have planted."""
    env = {k: v for k, v in os.environ.items() if k != 'ORG_DB_URL' and not k.startswith('INFISICAL_')}
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_TERMINAL_PROMPT='0')
    return env


def git(wt, *args, stdin=None, hooks=False):
    """One git call from the hub. Hooks and the file-system monitor of the repo
    are off unless the caller asks for the repo's hooks (the recovery commit)."""
    flags = ['-c', 'core.fsmonitor=false', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false']
    if not hooks:
        flags += ['-c', 'core.hooksPath=' + _no_hooks()]
    result = subprocess.run(['git', *flags, *args], cwd=str(wt), capture_output=True,
                            text=True, timeout=120,
                            **({'input': stdin} if stdin is not None else {'stdin': subprocess.DEVNULL}),
                            env=hub_env())
    if result.returncode:
        # git echoes a remote URL with its credentials. Every failure leaves
        # here redacted and bounded, so the reply and the audit row never see
        # the raw text; the caller's own error paths need no second filter.
        sub = next((a for a in args if not a.startswith('-')), 'command')
        detail = _redact((result.stderr or result.stdout or '').strip())[-300:]
        raise ValueError(f'git {sub} failed: {detail}')
    return result.stdout.strip()


def _native_windows():
    return os.name == 'nt'


def require_free_ram():
    """winbox runs a live EA: every verb that starts git or the scanner there
    first needs 4 GiB of free RAM. Fails closed when the figure is unknown."""
    if _native_windows():
        from tools.node_dispatch import _win_avail_phys_bytes
        free = _win_avail_phys_bytes()
        if free is None or free < WINBOX_MIN_FREE_RAM:
            raise ValueError('winbox requires 4 GB free RAM')


def publish_url(wt):
    """The one URL the hub fetches from and pushes to. It comes from
    config/projects.yaml on this host, by the project in the worktree's name
    (<project>__<role>__<task>), never from the worker's repository config."""
    from tools.delegate import _ssh_remote_url
    try:
        return _ssh_remote_url(config.get_project(Path(wt).name.partition('__')[0]).get('remote') or '')
    except ValueError:
        raise ValueError('no publish URL for this worktree') from None


def _refuse_split_remote(wt):
    """The repository's own remote.origin settings are not used to publish, but a
    push URL that differs from the fetch URL is a repository set up to send
    commits somewhere else: refuse it."""
    urls, pushurls = set(), set()
    for entry in git(wt, 'config', '--list', '--null').split('\0'):
        key, _, value = entry.partition('\n')
        if key == 'remote.origin.url':
            urls.add(value)
        elif key == 'remote.origin.pushurl':
            pushurls.add(value)
    if pushurls - urls:
        raise ValueError('remote.origin.pushurl differs from url: not publishing')


def identity(row):
    if row.get('host') != config.self_host() or row['host'] not in {'mac', 'winbox'}:
        raise ValueError('wrong host')
    tid = row.get('id', '')
    branch = row.get('branch', '')
    if not re.fullmatch(r'task-[0-9a-f]{8}', tid):
        raise ValueError('invalid task')
    if not re.fullmatch(r'agent/[a-z_]+-' + re.escape(tid), branch):
        raise ValueError('branch not bound to task')
    wt = contained(row['worktree'], config.host(row['host'])['worktrees'])
    if not isinstance(wt, Path):
        raise ValueError('non-native host path')
    if not wt.name.endswith('__' + tid):
        raise ValueError('worktree not bound to task')
    return wt


def tree_bytes(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return 0
    # Require the remote runtime dependency; reuse the steward's established
    # observable-cwd policy (system processes may deny cwd access). The task
    # owner PID is checked separately, with access denied treated as alive.
    import psutil  # noqa: F401
    cwds = list(disk_steward.live_cwds())
    disk_steward.guard_path(path, cwds=cwds)
    total = 0
    def unreadable(error):
        raise error
    for parent, dirs, files in os.walk(path, followlinks=False, onerror=unreadable):
        for name in dirs + files:
            entry = Path(parent) / name
            info = entry.lstat()
            if entry.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('linked/reparse descendant')
            disk_steward.guard_path(entry, cwds=[])
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
    return total


def clean_origin(wt, branch):
    if git(wt, 'symbolic-ref', '--short', 'HEAD') != branch:
        raise ValueError('checked out branch mismatch')
    if git(wt, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('dirty worktree')
    head = git(wt, 'rev-parse', 'HEAD')
    remote = git(wt, 'ls-remote', '--exit-code', 'origin', 'refs/heads/' + branch)
    if remote.split() != [head, 'refs/heads/' + branch]:
        raise ValueError('branch HEAD is not on origin')
    return head


@contextmanager
def host_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    # Atomic on Windows and POSIX. A crash leaves a fail-closed lock for PH.
    lock = root / '.remote-maintenance.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        yield
    finally:
        os.close(fd)
        lock.unlink()


def reap(payload):
    request = decode(payload)
    rows = request.get('tasks', [])
    if not isinstance(rows, list) or len(rows) > MAX_TASKS:
        raise ValueError('task cap exceeded')
    apply = request.get('apply') is True
    host = config.self_host()
    if host not in {'winbox', 'mac'}:
        raise ValueError('remote hosts only')
    require_free_ram()
    work_root = Path(disk_steward.machine(host)['hq']) / 'Work'
    results, used = [], 0
    with host_lock(work_root):
        for row in rows:
            result = {'task_id': row.get('id'), 'status': 'failed'}
            try:
                wt = identity(row)
                from lib import proc
                if row.get('pid') and proc.pid_alive(row['pid']):
                    raise ValueError('task owner is still alive')
                updated = datetime.fromisoformat(row['updated_at'])
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - updated).total_seconds()
                if row.get('status') not in TERMINAL or age < reap_grace_seconds():
                    raise ValueError('terminal grace not passed')
                work = contained(work_root / row['id'], work_root)
                if not wt.exists():
                    if work.exists():
                        raise ValueError('missing worktree; cannot verify origin')
                    result.update(status='absent', bytes=0)
                else:
                    head = clean_origin(wt, row['branch'])
                    size = tree_bytes(wt) + tree_bytes(work)
                    if used + size > MAX_BYTES:
                        raise ValueError('byte cap exceeded')
                    used += size
                    result.update(status='planned', bytes=size, head=head)
                    if apply:
                        # Recheck after traversal, before close's first deletion.
                        if clean_origin(wt, row['branch']) != head:
                            raise ValueError('HEAD changed')
                        tree_bytes(wt)
                        tree_bytes(work)
                        closed = (workdir.close(row['id'], root=work_root, archive=True)
                                  if work.exists() else {'closed': True})
                        if not closed.get('closed'):
                            raise ValueError('Drive archive/close failed')
                        if clean_origin(wt, row['branch']) != head:
                            raise ValueError('HEAD changed after archive')
                        tree_bytes(wt)
                        git(wt.parent, '--git-dir=' + git(wt, 'rev-parse', '--path-format=absolute', '--git-common-dir'),
                            'worktree', 'remove', str(wt))
                        result['status'] = 'run'
            except Exception as exc:
                result.update(status='failed', error=_redact(str(exc))[:300])
            results.append(result)
    return {'host': host, 'results': results, 'bytes': used, 'dry_run': not apply}


def _clean(text, limit):
    """A rule id or a path out of a report we do not control: printable,
    redacted, bounded."""
    return _redact(re.sub(r'[^\x20-\x7e]', '?', str(text)))[:limit]


def _findings(report):
    """(count, ['<rule id> <path>:<line>', ...]) from gitleaks' JSON report, or
    None when there is no usable one. Nothing else in a finding is read: the
    matched text, the secret and the fingerprint never leave this function."""
    try:
        rows = json.loads(Path(report).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(rows, list) or not rows:
        return None
    shown = []
    for row in rows[:MAX_FINDINGS]:
        if isinstance(row, dict):
            line = row.get('StartLine')
            shown.append(f"{_clean(row.get('RuleID', '?'), 64)} {_clean(row.get('File', '?'), 120)}:"
                         f"{line if isinstance(line, int) else '?'}")
    return len(rows), shown


@contextmanager
def scratch_repo(wt, url, head):
    """A repository the hub owns, built for one publish. It has none of the
    worker's config, hooks, attributes, refs or replace refs: it reads the
    worker's object store through `alternates` (an object is named by its hash,
    so what is scanned is what is pushed) and holds the public history, fetched
    from `url`, under refs/remotes/public. Everything that decides what is
    outgoing, and the push itself, runs here."""
    with tempfile.TemporaryDirectory(prefix='publish-', ignore_cleanup_errors=True) as tmp:
        repo = Path(tmp) / 'scan.git'
        git(tmp, 'init', '-q', '--bare', '--template=', str(repo))
        objects = repo / 'objects' / 'info'
        objects.mkdir(parents=True, exist_ok=True)
        common = git(wt, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        (objects / 'alternates').write_text(common + '/objects\n', encoding='utf-8')
        git(repo, 'fetch', '-q', '--no-tags', url, '+refs/heads/*:refs/remotes/public/*')
        git(repo, 'rev-parse', '--verify', head + '^{commit}')
        yield repo


def scan_outgoing(repo, head, exe):
    """Run gitleaks over exactly the commits about to be pushed, merge commits
    included (-m), in the hub's scratch repository. It runs from an empty
    working directory with the hub's own rules and `gitleaks:allow` comments
    ignored, so nothing the worker wrote or committed can tell it to look away.
    argv is a list: no shell."""
    with tempfile.TemporaryDirectory(prefix='gitleaks-', ignore_cleanup_errors=True) as tmp:
        report = os.path.join(tmp, 'report.json')
        rules = os.path.join(tmp, 'hub.toml')
        empty = os.path.join(tmp, 'cwd')
        os.mkdir(empty)
        with open(rules, 'w', encoding='utf-8') as stream:
            stream.write(HUB_GITLEAKS_TOML)
        argv = [exe, 'git', '--config', rules, '--log-opts=' + head + ' --not --remotes=public -m', '--redact',
                '--no-banner', '--ignore-gitleaks-allow', '--report-format', 'json', '--report-path', report,
                str(repo)]
        try:
            done = subprocess.run(argv, cwd=empty, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, timeout=GITLEAKS_TIMEOUT_S, env=hub_env())
        except subprocess.TimeoutExpired:
            raise ValueError('gitleaks timed out: not publishing') from None
        except OSError:
            raise ValueError(f'gitleaks did not run on {config.self_host()}: not publishing') from None
        if done.returncode == 0:
            return
        found = _findings(report)
    if not found:
        raise ValueError(f'gitleaks failed (exit {done.returncode}): not publishing')
    count, shown = found
    raise ValueError(f"gitleaks: {count} finding{'s' if count != 1 else ''} in outgoing commits "
                     f"({'; '.join(shown)}): not publishing")


def outgoing_check(wt, branch, *, push=False):
    """The gate in front of every push of a worker's commits (publish_branch,
    publish_ph, and the commit the hub makes for a dead worker, which is pushed
    only through here). All outgoing history is checked in the hub's own scratch
    repository: media and size for every object, including blobs deleted before
    HEAD, then a secret scan. What is public is read from one URL the hub holds
    (publish_url), not from the worker's remote settings. With push=True the
    same repository then pushes to that URL, so what is pushed is what was
    checked."""
    require_free_ram()
    exe = shutil.which('gitleaks')
    if not exe:
        raise ValueError(f'no gitleaks on {config.self_host()}: not publishing')
    url = publish_url(wt)
    _refuse_split_remote(wt)
    head = git(wt, 'rev-parse', 'refs/heads/' + branch)
    with scratch_repo(wt, url, head) as repo:
        commits = git(repo, 'rev-list', head, '--not', '--remotes=public')
        for commit in commits.splitlines():
            # A blob may have both a text and a media name; rev-list's object
            # name alone is not sufficient to enforce the extension policy.
            paths = git(repo, 'diff-tree', '--root', '-m', '--no-commit-id',
                        '--name-only', '-r', '-z', '--diff-filter=AMT', commit)
            if any(Path(name).suffix.lower().lstrip('.') in MEDIA for name in paths.split('\0')):
                raise ValueError('outgoing media path')
        entries = [line.partition(' ') for line in
                   git(repo, 'rev-list', '--objects', head, '--not', '--remotes=public').splitlines() if line]
        if entries:
            # One process for every object, not two per object: a large branch
            # must finish inside the 300 s the mesh call allows.
            info = git(repo, 'cat-file', '--batch-check=%(objecttype) %(objectsize)',
                       stdin=''.join(oid + '\n' for oid, _, _ in entries)).splitlines()
            if len(info) != len(entries):
                raise ValueError('outgoing object listing mismatch')
            for (oid, _, name), line in zip(entries, info):
                if line.endswith(' missing'):
                    raise ValueError('outgoing object missing')
                kind, _, size = line.partition(' ')
                if kind != 'blob':
                    continue
                if Path(name).suffix.lower().lstrip('.') in MEDIA:
                    raise ValueError('outgoing media object')
                if int(size) > 1048576:
                    raise ValueError('outgoing object exceeds 1 MB')
        scan_outgoing(repo, head, exe)
        if push:
            git(repo, 'push', url, head + ':refs/heads/' + branch)
    return head


def publish(payload, *, ph=False):
    require_free_ram()
    row = decode(payload)
    if ph:
        sid = row.get('session_id', '')
        if not re.fullmatch(r'[0-9a-f]{8}', sid):
            raise ValueError('invalid PH session')
        if row.get('host') != config.self_host() or row['host'] not in {'mac', 'winbox'}:
            raise ValueError('wrong host')
        if not re.fullmatch(r'ph/' + sid + r'-[a-z0-9][a-z0-9-]{0,63}', row.get('branch', '')):
            raise ValueError('branch not bound to PH session')
        wt = contained(row['worktree'], config.host(row['host'])['worktrees'])
        if not wt.name.endswith('__ph-' + sid):
            raise ValueError('worktree not bound to PH session')
    else:
        wt = identity(row)
        if row['host'] == 'winbox' and not completion(payload, recover=False).get('ready'):
            raise ValueError('launcher has not completed')
    if row.get('status') != 'review':
        raise ValueError('publication requires review')
    branch = row['branch']
    if git(wt, 'symbolic-ref', '--short', 'HEAD') != branch:
        raise ValueError('checked out branch mismatch')
    head = outgoing_check(wt, branch, push=True)
    return {'branch': branch, 'head': head, 'pushed': True}


def _quiet(gitdir):
    """True when the worktree's git state has not moved for RECOVERY_QUIET_S
    and no git command holds the index. Unknown means not quiet."""
    if (gitdir / 'index.lock').exists():
        return False
    times = [p.stat().st_mtime for p in (gitdir / 'index', gitdir / 'logs' / 'HEAD') if p.exists()]
    return bool(times) and time.time() - max(times) >= RECOVERY_QUIET_S


def _recover_commit(wt, row):
    """The worker's process is gone and its launcher never committed (a real
    winbox run, task-18ff8da2: complete diff staged, launcher step never ran).
    Do what the launcher's step does, minus anything that is not code: stage
    tracked changes and the task's own report, drop launcher scratch files and
    media, commit. The repository's own commit hooks run (its pre-commit secret
    scan is the point of them), the hub's other git calls run with hooks off;
    if a hook refuses, the row stays unrecovered. Nothing is pushed, untracked
    files other than the report stay untouched. The publish gate still checks
    every object."""
    tid = row['id']
    if git(wt, 'symbolic-ref', '--short', 'HEAD') != row['branch']:
        raise ValueError('checked out branch mismatch')
    report = wt / 'docs' / 'reports' / tid / 'REPORT.md'
    git(wt, 'add', '-u')
    if report.is_file() and not report.is_symlink() and report.stat().st_size <= 64000:
        first = report.read_text(encoding='utf-8', errors='replace').splitlines()[:1]
        if first != ['# REPORT ' + tid]:
            raise ValueError('report task mismatch')
        git(wt, 'add', '--', 'docs/reports/' + tid + '/REPORT.md')
    git(wt, 'reset', '-q', '--', *SCRATCH)
    if not git(wt, 'ls-files', '--', 'docs/reports/' + tid + '/REPORT.md'):
        raise ValueError('no report to publish')
    staged = git(wt, 'diff', '--cached', '--name-only', '-z', '--diff-filter=ACMRT').split('\0')
    media = [n for n in staged if n and Path(n).suffix.lower().lstrip('.') in MEDIA]
    if media:
        git(wt, 'reset', '-q', '--', *media)
    if git(wt, 'diff', '--cached', '--name-only'):
        git(wt, 'commit', '-q', '-m', f'task {tid}: hub recovery commit',
            '-m', 'The worker process ended before its launcher committed.', hooks=True)
    head = git(wt, 'rev-parse', 'HEAD')
    if row['host'] == 'winbox':
        (Path(git(wt, 'rev-parse', '--absolute-git-dir')) / 'org-publish-ready').write_text(head)
    return head


def completion(payload, recover=True):
    """Is this remote task finished, with its report on a commit? The recorded
    pid is the CLI's, not the launcher's, so a dead pid alone is not enough:
    the launcher's marker (winbox) or a still git state says the launcher is
    done. When neither shows after RECOVERY_QUIET_S, the launcher is gone and
    the hub commits the worker's tracked and staged changes itself."""
    from lib import proc
    require_free_ram()
    row = decode(payload)
    wt = identity(row)
    pid = row.get('pid')
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or proc.pid_alive(pid):
        return {'ready': False}
    head = git(wt, 'rev-parse', 'HEAD')
    gitdir = Path(git(wt, 'rev-parse', '--absolute-git-dir'))
    marker = gitdir / 'org-publish-ready'
    marked = row['host'] == 'winbox' and marker.exists() and marker.read_text().strip() == head
    dirty = bool(git(wt, '--no-optional-locks', 'status', '--porcelain', '--untracked-files=no'))
    if marked and dirty:
        return {'ready': False}
    if not marked and (row['host'] == 'winbox' or dirty):
        if not _quiet(gitdir):
            return {'ready': False}
        if dirty:
            if not recover:
                return {'ready': False}
            head = _recover_commit(wt, row)
    report = git(wt, 'show', head + ':docs/reports/' + row['id'] + '/REPORT.md')
    if not report or report.splitlines()[0] != '# REPORT ' + row['id']:
        raise ValueError('report task mismatch')
    if row.get('spawned_at'):
        spawned = datetime.fromisoformat(row['spawned_at'])
        if spawned.tzinfo is None:
            spawned = spawned.replace(tzinfo=timezone.utc)
        report_time = int(git(wt, 'log', '-1', '--format=%ct', head, '--',
                              'docs/reports/' + row['id'] + '/REPORT.md'))
        if report_time < int(spawned.timestamp()):
            return {'ready': False}
    return {'ready': True, 'head': head, 'report': report[:64000]}


def hub_publish(task):
    from lib import mesh
    if config.self_host() != 'contabo' or task.get('host') not in {'winbox', 'mac'}:
        return None
    row = {k: task.get(k) for k in ('id', 'host', 'branch', 'worktree', 'status', 'pid', 'spawned_at')}
    reply = mesh.dispatch(row['host'], 'publish_branch', row['id'], encode(row))
    return reply


def ph_stages(session_id):
    """The stages of the projects this PH session owns, read from the hub's
    portfolio: the review state is the hub's record, not a field the caller
    writes into the request."""
    from lib import db
    with db.get_conn(readonly=True) as conn:
        rows = conn.execute('SELECT stage FROM projects WHERE ph_session = ?', (session_id,)).fetchall()
    return {row['stage'] for row in rows}


def hub_publish_ph(host, session_id, branch, worktree):
    """Explicit PH review request, sent by the hub through the same push guard.

    Session identity is encoded in BOTH the branch and checkout basename;
    arbitrary refs/default branches cannot be named by this interface.
    """
    from lib import mesh
    if config.self_host() != 'contabo' or host not in {'winbox', 'mac'}:
        raise ValueError('remote PH publication is hub only')
    if not mesh.enabled():
        raise ValueError('mesh dispatch is off: not publishing')
    if not re.fullmatch(r'[0-9a-f]{8}', session_id or '') or 'review' not in ph_stages(session_id):
        raise ValueError('publication requires the PH project to be in review')
    return mesh.dispatch(host, 'publish_ph', encode(dict(host=host,
        session_id=session_id, branch=branch, worktree=worktree, status='review')))


def redact_reply(value):
    """Every string leaf of a remote reply, redacted, before the audit row."""
    if isinstance(value, str):
        return _redact(value)
    if isinstance(value, list):
        return [redact_reply(v) for v in value]
    if isinstance(value, dict):
        return {k: redact_reply(v) for k, v in value.items()}
    return value


STAMP = 'remote-reaped.json'


def _stamp_dir():
    """state/storage as a directory fd: the stamp files below are opened relative
    to it, so a link planted in the path cannot redirect this root-run code."""
    return os.open(disk_steward.STATE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)


def _read_stamp(dir_fd):
    try:
        fd = os.open(STAMP, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    except FileNotFoundError:
        return {}
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_size > 16 * 1024**2:
            raise ValueError('reap stamp is not a regular file of this user')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            return json.loads(stream.read().decode('utf-8'))
    finally:
        os.close(fd)


def _write_stamp(dir_fd, completed):
    temp = STAMP + '.tmp'
    try:
        os.unlink(temp, dir_fd=dir_fd)            # a leftover of a crashed run; unlink never follows a link
    except FileNotFoundError:
        pass
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(json.dumps(completed).encode('utf-8'))
    except BaseException:
        os.unlink(temp, dir_fd=dir_fd)
        raise
    os.replace(temp, STAMP, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)


def hub_reap(*, apply=False):
    """One bounded batch per host; selection and audit stay on Contabo. Off
    unless mesh dispatch is on: with the flag unset nothing is sent to a host."""
    from lib import db, mesh
    if config.self_host() != 'contabo':
        raise ValueError('hub only')
    if not mesh.enabled():
        return 0
    failed = False
    with host_lock(disk_steward.STATE):
        dir_fd = _stamp_dir()
        try:
            completed = _read_stamp(dir_fd)
            tasks = db.list_tasks(limit=10000)
            for host in ('winbox', 'mac'):
                candidates = []
                for row in tasks:
                    if row.get('host') != host or row.get('status') not in TERMINAL:
                        continue
                    if completed.get(host + ':' + row['id']) == row.get('updated_at'):
                        continue
                    try:
                        ts = datetime.fromisoformat(row['updated_at'])
                        ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
                        if (datetime.now(timezone.utc) - ts).total_seconds() < reap_grace_seconds():
                            continue
                    except (KeyError, TypeError, ValueError):
                        continue
                    candidates.append({k: row.get(k) for k in
                                       ('id', 'host', 'branch', 'worktree', 'status', 'updated_at', 'pid')})
                candidates.sort(key=lambda r: r['id'])
                cursor = completed.get('cursor:' + host, '')
                candidates = ([r for r in candidates if r['id'] > cursor] +
                              [r for r in candidates if r['id'] <= cursor])
                if apply and candidates:
                    completed['cursor:' + host] = candidates[:MAX_TASKS][-1]['id']
                try:
                    reply = mesh.dispatch(host, 'steward_reap', encode({'tasks': candidates[:MAX_TASKS], 'apply': apply}))
                    results = reply.get('result', {}).get('results', [])
                    expected = {r['id'] for r in candidates[:MAX_TASKS]}
                    allowed = {'run', 'absent'} if apply else {'planned', 'absent'}
                    ok = (reply.get('ok') and len(results) == len(expected)
                          and {r.get('task_id') for r in results} == expected
                          and all(r.get('status') in allowed for r in results))
                    status = ('run' if apply else 'planned') if ok else 'failed'
                    if apply and reply.get('ok'):
                        for result in results:
                            if result['status'] in {'run', 'absent'}:
                                match = next(r for r in candidates if r['id'] == result['task_id'])
                                completed[host + ':' + match['id']] = match['updated_at']
                except Exception as exc:
                    reply, status = {'error': type(exc).__name__}, 'failed'
                failed |= status == 'failed'
                for name in ('reap', 'orphans'):
                    disk_steward.record(dict(name=name, host=host, status=status,
                                             ts=datetime.now(timezone.utc).isoformat(),
                                             rc=int(status == 'failed'), result=redact_reply(reply)), False)
            if apply:
                _write_stamp(dir_fd, completed)
        finally:
            os.close(dir_fd)
    return int(failed)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Hub PH review publication')
    parser.add_argument('host', choices=['mac', 'winbox'])
    parser.add_argument('session_id')
    parser.add_argument('branch')
    parser.add_argument('worktree')
    args = parser.parse_args()
    reply = hub_publish_ph(args.host, args.session_id, args.branch, args.worktree)
    print(json.dumps(reply))
    raise SystemExit(0 if reply.get('ok') else 1)
