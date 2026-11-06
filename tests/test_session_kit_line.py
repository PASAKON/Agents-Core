import importlib.util
import io
import subprocess
import time
from pathlib import Path

import pytest


@pytest.mark.parametrize('failure', [None, 'pull', 'check'])
def test_deadlines_before_kit(monkeypatch, capsys, failure):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('deadline', root / 'scripts/session-deadline-check.py')
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    calls = []

    def run(argv, **kwargs):
        calls.append(argv[2])
        assert argv[0] == hook.sys.executable
        assert kwargs['cwd'] == root
        assert argv[3] == '--budget'
        assert kwargs['timeout'] == float(argv[4]) + 1
        assert 0 < float(argv[4]) <= (3 if argv[2] == 'pull' else 6.5)
        if argv[2] == failure:
            raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
        return subprocess.CompletedProcess(argv, 0, 'kit ok (12345678 contains origin/main)\n', '')

    monkeypatch.setattr(subprocess, 'run', run)
    monkeypatch.setattr(hook, 'load_env', lambda _: dict(
        SUPABASE_URL='https://fixture.invalid', SUPABASE_SECRET_KEY='test', LUNGNOTE_USER_ID='test'))
    monkeypatch.setattr(hook.urllib.request, 'urlopen', lambda *a, **kw: io.StringIO(
        '[{"text":"Fixture deadline", "due_at":"2026-10-30T00:00:00Z"}]'))
    hook.main()
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1] == ('kit check skipped: TimeoutExpired' if failure else
                        'kit ok (12345678 contains origin/main)')
    assert any('Fixture deadline' in line for line in lines)
    assert calls == (['pull'] if failure == 'pull' else ['pull', 'check'])


@pytest.mark.parametrize('exhausted', [False, True])
def test_slow_kit_preserves_deadlines(monkeypatch, capsys, exhausted):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('deadline', root / 'scripts/session-deadline-check.py')
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    monkeypatch.setattr(hook, 'load_env', lambda _: {})
    calls = []

    def slow(argv, **kwargs):
        calls.append(argv)
        time.sleep(float(argv[-1]))
        raise subprocess.TimeoutExpired(argv, float(argv[-1]))

    monkeypatch.setattr(hook.subprocess, 'run', slow)
    if exhausted:
        ticks = iter([0, 7, 7, 7])
        monkeypatch.setattr(hook.time, 'monotonic', lambda: next(ticks))
    start = time.perf_counter()
    hook.main()
    assert time.perf_counter() - start < 7.5
    lines = capsys.readouterr().out.splitlines()
    assert 'deadlines NOT checked' in lines[0]
    assert len([line for line in lines if line.startswith('kit check skipped:')]) == 1
    if exhausted:
        assert not calls
        assert lines[-1] == 'kit check skipped: no time left'
