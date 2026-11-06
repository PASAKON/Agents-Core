#!/usr/bin/env python3
"""Scan historical additions, emitting shapes only (never matched values)."""
import argparse
from dataclasses import dataclass
import re
import subprocess
from pathlib import Path


def git(repo, *args, allowed=(0,)):
    p = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    if p.returncode not in allowed:
        raise RuntimeError('git operation failed')
    return p


RULES = {
    'email': r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+',
    'thai-phone': r'(?:\+66|0)[689]\d[- ]?\d{3}[- ]?\d{4}',
    'line-id': r'\b[UCR][0-9a-f]{32}\b',
    'public-ipv4': r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])',
    'thai-id': r'(?<!\d)\d(?:-?\d){12}(?!\d)',
    'bank-account': r'(?<!\d)\d{3}-\d-\d{5}-\d(?!\d)',
    'private-key': r'BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY',
    'url-credential': r'[?&](?:access_token|token|key|sig|signature|code)=(?P<value>[^\s&#\'"<>]{8,})',
    'credential': r'''\b(?:password|secret|api_key|token)\b['"]?\s*[:=]\s*(?:"(?P<double>[^"\r\n]{8,})"|'(?P<single>[^'\r\n]{8,})'|(?P<bare>[^\s'",;]{8,}))''',
}


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    rule: str
    shape: str


def matches(line):
    if line.lstrip().startswith('@'):
        return
    for rule, pattern in RULES.items():
        for match in re.finditer(pattern, line, re.I if rule in {'credential', 'url-credential'} else 0):
            value = next((v for v in match.groupdict().values() if v is not None), match.group())
            if rule == 'email':
                domain = value.rsplit('@', 1)[1].lower()
                if value.lower() == 'noreply@anthropic.com' or domain in {
                    'users.noreply.github.com', 'example.com', 'example.org', 'localhost'
                }:
                    continue
            if rule == 'public-ipv4':
                a, b, c, d = map(int, value.split('.'))
                if max(a, b, c, d) > 255 or a in (0, 10, 127) or (a == 192 and b == 168) or (a == 100 and 64 <= b <= 127):
                    continue
            shape = ('x@' + value.rsplit('@', 1)[1]) if rule == 'email' else ''.join(
                '9' if ch.isdigit() else 'a' if ch.isalpha() else ch for ch in value)
            yield rule, value, shape


def scan(repo, base, head):
    # Resolve refs first so user input cannot be interpreted as log options.
    base = git(repo, 'rev-parse', '--verify', base + '^{commit}').stdout.decode().strip()
    head = git(repo, 'rev-parse', '--verify', head + '^{commit}').stdout.decode().strip()
    git(repo, 'rev-parse', '--verify', 'origin/main^{commit}')
    patch = git(repo, '-c', 'core.quotePath=false', 'log', '-p', '-m', '--no-renames', '--full-index',
                '--no-ext-diff', '--no-textconv', '--format=SCAN-COMMIT %H', base + '..' + head, '--').stdout.decode('utf-8', 'replace')
    hits, binaries, known = [], {}, {}
    path, commit, lineno, in_hunk, binary_blob = '', '', 0, False, ''
    for line in patch.splitlines():
        if line.startswith('SCAN-COMMIT '):
            commit = line.split()[1]
            in_hunk = False
        elif line.startswith('diff --git '):
            path = line.split(' b/', 1)[-1]
            in_hunk = False
            binary_blob = ''
        elif line.startswith('index ') and not in_hunk:
            old, new = line.split()[1].split('..')
            binary_blob = new if new.strip('0') else old
        elif line.startswith('+++ b/') and not in_hunk:
            path = line[6:].split('\t', 1)[0]
        elif line.startswith('Binary files '):
            if binary_blob:
                binaries[(commit, path)] = int(git(repo, 'cat-file', '-s', binary_blob).stdout)
        elif line.startswith('@@ '):
            lineno = int(re.search(r'\+(\d+)', line).group(1))
            in_hunk = True
        elif in_hunk and line.startswith('+'):
            for rule, value, shape in matches(line[1:]):
                if value not in known:
                    known[value] = git(repo, 'grep', '-F', '-l', '-e', value, 'origin/main', '--', allowed=(0, 1)).returncode == 0
                if not known[value]:
                    hit = Hit(path, lineno, rule, shape)
                    if hit not in hits:
                        hits.append(hit)
            lineno += 1
        elif in_hunk and line.startswith(' '):
            lineno += 1
    return hits, binaries


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base')
    parser.add_argument('head')
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        hits, binaries = scan(args.repo, args.base, args.head)
        for hit in hits:
            print(f'{hit.path} | {hit.rule} | {hit.shape}')
        for (_, path), size in binaries.items():
            print(f'{path} | binary | {size} bytes')
        return int(bool(hits))
    except (OSError, ValueError, RuntimeError):
        print('publish_scan: scan failed')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
