#!/usr/bin/env python3
"""Publish the hub's local main through a scanned PR, without changing the checkout."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.publish_scan import git, scan


def command(repo, args, allowed=(0,)):
    result = subprocess.run(args, cwd=repo, capture_output=True, text=True)
    if result.returncode not in allowed:
        raise RuntimeError('external command failed: ' + args[0])
    return result


def send_letter(repo, kind, body):
    from lib import mailbox
    sid = (repo / 'state/locks/cto-active').read_text().strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,63}', sid):
        raise RuntimeError('invalid CTO pointer')
    mailbox.send('cto', sid, body, 'system', 'hub-sync', kind=kind,
                 subject='hub sync ' + kind)


def run(repo, go=False, *, send=send_letter, out=print):
    repo = Path(repo)
    git(repo, 'fetch', 'origin', 'main')
    local = git(repo, 'rev-parse', 'main').stdout.decode().strip()
    remote = git(repo, 'rev-parse', 'origin/main').stdout.decode().strip()
    ahead = int(git(repo, 'rev-list', '--count', remote + '..' + local).stdout)
    if not ahead:
        out('nothing to publish')
        return 0
    prs = json.loads(command(repo, ['gh', 'pr', 'list', '--state', 'open', '--base', 'main', '--limit', '10000',
                                  '--json', 'number,headRefName,headRefOid']).stdout)
    previous = [p for p in prs if p['headRefName'].startswith('sync/contabo-main-')]
    for pr in previous:
        oid = pr['headRefOid']
        if git(repo, 'cat-file', '-e', oid, allowed=(0, 1, 128)).returncode:
            git(repo, 'fetch', 'origin', pr['headRefName'])
        parent = git(repo, 'rev-parse', '--verify', oid + '^1', allowed=(0, 128))
        if parent.returncode == 0 and parent.stdout.decode().strip() == local:
            out(f"nothing to publish (PR #{pr['number']} already contains local main)")
            return 0
    merged = git(repo, 'merge-tree', '--write-tree', local, remote, allowed=(0, 1))
    if merged.returncode:
        send(repo, 'blocker', 'hub sync: merge-tree conflict; no push')
        out('hub sync: conflict; no push')
        return 3
    tree = merged.stdout.decode().splitlines()[0]
    files = git(repo, 'diff', '--name-only', '-z', remote, tree).stdout.decode().split('\0')
    skills = sorted({p.split('/')[2] for p in files if p.startswith('.claude/skills/') and len(p.split('/')) > 2})
    skill_text = ', '.join(skills) or '(none)'
    count = len([p for p in files if p])
    with tempfile.TemporaryDirectory(prefix='hub-sync-') as temp:
        message = Path(temp) / 'message'
        message.write_text(f'Hub sync: {ahead} commits; skills: {skill_text}\n')
        candidate = git(repo, 'commit-tree', tree, '-p', local, '-p', remote, '-F', str(message)).stdout.decode().strip()
        report = Path(temp) / 'gitleaks.json'
        leaks = command(repo, ['gitleaks', 'git', '--log-opts', f'origin/main..{candidate}',
                              '--redact', '--no-banner', '--report-format', 'json',
                              '--report-path', str(report), '.'], allowed=(0, 1))
        findings = []
        if leaks.returncode:
            if not report.exists():
                raise RuntimeError('gitleaks failed without a report')
            for item in json.loads(report.read_text()):
                findings.append(f"{item['File']} | {item['StartLine']} | {item['RuleID']}")
            if not findings:
                raise RuntimeError('gitleaks failed without findings')
        hits, binaries = scan(repo, remote, candidate)
        findings.extend(f'{h.path} | {h.line} | {h.rule}' for h in hits)
        if findings:
            send(repo, 'blocker', '\n'.join(findings))
            out('hub sync: scan findings; no push')
            return 1
        branch = 'sync/contabo-main-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')
        plan = (f'{ahead} commits; {count} files; skills: {skill_text}; '
                f'gitleaks: clean; publish_scan: clean; binaries: {len(binaries)}')
        out(f'plan: {plan}')
        out(f'new branch: {branch}; PR to main')
        if not go:
            out('dry run: no push, PR or report letter')
            return 0
        # Refuse a same-minute collision rather than reusing an existing branch.
        existing = git(repo, 'ls-remote', '--heads', 'origin', 'refs/heads/' + branch).stdout
        if existing:
            raise RuntimeError('sync branch already exists; retry next minute')
        git(repo, 'push', 'origin', candidate + ':refs/heads/' + branch)
        body = Path(temp) / 'body.md'
        body.write_text(f'{plan}\n\n## Not checked / risk\n'
                        'Automated scans do not prove absence of sensitive information. '
                        'Binary contents and live behavior are not checked. Review before merging.\n')
        created = command(repo, ['gh', 'pr', 'create', '--base', 'main', '--head', branch,
                                 '--title', f'Hub sync: {ahead} commits', '--body-file', str(body)]).stdout.strip()
        match = re.search(r'/pull/(\d+)\s*$', created)
        if not match:
            raise RuntimeError('could not identify created PR')
        number = int(match.group(1))
        for pr in previous:
            command(repo, ['gh', 'pr', 'close', str(pr['number']), '--comment', f'superseded by #{number}'])
        send(repo, 'report', f'hub sync PR #{number} ready ({ahead} commits; skills: {skill_text})')
        out(f'PR #{number} ready')
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--go', action='store_true')
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        return run(args.repo, args.go)
    except (OSError, ValueError, KeyError, RuntimeError):
        print('hub sync: operation failed; inspect configuration and retry')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
