"""Check compatibility-path replacements without executing operational scripts."""
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    'scripts/install-share-broker.sh',
    'windows/ops/idm-fetch.sh',
    'windows/ops/idm-run-full.sh',
)
ASSETS = '/opt/MoonieXHQ/Assets/MoonieX/CookierunBot'


@pytest.mark.parametrize('script', SCRIPTS)
def test_bash_syntax(script):
    result = subprocess.run(['bash', '-n', str(ROOT / script)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('script', SCRIPTS)
def test_no_compat_paths(script):
    text = (ROOT / script).read_text()
    for old in ('/root/projects/mooniex-claudeflow', '/root/idm-baseline',
                '/root/idm-fetch.log', '/root/idm-full', '/root/idm-yt'):
        assert old not in text


def test_share_broker_example_target():
    text = (ROOT / SCRIPTS[0]).read_text()
    assert '/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env' in text


def test_fetch_paths():
    text = (ROOT / SCRIPTS[1]).read_text()
    assert f'log={ASSETS}/idm-fetch.log' in text
    assert 'cd /root/idm-packs || exit 1' in text


def test_full_run_paths():
    text = (ROOT / SCRIPTS[2]).read_text()
    assert f'LOG={ASSETS}/idm-full.log' in text
    assert f'"fetch done" {ASSETS}/idm-fetch.log' in text
    assert text.count(f'{ASSETS}/idm-baseline/report.json') == 3
    assert f'IDM_OUT={ASSETS}/idm-full IDM_DEVICE=cpu' in text
    assert 'PACKS=/root/idm-packs' in text
    assert 'VENV=/root/idm-venv/bin/python' in text
