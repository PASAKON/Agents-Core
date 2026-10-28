import argparse
import base64
import json
from pathlib import Path
import signal
import subprocess
import shutil

import pytest

from tools import flow_shoot_card as card


class FakeRunner:
    def __init__(self, before=100, after=95, lock=True, mismatch=False, terminate=False):
        self.balances = iter([before, after])
        self.lock = lock
        self.mismatch = mismatch
        self.terminate = terminate
        self.calls = []
        self.killed = []
        self.files = {}

    def call(self, verb, **kw):
        self.calls.append((verb, kw))
        if verb == 'lock':
            return self.lock
        if verb == 'balance':
            return next(self.balances)
        if verb == 'put':
            data = base64.b64decode(kw['data'])
            self.files[kw['name']] = data
            return 'bad' if self.mismatch else card.digest(data)
        if verb == 'run':
            if self.terminate:
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return 0
        if verb == 'pull':
            return {'ledger.tsv': base64.b64encode(b'shot\tstatus\n1\tverified\n').decode(),
                    'shot-01.mp4': base64.b64encode(b'clip').decode()}
        if verb == 'estimate':
            return 4
        raise AssertionError(verb)

    def kill(self, folder):
        self.killed.append(folder)

    def close(self):
        pass


@pytest.fixture
def setup(tmp_path):
    sheet = tmp_path / 'ACT1.md'
    sheet.write_text('https://flow.google.com/project/abc-123\n')
    ledger = tmp_path / 'shots.tsv'
    ledger.write_text('shot\tstatus\n1\ttodo\n')
    live = tmp_path / 'live.jsonl'
    live.touch()
    argv = ['--max-credits', '5', '--sheet', str(sheet), '--ledger', str(ledger),
            '--dest', str(tmp_path / 'out'), '--who', 'cto-fresh', '--channel', 'ILAG',
            '--purpose', 'dry run', '--task', 'task-18f51218']
    return argv, live


@pytest.mark.parametrize('runner,expected', [(FakeRunner(before=4), 3),
    (FakeRunner(before=None), 4), (FakeRunner(mismatch=True), 2), (FakeRunner(lock=False), 5)])
def test_gates(setup, runner, expected, capsys):
    argv, live = setup
    assert card.main(argv, runner, live) == expected
    verbs = [v for v, _ in runner.calls]
    assert 'run' not in verbs
    if expected in (3, 4, 5):
        assert 'put' not in verbs
    if expected == 3:
        assert 'over balance' in capsys.readouterr().out
    assert live.read_text() == ''


def test_exact_inner_argv(setup):
    argv, live = setup
    runner = FakeRunner()
    card.main(argv + ['--only', '1-2', '--dry-run'], runner, live)
    kw = next(kw for v, kw in runner.calls if v == 'run')
    f = kw['folder']
    assert kw['argv'] == [card.PYTHON, '-u', f + r'\tools\flow_shoot.py', 'run',
        '--max-credits', '5.0', '--sheet', f + r'\sheet.md', '--ledger', f + r'\ledger.tsv',
        '--dest', f + r'\out', '--resolution', '720p', '--only', '1-2', '--dry-run']
    assert kw['argv'].count('--max-credits') == 1
    assert '--credit-cap' not in kw['argv']


@pytest.mark.parametrize('flag', ['--max', '-m', '-N', '--credit-cap'])
def test_no_aliases(setup, flag):
    argv, _ = setup
    argv[0] = flag
    with pytest.raises(SystemExit) as error:
        card.parse(argv)
    assert error.value.code == 2


@pytest.mark.parametrize('value', ['nan', 'inf', '-1', '1e999', '1;evil'])
def test_invalid_cap(setup, value):
    argv, _ = setup
    argv[1] = value
    with pytest.raises(SystemExit):
        card.parse(argv)


@pytest.mark.parametrize('dry', [False, True])
def test_live_row(setup, dry):
    argv, live = setup
    assert card.main(argv + (['--dry-run'] if dry else []), FakeRunner(), live) == 0
    rows = [json.loads(line) for line in live.read_text().splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row.items() >= dict(engine='flow', unit='credits', amount=0 if dry else 5,
        balance_before=100, balance_after=95, who='cto-fresh', channel='ILAG',
        purpose='dry run', task='task-18f51218', kind='test' if dry else 'production').items()


def test_termination(setup):
    argv, live = setup
    runner = FakeRunner(terminate=True)
    assert card.main(argv, runner, live) == 143
    assert runner.killed
    assert any(v == 'pull' for v, _ in runner.calls)
    assert len(live.read_text().splitlines()) == 1


def test_taskkill_command(monkeypatch):
    calls = []
    monkeypatch.setattr(card.subprocess, 'run', lambda *a, **kw: calls.append((a, kw)))
    card.Runner.kill(None, r'C:\mooniex\flowcard\abc\run')
    assert calls[0][0][0] == ['ssh', 'winbox', 'powershell -NoProfile -NonInteractive -Command -']
    assert 'taskkill /PID $p /T /F' in calls[0][1]['input']


def test_over_cap(setup, capsys):
    argv, live = setup
    assert card.main(argv, FakeRunner(after=94), live) == 6
    assert 'OVER CAP by 1' in capsys.readouterr().out


def test_fallback(setup):
    argv, live = setup
    assert card.main(argv, FakeRunner(after=None), live) == 0
    row = json.loads(live.read_text())
    assert row['amount'] == 4
    assert row['balance_after'] is None
    assert 'estimates' in row['note']


def test_spend_tools():
    # Console grammar: non-comment lines contain repo path and cap flag.
    pairs = [line.split() for line in (card.ROOT / 'config/spend-tools.txt').read_text().splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    assert ['tools/flow_shoot_card.py', '--max-credits'] in pairs


def test_ambiguous_project(setup):
    argv, live = setup
    Path(argv[3]).write_text('no project')
    runner = FakeRunner()
    assert card.main(argv, runner, live) == 4
    assert not runner.calls


def test_unwritable_live_path(setup):
    argv, live = setup
    with pytest.raises(FileNotFoundError):
        card.main(argv, FakeRunner(), live.parent / 'missing.jsonl')


def test_duplicate_cap(setup):
    argv, _ = setup
    with pytest.raises(SystemExit):
        card.parse(argv + ['--max-credits', '8'])


def test_clip_conflict_still_accounts(setup):
    argv, live = setup
    dest = Path(argv[7])
    dest.mkdir()
    (dest / 'shot-01.mp4').write_bytes(b'existing')
    assert card.main(argv, FakeRunner(), live) == 2
    assert (dest / 'shot-01.mp4').read_bytes() == b'existing'
    assert json.loads(live.read_text())['amount'] == 5


def test_filtered_tree_help(tmp_path):
    tree = tmp_path / 'tree'
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=card.ROOT).decode().split('\0')
    names += ['tools/flow_shoot_card.py', 'tools/flow_shoot_card_remote.py']
    for name in names:
        src = card.ROOT / name
        if src.is_file() and src.suffix in ('.py', '.yaml', '.toml'):
            dst = tree / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    result = subprocess.run(['/usr/bin/python3', 'tools/flow_shoot_card.py', '--help'],
                            cwd=tree, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '--max-credits' in result.stdout
    # Import itself must neither need Playwright/requests nor import project helpers.
    check = subprocess.run(['/usr/bin/python3', '-c',
        'import tools.flow_shoot_card,sys; '
        'assert not any(x in sys.modules for x in ("requests", "playwright", "tools.flow_shoot"))'],
        cwd=tree, capture_output=True, text=True)
    assert check.returncode == 0, check.stderr
