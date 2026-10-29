import argparse
import base64
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import shutil
import io
import sys
from types import SimpleNamespace

import pytest

from tools import flow_shoot_card as card
from tools import flow_shoot_card_remote as remote


class FakeRunner:
    def __init__(self, before=100, after=95, lock=True, mismatch=False, terminate=False):
        self.balances = iter([before, after])
        self.lock = lock
        self.mismatch = mismatch
        self.terminate = terminate
        self.calls = []
        self.killed = []
        self.files = {}
        self.outputs = {'ledger.tsv': b'shot\tstatus\n1\tverified\n',
                        'out/shot-01.mp4': b'clip'}

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
        if verb == 'list':
            return [dict(name=n, size=len(b), sha256=card.digest(b)) for n, b in self.outputs.items()]
        if verb == 'get':
            return base64.b64encode(self.outputs[kw['name']]).decode()
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
        '--dest', f + r'\out', '--resolution', '720p', '--aspect', '9:16',
        '--only', '1-2', '--dry-run']
    assert kw['argv'].count('--max-credits') == 1
    assert '--credit-cap' not in kw['argv']


@pytest.mark.parametrize('flag', ['--max', '-m', '-N', '--credit-cap'])
def test_no_aliases(setup, flag):
    argv, _ = setup
    argv[0] = flag
    with pytest.raises(SystemExit) as error:
        card.parse(argv)
    assert error.value.code == 2


@pytest.mark.parametrize('aspect', [None, '9:16', '16:9'])
def test_card_aspect_forwarded(setup, aspect):
    argv, _ = setup
    args = card.parse(argv + (['--aspect', aspect] if aspect else []))
    assert args.aspect == (aspect or '9:16')
    inner = card.inner_argv(args, 'folder')
    assert inner.count('--aspect') == 1
    assert inner[inner.index('--aspect') + 1] == args.aspect
    assert inner.count('--max-credits') == 1


@pytest.mark.parametrize('extra', [
    ['--aspect', '4:3'], ['--aspect', '1:1'], ['--asp', '16:9'], ['-a', '16:9'],
])
def test_card_rejects_invalid_aspect(setup, extra):
    argv, _ = setup
    with pytest.raises(SystemExit) as exc:
        card.parse(argv + extra)
    assert exc.value.code == 2


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
    assert any(v == 'list' for v, _ in runner.calls)
    assert len(live.read_text().splitlines()) == 1


def test_taskkill_command(monkeypatch):
    calls = []
    def run(*a, **kw):
        calls.append((a, kw))
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(card.subprocess, 'run', run)
    card.Runner.kill(None, r'C:\mooniex\flowcard\abc\run')
    assert calls[0][0][0] == ['ssh', 'winbox', 'powershell -NoProfile -NonInteractive -Command -']
    assert 'taskkill /PID $p /T /F' in calls[0][1]['input']
    assert calls[0][1]['check'] is False


def test_failed_kill_still_accounts(setup, monkeypatch, capsys):
    argv, live = setup
    runner = FakeRunner(terminate=True)
    runner.kill = lambda folder: card.Runner.kill(None, folder)
    monkeypatch.setattr(card.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=1))
    assert card.main(argv, runner, live) == 143
    assert any(v == 'get' for v, _ in runner.calls)
    assert len(live.read_text().splitlines()) == 1
    assert 'taskkill return code: 1' in capsys.readouterr().out


def test_balance_rose(setup):
    argv, live = setup
    assert card.main(argv, FakeRunner(after=120), live) == 0
    row = json.loads(live.read_text())
    assert row['amount'] == 4
    assert row['balance_before'] == 100
    assert row['balance_after'] == 120
    assert 'balance rose by 20; amount = estimate sum' in row['note']


def test_one_get_per_clip(setup):
    argv, live = setup
    class Runner(FakeRunner):
        def call(self, verb, **kw):
            if verb == 'get' and kw['name'] == 'out/shot-03.mp4':
                assert (Path(argv[7]) / 'shot-02.mp4').read_bytes() == b'clip2'
            return super().call(verb, **kw)
    runner = Runner()
    runner.outputs.update({'out/shot-02.mp4': b'clip2', 'out/shot-03.mp4': b'clip3'})
    assert card.main(argv, runner, live) == 0
    assert [kw['name'] for v, kw in runner.calls if v == 'get'] == list(runner.outputs)
    for name, data in runner.outputs.items():
        if name.startswith('out/'):
            assert (Path(argv[7]) / Path(name).name).read_bytes() == data


@pytest.mark.parametrize('name', ['ledger.tsv', 'out/shot-01.mp4'])
def test_pull_hash_mismatch(setup, name):
    argv, live = setup
    class Runner(FakeRunner):
        def call(self, verb, **kw):
            result = super().call(verb, **kw)
            if verb == 'list':
                next(e for e in result if e['name'] == name)['sha256'] = '0' * 64
            return result
    original = Path(argv[5]).read_bytes()
    assert card.main(argv, Runner(), live) == 2
    assert Path(argv[5]).read_bytes() == original
    assert len(live.read_text().splitlines()) == 1


