#!/usr/bin/env python3
"""Report files shared by open PRs and Contabo's unpublished local main."""
import json
import os
from pathlib import Path
import socket
import subprocess


def run(repo=None, *, contabo=None, out=print):
    repo = Path(repo or Path.cwd())
    owners = {}
    def add(path, owner):
        owners.setdefault(path, set()).add(owner)
    try:
        result = subprocess.run(['gh', 'pr', 'list', '--limit', '10000', '--json', 'number,headRefName,files'],
                                cwd=repo, check=True, capture_output=True, text=True)
        for pr in json.loads(result.stdout):
            for file in pr['files']:
                add(file['path'], '#' + str(pr['number']))
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
        out('kit_overlap: could not read open PRs')
    if contabo is None:
        contabo = os.environ.get('ORG_HOST', socket.gethostname()).lower().startswith('contabo')
    if contabo:
        try:
            result = subprocess.run(['git', 'log', '-m', '--no-renames', '--format=', '--name-only', '-z', 'origin/main..main'],
                                    cwd=repo, check=True, capture_output=True, text=True)
            for path in result.stdout.split('\0'):
                if path.strip('\n'):
                    add(path.strip('\n'), 'contabo-local')
        except (OSError, subprocess.CalledProcessError):
            out('kit_overlap: could not read local main')
    for path in sorted(owners, key=lambda p: (not p.startswith('.claude/skills/'), p)):
        if len(owners[path]) >= 2:
            out(path + ' | ' + ', '.join(sorted(owners[path])))
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
