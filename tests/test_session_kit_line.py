import importlib.util
import io
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize('failure', [None, 'pull', 'check'])
def test_kit_before_deadlines(monkeypatch, capsys, failure):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('deadline', root / 'scripts/session-deadline-check.py')
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    calls = []

    def run(argv, **kwargs):
        calls.append(argv[-1])
        assert argv[0] == hook.sys.executable
        assert kwargs['cwd'] == root
        assert 0 < kwargs['timeout'] <= 25
        if argv[-1] == failure:
            raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
        return subprocess.CompletedProcess(argv, 0, 'kit ok (12345678 contains origin/main)\n', '')

    monkeypatch.setattr(hook.subprocess, 'run', run)
    monkeypatch.setattr(hook, 'load_env', lambda _: dict(
        SUPABASE_URL='https://fixture.invalid', SUPABASE_SECRET_KEY='test', LUNGNOTE_USER_ID='test'))
    monkeypatch.setattr(hook.urllib.request, 'urlopen', lambda *a, **kw: io.StringIO(
        '[{"text":"Fixture deadline", "due_at":"2026-10-30T00:00:00Z"}]'))
    hook.main()
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == ('kit check skipped: TimeoutExpired' if failure else
                        'kit ok (12345678 contains origin/main)')
    assert any('Fixture deadline' in line for line in lines)
    assert calls == (['pull'] if failure == 'pull' else ['pull', 'check'])