def remote_requests(monkeypatch, tmp_path, requests, busy=False):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, 'msvcrt', SimpleNamespace(LK_NBLCK=1, locking=lambda *a: None))
    monkeypatch.setattr(remote, 'other_flow_job', lambda: busy)
    monkeypatch.setattr(remote, 'ensure_tab', lambda project: None)
    monkeypatch.setattr(sys, 'stdin', io.StringIO('\n'.join(json.dumps(q) for q in [{'verb': 'lock'}] + requests)))
    output = io.StringIO()
    monkeypatch.setattr(sys, 'stdout', output)
    remote.serve()
    return [json.loads(line) for line in output.getvalue().splitlines()]


@pytest.mark.parametrize('settles', [True, False])
def test_remote_balance_retry(monkeypatch, tmp_path, settles):
    outputs = iter(['btn none\n', 'BALANCE ?\n', 'BALANCE 73\n' if settles else 'BALANCE ?\n'])
    calls, sleeps = [], []
    def run(*args, **kw):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=next(outputs))
    monkeypatch.setattr(remote.subprocess, 'run', run)
    monkeypatch.setattr(remote.time, 'sleep', sleeps.append)
    replies = remote_requests(monkeypatch, tmp_path, [dict(verb='balance', project='https://flow.google.com/project/own',
        source=(card.ROOT / 'tools/flow_balance_ws.py').read_text())])
    assert replies[-1] == {'result': 73 if settles else None}
    assert len(calls) == 3
    assert sleeps == [5, 5]
    source = calls[0][0][3]
    assert repr(remote.own_tab('https://flow.google.com/project/own')) in source
    assert 'assert mine,' in source and 'mine.sort(' in source


@pytest.mark.parametrize('url, mine', [
    ('https://flow.google.com/project/own', True),
    ('https://flow.google.com/project/own/edit/clip-1', True),
    ('https://flow.google.com/project/own?pli=1', True),
    ('https://flow.google.com/u/1/project/own', True),
    ('https://flow.google.com/project/owner', False),
    ('https://flow.google.com/project/other', False),
    ('https://flow.google.com/', False),
    ('https://evil.example/flow.google.com/project/own', False),
])
def test_own_tab(url, mine):
    assert bool(re.match(remote.own_tab('https://flow.google.com/project/own'), url)) is mine


@pytest.mark.parametrize('open_tabs, opened', [
    ([{'type': 'page', 'url': 'https://flow.google.com/project/own/edit/x'}], False),
    ([{'type': 'page', 'url': 'https://flow.google.com/'}], True),
])
def test_ensure_tab(monkeypatch, open_tabs, opened):
    requests, lists = [], [open_tabs, open_tabs + [{'type': 'page', 'url': 'https://flow.google.com/project/own'}]]
    def urlopen(req, timeout):
        url = req if isinstance(req, str) else req.full_url
        requests.append((getattr(req, 'method', 'GET'), url))
        return io.BytesIO(json.dumps(lists.pop(0) if url.endswith('/json/list') else {}).encode())
    monkeypatch.setattr(remote.urllib.request, 'urlopen', urlopen)
    monkeypatch.setattr(remote.time, 'sleep', lambda s: None)
    remote.ensure_tab('https://flow.google.com/project/own')
    puts = [r for r in requests if r[0] == 'PUT']
    assert puts == ([('PUT', remote.CDP + '/json/new?https://flow.google.com/project/own')] if opened else [])
    assert not any('/json/close' in url for _, url in requests)


def test_remote_lock_refuses_other_flow_job(monkeypatch, tmp_path):
    replies = remote_requests(monkeypatch, tmp_path, [dict(verb='balance', project='p/project/own', source='')],
                              busy=True)
    assert replies[0] == {'result': False}
    assert replies[1] == {'error': 'lock required'}


@pytest.mark.parametrize('lines, busy', [
    (r'C:\mooniex\pwvenv\Scripts\python.exe tools\flow_shoot.py run --sheet x', True),
    (r'python.exe -u -c boot C:\mooniex\flowcard\a\b\tools\flow_shoot_card_remote.py shoot', False),
    (r'python.exe tools\flow_balance_ws.py 29b3326b --reload', False),
    ('', False),
])
def test_other_flow_job(monkeypatch, lines, busy):
    monkeypatch.setattr(remote.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout=lines + '\n'))
    assert remote.other_flow_job() is busy


