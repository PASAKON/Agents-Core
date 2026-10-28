"""Offline tests: no launchd, DB, Drive, or actual steward execution."""
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'repo with & spaces'
    for name in ('scripts/disk-steward-mac.sh', 'scripts/install-disk-steward-mac.sh',
                 'deploy/launchd/com.mooniex.disk-steward.plist'):
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    (root / '.venv/bin').mkdir(parents=True)
    (root / '.venv/bin/python').symlink_to(sys.executable)
    (root / 'config').mkdir()
    (root / 'config/machine-contract.yaml').write_text('machines: {}\n')
    return root


def run(root, script, *args, home='/Users/someone'):
    return subprocess.run(['bash', str(root / 'scripts' / script), *args],
                          env={**os.environ, 'HOME': str(home)}, cwd=root,
                          text=True, capture_output=True)


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() if p.is_file() else None
            for p in root.rglob('*')}


def test_render_and_dry_run_changes_nothing(repo, tmp_path):
    before = snapshot(tmp_path)
    result = run(repo, 'install-disk-steward-mac.sh', '--dry-run')
    assert result.returncode == 0, result.stderr
    xml = result.stdout.split('</plist>', 1)[0] + '</plist>'
    data = plistlib.loads(xml.encode())  # portable; no plutil
    assert data['StartInterval'] == 1800
    assert data['RunAtLoad'] is True
    assert data['ProgramArguments'] == ['/bin/bash', str(repo / 'scripts/disk-steward-mac.sh')]
    assert data['WorkingDirectory'] == str(repo)
    assert data['EnvironmentVariables']['HOME'] == '/Users/someone'
    assert '/Users/gob' not in result.stdout
    assert 'launchctl bootstrap gui/' in result.stdout
    assert 'launchctl bootout gui/$(id -u)/com.mooniex.disk-steward && rm ~/Library/LaunchAgents/com.mooniex.disk-steward.plist' in result.stdout
    assert snapshot(tmp_path) == before


def test_uninstall_dry_run_preserves_existing_plist(repo, tmp_path):
    home = tmp_path / 'home'
    plist = home / 'Library/LaunchAgents/com.mooniex.disk-steward.plist'
    plist.parent.mkdir(parents=True)
    plist.write_text('existing')
    before = snapshot(tmp_path)
    result = run(repo, 'install-disk-steward-mac.sh', '--uninstall', '--dry-run', home=home)
    assert result.returncode == 0, result.stderr
    assert 'launchctl bootout gui/' in result.stdout
    assert snapshot(tmp_path) == before


def test_missing_mac_row_fails_clearly(repo):
    result = run(repo, 'disk-steward-mac.sh')
    assert result.returncode != 0
    assert 'machine-contract.yaml' in result.stderr
    assert 'requires machines.mac' in result.stderr
    assert not (repo / 'state').exists()


def test_runner_wrapper_environment_rotation_and_exit(repo, tmp_path):
    import yaml
    home = str(tmp_path / 'someone home')
    claude = home + '/claude profile'
    hq = home + '/HQ'
    (repo / 'config/machine-contract.yaml').write_text(yaml.safe_dump({'machines': {'mac': {
        'home': home, 'hq': hq, 'claude_config_dir': claude, 'drive_leg': 'rest_work_archive'}}}))
    (repo / 'tools').mkdir()
    (repo / 'tools/disk_steward.py').write_text('# fixture only\n')
    (repo / 'scripts/hub').mkdir()
    (repo / 'scripts/hub/org-python.sh').write_text(
        'printf "%s\\n" "$HOME" "$MOONIEX_HQ" "$CLAUDE_CONFIG_DIR" "$ORG_HOST" "$@"\nexit 7\n')
    log = repo / 'state/storage/steward-mac.log'
    log.parent.mkdir(parents=True)
    log.write_bytes(b'x' * (5 * 1024 * 1024))
    result = run(repo, 'disk-steward-mac.sh', '--dry-run')
    assert result.returncode == 7, result.stderr
    assert log.with_suffix('.log.1').stat().st_size == 5 * 1024 * 1024
    assert log.read_text().splitlines() == [home, hq, claude, 'mac',
        'tools/disk_steward.py', 'tick', '--host', 'mac', '--dry-run']


def test_install_and_uninstall_are_idempotent_with_mock_launchctl(repo, tmp_path, monkeypatch):
    home = tmp_path / 'home'
    bins = tmp_path / 'bin'
    bins.mkdir()
    (repo / 'tools').mkdir()
    (repo / 'tools/disk_steward.py').write_text('# never executed\n')
    state = tmp_path / 'loaded'
    calls = tmp_path / 'calls'
    scripts = {
        'id': 'echo 501\n',
        'uname': 'echo Darwin\n',
        'launchctl': '''echo "$*" >> "$MOCK_CALLS"
case "$1" in
  print) test -f "$MOCK_STATE" ;;
  bootout) test -f "$MOCK_STATE" && rm "$MOCK_STATE" ;;
  bootstrap) test ! -f "$MOCK_STATE" && touch "$MOCK_STATE" ;;
  *) exit 99 ;;
esac
''',
    }
    for name, body in scripts.items():
        path = bins / name
        path.write_text('#!/bin/bash\n' + body)
        path.chmod(0o755)
    monkeypatch.setenv('PATH', str(bins) + ':' + os.environ['PATH'])
    monkeypatch.setenv('MOCK_STATE', str(state))
    monkeypatch.setenv('MOCK_CALLS', str(calls))
    plist = home / 'Library/LaunchAgents/com.mooniex.disk-steward.plist'
    for _ in range(2):
        result = run(repo, 'install-disk-steward-mac.sh', home=home)
        assert result.returncode == 0, result.stderr
        assert state.exists()
        assert plistlib.loads(plist.read_bytes())['Label'] == 'com.mooniex.disk-steward'
    for _ in range(2):
        result = run(repo, 'install-disk-steward-mac.sh', '--uninstall', home=home)
        assert result.returncode == 0, result.stderr
        assert not plist.exists()
        assert not state.exists()
    lines = calls.read_text().splitlines()
    assert sum(line.startswith('bootstrap gui/501 ') for line in lines) == 2
    assert lines.count('bootout gui/501/com.mooniex.disk-steward') == 2
