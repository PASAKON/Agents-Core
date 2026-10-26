"""Offline spend admission, immutable execution and teardown tests. No Colab calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools import colab_batch as cb


@pytest.fixture(autouse=True)
def no_external_process(monkeypatch):
    monkeypatch.setattr(cb.subprocess, 'run', lambda *a, **k: pytest.fail('unexpected subprocess'))
    monkeypatch.setattr(cb.subprocess, 'Popen', lambda *a, **k: pytest.fail('unexpected child'))


@pytest.fixture
def job(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, 'WORK', tmp_path)
    source = tmp_path / 'source'
    files = {cb.ENTRY: b'pass\n', 'workflows/r2v.json': b'{}'}
    for rel, data in files.items():
        p = source / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    monkeypatch.setattr(cb, 'PINNED', {k: hashlib.sha256(v).hexdigest() for k, v in files.items()})
    takes = []
    for i in range(2):
        take = tmp_path / f'take{i}'
        take.mkdir()
        (take / 'ref.png').write_bytes(b'image')
        (take / 'spec.json').write_text(json.dumps({'workflow': 'r2v',
            'budget': {'max_cu': 4, 'max_minutes': 2}, 'scenes': [{'refs': ['ref.png']}]}))
        takes.append(str(take))
    data = {'takes': takes, 'checkpoints': [], 'log': str(tmp_path / 'batch.log'),
            'run_take': {'root': str(source), 'python': sys.executable}}
    path = tmp_path / 'job.json'
    path.write_text(json.dumps(data))
    return path


def invoke(job, balances=(100, 100, 98, 98, 96), cap='10', outcomes=(0, 0), messages=None,
           stop=True):
    reads, calls, stops, sleeps = [], [], [], []
    values, results = iter(balances), iter(outcomes)
    def reader():
        reads.append('balance')
        return next(values)
    def runner(python, root, spec, directory, output, timeout):
        assert root.stat().st_mode & 0o777 == 0o700
        assert not (directory / 'progress.json').exists()
        assert timeout == 420
        calls.append(root)
        output.write((messages or 'ok\n').encode())
        result = next(results)
        if isinstance(result, Exception):
            raise result
        return result
    def stopper(*args):
        stops.append('stop')
        reads.append('stop')
        return stop
    rc = cb.main(['--job', str(job), '--max-credits', cap], balance_reader=reader,
                 take_runner=runner, stop_runner=stopper, sleep=sleeps.append,
                 interpreter_validator=lambda *a: None)
    assert all(not root.exists() for root in calls)
    return rc, calls, stops, sleeps, reads


def test_happy(job, capsys):
    rc, calls, stops, _, events = invoke(job)
    assert rc == 0 and len(calls) == len(stops) == 2
    assert events == ['balance', 'balance', 'stop', 'balance', 'balance', 'stop', 'balance']
    assert 'DONE spent 4 CU' in capsys.readouterr().out


def test_cap(job):
    rc, calls, *_ = invoke(job, balances=(100, 100, 97, 97), cap='6')
    assert rc == cb.EXIT_CAP and len(calls) == 1


@pytest.mark.parametrize('value', ['', None, 'unreadable', 'nan', 'inf', -1])
def test_balance_refuses(job, value):
    rc, calls, *_ = invoke(job, balances=(100, value))
    assert rc == cb.EXIT_BALANCE and not calls


def test_checkpoint(job):
    data = json.loads(job.read_text())
    data['checkpoints'] = [{'after': data['takes'][:1], 'scenes': 2, 'max_cu_per_scene': 0.4}]
    job.write_text(json.dumps(data))
    rc, calls, *_ = invoke(job)
    assert rc == cb.EXIT_CHECKPOINT and len(calls) == 1


@pytest.mark.parametrize('bad', ['spec', 'ref', 'json'])
def test_preflight_zero_cu(job, bad):
    take = job.parent / 'take1'
    if bad == 'json':
        (take / 'spec.json').write_text('not json')
    else:
        (take / ('spec.json' if bad == 'spec' else 'ref.png')).unlink()
    rc, calls, _, _, reads = invoke(job, balances=())
    assert rc == cb.EXIT_BAD and not calls and not reads


@pytest.mark.parametrize('missing', [False, True])
def test_pin_refuses_zero_cu(job, missing):
    entry = job.parent / 'source' / cb.ENTRY
    if missing:
        entry.unlink()
    else:
        entry.write_text('changed')
    rc, calls, _, _, reads = invoke(job, balances=())
    assert rc == cb.EXIT_PIN and not calls and not reads


def test_source_changed_during_copy(job, monkeypatch):
    copy = cb.shutil.copyfile
    def raced(src, dest):
        src.write_text('changed after preflight')
        return copy(src, dest)
    monkeypatch.setattr(cb.shutil, 'copyfile', raced)
    assert invoke(job, balances=())[0] == cb.EXIT_PIN


@pytest.mark.parametrize('message', ['not found', 'FAILED VM', 'failed in provision', 'failed upload'])
def test_provision_retry(job, message):
    rc, calls, stops, sleeps, _ = invoke(job, balances=(100,) * 7, cap='20',
                                       outcomes=(1, 0, 0), messages=message)
    assert rc == 0 and len(calls) == len(stops) == 3 and sleeps == [60]


def test_other_failure_not_retried(job):
    rc, calls, _, sleeps, _ = invoke(job, outcomes=(1,), messages='render error')
    assert rc == cb.EXIT_FAIL and len(calls) == 1 and not sleeps


def test_retry_limit_and_last_six_lines(job):
    result = invoke(job, balances=(100,) * 7, outcomes=(1, 1, 1), cap='20', messages='failed vm')
    assert result[0] == cb.EXIT_FAIL and len(result[1]) == 3 and result[3] == [60, 60]
    result = invoke(job, outcomes=(1,), messages='failed vm\n' + 'render error\n' * 6)
    assert result[0] == cb.EXIT_FAIL and len(result[1]) == 1


@pytest.mark.parametrize('outcome', [-9, subprocess.TimeoutExpired('fake', 1)])
def test_dead_or_hung_child_stops_before_balance(job, outcome):
    result = invoke(job, outcomes=(outcome,))
    assert result[0] == cb.EXIT_FAIL and result[4] == ['balance', 'balance', 'stop', 'balance']


def test_shutdown_unknown_never_counts_spend_or_retries(job):
    result = invoke(job, balances=(100, 100), outcomes=(1,), stop=False, messages='failed vm')
    assert result[0] == cb.EXIT_SHUTDOWN and result[4] == ['balance', 'balance', 'stop']


def test_retry_cap(job):
    result = invoke(job, cap='4', balances=(100, 100, 99, 99), outcomes=(1,), messages='failed vm')
    assert result[0] == cb.EXIT_CAP and len(result[1]) == 1


@pytest.mark.parametrize('args', [['--max-c', '10'], ['--max-credits', '10', '--probe-only'],
                                  ['--max-credits', 'nan']])
def test_exact_arguments(job, args):
    with pytest.raises(SystemExit) as exc:
        cb.main(['--job', str(job), *args])
    assert exc.value.code == 2


def test_unpinned_import_fails(job, monkeypatch):
    # Restore subprocess only for this local, harmless fake entry.
    monkeypatch.undo()
    source = job.parent / 'source'
    (source / cb.ENTRY).write_text('import unpinned_module\n')
    (source / 'scripts/colab/unpinned_module.py').write_text("raise RuntimeError('executed')\n")
    monkeypatch.setattr(cb, 'PINNED', {cb.ENTRY: hashlib.sha256((source / cb.ENTRY).read_bytes()).hexdigest()})
    with cb.pinned_tree(source) as root:
        result = subprocess.run([sys.executable, '-I', '-S', str(root / 'bootstrap.py'), 'unused'],
                                cwd=root, capture_output=True, text=True)
        assert result.returncode != 0 and 'ModuleNotFoundError' in result.stderr
        assert 'RuntimeError' not in result.stderr


def test_parent_timeout_kills_process_group(job, monkeypatch):
    killed = []
    class Process:
        pid = 12345
        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired('fake', timeout)
            return -9
    def popen(argv, **kwargs):
        assert argv[1:3] == ['-I', '-S'] and kwargs['start_new_session']
        return Process()
    monkeypatch.setattr(cb.subprocess, 'Popen', popen)
    monkeypatch.setattr(cb.os, 'killpg', lambda *a: killed.append(a))
    with pytest.raises(subprocess.TimeoutExpired):
        cb.run_take(sys.executable, job.parent, job, job.parent, None, 1)
    assert killed == [(12345, cb.signal.SIGKILL)]


def test_bootstrap_shutdown_uses_pinned_colabctl(job, monkeypatch):
    monkeypatch.undo()
    source = job.parent / 'source'
    module = source / 'scripts/colab/colabctl.py'
    module.write_text("import re\nSESSION_RE = re.compile('unused')\nclass ColabError(Exception): pass\nclass Colab:\n def __init__(self, config): pass\ndef stop_vms(c, names, endpoints):\n return {'remaining': 0}\n")
    monkeypatch.setattr(cb, 'PINNED', {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in source.rglob('*.py')})
    with cb.pinned_tree(source) as root:
        assert cb.shutdown(sys.executable, root, job.parent)


def test_interpreter_permissions(job, monkeypatch):
    executable = job.parent / 'python'
    executable.write_text('')
    executable.chmod(0o777)
    with pytest.raises(cb.PinError):
        cb.trusted_interpreter(str(executable), job.parent)


def test_site_hook_refused(job, monkeypatch):
    executable = job.parent / 'bin/python'
    executable.parent.mkdir()
    executable.write_text('')
    executable.chmod(0o755)
    site = job.parent / 'lib/python3.12/site-packages'
    site.mkdir(parents=True)
    (site / 'checkout.pth').write_text(str(job.parent / 'source'))
    monkeypatch.setattr(cb.subprocess, 'run', lambda *a, **k:
                        subprocess.CompletedProcess(a, 0, json.dumps([str(job.parent), [3, 12]])))
    with pytest.raises(cb.PinError):
        cb.trusted_interpreter(str(executable), job.parent / 'source')


@pytest.mark.parametrize('text,code,expected', [
    ('Current balance: 150.25 CU\n', 0, '150.25'),
    ('', 0, None), ('Current balance: unknown', 0, None),
    ('Current balance: 150', 1, None), ('Current balance: NaN', 0, None),
])
def test_usage_parser_is_offline(monkeypatch, text, code, expected):
    def fake(argv, **kwargs):
        assert argv == ['/root/.local/bin/colab', 'usage']
        assert kwargs['timeout'] == 60
        return subprocess.CompletedProcess(argv, code, text, '')
    monkeypatch.setattr(cb.subprocess, 'run', fake)
    if expected is None:
        with pytest.raises(cb.BalanceError):
            cb.read_balance()
    else:
        assert str(cb.read_balance()) == expected


def test_progress_deleted_before_each_try(job):
    for name in ('take0', 'take1'):
        (job.parent / name / 'progress.json').write_text('{}')
    assert invoke(job)[0] == 0


def test_checkpoint_glob(job):
    data = json.loads(job.read_text())
    data['checkpoints'] = [{'after': str(job.parent / 'take*'), 'scenes': 2, 'max_cu_per_scene': 1}]
    job.write_text(json.dumps(data))
    result = invoke(job)
    assert result[0] == cb.EXIT_CHECKPOINT and len(result[1]) == 2


def test_caller_environment_is_not_forwarded(monkeypatch):
    monkeypatch.setenv('PYTHONPATH', '/untrusted')
    monkeypatch.setenv('COLAB_BIN', '/untrusted')
    monkeypatch.setenv('COLAB_WATCHDOG_RELEASE_CMD', 'unsafe')
    assert cb.child_env() == {'PATH': '/usr/bin:/bin', 'HOME': '/root', 'LANG': 'C.UTF-8',
                              'COLAB_BIN': '/root/.local/bin/colab'}


def test_stdlib_only():
    import ast
    tree = ast.parse(Path(cb.__file__).read_text())
    imports = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imports |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert imports <= sys.stdlib_module_names
