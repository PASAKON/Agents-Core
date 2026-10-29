"""Isolated installer: fake checkout, unit directory and systemctl only."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / 'checkout'
    for name in ('scripts/hub', 'tools', 'lib', 'runners', 'deploy/systemd', '.venv/bin'):
        (root / name).mkdir(parents=True)
    for name in ('scripts/install-disk-steward.sh', 'deploy/systemd/org-disk-steward.service',
                 'deploy/systemd/org-disk-steward.timer'):
        shutil.copyfile(ROOT / name, root / name)
    for name in ('tools/disk_steward.py', 'scripts/hub/with-org-db-env.sh', '.venv/bin/python'):
        (root / name).write_text('#!/bin/sh\nexit 0\n')
        (root / name).chmod(0o755)
    units = tmp_path / 'units'
    units.mkdir()
    (units / 'org-worktree-reap.timer').write_text('preserve me')
    ctl = tmp_path / 'systemctl'
    ctl.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\n')
    ctl.chmod(0o755)
    calls = tmp_path / 'calls'
    env = dict(os.environ, ORG_STEWARD_UNIT_DIR=str(units), ORG_STEWARD_SYSTEMCTL=str(ctl), CALLS=str(calls))
    def run(action='install'):
        return subprocess.run(['bash', str(root / 'scripts/install-disk-steward.sh'), action],
                              env=env, text=True, capture_output=True)
    return root, units, calls, run


def test_install_repeat_uninstall_status(setup):
    root, units, calls, run = setup
    for _ in range(2):
        result = run()
        assert result.returncode == 0, result.stderr
        assert 'Rollback:' in result.stdout
        service = (units / 'org-disk-steward.service').read_text()
        assert '@ROOT@' not in service and str(root) in service
        assert 'Environment=ORG_HOST=contabo' in service
        assert 'TimeoutStartSec=45min' in service
        assert 'disk_steward.py tick' in service
    assert 'disable --now org-worktree-reap.timer' in calls.read_text()
    assert run('status').returncode == 0
    assert run('uninstall').returncode == 0
    assert not (units / 'org-disk-steward.service').exists()
    assert (units / 'org-worktree-reap.timer').read_text() == 'preserve me'
    assert 'enable --now org-worktree-reap.timer' in calls.read_text()


def test_missing_python_and_bad_action(setup):
    root, units, calls, run = setup
    (root / '.venv/bin/python').unlink()
    assert run().returncode != 0
    assert run('bogus').returncode == 2
    assert not calls.exists()


@pytest.mark.parametrize('target', ['tools/disk_steward.py', 'scripts/hub', 'deploy/systemd/org-disk-steward.service'])
def test_writable_source_refused(setup, target):
    if os.geteuid() != 0:
        pytest.skip('root trust gate')
    root, units, calls, run = setup
    (root / target).chmod(0o777)
    assert run().returncode != 0
    assert not calls.exists()


def test_worktree_refused(setup):
    root, units, calls, run = setup
    nested = root / 'worktrees' / 'nested'
    (nested / 'scripts').mkdir(parents=True)
    shutil.copyfile(root / 'scripts/install-disk-steward.sh', nested / 'scripts/install-disk-steward.sh')
    result = subprocess.run(['bash', str(nested / 'scripts/install-disk-steward.sh')],
        env=dict(os.environ, ORG_STEWARD_UNIT_DIR=str(units)), capture_output=True, text=True)
    assert result.returncode != 0 and 'worktrees/' in result.stderr
    assert not calls.exists()


def test_timer_contract():
    timer = (ROOT / 'deploy/systemd/org-disk-steward.timer').read_text()
    assert all(s in timer for s in ('OnBootSec=10min', 'OnUnitActiveSec=30min', 'Persistent=true'))