def test_remote_list_and_get(monkeypatch, tmp_path):
    folder = tmp_path / 'run'
    (folder / 'out').mkdir(parents=True)
    files = {'ledger.tsv': b'ledger', **{f'out/shot-{i}.mp4': bytes([i]) for i in range(3)}}
    for name, data in files.items():
        (folder / name).write_bytes(data)
    replies = remote_requests(monkeypatch, tmp_path, [dict(verb='list', folder=str(folder))] +
        [dict(verb='get', folder=str(folder), name=name) for name in files])
    assert sorted(replies[1]['result'], key=lambda e: e['name']) == sorted(
        [dict(name=n, size=len(b), sha256=card.digest(b)) for n, b in files.items()], key=lambda e: e['name'])
    assert [base64.b64decode(r['result']) for r in replies[2:]] == list(files.values())


@pytest.mark.parametrize('front_raises', [False, True])
def test_remote_attach_foreground(monkeypatch, tmp_path, front_raises):
    from tools import flow_shoot
    events = []
    project = 'https://flow.google.com/project/own'
    (tmp_path / 'project.txt').write_text(project)
    def front():
        events.append('front')
        if front_raises:
            raise RuntimeError('foreground unavailable')
    own = SimpleNamespace(url=project, bring_to_front=front, on=lambda *a: events.append('response'))
    other = SimpleNamespace(url='https://flow.google.com/project/other')
    own_edit = SimpleNamespace(url=project + '/edit/clip-1')
    browser = SimpleNamespace(contexts=[SimpleNamespace(pages=[other, own_edit, own])])
    def start():
        events.append('start')
        return SimpleNamespace(chromium=SimpleNamespace(connect_over_cdp=lambda url: browser))
    monkeypatch.setitem(sys.modules, 'playwright.sync_api', SimpleNamespace(sync_playwright=lambda: SimpleNamespace(start=start)))
    monkeypatch.setattr(flow_shoot.flow_cdp, 'enforce_platform', lambda: events.append('platform'))
    monkeypatch.setattr(flow_shoot.FlowBrowser, 'attach', flow_shoot.FlowBrowser.attach)
    def main(args):
        instance = SimpleNamespace(cdp_url='http://127.0.0.1:9226', _on_response=lambda r: None)
        assert flow_shoot.FlowBrowser.attach(instance) is own
        return 0
    monkeypatch.setattr(flow_shoot, 'main', main)
    monkeypatch.setattr(sys, 'argv', ['remote.py', 'shoot', str(tmp_path), 'run'])
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(card.ROOT))
    monkeypatch.setenv('FLOW_CDP', 'test')
    with pytest.raises(SystemExit) as exc:
        remote.shoot()
    assert exc.value.code == 0
    assert events == ['platform', 'start', 'front', 'response']


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


def plant(path, victim, link):
    path.unlink()
    if link == 'symlink':
        path.symlink_to(victim)
    elif link == 'hardlink':
        os.link(victim, path)
    else:
        os.mkfifo(path)


# The card runs as root and state/ is group-writable: a planted link must not redirect it.
@pytest.mark.parametrize('which', [3, 5])
@pytest.mark.parametrize('link', ['symlink', 'hardlink', 'fifo'])
def test_refuses_linked_input(setup, tmp_path, which, link, capsys):
    argv, live = setup
    victim = tmp_path / 'victim'
    victim.write_bytes(Path(argv[which]).read_bytes())
    plant(Path(argv[which]), victim, link)
    runner = FakeRunner()
    assert card.main(argv, runner, live) == 4
    assert not runner.calls
    assert capsys.readouterr().out.startswith('refused: ')


@pytest.mark.parametrize('link', ['symlink', 'hardlink'])
def test_ledger_swapped_before_write(setup, tmp_path, link):
    argv, live = setup
    victim = tmp_path / 'victim'
    victim.write_bytes(b'root only\n')
    class Runner(FakeRunner):
        def call(self, verb, **kw):
            if verb == 'get' and kw['name'].startswith('out/'):
                plant(Path(argv[5]), victim, link)  # after the compare-and-swap read
            return super().call(verb, **kw)
    assert card.main(argv, Runner(), live) == 2
    assert victim.read_bytes() == b'root only\n'
    assert len(live.read_text().splitlines()) == 1


def test_dest_symlink(setup, tmp_path):
    argv, live = setup
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    Path(argv[7]).symlink_to(elsewhere)
    original = Path(argv[5]).read_bytes()
    assert card.main(argv, FakeRunner(), live) == 2
    assert not list(elsewhere.iterdir())
    assert Path(argv[5]).read_bytes() == original
    assert len(live.read_text().splitlines()) == 1


def test_existing_clip_symlink(setup, tmp_path):
    argv, live = setup
    victim = tmp_path / 'victim'
    victim.write_bytes(b'clip')
    dest = Path(argv[7])
    dest.mkdir()
    (dest / 'shot-01.mp4').symlink_to(victim)
    assert card.main(argv, FakeRunner(), live) == 2
    assert (dest / 'shot-01.mp4').is_symlink()


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
