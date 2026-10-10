"""Read-only HQ compatibility-link audit. A clean result is not permission to remove links."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import stat
import subprocess
import sys

SECRET_NAMES = ('.env', '.env.*', '*.env', 'credentials*', '*.pem', '*.key', '.credentials.json')
FORBIDDEN = ('/etc/infisical', '/etc/mooniex', '/etc/sompong')
CATEGORIES = ('services', 'scripts', 'cron', 'git', 'claude', 'virtualenvs', 'processes', 'not scanned')


def secret(path):
    path = Path(path)
    return any(fnmatch.fnmatch(part, pattern) for part in path.parts for pattern in SECRET_NAMES) or any(
        str(path) == base or str(path).startswith(base + '/') for base in FORBIDDEN)


def regular(path):
    """Reject symlinks, including symlink ancestors, before opening a file."""
    path = Path(path).absolute()
    if secret(path):
        return False
    if any(p.is_symlink() for p in (path, *path.parents)):
        return False
    return stat.S_ISREG(path.lstat().st_mode)


def reason(exc):
    # Exception text and command stderr can contain sensitive file contents.
    return getattr(exc, 'strerror', None) or type(exc).__name__


def run(args):
    return subprocess.run(args, capture_output=True, text=True, errors='replace', check=False)


def walk(root, errors):
    root = Path(root)
    if secret(root) or root.is_symlink():
        return
    def failed(exc):
        errors.append(reason(exc))
    for base, dirs, files in os.walk(root, followlinks=False, onerror=failed):
        dirs[:] = sorted(d for d in dirs if d not in ('worktrees', 'node_modules', '.git')
                         and not secret(Path(base) / d) and not (Path(base) / d).is_symlink())
        yield Path(base), files


def discover_links(hq_root, link_dirs):
    links, errors = [], []
    hq = Path(hq_root).resolve()
    for directory in link_dirs:
        try:
            for path in Path(directory).iterdir():
                if stat.S_ISLNK(path.lstat().st_mode) and path.resolve().is_relative_to(hq):
                    links.append(str(path.absolute()))
        except (OSError, RuntimeError) as exc:
            errors.append(reason(exc))
    return sorted(set(links)), errors


def matches(text, old):
    return re.search(re.escape(old) + r'(?=$|/|[^\w.\-~])', text) is not None


def read_lines(path, records, errors, first=False):
    try:
        if regular(path):
            with Path(path).open(errors='replace') as stream:
                for number, line in enumerate(stream, 1):
                    records.append((f'{path}:{number}', line))
                    if first:
                        break
    except OSError as exc:
        errors.append(reason(exc))


def read_services(root, platform):
    records, errors, scripts = [], [], set()
    paths = []
    if platform == 'linux':
        for base, files in walk(root, errors):
            paths.extend(base / f for f in files if Path(f).suffix in ('.service', '.timer', '.conf'))
    else:
        try:
            paths = list(Path(root).glob('*.plist'))
            # iterdir reports permissions that glob can hide.
            list(Path(root).iterdir())
        except FileNotFoundError:
            pass
        except OSError as exc:
            errors.append(reason(exc))
    for path in paths:
        start = len(records)
        read_lines(path, records, errors)
        try:
            if not regular(path):
                continue
            if platform == 'darwin':
                with path.open('rb') as stream:
                    data = plistlib.load(stream)
                args = data.get('ProgramArguments', []) + [data.get('Program', '')]
            else:
                text = ''.join(line for _, line in records[start:]).replace('\\\n', '')
                args = []
                for line in text.splitlines():
                    if line.strip().startswith('ExecStart='):
                        args.extend(shlex.split(line.strip().split('=', 1)[1]))
            for arg in args:
                candidate = arg.lstrip('-+!:@')
                if candidate.startswith('/'):
                    try:
                        # Explicit script references can use a compat-link ancestor.
                        resolved = Path(candidate).resolve()
                        if not secret(candidate) and regular(resolved):
                            scripts.add(resolved)
                    except FileNotFoundError:
                        pass
        except (OSError, ValueError, TypeError, plistlib.InvalidFileException) as exc:
            errors.append(reason(exc))
    return records, errors, scripts


def read_scripts(paths):
    records, errors = [], []
    for path in sorted(paths):
        read_lines(path, records, errors)
    return records, errors


def read_cron(root, platform, runner=run):
    records, errors = [], []
    try:
        result = runner(['crontab', '-l'])
        if result.returncode == 0:
            records.extend((f'crontab:{n}', line) for n, line in enumerate(result.stdout.splitlines(), 1))
        elif 'no crontab for' not in result.stderr.lower():
            errors.append('crontab command failed')
    except FileNotFoundError:
        pass  # crontab is optional.
    except OSError as exc:
        errors.append(reason(exc))
    if platform == 'linux':
        try:
            for path in Path(root).iterdir():
                read_lines(path, records, errors)
        except FileNotFoundError:
            pass
        except OSError as exc:
            errors.append(reason(exc))
    return records, errors


def read_claude(home):
    records, errors = [], []
    for name in ('settings.json', 'settings.local.json'):
        path = Path(home) / '.claude' / name
        if path.exists():
            read_lines(path, records, errors)
    path = Path(home) / '.claude.json'
    try:
        if regular(path):
            with path.open() as stream:
                data = json.load(stream)
            projects = data.get('projects', {})
            if not isinstance(projects, dict):
                raise ValueError('invalid projects')
            records.extend((key, key) for key in projects)
    except FileNotFoundError:
        pass
    except (OSError, ValueError, AttributeError) as exc:
        errors.append(reason(exc))
    return records, errors


def read_hq(root):
    repos, records, errors, unscanned = [], [], [], []
    for base, files in walk(root, errors):
        marker = base / '.git'
        if marker.is_dir() and not marker.is_symlink():
            repos.append(base)
        for name in files:
            if name.startswith('.env'):
                unscanned.append(str(base / name))
        if 'pyvenv.cfg' in files:
            read_lines(base / 'pyvenv.cfg', records, errors)
            try:
                if not (base / 'bin').is_symlink():
                    for path in (base / 'bin').iterdir():
                        read_lines(path, records, errors, first=True)
            except OSError as exc:
                errors.append(reason(exc))
    unscanned = [p for p in unscanned if any(Path(p).is_relative_to(r) for r in repos)]
    return repos, records, errors, unscanned


def read_git(repo, old, runner=run):
    hits, errors = [], []
    # Exclude secrets in git itself, before grep opens blobs or working-tree files.
    exclusions = [f':(exclude,glob)**/{pattern}' for pattern in SECRET_NAMES]
    exclusions += [f':(exclude,glob)**/{pattern}/**' for pattern in SECRET_NAMES]
    try:
        tracked = runner(['git', '-C', str(repo), 'ls-files', '-z'])
        if tracked.returncode:
            return {'repo': str(repo), 'count': 0, 'hits': []}, ['git ls-files failed']
        for name in tracked.stdout.split('\0'):
            if not name:
                continue
            try:
                safe = regular(Path(repo) / name)
            except FileNotFoundError:
                safe = False
            if not safe:
                exclusions.append(f':(exclude,literal){name}')
        result = runner(['git', '-C', str(repo), 'grep', '-n', '-z', '-F', '-I', '-e', old,
                         '--', '.', *exclusions])
        if result.returncode not in (0, 1):
            errors.append('git grep failed')
        else:
            for row in result.stdout.splitlines():
                parts = row.split('\0', 2)
                if len(parts) == 3 and matches(parts[2], old):
                    hits.append(f'{parts[0]}:{parts[1]}')
    except OSError as exc:
        errors.append(reason(exc))
    return {'repo': str(repo), 'count': len(hits), 'hits': hits[:20]}, errors


def read_processes(root, platform, runner=run):
    records, errors = [], []
    if platform == 'darwin':
        try:
            names = runner(['ps', '-axo', 'pid=,comm='])
            commands = runner(['ps', '-axo', 'pid=,command='])
            if names.returncode or commands.returncode:
                return [], ['ps command failed']
            comm = dict(line.strip().split(None, 1) for line in names.stdout.splitlines() if line.strip())
            for line in commands.stdout.splitlines():
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    records.append(({'pid': int(parts[0]), 'name': comm.get(parts[0], 'unknown')}, parts[1]))
        except (OSError, ValueError) as exc:
            errors.append(reason(exc))
    else:
        try:
            pids = list(Path(root).iterdir())
        except OSError as exc:
            return [], [reason(exc)]
        for pid in pids:
            if not pid.name.isdigit() or pid.is_symlink():
                continue
            try:
                name = (pid / 'comm').read_text().strip()
                command = (pid / 'cmdline').read_bytes().decode(errors='replace').replace('\0', ' ')
                cwd = os.readlink(pid / 'cwd')
                records.append(({'pid': int(pid.name), 'name': name}, command + '\n' + cwd))
            except FileNotFoundError:
                continue  # Processes can exit during the audit.
            except OSError as exc:
                errors.append(reason(exc))
    return records, errors


def audit(hq_root, link_dirs, platform, home, service_root, cron_root, proc_root, runner=run):
    links, errors = discover_links(hq_root, link_dirs)
    services, service_errors, scripts = read_services(service_root, platform)
    repos, venvs, hq_errors, unscanned = read_hq(hq_root)
    sources = {
        'services': (services, service_errors), 'scripts': read_scripts(scripts),
        'cron': read_cron(cron_root, platform, runner), 'claude': read_claude(home),
        'virtualenvs': (venvs, hq_errors), 'processes': read_processes(proc_root, platform, runner),
    }
    errors.extend(hq_errors)
    result = {'links': [], 'unreadable': errors}
    for old in links:
        categories = {}
        for category, (records, failures) in sources.items():
            hits = [location for location, line in records if matches(line, old)]
            categories[category] = {'count': len(hits), 'hits': hits, 'unreadable': failures}
        git_repos, git_errors = [], []
        for repo in repos:
            entry, failures = read_git(repo, old, runner)
            git_repos.append(entry)
            git_errors.extend(failures)
        categories['git'] = {'count': sum(r['count'] for r in git_repos), 'repos': git_repos,
                             'unreadable': git_errors}
        categories['not scanned'] = {'count': len(unscanned), 'hits': unscanned}
        result['links'].append({'path': old, 'categories': categories})
    # Even an empty discovery result cannot hide unreadable readers.
    result['unreadable'].extend(f'{name}: {failure}' for name, (_, failures) in sources.items()
                                for failure in failures)
    return result


def exit_code(result):
    return int(bool(result['unreadable']) or any(
        data['count'] or data.get('unreadable') for link in result['links']
        for name, data in link['categories'].items() if name != 'not scanned'))


def render(result):
    lines = [f'unreadable: {error}' for error in result['unreadable']]
    for link in result['links']:
        lines.append(link['path'])
        for category in CATEGORIES:
            data = link['categories'][category]
            lines.append(f'  {category:<15} -> {data["count"]}')
            lines.extend(f'    unreadable: {error}' for error in data.get('unreadable', []))
            for hit in data.get('hits', []):
                if isinstance(hit, dict):
                    hit = f'{hit["pid"]} {hit["name"]}'
                suffix = ' (not scanned (secret file, check by hand))' if category == 'not scanned' else ''
                lines.append(f'    {hit}{suffix}')
            for repo in data.get('repos', []):
                lines.append(f'    {repo["repo"]}: {repo["count"]} total (up to 20 shown)')
                lines.extend(f'      {hit}' for hit in repo['hits'])
    return '\n'.join(lines) or 'No compat links found.'


def main(argv=None, *, auditor=audit, platform=None, home=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hq-root', type=Path)
    parser.add_argument('--link-dir', action='append', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    platform = platform or sys.platform
    if platform not in ('linux', 'darwin'):
        parser.error('supported platforms: linux, darwin')
    home = Path(home) if home is not None else Path.home()
    hq = args.hq_root or (Path('/opt/MoonieXHQ') if platform == 'linux' else home / 'MoonieXHQ')
    dirs = args.link_dir or ([Path('/opt'), Path('/root'), Path('/root/projects')]
                             if platform == 'linux' else [home / 'Projects'])
    result = auditor(hq.expanduser().absolute(), [p.expanduser().absolute() for p in dirs], platform, home,
                     Path('/etc/systemd/system') if platform == 'linux' else home / 'Library/LaunchAgents',
                     Path('/etc/cron.d'), Path('/proc'))
    print(json.dumps(result, indent=2) if args.json else render(result))
    return exit_code(result)


if __name__ == '__main__':
    sys.exit(main())
